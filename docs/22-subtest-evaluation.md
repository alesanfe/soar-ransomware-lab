# Evaluación a nivel subtest — suite E2E completa

> Generada del catálogo real + evidencias verificadas de ejecución.

## TC-00 — nota: **9.5**

- **Positivos**: Happy path alert→workflow→case→metrics; verificado
- **Negativos**: execution_time usa histórico sin aislar; sin warm-up
- **Deuda**: Baseline aislado, warm-up, paralelismo por spans
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-00-01 | `test_workflow_malicious` | implementado |
| TC-00-02 | `test_parallel_workflow_execution` | implementado |
| TC-00-03 | `test_workflow_consistency` | implementado |
| TC-00-04 | `test_execution_time_comparison` | implementado |

**Subtests existentes**: 4

## TC-01 — nota: **9.5**

- **Positivos**: Infra del workflow end-to-end
- **Negativos**: 95s/test mezcla setup y asserts; sin timeout por fase
- **Deuda**: Diagnóstico de fase lenta
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-01-01 | `test_malicious_alert_full_workflow_group_1` | implementado |
| TC-01-02 | `test_malicious_alert_full_workflow_group_2` | implementado |
| TC-01-03 | `test_malicious_alert_full_workflow_group_3` | implementado |
| TC-01-04 | `test_malicious_alert_full_workflow_group_4` | implementado |
| TC-01-05 | `test_observable_validation` | implementado |
| TC-01-06 | `test_ioc_validation` | implementado |
| TC-01-07 | `test_tag_validation` | implementado |
| TC-01-08 | `test_tlp_pap_validation` | implementado |
| TC-01-09 | `test_task_validation` | implementado |
| TC-01-10 | `test_state_machine_validation` | implementado |
| TC-01-11 | `test_opensearch_validation` | implementado |

**Subtests existentes**: 11

## TC-02 — nota: **9.0**

- **Positivos**: Clasificación de alertas
- **Negativos**: Cierre benigno→FP formal, motivo, reclasificación FP→TP
- **Deuda**: E2E-FUN-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-02-01 | `test_benign_alert_workflow` | implementado |
| TC-02-02 | `test_no_blocking` | implementado |
| TC-02-03 | `test_no_isolation` | implementado |
| TC-02-04 | `test_no_unnecessary_intelligence` | implementado |
| TC-02-05 | `test_audit_trail` | implementado |
| TC-02-06 | `test_case_closed_false_positive_with_reason` | implementado |
| TC-02-07 | `test_fp_reclassification_to_true_positive` | implementado |
| TC-02-08 | `test_invalid_resolution_status_rejected` | implementado |

**Subtests existentes**: 8

## TC-03 — nota: **9.0**

- **Positivos**: Validación/admisión de payloads
- **Negativos**: JSON depth, NaN, null-byte, claves dup, chunked, ±1B
- **Deuda**: E2E-SIZE-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-03-01 | `test_edge_cases_resilience` | implementado |
| TC-03-02 | `test_empty_payload` | implementado |
| TC-03-03 | `test_null_fields` | implementado |
| TC-03-04 | `test_unicode_characters` | implementado |
| TC-03-05 | `test_special_characters` | implementado |
| TC-03-06 | `test_large_payload` | implementado |
| TC-03-07 | `test_empty_arrays` | implementado |
| TC-03-08 | `test_nested_json` | implementado |
| TC-03-09 | `test_invalid_dates` | implementado |
| TC-03-10 | `test_invalid_hash` | implementado |
| TC-03-11 | `test_limit_minus_1b_passes_edge` | implementado |
| TC-03-12 | `test_limit_plus_1b_rejected` | implementado |
| TC-03-13 | `test_json_depth_bounded` | implementado |

**Subtests existentes**: 13

## TC-04 — nota: **9.5**

- **Positivos**: Performance con medición real
- **Negativos**: Baseline versionado y drift automático aún rígidos
- **Deuda**: PERF-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-04-01 | `test_single_alert_latency` | implementado |
| TC-04-02 | `test_concurrent_alerts` | implementado |
| TC-04-03 | `test_sequential_batch` | implementado |
| TC-04-04 | `test_memory_usage` | implementado |
| TC-04-05 | `test_cpu_usage` | implementado |
| TC-04-06 | `test_kpi_calculation_performance` | implementado |
| TC-04-07 | `test_queue_depth` | implementado |
| TC-04-08 | `test_workflow_latency` | implementado |
| TC-04-09 | `test_total_response_time` | implementado |
| TC-04-10 | `test_p50_percentile` | implementado |
| TC-04-11 | `test_p95_percentile` | implementado |
| TC-04-12 | `test_p99_percentile` | implementado |
| TC-04-13 | `test_redis_cache_hit` | implementado |
| TC-04-14 | `test_sla_compliance` | implementado |

**Subtests existentes**: 14

## TC-05 — nota: **9.5**

- **Positivos**: Concurrencia/alert-storm
- **Negativos**: Capacidad máx, fairness, drenado post-carga
- **Deuda**: PERF-003
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-05-01 | `test_concurrent_alerts` | implementado |
| TC-05-02 | `test_10_concurrent_alerts` | implementado |
| TC-05-03 | `test_mass_concurrent_alerts` | implementado |
| TC-05-04 | `test_data_consistency` | implementado |
| TC-05-05 | `test_no_duplicates` | implementado |
| TC-05-06 | `test_recovery_after_load` | implementado |

**Subtests existentes**: 6

## TC-06 — nota: **9.0**

