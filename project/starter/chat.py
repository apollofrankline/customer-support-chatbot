#!/usr/bin/env python3
"""Chat with your support chatbot from the terminal."""

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.eventstream import EventStream


REASONING_PATTERN = re.compile(
    r"<\s*(thinking|analysis|reasoning)\s*>.*?"
    r"<\s*/\s*\1\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)

OPEN_REASONING_PATTERN = re.compile(
    r"<\s*(thinking|analysis|reasoning)\s*>.*$",
    flags=re.IGNORECASE | re.DOTALL,
)

REASONING_TAG_PATTERN = re.compile(
    r"</?\s*(thinking|analysis|reasoning)\s*>",
    flags=re.IGNORECASE,
)


def remove_internal_reasoning(text):
    """Remove tagged internal reasoning before displaying assistant text."""
    cleaned = REASONING_PATTERN.sub("", text)
    cleaned = OPEN_REASONING_PATTERN.sub("", cleaned)
    cleaned = REASONING_TAG_PATTERN.sub("", cleaned)
    return cleaned.strip()


def event_stream(response):
    """Locate the streaming part of the invoke_harness response."""
    for value in response.values():
        if isinstance(value, EventStream):
            return value
    raise RuntimeError(f"No event stream in response: {list(response)}")


def invoke(rt, config, session_id, user_text, verbose=False):
    """Send one user message and display only customer-facing text."""
    response = rt.invoke_harness(
        harnessArn=config["harness_arn"],
        runtimeSessionId=session_id,
        model={
            "bedrockModelConfig": {
                "modelId": config.get(
                    "model_id", "us.amazon.nova-pro-v1:0"
                )
            }
        },
        tools=[{
            "type": "agentcore_gateway",
            "name": "support_gateway",
            "config": {
                "agentCoreGateway": {
                    "gatewayArn": config["gateway_arn"]
                }
            },
        }],
        messages=[{
            "role": "user",
            "content": [{"text": user_text}],
        }],
    )

    visible_texts = []
    buffer = []

    def flush_text_block():
        """Filter and display one completed assistant text block."""
        if not buffer:
            return

        raw_text = "".join(buffer)
        buffer.clear()

        visible_text = remove_internal_reasoning(raw_text)
        if visible_text:
            print(visible_text, end="", flush=True)
            visible_texts.append(visible_text)

    for event in event_stream(response):
        if verbose:
            # Do not expose raw assistant text in diagnostic output.
            logged_event = json.loads(json.dumps(event, default=str))
            delta_event = logged_event.get("contentBlockDelta", {})
            delta = delta_event.get("delta", {})
            if "text" in delta:
                delta["text"] = "[assistant text buffered and redacted]"
            print(
                f"\n[event] {json.dumps(logged_event, default=str)}",
                file=sys.stderr,
            )

        if "contentBlockStart" in event:
            tool_use = (
                event["contentBlockStart"]
                .get("start", {})
                .get("toolUse")
            )
            if tool_use:
                flush_text_block()
                print(
                    f"\n[tool call] {tool_use.get('name', '?')}",
                    flush=True,
                )

        elif "contentBlockDelta" in event:
            delta = event["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                buffer.append(delta["text"])

        elif "contentBlockStop" in event:
            flush_text_block()

        elif "messageStop" in event:
            flush_text_block()

    flush_text_block()
    print()
    return "\n".join(visible_texts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="agentcore_config.json",
        help="Config file written by the setup scripts.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print stream events with assistant text redacted.",
    )
    args = parser.parse_args()

    config = json.loads(
        Path(args.config).read_text(encoding="utf-8")
    )

    if "harness_arn" not in config:
        sys.exit(
            "No harness in config yet — run create_harness.py first."
        )

    session_id = f"{uuid.uuid4()}-support-chat"

    rt = boto3.client(
        "bedrock-agentcore",
        region_name=config["region"],
        config=Config(
            read_timeout=300,
            retries={"max_attempts": 1},
        ),
    )

    print(
        f"Connected to harness {config.get('harness_name', '?')} "
        f"(session {session_id})."
    )
    print("Type a message, or 'quit' to exit.\n")

    while True:
        try:
            first_line = input("you> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if first_line.strip().lower() in ("quit", "exit"):
            break

        if not first_line.strip():
            continue

        message_lines = [first_line]

        print("    Continue typing. Enter /send on its own line to submit.")
        while True:
            try:
                line = input("... ")
            except (EOFError, KeyboardInterrupt):
                print()
                message_lines = []
                break

            if line.strip() == "/send":
                break

            message_lines.append(line)

        if not message_lines:
            break

        user_text = "\n".join(message_lines).strip()
        if not user_text:
            continue

        print("bot> ", end="", flush=True)
        invoke(
            rt,
            config,
            session_id,
            user_text,
            verbose=args.verbose,
        )
        print()


if __name__ == "__main__":
    main()
