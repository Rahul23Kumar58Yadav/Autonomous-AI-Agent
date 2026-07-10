

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from model.schemas import AgentRequest, AgentResponse
from llm.client import LLMClient
from agent.planner import Planner
from agent.executor import Executor
from agent.memory import ConversationMemory
from docgen.docx_builder import DocxBuilder

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("main")

app = FastAPI(
    title="Autonomous Document Agent",
    description="Accepts a natural language request, plans its own execution, "
                 "runs each step, and returns a generated Word document.",
    version="1.0.0",
)

# --- Wire up dependencies once at startup (simple singleton pattern; fine at this scale) ---
llm_client = LLMClient()
planner = Planner(llm_client)
executor = Executor(llm_client)
memory = ConversationMemory()
docx_builder = DocxBuilder()


@app.get("/")
def root():
    return {
        "service": "autonomous-document-agent",
        "status": "ok",
        "endpoints": ["POST /agent", "GET /agent/download/{filename}"],
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/agent", response_model=AgentResponse)
def run_agent(payload: AgentRequest):
    """
    Main autonomous agent entrypoint.
    """
    request_text = payload.request.strip()
    session_id = payload.session_id or "default"

    # --- Guardrail: basic request validation beyond pydantic's min_length ---
    if len(request_text.split()) < 3:
        raise HTTPException(
            status_code=422,
            detail="Request is too short/vague for the agent to plan against. "
                   "Please provide more detail about what document you need.",
        )

    logger.info(f"[session={session_id}] Received request: {request_text}")

    # --- Step 1: Pull prior context for this session (conversation memory) ---
    context = memory.get_context(session_id)
    if context:
        logger.info(f"[session={session_id}] Using prior context ({len(context)} chars).")

    # --- Step 2: Autonomous planning ---
    try:
        plan = planner.create_plan(request_text, context=context)
    except Exception as e:
        logger.error(f"Planning failed entirely: {e}")
        raise HTTPException(status_code=500, detail=f"Agent failed to create a plan: {e}")

    logger.info(
        f"[session={session_id}] Plan created — type='{plan.document_type}', "
        f"steps={len(plan.steps)}"
    )

    # --- Step 3: Execute the plan ---
    try:
        result = executor.run(plan, original_request=request_text)
    except Exception as e:
        logger.error(f"Execution failed entirely: {e}")
        raise HTTPException(status_code=500, detail=f"Agent failed during execution: {e}")

    outputs = result["outputs"]
    step_log = result["step_log"]
    reflection = result["reflection"]

    failed_steps = [s for s in step_log if s["status"] == "failed"]
    if failed_steps:
        logger.warning(f"[session={session_id}] {len(failed_steps)} step(s) degraded to fallback content.")

    # --- Step 4: Build the Word document ---
    try:
        doc_path = docx_builder.build(
            document_type=plan.document_type,
            title=plan.title,
            assumptions=plan.assumptions,
            outputs=outputs,
            step_log=step_log,
        )
    except Exception as e:
        logger.error(f"Document generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent failed to generate document: {e}")

    # --- Step 5: Update conversation memory for this session ---
    memory.add_turn(
        session_id=session_id,
        request=request_text,
        assumptions=plan.assumptions,
        document_type=plan.document_type,
        title=plan.title,
    )

    # --- Step 6: Build response message ---
    message = _build_summary_message(plan, step_log, reflection, failed_steps)

    return AgentResponse(
        message=message,
        document_type=plan.document_type,
        title=plan.title,
        assumptions=plan.assumptions,
        task_list=plan.steps,
        document_path=doc_path,
    )


@app.get("/agent/download/{filename}")
def download_document(filename: str):
    """
    Serves a previously generated .docx file for download.
    Path traversal guardrail: only allow filenames that exist directly
    inside outputs/, never accept nested paths.
    """
    safe_name = os.path.basename(filename)
    filepath = os.path.join("outputs", safe_name)

    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Document not found.")

    return FileResponse(
        path=filepath,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=safe_name,
    )


def _build_summary_message(plan, step_log, reflection, failed_steps) -> str:
    parts = [
        f"Generated a {plan.document_type} titled '{plan.title}' "
        f"using {len(plan.steps)} autonomously planned steps."
    ]

    if plan.assumptions:
        parts.append(f"The agent made {len(plan.assumptions)} assumption(s) to resolve ambiguity in the request.")

    if failed_steps:
        parts.append(
            f"Note: {len(failed_steps)} step(s) fell back to placeholder content after retries failed."
        )

    if reflection and not reflection.get("ok", True):
        issues = reflection.get("issues", [])
        if issues:
            parts.append(f"Self-review flagged {len(issues)} issue(s): {', '.join(issues[:3])}.")

    return " ".join(parts)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)