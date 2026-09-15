"""
In-memory, TTL-based conversation history store for a short-lived
customer-support chatbot (small business scale, single-process deployment).

Design:
- Keyed directly by `customer_id` (Shopify's `logged_in_customer_id`
  proxy param). Only logged-in customers get conversation history;
  anonymous/guest visitors are stateless (no key to store under, so
  callers should skip get_history/add_turn entirely when customer_id
  is None/absent).
- History is capped at MAX_MESSAGES (user+assistant pairs count individually,
  so 20 messages = last 10 turns).
- Entries expire after TTL_SECONDS of inactivity; a background sweep
  removes them so memory doesn't grow unbounded.

NOTE: this is single-process only. If you ever run multiple workers/replicas,
swap the dict for Redis (same interface, TTL becomes native EXPIRE).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import TypedDict

logger = logging.getLogger(__name__)

MAX_MESSAGES = 20  # 20 messages = 10 full (user, assistant) turns
TTL_SECONDS = 120  # 2 minutes of inactivity -> thread forgotten
CLEANUP_INTERVAL_SECONDS = 60


# Serialization simplicity. HumanMessage/AIMessage are Pydantic objects — they're deque-storable fine in memory,
# but the moment you want to persist this somewhere (Redis, a DB, logging, debugging by printing the dict) we have to convert them to dicts.
# So we just store dicts in memory and may convert them to HumanMessage/AIMessage when we need to call the LLM. This is a tradeoff for simplicity and persistence.
class Message(TypedDict):
    role: str  # "user" | "assistant"
    content: str


@dataclass
class ChatEntry:
    messages: deque[Message] = field(default_factory=lambda: deque(maxlen=MAX_MESSAGES))
    last_active: float = field(default_factory=time.time)


class ChatHistoryStore:
    """
    Thread-safe in-memory store, keyed directly by customer_id.
    Callers must not call get_history/add_turn for guests (customer_id
    is None) — there is no key to store under, so skip history entirely
    for anonymous traffic at the call site.
    """

    def __init__(
        self, max_messages: int = MAX_MESSAGES, ttl_seconds: int = TTL_SECONDS
    ) -> None:
        self._store: dict[str, ChatEntry] = {}
        self._lock = Lock()
        self._max_messages = max_messages
        self._ttl_seconds = ttl_seconds

    def _is_expired(self, entry: ChatEntry) -> bool:
        return (time.time() - entry.last_active) > self._ttl_seconds

    def get_history(self, customer_id: str) -> list[Message]:
        """Returns the message list for a customer, or [] if missing/expired."""
        with self._lock:
            entry = self._store.get(customer_id)
            if entry is None:
                return []
            if self._is_expired(entry):
                del self._store[customer_id]
                logger.info(
                    "History for customer %s expired on read, dropped", customer_id
                )
                return []
            return list(entry.messages)

    def add_turn(self, customer_id: str, user_msg: str, ai_msg: str) -> None:
        """
        Adds one full turn (user message + final assistant reply).
        Call this once per request, after you have the final LLM output —
        not for intermediate/internal agent hops. Only call for logged-in
        customers (customer_id must not be None/empty).
        """
        with self._lock:
            entry = self._store.get(customer_id)

            # fresh customer, or previous entry expired -> start clean
            if entry is None or self._is_expired(entry):
                entry = ChatEntry(messages=deque(maxlen=self._max_messages))
                self._store[customer_id] = entry

            entry.messages.append({"role": "user", "content": user_msg})
            entry.messages.append({"role": "assistant", "content": ai_msg})
            entry.last_active = time.time()

    def cleanup_expired(self) -> int:
        """Removes expired entries. Returns count removed."""
        now = time.time()
        with self._lock:
            expired = [
                cid
                for cid, e in self._store.items()
                if (now - e.last_active) > self._ttl_seconds
            ]
            for cid in expired:
                del self._store[cid]
        if expired:
            logger.info("Cleaned up %d expired customer histor(y/ies)", len(expired))
        return len(expired)

    def active_count(self) -> int:
        with self._lock:
            return len(self._store)


# Single shared instance for the app to import
chat_store = ChatHistoryStore()


async def start_cleanup_loop(interval: int = CLEANUP_INTERVAL_SECONDS) -> None:
    """
    Background task: run this once at app startup, e.g. in FastAPI:

        @app.on_event("startup")
        async def on_startup():
            asyncio.create_task(start_cleanup_loop())
    """
    while True:
        await asyncio.sleep(interval)
        try:
            chat_store.cleanup_expired()
        except Exception:
            logger.exception("Cleanup loop error")
