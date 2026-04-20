# Databricks Asset Bundle Template

A [Databricks Asset Bundle template](https://docs.databricks.com/en/dev-tools/bundles/templates.html) for data engineering projects that read from a star-schema warehouse, enrich telemetry data, and produce analytics.

**Documentation layout:** This **root `README.md`** is the canonical, GitHub-rendered handbook for the template and for how generated projects work. Repos created with `bundle init` ship a **short project `README.md`** (quick commands + pointer here) so day-to-day docs stay in one place—the template repo you init from.

## Status: experimental Sail integration

This version experiments with [LakeHQ Sail](https://github.com/lakehq/sail) as the local Spark backend for tests (in place of a JVM PySpark session). Generated projects wire `pysail` + `pyspark-client` into `tests/conftest.py` and use Python-defined fixture modules under `tests/data/` (DataFrame factories grouped into `SEED_TABLES` / `EXPECTED_OUTPUTS` / `ALL_TABLES`).

Current caveats:

- Tables written during tests (`saveAsTable`) land as **Parquet files in the local `spark-warehouse/` folder** (ignored by `.gitignore`). There is no Delta or Unity Catalog locally — anything Delta/UC-specific must be covered by Databricks integration tests.
- The fixture layer is a bespoke in-repo convention, not a shared library.

**Planned direction:** add Sail + Python-generated fixture support to [`datamole-ai/pysparkdt`](https://github.com/datamole-ai/pysparkdt) (today it targets Apache PySpark with NDJSON / JSON test data) and switch the template over to `pysparkdt` instead of the ad-hoc Sail wiring and `tests/data/` fixture convention used here.

## Quick start

```bash
databricks bundle init /path/to/dab-template
cd <project_name>
uv sync --group dev
uv run pytest tests/ -v
```

After init, set `owner` and `repository` in `cog.toml` and point `config/app.yaml` at your warehouse (`defaults.source_catalog` / `defaults.source_schema`). The generated project **README** only summarizes settings and commands; **this file** remains the full guide—keep the template repo bookmarked or vendored alongside your docs.

**Databricks CLI** (deploy, `bundle run`) needs a configured profile and network access to your workspace.

### Command cheat sheet (generated project)

```bash
uv sync --group dev
uv run pytest tests/ -v
uv run ruff check . && uv run ruff format .

databricks bundle deploy --target dev
# dev_id: required for bundle run (jobs); any unique string is fine (CI uses github.run_id)
databricks bundle run integration_test_job --target dev --params dev_id=my_run,scenario=basic
databricks bundle run <project_name>_pipeline --target dev --params dev_id=my_run
```

`load_config` derives `dev_id` from `current_user()` only for **interactive** notebook runs (no job run id). `**databricks bundle run`** starts **jobs**, so if your config uses `**{dev_id}`** placeholders you must pass `**dev_id`** (any unique string; CI uses `github.run_id`) or `load_config` raises.

## Template prompts


| Prompt             | Type   | Default       | Description                                                                               |
| ------------------ | ------ | ------------- | ----------------------------------------------------------------------------------------- |
| `project_name`     | string | `my_project`  | Package and bundle name. Lowercase, `a-z/0-9/_`, min 3 chars.                             |
| `deployment_model` | enum   | `dev_stg_prd` | `dev_prd` (dev+prd), `dev_stg_prd` (dev+stg+prd), or `dev_tst_acc_prd` (dev+tst+acc+prd). |
| `serverless`       | enum   | `yes`         | `yes` uses serverless environments; `no` uses job clusters.                               |


## What gets generated

### Pipeline

Three tasks in a single Databricks job with fan-out parallelism:

```
ingest ──┬──▶ compute_metrics
         └──▶ detect_anomalies
```

- **ingest**: Joins telemetry fact with site and device dimensions into `enriched_telemetry`.
- **compute_metrics**: Aggregates per-equipment health metrics.
- **detect_anomalies**: Rule-based threshold alerts (high temperature, high vibration).

### Demo domain

```
Source warehouse (external)        Owned pipeline output
─────────────────────────         ──────────────────────
telemetry_fact ──┐                ingestion.tables.enriched_telemetry
site_dim ────────┼─▶ enrich ───▶    │
device_dim ──────┘                   ├──▶ analytics.tables.equipment_metrics
                                     └──▶ analytics.tables.anomaly_alerts
```

**External (read-only in prod):** `telemetry_fact`, `site_dim`, `device_dim` (star schema: fact + dimensions).

**Owned:** `ingestion.tables.enriched_telemetry`; `analytics.tables.equipment_metrics`; `analytics.tables.anomaly_alerts` (rule-based thresholds).

### Configuration

Runtime catalog, schemas, and flags live in `**config/app.yaml`**: a `defaults` map plus `environments.<env>` (which envs exist depends on `deployment_model`). `**databricks.yml`** sets `config_file_path` and `env` per target; values flow into notebooks as job parameters / widgets together with optional `**dev_id**` (schema isolation) and `**scenario**` (which fixture module the integration job uses).

`**load_config(dbutils, spark)**` (defined in `notebooks/_load_config.py`, sibling-imported from every notebook) resolves merged YAML, substitutes `{dev_id}`, and finds `config/app.yaml` by walking up from the driver working directory and the notebook path (`REPO_ROOT` can override). If `dev_id` is empty but the resolved config still needs it, interactive runs may fall back to `current_user()`; **CI and shared workspaces should pass `dev_id` explicitly** (GitHub Actions uses `github.run_id`). **Job runs** (including `databricks bundle run`) must pass `**dev_id`** when the merged config contains `**{dev_id}`** — see the cheat sheet above.

### Testing pyramid

Treat development as **three complementary layers** (local → interactive Databricks → production-like job); all should converge on the same `**integration_test_job`**.

- **Local tests** ([Sail](https://github.com/lakehq/sail) + **PySpark 4.1.x** (`pyspark-client`) + [chispa](https://github.com/MrPowers/chispa); see [Sail docs](https://docs.lakesail.com/sail/latest/introduction/getting-started/)): Fast feedback for most logic work. A session-scoped Sail Spark Connect server and remote `SparkSession` (see `tests/conftest.py`) let tests run **orchestrators** end-to-end (read → transform → write) against Sail's built-in catalog; no Databricks cluster or local JDK required. `pyspark-client` keeps the dev install small (no full `pyspark` shell). **Experimental**: tables persist as **Parquet in `spark-warehouse/`** (no Delta / UC locally), and fixtures are Python-defined DataFrame factories under `tests/data/`. The plan is to move both concerns into [`datamole-ai/pysparkdt`](https://github.com/datamole-ai/pysparkdt) (Sail backend + Python fixtures) and depend on that instead — see the Status section.
- **Interactive Databricks** (notebooks + `notebooks/_bootstrap.py`): For behavior Sail cannot emulate (Unity Catalog, Delta MERGE, materialized views, Autoloader, cross-catalog reads, etc.). First notebook cell runs `%run ./_bootstrap` **alone** (keep it isolated so the job parser doesn't merge it with imports). With the **wheel** on jobs, the bootstrap is a no-op (missing wheel → `RuntimeError` with a fix hint). On Repos without the wheel, it does editable `pip install -e`, prepends `src/`, and enables autoreload — needs cluster **egress** and does **not** mirror `uv.lock`. Integration notebooks `%run ./_bootstrap` too, pointing at a **tiny** `tests/integration/_bootstrap.py` that chains `%run ../../notebooks/_bootstrap` and then adds `<repo_root>/notebooks` to `sys.path` so sibling imports of `_load_config` resolve. Entry layout: `%run ./_bootstrap` cell → imports (including `from _load_config import load_config`) → `SparkSession` + `load_config` → `run_*`.
- **Integration tests** (dev target, **wheel on cluster**): `integration_test_job` mirrors production: seed → pipeline → verify → teardown, with libraries from `resources/*.yml` — **no** `pip install -e` / `src/` for those runs. Pass `**dev_id`** (required when config uses `{dev_id}`; not auto-filled in job context) and optional `**scenario`** (default `basic`). Verify uses chispa against fixture expectations. **Cost note:** the GitHub Actions runner stays idle while `databricks bundle run` polls the remote job — you pay for runner time for the full job duration.

Pure-transform tests (DataFrame in/out only) are optional but help localize failures in multi-step logic.

**CI:** integration tests run on **non-draft** PRs to `main` (and `**release/`**** when the deployment model uses release branches), optional `**workflow_dispatch`**, and **before every deploy** via one reusable workflow; **deploy** always depends on that run. **Concurrency** uses `cancel-in-progress: false` so in-flight runs finish teardown (no orphan dev bundles).

### Deployment models


| Model             | Targets (tiers)    | Promotion                                                                                     | Tags / releases                                                        |
| ----------------- | ------------------ | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `dev_prd`         | dev, prd           | Push `main` → integration test → **prod**                                                     | Optional `v*` tag → GitHub Release only (no deploy from tag)           |
| `dev_stg_prd`     | dev, stg, prd      | Push `main` → **staging**; tag `**vX.Y.Z`** → **prod**                                        | Stable tags + changelog; **release/** hotfix branches supported        |
| `dev_tst_acc_prd` | dev, tst, acc, prd | Push `main` → **test** (subset); tag `**vX.Y.Z-rc.N`** → **acc**; tag `**vX.Y.Z`** → **prod** | Semver pre-releases + stable; GitHub Release on stable only by default |


Each target uses its own Unity Catalog name (`<project>_dev`, `<project>_staging`, `<project>_test`, `<project>_acc`, `<project>_prod` depending on `deployment_model`). **Dev** uses seeded data and per-developer schema suffixes where configured (e.g. `ingestion_<user>`). **Staging / test** (models that include them) point at the real warehouse with `TEST_SITE_IDS` in `ingestion/tables/source_tables.py`. **Acceptance / prod** use the full real catalog as configured.

`resources/variables.yml` holds bundle parameters (`config_file_path`, `env`, `service_principal_id`) — not table routing; routing stays in `config/app.yaml`.

#### Catalog names (reference)

Unity Catalog names follow `<project_name>_<env>`. Not every model defines every tier.


| Tier       | Catalog             | Used by           | Typical data                                                                                 |
| ---------- | ------------------- | ----------------- | -------------------------------------------------------------------------------------------- |
| dev        | `<project>_dev`     | all models        | Seeded fixtures; schemas often include `dev_id` / user for isolation (e.g. `ingestion_jdoe`) |
| staging    | `<project>_staging` | `dev_stg_prd`     | Real warehouse; `TEST_SITE_IDS`                                                              |
| test       | `<project>_test`    | `dev_tst_acc_prd` | Real warehouse subset (`TEST_SITE_IDS`)                                                      |
| acceptance | `<project>_acc`     | `dev_tst_acc_prd` | Full real warehouse (UAT)                                                                    |
| prod       | `<project>_prod`    | all models        | Full real warehouse                                                                          |


#### Promotion by deployment model

##### `dev_prd`

- Push to `main` → integration test → deploy **prod**.
- Optional stable tags `v*`: GitHub Release + changelog (`release.yaml`). Tags do **not** trigger deploy in this model.

##### `dev_stg_prd`

- Push to `main` → integration test → deploy **staging** (real sources, no separate UAT tier in this model).
- Tag `vX.Y.Z` → integration test → deploy **prod** + GitHub Release.
- **Hotfix:** branch `release/x.y` from the stable tag, PR into that branch (integration tests in dev), squash-merge, tag `vX.Y.Z+1`, merge the release branch back to `main` when appropriate.

##### `dev_tst_acc_prd`

- Push to `main` → integration test → deploy **test** (subset via `TEST_SITE_IDS`).
- Tag `vX.Y.Z-rc.N` (pre-release) → integration test → deploy **acceptance** (UAT).
- Tag `vX.Y.Z` (no `-rc.`) → integration test → deploy **prod** + GitHub Release. Pre-release tags skip the GitHub Release job by default (extend `release.yaml` for rc notes).
- **Hotfix:** same release-branch pattern as `dev_stg_prd`. If a `vX.Y.Z-rc.N` is in flight and `main` has diverged, use an `rc-release` branch from the rc tag, merge the hotfix release branch, re-run integration tests, then merge to `main` via PR.

### Conventional commits and cocogitto

PRs should use [Conventional Commits](https://www.conventionalcommits.org/) titles (e.g. `feat(ingestion): add site filter`); with **squash-merge**, that title becomes the single commit on `main`.

All models ship **cocogitto** via `.github/actions/setup-cocogitto`: `cog verify` on PR titles (`pr-title` job) and `cog check --from-latest-tag` on pushes (`commit-check` — needs tags configured in `cog.toml`). Set `owner` and `repository` in `cog.toml` for changelog generation. If your policy allows unverified Marketplace actions, you can swap in `cocogitto/cocogitto-action` or `amannn/action-semantic-pull-request` instead.

### Hotfix flow (`dev_stg_prd` and `dev_tst_acc_prd`)

See **Promotion by deployment model** above for the release-branch and `rc-release` patterns. In short: create `release/*` from a stable tag, fix via PR (integration tests in dev), tag a new `v*`, deploy prod, then merge back to `main` through a PR.

### GitHub Releases

`release.yaml` runs on `v*` tags: `**cog changelog`** and `**gh release create`**. In `**dev_tst_acc_prd**`, pre-release tags (`-rc.`) skip the GitHub Release job unless you change the workflow.

### Branch protection and environments (recommended)

Protect `main` (and `release/**` when your model uses release branches). Require CI checks you care about (`lint`, `test`, `validate`, `pr-title`, `commit-check`) plus **Integration Test** on PRs; use **squash merge** if you want one conventional commit per PR.

Optionally set `environment: production` (or `acceptance`) on deploy jobs and use GitHub **required reviewers** so deploy waits for approval after the workflow starts.

## Project structure (generated)

```
<project_name>/
  pyproject.toml                    # uv_build; runtime: pyyaml, chispa, databricks-sdk; dev: pysail, pyspark-client, pytest, ruff
  README.md                         # minimal; canonical docs = template root README.md
  CHANGELOG.md
  cog.toml
  .gitignore
  .github/
    actions/setup-cocogitto/action.yml
    workflows/
      ci.yaml                       # lint, test, validate, pr-title, commit-check
      deploy.yaml                   # integration test → deploy (per model)
      integration-test.yaml         # PR + dispatch → reusable workflow
      _integration-test.yaml        # reusable: deploy dev, run, destroy
      release.yaml                  # tag v* → GitHub Release + changelog
  databricks.yml                    # targets (config_file_path, env), artifacts
  config/
    app.yaml                        # multi-env runtime config (YAML)
  resources/
    variables.yml                   # config_file_path, env, service_principal_id
    pipeline_job.yml                # notebook_task (.py): ingest → [metrics, anomalies]
    integration_test_job.yml        # notebook_task (.py): seed → pipeline → verify → teardown
  notebooks/                        # production pipeline notebooks (flat)
    _bootstrap.py                   # wheel vs editable-install + autoreload
    _load_config.py                 # load_config: resolves path/widgets/dev_id → delegates to <project_name>.config
    ingest.py
    metrics.py
    anomaly.py
  src/<project_name>/                # pure Python, no Databricks deps — unit-testable locally
    config.py                       # load_yaml_config: pure YAML merge + {dev_id} substitution
    ingestion/
      enrich.py                     # enrich_telemetry (pure) + run_ingestion (orchestrator)
      tables/
        enriched_telemetry.py       # TABLE_NAME + COL_* + SCHEMA
        source_tables.py            # external table names + TEST_SITE_IDS
    analytics/
      metrics.py                    # compute_equipment_metrics + run_equipment_metrics
      anomaly_detection.py          # detect_anomalies + run_anomaly_detection
      tables/
        equipment_metrics.py        # TABLE_NAME + COL_* + SCHEMA
        anomaly_alerts.py           # TABLE_NAME + COL_* + SCHEMA
  tests/
    conftest.py                     # Sail SparkConnectServer + remote SparkSession + table fixtures
    data/
      basic.py                      # SEED_TABLES / EXPECTED_OUTPUTS / ALL_TABLES (extend with more modules)
    unit/                           # unit tests mirroring src/<project_name>/
      test_config.py
      ingestion/
        test_ingestion.py
      analytics/
        test_metrics.py
        test_anomaly_detection.py
    integration/                    # Databricks integration test notebooks (pytest ignores; no test_ prefix)
      _bootstrap.py                 # chains %run ../../notebooks/_bootstrap + puts notebooks/ on sys.path
      _load_scenario.py             # load_scenario: importlib loader for tests/data/<name>.py
      seed.py
      verify.py
      teardown.py
```

## Key design decisions

- **YAML + Databricks `.py` notebooks** — sources under `notebooks/*.py` and `tests/integration/*.py` start with `# Databricks notebook source`, call `load_config`, then **inline** calls to library orchestrators in `<project_name>.ingestion` / `<project_name>.analytics` — **no `argparse` on the cluster**.
- **Flat package + notebook-side sibling helpers** — `src/<project_name>/` holds everything that can be tested with `pytest` locally: business logic (`ingestion`, `analytics`) and pure YAML config loading (`load_yaml_config` in `<project_name>.config`). Cluster-only helpers live next to the notebooks that use them: `notebooks/_bootstrap.py` (wheel vs editable install + autoreload), `notebooks/_load_config.py` (`load_config()` — dbutils widget resolution + path discovery, delegates to `<project_name>.config.load_yaml_config`), `tests/integration/_bootstrap.py` (chains the notebook bootstrap and adds `<repo_root>/notebooks` to `sys.path` so integration notebooks can sibling-import `_load_config`), and `tests/integration/_load_scenario.py` (scenario loader for integration tests). Notebooks pick them up via sibling-absolute imports (`from _load_config import load_config`).
- **Per-table contract modules** — under `ingestion/tables/` and `analytics/tables/`: each owned (or referenced) table gets `TABLE_NAME`, `COL_*` constants, and `SCHEMA` (StructType) where applicable. Column names repeated across tables are defined **per file** so each module stays a self-contained contract.
- **Fixtures in `tests/data/`** — DataFrame factories grouped as `SEED_TABLES`, `INTERMEDIATE_TABLES`, `EXPECTED_OUTPUTS` (`expected_*` names avoid colliding with written tables), and `ALL_TABLES` for `conftest.py`. Unit tests import via `tests.data.<scenario>`; integration notebooks resolve scenarios at runtime via `from _load_scenario import load_scenario` (sibling import of `tests/integration/_load_scenario.py`, which anchors the `tests/data/` path to its own `__file__`) so fixtures are not shipped in the wheel. Add scenarios by new fixture modules (e.g. `edge_cases.py`) and `integration_test_job --params scenario=…`.
- **Sail for local tests** — Rust Spark Connect server (`pysail` + pinned `**pyspark-client`** 4.1.x per Sail’s install guide). Library code takes `**spark` as an argument** instead of `from databricks.sdk.runtime import spark`. You can retarget `tests/conftest.py` to another Connect endpoint if needed.
- **Catalog-per-environment** — separate Unity Catalog per tier; see deployment models above for dev vs subset vs full real data.
- **Single integration test job** — seed → pipeline (`run_job_task`) → verify → teardown in one job; teardown uses `run_if: ALL_DONE` for cleanup.
- **Reusable GitHub workflow** for integration tests — shared by PR checks and deploy; no `cancel-in-progress` on in-flight runs so teardown completes.
- **Serverless conditional** — `environment_key` + `environments` when serverless, `job_cluster_key` + `job_clusters` when classic.

## Extending and limitations

- **New pipeline job:** add `resources/<job>.yml`, wire a `run_job_task` from `integration_test_job.yml`, and extend `tests/integration/verify.py` plus fixtures as needed.
- **Autoloader, CDC, heavy Delta features:** implement under `ingestion/` / `analytics/` (add table contracts under `tables/` as needed) and validate with **integration tests**; Sail-backed pytest cannot fully replace a live workspace for these paths.