- **Positivos**: Severidad+enriquecimiento
- **Negativos**: Matriz transiciones, ausente→derivada, conflicto
- **Deuda**: E2E-FUN-002
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-06-01 | `test_critical_severity` | implementado |
| TC-06-02 | `test_critical_workflow` | implementado |
| TC-06-03 | `test_correct_priority` | implementado |
| TC-06-04 | `test_critical_tasks` | implementado |
| TC-06-05 | `test_critical_sla` | implementado |
| TC-06-06 | `test_auto_escalation` | implementado |
| TC-06-07 | `test_full_severity_range_accepted` | implementado |
| TC-06-08 | `test_out_of_range_bounded_not_stored` | implementado |
| TC-06-09 | `test_severity_type_coercion_bounded` | implementado |

**Subtests existentes**: 9

## TC-07 — nota: **9.0**

- **Positivos**: Errores de validación
- **Negativos**: Texto exacto→contrato {code,field,category,retryable,correlation_id}
- **Deuda**: E2E-CONTRACT-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-07-01 | `test_missing_fields` | implementado |
| TC-07-02 | `test_missing_required_field` | implementado |
| TC-07-03 | `test_missing_optional_field` | implementado |
| TC-07-04 | `test_derivable_field` | implementado |
| TC-07-05 | `test_error_message` | implementado |
| TC-07-06 | `test_422_field_pinpointed_contract` | implementado |
| TC-07-07 | `test_401_machine_readable_with_correlation` | implementado |
| TC-07-08 | `test_404_machine_readable_with_correlation` | implementado |
| TC-07-09 | `test_error_responses_are_json` | implementado |

**Subtests existentes**: 9

## TC-08 — nota: **9.0**

- **Positivos**: Mass assignment rechazado
- **Negativos**: Anidado, arrays, notación punto, case-sensitivity
- **Deuda**: E2E-CONTRACT-002
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-08-01 | `test_additional_fields` | implementado |
| TC-08-02 | `test_unknown_field` | implementado |
| TC-08-03 | `test_custom_metadata` | implementado |
| TC-08-04 | `test_field_override_prevention` | implementado |
| TC-08-05 | `test_nested_privilege_objects_not_persisted` | implementado |
| TC-08-06 | `test_dotted_and_proto_keys_rejected_or_inert` | implementado |
| TC-08-07 | `test_array_of_objects_does_not_expand` | implementado |

**Subtests existentes**: 7

## TC-09 — nota: **9.5**

- **Positivos**: Vectores ransomware ampliados
- **Negativos**: Doble extorsión/lateral parcial; cache firmado offline
- **Deuda**: TEST-SEC-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-09-01 | `test_realistic_ransomware` | implementado |
| TC-09-02 | `test_ransomware_detection` | implementado |
| TC-09-03 | `test_case_creation` | implementado |
| TC-09-04 | `test_cortex_analysis` | implementado |
| TC-09-05 | `test_misp_ioc` | implementado |
| TC-09-06 | `test_evidence_collection` | implementado |
| TC-09-07 | `test_task_assignment` | implementado |

**Subtests existentes**: 7

## TC-10 — nota: **9.0**

- **Positivos**: Tenzir funcional
- **Negativos**: PCAP realista versionado + oráculo semántico
- **Deuda**: E2E-NET-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-10-01 | `test_tenzir_service_availability` | implementado |
| TC-10-02 | `test_tenzir_pipeline_execution` | implementado |
| TC-10-03 | `test_tenzir_pipeline_execution_cli` | implementado |
| TC-10-04 | `test_tenzir_network_events_retrieval` | implementado |
| TC-10-05 | `test_tenzir_integration_completeness` | implementado |
| TC-10-06 | `test_tenzir_error_handling` | implementado |
| TC-10-07 | `test_tenzir_performance_requirements` | implementado |
| TC-10-08 | `test_tenzir_ingestion` | implementado |
| TC-10-09 | `test_tenzir_query` | implementado |
| TC-10-10 | `test_tenzir_correlation` | implementado |
| TC-10-11 | `test_tenzir_latency` | implementado |

**Subtests existentes**: 11

## TC-11 — nota: **9.0**

- **Positivos**: Watcher health/precisión
- **Negativos**: TP/FP/FN formales, IPv6, conexiones breves
- **Deuda**: E2E-NET-002
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-11-01 | `test_network_watcher_service_availability` | implementado |
| TC-11-02 | `test_network_watcher_connections_endpoint` | implementado |
| TC-11-03 | `test_network_watcher_connection_monitoring` | implementado |
| TC-11-04 | `test_network_watcher_real_time_monitoring` | implementado |
| TC-11-05 | `test_network_watcher_error_handling` | implementado |
| TC-11-06 | `test_network_watcher_performance_requirements` | implementado |
| TC-11-07 | `test_network_watcher_integration_completeness` | implementado |
| TC-11-08 | `test_network_connection` | implementado |
| TC-11-09 | `test_network_source` | implementado |
| TC-11-10 | `test_network_destination` | implementado |
| TC-11-11 | `test_network_correlation` | implementado |

**Subtests existentes**: 11

## TC-12 — nota: **9.0**

- **Positivos**: Cache IoC operativa
- **Negativos**: Eviction, stampede, poisoning, hit/miss rate
- **Deuda**: E2E-CACHE-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-12-01 | `test_redis_service_availability` | implementado |
| TC-12-02 | `test_redis_direct_connection` | implementado |
| TC-12-03 | `test_redis_ioc_caching_in_workflow` | implementado |
| TC-12-04 | `test_redis_ioc_storage` | implementado |
| TC-12-05 | `test_redis_ioc_retrieval` | implementado |
| TC-12-06 | `test_redis_cache_expiration` | implementado |
| TC-12-07 | `test_redis_pattern_matching` | implementado |
| TC-12-08 | `test_redis_performance_requirements` | implementado |
| TC-12-09 | `test_redis_error_handling` | implementado |
| TC-12-10 | `test_redis_integration_completeness` | implementado |

