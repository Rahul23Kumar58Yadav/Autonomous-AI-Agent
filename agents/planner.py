import json
import logging
from typing import Optional

from llm.client import LLMClient
from agent.prompts import PLANNER_SYSTEM_PROMPT, PLANNER_USER_TEMPLATE
from model.schemas import ExecutionPlan

logger = logging.getLogger("agent.planner")


class Planner:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def create_plan(self, request: str, context: str = "") -> ExecutionPlan:
       
        prompt = PLANNER_USER_TEMPLATE.format(request=request, context=context or "none")

        raw_output = self.llm.complete(
            prompt=prompt,
            system=PLANNER_SYSTEM_PROMPT,
        )

        plan_dict = self._safe_parse_json(raw_output)

        if plan_dict is None:
            logger.warning("Planner LLM output was not valid JSON. Using fallback plan.")
            plan_dict = self._fallback_plan(request)

        try:
            plan = ExecutionPlan(**plan_dict)
        except Exception as e:
            logger.warning(f"Plan failed schema validation ({e}). Using fallback plan.")
            plan = ExecutionPlan(**self._fallback_plan(request))

        return plan

    @staticmethod
    def _safe_parse_json(raw: str) -> Optional[dict]:
        raw = raw.strip()
        # Strip accidental markdown fences if the model adds them anyway
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Attempt to salvage the JSON object substring
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start:end + 1])
                except json.JSONDecodeError:
                    return None
            return None

    @staticmethod
    def _fallback_plan(request: str) -> dict:
        """Deterministic safety-net plan when the LLM planning step fails."""
        return {
            "document_type": "business report",
            "title": "Generated Document",
            "assumptions": [
                "Request could not be parsed into a specific structure; "
                "using a generic business report format."
            ],
            "steps": [
                {
                    "id": 1,
                    "action": "clarify_assumptions",
                    "description": f"Interpret and structure the raw request: {request}",
                    "output_key": "assumptions_note",
                },
                {
                    "id": 2,
                    "action": "draft_section",
                    "description": "Write an executive summary of the request.",
                    "output_key": "executive_summary",
                },
                {
                    "id": 3,
                    "action": "draft_section",
                    "description": "Write the main body content addressing the request.",
                    "output_key": "main_content",
                },
                {
                    "id": 4,
                    "action": "review_and_refine",
                    "description": "Review the draft for completeness and tone.",
                    "output_key": "review_notes",
                },
            ],
        }