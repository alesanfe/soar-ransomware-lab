# Reports

Generated evidence and quality reports for the SOAR Ransomware Lab.

Reports are produced by the Makefile quality/e2e targets and written under
`reports/` (gitignored). Chart assets referenced by those reports live in
this section's subdirectories:

- `e2e/charts/` — end-to-end run charts (MTTR, decision distribution, alert mix)
- `holistic/` — Holistic Project Radar artifacts
- `mutmut/` — mutation testing output
- `quality/` — static quality suite output
- `test-review/` — test review report output

Regenerate with `make test-e2e`, `make holistic-review`, `make mutation`,
`make quality`, `make test-review`.
