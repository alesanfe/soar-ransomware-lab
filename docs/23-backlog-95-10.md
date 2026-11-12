# Backlog exhaustivo → 9.5/10 — todos los subtests faltantes

## Estado de ejecución (sesión actual)

| Bloque | Estado | Evidencia |
|---|---|---|
| **NET-001** netem real | ✅ CERRADO | 8/8 subtests verdes en TC-37 (`nicolaka/netshoot` + `--cap-add NET_ADMIN` sidecar en el netns real): delay 250ms, loss 10%, jitter, duplicación 25%, reorder 50%, partición 100% loss, partición unilateral iptables-OUTPUT-DROP, higiene `test_no_orphan_qdisc`. JUnit `junit-tc-37-netem*.xml`. |
| **TMO-001** timeout states | ✅ CERRADO | GC reescrito como máquina de estados real `EXECUTING→TIMED_OUT→CANCELLING→ABORTED` con transiciones condicionales scripted (resultado tardío = noop, nunca se pisa), `aborted_at/forced` audit, forced-abort tras `MAX_CONFIRM_ATTEMPTS`, métricas `soar_workflow_stuck_total`/`soar_workflow_oldest_executing_seconds`/`soar_workflow_timeout_transitions_total` en `/metrics`, regla Grafana `soar_workflow_executing_stuck` provisionada (13 rules). 23/23 unit + 7/7 e2e. Residual: timeout por nodo individual (workflow-level, requiere cambio en Shuffle). |
| CRED-001 rotación credenciales | ✅ CERRADO | MISP authkeys reales: coexistencia old+new, revocación → 401/403, propagación env-file autenticada. 3/3 e2e. |
| DS-001 disk-full físico | ✅ CERRADO | tmpfs 48MB en api → ENOSPC real del kernel, escritura acotada, recovery inmediata, artefacto parcial rechazado por integrity gate. 3/3 e2e. |
| **PKI completo** (TC-40-12..16) | ✅ CERRADO | mini-CA openssl real en test: expirado, not-yet-valid, cadena incompleta, **revocación CRL real**, mTLS trust contract. 5/5. |
| **TAXII avanzado** (TC-41-07..09) | ✅ CERRADO | paginación limit+next, `added_after` incremental, composición con match[id]. 3/3 contra medallion real. |
| **Timeout por nodo** (TC-38-08) | ✅ CERRADO | `node_timings` reales en soar-metrics: todo nodo < bound de workflow. 1/1. |
| **TC-07 error contract** | ✅ CERRADO | 4/4: 422 {type,loc,msg} campo exacto, 401/404 JSON+correlación, errores siempre JSON. **Bug prod arreglado**: `x-request-id` ausente en 401 (TraceId movido a outermost en `main.py`). |
| **TC-03/29 boundary ±1B** | ✅ CERRADO | 3/3: 2MiB−1 cruza, 2MiB+1 → 413 en edge nginx real, depth 500 acotado. |
| **TC-08 mass-assignment** | ✅ CERRADO | 3/3: nested role/admin no persiste verbatim, dotted+__proto__ sin 5xx, array 500 sin fan-out. |
| **TC-06 severity matrix** | ✅ CERRADO | 3/3: escala real 1-4 verificada, out-of-range → 422/normalizado, coerción acotada. |
| **TC-21 tamper evidencias** | ✅ CERRADO | 3/3: mutación/rollback-parcial detectados por fingerprint, borrado → gap exacto. |
| **TC-22 restore selectivo** | ✅ CERRADO | 3/3: miembro único, RPO=0 + RTO<30s medido, versión alternativa. |
| **TC-24 playbooks** | ✅ CERRADO | 3/3 + 4 reglas sigma nuevas (phishing/BEC, exfil, cred-stuffing, webshell) con MITRE tags. |
| **TC-31 STIX/ATT&CK** | ✅ CERRADO | 5/5 — catálogo versionado detections/attack-catalog.yaml (9 técnicas + D3FEND + 2 deprecated); tags añadidos a c2-infrastructure y ransomware-impact. |
| **KPI isolation (KPI-01..06)** | ✅ CERRADO | 3/3 — aislamiento por run (alert_id/trace_id), numerador/denominador formal, guard mttr=0/negativo. |
| **TC-39 bordes temporales** | ✅ CERRADO | 4/4 — mttr clamp futuro exacto, offset/DST, replay alert_id acotado. |
| **TC-41 versions+rate-limit** | ✅ CERRADO | 3/3 — /versions real, burst consistente (medallion sin 429, documentado). |
| **TC-02 FP closure** | ✅ CERRADO | 3/3 — cierre FP con motivo, reclasificación FP→TP, status inválido rechazado. |
| **TC-20 matriz/egress** | ✅ CERRADO | 6/6 — matriz 8 servicios, proxy verbs 403, **egress real bloqueado via api-egress-guard** (sidecar NET_ADMIN en netns api), sin IPv6 global, sin socket raw. BUG REAL arreglado: api recreado sin overlay hardened (socket RW + root) + dup security_opt que invalidaba el merge — contrato test_compose_files añadido (5/5). |
| **TC-36 ES profundo** | ✅ CERRADO | 4/4 — bulk parcial per-item, mapping incompatible 4xx, dedup post-replay, ghost≠zero. |
| **TC-19 inyección ext** | ✅ CERRADO | 7/7 — XXE, SSTI, CRLF, CL.TE smuggling, CSV, path traversal, ReDoS acotado. |
| **TC-40 analyzer semantics** | ✅ CERRADO | 3/3 — opcional (skip en observable vacío/malformado) + spine decisión obligatorio. |
| **PII multi-artefacto** | ✅ CERRADO | 3/3 — diccionario PII sobre JUnit, canary en soar-metrics y Loki (HTTPS fix). |
| **TC-29 payload abuse** | ✅ CERRADO | 3/3 — chunked, gzip-bomb 50x+, zip-like attachment acotados. |
| **TC-28 WCAG server-side** | ✅ CERRADO | 21/21 — lang, title, h1 único, landmarks, alt, labels, viewport. BUGS REALES arreglados: nav landmark ausente en api-docs, selects sin label en web-management, alias soar.local ausente (TLS SAN). |
| **SBOM/secret-scan gate** | ✅ CERRADO | 3/3 contracts — SBOM CycloneDX pinned, diccionario secretos fuente, .env.example limpio. |
| **TC-28 WCAG navegador real** | ✅ CERRADO | 3/3 — axe-core en Chromium real vía sidecar `grafana-image-renderer` + Puppeteer (sin playwright host): owned pages sin violaciones critical/serious, vendor info-only, render verificado. |
| **TC-37 netem avanzado** | ✅ CERRADO | 4/4 — corrupt 5%, tbf bandwidth 2mbit (6.3MB estirado), delay asimétrico egress-only, higiene qdisc total. |
| **CRED-001 mid-flight** | ✅ CERRADO | 1/1 — authkey MISP rotada durante workflow en vuelo; el pipeline termina y la clave primaria sigue válida. |
| **FIX e2e env-loading** | ✅ CERRADO | Bug real: `pytest tests/e2e/…` usa rootdir `tests/e2e` y el confcutdir excluía `tests/conftest.py` → `.env.container` nunca se cargaba en runs e2e-only (la key horneada lo enmascaraba). `tests/e2e/conftest.py` ahora carga `.env.container`→`.env.full` en el mismo orden. |
| **FIX pytest classmethod** | ✅ CERRADO | `PytestRemovedIn10Warning` en fixtures class-scoped (axe + semantic) → `@classmethod`. |
| **TC-11 watcher precision** | ✅ CERRADO | 5/5 — matriz TP/FP/FN vs ground truth `docker network inspect` (29 TP/0 FP/0 FN), IPv4 parseable, sin duplicados post-restart, brief-connection tracked+removed, **impostor `worker-evil` rechazado por allowlist de imagen**. |
| **TC-36 obs-outage matrix** | ✅ CERRADO | 4/4 — otel-collector/tempo/prometheus/promtail-down: API sigue sana, promtail replay sin pérdida, prometheus `/ready`+`up` recuperados (diagnóstico `series=32 up=32`). |
| **FIX test-portabilidad** | ✅ CERRADO | `API = localhost:8000` hardcodeado → `E2E_API_URL` env (default `http://api:8000`) — funciona en api y en runner dedicado. |
| **FIX skip-list clobber** | ✅ CERRADO | `setup_method` sobrescribía `E2E_SKIP_SERVICES` → ahora mergea con el env del caller. |
| **FIX TheHive locked-user** | ✅ CERRADO | Bug real: rollback BJE resucita `analyst@soar.local` con `locked:true` → toda key renovada 401. `init_thehive.py` ahora hace `PATCH user/{id} {locked:false}` antes del renew. |
| **FIX health-gate** | ✅ CERRADO | `_check_with_warmup_retries` env-tunable: `E2E_HEALTH_ATTEMPTS` (def 10) / `E2E_HEALTH_PAUSE_S` (def 8) — sobrevive olas de reconciliación de Docker Desktop (~5min). |
| **INFRA soar_test_runner** | ✅ CERRADO | Contenedor dedicado fuera del proyecto compose (misma imagen/mounts/env) — los pytest e2e ya no mueren cuando la reconciliación recrea `soar_api`. Script: `scripts/debug/mk_test_runner.py`. |
| **INFRA egress-guard re-anclado** | ✅ CERRADO | Bug real: `network_mode: service:api` resuelve a container-ID en creación → tras cada recreate del api el sidecar queda huérfano de un netns muerto y las reglas EGRESS_GUARD se pierden en silencio. Re-anclado + documentado en AGENTS.md. |


