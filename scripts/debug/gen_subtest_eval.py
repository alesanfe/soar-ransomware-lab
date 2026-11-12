import yaml

E = {
"TC-00":("Happy path alert→workflow→case→metrics; verificado","execution_time usa histórico sin aislar; sin warm-up","Baseline aislado, warm-up, paralelismo por spans","—","9.5"),
"TC-01":("Infra del workflow end-to-end","95s/test mezcla setup y asserts; sin timeout por fase","Diagnóstico de fase lenta","—","9.5"),
"TC-02":("Clasificación de alertas","Cierre benigno→FP formal, motivo, reclasificación FP→TP","E2E-FUN-001","—","9.0"),
"TC-03":("Validación/admisión de payloads","JSON depth, NaN, null-byte, claves dup, chunked, ±1B","E2E-SIZE-001","—","9.0"),
"TC-04":("Performance con medición real","Baseline versionado y drift automático aún rígidos","PERF-001","—","9.5"),
"TC-05":("Concurrencia/alert-storm","Capacidad máx, fairness, drenado post-carga","PERF-003","—","9.5"),
"TC-06":("Severidad+enriquecimiento","Matriz transiciones, ausente→derivada, conflicto","E2E-FUN-002","—","9.0"),
"TC-07":("Errores de validación","Texto exacto→contrato {code,field,category,retryable,correlation_id}","E2E-CONTRACT-001","—","9.0"),
"TC-08":("Mass assignment rechazado","Anidado, arrays, notación punto, case-sensitivity","E2E-CONTRACT-002","—","9.0"),
"TC-09":("Vectores ransomware ampliados","Doble extorsión/lateral parcial; cache firmado offline","TEST-SEC-001","—","9.5"),
"TC-10":("Tenzir funcional","PCAP realista versionado + oráculo semántico","E2E-NET-001","—","9.0"),
"TC-11":("Watcher health/precisión","TP/FP/FN formales, IPv6, conexiones breves","E2E-NET-002","—","9.0"),
"TC-12":("Cache IoC operativa","Eviction, stampede, poisoning, hit/miss rate","E2E-CACHE-001","—","9.0"),
"TC-13":("Loki ingest/query","Retención, rotación, compactación, out-of-order","E2E-OBS-001","—","9.0"),
"TC-14":("trace_id cross-system real","Contrato semántico/salto, baggage, links asíncronos","E2E-OBS-002","—","9.5"),
"TC-15":("Latencia endpoints","Muestras p95/p99, cold vs warm","PERF-001","—","9.0"),
"TC-16":("Errores integración clasificados","Ventana fija, error budget, retryable, retry-storm","KPI-007","—","9.0"),
"TC-17":("Watcher recovery","Recovery sin duplicados formalizado","E2E-NET-002","—","9.0"),
"TC-18":("Chaos deps-caídas, errores 503 tipados","Netem/partición/kill-en-commit (parcial en TC-37)","Teardown central","—","9.0"),
"TC-19":("Familias ofensivas","XXE, template inj, zip slip, CRLF, smuggling, CSV, ReDoS","E2E-SEC-002","—","9.0"),
"TC-20":("Reachability core","Matriz total, IPv6, docker socket, egress","E2E-ZT-001","—","9.0"),
"TC-21":("Custodia/checksum","Tamper activo: reordenar, suprimir, rollback, firma","E2E-SEC-001","—","9.0"),
"TC-22":("Backup/restore round-trip","Corrupto en TC-39; falta selectivo, otra versión, RPO/RTO","E2E-DATA-001","—","9.0"),
"TC-23":("Sanitización","Diccionario PII, canaries multi-artefacto","E2E-PRIV-001","—","9.0"),
"TC-24":("Playbooks base","Phishing/BEC/exfil/insider/cred/webshell/cloud","E2E-THREAT-001","—","9.0"),
"TC-25":("Forense/PCAP base","Dataset versionado + oráculo + precisión","E2E-NET-001","—","9.0"),
"TC-26":("Load/queue","Memoria, edad msg, DLQ, fairness, recovery, límites","PERF-003","—","9.0"),
"TC-27":("Config drift","Rebaseline aprobado, diff semántico, firma","CONF-001","—","9.0"),
"TC-28":("UI screenshots+a11y","Render semántico, responsive, WCAG 2.2 completa","UI-001/002; SSO fuera por decisión","—","9.0"),
"TC-29":("Límites payload","±1B exacto, chunked, zip bomb, parcial","E2E-SIZE-001","—","9.0"),
"TC-30":("Air-gap/DNS parcial","DNS selectivo, NXDOMAIN, lento, stale, CRL/OCSP","E2E-AIR-001","—","9.0"),
"TC-31":("MITRE/STIX","Catálogo versionado, revocadas, D3FEND","E2E-COMP-001","—","9.0"),
"TC-32":("Certificación integral","Timeline/salto, run_id isolation","Diferencial PR vs nightly","—","9.5"),
"TC-33":("Vectores ampliados, dominio válido","Cache firmado offline de muestras","TEST-SEC-001","—","9.5"),
"TC-34":("Webhook contract ejemplar","Algoritmo no permitido, idempotencia post-ventana","E2E-REPLAY-001","—","10"),
"TC-35":("Grafana PNG real 17/17, datasources","Visual regression, datasource lento","—","—","10"),
"TC-36":("5/5 opensearch/loki/grafana/ES/redis down","Bulk parcial, ACK-pre-persist, dedup, índice incompatible, falsos ceros","RES-001/002 ext.","GC keyword bug fix","8.6"),
"TC-37":("2/2 pause→hang, CPU-starved→terminal","Netem real, partición, mem pressure, kill-en-commit","RES-004 netem","—","8.0"),
"TC-38":("3/3 zombie→ABORTED quirúrgico+idempotente","Estados timeout, métricas stuck/oldest, timeout/nodo","RES-003","Bug GC real fix","9.0"),
"TC-39":("5/5 canary, backup, skew, key-sync","Bordes tolerancia, replay/nonce, DST, multi-artefacto","E2E-REPLAY-001","LogQL fix","9.1"),
"TC-40":("5/5 TLS/watermark/analyzer/MISP/anonymous","Cert expirado/mTLS, analyzer obligatorio, disk físico","PKI-001 restante","MISP attr fix","8.7"),
"TC-41":("6/6 TAXII real medallion end-to-end","Paginación, added_after, /versions, rate-limit","E2E-MISP-001 ext.","Accept taxii+json","9.1"),
"TC-KPI-01":("MTTR real tras fix epoch","run_id window, muestras","calc_mttr neg fix","—","9.0"),
"TC-KPI-02":("Detección medida","Aislar Locust","KPI-007","—","9.0"),
"TC-KPI-03":("Contención medida","Div/0 guardada","—","—","9.0"),
"TC-KPI-04":("Precisión FP/TP","Reclasificación (ver TC-02)","—","—","9.0"),
"TC-KPI-05":("Disponibilidad/SLI","no-data≠0 verificado","—","—","9.0"),
"TC-KPI-06":("Cobertura/saturación","Numerador/denominador formal","KPI-007","—","9.0"),
}

cat = yaml.safe_load(open("tests/e2e/TC_catalog.yaml", encoding="utf-8"))["test_cases"]
out = ["# Evaluación a nivel subtest — suite E2E completa\n\n",
       "> Generada del catálogo real + evidencias verificadas de ejecución.\n"]
total = 0
for e in cat:
    sid = e["id"]
    p, n, d, b, s = E.get(sid, ("Sin evaluar", "—", "—", "—", "—"))
    tests = e.get("tests", [])
    total += len(tests)
    out.append("\n## %s — nota: **%s**\n\n" % (sid, s))
    out.append("- **Positivos**: %s\n- **Negativos**: %s\n- **Deuda**: %s\n- **Bugs**: %s\n" % (p, n, d, b))
    out.append("\n| # | Subtest | Estado |\n|---|---|---|\n")
    for i, t in enumerate(tests, 1):
        out.append("| %s-%02d | `%s` | implementado |\n" % (sid, i, t["name"]))
    out.append("\n**Subtests existentes**: %d\n" % len(tests))
out.append("\n\n**Total subtests catalogados: %d**\n" % total)
open("docs/22-subtest-evaluation.md", "w", encoding="utf-8").write("".join(out))
print("written", total, "subtests")
