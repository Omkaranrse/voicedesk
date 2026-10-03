import asyncio
import uuid

from livekit.agents import llm
from livekit.agents.llm import ChatChunk, ChatContext, ChoiceDelta
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS

from voicedesk.resilient_llm import DEFAULT_RECOVERY_MESSAGE, ResilientLLM


class MockNormalLLM(llm.LLM):
    def __init__(self, response_text: str = "Hello from primary!"):
        super().__init__()
        self._response_text = response_text

    def chat(
        self,
        *,
        chat_ctx,
        tools=None,
        conn_options=DEFAULT_API_CONNECT_OPTIONS,
        **kwargs,
    ):
        text = self._response_text

        class NormalStream(llm.LLMStream):
            async def _run(self):
                self._event_ch.send_nowait(
                    ChatChunk(
                        id=f"c-{uuid.uuid4().hex[:6]}",
                        delta=ChoiceDelta(role="assistant", content=text),
                    )
                )

        return NormalStream(
            self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options
        )


class MockFailingLLM(llm.LLM):
    def chat(
        self,
        *,
        chat_ctx,
        tools=None,
        conn_options=DEFAULT_API_CONNECT_OPTIONS,
        **kwargs,
    ):
        class FailingStream(llm.LLMStream):
            async def _run(self):
                raise ConnectionRefusedError(
                    "Ollama service unavailable (connection refused)"
                )

        return FailingStream(
            self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options
        )


def test_case_a_primary_available():
    """CASE A: Primary LLM is available and serves requests normally."""

    async def _test():
        primary = MockNormalLLM("Primary response")
        adapter = llm.FallbackAdapter([primary], attempt_timeout=2.0)
        resilient = ResilientLLM(adapter)

        collected = await resilient.chat(chat_ctx=ChatContext.empty()).collect()
        assert collected.text == "Primary response"

    asyncio.run(_test())


def test_case_b_primary_fails_fallback_succeeds():
    """CASE B: Primary LLM fails mid-call; FallbackAdapter automatically switches to backup."""

    async def _test():
        primary = MockFailingLLM()
        backup = MockNormalLLM("Backup response")
        adapter = llm.FallbackAdapter([primary, backup], attempt_timeout=2.0)
        resilient = ResilientLLM(adapter)

        collected = await resilient.chat(chat_ctx=ChatContext.empty()).collect()
        assert collected.text == "Backup response"

    asyncio.run(_test())


def test_case_c_no_fallback_configured_primary_fails():
    """CASE C: Primary LLM fails and no backup is configured;
    ResilientLLM catches the error and emits the spoken recovery phrase.
    """

    async def _test():
        primary = MockFailingLLM()
        adapter = llm.FallbackAdapter([primary], attempt_timeout=2.0)
        resilient = ResilientLLM(adapter)

        collected = await resilient.chat(chat_ctx=ChatContext.empty()).collect()
        assert collected.text == DEFAULT_RECOVERY_MESSAGE
        assert "Sorry" in collected.text

    asyncio.run(_test())


def test_case_c_both_primary_and_fallback_fail():
    """CASE C variant: Both primary and backup fail;
    ResilientLLM catches the combined failure and emits the recovery phrase.
    """

    async def _test():
        primary = MockFailingLLM()
        backup = MockFailingLLM()
        adapter = llm.FallbackAdapter([primary, backup], attempt_timeout=1.0)
        resilient = ResilientLLM(adapter)

        collected = await resilient.chat(chat_ctx=ChatContext.empty()).collect()
        assert collected.text == DEFAULT_RECOVERY_MESSAGE

    asyncio.run(_test())