> Origen: `docs/22-subtest-evaluation.md` (445 subtests catalogados, notas por suite).
> Objetivo: cada suite ≥9.5. Prioridad: **P0** cierra falsos-verde/pérdida/seguridad; **P1** eleva nota; **P2** consolida 10.
> DoD por subtest: timeout explícito, cleanup idempotente, evidencia (JUnit+artifact), catalogado, `make_target` opcional, ≥10 runs verdes (críticos 30).

## P0 — infraestructura de fiabilidad (desbloquea todo lo demás)

| ID | Alcance | Subtests a crear | Aceptación |
|---|---|---|---|
| NET-001 | **Netem real** (TC-37) — la mayor deuda | `test_netem_delay_250ms_shuffle_thehive`, `test_netem_jitter_loss_2pct`, `test_netem_loss_5pct_cortex`, `test_netem_dup_reorder`, `test_netem_partition_unilateral`, `test_netem_bilateral`, `test_netem_dns_slow`, `test_netem_tcp_reset`, `test_tc_qdisc_always_removed` | `tc qdisc` dentro del netns del contenedor objetivo (o `docker run --cap-add NET_ADMIN` sidecar); timeout+retry coherentes, sin retry-storm, teardown borra qdisc aunque falle |
| TMO-001 | **Máquina de estados timeout** (TC-38) | `test_state_timed_out`, `test_state_cancelling_cancelled`, `test_state_recovering`, `test_late_result_reconciled_not_silent`, `test_node_timeout_vs_global_timeout`, `test_orborus_restart_orphan_adopted`, `test_metric_workflow_stuck_total`, `test_gauge_oldest_executing_seconds`, `test_alert_slo_execution_breach` | Estados explícitos en `stale_execution_gc`+docs; métricas exportadas en `/metrics`; resultado tardío nunca muta estado terminal sin auditoría |
| CRED-001 | **Rotación credenciales mid-suite** (TC-39 ext) | `test_thehive_key_rotation_live`, `test_shuffle_key_rotation_coexistence`, `test_old_key_revoked_immediately`, `test_worker_cached_secret_refresh`, `test_rollback_rotation`, `test_new_key_invalid_bounded` | Rotación real vía `init_thehive.py`/Shuffle API; ventana de coexistencia documentada; sin secretos en logs/JUnit |
| DS-001 | **Data safety extendido** | `test_disk_full_real_fs` (fallocate en volumen scratch), `test_inodes_exhausted`, `test_es_write_during_flood_recovery`, `test_backup_manifest_tampered`, `test_backup_wrong_version`, `test_backup_wrong_key` | Restore rechaza antes de escribir; error distingue corrupción/versión/credencial; recuperación sin recrear stack |

