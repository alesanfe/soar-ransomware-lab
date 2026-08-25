"""network_watcher.py - Conecta workers/app-containers de Shuffle a TARGET_NETWORK.

antes de que arranquen, para que el DNS de la red SOAR esté disponible.
"""

import logging
import os
import threading
from http.server import ThreadingHTTPServer

import docker

# Support both soar_lab package context (API container) and standalone
# context (lightweight Alpine watcher container).
try:
    from soar_lab.infrastructure.network_watcher._constants import (
        CONTENT_TYPE_JSON,
        DEFAULT_DOCKER_SOCKET_MODE,
        HEADER_CONTENT_TYPE,
        TARGET_NETWORK,
    )
    from soar_lab.infrastructure.network_watcher._handler import create_handler
except ImportError:
    from _constants import (  # type: ignore[no-redef]
        CONTENT_TYPE_JSON,
        DEFAULT_DOCKER_SOCKET_MODE,
        HEADER_CONTENT_TYPE,
        TARGET_NETWORK,
    )
    from _handler import create_handler  # type: ignore[no-redef]

# Re-exported for test compatibility
__all__ = [
    "CONTENT_TYPE_JSON",
    "HEADER_CONTENT_TYPE",
    "TARGET_NETWORK",
    "DEFAULT_DOCKER_SOCKET_MODE",
    "create_handler",
    "is_shuffle_container",
    "get_ip",
    "inject_hosts",
    "setup_docker_socket",
    "fix_resolv",
    "attach",
    "inject_hosts_file",
    "start_http_server",
    "main",
]

logger = logging.getLogger(__name__)


def is_shuffle_container(name: str) -> bool:
    """Check whether a container name belongs to a Shuffle worker or app.

    Args:
        name: Container name to check.

        Returns:
            True if the container is a Shuffle worker or app container.
    """
    return name.startswith("worker-") or name.startswith("HTTP_") or "_act_" in name


INJECT_HOSTS = os.environ.get("INJECT_HOSTS", "shuffle-backend,elasticsearch,thehive,misp").split(
    ","
)


def get_ip(client: docker.DockerClient, container_name: str, network_name: str) -> str:
    """Retrieve the IP address of a container on a given network.

    Args:
        client: Docker client instance.
        container_name: Name of the container to inspect.
        network_name: Name of the network to look up.

    Returns:
        The container's IP address string, or empty string on error.
    """
    try:
        c = client.containers.get(container_name)
        return c.attrs["NetworkSettings"]["Networks"].get(network_name, {}).get("IPAddress", "")
    except Exception:
        return ""


def _resolve_service_ip(
    client: docker.DockerClient,
    svc: str,
    network_name: str,
) -> str | None:
    """Resolve the IP address for a service on the target network.

    Busca IPs en target_network primero (donde están los servicios
    SOAR) y hace fallback a la red ``bridge`` si no se encuentra.

    Args:
        client: Docker client instance.
        svc: Service name to resolve.
        network_name: Target network to look up first.

    Returns:
        The resolved IP address string, or ``None`` if not found.
    """
    # Mapeo de nombres de servicios a nombres de contenedores
    container_names = [
        f"soar_{svc.replace('-', '_')}",  # e.g., soar_thehive
        svc,  # e.g., thehive
    ]
    # Buscar IP en target_network primero (red SOAR)
    for cname in container_names:
        ip = get_ip(client, cname, network_name)
        if ip:
            return ip
    # Fallback a bridge si no se encuentra
    for cname in container_names:
        ip = get_ip(client, cname, "bridge")
        if ip:
            return ip
    return None


def _build_hosts_lines(
    client: docker.DockerClient,
    network_name: str,
) -> list[str]:
    """Build a list of ``"ip\\tsvc"`` entries for all injectable services.

    Args:
        client: Docker client instance.
        network_name: Target network to look up first.

    Returns:
        A list of ``"ip\\tsvc"`` strings for services whose IP was found.
    """
    lines = []
    for svc in INJECT_HOSTS:
        ip = _resolve_service_ip(client, svc, network_name)
        if ip:
            lines.append(f"{ip}\t{svc}")
    return lines