**Subtests existentes**: 10

## TC-13 — nota: **9.0**

- **Positivos**: Loki ingest/query
- **Negativos**: Retención, rotación, compactación, out-of-order
- **Deuda**: E2E-OBS-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-13-01 | `test_loki_service_availability` | implementado |
| TC-13-02 | `test_loki_query_range_endpoint` | implementado |
| TC-13-03 | `test_loki_hostname_filtering` | implementado |
| TC-13-04 | `test_loki_ip_filtering` | implementado |
| TC-13-05 | `test_loki_in_workflow` | implementado |
| TC-13-06 | `test_loki_log_parsing` | implementado |
| TC-13-07 | `test_loki_time_range_queries` | implementado |
| TC-13-08 | `test_loki_error_handling` | implementado |
| TC-13-09 | `test_loki_performance_requirements` | implementado |
| TC-13-10 | `test_loki_integration_completeness` | implementado |
| TC-13-11 | `test_loki_log_aggregation` | implementado |
| TC-13-12 | `test_loki_ingestion` | implementado |
| TC-13-13 | `test_loki_trace_id_search` | implementado |
| TC-13-14 | `test_loki_latency` | implementado |
| TC-13-15 | `test_loki_hidden_errors` | implementado |

**Subtests existentes**: 15

## TC-14 — nota: **9.5**

- **Positivos**: trace_id cross-system real
- **Negativos**: Contrato semántico/salto, baggage, links asíncronos
- **Deuda**: E2E-OBS-002
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-14-01 | `test_all_new_services_availability` | implementado |
| TC-14-02 | `test_complete_workflow_execution` | implementado |
| TC-14-03 | `test_data_flow_between_services` | implementado |
| TC-14-04 | `test_error_handling_and_recovery` | implementado |
| TC-14-05 | `test_tenzir_data_flow` | implementado |
| TC-14-06 | `test_network_watcher_data_flow` | implementado |
| TC-14-07 | `test_redis_cache_flow` | implementado |
| TC-14-08 | `test_loki_log_flow` | implementado |
| TC-14-09 | `test_trace_id_propagation` | implementado |
| TC-14-10 | `test_cross_system_coherence` | implementado |

**Subtests existentes**: 10

## TC-15 — nota: **9.0**

- **Positivos**: Latencia endpoints
- **Negativos**: Muestras p95/p99, cold vs warm
- **Deuda**: PERF-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-15-01 | `test_get_latency` | implementado |
| TC-15-02 | `test_post_latency` | implementado |
| TC-15-03 | `test_search_latency` | implementado |
| TC-15-04 | `test_p95_latency` | implementado |
| TC-15-05 | `test_sla_compliance` | implementado |
| TC-15-06 | `test_thehive_api_latency` | implementado |
| TC-15-07 | `test_cortex_api_latency` | implementado |
| TC-15-08 | `test_misp_api_latency` | implementado |

**Subtests existentes**: 8

## TC-16 — nota: **9.0**

- **Positivos**: Errores integración clasificados
- **Negativos**: Ventana fija, error budget, retryable, retry-storm
- **Deuda**: KPI-007
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-16-01 | `test_error_classification` | implementado |
| TC-16-02 | `test_partial_success` | implementado |
| TC-16-03 | `test_degraded_mode` | implementado |
| TC-16-04 | `test_error_recovery` | implementado |
| TC-16-05 | `test_error_rate_by_service` | implementado |
| TC-16-06 | `test_error_rate_by_type` | implementado |

**Subtests existentes**: 6

## TC-17 — nota: **9.0**

- **Positivos**: Watcher recovery
- **Negativos**: Recovery sin duplicados formalizado
- **Deuda**: E2E-NET-002
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-17-01 | `test_network_watcher_health` | implementado |
| TC-17-02 | `test_network_watcher_connections` | implementado |
| TC-17-03 | `test_network_watcher_real_time_updates` | implementado |
| TC-17-04 | `test_restart_recovery` | implementado |
| TC-17-05 | `test_connection_tracking` | implementado |
| TC-17-06 | `test_ip_filtering` | implementado |
| TC-17-07 | `test_port_monitoring` | implementado |
| TC-17-08 | `test_protocol_detection` | implementado |

**Subtests existentes**: 8

## TC-18 — nota: **9.0**

- **Positivos**: Chaos deps-caídas, errores 503 tipados
- **Negativos**: Netem/partición/kill-en-commit (parcial en TC-37)
- **Deuda**: Teardown central
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-18-01 | `test_cortex_unavailable` | implementado |
| TC-18-02 | `test_misp_unavailable` | implementado |
| TC-18-03 | `test_both_unavailable` | implementado |
| TC-18-04 | `test_orborus_unavailable` | implementado |
| TC-18-05 | `test_dependency_timeout` | implementado |

**Subtests existentes**: 5

## TC-19 — nota: **9.0**

