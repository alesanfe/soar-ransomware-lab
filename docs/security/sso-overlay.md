# SSO Overlay — Keycloak + oauth2-proxy

Opt-in single sign-on for the lab. **Disabled by default**: the base stack keeps
its per-app auth and direct published ports. Enable it explicitly with the
`docker-compose.sso.yml` overlay.

## Architecture

```text
browser ──► oauth2-proxy-web    :8088 ──► web-management:80
        ──► oauth2-proxy-shuffle :8089 ──► shuffle-frontend:80
                     │
                     └─► keycloak :8087 (realm `soar`, IdP)
```

- **Keycloak 26** is the identity provider. It imports
  `infra/docker/config/keycloak/soar-realm.json` (realm `soar`) on first boot.
  Admin console: `http://localhost:8087/admin` (`KEYCLOAK_ADMIN` /
  `KEYCLOAK_ADMIN_PASSWORD` from the env file).
- **oauth2-proxy** gates UIs that lack adequate native OIDC. Two gateways are
  provided as reference implementations:
  - `http://localhost:8088` → web-management UI
  - `http://localhost:8089` → Shuffle frontend
- The application behind the proxy still enforces its own app-level auth; the
  proxy is an additional edge gate, not a replacement.

## Split-host OIDC (important)

Keycloak advertises `http://localhost:8087/realms/soar` as its issuer
(`--hostname`). The proxies therefore use `SKIP_OIDC_DISCOVERY=true` with:

- `LOGIN_URL` → `localhost:8087` (browser-facing authorization endpoint)
- `REDEEM_URL` / `OIDC_JWKS_URL` → `keycloak:8080` (in-network backchannel)

Without this split the proxies fail with `issuer did not match` because the
browser and the container resolve different hosts.

## Enabling

```bash
docker compose --env-file .env.full \
  -f infra/docker/compose/docker-compose.yml \
  -f infra/docker/compose/docker-compose.core.yml \
  -f infra/docker/compose/docker-compose.api.yml \
  -f infra/docker/compose/docker-compose.misp.yml \
  -f infra/docker/compose/docker-compose.opensearch.yml \
  -f infra/docker/compose/logging/docker-compose.logging.yml \
  -f infra/docker/compose/docker-compose.sso.yml \
  up -d
```

Wait for `soar_keycloak` to become healthy (its healthcheck polls the
**management** endpoint `http://localhost:9000/health/ready`, not the app port).

## Realm contents

| Item | Value |
|---|---|
| Realm | `soar` |
| Client | `soar-proxy` (confidential, secret `OIDC_CLIENT_SECRET`) |
| Users | `admin` / `soar-admin`, `analyst` / `soar-analyst` (lab-only, `temporary=false`, `emailVerified=true`) |
| Realm roles | `platform-admin`, `soc-analyst-l2`, `soc-analyst-l1`, `responder`, `auditor`, `infra-operator` — mirror `docs/rbac-matrix.md` |

These credentials are for local development only. Production deployments must
replace users, secrets (`OIDC_CLIENT_SECRET`, `OAUTH2_PROXY_COOKIE_SECRET` —
16/24/32 bytes), the admin password, and enable `cookie_secure` + TLS.

## Verified flow (E2E evidence)

1. `GET http://localhost:8088/` → `302` → Keycloak authorization endpoint.
2. Login as `analyst` → `authorization_code` callback → session cookie.
3. Upstream `web-management` renders ("SOAR Lab Management UI").
4. Same flow on `:8089` lands on the Shuffle UI behind the gate.

## Native OIDC — remaining apps

Grafana, TheHive, Cortex and MISP support OIDC natively and can be pointed at
the `soar` realm (each needs its own client + role mapping). TheHive 5 / Cortex
3 OAuth modules are left on their built-in auth for stability in the lab; the
gateway pattern above is the supported path. Extending coverage
is additive: add another `oauth2-proxy-*` service with its own `REDIRECT_URL`
registered in the `soar-proxy` client's `redirectUris` list (or a dedicated
client).