## P1 — subtests funcionales/seguridad por suite

| Suite | Subtests a crear (nombres canónicos) | Eleva a |
|---|---|---|
| TC-02 | `test_benign_closes_as_false_positive`, `test_close_requires_reason`, `test_no_containment_on_benign`, `test_reclassify_fp_to_tp_once`, `test_close_preserves_observables`, `test_fp_metrics_updated` | 9.5 |
| TC-03/29 | `test_payload_boundary_minus1_exact_plus1`, `test_chunked_encoding`, `test_zip_bomb_ratio_limit`, `test_json_depth_limit`, `test_nan_infinity_rejected`, `test_null_byte`, `test_duplicate_keys`, `test_upload_interrupted_no_tmp_leak` | 9.5 |
| TC-06 | `test_severity_critical_to_high`, `test_severity_absent_derived`, `test_severity_invalid_rejected`, `test_severity_change_recalculates_sla`, `test_severity_conflict_source_vs_computed`, `test_escalation_notifies_assignment` | 9.5 |
| TC-07 | `test_error_contract_code_field`, `test_error_category_retryable`, `test_error_correlation_id_in_logs`, `test_error_no_internal_details`, `test_multi_missing_fields_order_independent` | 9.5 |
| TC-08 | `test_nested_protected_field_ignored`, `test_array_object_injection`, `test_dot_notation_override`, `test_duplicate_keys`, `test_case_variation`, `test_attempt_audited_without_payload` | 9.5 |
| TC-10/25 | `test_pcap_dns_c2_detected`, `test_pcap_http_beaconing`, `test_pcap_sni_suspicious`, `test_pcap_exfil_low_and_slow`, `test_pcap_lateral_smb`, `test_pcap_truncated_out_of_order`, `test_pcap_ipv6`, `test_zero_event_loss_or_tolerance` | 9.5 |
| TC-11/17 | `test_precision_tp_fp_fn_matrix`, `test_ipv6_connection`, `test_brief_connection`, `test_recovery_no_duplicate_events`, `test_detection_latency_measured` | 9.5 |
| TC-12/26 | `test_eviction_noeviction`, `test_eviction_allkeys_lru_ioc_recomputable`, `test_cache_stampede`, `test_hot_key_contention`, `test_hit_miss_rate_exported`, `test_queue_oldest_message_age`, `test_dlq_redrive`, `test_drain_within_slo`, `test_fairness_critical_vs_normal` | 9.5 |
| TC-13 | `test_loki_retention_policy`, `test_rotation_compaction`, `test_out_of_order_logs`, `test_future_timestamp`, `test_query_across_retention_boundary` | 9.5 |
| TC-14 | `test_per_hop_semantic_contract`, `test_field_loss_documented`, `test_tlp_pap_propagation`, `test_otel_baggage_limits`, `test_async_span_links`, `test_no_pii_in_attributes` | 10 |
| TC-15 | `test_p95_100_samples`, `test_cold_vs_warm`, `test_client_vs_server_latency`, `test_ci_interval_published` | 9.5 |
| TC-16 | `test_error_budget_window`, `test_retryable_vs_nonretryable`, `test_degraded_partial_side_effects`, `test_retry_storm_protection` | 9.5 |
| TC-19 | `test_xxe_local_entity`, `test_billion_laughs_limited`, `test_template_injection_jinja`, `test_command_injection`, `test_zip_slip`, `test_crlf_header`, `test_host_header_poison`, `test_csv_injection`, `test_redos_bounded`, `test_null_byte_injection`, `test_polyglot_file`, `test_unsigned_alg_rejected` | 9.5 |
| TC-20 | `test_full_reachability_matrix`, `test_denied_pairs_fail`, `test_no_public_db_ports`, `test_no_lateral_between_networks`, `test_ipv6_restrictions`, `test_docker_socket_scoped`, `test_dns_scope`, `test_egress_allowlist` | 9.5 |
| TC-21 | `test_artifact_modified_detected`, `test_metadata_altered`, `test_audit_link_removed`, `test_events_reordered`, `test_same_name_substitution`, `test_stored_checksum_altered`, `test_old_valid_restore_detected`, `test_actor_time_checksums_logged` | 9.5 |
| TC-22 | `test_selective_restore`, `test_restore_other_version`, `test_backup_during_writes`, `test_rpo_rto_measured`, `test_cleanup_after_failed_restore` | 9.5 |
| TC-23 | `test_pii_dictionary_enforced`, `test_canary_in_junit`, `test_canary_in_traces`, `test_canary_in_backups`, `test_canary_in_screenshots`, `test_canary_in_dlq`, `test_url_embedded_secrets`, `test_nested_json_secrets`, `test_high_cardinality_labels` | 9.5 |
| TC-24 | `test_playbook_phishing`, `test_playbook_bec`, `test_playbook_exfiltration`, `test_playbook_insider`, `test_playbook_credential_stuffing`, `test_playbook_webshell`, `test_playbook_cloud_abuse`, `test_playbook_dns_tunneling` | 9.5 |
| TC-27 | `test_rebaseline_requires_approval`, `test_semantic_diff`, `test_secret_normalization`, `test_volatile_fields_ignored`, `test_baseline_signed_versioned` | 9.5 |
| TC-28 | `test_dom_semantic_dashboard`, `test_no_js_errors`, `test_no_failed_critical_requests`, `test_keyboard_navigation`, `test_wcag22_aa_zero_critical`, `test_reflow_320px`, `test_zoom_200`, `test_responsive_3_viewports`, `test_expired_session_redirect` | 9.5 |
| TC-30 | `test_dns_total_failure`, `test_nxdomain_single`, `test_dns_slow_bounded`, `test_stale_cache_behavior`, `test_internal_ok_external_fail`, `test_crl_ocsp_unreachable` | 9.5 |
| TC-31 | `test_technique_exists_in_catalog`, `test_revoked_technique_warns`, `test_threat_technique_mitigation_chain`, `test_d3fend_mapping`, `test_catalog_version_pinned`, `test_tactic_coverage_report` | 9.5 |
| TC-33 | `test_offline_mode_full`, `test_sample_cache_sha256`, `test_inert_samples_verified`, `test_availability_gate_before_run` | 10 |