- **Positivos**: Familias ofensivas
- **Negativos**: XXE, template inj, zip slip, CRLF, smuggling, CSV, ReDoS
- **Deuda**: E2E-SEC-002
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-19-01 | `test_malformed_json` | implementado |
| TC-19-02 | `test_invalid_data_types` | implementado |
| TC-19-03 | `test_sql_injection_attempt` | implementado |
| TC-19-04 | `test_xss_attempt` | implementado |
| TC-19-05 | `test_replay_attack_prevention` | implementado |
| TC-19-06 | `test_oversized_payload` | implementado |
| TC-19-07 | `test_broken_json` | implementado |
| TC-19-08 | `test_unexpected_xml` | implementado |
| TC-19-09 | `test_excessive_payload` | implementado |
| TC-19-10 | `test_expired_jwt` | implementado |
| TC-19-11 | `test_revoked_api_key` | implementado |
| TC-19-12 | `test_replay_attack` | implementado |
| TC-19-13 | `test_rate_limiting` | implementado |
| TC-19-14 | `test_ssrf_attempt` | implementado |
| TC-19-15 | `test_deserialization_attempt` | implementado |
| TC-19-16 | `test_xxe_entity_expansion_never_resolves` | implementado |
| TC-19-17 | `test_ssti_payloads_stored_verbatim_never_evaluated` | implementado |
| TC-19-18 | `test_crlf_header_injection_never_lands` | implementado |
| TC-19-19 | `test_cl_te_smuggling_bounded` | implementado |
| TC-19-20 | `test_csv_formula_injection_stored_verbatim` | implementado |
| TC-19-21 | `test_path_traversal_fields_stored_verbatim` | implementado |
| TC-19-22 | `test_pathological_input_bounded_latency` | implementado |

**Subtests existentes**: 22

## TC-20 — nota: **9.0**

- **Positivos**: Reachability core
- **Negativos**: Matriz total, IPv6, docker socket, egress
- **Deuda**: E2E-ZT-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-20-01 | `test_zero_trust_authentication` | implementado |
| TC-20-02 | `test_network_segmentation` | implementado |
| TC-20-03 | `test_least_privilege` | implementado |
| TC-20-04 | `test_micro_segmentation` | implementado |
| TC-20-05 | `test_api_has_no_raw_docker_socket` | implementado |
| TC-20-06 | `test_docker_proxy_denies_privileged_verbs` | implementado |
| TC-20-07 | `test_no_service_exposes_docker_tcp` | implementado |
| TC-20-08 | `test_full_service_port_matrix` | implementado |
| TC-20-09 | `test_egress_external_ip_blocked` | implementado |
| TC-20-10 | `test_no_ipv6_global_address` | implementado |

**Subtests existentes**: 10

## TC-21 — nota: **9.0**

- **Positivos**: Custodia/checksum
- **Negativos**: Tamper activo: reordenar, suprimir, rollback, firma
- **Deuda**: E2E-SEC-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-21-01 | `test_chain_of_custody` | implementado |
| TC-21-02 | `test_audit_trail` | implementado |
| TC-21-03 | `test_immutability` | implementado |
| TC-21-04 | `test_chain_of_custody_subcase` | implementado |
| TC-21-05 | `test_checksum_backup` | implementado |
| TC-21-06 | `test_evidence_immutability` | implementado |
| TC-21-07 | `test_audit_trail_subcase` | implementado |
| TC-21-08 | `test_fingerprint_detects_field_mutation` | implementado |
| TC-21-09 | `test_fingerprint_detects_partial_rollback` | implementado |
| TC-21-10 | `test_deleted_evidence_detectable_by_gap` | implementado |

**Subtests existentes**: 10

## TC-22 — nota: **9.0**

- **Positivos**: Backup/restore round-trip
- **Negativos**: Corrupto en TC-39; falta selectivo, otra versión, RPO/RTO
- **Deuda**: E2E-DATA-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-22-01 | `test_elasticsearch_persistence` | implementado |
| TC-22-02 | `test_thehive_persistence` | implementado |
| TC-22-03 | `test_volume_persistence` | implementado |
| TC-22-04 | `test_backup_integrity` | implementado |
| TC-22-05 | `test_data_consistency_after_restart` | implementado |
| TC-22-06 | `test_reboot_thehive` | implementado |
| TC-22-07 | `test_container_recreation` | implementado |
| TC-22-08 | `test_docker_down_up` | implementado |
| TC-22-09 | `test_backup_restore` | implementado |
| TC-22-10 | `test_selective_member_restore` | implementado |
| TC-22-11 | `test_rpo_rto_measured_and_bounded` | implementado |
| TC-22-12 | `test_alternate_version_restore` | implementado |

**Subtests existentes**: 12

## TC-23 — nota: **9.0**

- **Positivos**: Sanitización
- **Negativos**: Diccionario PII, canaries multi-artefacto
- **Deuda**: E2E-PRIV-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-23-01 | `test_pii_masking` | implementado |
| TC-23-02 | `test_secret_redaction` | implementado |
| TC-23-03 | `test_data_minimization` | implementado |
| TC-23-04 | `test_pii_masking_subcase` | implementado |
| TC-23-05 | `test_secret_redaction_subcase` | implementado |
| TC-23-06 | `test_external_filtering` | implementado |
| TC-23-07 | `test_sensitive_artifacts` | implementado |
| TC-23-08 | `test_junit_artifacts_carry_no_real_pii` | implementado |
| TC-23-09 | `test_stored_metrics_doc_carries_no_unmasked_pii` | implementado |
| TC-23-10 | `test_loki_streams_carry_no_raw_canary` | implementado |

**Subtests existentes**: 10

## TC-24 — nota: **9.0**

