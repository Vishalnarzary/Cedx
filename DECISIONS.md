# Decisions

## Industry

I chose Recruitment and Staffing because the generic work requests map naturally to staffing operations: onboarding, renewals, reviews, reports, and intake packages. The delivery artifact is a governed staffing package rather than a financial report.

## What I did not automate

I did not build a browser UI. The assessment accepts a CLI, and the highest-risk areas are agent boundaries, approval refusal, append-only audit behavior, traceability, and probes. A UI would add surface area without improving those gates.

I also did not silently repair Class-A problems. Stale deadlines, missing input, prompt injection, outliers, low confidence, unknown anomalies, and agent failures route to the exception queue.

## Thresholds

Outliers use robust statistics. The detector combines MAD-based robust z-score and IQR fencing. This avoids hardcoding the seed value `250000` and still generalizes to held-out batches with different magnitudes.

Low confidence is used for invalid categories and contradictory notes. Unknown conflicts, such as notes contradicting a structured amount without matching a known safe resolution, route to `UNVERIFIED_ANOMALY`.

## Router policy

The router uses the model policy :

- Easy tasks: `gpt-4o-mini`.
- Hard or escalated tasks: `gemini-1.5-flash`.

A record is hard if it already has a non-blocking reason such as schema drift, has high value, or contains notes suggesting correction, partner-feed handling, side letters, or inconsistency. Blocking records do not go to Worker assembly.

## Cost and scale

The run records estimated tokens, cost, and latency per span. On the provided seed, replay accounting produces about `$0.0015` total cost and about `$0.65` per 10,000 records. At real scale, the first pressure point would be sequential processing and single-file audit writes. The next step would be SQLite/Postgres state, partitioned audit files, and batch/parallel Worker calls.

Worker requests are converted from JSON-like Python dictionaries into compact TOON-style prompt text before real model calls. The JSON structure is still kept inside transcripts for auditability, but the model sees the shorter TOON representation.

For the weaker text-only note detectors, the code now supports an optional LLM second opinion in real-online mode. This is disabled in replay mode so the offline Docker path remains fully local and deterministic.

## Provenance

Each delivered record stores:

- source version hash
- Worker transcript hash
- delivered fields hash
- agent trace
- approval trail
- append-only event log entries

`verify_audit.py` confirms delivered fields hash back to Worker transcripts.

## CASE_ID

`CASE_ID` is `CEDX-681ACE`. The amendment computed from this value is `compliance@40000`. The value can still be overridden through the environment for grader experiments.
