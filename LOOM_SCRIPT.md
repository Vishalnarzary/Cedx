# 3-Minute Loom Script

This script is written so you can read it almost verbatim while recording.

## Before Recording

Keep these tabs or files ready:

- `README.md`
- `ARCHITECTURE.md`
- `out/audit.json`
- terminal in the project root

Recommended commands to run during the Loom:

```bash
python -m cedx_fleet.cli demo
python verify_audit.py --audit out/audit.json --transcripts transcripts --schema audit.schema.json
python -m cedx_fleet.cli trace --id REC-001
python -m cedx_fleet.cli probe-agent-failure
```

If `python` is not available on your machine path, use the interpreter command that works in your setup.

## Script

### 0:00 - 0:20 | Intro

Say:

"Hi, this is my CEDX agent fleet submission for the Recruitment and Staffing workflow. The main goal of this system is to take intake records from a JSON feed plus email and PDF inbox sources, normalize them, block bad records, generate a branded staffing output, verify that output independently, and then deliver it with a full audit trail."

### 0:20 - 0:55 | Show Architecture

Open `ARCHITECTURE.md`.

Say:

"The important architectural choice here is that this is controller-led. The Orchestrator owns the run loop and decides how each record moves. It calls three other agent roles: Router, Worker, and Verifier."

"The Router chooses which model to use. The Worker drafts the structured Recruitment and Staffing output. Then the Verifier independently checks the Worker output against the source record and can overrule it. That agent-checks-agent step is one of the most important parts of the system."

"I also separate agents from helpers. Intake, detectors, review, audit, and LLM formatting are pipeline helpers, but the real agent roster emitted into the audit is orchestrator, router, staffing_worker, and verifier."

### 0:55 - 1:25 | Explain Record Flow

Point to the runtime flow in `ARCHITECTURE.md`.

Say:

"A clean record goes through intake, version selection, detection, routing, worker drafting, verifier review, approval gating, and then delivery. A bad record never reaches delivery. If detectors find a blocking issue like stale data, missing input, injection attempts, outliers, or low confidence, the Orchestrator sends it directly to the exception queue."

"For my case amendment, `CEDX-681ACE`, records at or above 40,000 require a second approver role, which is compliance. So even a good Worker and Verifier result still cannot be delivered unless the approval state is valid."

### 1:25 - 1:50 | Run Demo

In terminal run:

```bash
python -m cedx_fleet.cli demo
```

Say:

"Now I’m running the full demo end to end."

After it completes, say:

"On the current seed, this run produces 23 total records: 15 delivered, 7 exceptions, and 1 superseded version. It also writes the intake snapshot, exception queue, delivery package, transcripts, and final audit."

### 1:50 - 2:10 | Show Audit

Open `out/audit.json`.

Say:

"This audit is the main evidence bundle. It contains the agent roster, case amendment, cost summary, append-only event log, and per-record traces. For delivered records, the normal trace order is orchestrator, router, staffing_worker, and verifier."

"You can also see the amendment here: role compliance, threshold 40,000, tied to case ID CEDX-681ACE."

### 2:10 - 2:30 | Verify Audit

In terminal run:

```bash
python verify_audit.py --audit out/audit.json --transcripts transcripts --schema audit.schema.json
```

Say:

"This command validates the audit bundle against the grading-style checks. It confirms the schema, the multi-agent roster, the verifier presence, approval trail, transcript linkage, costs, and append-only event shape."

### 2:30 - 2:45 | Show One Trace

In terminal run:

```bash
python -m cedx_fleet.cli trace --id REC-001
```

Say:

"This lets me inspect one record path. Instead of just saying the agents exist, I can show the actual trace spans, selected model, verifier verdict, and details for a specific record."

### 2:45 - 2:58 | Show Failure Handling

In terminal run:

```bash
python -m cedx_fleet.cli probe-agent-failure
```

Say:

"This probe demonstrates that the Verifier catches bad Worker behavior. If the Worker hallucinates fields or returns malformed output, the system routes that record to exception instead of silently delivering it."

### 2:58 - 3:05 | Close

Say:

"So the key idea in this system is not just generating outputs, but governing them: controlled orchestration, explicit exception handling, verifier override, approval enforcement including the case amendment, and a replayable audit trail."

## Short Backup Version

If you need a faster version, say:

"This is a controller-led multi-agent fleet for Recruitment and Staffing. The Orchestrator runs the workflow, the Router selects the model, the Worker drafts the output, and the Verifier independently checks it before delivery. Blocking issues go to the exception queue, high-value records require the extra compliance approval for my case amendment, and every run produces a replayable audit with per-agent traces, transcripts, cost, and events."

