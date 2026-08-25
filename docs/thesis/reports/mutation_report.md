# Mutation Testing Report (mutmut)

Generated: **2026-08-22 21:55:05 UTC**
Environment: Docker container `soar_api` (f5f8300a8c12)
Source mutated: `src/soar_lab/`

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Mutation Score** | **0%** |
| **Status** | **Critical** |
| Total mutants | 0 |
| Killed | 0 |
| Survived | 0 |
| Timeout | 0 |
| Suspicious | 0 |
| Skipped | 0 |

### Score interpretation

| Score | Status | Meaning |
|-------|--------|---------|
| 90-100 | Excellent | Tests catch almost all mutations |
| 80-89 | Good | Tests catch most mutations |
| 70-79 | Acceptable | Some gaps in test coverage |
| 60-69 | Medium risk | Notable gaps in test quality |
| 50-59 | High risk | Significant test quality issues |
| 0-49 | Critical | Tests fail to catch most mutations |

## Mutant Status Breakdown

| Status | Count | Percentage | Description |
|--------|-------|------------|-------------|
| 🎉 Killed | 0 | - | - |
| 🙁 Survived | 0 | - | - |

## Surviving Mutants (Detailed)

No surviving mutants found. All mutations were killed by the test suite.

## Configuration

Mutmut configuration from `pyproject.toml`:

```toml
[tool.mutmut]
paths_to_mutate = ["src/soar_lab/"]
do_not_mutate = ["__init__.py", "scripts/", "tests/"]
runner_command = "python -m pytest -x -q --tb=no -m 'not requires_docker and not requires_external' --ignore=tests/e2e --ignore=tests/atomic"
```

## Recommendations


## How to reproduce

```bash
# Inside the Docker container (soar_api):
# mutmut is installed via pyproject.toml [project.optional-dependencies] quality
python -m mutmut run
python -m mutmut results
python -m mutmut show all

# Or from the host:
make mutation
```