- **Positivos**: Playbooks base
- **Negativos**: Phishing/BEC/exfil/insider/cred/webshell/cloud
- **Deuda**: E2E-THREAT-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-24-01 | `test_ransomware_response` | implementado |
| TC-24-02 | `test_rat_response` | implementado |
| TC-24-03 | `test_worm_response` | implementado |
| TC-24-04 | `test_cryptominer_response` | implementado |
| TC-24-05 | `test_rules_wellformed_sigma_with_mitre_tags` | implementado |
| TC-24-06 | `test_typed_alerts_admitted_by_pipeline` | implementado |
| TC-24-07 | `test_playbook_alert_reaches_a_decision` | implementado |

**Subtests existentes**: 7

## TC-25 — nota: **9.0**

- **Positivos**: Forense/PCAP base
- **Negativos**: Dataset versionado + oráculo + precisión
- **Deuda**: E2E-NET-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-25-01 | `test_polymorphic_behavior` | implementado |
| TC-25-02 | `test_low_and_slow_exfiltration` | implementado |
| TC-25-03 | `test_multi_stage_kill_chain` | implementado |
| TC-25-04 | `test_canary_file_detection` | implementado |

**Subtests existentes**: 4

## TC-26 — nota: **9.0**

- **Positivos**: Load/queue
- **Negativos**: Memoria, edad msg, DLQ, fairness, recovery, límites
- **Deuda**: PERF-003
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-26-01 | `test_alert_storm` | implementado |
| TC-26-02 | `test_concurrency_limit` | implementado |
| TC-26-03 | `test_backpressure` | implementado |
| TC-26-04 | `test_duplicate_prevention` | implementado |

**Subtests existentes**: 4

## TC-27 — nota: **9.0**

- **Positivos**: Config drift
- **Negativos**: Rebaseline aprobado, diff semántico, firma
- **Deuda**: CONF-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-27-01 | `test_configuration_drift_detection` | implementado |
| TC-27-02 | `test_golden_configuration` | implementado |
| TC-27-03 | `test_volume_persistence` | implementado |
| TC-27-04 | `test_environment_variables` | implementado |

**Subtests existentes**: 4

## TC-28 — nota: **9.0**

- **Positivos**: UI screenshots+a11y
- **Negativos**: Render semántico, responsive, WCAG 2.2 completa
- **Deuda**: UI-001/002; SSO fuera por decisión
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-28-01 | `test_shuffle_login` | implementado |
| TC-28-02 | `test_thehive_navigation` | implementado |
| TC-28-03 | `test_shuffle_workflow_creation` | implementado |
| TC-28-04 | `test_thehive_case_creation` | implementado |
| TC-28-05 | `test_dashboard_accessibility` | implementado |
| TC-28-06 | `test_cortex_ui` | implementado |
| TC-28-07 | `test_network_watcher_ui` | implementado |
| TC-28-08 | `test_api_ui` | implementado |
| TC-28-09 | `test_docs_site_ui` | implementado |
| TC-28-10 | `test_web_management_ui` | implementado |
| TC-28-11 | `test_misp_ui` | implementado |
| TC-28-12 | `test_all_ui_accessibility` | implementado |
| TC-28-13 | `test_shuffle_frontend_renders` | implementado |
| TC-28-14 | `test_thehive_login_page_renders` | implementado |
| TC-28-15 | `test_grafana_kpi_dashboard_renders_panels` | implementado |
| TC-28-16 | `test_cortex_ui_renders` | implementado |
| TC-28-17 | `test_port_surface_inventory` | implementado |
| TC-28-18 | `test_all_uis_render_and_capture` | implementado |
| TC-28-19 | `test_web_management_soar_panel_present` | implementado |
| TC-28-20 | `test_web_management_authenticated_capture` | implementado |
| TC-28-21 | `test_all_pages_captured` | implementado |
| TC-28-22 | `test_wcag_aa_audit` | implementado |
| TC-28-23 | `test_document_language_declared` | implementado |
| TC-28-24 | `test_nonempty_title` | implementado |
| TC-28-25 | `test_single_h1_and_ordered_headings` | implementado |
| TC-28-26 | `test_landmark_regions_present` | implementado |
| TC-28-27 | `test_images_have_alt_text` | implementado |
| TC-28-28 | `test_form_controls_labeled` | implementado |
| TC-28-29 | `test_responsive_viewport_meta` | implementado |
| TC-28-30 | `test_owned_pages_have_no_gate_violations` | implementado |
| TC-28-31 | `test_audit_renders_document` | implementado |
| TC-28-32 | `test_vendor_pages_audited_informational` | implementado |

**Subtests existentes**: 32

## TC-29 — nota: **9.0**

- **Positivos**: Límites payload
- **Negativos**: ±1B exacto, chunked, zip bomb, parcial
- **Deuda**: E2E-SIZE-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-29-01 | `test_mitre_attack_mapping` | implementado |
| TC-29-02 | `test_mass_evidence_upload` | implementado |
| TC-29-03 | `test_nginx_size_limit` | implementado |
| TC-29-04 | `test_cortex_large_artifact` | implementado |
| TC-29-05 | `test_checksum_validation` | implementado |
| TC-29-06 | `test_chunked_transfer_encoding_bounded` | implementado |
| TC-29-07 | `test_gzip_bomb_class_body_bounded` | implementado |
| TC-29-08 | `test_nested_zip_like_attachment_bounded` | implementado |

**Subtests existentes**: 8

## TC-30 — nota: **9.0**

- **Positivos**: Air-gap/DNS parcial
- **Negativos**: DNS selectivo, NXDOMAIN, lento, stale, CRL/OCSP
- **Deuda**: E2E-AIR-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-30-01 | `test_air_gapped_mode` | implementado |
| TC-30-02 | `test_internet_failure_simulation` | implementado |
| TC-30-03 | `test_offline_recovery` | implementado |

