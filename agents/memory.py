
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any


class ConversationMemory:
    def __init__(self, max_turns_per_session: int = 6):
        self._store: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.max_turns_per_session = max_turns_per_session

    def add_turn(
        self,
        session_id: str,
        request: str,
        assumptions: List[str],
        document_type: str,
        title: str,
    ) -> None:
        turn = {
            "timestamp": datetime.utcnow().isoformat(),
            "request": request,
            "assumptions": assumptions,
            "document_type": document_type,
            "title": title,
        }
        self._store[session_id].append(turn)
        # Trim to keep prompt context bounded
        if len(self._store[session_id]) > self.max_turns_per_session:
            self._store[session_id] = self._store[session_id][-self.max_turns_per_session:]

    def get_context(self, session_id: str) -> str:
        """Render prior turns as a compact text block for prompt injection."""
        turns = self._store.get(session_id, [])
        if not turns:
            return ""

        lines = []
        for i, t in enumerate(turns, start=1):
            lines.append(
                f"Turn {i} — request: \"{t['request']}\" | "
                f"doc_type: {t['document_type']} | title: {t['title']} | "
                f"assumptions: {t['assumptions']}"
            )
        return "\n".join(lines)

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def has_history(self, session_id: str) -> bool:
        return bool(self._store.get(session_id))