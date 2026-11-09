# Playbooks as code (IR2)

Shuffle workflow definitions exported from the running stack. This
directory is the **GitOps source of truth**: playbook changes are
reviewable diffs, and a `make reset` no longer loses the response logic.

## Playbooks

| File | Workflow | Containment |
|---|---|---|
| `soar-ransomware-response-*.json` | `SOAR-Ransomware-Response` | Supervised: posts to `/api/v1/contain` only when `decision=contain` |
| `soar-ransomware-response-observeonly-*.json` | `SOAR-Ransomware-Response-ObserveOnly` | Never: `containment_observe` records the verdict as its node result |

The observe-only variant (SOAR-01) runs the **identical**
detect→enrich→decide pipeline but replaces the containment node with a
pure audit action (no network calls). It carries **no webhook trigger**
— it runs manually or as a subflow, so it cannot steal the SIEM hook and
double-fire alongside the supervised playbook. Use it for
safe-by-default deployments; promote to the full playbook to enable
containment.

## Export

```bash
make export-playbooks   # or:
python scripts/maintenance/export_workflows.py --out playbooks
```

Files are named `<slug>-<workflow_id8>.json`, deterministic order
(`sort_keys`), so re-exports only diff when the playbook really changed.

## Regenerating the observe-only variant

The variant is derived from the base export — never edit it by hand:

```bash
# 1. Generate the draft (deterministic id, webhook stripped — its
#    trigger-fed branches are pruned so the start node stays parentless)
python scripts/maintenance/gen_observe_only_playbook.py \
    --base playbooks/soar-ransomware-response-efbccc68.json \
    --out /tmp/observe_only_draft.json

# 2. Import into Shuffle (POST /api/v1/workflows — backend assigns the id)

# 3. Re-export so this directory mirrors what Shuffle actually runs
python scripts/maintenance/export_workflows.py --out playbooks
```

## Restore / sync

After `make reset`: re-create the workflow in Shuffle from the exported
JSON (Shuffle API `POST /api/v1/workflows` accepts the same document —
minus server-assigned fields like `id`, `org_id`, `created`), then
`make init-webhook` to re-wire the webhook URL.
