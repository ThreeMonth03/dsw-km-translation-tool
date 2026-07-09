"""Small Weblate upload client used by trusted post-merge workflows."""

from __future__ import annotations

import mimetypes
import secrets
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .http_auth import token_authorization_header

Urlopen = Callable[..., object]


@dataclass(frozen=True)
class WeblateUploadResult:
    """Summary of one Weblate file upload."""

    api_url: str
    bytes_uploaded: int
    status: int | None
    response_body: str


def resolve_weblate_file_api_url(download_url: str) -> str:
    """Resolve Weblate's translation-file API endpoint from a download URL."""

    parsed_url = urllib.parse.urlparse(download_url)
    path_parts = [part for part in parsed_url.path.split("/") if part]
    try:
        download_index = path_parts.index("download")
        project, component, language = path_parts[download_index + 1 : download_index + 4]
    except (ValueError, IndexError) as error:
        raise ValueError("Cannot derive Weblate file API URL from localize.download_url") from error
    return urllib.parse.urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            f"/api/translations/{project}/{component}/{language}/file/",
            "",
            "",
            "",
        )
    )


def upload_translation_file(
    *,
    api_url: str,
    po_path: Path,
    token: str,
    method: str = "translate",
    conflicts: str = "replace-translated",
    author_name: str | None = None,
    author_email: str | None = None,
    urlopen: Urlopen | None = None,
) -> WeblateUploadResult:
    """Upload one PO file to Weblate using the official file endpoint."""

    body, content_type = encode_multipart_form(
        fields={
            "method": method,
            "conflicts": conflicts,
            **({"author_name": author_name} if author_name else {}),
            **({"author_email": author_email} if author_email else {}),
        },
        file_field="file",
        file_path=po_path,
    )
    request = urllib.request.Request(
        api_url,
        data=body,
        headers={
            "Authorization": token_authorization_header(token),
            "Content-Type": content_type,
        },
        method="POST",
    )
    opener = urlopen or urllib.request.urlopen
    with opener(request, timeout=60) as response:
        response_body = response.read().decode("utf-8", errors="replace")
        status = getattr(response, "status", None)
    return WeblateUploadResult(
        api_url=api_url,
        bytes_uploaded=len(body),
        status=status,
        response_body=response_body,
    )


def encode_multipart_form(
    *,
    fields: dict[str, str],
    file_field: str,
    file_path: Path,
) -> tuple[bytes, str]:
    """Encode one multipart form with a single uploaded file."""

    boundary = f"----dsw-km-{secrets.token_hex(12)}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    content_type = mimetypes.guess_type(file_path.name)[0] or "text/plain"
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{file_path.name}"\r\n'
            ).encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"
