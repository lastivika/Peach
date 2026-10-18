"""Adapt Bedrock Converse to the existing validated parser message contract."""

import os
from functools import lru_cache

import boto3
from anthropic.types import Message
from botocore.config import Config


@lru_cache
def runtime():
    return boto3.client(
        "bedrock-runtime",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        config=Config(connect_timeout=2, read_timeout=10, retries={"total_max_attempts": 1}),
    )


def create_message(*, model, messages, max_tokens, system=None, tools=None, **_):
    converted = []
    for message in messages:
        source = message["content"]
        content = []
        for block in [{"type": "text", "text": source}] if isinstance(source, str) else source:
            if block["type"] == "text":
                content.append({"text": block["text"]})
            elif block["type"] == "tool_use":
                content.append(
                    {
                        "toolUse": {
                            "toolUseId": block["id"],
                            "name": block["name"],
                            "input": block["input"],
                        }
                    }
                )
            elif block["type"] == "tool_result":
                content.append(
                    {
                        "toolResult": {
                            "toolUseId": block["tool_use_id"],
                            "content": [{"text": block["content"]}],
                            "status": "error" if block.get("is_error") else "success",
                        }
                    }
                )
            else:
                raise ValueError("Unsupported Converse content block")
        converted.append({"role": message["role"], "content": content})
    request = {
        "modelId": model,
        "messages": converted,
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0},
    }
    if system:
        request["system"] = [{"text": system}]
    if tools:
        request["toolConfig"] = {
            "tools": [
                {
                    "toolSpec": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "inputSchema": {"json": tool["input_schema"]},
                    }
                }
                for tool in tools
            ]
        }
    result = runtime().converse(**request)
    blocks = []
    for block in result["output"]["message"]["content"]:
        if "text" in block:
            blocks.append({"type": "text", "text": block["text"]})
        elif "toolUse" in block:
            call = block["toolUse"]
            blocks.append(
                {
                    "type": "tool_use",
                    "id": call["toolUseId"],
                    "name": call["name"],
                    "input": call["input"],
                }
            )
    return Message.model_validate(
        {
            "id": result.get("ResponseMetadata", {}).get("RequestId", "converse"),
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": blocks,
            "stop_reason": {
                "tool_use": "tool_use",
                "end_turn": "end_turn",
                "max_tokens": "max_tokens",
            }.get(result["stopReason"], "refusal"),
            "usage": {
                "input_tokens": result["usage"]["inputTokens"],
                "output_tokens": result["usage"]["outputTokens"],
            },
        }
    )
