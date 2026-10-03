"""Session Memory Manager for conversation history and checkpointing."""

from __future__ import annotations
import threading
from typing import Any, Dict, List


class SessionMemoryManager:
    """Thread-safe in-memory session store with Redis adapter hook."""

    def __init__(self, redis_client: Any | None = None):
        self.redis_client = redis_client
        self._store: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._store.get(session_id, []))

    def append_turn(self, session_id: str, user_query: str, response: str, metadata: dict[str, Any] | None = None) -> None:
        with self._lock:
            if session_id not in self._store:
                self._store[session_id] = []
            turn = {
                "turn": len(self._store[session_id]) + 1,
                "user": user_query,
                "response": response,
                "metadata": metadata or {},
            }
            self._store[session_id].append(turn)

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(session_id, None)
