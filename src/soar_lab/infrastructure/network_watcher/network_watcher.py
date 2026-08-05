"""
network_watcher.py - Conecta workers/app-containers de Shuffle a TARGET_NETWORK
antes de que arranquen, para que el DNS de la red SOAR esté disponible.
"""
import docker
import ipaddress
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TARGET_NETWORK = os.environ.get('TARGET_NETWORK', 'soar_net')


def is_shuffle_container(name):
    return (name.startswith('worker-') or
            name.startswith('HTTP_') or
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
    Busca IPs en target_network primero (donde están los servicios SOAR)."""
    try:
        lines = []
        for svc in INJECT_HOSTS:
            # Mapeo de nombres de servicios a nombres de contenedores
            container_names = [
                f'soar_{svc.replace("-", "_")}',  # e.g., soar_thehive
                svc,  # e.g., thehive
            ]
            # Buscar IP en target_network primero (red SOAR)
            ip = None
            for cname in container_names:
                ip = get_ip(client, cname, network_name)
                if ip:
                    break
            # Fallback a bridge si no se encuentra
            if not ip:
                for cname in container_names:
                    ip = get_ip(client, cname, 'bridge')
                    if ip:
                        break
            if ip:
                lines.append(f'{ip}\t{svc}')
        if not lines:
            print(f'[watcher] no IPs found for hosts injection in {c.name}', flush=True)
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
    hostnames de la red SOAR. Necesita ejecutarse después de 'start'."""
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
        c = client.containers.get(cid)

        # Verificar si el contenedor está en network_mode compartido (container:orborus)
        # Estos contenedores no pueden conectarse a redes adicionales
        network_mode = c.attrs.get('HostConfig', {}).get('NetworkMode', '')
        if network_mode.startswith('container:'):
            print(f'[watcher] skip {name} (network_mode={network_mode})', flush=True)
            # Aún inyectar hosts si es un contenedor Shuffle
            if (name.startswith('worker-') or is_shuffle_container(name)):
                c.reload()
                if c.status == 'running':
                    threading.Thread(target=fix_resolv, args=(c, network_name), daemon=True).start()
                    threading.Thread(target=inject_hosts, args=(c, client, network_name), daemon=True).start()
                    threading.Thread(target=setup_docker_socket, args=(c,), daemon=True).start()
            return

        # Conectar a la red
        nets = c.attrs.get('NetworkSettings', {}).get('Networks', {})
        if network_name not in nets:
            net.connect(c)
            print(f'[watcher] +net {name} -> {network_name} t={_t.time():.4f}', flush=True)

        # Inyectar hosts en workers y en contenedores de apps Shuffle (TheHive, MISP, etc.)
        if (name.startswith('worker-') or is_shuffle_container(name)):
            c.reload()
            if c.status == 'running':
                threading.Thread(target=fix_resolv, args=(c, network_name), daemon=True).start()
                threading.Thread(target=inject_hosts, args=(c, client, network_name), daemon=True).start()
                threading.Thread(target=setup_docker_socket, args=(c,), daemon=True).start()
            elif action == 'create' and is_shuffle_container(name):
                # Pre-inyectar hosts en contenedores de apps antes de que arranquen
                threading.Thread(target=inject_hosts_file, args=(c, client, network_name), daemon=True).start()
    except Exception as e:
        print(f'[watcher] ERR {name}: {e}', flush=True)


def inject_hosts_file(c, client, network_name):
    """Escribe entradas de hosts en el archivo /etc/hosts del container antes de que arranque,
    usando docker cp con un archivo temporal."""
    import tempfile, tarfile, io, time as _t
    max_retries = 5
    for attempt in range(max_retries):
        try:
            lines = []
            for svc in INJECT_HOSTS:
                container_names = [
                    f'soar_{svc.replace("-", "_")}',
                    svc,
                ]
                ip = None
                for cname in container_names:
                    ip = get_ip(client, cname, network_name)
                    if ip:
                        break
                if ip:
                    lines.append(f'{ip}\t{svc}\n')
            if not lines:
                print(f'[watcher] no IPs found for hosts file injection in {c.name}', flush=True)
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
            return
        except Exception as e:
            if attempt < max_retries - 1:
                _t.sleep(0.1)
            else:
                print(f'[watcher] hosts file ERR {c.name} (attempt {attempt + 1}/{max_retries}): {e}', flush=True)


def create_handler(client):
    class Handler(BaseHTTPRequestHandler):
        def _write_json(self, status, body):
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == '/health':
                try:
                    network = client.networks.get(TARGET_NETWORK)
                    self._write_json(200, {'status': 'ok', 'network': network.name})
                except docker.errors.NotFound:
                    self._write_json(503, {'status': 'unavailable', 'network': TARGET_NETWORK})
                return
            if parsed.path == '/api/connections':
                query = parse_qs(parsed.query)
                raw_limit = query.get('limit', ['100'])[0]
                requested_ip = query.get('ip', [None])[0]
                try:
                    limit = int(raw_limit)
                    if not 1 <= limit <= 1000:
                        raise ValueError
                    if requested_ip is not None:
                        ipaddress.ip_address(requested_ip)
                except ValueError:
                    self._write_json(400, {'error': 'ip must be a valid address and limit must be between 1 and 1000'})
                    return
                try:
                    containers = client.networks.get(TARGET_NETWORK).attrs.get('Containers') or {}
                    connections = [{'id': container_id, 'name': container.get('Name', ''),
                                    'ip': container.get('IPv4Address', '').split('/')[0],
                                    'endpoint_id': container.get('EndpointID', '')} for container_id, container in
                                   containers.items()]
                    if requested_ip is not None:
                        connections = [connection for connection in connections if connection['ip'] == requested_ip]
                    self._write_json(200, {'network': TARGET_NETWORK, 'total': len(connections),
                                           'connections': connections[:limit]})
                except docker.errors.NotFound:
                    self._write_json(503, {'error': f'network {TARGET_NETWORK} is unavailable'})
                return
            prefix = '/api/connections/'
            if parsed.path.startswith(prefix):
                connection_id = parsed.path[len(prefix):]
                try:
                    containers = client.networks.get(TARGET_NETWORK).attrs.get('Containers') or {}
                    container = containers.get(connection_id)
                    if container is None:
                        self._write_json(404, {'error': 'connection not found'})
                    else:
                        self._write_json(200, {'id': connection_id, 'name': container.get('Name', ''),
                                               'ip': container.get('IPv4Address', '').split('/')[0],
                                               'endpoint_id': container.get('EndpointID', ''),
                                               'network': TARGET_NETWORK})
                except docker.errors.NotFound:
                    self._write_json(503, {'error': f'network {TARGET_NETWORK} is unavailable'})
                return
            self._write_json(404, {'error': 'not found'})

        def log_message(self, format, *args):
            return

    return Handler


def start_http_server(client):
    server = ThreadingHTTPServer(('0.0.0.0', 8080), create_handler(client))
    threading.Thread(target=server.serve_forever, daemon=True).start()


def main():
    client = docker.from_env()
    start_http_server(client)
    print(f'[watcher] Watching -> {TARGET_NETWORK}', flush=True)

    # Conectar workers ya corriendo
    for c in client.containers.list():
        if is_shuffle_container(c.name):
            threading.Thread(target=attach, args=(client, c.id, c.name, TARGET_NETWORK), daemon=True).start()

    import time
    # Escuchar create + start (start como fallback)
    for event in client.events(decode=True, filters={'type': 'container', 'event': ['create', 'start']}):
        name = event.get('Actor', {}).get('Attributes', {}).get('name', '')
        cid = event.get('Actor', {}).get('ID', '')
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