def inject_hosts(
    c: docker.models.containers.Container,
    client: docker.DockerClient,
    network_name: str,
) -> None:
    """Inyecta entradas en /etc/hosts del container.

    Busca IPs en target_network primero (donde están los servicios
    SOAR).
    """
    try:
        lines = _build_hosts_lines(client, network_name)
        if not lines:
            logger.warning(f"[watcher] no IPs found for hosts injection in {c.name}")
            return
        entry = "\\n".join(lines)
        c.exec_run(["sh", "-c", f'printf "{entry}\\n" >> /etc/hosts'], user="root")
        logger.info(
            f"[watcher] hosts injected into {c.name}: {[line.split()[1] for line in lines]}"
        )
    except Exception as e:
        logger.error(f"[watcher] hosts inject ERR {c.name}: {e}")


DOCKER_PROXY_HOST = os.environ.get("DOCKER_PROXY_HOST", "host.docker.internal")
DOCKER_PROXY_PORT = os.environ.get("DOCKER_PROXY_PORT", "2375")


def setup_docker_socket(c: docker.models.containers.Container) -> None:
    """Crea /var/run/docker.sock en el worker como Unix socket que forwarda al.

    proxy TCP Docker.
    """
    import io
    import os as _os
    import tarfile

    try:
        # Copiar socat desde la imagen del watcher al worker (usar binario real, no symlink)
        socat_path = "/usr/bin/socat1"
        if not _os.path.exists(socat_path):
            socat_path = "/usr/bin/socat"
        if not _os.path.isfile(socat_path):
            logger.warning("[watcher] socat binary not found, skipping socket setup")
            return

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tf:
            tf.add(socat_path, arcname="socat")
        buf.seek(0)
        c.put_archive("/usr/local/bin/", buf.read())

        # Lanzar socat como daemon dentro del worker
        cmd = (
            f"chmod +x /usr/local/bin/socat && "
            f"mkdir -p /var/run && rm -f /var/run/docker.sock && "
            f"nohup /usr/local/bin/socat "
            f"UNIX-LISTEN:/var/run/docker.sock,fork,reuseaddr,mode={DEFAULT_DOCKER_SOCKET_MODE} "
            f"TCP:{DOCKER_PROXY_HOST}:{DOCKER_PROXY_PORT} "
            f">/tmp/socat.log 2>&1 &"
        )
        c.exec_run(["sh", "-c", cmd], user="root", detach=True)
        logger.info(
            f"[watcher] docker socket forwarded in {c.name} -> "
            f"{DOCKER_PROXY_HOST}:{DOCKER_PROXY_PORT}"
        )
    except Exception as e:
        logger.error(f"[watcher] socket ERR {c.name}: {e}")


def fix_resolv(c: docker.models.containers.Container, network_name: str) -> None:
    """Reescribe /etc/resolv.conf para que el DNS embebido de Docker resuelva.

    hostnames de la red SOAR.

    Necesita ejecutarse después de 'start'.
    """
    try:
        new_conf = "nameserver 127.0.0.11\noptions ndots:0\n"
        c.exec_run(["sh", "-c", f'echo "{new_conf}" > /etc/resolv.conf'], user="root")
        logger.info(f"[watcher] resolv.conf fixed in {c.name}")
    except Exception as e:
        logger.error(f"[watcher] resolv ERR {c.name}: {e}")


def attach(
    client: docker.DockerClient,
    cid: str,
    name: str,
    network_name: str,
    action: str = "start",
) -> None:
    """Connect a Shuffle container to the target network and inject hosts.

    Args:
        client: Docker client instance.
        cid: Container ID to attach.
        name: Container name (used for logging and Shuffle detection).
        network_name: Target network to connect to.
        action: Docker event action (``"create"`` or ``"start"``).
    """
    import time as _t

    try:
        net = client.networks.get(network_name)
        c = client.containers.get(cid)

        # Verificar si el contenedor está en network_mode compartido (container:orborus)
        # Estos contenedores no pueden conectarse a redes adicionales
        network_mode = c.attrs.get("HostConfig", {}).get("NetworkMode", "")
        if network_mode.startswith("container:"):
            logger.info(f"[watcher] skip {name} (network_mode={network_mode})")
            # Aún inyectar hosts si es un contenedor Shuffle
            if name.startswith("worker-") or is_shuffle_container(name):
                c.reload()
                if c.status == "running":
                    threading.Thread(target=fix_resolv, args=(c, network_name), daemon=True).start()
                    threading.Thread(
                        target=inject_hosts, args=(c, client, network_name), daemon=True
                    ).start()
                    threading.Thread(target=setup_docker_socket, args=(c,), daemon=True).start()
            return

        # Conectar a la red
        nets = c.attrs.get("NetworkSettings", {}).get("Networks", {})
        if network_name not in nets:
            net.connect(c)
            logger.info(f"[watcher] +net {name} -> {network_name} t={_t.time():.4f}")

        # Inyectar hosts en workers y en contenedores de apps Shuffle (TheHive, MISP, etc.)
        if name.startswith("worker-") or is_shuffle_container(name):
            c.reload()
            if c.status == "running":
                threading.Thread(target=fix_resolv, args=(c, network_name), daemon=True).start()
                threading.Thread(
                    target=inject_hosts, args=(c, client, network_name), daemon=True
                ).start()
                threading.Thread(target=setup_docker_socket, args=(c,), daemon=True).start()
            elif action == "create" and is_shuffle_container(name):
                # Pre-inyectar hosts en contenedores de apps antes de que arranquen
                threading.Thread(
                    target=inject_hosts_file, args=(c, client, network_name), daemon=True
                ).start()
    except Exception as e:
        logger.error(f"[watcher] ERR {name}: {e}")


