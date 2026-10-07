"""Prepare disposable DSW images without retrying container or browser failures."""

from __future__ import annotations

import re
import subprocess
import time

PREPARATION_TIMEOUT = 300
MAX_ATTEMPTS = 3
TRANSIENT_DOWNLOAD_ERROR = re.compile(
    r"(?:unexpected (?:http )?status|http(?:/\d(?:\.\d)?)?|status code)"
    r"[^\n]*\b(?:500|502|503|504)\b"
    r"|net/http: TLS handshake timeout|i/o timeout|connection reset by peer|unexpected EOF",
    re.IGNORECASE,
)


def prepare_images(command: list[str], *, env: dict[str, str]) -> None:
    """Pull and build images within one five-minute budget and three attempts per stage."""
    deadline = time.monotonic() + PREPARATION_TIMEOUT
    for arguments in (("pull", "--ignore-buildable"), ("build",)):
        invocation = [*command, *arguments]
        for attempt in range(1, MAX_ATTEMPTS + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(invocation, PREPARATION_TIMEOUT)
            print(
                f"Preparing Docker images: {arguments[0]} (attempt {attempt}/{MAX_ATTEMPTS})",
                flush=True,
            )
            result = subprocess.run(
                invocation,
                env=env,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=remaining,
            )
            output = result.stdout or ""
            print(output, end="", flush=True)
            if result.returncode == 0:
                break
            if attempt == MAX_ATTEMPTS or not TRANSIENT_DOWNLOAD_ERROR.search(output):
                raise subprocess.CalledProcessError(result.returncode, invocation, output=output)
            delay = 5 * attempt
            if deadline - time.monotonic() <= delay:
                raise subprocess.TimeoutExpired(invocation, PREPARATION_TIMEOUT, output=output)
            print(f"Transient image download failure; retrying in {delay} seconds.", flush=True)
            time.sleep(delay)