**Subtests existentes**: 3

## TC-31 — nota: **9.0**

- **Positivos**: MITRE/STIX
- **Negativos**: Catálogo versionado, revocadas, D3FEND
- **Deuda**: E2E-COMP-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-31-01 | `test_mitre_attack_mapping` | implementado |
| TC-31-02 | `test_d3fend_mapping_full` | implementado |
| TC-31-03 | `test_audit_trail_compliance` | implementado |
| TC-31-04 | `test_regulatory_compliance` | implementado |
| TC-31-05 | `test_mitre_mapping` | implementado |
| TC-31-06 | `test_d3fend_mapping` | implementado |
| TC-31-07 | `test_audit_trail` | implementado |
| TC-31-08 | `test_closure_report` | implementado |
| TC-31-09 | `test_containment_endpoint_success` | implementado |
| TC-31-10 | `test_containment_endpoint_validation_error` | implementado |
| TC-31-11 | `test_containment_endpoint_default_mode` | implementado |
| TC-31-12 | `test_catalog_versioned_and_wellformed` | implementado |
| TC-31-13 | `test_no_rule_uses_deprecated_technique` | implementado |
| TC-31-14 | `test_every_tagged_technique_in_versioned_catalog` | implementado |
| TC-31-15 | `test_every_used_technique_has_d3fend_coverage` | implementado |
| TC-31-16 | `test_technique_tag_format_is_stix_attack_pattern` | implementado |

**Subtests existentes**: 16

## TC-32 — nota: **9.5**

- **Positivos**: Certificación integral
- **Negativos**: Timeline/salto, run_id isolation
- **Deuda**: Diferencial PR vs nightly
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-32-01 | `test_golden_thread_integrity` | implementado |
| TC-32-02 | `test_end_to_end_data_flow` | implementado |
| TC-32-03 | `test_health_matrix` | implementado |
| TC-32-04 | `test_full_remediation_cycle` | implementado |
| TC-32-05 | `test_ioc_analysis_time` | implementado |

**Subtests existentes**: 5

## TC-33 — nota: **9.5**

- **Positivos**: Vectores ampliados, dominio válido
- **Negativos**: Cache firmado offline de muestras
- **Deuda**: TEST-SEC-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-33-01 | `test_download_and_hash_all_samples` | implementado |
| TC-33-02 | `test_malicious_hash_ioc` | implementado |
| TC-33-03 | `test_pulsar_rat_hash` | implementado |
| TC-33-04 | `test_c2_url_ioc` | implementado |
| TC-33-05 | `test_c2_domain_ioc` | implementado |
| TC-33-06 | `test_c2_ip_ioc` | implementado |
| TC-33-07 | `test_telegram_ioc` | implementado |
| TC-33-08 | `test_registry_persistence` | implementado |
| TC-33-09 | `test_mitre_mapping` | implementado |
| TC-33-10 | `test_multi_ioc_alert` | implementado |

**Subtests existentes**: 10

## TC-34 — nota: **10**

- **Positivos**: Webhook contract ejemplar
- **Negativos**: Algoritmo no permitido, idempotencia post-ventana
- **Deuda**: E2E-REPLAY-001
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-34-01 | `test_valid_admission` | implementado |
| TC-34-02 | `test_rejected_status` | implementado |
| TC-34-03 | `test_rejected_no_side_effects` | implementado |
| TC-34-04 | `test_replay_idempotent` | implementado |
| TC-34-05 | `test_secret_not_leaked_to_logs` | implementado |
| TC-34-06 | `test_rate_limited` | implementado |
| TC-34-07 | `test_matrix_completeness` | implementado |

**Subtests existentes**: 7

## TC-35 — nota: **10**

- **Positivos**: Grafana PNG real 17/17, datasources
- **Negativos**: Visual regression, datasource lento
- **Deuda**: —
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-35-01 | `test_delivered_alert_visible_in_loki` | implementado |
| TC-35-02 | `test_elasticsearch_exporter_scraped` | implementado |
| TC-35-03 | `test_no_rule_stuck_in_error_state` | implementado |
| TC-35-04 | `test_error_query_excludes_observability_stack` | implementado |
| TC-35-05 | `test_grafana_health_database_ok` | implementado |
| TC-35-06 | `test_all_dashboards_provisioned` | implementado |
| TC-35-07 | `test_all_datasources_resolve` | implementado |
| TC-35-08 | `test_every_panel_renders_real_png` | implementado |
| TC-35-09 | `test_es_terms_agg_returns_multiple_buckets` | implementado |
| TC-35-10 | `test_loki_recent_logs_nonzero` | implementado |
| TC-35-11 | `test_contact_point_provisioned` | implementado |
| TC-35-12 | `test_notification_policy_routes_to_webhook` | implementado |
| TC-35-13 | `test_grafana_alert_webhook_accepts_notification` | implementado |
| TC-35-14 | `test_prometheus_targets_up` | implementado |
| TC-35-15 | `test_alert_rules_provisioned_and_evaluating` | implementado |
| TC-35-16 | `test_spanmetrics_p99_resolves` | implementado |
| TC-35-17 | `test_all_panels_have_descriptions` | implementado |

**Subtests existentes**: 17

## TC-KPI-01 — nota: **9.0**

- **Positivos**: MTTR real tras fix epoch
- **Negativos**: run_id window, muestras
- **Deuda**: calc_mttr neg fix
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-KPI-01-01 | `test_mttr_calculation` | implementado |

