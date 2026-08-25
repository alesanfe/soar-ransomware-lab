#!/usr/bin/env python3
"""Configure Elasticsearch index templates for single-node deployment.

Sets number_of_replicas=0 for all SOAR-related indices.
"""

import logging
import os
import sys
import time

import requests

logger = logging.getLogger(__name__)

DEFAULT_ES_URL = os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200")
DEFAULT_ES_WAIT_TIMEOUT = 4
DEFAULT_ES_WAIT_RETRIES = 24


def get_auth():
    """Return Basic Auth tuple from environment when security is enabled."""
    user = os.environ.get("ELASTIC_USERNAME", "elastic")
    password = os.environ.get("ELASTIC_PASSWORD", "")
    if user and password:
        return (user, password)
    return None


def main():
    es_url = os.environ.get("ES_URL", DEFAULT_ES_URL)
    auth = get_auth()

    # Wait for Elasticsearch to be ready
    logger.info("Waiting for Elasticsearch to be ready...")
    for i in range(DEFAULT_ES_WAIT_RETRIES):
        try:
            r = requests.get(
                f"{es_url}/_cluster/health", auth=auth, timeout=DEFAULT_ES_WAIT_TIMEOUT
            )
            if r.status_code == 200:
                logger.info(f"Elasticsearch ready after {i * 5}s")
                break
        except Exception as _e:
            logging.debug("ES not ready yet: %s", _e)
        time.sleep(5)
    else:
        logger.error("ERROR: Elasticsearch not ready after 120s")
        sys.exit(1)

    # Create index template for replicas=0 and fast writes
    # NOTE: refresh_interval MUST be short (1s, the ES default) because
    # TheHive/Cortex use refresh=wait_for on index operations.  With
    # refresh_interval=30s, ES can take up to 30s to respond, which
    # exactly matches the Apache HttpAsyncClient socket timeout (30s)
    # and causes SocketTimeoutException on every write.
    logger.info("Creating index template for replicas=0 and fast writes...")
    tpl = {
        "index_patterns": ["shuffle*", "the_hive*", "cortex*", "soar*"],
        "settings": {
            "number_of_replicas": 0,
            "refresh_interval": "1s",
            "translog.durability": "request",
        },
    }
    r = requests.put(f"{es_url}/_template/soar_no_replicas", auth=auth, json=tpl)
    logger.info(f"[ES template] {r.status_code} {r.text[:80]}")

    # Pre-create index template for Shuffle's environments index with
    # explicit field mappings.  Shuffle's backend sorts by `created`
    # immediately after creating the index, but with dynamic mapping
    # the field doesn't exist until the first document is indexed,
    # causing "No mapping found for [created]" (HTTP 400) errors.
    logger.info("Creating index template for environments* (pre-map fields)...")
    env_tpl = {
        "index_patterns": ["environments*"],
        "settings": {
            "number_of_replicas": 0,
            "refresh_interval": "1s",
            "translog.durability": "request",
        },
        "mappings": {
            "dynamic_templates": [
                {"strings_as_keywords": {"match_mapping_type": "string", "mapping": {"type": "keyword"}}}
            ],
            "properties": {
                "Name": {"type": "keyword"},
                "Registered": {"type": "boolean"},
                "Type": {"type": "keyword"},
                "archived": {"type": "boolean"},
                "created": {"type": "long"},
                "edited": {"type": "long"},
                "default": {"type": "boolean"},
                "id": {"type": "keyword"},
                "org_id": {"type": "keyword"},
                "orborus_uuid": {"type": "keyword"},
                "running_ip": {"type": "keyword"},
                "run_type": {"type": "keyword"},
                "sensor_group": {"type": "keyword"},
            },
        },
    }
    r = requests.put(f"{es_url}/_template/soar_environments", auth=auth, json=env_tpl)
    logger.info(f"[ES env template] {r.status_code} {r.text[:80]}")

    # Pre-create index template for Shuffle's workflowqueue index with
    # explicit field mappings.  Shuffle's Orborus sorts by `priority`
    # immediately after creating the index, causing "No mapping found
    # for [priority]" (HTTP 400) errors during startup.
    logger.info("Creating index template for workflowqueue* (pre-map fields)...")
    wq_tpl = {
        "index_patterns": ["workflowqueue*"],
        "settings": {
            "number_of_replicas": 0,
            "refresh_interval": "1s",
            "translog.durability": "request",
        },
        "mappings": {
            "dynamic_templates": [
                {"strings_as_keywords": {"match_mapping_type": "string", "mapping": {"type": "keyword"}}}
            ],
            "properties": {
                "authgroup": {"type": "keyword"},
                "authorization": {"type": "keyword"},
                "created_at": {"type": "long"},
                "environments": {"type": "keyword"},
                "execution_argument": {"type": "text"},
                "execution_id": {"type": "keyword"},
                "execution_source": {"type": "keyword"},
                "priority": {"type": "long"},
                "start": {"type": "long"},
                "status": {"type": "keyword"},
                "type": {"type": "keyword"},
                "workflow_id": {"type": "keyword"},
            },
        },
    }
    r = requests.put(f"{es_url}/_template/soar_workflowqueue", auth=auth, json=wq_tpl)
    logger.info(f"[ES wq template] {r.status_code} {r.text[:80]}")

    # Set default search timeout to 60s (prevents TheHive SocketTimeoutException)
    # NOTE: disabled — this setting does NOT affect /_cluster/health/{index}
    # which has its own 30s timeout. The real fix is pre-creating indices.
    # print("Setting search.default_search_timeout=60s...")
    # r = requests.put(
    #     f"{es_url}/_cluster/settings",
    #     auth=auth,
    #     json={"persistent": {"search.default_search_timeout": "60s"}},
    # )
    # print(f"[ES search timeout] {r.status_code} {r.text[:80]}")

    # Update existing indices
    logger.info("Updating existing indices to replicas=0 and fast writes...")
    indices = requests.get(f"{es_url}/_cat/indices?h=index", auth=auth).text.split()
    for idx in indices:
        if idx:
            try:
                requests.put(
                    f"{es_url}/{idx}/_settings",
                    auth=auth,
                    json={
                        "index": {
                            "number_of_replicas": 0,
                            "refresh_interval": "1s",
                            "translog.durability": "request",
                        }
                    },
                )
                logger.info(f"  Updated {idx}")
            except Exception as e:
                logger.error(f"  Failed to update {idx}: {e}")

    # Also disable replicas on OpenSearch indices (Shuffle backend uses OS)
    os_url = os.environ.get("SHUFFLE_OPENSEARCH_URL", "http://opensearch:9200")
    logger.info(f"Disabling replicas on OpenSearch ({os_url})...")
    try:
        os_indices = requests.get(f"{os_url}/_cat/indices?h=index", timeout=15).text.split()
        for idx in os_indices:
            if idx:
                try:
                    requests.put(
                        f"{os_url}/{idx}/_settings",
                        json={"index": {"number_of_replicas": 0, "refresh_interval": "1s"}},
                        timeout=15,
                    )
                    logger.info(f"  OS Updated {idx}")
                except Exception as e:
                    logger.warning(f"  OS Failed to update {idx}: {e}")
    except Exception as e:
        logger.warning(f"Could not connect to OpenSearch: {e}")

    # Pre-create TheHive and Cortex indices to prevent 30s timeouts on
    # /_cluster/health/{index} when the index does not exist yet.
    # ES 7.x waits up to 30s for a non-existent index's health check,
    # which causes elastic4s SocketTimeoutException in TheHive/Cortex.
    #
    # CRITICAL: elastic4play (TheHive/Cortex) uses `term` queries to look up
    # API keys, passwords, user names, etc.  `term` queries only match
    # `keyword` fields, NOT `text` fields.  If we let ES auto-create the
    # mapping with dynamic templates, string fields default to `text` with a
    # `.keyword` sub-field — but elastic4play queries the base field name
    # (e.g. `key`, not `key.keyword`), so the `term` query silently fails and
    # authentication returns 401.
    #
    # The fix: use a dynamic_template that maps ALL string fields to `keyword`
    # by default.  elastic4play will update the mapping with the correct
    # `text` fields (title, description, summary, etc.) when it first writes,
    # but those updates only ADD new field mappings — they don't conflict with
    # the keyword template because elastic4play uses explicit `properties`
    # for text fields.
    #
    # CRITICAL #2: The `relations` field MUST be mapped as type `join` with
    # the correct parent-child relations.  elastic4play's DBCreate.scala sets
    # `relations` to either a string (for parent docs: `relations: "case"`)
    # or an object (for child docs: `relations: {name: "case_task", parent:
    # "abc123"}`).  If `relations` is mapped as `keyword` (which the
    # dynamic_template would do), indexing child documents fails with
    # `mapper_parsing_exception: Can't get text on a START_OBJECT`.
    # The relations were extracted from the TheHive 3.5.2 and Cortex 3.2.0
    # JAR files by decompiling the ModelDef/ChildModelDef classes.
    logger.info("Pre-creating TheHive and Cortex indices...")

    # TheHive 3.5.2 relations (from ES template + decompiled model classes):
    #   case        -> [dummy-case, case_task, case_artifact]
    #   case_task   -> [case_task_log, dummy-case_task]
    #   case_task_log -> [dummy-case_task_log]
    #   alert       -> [dummy-alert]
    #   audit       -> [dummy-audit]
    #   user        -> [dummy-user]
    #   caseTemplate -> [dummy-caseTemplate]
    #   dashboard   -> [dummy-dashboard]
    #   sequence    -> [dummy-sequence]
    #   datastore   -> [dummy-datastore]
    #   dblist      -> [dblistitem, dummy-dblist]
    thehive_relations = {
        "case": ["dummy-case", "case_task", "case_artifact"],
        "case_task": ["case_task_log", "dummy-case_task"],
        "case_task_log": ["dummy-case_task_log"],
        "alert": ["dummy-alert"],
        "audit": ["dummy-audit"],
        "user": ["dummy-user"],
        "caseTemplate": ["dummy-caseTemplate"],
        "dashboard": ["dummy-dashboard"],
        "sequence": ["dummy-sequence"],
        "datastore": ["dummy-datastore"],
        "dblist": ["dblistitem", "dummy-dblist"],
    }

    # Cortex 3.2.0 relations (from decompiled model classes):
    #   organization -> [dummy-organization, worker]
    #   job          -> [dummy-job, report]
    #   report       -> [artifact]
    #   audit        -> [dummy-audit]
    #   user         -> [dummy-user]
    #   sequence     -> [dummy-sequence]
    #   datastore    -> [dummy-datastore]
    #   dblist       -> [dummy-dblist]
    cortex_relations = {
        "organization": ["dummy-organization", "worker"],
        "job": ["dummy-job", "report"],
        "report": ["artifact"],
        "audit": ["dummy-audit"],
        "user": ["dummy-user"],
        "sequence": ["dummy-sequence"],
        "datastore": ["dummy-datastore"],
        "dblist": ["dummy-dblist"],
    }

    pre_indices = {
        "the_hive_17": thehive_relations,
        "cortex_6": cortex_relations,
    }
    for idx_name, relations in pre_indices.items():
        try:
            r = requests.head(f"{es_url}/{idx_name}", auth=auth, timeout=5)
            if r.status_code == 404:
                r = requests.put(
                    f"{es_url}/{idx_name}",
                    auth=auth,
                    json={
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0,
                            "mapping.total_fields.limit": 2000,
                            "index.mapping.nested_fields.limit": 100,
                        },
                        "mappings": {
                            "dynamic": True,
                            "dynamic_templates": [
                                {
                                    "strings_as_keyword": {
                                        "match_mapping_type": "string",
                                        "mapping": {
                                            "type": "keyword",
                                            "ignore_above": 512,
                                        },
                                    }
                                }
                            ],
                            "properties": {
                                "createdAt": {"type": "date"},
                                "createdBy": {"type": "keyword"},
                                "updatedAt": {"type": "date"},
                                "updatedBy": {"type": "keyword"},
                                # Text fields that elastic4play expects to be
                                # searchable as full text
                                "title": {
                                    "type": "text",
                                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                                },
                                "description": {"type": "text"},
                                "summary": {"type": "text"},
                                "message": {"type": "text"},
                                # The `relations` field is the elastic4play
                                # join field.  It MUST be type `join` with the
                                # correct parent-child relations, otherwise
                                # indexing child documents fails with
                                # mapper_parsing_exception.
                                "relations": {
                                    "type": "join",
                                    "relations": relations,
                                },
                            },
                        },
                    },
                    timeout=10,
                )
                logger.info(f"  Created {idx_name}: {r.status_code}")
            else:
                logger.info(f"  {idx_name} already exists")
        except Exception as e:
            logger.error(f"  Failed to pre-create {idx_name}: {e}")

    logger.info("Elasticsearch configuration complete")


if __name__ == "__main__":
    main()
