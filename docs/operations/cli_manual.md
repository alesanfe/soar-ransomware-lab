# Manual de la CLI `soar-lab`

## 1. Resumen

El proyecto expone el comando nativo `soar-lab` como entry point del paquete Python. Permite arrancar la API de gestión,
generar IOCs simulados y generar secretos seguros sin depender de los contenedores Docker.

## 2. Instalación del comando

Desde el directorio raíz del repositorio con Python 3.11+:

```bash
python -m pip install -e .
```

Esto registra el comando `soar-lab` (definido en `pyproject.toml` como
`soar-lab = "soar_lab.interfaces.api.cli:main"`).

> **Ruta canónica:** La implementación real del CLI está en `src/soar_lab/interfaces/api/cli.py`.
> `src/soar_lab/api/cli.py` es un re-export de compatibilidad; `pyproject.toml` apunta a la ruta canónica.
> En la documentación y en dependencias internas se debe referir siempre a `src/soar_lab/interfaces/api/cli.py`.

## 3. Comandos disponibles

### 3.1 `soar-lab version`

Muestra la versión del paquete.

```bash
soar-lab version
# 1.4.0
```

### 3.2 `soar-lab api`

Arranca el servidor de management API con el `CompositionRoot` completo.

```bash
soar-lab api --host 0.0.0.0 --port 8000
```

- Equivalente a `uvicorn soar_lab.interfaces.api.composition:create_app --host 0.0.0.0 --port 8000 --factory`.
- Requiere que las variables de entorno o `.env.full` tengan los valores necesarios.

### 3.3 `soar-lab generate-iocs`

Genera un paquete de IOCs simulados.

```bash
# Imprimir por pantalla (JSON)
soar-lab generate-iocs --count 10

# Guardar a fichero JSON
soar-lab generate-iocs --count 20 --output artifacts/results/iocs.json

# Valores por defecto:
# - count = 5
# - output = stdout si no se especifica
```

**Formatos y destino:**

- El comando imprime un objeto JSON con hashes, IPs, dominios y URLs simulados.
- Se recomienda guardar la salida bajo `artifacts/results/` o un directorio temporal para tests.
- El nombre del fichero debe seguir el patrón `iocs_<entorno>_<fecha>.json` en entornos compartidos.

**Limpieza y reproducibilidad:**

- No existe parámetro `--seed` en la CLI actualmente. Las IPs, dominios y URLs se generan con
  `random` no inicializado, por lo que las ejecuciones sucesivas producen resultados distintos.
- Los hashes simulados (benignos/maliciosos) usan un contador interno: `malicious_0`, `benign_0`, etc.
  Si se necesita reproducibilidad, invocar `SimulatedIOCGenerator` directamente con `seed` desde un
  script propio o añadir `random.seed()` antes de la llamada.
- Eliminar los IOCs generados cuando finalicen las pruebas para evitar datos obsoletos en `artifacts/results/`.

### 3.4 `soar-lab generate-secrets`

Genera secretos seguros para el laboratorio.

```bash
# Formato JSON legible
soar-lab generate-secrets --output secrets.json

# Formato .env (listo para copiar a .env.full)
# Redirigir a un fichero, NUNCA mostrar en terminal compartida
soar-lab generate-secrets --env > .env.full

# Ejemplo de salida .env
# ELASTIC_PASSWORD=<random>
# SHUFFLE_DEFAULT_PASSWORD=<random>
# SHUFFLE_DEFAULT_APIKEY=<random>
# THEHIVE_SECRET=<random>
# THEHIVE_API_KEY=<random>
# CORTEX_SECRET=<random>
# CORTEX_API_KEY=<random>
# SIEM_WEBHOOK_TOKEN=<random>
# EDR_SIM_TOKEN=<random>
# FIREWALL_SIM_TOKEN=<random>
# POSTGRES_PASSWORD=<random>
# REDIS_PASSWORD=<random>
# JWT_SECRET_KEY=<random>
# JWT_EXPIRATION_MINUTES=60
# JWT_ALGORITHM=HS256
```

