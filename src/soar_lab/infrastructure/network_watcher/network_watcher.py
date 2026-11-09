"""network_watcher.py - Conecta workers/app-containers de Shuffle a TARGET_NETWORK.

antes de que arranquen, para que el DNS de la red SOAR esté disponible.
"""

import io
import logging
import os
import random
import tarfile
import threading
import time
from contextlib import suppress
from http.server import ThreadingHTTPServer
from pathlib import Path

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
    return name.startswith(("worker-", "HTTP_")) or "_act_" in name


# ---------------------------------------------------------------------------
# P0.1: Zero-Trust container verification (replaces name-only trust)
#
# Name-prefix trust (``worker-*``) is trivially spoofable: any user able to
# run ``docker run --name worker-evil`` on the host gets hosts injected and
# a daemon socket forwarded. The watcher now verifies ownership with
# multiple factors before mutating a container:
#
#   1. ``com.shuffle.managed=true`` label (set by Orborus/compose) — the
#      STRONGEST factor; required in ``label``/``strict`` trust modes.
#   2. Image reference checked against ``WATCHER_MANAGED_IMAGES`` allowlist
#      when configured.
#   3. Name pattern — kept only as a *fast pre-filter* and as the lab
#      fallback in ``hybrid`` mode, never as sole proof of ownership.
#
# Trust modes (env ``WATCHER_TRUST_MODE``):
#   label  — only label-managed containers are touched (strictest)
#   hybrid — label OR (name pattern AND image allowlist when configured)
#   name   — legacy behaviour; logs a SECURITY deprecation warning
# ---------------------------------------------------------------------------

