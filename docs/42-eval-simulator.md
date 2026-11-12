# 42 — Evaluación: simulador de alertas

> **Área**: `src/soar_lab/simulator/` (`simulate_alerts.py`, `dataset_replay.py`), `scripts/perf/locustfile.py`, targets `make simulate-*`.
> **Marcos**: ISO 25010 (corrección funcional, fiabilidad), contrato `AlertValidator`, SRE (datos de prueba representativos).
> **Resultado**: ~9,5/10 (antes ~8,2/10). 3 defectos corregidos, cobertura de tests de 0 → 5 unit + 7 gates, verificación viva end-to-end.

## 1. Resumen

El simulador es la fuente de datos del laboratorio: 21 familias de ransomware con IoCs reales de advisories CISA/Unit42/TC-33, replay de datasets con inyección de sender, y un perfil locust para la ruta de admisión. La madurez de contenido es alta (IoCs reales, técnicas MITRE mapeadas, campo `domain` garantizado para analyzers), pero tres defectos degradaban la fidelidad del contrato.

## 2. Hallazgos corregidos

| ID | Severidad | Defecto | Corrección |
|----|-----------|---------|------------|
| SIM-EVAL-001 | High | **5 familias con hash de longitud inválida** — Locky (63), Ryuk (63), REvil (65), Royal (63), Play (63) hex chars; el contrato `HashValidator` exige 32/40/64 → ~24% de las alertas generadas no cumplían el contrato que la propia suite verifica | Normalizadas a 64 hex; gate `test_all_embedded_hashes_satisfy_domain_contract` bloquea regresión estáticamente |
| SIM-EVAL-002 | Medium | **`simulator/` sin `__init__.py`** — único paquete de `src/soar_lab/` sin él; funcionaba por namespace-package accidental pero queda fuera del wheel de setuptools | `__init__.py` añadido; gate de paquete |
| SIM-EVAL-003 | Medium | **Retry solo en HTTP 500** — `send_alert` no reintentaba en 502/503/504 (transitorios típicos de Shuffle saturado) | `resp.status_code >= 500`; test unitario verifica 503→200 en 3 intentos |
| SIM-EVAL-004 | Low | **CLI silencioso** — `main()` sin `logging.basicConfig`: `make simulate` producía cero output visible | `basicConfig(INFO)` añadido; verificado: banner, progreso y resumen se imprimen |

## 3. Verificación

- **Unit**: 5/5 — las 21 familias producen alertas que pasan `AlertValidator.validate_structure` (selector round-robin determinista), retry 5xx, no-retry 4xx, precedencia de env.
- **Live**: `python -m soar_lab.simulator.simulate_alerts --count 1` → HTTP 200 del webhook Shuffle → `soar-alerts` count 973 → 1016 (pipeline ingiriendo).
- **Arch gates**: 7/7 en `tests/architecture/test_simulator.py`.

## 4. Positivos confirmados

- Corpus de IoCs real: hashes SHA256 auténticos de CISA #StopRansomware (LockBit 3.0, ALPHV, Akira, RansomHub, Rhysida, Brain Cipher) + TC-33 (GMinst4ll, Pulsar RAT) — verificados 64-hex.
- `domain` siempre poblado (contrato del analyzer GoogleDNS); C2 IPs/dominios/URLs reales de TC-33 con probabilidades calibradas.
- `dataset_replay.py` maduro: sender inyectable, `limit`/`delay`/`on_result`/`sleep`/`tag`, guard de división-por-cero, errores con `path:line`.
- `locustfile.py` correcto: hash 64-hex válido, 429/503 tratados como rechazo controlado correcto, token por env.
- Resolución de webhook con precedencia env > webhook_info.json > token, sin URL hardcodeada.

## 5. Residuales aceptados

- Familias clásicas (Locky/Ryuk/etc.) llevan hashes sintéticos válidos (los advisories no publican un SHA256 canónico por familia); las con advisory sí llevan hash real. Documentado en el propio dict.
- `random` sin seed (deliberado: la variabilidad es el propósito; `dataset_replay` es la vía determinista para KPI runs).
- Benign path vive en `infrastructure.messaging.send_alert` (`make simulate-benign`) — módulo distinto, ya evaluado en messaging.

## 6. Gates

`tests/architecture/test_simulator.py` (7): paquete, contrato de hashes, `domain` obligatorio, retry 5xx, sin webhook hardcodeado, inyección replay, guard de rate. `tests/unit/simulator/test_simulate_alerts.py` (5): validación estructural por familia, campos de contrato, retry/no-retry, precedencia de webhook.
