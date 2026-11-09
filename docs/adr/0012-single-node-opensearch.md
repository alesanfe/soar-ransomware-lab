# ADR-0012: OpenSearch/Elasticsearch single-node — limitación estructural aceptada

**Estado**: Aceptado · **Evidencia**: `docker-compose.opensearch.yml`
(`discovery.type=single-node`), health `yellow` documentado en
`AGENTS.md`/`docs/04-operations.md`.

## Contexto

OpenSearch (y el Elasticsearch legado que coexiste) corre como nodo único
en el stack del lab. Un cluster real exige 3 nodos master-eligible para
quórum, más nodos data para réplicas — ~6 contenedores adicionales y
varios GB de RAM sobre un Docker Desktop doméstico que ya soporta ~15
servicios.

El estado `yellow` (réplicas sin asignar) es permanente e **informativo,
no un defecto**.

## Decisión

**Single-node es la topología canónica del lab**, con las cotas:

1. **No se simula HA de storage**: la resiliencia del lab vive en la capa
   de aplicación (DLQ, idempotencia, GC, backups) — no pretendemos
   durabilidad multi-nodo que no existe.
2. **Persistencia real**: volúmenes nombrados + `make backup` cubren la
   recuperación ante pérdida de contenedor — RPO del último backup.
3. **Criterio de reversa**: escalar a 2+ nodos si el lab migra a un
   host con ≥32 GB RAM o si se estudia específicamente clustering —
   el compose ya parametriza `discovery.type`.

## Consecuencias

- Pérdida del contenedor/volumen = pérdida de índices desde el último
  backup (aceptado: corpus regenerable vía simulador).
- `yellow` permanece en healthchecks — los runbooks lo marcan como
  normalidad, no alerta.
- Los tests de resiliencia no evalúan failover de storage — alcance
  explícito, no omisión.

## Alternativas descartadas

- **3-node cluster en compose**: ~6 GB RAM extra + arranque más lento;
  el recurso es el cuello de botella real en Docker Desktop.
- **OpenSearch serverless/externo**: rompe el principio
  self-contained del lab y añade credenciales cloud al threat model.