**Subtests existentes**: 1

## TC-KPI-02 — nota: **9.0**

- **Positivos**: Detección medida
- **Negativos**: Aislar Locust
- **Deuda**: KPI-007
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-KPI-02-01 | `test_kpi_dashboard` | implementado |
| TC-KPI-02-02 | `test_mttr_percentiles` | implementado |
| TC-KPI-02-03 | `test_run_scoped_query_excludes_ambient_load` | implementado |
| TC-KPI-02-04 | `test_formal_numerator_denominator_success_rate` | implementado |
| TC-KPI-02-05 | `test_mttr_numerator_excludes_zero_mttr_docs` | implementado |

**Subtests existentes**: 5

## TC-KPI-03 — nota: **9.0**

- **Positivos**: Contención medida
- **Negativos**: Div/0 guardada
- **Deuda**: —
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-KPI-03-01 | `test_kpi_alerts` | implementado |

**Subtests existentes**: 1

## TC-KPI-04 — nota: **9.0**

- **Positivos**: Precisión FP/TP
- **Negativos**: Reclasificación (ver TC-02)
- **Deuda**: —
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-KPI-04-01 | `test_mttr_percentiles` | implementado |
| TC-KPI-04-02 | `test_service_success_rates_by_alert_type` | implementado |

**Subtests existentes**: 2

## TC-KPI-05 — nota: **9.0**

- **Positivos**: Disponibilidad/SLI
- **Negativos**: no-data≠0 verificado
- **Deuda**: —
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-KPI-05-01 | `test_node_timings` | implementado |
| TC-KPI-05-02 | `test_service_success_rates_by_alert_type` | implementado |

**Subtests existentes**: 2

## TC-KPI-06 — nota: **9.0**

- **Positivos**: Cobertura/saturación
- **Negativos**: Numerador/denominador formal
- **Deuda**: KPI-007
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-KPI-06-01 | `test_shuffle_thehive_coherence` | implementado |
| TC-KPI-06-02 | `test_elasticsearch_opensearch_coherence` | implementado |
| TC-KPI-06-03 | `test_loki_workflow_coherence` | implementado |
| TC-KPI-06-04 | `test_cross_system_metric_coherence` | implementado |
| TC-KPI-06-05 | `test_cortex_analyzer_success_rate` | implementado |
| TC-KPI-06-06 | `test_misp_api_functional` | implementado |
| TC-KPI-06-07 | `test_workflow_notification_rate` | implementado |
| TC-KPI-06-08 | `test_workflow_aborted_rate` | implementado |
| TC-KPI-06-09 | `test_cortex_analyzer_images_available` | implementado |

**Subtests existentes**: 9

## TC-36 — nota: **8.6**

- **Positivos**: 5/5 opensearch/loki/grafana/ES/redis down
- **Negativos**: Bulk parcial, ACK-pre-persist, dedup, índice incompatible, falsos ceros
- **Deuda**: RES-001/002 ext.
- **Bugs**: GC keyword bug fix

| # | Subtest | Estado |
|---|---|---|
| TC-36-01 | `test_loki_unavailable_pipeline_survives` | implementado |
| TC-36-02 | `test_opensearch_down_bounded_failure_then_recovers` | implementado |
| TC-36-03 | `test_grafana_down_zero_functional_impact` | implementado |
| TC-36-04 | `test_elasticsearch_down_bounded_then_recovers` | implementado |
| TC-36-05 | `test_redis_down_bounded_then_recovers` | implementado |
| TC-36-06 | `test_bulk_partial_failure_reports_per_item` | implementado |
| TC-36-07 | `test_incompatible_index_mapping_rejected_bounded` | implementado |
| TC-36-08 | `test_reingested_duplicate_alert_dedupes_by_id` | implementado |
| TC-36-09 | `test_metrics_absent_does_not_read_as_zero` | implementado |

**Subtests existentes**: 9

## TC-37 — nota: **8.0**

- **Positivos**: 2/2 pause→hang, CPU-starved→terminal
- **Negativos**: Netem real, partición, mem pressure, kill-en-commit
- **Deuda**: RES-004 netem
- **Bugs**: —

| # | Subtest | Estado |
|---|---|---|
| TC-37-01 | `test_thehive_frozen_bounded_hang` | implementado |
| TC-37-02 | `test_cortex_cpu_starved_workflow_survives` | implementado |
| TC-37-03 | `test_netem_delay_250ms_bounded` | implementado |
| TC-37-04 | `test_netem_packet_loss_10pct_bounded` | implementado |
| TC-37-05 | `test_netem_jitter_delay_bounded` | implementado |
| TC-37-06 | `test_netem_partition_fails_bounded_then_recovers` | implementado |
| TC-37-07 | `test_no_orphan_qdisc_after_degradation` | implementado |
| TC-37-08 | `test_netem_duplication_bounded` | implementado |
| TC-37-09 | `test_netem_reorder_bounded` | implementado |
| TC-37-10 | `test_unilateral_partition_egress_drop` | implementado |
| TC-37-11 | `test_netem_corruption_bounded` | implementado |
| TC-37-12 | `test_netem_bandwidth_ceiling_bounded` | implementado |
| TC-37-13 | `test_netem_asymmetric_one_direction_only` | implementado |
| TC-37-14 | `test_qdisc_gone_after_all_faults` | implementado |

**Subtests existentes**: 14

## TC-38 — nota: **9.0**

