# SCOPE - tracer checkpoint

- **Candidate name:** TBD
- **CASE_ID (assigned live):** CEDX-681ACE
- **Industry chosen:** Recruitment and Staffing
- **Tier:** Governed staffing operations package
- **Stack / language:** Python CLI, deterministic replay by default

## Amendment

- **My role R:** compliance
- **My threshold T:** 40000

## What I will build

- [x] Sources/Intake (parse feed.json + inbox PDF/email)
- [x] Orchestration (declarative normalize + exception queue, all reason codes)
- [x] Assembly (LLM structured output + abstain path)
- [x] Review (operator approval state machine + CASE_ID amendment)
- [x] Delivery (branded package + append-only audit + replay)

## What I will deliberately NOT build

- A browser UI. The assessment allows a CLI, and a CLI keeps the approval, trace, and probe controls easier to audit live.
