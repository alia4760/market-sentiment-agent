import json
import logging
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

LIMIT = 1900  # Discord rejects messages over 2000 characters


def _chunks(text: str) -> list[str]:
    """Split on line breaks so no message is over the limit."""
    chunks, current = [], ""
    for line in text.split("\n"):
        while len(line) > LIMIT:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:LIMIT])
            line = line[LIMIT:]
        if len(current) + len(line) + 1 > LIMIT:
            chunks.append(current)
            current = ""
        current += line + "\n"
    if current.strip():
        chunks.append(current)
    return chunks


def send_brief(message: str, pdf: bytes, filename: str) -> None:
    """Post one short message with the full report attached as a PDF."""
    url = os.environ["DISCORD_WEBHOOK_URL"]
    for attempt in range(3):
        response = requests.post(
            url,
            data={"payload_json": json.dumps({"content": message})},
            files={"file": (filename, pdf, "application/pdf")},
            timeout=60,
        )
        if response.status_code == 429:  # rate limited: wait as long as Discord says
            time.sleep(float(response.json().get("retry_after", 1)) + 0.5)
            continue
        response.raise_for_status()
        return
    raise RuntimeError("Discord kept rate-limiting the report")


def send_report(text: str) -> int:
    """Post the report to the Discord webhook in as many messages as needed. Returns the count."""
    url = os.environ["DISCORD_WEBHOOK_URL"]
    chunks = _chunks(text)
    for chunk in chunks:
        for attempt in range(3):
            response = requests.post(url, json={"content": chunk}, timeout=30)
            if response.status_code == 429:  # rate limited: wait as long as Discord says
                time.sleep(float(response.json().get("retry_after", 1)) + 0.5)
                continue
            response.raise_for_status()
            break
        else:
            raise RuntimeError("Discord kept rate-limiting the report")
        time.sleep(0.5)
    return len(chunks)
