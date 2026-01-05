# newsbot Hardening Report
**Date:** 2025-11-11  
**Branch:** `chore/hardening-mvp`

## Overview

This iteration focused on improving reliability, security, and observability for the newsbot MVP while enabling safer automation. Enhancements spanned API retries, asynchronous summarization, SSRF-resistant collection, prompt externalization, smoke testing, and CI improvements. All changes are tracked on branch `chore/hardening-mvp`.

## Reliability & Cost Controls

- Added `tenacity`-based retry decorators (`src/utils/retry.py`) for both LLM calls and WordPress publishing. Retries cover timeouts, 429s, and 5xx responses with exponential backoff (≤5 attempts, max wait 30s).
- Introduced `MAX_ARTICLES_PER_RUN` and `MAX_TOKENS_PER_RUN` env gates, enforced before/within summarization to avoid runaway cost.
- Reworked `summarize_articles` (now async + `ThreadPoolExecutor`) to process up to **5 articles concurrently** while capturing failures and token estimates in `SummarizationResult`.

## Security Hardening

- Created `config/allowlist.txt` and enforced HTTPS-only crawling with domain allowlisting and DNS-IP validation (`src/collect.py`). Any resolution to private/loopback/link-local networks is rejected up front, protecting against SSRF vectors.
- Added comprehensive tests for allowlist loading and validator edge cases (`tests/test_collect.py`).

## Prompt Management

- Externalized compose/summarize system & user prompts into `prompts/<feature>/<role>/<variant>.txt`.
- Added `src/prompts.py` loader with LRU caching, variant fallback (`PROMPT_VARIANT`), and templated rendering (`render_prompt`).
- Updated summarization and composition flows to consume file-based prompts, enabling A/B experimentation without code changes.

## Testing & Fixtures

- Extended unit coverage for summarization token budgeting and failure accounting (`tests/test_summarize.py`).
- Added `tests/test_e2e_smoke.py` plus deterministic RSS/article fixtures. This smoke test mocks feed parsing, article extraction, LLM output, and WordPress responses (via `responses`) to assert end-to-end behavior, including the final POST payload and persisted draft.
- Added prompt loader tests (`tests/test_prompts.py`) to ensure variant fallback safety.

## CI/CD Improvements

- GitHub Actions now runs `make lint` and `pytest -q` across a Python **3.10 / 3.11** matrix with pip caching (`.github/workflows/newsbot.yml`).
- Artifacts now capture `out/draft.md` instead of the root-level draft to align with the new output directory.

## Observability & UX

- Logging can emit structured JSON (`JSON_LOGS=true`). A finishing metrics line reports processed counts, failures, token estimates, WP publish status, and total duration. Example:  
  ```json
  {"run_metrics":{"articles_collected":2,"articles_after_limit":2,"summaries_generated":2,"summaries_failed":0,"tokens_estimated":1200,"token_limit_reached":false,"wordpress_published":true,"duration_seconds":8.42}}
  ```
- Drafts (success or failure) are written to `out/draft.md`. The save helper ensures directories exist, making CI artifacts and local inspection consistent.
- README/.env.sample updated with new knobs (allowlist path, prompt variant, JSON logs, draft path, cost caps) and operation notes.

## Verification

- `pip install --break-system-packages -r requirements.txt`
- `make test` → `34 passed`
- `DRY_RUN=true python3 main.py` (fails intentionally without RSS feeds but exercises draft persistence + metrics logging)

## Residual Considerations

- Allowlist maintenance: operators must keep `config/allowlist.txt` current with trusted domains and HTTPS endpoints.
- Async summarization still uses threadpool + blocking clients; migrating to native async SDKs would reduce thread usage and improve cancellation.
- Cost ceilings rely on heuristic token estimation; integrating model-specific tokenization would improve accuracy for tighter budgets.

The codebase is now substantially more resilient against flaky integrations, malicious feeds, and operational blind spots, preparing it for higher-throughput or automated deployments.