- **Positivos**: 3/3 zombie→ABORTED quirúrgico+idempotente
- **Negativos**: Estados timeout, métricas stuck/oldest, timeout/nodo
- **Deuda**: RES-003
- **Bugs**: Bug GC real fix

| # | Subtest | Estado |
|---|---|---|
| TC-38-01 | `test_gc_aborts_only_stale_executing` | implementado |
| TC-38-02 | `test_gc_idempotent_double_pass` | implementado |
| TC-38-03 | `test_no_zombie_executing_older_than_stale_window` | implementado |
| TC-38-04 | `test_timeout_state_machine_audit_trail` | implementado |
| TC-38-05 | `test_late_result_is_reconciled_not_clobbered` | implementado |
| TC-38-06 | `test_cancelling_forced_abort_after_max_confirms` | implementado |
| TC-38-07 | `test_timeout_metrics_exposed_on_prometheus_endpoint` | implementado |
| TC-38-08 | `test_node_durations_bounded_observed` | implementado |

**Subtests existentes**: 8

## TC-39 — nota: **9.1**

- **Positivos**: 5/5 canary, backup, skew, key-sync
- **Negativos**: Bordes tolerancia, replay/nonce, DST, multi-artefacto
- **Deuda**: E2E-REPLAY-001
- **Bugs**: LogQL fix

| # | Subtest | Estado |
|---|---|---|
| TC-39-01 | `test_clock_skew_bounded` | implementado |
| TC-39-02 | `test_real_secret_never_leaks_to_loki` | implementado |
| TC-39-03 | `test_shuffle_env_key_still_valid` | implementado |
| TC-39-04 | `test_corrupt_backup_rejected_before_touching_files` | implementado |
| TC-39-05 | `test_missing_checksum_sidecar_still_verifies_tar` | implementado |
| TC-39-06 | `test_detection_time_now_mttr_positive_and_bounded` | implementado |
| TC-39-07 | `test_future_detection_time_clamps_mttr_to_zero` | implementado |
| TC-39-08 | `test_timezone_offset_instant_equivalent_to_z` | implementado |
| TC-39-09 | `test_replay_same_alert_id_bounded_no_corruption` | implementado |

**Subtests existentes**: 9

## TC-40 — nota: **8.7**

- **Positivos**: 5/5 TLS/watermark/analyzer/MISP/anonymous
- **Negativos**: Cert expirado/mTLS, analyzer obligatorio, disk físico
- **Deuda**: PKI-001 restante
- **Bugs**: MISP attr fix

| # | Subtest | Estado |
|---|---|---|
| TC-40-01 | `test_tls_untrusted_ca_rejected` | implementado |
| TC-40-02 | `test_es_readonly_watermark_clear_block` | implementado |
| TC-40-03 | `test_analyzer_job_bounded_terminal_state` | implementado |
| TC-40-04 | `test_misp_ioc_pull_push_roundtrip` | implementado |
| TC-40-05 | `test_anonymous_requests_rejected_everywhere` | implementado |
| TC-40-06 | `test_coexistence_window_two_keys_valid` | implementado |
| TC-40-07 | `test_stale_key_rejected_after_revocation` | implementado |
| TC-40-08 | `test_rotation_repeatable_and_propagatable` | implementado |
| TC-40-09 | `test_bounded_filesystem_exists` | implementado |
| TC-40-10 | `test_disk_full_fails_fast_then_recovers` | implementado |
| TC-40-11 | `test_partial_artifact_never_passes_integrity` | implementado |
| TC-40-12 | `test_expired_certificate_rejected` | implementado |
| TC-40-13 | `test_not_yet_valid_certificate_rejected` | implementado |
| TC-40-14 | `test_incomplete_chain_rejected` | implementado |
| TC-40-15 | `test_revoked_certificate_rejected_via_crl` | implementado |
| TC-40-16 | `test_mtls_client_cert_trust_contract` | implementado |
| TC-40-17 | `test_empty_observable_guarded_nodes_workflow_finishes` | implementado |
| TC-40-18 | `test_malformed_observable_bounded_not_hung` | implementado |
| TC-40-19 | `test_mandatory_decision_spine_always_present` | implementado |
| TC-40-20 | `test_misp_key_rotated_while_workflow_in_flight` | implementado |

**Subtests existentes**: 20

## TC-41 — nota: **9.1**

- **Positivos**: 6/6 TAXII real medallion end-to-end
- **Negativos**: Paginación, added_after, /versions, rate-limit
- **Deuda**: E2E-MISP-001 ext.
- **Bugs**: Accept taxii+json

| # | Subtest | Estado |
|---|---|---|
| TC-41-01 | `test_taxii_discovery_and_api_root` | implementado |
| TC-41-02 | `test_taxii_pull_seeded_collection` | implementado |
| TC-41-03 | `test_taxii_push_then_pull_back` | implementado |
| TC-41-04 | `test_taxii_malformed_bundle_rejected` | implementado |
| TC-41-05 | `test_taxii_anonymous_rejected` | implementado |
| TC-41-06 | `test_taxii_feed_into_misp` | implementado |
| TC-41-07 | `test_pagination_limit_and_next` | implementado |
| TC-41-08 | `test_added_after_incremental_sync` | implementado |
| TC-41-09 | `test_pagination_respects_match_id_filter` | implementado |
| TC-41-10 | `test_versions_endpoint_lists_object_history` | implementado |
| TC-41-11 | `test_burst_requests_consistent_and_bounded` | implementado |
| TC-41-12 | `test_anonymous_burst_uniformly_rejected` | implementado |

**Subtests existentes**: 12


**Total subtests catalogados: 445**