MANAGED_LABEL = "com.shuffle.managed"
TRUST_MODE = os.environ.get("WATCHER_TRUST_MODE", "hybrid").lower()
MANAGED_IMAGES = {
    img.strip() for img in os.environ.get("WATCHER_MANAGED_IMAGES", "").split(",") if img.strip()
}
# P0.2: the daemon socket forward into workers is OFF by default. It is a
# privilege-escalation primitive (worker -> docker.sock -> daemon root)
# and only exists for the Cortex DinD analyzer flow. Re-enable explicitly
# with WATCHER_DOCKER_SOCKET_INJECT=true when that flow is in use.
SOCKET_INJECT_ENABLED = os.environ.get("WATCHER_DOCKER_SOCKET_INJECT", "false").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
# Hosts/resolv injection still required for Shuffle DNS in the lab, but
# it is now an explicit, documented capability you can disable.
HOST_INJECT_ENABLED = os.environ.get("WATCHER_HOST_INJECT", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

_REJECTED: dict[str, int] = {"count": 0}


def _is_truthy_label(value: object) -> bool:
    return str(value).lower() in ("1", "true", "yes", "on")


def verify_managed_container(
    name: str,
    *,
    labels: dict | None = None,
    image: str | None = None,
) -> tuple[bool, str]:
    """Zero-Trust verdict for a candidate container (P0.1).

    Args:
        name: Container name from the event stream.
        labels: Container labels (``Config.Labels`` / inspect data).
        image: Container image reference (``Config.Image``).

    Returns:
        ``(allowed, reason)`` — ``reason`` is logged for audit either way.
    """
    labels = labels or {}
    labelled = _is_truthy_label(labels.get(MANAGED_LABEL))

    if not is_shuffle_container(name) and not labelled:
        return False, "not-managed: fails name pre-filter and has no managed label"

    if labelled:
        return _labelled_verdict(image)
    return _unlabelled_verdict(image)


def _labelled_verdict(image: str | None) -> tuple[bool, str]:
    if (
        MANAGED_IMAGES
        and image
        and not any(image.startswith(allowed) for allowed in MANAGED_IMAGES)
    ):
        return False, f"labelled but image {image!r} outside allowlist"
    return True, "managed-label"


def _unlabelled_verdict(image: str | None) -> tuple[bool, str]:
    """No managed label: fall back per trust mode."""
    if TRUST_MODE == "label":
        return False, f"missing {MANAGED_LABEL}=true label (TRUST_MODE=label)"

    if TRUST_MODE == "name":
        logger.warning(
            "[watcher][SECURITY] TRUST_MODE=name — name-only trust is spoofable; "
            "migrate to managed labels"
        )
        return True, "legacy-name-trust (INSECURE)"

    # hybrid: name pattern matched; additionally require image allowlist
    # match when one is configured.
    if MANAGED_IMAGES:
        if not image:
            return False, "hybrid: no image data to verify against allowlist"
        if not any(image.startswith(allowed) for allowed in MANAGED_IMAGES):
            return False, f"hybrid: image {image!r} outside allowlist"
    return True, "name-pattern" + ("+image-allowlist" if MANAGED_IMAGES else "")


def _reject(name: str, reason: str) -> None:
    _REJECTED["count"] += 1
    logger.warning("[watcher][SECURITY] REJECTED container %s: %s", name, reason)


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
    r"""Build a list of ``"ip\\tsvc"`` entries for all injectable services.

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
    except Exception:
        logger.exception(f"[watcher] hosts inject ERR {c.name}")


DOCKER_PROXY_HOST = os.environ.get("DOCKER_PROXY_HOST", "host.docker.internal")
DOCKER_PROXY_PORT = os.environ.get("DOCKER_PROXY_PORT", "2375")


def setup_docker_socket(c: docker.models.containers.Container) -> None:
    """Crea /var/run/docker.sock en el worker como Unix socket que forwarda al.

    proxy TCP Docker.
    """
    try:
        # Copiar socat desde la imagen del watcher al worker (usar binario real, no symlink)
        socat_path = "/usr/bin/socat1"
        if not Path(socat_path).exists():
            socat_path = "/usr/bin/socat"
        if not Path(socat_path).is_file():
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
    except Exception:
        logger.exception(f"[watcher] socket ERR {c.name}")


def fix_resolv(c: docker.models.containers.Container, network_name: str) -> None:
    """Reescribe /etc/resolv.conf para que el DNS embebido de Docker resuelva.

    hostnames de la red SOAR.

    Necesita ejecutarse después de 'start'.
    """
    try:
        new_conf = "nameserver 127.0.0.11\noptions ndots:0\n"
        c.exec_run(["sh", "-c", f'echo "{new_conf}" > /etc/resolv.conf'], user="root")
        logger.info(f"[watcher] resolv.conf fixed in {c.name}")
    except Exception:
        logger.exception(f"[watcher] resolv ERR {c.name}")


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
    try:
        net = client.networks.get(network_name)
        c = client.containers.get(cid)

        # P0.1: Zero-Trust verification BEFORE any mutation (connect/exec)
        if not _verify_trust(c, name):
            return

        # Verificar si el contenedor está en network_mode compartido (container:orborus)
        # Estos contenedores no pueden conectarse a redes adicionales
        network_mode = c.attrs.get("HostConfig", {}).get("NetworkMode", "")
        if network_mode.startswith("container:"):
            logger.info(f"[watcher] skip {name} (network_mode={network_mode})")
            # Aún inyectar hosts si es un contenedor Shuffle
            _inject_running(c, client, name, network_name)
            return

        # Conectar a la red
        nets = c.attrs.get("NetworkSettings", {}).get("Networks", {})
        if network_name not in nets:
            net.connect(c)
            logger.info(f"[watcher] +net {name} -> {network_name} t={time.time():.4f}")

        # Inyectar hosts en workers y en contenedores de apps Shuffle (TheHive, MISP, etc.)
        _inject_running(c, client, name, network_name)
        c.reload()
        if (
            c.status != "running"
            and action == "create"
            and is_shuffle_container(name)
            and HOST_INJECT_ENABLED
        ):
            # Pre-inyectar hosts en contenedores de apps antes de que arranquen
            threading.Thread(
                target=inject_hosts_file, args=(c, client, network_name), daemon=True
            ).start()
    except Exception:
        logger.exception(f"[watcher] ERR {name}")


def _verify_trust(c: docker.models.containers.Container, name: str) -> bool:
    """Zero-trust verdict for a container; rejects and returns False if untrusted."""
    cfg = c.attrs.get("Config", {}) or {}
    eff_name = c.name if isinstance(c.name, str) and c.name else name
    labels = cfg.get("Labels")
    labels = labels if isinstance(labels, dict) else {}
    image = cfg.get("Image")
    image = image if isinstance(image, str) else ""
    allowed, reason = verify_managed_container(eff_name, labels=labels, image=image)
    if not allowed:
        _reject(eff_name, reason)
        return False
    logger.debug("[watcher] trust verdict for %s: %s", eff_name, reason)
    return True


def _inject_running(
    c: docker.models.containers.Container,
    client: docker.DockerClient,
    name: str,
    network_name: str,
) -> None:
    """Inject hosts/resolv/docker-socket into a running Shuffle container."""
    if not (name.startswith("worker-") or is_shuffle_container(name)):
        return
    c.reload()
    if c.status != "running":
        return
    if HOST_INJECT_ENABLED:
        threading.Thread(target=fix_resolv, args=(c, network_name), daemon=True).start()
        threading.Thread(target=inject_hosts, args=(c, client, network_name), daemon=True).start()
    if SOCKET_INJECT_ENABLED:
        threading.Thread(target=setup_docker_socket, args=(c,), daemon=True).start()


def inject_hosts_file(
    c: docker.models.containers.Container,
    client: docker.DockerClient,
    network_name: str,
) -> None:
    """Escribe entradas de hosts en el archivo /etc/hosts del container antes.

    de que arranque, usando docker cp con un archivo temporal.
    """
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
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(0.1)
            else:
                logger.exception(
                    f"[watcher] hosts file ERR {c.name} (attempt {attempt + 1}/{max_retries})"
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

    def _dispatch_events(cli: docker.DockerClient) -> None:
        # Escuchar create + start (start como fallback)
        for event in cli.events(
            decode=True, filters={"type": "container", "event": ["create", "start"]}
        ):
            name = event.get("Actor", {}).get("Attributes", {}).get("name", "")
            cid = event.get("Actor", {}).get("ID", "")
            action = event.get("Action", "start")
            if is_shuffle_container(name):
                t = time.time()
                logger.info(f"[watcher] event={action} name={name} t={t:.4f}")
                if action == "create":
                    # Síncrono: garantiza que net.connect termina antes de
                    # que Orborus llame a start
                    attach(cli, cid, name, TARGET_NETWORK, action)
                else:
                    # start/die: asíncrono para no bloquear el event loop
                    threading.Thread(
                        target=attach,
                        args=(cli, cid, name, TARGET_NETWORK, action),
                        daemon=True,
                    ).start()

    _watch_forever(_dispatch_events)


def _watch_forever(dispatch) -> None:
    """P0.1 daemon-resilience: reconnect with backoff+jitter on daemon loss.

    Before, a single ``DockerException`` (daemon restart, socket hiccup)
    killed the watcher silently and workers stopped being wired. Now the
    event loop is supervised: exponential backoff 1s→2s→…→60s cap with
    full jitter, and the client is recreated each cycle.
    """
    base, cap, attempt = 1.0, 60.0, 0
    rng = random.Random()
    while True:
        cli = None
        try:
            cli = docker.from_env()
            dispatch(cli)
            attempt = 0  # clean exit of the event stream -> reset backoff
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            attempt += 1
            delay = rng.uniform(0, min(cap, base * (2 ** (attempt - 1))))
            logger.warning(
                "[watcher] event stream lost (attempt %d): %s — reconnecting in %.1fs",
                attempt,
                exc,
                delay,
            )
            with suppress(Exception):
                if cli is not None:
                    cli.close()
            time.sleep(delay)


if __name__ == "__main__":
    main()
