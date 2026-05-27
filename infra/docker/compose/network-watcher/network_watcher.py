"""
network_watcher.py - Conecta workers/app-containers de Shuffle a TARGET_NETWORK
antes de que arranquen, para que el DNS de soar_soar_net esté disponible.
"""
import docker
import os
import threading

TARGET_NETWORK = os.environ.get('TARGET_NETWORK', 'soar_soar_net')

def is_shuffle_container(name):
    return (name.startswith('worker-') or
            name.startswith('HTTP_')   or
            '_act_' in name)

INJECT_HOSTS = os.environ.get('INJECT_HOSTS', 'shuffle-backend,elasticsearch,thehive,misp').split(',')

def get_ip(client, container_name, network_name):
    try:
        c = client.containers.get(container_name)
        return c.attrs['NetworkSettings']['Networks'].get(network_name, {}).get('IPAddress', '')
    except Exception:
        return ''

def inject_hosts(c, client, network_name):
    """Inyecta entradas en /etc/hosts del container.
    Prioriza IPs de la red 'bridge' (accesibles sin DNS desde workers)
    y hace fallback a IPs de target_network."""
    try:
        lines = []
        for svc in INJECT_HOSTS:
            # Preferir IP de bridge para que no dependa de DNS
            ip = get_ip(client, f'soar_{svc.replace("-", "_")}', 'bridge')
            if not ip:
                ip = get_ip(client, svc, 'bridge')
            if not ip:
                ip = get_ip(client, f'soar_{svc.replace("-", "_")}', network_name)
            if not ip:
                ip = get_ip(client, svc, network_name)
            if ip:
                lines.append(f'{ip}\t{svc}')
        if not lines:
            return
        entry = '\\n'.join(lines)
        c.exec_run(['sh', '-c', f'printf "{entry}\\n" >> /etc/hosts'], user='root')
        print(f'[watcher] hosts injected into {c.name}: {[l.split()[1] for l in lines]}', flush=True)
    except Exception as e:
        print(f'[watcher] hosts inject ERR {c.name}: {e}', flush=True)

DOCKER_PROXY_HOST = os.environ.get('DOCKER_PROXY_HOST', 'host.docker.internal')
DOCKER_PROXY_PORT = os.environ.get('DOCKER_PROXY_PORT', '2375')

def setup_docker_socket(c):
    """Crea /var/run/docker.sock en el worker como Unix socket que forwarda al proxy TCP Docker."""
    import tarfile, io, os as _os, subprocess as _sp
    try:
        # Copiar socat desde la imagen del watcher al worker (usar binario real, no symlink)
        socat_path = '/usr/bin/socat1'
        if not _os.path.exists(socat_path):
            socat_path = '/usr/bin/socat'
        if not _os.path.isfile(socat_path):
            print(f'[watcher] socat binary not found, skipping socket setup', flush=True)
            return

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w') as tf:
            tf.add(socat_path, arcname='socat')
        buf.seek(0)
        c.put_archive('/usr/local/bin/', buf.read())

        # Lanzar socat como daemon dentro del worker
        cmd = (
            f'chmod +x /usr/local/bin/socat && '
            f'mkdir -p /var/run && rm -f /var/run/docker.sock && '
            f'nohup /usr/local/bin/socat '
            f'UNIX-LISTEN:/var/run/docker.sock,fork,reuseaddr,mode=777 '
            f'TCP:{DOCKER_PROXY_HOST}:{DOCKER_PROXY_PORT} '
            f'>/tmp/socat.log 2>&1 &'
        )
        c.exec_run(['sh', '-c', cmd], user='root', detach=True)
        print(f'[watcher] docker socket forwarded in {c.name} -> {DOCKER_PROXY_HOST}:{DOCKER_PROXY_PORT}', flush=True)
    except Exception as e:
        print(f'[watcher] socket ERR {c.name}: {e}', flush=True)


