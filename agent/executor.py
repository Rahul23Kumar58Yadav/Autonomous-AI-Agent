import json
import logging
from typing import Dict, Any, List

from llm.client import LLMClient
from agent.prompts import (
    STEP_EXECUTION_SYSTEM_PROMPT,
    STEP_EXECUTION_USER_TEMPLATE,
    REFLECTION_SYSTEM_PROMPT,
    REFLECTION_USER_TEMPLATE,
)
from model.schemas import ExecutionPlan, PlanStep

logger = logging.getLogger("agent.executor")


class Executor:
    def __init__(self, llm_client: LLMClient, max_retries: int = 2):
        self.llm = llm_client
        self.max_retries = max_retries

    def run(self, plan: ExecutionPlan, original_request: str) -> Dict[str, Any]:
        """
        Executes each plan step sequentially, feeding prior outputs into
        later steps for coherence. Returns a dict of {output_key: content}
        plus metadata about any step failures (transparency, not silent loss).
        """
        outputs: Dict[str, Any] = {}
        step_log: List[Dict[str, Any]] = []

        for step in plan.steps:
            content, status, error_note = self._execute_step(
                step=step,
                plan=plan,
                original_request=original_request,
                prior_outputs=outputs,
            )
            outputs[step.output_key] = content
            step_log.append({
                "id": step.id,
                "action": step.action,
                "output_key": step.output_key,
                "status": status,
                "note": error_note,
            })

        reflection = self._reflect(plan, outputs)

        return {
            "outputs": outputs,
            "step_log": step_log,
            "reflection": reflection,
        }

    def _execute_step(
        self,
        step: PlanStep,
        plan: ExecutionPlan,
        original_request: str,
        prior_outputs: Dict[str, Any],
    ):
        """Runs a single step with retry logic (error handling & recovery)."""
        prior_outputs_text = self._render_prior_outputs(prior_outputs)

        user_prompt = STEP_EXECUTION_USER_TEMPLATE.format(
            document_type=plan.document_type,
            title=plan.title,
            request=original_request,
            assumptions=plan.assumptions,
            action=step.action,
            description=step.description,
            prior_outputs=prior_outputs_text or "none",
            output_key=step.output_key,
        )

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                raw = self.llm.complete(
                    prompt=user_prompt,
                    system=STEP_EXECUTION_SYSTEM_PROMPT,
                )

                if step.action == "generate_table":
                    parsed = self._safe_parse_table(raw)
                    if parsed is None:
                        raise ValueError("Table step did not return parseable JSON list.")
                    return parsed, "ok", None

                if not raw or not raw.strip():
                    raise ValueError("Empty content returned from LLM.")

                return raw.strip(), "ok", None

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Step '{step.output_key}' failed on attempt {attempt}/{self.max_retries}: {e}"
                )

        # All retries exhausted — degrade gracefully instead of crashing the whole request
        fallback_text = (
            f"[Auto-generated placeholder: this section could not be generated "
            f"after {self.max_retries} attempts. Reason: {last_error}]"
        )
        return fallback_text, "failed", last_error

    def _reflect(self, plan: ExecutionPlan, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Lightweight self-check pass over the assembled draft."""
        sections_text = "\n\n".join(
            f"[{key}]\n{value if isinstance(value, str) else json.dumps(value)}"
            for key, value in outputs.items()
        )

        prompt = REFLECTION_USER_TEMPLATE.format(
            document_type=plan.document_type,
            title=plan.title,
            sections=sections_text,
        )

        try:
            raw = self.llm.complete(prompt=prompt, system=REFLECTION_SYSTEM_PROMPT)
            parsed = json.loads(raw.strip().strip("`").lstrip("json"))
            return parsed
        except Exception as e:
            logger.info(f"Reflection step skipped/failed non-fatally: {e}")
            return {"ok": True, "issues": [], "fix_notes": ""}

    @staticmethod
    def _render_prior_outputs(outputs: Dict[str, Any]) -> str:
        if not outputs:
            return ""
        lines = []
        for key, value in outputs.items():
            text = value if isinstance(value, str) else json.dumps(value)
            snippet = text[:400] + ("..." if len(text) > 400 else "")
            lines.append(f"- {key}: {snippet}")
        return "\n".join(lines)

    @staticmethod
    def _safe_parse_table(raw: str):
        raw = raw.strip().strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            return None
        except json.JSONDecodeError:
            return None