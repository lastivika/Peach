"""Local lab entry points; prints actual model output and metering."""

import argparse
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from app.ai.agenda import PROMPT_VERSION, cost_usd, invoke, model_id, parse_agenda


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["hello", "parse"])
    parser.add_argument("--tz", default="Europe/Kyiv")
    args = parser.parse_args()
    if args.command == "hello":
        msg = invoke(
            model=model_id(),
            max_tokens=256,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": "In one sentence: what is an ISO week?"}],
        )
        print(
            json.dumps(
                {
                    "answer": " ".join(b.text for b in msg.content if b.type == "text"),
                    "stop_reason": msg.stop_reason,
                    "usage": msg.usage.model_dump(),
                },
                indent=2,
            )
        )
    else:
        agenda, usage = parse_agenda(
            os.environ.get("TEXT", ""), datetime.now(ZoneInfo(args.tz)).date(), args.tz
        )
        print(
            json.dumps(
                {
                    "agenda": agenda.model_dump(mode="json"),
                    "usage": usage,
                    "model": model_id(),
                    "prompt_version": PROMPT_VERSION,
                    "cost_usd": cost_usd(usage),
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
