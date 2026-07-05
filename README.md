# CEDX Tiny Agent Fleet - Recruitment and Staffing

## 1. Industry & Scope (+tier, CASE_ID)

Industry: Recruitment and Staffing. Tier: governed staffing operations package for intake, exception handling, approval, and delivery.

`CASE_ID` is `CEDX-681ACE` by default and can still be overridden with the environment for grading experiments.

## 2. Agent topology (roster + contracts + file pointers)

The fleet has four separable agents:

- `orchestrator` in `cedx_fleet/orchestrator.py`: owns run state, routing, budgets, audit, and delivery refusal.
- `router` in `cedx_fleet/agents/router.py`: chooses `gpt-4o-mini` for easy records and `gemini-1.5-flash` for hard/escalated records by default. This is easy to swap through the Router agent.
- `staffing_worker` in `cedx_fleet/agents/worker.py`: creates structured Recruitment and Staffing delivery fields.
- `verifier` in `cedx_fleet/agents/verifier.py`: independently checks Worker output against source fields and can overrule it.

Typed contracts live in `cedx_fleet/contracts.py`. The agent roster is emitted into `out/audit.json`.

## 3. How to Run

```bash
make demo
make verify
```

The default path is offline replay: `REPLAY_LLM=true`. To run against another seed:

```bash
SEED_DIR=/path/to/seed CASE_ID=CEDX-681ACE make demo
```

## 4. Controls

The required controls are wired through the Makefile:

- `make trace ID=REC-001`
- `make replay ID=REC-001`
- `make eval`
- `make probe-approval`
- `make probe-agent-failure`
- `make probe-budget`
- `make probe-append-only`
- `make probe-idempotency`

## 5. Planted-problem handling (data + agent layer)

Data layer:

- `STALE`: deadline earlier than `PIPELINE_NOW`.
- `MISSING_INPUT`: required field is missing or null.
- `OUTLIER`: robust statistical outlier using MAD/IQR, not record IDs.
- `INJECTION_BLOCKED`: direct instruction to bypass rules, approve, or skip review.
- `LOW_CONFIDENCE`: ambiguous category or contradictory notes.
- `UNVERIFIED_ANOMALY`: validation conflict that does not match a known detector.
- `SCHEMA_DRIFT`: non-blocking mapping such as `Value` to `amount`.
- `SUPERSEDED_VERSION`: lower version retained as superseded while latest proceeds.

Agent layer:

- `AGENT_HALLUCINATION`: Verifier finds source-unsupported fields.
- `AGENT_MALFORMED`: Worker output is structurally invalid.
- `BUDGET_EXCEEDED`: cost or step ceiling is exceeded.
- `AGENT_LOOP`: represented by the same step-budget kill path.

## 6. Generalization

The detectors use dates, required-field validation, schema mapping, robust statistics, and text patterns. They do not match seed record IDs or fixed seed values. Unknown validation failures route to `UNVERIFIED_ANOMALY` instead of being silently delivered. In real-online mode, an optional LLM note classifier can provide a second opinion for ambiguous note text while the offline path stays fully local.

## 7. LLM/agent contract & eval

`REPLAY_LLM=true` generates deterministic transcript files in `transcripts/` and hashes each Worker response. Delivered fields in `out/audit.json` hash back to the Worker transcript. Before any request is sent to a real model, the JSON-like Worker payload is converted locally into compact TOON-style text to reduce prompt tokens. `REPLAY_LLM=false` calls an OpenAI-compatible endpoint or the Gemini generateContent endpoint depending on the model name. The current default router policy uses `gpt-4o-mini` for easy records and `gemini-1.5-flash` for hard/escalated records.

Optional real-LLM note classifier:

- `USE_LLM_NOTE_CLASSIFIER=true` enables an LLM second opinion for note-based text categorization only when `REPLAY_LLM=false`.
- `NOTE_CLASSIFIER_MODEL` can be set separately from the Worker model if you want a cheaper classifier.

`make eval` prints a 10-case golden harness summary and per-agent scores.

## 8. Cost & scale

The demo currently reports cost in `out/audit.json`. On the provided seed it is about `$0.0014` total in replay-priced accounting. Real provider pricing may differ, but the router keeps clean records on the cheap model and reserves the stronger model for hard/escalated tasks.

## 9. Amendment

At startup the fleet prints:

```text
AMENDMENT: role=<role> threshold=<threshold>
```

For `CEDX-681ACE`, the amendment is `role=compliance` and `threshold=40000`. Records at or above the threshold require compliance approval in addition to normal approval before delivery.

## 10. AI usage / real-vs-faked

AI tools were used to build the implementation. The fleet itself still has real separable agents, explicit contracts, replayable transcripts, Verifier overrule behavior, budget handling, and audit evidence. Intake, normalization, detectors, approval, audit, trace, replay, and probes are not stubbed.

## 11. Tradeoffs & next week

This submission favors a reliable CLI over a UI. Next improvements would be durable SQLite state, richer real-LLM transcript capture, parallel record processing, crash-resume checkpoints, and a small operator web view for approvals.
