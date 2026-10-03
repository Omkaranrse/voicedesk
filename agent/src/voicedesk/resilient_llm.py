from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Literal

from livekit.agents import llm
from livekit.agents.llm import ChatChunk, ChatContext, ChoiceDelta, Tool
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions

logger = logging.getLogger("voicedesk.resilient_llm")

DEFAULT_RECOVERY_MESSAGE = "Sorry, give me a moment."
DEFAULT_MAX_CONTEXT_ITEMS = (
    14  # Preserves system instructions + last 6-7 conversational turns
)


class ResilientLLMStream(llm.LLMStream):
    """An LLMStream wrapper that enforces context window boundaries and provides spoken error recovery."""

    def __init__(
        self,
        resilient_llm: ResilientLLM,
        *,
        chat_ctx: ChatContext,
        tools: list[Tool],
        conn_options: APIConnectOptions,
        parallel_tool_calls: Any = None,
        tool_choice: Any = None,
        extra_kwargs: Any = None,
    ) -> None:
        super().__init__(
            resilient_llm,
            chat_ctx=chat_ctx,
            tools=tools,
            conn_options=conn_options,
        )
        self._resilient_llm = resilient_llm
        self._parallel_tool_calls = parallel_tool_calls
        self._tool_choice = tool_choice
        self._extra_kwargs = extra_kwargs

    async def _run(self) -> None:
        chunks_sent = 0
        try:
            # Context Window Management: prune history to prevent unbounded token growth
            # LiveKit's truncate preserves the initial system instruction while keeping the last N items
            if len(self._chat_ctx.items) > self._resilient_llm._max_context_items:
                logger.debug(
                    "Truncating chat context from %d items to %d items",
                    len(self._chat_ctx.items),
                    self._resilient_llm._max_context_items,
                )
                self._chat_ctx.truncate(
                    max_items=self._resilient_llm._max_context_items
                )

            kwargs: dict[str, Any] = {}
            if self._parallel_tool_calls is not None:
                kwargs["parallel_tool_calls"] = self._parallel_tool_calls
            if self._tool_choice is not None:
                kwargs["tool_choice"] = self._tool_choice
            if self._extra_kwargs is not None:
                kwargs["extra_kwargs"] = self._extra_kwargs

            stream = self._resilient_llm._underlying.chat(
                chat_ctx=self._chat_ctx,
                tools=self._tools,
                conn_options=self._conn_options,
                **kwargs,
            )

            async for chunk in stream:
                chunks_sent += 1
                self._event_ch.send_nowait(chunk)

        except Exception as exc:  # noqa: BLE001 - Resilience layer catches provider errors to emit recovery message
            logger.warning(
                "LLM generation failed (%s): %s. Emitting recovery message.",
                type(exc).__name__,
                exc,
            )
            # Only emit recovery message if no response chunks were yielded yet
            if chunks_sent == 0:
                recovery_chunk = ChatChunk(
                    id=f"rec-{uuid.uuid4().hex[:8]}",
                    delta=ChoiceDelta(
                        role="assistant",
                        content=self._resilient_llm._recovery_message,
                    ),
                )
                self._event_ch.send_nowait(recovery_chunk)


class ResilientLLM(llm.LLM[Literal["metrics_collected"]]):
    """Wraps an underlying LLM (or FallbackAdapter) to enforce context length limits,
    intercept fatal provider errors, and speak a recovery message when LLMs fail.
    """

    def __init__(
        self,
        underlying: llm.LLM,
        recovery_message: str = DEFAULT_RECOVERY_MESSAGE,
        max_context_items: int = DEFAULT_MAX_CONTEXT_ITEMS,
    ) -> None:
        super().__init__()
        self._underlying = underlying
        self._recovery_message = recovery_message
        self._max_context_items = max_context_items
        self._underlying.on("metrics_collected", self._on_metrics_collected)

    def _on_metrics_collected(self, *args: Any, **kwargs: Any) -> None:
        self.emit("metrics_collected", *args, **kwargs)

    @property
    def model(self) -> str:
        return self._underlying.model

    @property
    def provider(self) -> str:
        return self._underlying.provider

    @property
    def metrics_metadata(self) -> dict[str, Any]:
        return self._underlying.metrics_metadata

    def prewarm(self, *, loop: asyncio.AbstractEventLoop | None = None) -> None:
        self._underlying.prewarm(loop=loop)

    async def aclose(self) -> None:
        self._underlying.off("metrics_collected", self._on_metrics_collected)
        await self._underlying.aclose()
        await super().aclose()

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list[Tool] | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls: Any = None,
        tool_choice: Any = None,
        extra_kwargs: Any = None,
    ) -> llm.LLMStream:
        return ResilientLLMStream(
            self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
            parallel_tool_calls=parallel_tool_calls,
            tool_choice=tool_choice,
            extra_kwargs=extra_kwargs,
        )