def inject_hosts_file(
    c: docker.models.containers.Container,
    client: docker.DockerClient,
    network_name: str,
) -> None:
    """Escribe entradas de hosts en el archivo /etc/hosts del container antes.

    de que arranque, usando docker cp con un archivo temporal.
    """
    import io
    import tarfile
    import time as _t

    max_retries = 5
    for attempt in range(max_retries):
        try:
            lines = [f"{line}\n" for line in _build_hosts_lines(client, network_name)]
            if not lines:
                logger.warning(f"[watcher] no IPs found for hosts file injection in {c.name}")
                return

            # Leer /etc/hosts actual del container
            bits, _ = c.get_archive("/etc/hosts")
            buf = io.BytesIO(b"".join(bits))
            with tarfile.open(fileobj=buf) as tf:
                existing = tf.extractfile("hosts").read().decode()

            new_content = existing + "".join(lines)
            new_buf = io.BytesIO()
            with tarfile.open(fileobj=new_buf, mode="w") as tf:
                data = new_content.encode()
                info = tarfile.TarInfo(name="hosts")
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
            new_buf.seek(0)
            c.put_archive("/etc/", new_buf.read())
            logger.info(
                f"[watcher] hosts pre-injected (create) into {c.name}: "
                f"{[line.split()[1] for line in lines]}"
            )
            return
        except Exception as e:
            if attempt < max_retries - 1:
                _t.sleep(0.1)
            else:
                logger.error(
                    f"[watcher] hosts file ERR {c.name} (attempt {attempt + 1}/{max_retries}): {e}"
                )


def start_http_server(client: docker.DockerClient) -> None:
    """Start the watcher's HTTP server in a background daemon thread.

    Args:
        client: Docker client instance passed to the request handler.
    """
    server = ThreadingHTTPServer(
        ("0.0.0.0", 8080),  # nosec B104 — Docker internal
        create_handler(client),
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()


def main() -> None:
    """Entry point: start the HTTP server and listen for Docker container events."""
    client = docker.from_env()
    start_http_server(client)
    logger.info(f"[watcher] Watching -> {TARGET_NETWORK}")

    # Conectar workers ya corriendo
    for c in client.containers.list():
        if is_shuffle_container(c.name):
            threading.Thread(
                target=attach, args=(client, c.id, c.name, TARGET_NETWORK), daemon=True
            ).start()

    import time

    # Escuchar create + start (start como fallback)
    for event in client.events(
        decode=True, filters={"type": "container", "event": ["create", "start"]}
    ):
        name = event.get("Actor", {}).get("Attributes", {}).get("name", "")
        cid = event.get("Actor", {}).get("ID", "")
        action = event.get("Action", "start")
        if is_shuffle_container(name):
            t = time.time()
            logger.info(f"[watcher] event={action} name={name} t={t:.4f}")
            if action == "create":
                # Síncrono: garantiza que net.connect termina antes de que Orborus llame a start
                attach(client, cid, name, TARGET_NETWORK, action)
            else:
                # start/die: asíncrono para no bloquear el event loop
                threading.Thread(
                    target=attach, args=(client, cid, name, TARGET_NETWORK, action), daemon=True
                ).start()


if __name__ == "__main__":
    main()