## P1 — suites nuevas (resiliencia profunda)

| Suite | Subtests | Nota tras |
|---|---|---|
| TC-36 ext | `test_es_partial_bulk_acceptance`, `test_es_ack_before_persist`, `test_es_index_missing`, `test_es_incompatible_mapping`, `test_es_recovery_inside_retry_window`, `test_es_recovery_after_window`, `test_es_connection_reset`, `test_es_no_duplicate_docs_after_recovery`, `test_delayed_metrics_policy`, `test_dashboards_no_false_zeros`, `test_redis_maxmemory_reached`, `test_redis_eviction_lru`, `test_redis_noeviction`, `test_redis_readonly_error`, `test_redis_slow_responses`, `test_redis_dedup_during_outage`, `test_redis_state_loss_documented`, `test_promtail_buffer_replay`, `test_otel_collector_down`, `test_tempo_down`, `test_prometheus_down` | 9.5 |
| TC-38 ext | ver TMO-001 | 9.5 |
| TC-39 ext | `test_skew_exact_tolerance_edges`, `test_replay_same_nonce`, `test_new_signature_same_body`, `test_dst_transition`, `test_epoch_ms_vs_seconds`, `test_canary_in_junit`, `test_canary_in_screenshots`, `test_canary_in_traces`, `test_backup_manifest_altered`, `test_backup_incompatible_version` | 9.5 |
| TC-40 ext | `test_cert_expired`, `test_cert_not_yet_valid`, `test_cert_revoked`, `test_incomplete_chain`, `test_weak_algorithm`, `test_mtls_missing_client_cert`, `test_mtls_expired_client`, `test_cert_rotation_persistent_conn`, `test_analyzer_optional_fails_workflow_survives`, `test_analyzer_mandatory_fails_workflow_fails`, `test_analyzer_partial_labeled`, `test_analyzer_invalid_json`, `test_analyzer_cancel`, `test_auth_matrix_methods_post_put_delete`, `test_disk_full_physical` | 9.5 |
| TC-41 ext | `test_pagination_beyond_100`, `test_added_after_incremental`, `test_object_versions_endpoint`, `test_status_endpoint_polling`, `test_stix20_vs_21_negotiation`, `test_duplicate_object_idempotent`, `test_collection_not_found`, `test_invalid_auth` | 9.5 |

