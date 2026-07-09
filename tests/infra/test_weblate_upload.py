"""Tests for Weblate file upload helpers."""

from __future__ import annotations

import urllib.request
from pathlib import Path

from dsw_km_translation_tool.http_auth import token_authorization_header
from dsw_km_translation_tool.weblate_upload import (
    encode_multipart_form,
    resolve_weblate_file_api_url,
    upload_translation_file,
)


def test_token_authorization_header_defaults_to_token_scheme() -> None:
    """Verify Weblate tokens use Weblate's documented Token scheme."""

    assert token_authorization_header(" secret ") == "Token secret"
    assert token_authorization_header("Bearer abc") == "Bearer abc"
    assert token_authorization_header("Token abc") == "Token abc"


def test_resolve_weblate_file_api_url() -> None:
    """Verify upload API coordinates are derived from the download URL."""

    assert resolve_weblate_file_api_url(
        "https://localize.ds-wizard.org/download/knowledge-models/"
        "common-dsw-knowledge-model/zh_Hant/"
    ) == (
        "https://localize.ds-wizard.org/api/translations/knowledge-models/"
        "common-dsw-knowledge-model/zh_Hant/file/"
    )


def test_encode_multipart_form_includes_fields_and_file(workspace: Path) -> None:
    """Verify multipart upload bodies contain method, conflicts, and file data."""

    po_path = workspace / "import.po"
    po_path.write_text('msgid "A"\nmsgstr "B"\n', encoding="utf-8")

    body, content_type = encode_multipart_form(
        fields={"method": "translate", "conflicts": "replace-translated"},
        file_field="file",
        file_path=po_path,
    )

    assert content_type.startswith("multipart/form-data; boundary=")
    assert b'name="method"' in body
    assert b"translate" in body
    assert b'name="conflicts"' in body
    assert b"replace-translated" in body
    assert b'filename="import.po"' in body
    assert b'msgstr "B"' in body


def test_upload_translation_file_posts_authenticated_request(workspace: Path) -> None:
    """Verify uploads use POST with a Weblate token Authorization header."""

    po_path = workspace / "import.po"
    po_path.write_text('msgid "A"\nmsgstr "B"\n', encoding="utf-8")
    requests: list[urllib.request.Request] = []

    class FakeResponse:
        status = 200

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        @staticmethod
        def read() -> bytes:
            return b'{"result": true}'

    def fake_urlopen(request: urllib.request.Request, timeout: int) -> FakeResponse:
        assert timeout == 60
        requests.append(request)
        return FakeResponse()

    result = upload_translation_file(
        api_url="https://localize.example/api/translations/p/c/l/file/",
        po_path=po_path,
        token="wlu_secret",
        urlopen=fake_urlopen,
    )

    assert result.status == 200
    assert requests[0].get_method() == "POST"
    assert requests[0].headers["Authorization"] == "Token wlu_secret"
