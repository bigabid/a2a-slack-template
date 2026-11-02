from slack_bolt.async_app import AsyncApp
from logging import Logger
from slack_sdk.web.async_client import AsyncWebClient
import re
import uuid
import httpx
import os
from a2a.client import A2AClient
from a2a.types import Message, TextPart, MessageSendParams, SendMessageRequest

AGENT_NAME = os.environ.get("AGENT_DISPLAY_NAME", "The agent")
CHANNELS = {c.strip() for c in os.environ.get("SLACK_CHANNELS", "").split(",") if c.strip()}
TIMEOUT = float(os.environ.get("A2A_TIMEOUT_SECONDS", "600"))
MARKDOWN_BLOCK_LIMIT = 12000
FALLBACK_TEXT_LIMIT = 3000


async def invoke_a2a_agent(agent_url: str, input: str, context_id: str, user: str, logger: Logger):
    """
    Invokes the A2A agent in the conversation `context_id` and returns the answer and usage information.
    """
    a2a_client = A2AClient(
        url=agent_url,
        httpx_client=httpx.AsyncClient(timeout=TIMEOUT, headers={"X-User-Id": user}),
    )

    message = Message(role="user", parts=[TextPart(text=input)], message_id=str(uuid.uuid4()), context_id=context_id)

    logger.info(f"Invoking the agent: {agent_url} context={context_id}")
    response = await a2a_client.send_message(SendMessageRequest(id=str(uuid.uuid4()), params=MessageSendParams(message=message)))

    result = getattr(response.root, "result", None)
    if result is None:
        error = getattr(response.root, "error", None)
        raise RuntimeError(getattr(error, "message", None) or "No response from the agent")

    texts = [
        part.root.text
        for artifact in (getattr(result, "artifacts", None) or [])
        for part in (artifact.parts or [])
        if hasattr(part.root, "text") and part.root.text and part.root.text.strip()
    ]
    status = getattr(result, "status", None)
    state = getattr(getattr(status, "state", None), "value", None)
    if state != "completed" or not texts:
        detail = ""
        if status and status.message:
            detail = " ".join(p.root.text for p in status.message.parts if hasattr(p.root, "text"))
        raise RuntimeError(detail or f"agent ended in state {state}")

    # Some models return their working first; the last text part is the answer.
    return texts[-1].strip(), extract_usage_info(result)


def extract_usage_info(task) -> str:
    """
    Extract usage information from the task metadata.
    """
    try:
        usage_meta = (task.metadata or {}).get("adk_usage_metadata")
        if usage_meta:
            prompt_tokens = usage_meta.get("promptTokenCount", 0)
            candidates_tokens = usage_meta.get("candidatesTokenCount", 0)
            total_tokens = usage_meta.get("totalTokenCount", 0)
            return f"Tokens: prompt {prompt_tokens:,} · response {candidates_tokens:,} · total {total_tokens:,}"
    except Exception:
        pass
    return ""


async def on_mention(event, client: AsyncWebClient, logger: Logger):
    """
    Answers an @mention in a configured channel, in the thread. Each thread is one agent session.
    """
    channel = event["channel"]
    if CHANNELS and channel not in CHANNELS:
        return
    thread_ts = event.get("thread_ts") or event["ts"]
    question = re.sub(r"<@[A-Z0-9]+>", "", event.get("text", "")).strip()
    if not question:
        return

    kagent_a2a_url = os.environ["KAGENT_A2A_URL"]
    await client.reactions_add(channel=channel, timestamp=event["ts"], name="eyes")
    usage_info = ""
    try:
        answer, usage_info = await invoke_a2a_agent(
            kagent_a2a_url, question, f"slack-{channel}-{thread_ts}", f"slack:{event.get('user', 'unknown')}", logger)
    except Exception as e:
        logger.exception(f"agent call failed for {channel}/{thread_ts}")
        answer = f":warning: {AGENT_NAME} couldn't answer: {str(e)[:500]}"

    blocks = [{"type": "markdown", "text": answer[:MARKDOWN_BLOCK_LIMIT]}]
    if usage_info:
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": usage_info}]})
    await client.chat_postMessage(
        channel=channel, thread_ts=thread_ts, blocks=blocks,
        text=answer[:FALLBACK_TEXT_LIMIT], unfurl_links=False,
    )
    try:
        await client.reactions_remove(channel=channel, timestamp=event["ts"], name="eyes")
    except Exception:
        pass


def register_handlers(app: AsyncApp):
    """
    Register all handlers for the bot.
    """
    app.event("app_mention")(on_mention)