#### Uso seguro de `generate-secrets --env`

1. **Destino**: redirigir siempre la salida a un fichero, por ejemplo `.env.full`:
   ```bash
   soar-lab generate-secrets --env > .env.full
   ```
2. **Permisos**: restringir acceso al fichero generado:
   ```bash
   chmod 600 .env.full
   ```
3. **No exponer en terminal**: no ejecutar `soar-lab generate-secrets --env` en logs de CI, capturas de pantalla o sesiones compartidas sin redirección.
4. **Validación posterior**:
   ```bash
   grep -E 'JWT_SECRET_KEY|ELASTIC_PASSWORD|SHUFFLE_DEFAULT_APIKEY' .env.full
   ```
   El fichero debe contener valores aleatorios de 32-64 caracteres y no contener literales como `change-me` o `CHANGE_ME`.
5. **No versionar**: asegurar que `.env.full`, `secrets.json` y cualquier otro artefacto con credenciales estén en `.gitignore`.

> **Atención:** El modo `--env` genera `JWT_SECRET_KEY`, `JWT_EXPIRATION_MINUTES` y `JWT_ALGORITHM`.
> La variable `API_AUTH_SECRET` es un fallback legacy; preferir `JWT_SECRET_KEY`.
> Nunca se deben commitear esos valores.

## 4. Uso típico

1. Generar credenciales iniciales:

   ```bash
   soar-lab generate-secrets --env > .env.full
   ```

2. Ajustar el resto de variables de entorno (puertos, hosts, nombres de proyecto).

3. Levantar el stack:

   ```bash
   make up
   ```

4. (Opcional) Arrancar la API manualmente para depuración:

   ```bash
   soar-lab api --host 0.0.0.0 --port 8000
   ```

### 4.1 Simulador de alertas (`simulate_alerts.py`)

El simulador genera alertas de ransomware de prueba y las envía al webhook de Shuffle. No requiere una VM Windows real.

```bash
# Desde dentro del contenedor / red Docker (valor por defecto del script)
PYTHONPATH=src python -m soar_lab.simulator.simulate_alerts --count 5 --delay 2

# Desde el host apuntando al webhook expuesto
PYTHONPATH=src python -m soar_lab.simulator.simulate_alerts \
  --count 10 \
  --delay 1 \
  --webhook http://localhost:15001/api/v1/hooks/<workflow_id>
```

- La URL se resuelve automáticamente desde `SIEM_WEBHOOK_URL`, `SIEM_WEBHOOK_TOKEN` o `webhook_info.json`.
- Internamente usa `http://soar_shuffle_backend:5001/api/v1/hooks/<workflow_id>`.
- Desde el host expuesto se usa el puerto `15001`, **no** `8081` (ese es la UI de Shuffle).

**Payload generado por el simulador (ejemplo):**

```json
{
  "alert_id": "SIM-WIN-0001",
  "timestamp": "2026-07-18T00:00:00Z",
  "severity": "critical",
  "classification": "malicious",
  "src_ip": "185.220.101.42",
  "dst_ip": "192.168.56.10",
  "description": "Ransomware WannaCry detectado",
  "file_hash": "d41d8cd98f00b204e9800998ecf8427e",
  "process_name": "encryptor.exe",
  "host": "victima-windows-sim",
  "source": "windows_defender_sim",
  "MITRE": "T1486"
}
```

> El workflow de Shuffle (`init_shuffle_webhook.py`) normaliza estos campos al modelo `RansomwareAlert` esperado por la API.

## 5. Referencias

- [Especificación de APIs](../integrations/api_contracts.md)
- [Composition Root](../architecture/composition_root.md)
- [src/soar_lab/interfaces/api/cli.py](/src/soar_lab/interfaces/api/cli.py)