def fix_resolv(c, network_name):
    """Reescribe /etc/resolv.conf para que el DNS embebido de Docker resuelva
    hostnames de soar_soar_net. Necesita ejecutarse después de 'start'."""
    try:
        new_conf = (
            'nameserver 127.0.0.11\n'
            'options ndots:0\n'
        )
        c.exec_run(
            ['sh', '-c', f'echo "{new_conf}" > /etc/resolv.conf'],
            user='root'
        )
        print(f'[watcher] resolv.conf fixed in {c.name}', flush=True)
    except Exception as e:
        print(f'[watcher] resolv ERR {c.name}: {e}', flush=True)


def attach(client, cid, name, network_name, action='start'):
    import time as _t
    try:
        net = client.networks.get(network_name)
        c   = client.containers.get(cid)

        # Conectar a la red
        nets = c.attrs.get('NetworkSettings', {}).get('Networks', {})
        if network_name not in nets:
            net.connect(c)
            print(f'[watcher] +net {name} -> {network_name} t={_t.time():.4f}', flush=True)

        # Inyectar hosts/resolv/socket solo si el container ya está corriendo (evento start)
        if action != 'create' and name.startswith('worker-'):
            c.reload()
            if c.status == 'running':
                threading.Thread(target=fix_resolv, args=(c, network_name), daemon=True).start()
                threading.Thread(target=inject_hosts, args=(c, client, network_name), daemon=True).start()
                threading.Thread(target=setup_docker_socket, args=(c,), daemon=True).start()
    except Exception as e:
        print(f'[watcher] ERR {name}: {e}', flush=True)


def inject_hosts_file(c, client, network_name):
    """Escribe entradas de hosts en el archivo /etc/hosts del container antes de que arranque,
    usando docker cp con un archivo temporal."""
    import tempfile, tarfile, io
    try:
        lines = []
        for svc in INJECT_HOSTS:
            ip = get_ip(client, f'soar_{svc.replace("-", "_")}', network_name)
            if not ip:
                ip = get_ip(client, svc, network_name)
            if ip:
                lines.append(f'{ip}\t{svc}\n')
        if not lines:
            return

        # Leer /etc/hosts actual del container
        bits, _ = c.get_archive('/etc/hosts')
        buf = io.BytesIO(b''.join(bits))
        with tarfile.open(fileobj=buf) as tf:
            existing = tf.extractfile('hosts').read().decode()

        new_content = existing + ''.join(lines)
        new_buf = io.BytesIO()
        with tarfile.open(fileobj=new_buf, mode='w') as tf:
            data = new_content.encode()
            info = tarfile.TarInfo(name='hosts')
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        new_buf.seek(0)
        c.put_archive('/etc/', new_buf.read())
        print(f'[watcher] hosts pre-injected (create) into {c.name}: {[l.split()[1] for l in lines]}', flush=True)
    except Exception as e:
        print(f'[watcher] hosts file ERR {c.name}: {e}', flush=True)

def main():
    client = docker.from_env()
    print(f'[watcher] Watching -> {TARGET_NETWORK}', flush=True)

    # Conectar workers ya corriendo
    for c in client.containers.list():
        if is_shuffle_container(c.name):
            threading.Thread(target=attach, args=(client, c.id, c.name, TARGET_NETWORK), daemon=True).start()

    import time
    # Escuchar create + start (start como fallback)
    for event in client.events(decode=True, filters={'type': 'container', 'event': ['create', 'start']}):
        name   = event.get('Actor', {}).get('Attributes', {}).get('name', '')
        cid    = event.get('Actor', {}).get('ID', '')
        action = event.get('Action', 'start')
        if is_shuffle_container(name):
            t = time.time()
            print(f'[watcher] event={action} name={name} t={t:.4f}', flush=True)
            if action == 'create':
                # Síncrono: garantiza que net.connect termina antes de que Orborus llame a start
                attach(client, cid, name, TARGET_NETWORK, action)
            else:
                # start/die: asíncrono para no bloquear el event loop
                threading.Thread(target=attach, args=(client, cid, name, TARGET_NETWORK, action), daemon=True).start()

if __name__ == '__main__':
    main()
