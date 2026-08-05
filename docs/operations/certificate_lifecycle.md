# Ciclo de vida de certificados SSL/TLS

El laboratorio utiliza certificados autofirmados para Nginx (`soar.local`), servicios internos y componentes Wazuh. Esta guía describe su generación, confianza y renovación.

## Certificados gestionados

| Certificado | Uso | Ubicación por defecto | Generador |
|-------------|-----|----------------------|-----------|
| `soar.local.crt` / `soar.local.key` | Terminación TLS en Nginx para `https://soar.local` | `infra/docker/config/nginx/ssl/` | `make certs` / `src/soar_lab/scripts/setup/gen_certs.sh` |
| `misp.crt` / `misp.key` (si aplica) | Servicio MISP con TLS interno | `infra/docker/config/nginx/ssl/` | `gen_certs.sh` con `--host misp` |
| CA local (`ca.crt` / `ca.key`) | Firma de certificados de servicio | `infra/docker/config/nginx/ssl/` | `gen_certs.sh` |
| Certificados Wazuh Indexer | TLS entre nodos Wazuh (manager, indexer, dashboard) | `infra/docker/compose/wazuh/config/wazuh_indexer_ssl_certs/` | `docker compose -f infra/docker/compose/wazuh/generate-indexer-certs.yml run --rm generator` |

### Permisos y montajes Docker

- Las claves privadas (`*.key`) deben tener permisos **600** (`-rw-------`); los certificados (`*.crt`) **644** (`-rw-r--r--`).
- Evitar exponer claves privadas en bind mounts accesibles desde contenedores que no las necesiten; montar únicamente el certificado/CA cuando sea posible.
- En `docker-compose*.yml` no mapear el directorio `ssl/` completo como `ro` en servicios que solo necesiten la CA o el certificado: mapear archivos individuales (`soar.local.crt`, `ca.crt`) para minimizar superficie.
- Los certificados generados y claves privadas están incluidos en `.gitignore`; no deben versionarse.

## Generación

### Nginx y servicios del laboratorio

Ejecutar desde la raíz del repositorio:

```bash
# Linux / macOS
make certs

# Windows (PowerShell)
make -f Makefile.win certs

# Manual
src/soar_lab/scripts/setup/gen_certs.sh
```

`gen_certs.sh` realiza los siguientes pasos:

1. Crea el directorio destino (`infra/docker/config/nginx/ssl/` por defecto).
2. Genera una CA local RSA 4096 bits y certificado autofirmado válido 10 años.
3. Genera claves RSA 2048 bits y certificados firmados por la CA para cada hostname solicitado (`soar.local` por defecto).
4. Verifica la cadena con `openssl verify`.

### Wazuh Indexer

En un despliegue nuevo o tras regenerar certificados Wazuh:

```bash
docker compose -f infra/docker/compose/wazuh/generate-indexer-certs.yml run --rm generator
```

El generador usa la imagen `wazuh/wazuh-certs-generator:0.0.2` y produce los certificados necesarios para `wazuh.manager`, `wazuh.indexer` y `wazuh.dashboard`.

## Confianza en el navegador / sistema operativo

Para evitar advertencias de certificado al acceder a `https://soar.local`:

- **Windows**: importar `infra/docker/config/nginx/ssl/ca.crt` (o `soar.local.crt`) en *Certificados* → *Autoridades de certificación raíz de confianza* (`certmgr.msc`).
- **Linux**: copiar `ca.crt` a `/usr/local/share/ca-certificates/` y ejecutar `sudo update-ca-certificates` (nombre Debian/Ubuntu).
- **macOS**: `sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ca.crt`.
- **Navegadores**: importar la CA local en el almacén de certificados raíz del navegador.

> **Nota**: Los certificados son autofirmados y solo son válidos para el entorno de laboratorio. No deben usarse en producción sin una CA corporativa o pública.

## Renovación

Los certificados de servicio tienen una validez de **365 días**; la CA local es válida **10 años**.

### Verificar fechas de expiración

```bash
openssl x509 -in infra/docker/config/nginx/ssl/soar.local.crt -noout -dates
openssl x509 -in infra/docker/config/nginx/ssl/ca.crt -noout -dates
```

### Renovar certificados de servicio

Antes de la renovación se recomienda hacer un backup del directorio `ssl/`:

```bash
cp -r infra/docker/config/nginx/ssl infra/docker/config/nginx/ssl.bak.$(date +%Y%m%d)
```

Luego regenerar:

```bash
make certs
# o manualmente
src/soar_lab/scripts/setup/gen_certs.sh -o infra/docker/config/nginx/ssl
```

Finalmente, reiniciar Nginx para cargar los nuevos certificados:

```bash
docker compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.api.yml restart nginx
```

### Renovar certificados Wazuh

1. Detener los servicios Wazuh:

   ```bash
   docker compose -f infra/docker/compose/docker-compose.wazuh.yml down
   ```

2. Regenerar certificados:

   ```bash
   docker compose -f infra/docker/compose/wazuh/generate-indexer-certs.yml run --rm generator
   ```

3. Levantar los servicios:

   ```bash
   docker compose -f infra/docker/compose/docker-compose.wazuh.yml up -d
   ```

## Automatización en CI/CD

Para evitar certificados expirados en despliegues automatizados, se recomienda:

- Incluir un job de CI que verifique las fechas de expiración con `openssl x509 -noout -enddate`.
- Rechazar builds cuyos certificados expiren en menos de 30 días.
- No versionar certificados generados (`infra/docker/config/nginx/ssl/` está en `.gitignore`).

## Referencias

- `src/soar_lab/scripts/setup/gen_certs.sh`
- `infra/docker/compose/wazuh/generate-indexer-certs.yml`
- `docs/getting_started/installation_guide.md`
- `docs/operations/configuration_manual.md`