## P1 — KPIs (todos KPI-01..06)

`test_run_id_isolation`, `test_locust_excluded`, `test_utc_normalized`, `test_temporal_order`, `test_min_samples`, `test_numerator_denominator_formal`, `test_no_data_distinct_from_zero`, `test_division_by_zero`, `test_traces_to_source_events` → 9.5

## P2 — consolidación 10

| ID | Entregable |
|---|---|
| QUAL-001 | Matriz trazabilidad requisito→riesgo→control→test→evidencia→resultado completa (extender `docs/09`) |
| PERF-001 | Baselines por versión/hardware/volumen; p95/p99 con ≥100 muestras; regresión >10% warn, >20% fail |
| TEST-INFRA-003 | Catálogo auto-generado con marcadores/prioridad/duración/destructivo/paralelizable/ISO-MITRE mapping/flakiness |
| TEST-SEC-002 | Secret-scan gate sobre repo+logs+JUnit+screenshots+backups+volúmenes — canary bloquea |
| TEST-SEC-003 | SBOM imágenes+herramientas, versiones pineadas, sin installers dinámicos |
| UI-002 | WCAG 2.2 AA cero críticas/cero serias sin excepción documentada |
| OBS-003 | Tempo/Prometheus/Promtail/OTel-collector outage matrix (ver TC-36 ext) |
| STAB-001 | 30 runs CI ≥99%, flake <0.5%, cero críticos en cuarentena — medido vía junit+flaky_report |

## Orden de ejecución

1. **NET-001 + TMO-001** (P0, mayor impacto/nota: TC-37 8.0→9.5, TC-38 →9.5)
2. **DS-001 + CRED-001** (P0 seguridad/datos)
3. **TC-36/40/41 ext** (suites ya verdes → completar casos)
4. **P1 funcionales** TC-02..33 por orden alfabético
5. **P2** trazabilidad/baselines/catálogo-auto/secret-gate
6. **STAB-001** medición 30 runs (calendario CI, iniciar ya el nightly)

> Estimación global: P0 ~2 semanas de sesiones, P1 ~4-6, P2 ~2. Tras P0+P1 completos: media ≥9.5 defendible.
