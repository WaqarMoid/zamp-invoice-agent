# 00 · Index and phase reading map

**Rule: read only what the current phase lists.** Each doc says at its top which phases need it. Do not read the whole `docs/` folder up front. Seed JSON files are data, not instructions: read them with a script or `head`, never paste them whole into context.

| Doc | Topic |
|---|---|
| 01_CONTEXT_AND_ASSUMPTIONS | The assignment, the fictional company, assumptions, out of scope |
| 02_PROCESS_MAP | Flow diagram, decision points, edge cases |
| 03_ARCHITECTURE | Stack, versions, repo layout, env vars, coding standards |
| 04_DATA_MODEL | Tables, domain models, serialisation |
| 05_SEED_AND_FIXTURES | Seed data, PDF fixture generator, golden files |
| 06_EXTRACTION | LLM extraction, prompt, fallback, accuracy eval |
| 07_PIPELINE_AND_RULES | Stages, checks, thresholds, decision logic, expected results (**source of truth**) |
| 08_API_CONTRACT | Endpoints, SSE, TypeScript types |
| 09_UI_UX_SPEC | Design system, components, pages |
| 10_TESTING | Unit, golden, API, frontend tests |
| 11_DEPLOYMENT | GitHub, Neon, Render, Vercel |
| 12_DEMO_SCRIPT | Video and interview run order |

## Phases

| Phase | Goal | Read | Exit criteria (all must hold) |
|---|---|---|---|
| **P0 Bootstrap** | Repo skeleton runs | 01, 03, 02 §2.2 skim | `git init -b main` done; folders per 03 §3.3; backend `/api/health` returns ok locally; Vite app shows an empty AppShell placeholder; `.gitignore`, `.env.example` files; first commit |
| **P1 Data layer** | DB + seed + utils | 04, 05 §5.1-5.2, 07 §7.4.0, 10 §10.1 (money, gstin, text, dates) | Tables create on SQLite; seed loads; `/api/vendors` and `/api/purchase-orders` return data matching 05 §5.2; unit tests for money/gstin/text/dates green |
| **P2 Fixtures** | 9 invoice PDFs + golden JSON | 05 §5.3-5.6 | 05 §5.6 acceptance met; PNG previews of F01, F03, F05, F07 inspected and described in PROGRESS.md |
| **P3 Extraction** | LLM reading works | 06 | `eval_extraction.py` 100% on critical fields for F01-F09; model ID recorded; cache works (second run `cached=true`) |
| **P4 Pipeline & rules** | Decisions correct | 02, 07 (all), 04 §4.3-4.4, 10 §10.1-10.2 | Every golden test and sequence test passes; `reports/golden_results.md` written |
| **P5 API & streaming** | Contract complete | 08 | 08 §8.5 curl checks pass, outputs pasted into PROGRESS.md; `test_api.py` green |
| **P6 Frontend** | Graded UI | 09 (per sub-phase), 08 §8.4 | 09 §9.12 checklist all ticked |
| 6a | Tokens, fonts, shell, components | 09 §9.0-9.7 | Component gallery page `/__gallery` (dev only) shows every component and state |
| 6b | Dashboard | 09 §9.8.1 | |
| 6c | Process invoice | 09 §9.8.2 | |
| 6d | Run detail live view | 09 §9.8.3, §9.9 | |
| 6e | Purchase orders | 09 §9.8.4 | |
| 6f | Rules | 09 §9.8.5 | |
| 6g | Responsive, a11y, polish | 09 §9.10-9.12 | |
| **P7 Hardening** | Everything tested | 10 | 10 §10.6 |
| **P8 Deploy** | Public links | 11 | 11 §11.5 all verified; URLs in README |
| **P9 Demo prep** | Rehearsed | 12 | `DEMO_CHECKLIST.md` written; full run order executed on production without errors |

After P9: rewrite `README.md` for reviewers (what it does, live link, how to run, architecture diagram from 02, edge case table, assumptions from 01, test commands, next steps). Keep it under 250 lines.
