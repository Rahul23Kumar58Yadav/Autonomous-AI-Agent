# Autonomous Document Agent

An autonomous AI agent that takes a natural language request, independently plans
its execution steps, runs them, self-reviews its own output, and produces a
polished Microsoft Word (.docx) document — with conversation memory across turns.

Built for the **Python AI Engineer – Autonomous Agents – 60-Minute Build Challenge**.

---

## Overview

Send it a request like *"create a project plan for launching a mobile banking
feature"* and the agent will:

1. **Plan** — decompose the request into an ordered list of execution steps.
   No hardcoded templates; the LLM decides the plan structure per request.
2. **Execute** — run each step sequentially, feeding prior step outputs into
   later steps for coherence, with automatic retries if a step fails.
3. **Reflect** — self-review the drafted document for missing sections,
   inconsistencies, or leftover placeholder text.
4. **Generate** — render the final structured content into a polished `.docx`
   with a title page, assumptions section, formatted body, tables, and an
   execution-log appendix.

For ambiguous or conflicting requests, the agent makes reasonable assumptions
and surfaces them explicitly in the document instead of guessing silently.




| Module | Responsibility |
|---|---|
| `agent/planner.py` | Turns the request into a validated, ordered execution plan via the LLM. Falls back to a deterministic plan if the LLM output is malformed. |
| `agent/executor.py` | Runs each planned step, retries on failure, degrades gracefully to a placeholder if retries exhaust, and runs a final reflection pass. |
| `agent/memory.py` | Conversation memory across turns — the mandatory engineering improvement. |
| `agent/prompts.py` | Centralized prompt templates for planning, execution, and reflection. |
| `docgen/docx_builder.py` | Pure rendering layer — takes structured content and produces a formatted Word document. Knows nothing about the LLM. |
| `llm/client.py` | Wraps the Groq API with retry/backoff on transient failures. |
| `models/schemas.py` | Pydantic models for request/response validation. |
| `main.py` | FastAPI app exposing `POST /agent`. |

---

## Mandatory Engineering Improvement: Conversation Memory

Without memory, every `/agent` call is fully stateless — a follow-up request
like *"make it shorter"* or *"reuse the same client name"* has nothing to
anchor to. This agent stores recent turns per session (request, assumptions,
document type, title) and injects that context into the next planning call,
so multi-turn document iteration stays coherent within a session.

The storage is intentionally a simple in-memory dictionary for this scope —
the interface (`add_turn` / `get_context`) hides the storage detail, so
swapping to Redis or Postgres later is a one-file change, not a redesign.

---

## Tech Stack

- **FastAPI** — REST API framework
- **Groq (Llama 3.3 70B)** — free-tier LLM used for planning, execution, and reflection
- **python-docx** — Word document generation
- **Pydantic** — request/response validation and schema enforcement

---

## Setup

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add your GROQ_API_KEY
```

## Run

```bash
uvicorn main:app --reload
```

Interactive API docs available at `http://127.0.0.1:8000/docs`

## Test

```bash
python -m tests.test_standard_request
python -m tests.test_complex_request
```

Or run both test cases against the live server with a clean printout:

```bash
python run_demo.py
```

---

## API

**POST /agent**

Request:
```json
{ "request": "Create a project plan for launching...", "session_id": "abc123" }
```

Response includes the agent's generated task list, assumptions made, inferred
document type, and the path to the generated `.docx` file.

**GET /agent/download/{filename}**

Downloads a previously generated document by filename.

---

## Example Scenarios

**Standard request** — clear, well-specified: a 3-month mobile banking
feature launch involving engineering, design, and QA. The agent plans 6
steps and surfaces 2 clarifying assumptions.

**Complex/ambiguous request** — a client-meeting document about a payment
gateway migration, with conflicting inputs from leadership, engineering, and
finance, and no document type specified. The agent infers "project plan" as
the appropriate format on its own, and explicitly surfaces its assumptions
about the compliance deadline and budget instead of resolving the conflict
silently.

---

## Engineering Tradeoff: Autonomous Planning vs. Deterministic Workflows

The planner is fully LLM-driven rather than following a fixed template per
document type. This gives real flexibility — the same endpoint handles both
a structured project plan and a messy, ambiguous request without any
branching logic. The cost is unpredictability: LLM output can occasionally be
malformed or vary in shape between runs. This is mitigated with strict
schema validation (Pydantic) and a deterministic fallback plan, so a bad LLM
response degrades gracefully instead of crashing the request.

---

## License

MIT
---

## Architecture
