#!/usr/bin/env python3
"""Fix missing org user id/apikey in Elasticsearch organizations index.

After a fresh Shuffle deploy the org document may contain an empty user stub
(id='', apikey=''). Shuffle's GetApikey() then tries GET /users/_doc/ (no id)
and gets HTTP 405, making the backend unhealthy and blocking workflow execution.
This helper links the stub to the real admin user in the 'users' index.
"""
import base64
import requests


def fix_organization_users(es_url, es_user, es_pass, verify=False):
    """Populate missing id/apikey/username in organizations.users from users index."""
    auth = base64.b64encode(f"{es_user}:{es_pass}".encode()).decode() if es_user and es_pass else None
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Basic {auth}"

    try:
        usr_r = requests.get(f"{es_url}/users/_search?size=100", headers=headers, timeout=10, verify=verify)
        users = usr_r.json().get("hits", {}).get("hits", []) if usr_r.status_code == 200 else []
        if not users:
            print("  [org-fix] No users found in users index, skipping")
            return

        org_r = requests.get(f"{es_url}/organizations/_search?size=20", headers=headers, timeout=10, verify=verify)
        if org_r.status_code != 200:
            print(f"  [org-fix] No organizations index: {org_r.status_code}")
            return

        fixed = 0
        for org_hit in org_r.json().get("hits", {}).get("hits", []):
            org_id = org_hit["_id"]
            org_src = org_hit["_source"]
            changed = False

            for u in org_src.get("users", []):
                if u.get("id") and u.get("apikey") and u.get("username"):
                    continue

                match = None
                for hit in users:
                    src = hit["_source"]
                    uid = src.get("id", hit["_id"])
                    if uid == u.get("id") or src.get("username") == u.get("username"):
                        match = src
                        break

                    active_org_id = src.get("active_org", {}).get("id") or src.get("active_org", {}).get("org_id", "")
                    if org_id in (active_org_id, src.get("active_org", {}).get("org_id", "")) or org_id in (
                        src.get("orgs") or []):
                        if src.get("role") == "admin" or "admin" in (src.get("roles") or []):
                            match = src
                            break

                if match:
                    u["id"] = match.get("id", u.get("id"))
                    u["username"] = match.get("username", u.get("username"))
                    u["apikey"] = match.get("apikey", u.get("apikey"))
                    u["verified"] = match.get("verified", u.get("verified", False))
                    u["role"] = match.get("role", u.get("role", "admin"))
                    u["roles"] = match.get("roles", u.get("roles", ["admin"]))
                    u["active"] = match.get("active", u.get("active", True))
                    u["creation_time"] = match.get("creation_time", u.get("creation_time", 0))
                    u["Password"] = match.get("Password", u.get("Password", ""))
                    u["active_org"] = match.get("active_org", u.get("active_org", {}))
                    u["orgs"] = match.get("orgs", u.get("orgs", []))
                    u["limits"] = match.get("limits", u.get("limits", {}))
                    u["executions"] = match.get("executions", u.get("executions", {}))
                    changed = True
                    print(f"  [org-fix] User {u['username']} ({u['id'][:8]}) linked to org {org_id[:8]}")

            if not org_src.get("creator_id"):
                for hit in users:
                    src = hit["_source"]
                    if src.get("role") == "admin" or "admin" in (src.get("roles") or []):
                        org_src["creator_id"] = src.get("id", hit["_id"])
                        changed = True
                        break

            if changed:
                pr = requests.put(f"{es_url}/organizations/_doc/{org_id}", headers=headers, json=org_src, timeout=10,
                                  verify=verify)
                if pr.status_code in (200, 201):
                    fixed += 1
                else:
                    print(f"  [org-fix] Error updating org {org_id}: {pr.status_code}")

        if fixed:
            print(f"  [org-fix] {fixed} org(s) fixed")
        else:
            print("  [org-fix] org users already have id/apikey")
    except Exception as e:
        print(f"  [org-fix] Error: {e}")


if __name__ == "__main__":
    import os

    fix_organization_users(
        os.environ.get("ES_URL", "http://soar_elasticsearch:9200"),
        os.environ.get("ELASTIC_USERNAME", "elastic"),
        os.environ.get("ELASTIC_PASSWORD", ""),
    )
