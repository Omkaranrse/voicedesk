import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

# Dynamically locate .env file from common run directories
for candidate in (
    ".env",
    "../.env",
    str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
):
    if Path(candidate).is_file():
        load_dotenv(candidate)
        break

from livekit.agents import AgentServer, AgentSession, JobContext, cli
from livekit.plugins import silero

from . import db
from .agent import Assistant
from .config import settings as s
from .metrics import attach_metrics
from .pipeline import build_session

logger = logging.getLogger("voicedesk.main")
server = AgentServer(num_idle_processes=s.num_idle_processes)


async def _enforce_call_duration_cap(
    session: AgentSession,
    ctx: JobContext,
    max_duration: int,
) -> None:
    """Enforce a hard per-session maximum call duration.
    Announces the timeout gracefully before cleanly disconnecting the room.
    """
    try:
        await asyncio.sleep(max_duration)
        logger.warning(
            "Call in room %s reached maximum duration limit of %ds. Terminating session.",
            ctx.room.name,
            max_duration,
        )
        try:
            handle = session.say(
                "Sorry, we've reached the maximum call time. Goodbye.",
                allow_interruptions=False,
            )
            # Wait briefly for speech completion (up to 3.0s)
            await asyncio.wait_for(handle, timeout=3.0)
        except Exception as exc:  # noqa: BLE001 - Caller may hang up or disconnect during announcement
            logger.debug("Timeout announcement ended or interrupted: %s", exc)
        finally:
            await ctx.room.disconnect()
    except asyncio.CancelledError:
        logger.debug("Call duration supervisor cancelled for room %s", ctx.room.name)


@server.rtc_session
async def entrypoint(ctx: JobContext):
    vad = silero.VAD.load()

    session = build_session(vad=vad)

    # Attach performance metrics (duration, TTFT, TTFB, EOU delay - no transcript text)
    attach_metrics(session, ctx.room.name)

    # Privacy default: only log transcripts if explicitly enabled via LOG_TRANSCRIPTS=true
    if s.log_transcripts:
        logger.info("Transcript logging is ENABLED (development mode).")

        @session.on("user_input_transcribed")
        def _on_user_transcript(ev):
            if ev.is_final and ev.transcript:
                logger.info("[Transcript] User: %s", ev.transcript)

        @session.on("conversation_item_added")
        def _on_conversation_item(ev):
            if hasattr(ev.item, "role") and ev.item.role == "assistant":
                text = getattr(ev.item, "text_content", "")
                if text:
                    logger.info("[Transcript] Assistant: %s", text)
    else:
        logger.info("Transcript logging is DISABLED (privacy default).")

    await session.start(
        room=ctx.room,
        agent=Assistant(),
    )

    await ctx.connect()

    # Per-session call length cap supervisor
    timeout_task = asyncio.create_task(
        _enforce_call_duration_cap(session, ctx, s.max_call_duration_seconds),
        name=f"timeout-{ctx.room.name}",
    )

    def _cancel_timeout_sync(*_):
        if not timeout_task.done():
            timeout_task.cancel()

    async def _cancel_timeout_async(*_):
        if not timeout_task.done():
            timeout_task.cancel()

    session.on("close", _cancel_timeout_sync)
    ctx.add_shutdown_callback(_cancel_timeout_async)

    # Wait for caller/participant connection before greeting to avoid dropped/clipped speech
    participant = await ctx.wait_for_participant()

    # SIP Caller ID Integration: detect phone number from attributes, identity, or room prefix
    caller_phone = None
    if participant:
        attrs = getattr(participant, "attributes", {}) or {}
        for key in (
            "sip.phoneNumber",
            "sip.callerId",
            "sip.trunkPhoneNumber",
            "phone_number",
        ):
            if attrs.get(key):
                caller_phone = str(attrs[key]).strip()
                break

        if not caller_phone:
            ident = getattr(participant, "identity", "") or ""
            if ident.startswith(("sip_", "+")) or ident.replace("+", "").isdigit():
                clean_id = ident.removeprefix("sip_").strip()
                if clean_id:
                    caller_phone = clean_id

    if not caller_phone and ctx.room and ctx.room.name:
        import re

        match = re.search(r"sip-call-_([^_]+)_", ctx.room.name)
        if match:
            caller_phone = match.group(1).strip()

    if caller_phone:
        logger.info(
            "Detected SIP Caller ID for room %s: %s", ctx.room.name, caller_phone
        )
        greeting_prompt = f"Greet the caller in one short sentence. (Detected caller phone: {caller_phone})"
    else:
        greeting_prompt = "Greet the caller in one short sentence."

    session.generate_reply(instructions=greeting_prompt)


if __name__ == "__main__":
    db.init_db()
    cli.run_app(server)
