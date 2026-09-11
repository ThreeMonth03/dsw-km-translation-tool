"""Exercise official PO import in a fresh, loopback-only DSW Docker stack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import socket
import subprocess
import tempfile
import time
import uuid
from contextlib import ExitStack
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import yaml
from babel.messages.pofile import read_po
from playwright.sync_api import Error, TimeoutError, expect, sync_playwright

from dsw_km_translation_tool.locale_coverage import compare_locale_coverage, render_locale_coverage
from dsw_km_translation_tool.translation_repository_config import (
    load_translation_repository_config,
    version_paths,
)

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = Path(__file__).with_name("compose.yml")
LOGIN = {"email": "albert.einstein@example.com", "password": "password", "code": None}


def checked(response, operation: str):
    """Do not include request headers, tokens or response bodies in errors."""
    if not response.ok:
        raise RuntimeError(f"{operation} failed (HTTP {response.status})")
    return response


def translated_chapter(pot_path: Path, po_path: Path) -> tuple[str, str]:
    with pot_path.open(encoding="utf-8") as handle:
        pot = read_po(handle, abort_invalid=True)
    with po_path.open(encoding="utf-8") as handle:
        po = read_po(handle, abort_invalid=True)
    for source in pot:
        if not any(
            ref.startswith("chapter/") and ref.endswith("/title") for ref, _ in source.locations
        ):
            continue
        target = po.get(source.id, context=source.context)
        if target and not target.fuzzy and target.string and target.string != source.id:
            return source.id, target.string
    raise RuntimeError("Browser check requires at least one translated chapter title")


def verify_browser(api, client, minio, km_path, po_path, package_id, source, target, out, result):
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1500, "height": 1080})
        page = context.new_page()
        page.set_default_timeout(30000)
        page.on("dialog", lambda dialog: dialog.accept())
        try:
            deadline = time.monotonic() + 180
            while True:
                try:
                    login = context.request.post(f"{api}/tokens", data=LOGIN, timeout=5000)
                    if login.ok:
                        break
                except Error:
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("Disposable DSW did not become ready")
                time.sleep(2)
            headers = {"Authorization": f"Bearer {login.json()['token']}"}
            imported = checked(
                context.request.post(
                    f"{api}/knowledge-model-packages/bundle",
                    headers=headers,
                    multipart={
                        "file": {
                            "name": km_path.name,
                            "mimeType": "application/octet-stream",
                            "buffer": km_path.read_bytes(),
                        }
                    },
                ),
                "Source KM import",
            ).json()
            km_url = f"{api}/knowledge-model-packages/{imported['uuid']}"
            descriptor = checked(
                context.request.get(f"{km_url}/locales/template", headers=headers), "POT export"
            ).json()
            location = urlsplit(descriptor["url"])
            if location.scheme != "http" or location.netloc != "minio:9000":
                raise RuntimeError("POT export must use the disposable Minio service")
            # Preserve the signed Host while accessing the loopback-published port.
            download = checked(
                context.request.get(
                    urlunsplit(location._replace(netloc=urlsplit(minio).netloc)),
                    headers={"Host": location.netloc},
                ),
                "POT download",
            )
            pot_path = out / "official.pot"
            pot_path.write_bytes(download.body())
            coverage = compare_locale_coverage(
                pot_path=pot_path,
                po_path=po_path,
                package_id=package_id,
                source_language=source,
                target_language=target,
            )
            result["coverage"] = coverage
            (out / "coverage.json").write_text(
                json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (out / "coverage.md").write_text(render_locale_coverage(coverage), encoding="utf-8")
            summary = render_locale_coverage(coverage, details=False)
            print(summary, flush=True)
            if os.environ.get("GITHUB_STEP_SUMMARY"):
                with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as handle:
                    handle.write(summary)
            if coverage["status"] == "incomplete":
                print(
                    "::warning::Official POT coverage is incomplete; see coverage.md for missing, untranslated, fuzzy and extra messages.",
                    flush=True,
                )
            original, translated = translated_chapter(pot_path, po_path)
            page.goto(client)
            page.get_by_placeholder("Email", exact=True).fill(LOGIN["email"])
            page.get_by_placeholder("Password", exact=True).fill(LOGIN["password"])
            page.get_by_role("button", name="Log In", exact=True).click()
            page.get_by_text("Albert Einstein", exact=True).wait_for()
            page.goto(f"{client}/knowledge-models/{imported['uuid']}")
            page.wait_for_load_state("networkidle")
            page.get_by_text("Locales", exact=True).last.click()
            page.locator("button.btn-primary.with-icon").click()
            page.get_by_label("Name", exact=True).fill("CI test locale")
            with page.expect_file_chooser() as chooser:
                page.get_by_role("button", name="Select .po file", exact=True).click()
            chooser.value.set_files(po_path)
            with page.expect_response(
                lambda r: r.url == f"{km_url}/locales" and r.request.method == "POST"
            ) as upload:
                page.locator(".modal.visible").get_by_role(
                    "button", name="Import", exact=True
                ).click()
            locale = checked(upload.value, "Browser PO import").json()
            if locale["code"] != target:
                raise RuntimeError("Imported locale language differs from the configured language")
            expect(page.get_by_text("CI test locale", exact=True)).to_be_visible()
            page.screenshot(path=out / "locale-imported.png", full_page=True)
            stored = checked(
                context.request.get(f"{km_url}/locales/{locale['uuid']}/content", headers=headers),
                "PO round trip",
            )
            if stored.body() != po_path.read_bytes():
                raise RuntimeError("Downloaded locale differs from the uploaded PO")
            result["po_round_trip"] = "passed"
            project = checked(
                context.request.post(
                    f"{api}/projects",
                    headers=headers,
                    data={
                        "name": "Native locale CI review",
                        "knowledgeModelPackageUuid": imported["uuid"],
                        "visibility": "PrivateProjectVisibility",
                        "sharing": "RestrictedProjectSharing",
                        "questionTagUuids": [],
                        "documentTemplateUuid": None,
                        "formatUuid": None,
                        "language": source,
                    },
                ),
                "Test project creation",
            ).json()
            project_url = f"{client}/projects/{project['uuid']}"
            for language, title, screenshot in (
                (source, original, "source"),
                (target, translated, "translated"),
                (source, original, "source-restored"),
            ):
                page.goto(f"{project_url}/settings")
                field = page.get_by_label("Language", exact=True)
                if field.input_value() != language:
                    field.select_option(language)
                    with page.expect_navigation(wait_until="networkidle"):
                        with page.expect_response(
                            lambda r: "/settings" in r.url and r.request.method == "PUT"
                        ) as saved:
                            page.get_by_role("button", name="Save", exact=True).last.click()
                    checked(saved.value, "Project language save")
                expect(page.get_by_label("Language", exact=True)).to_have_value(language)
                page.goto(project_url)
                page.reload()
                expect(page.get_by_text(title, exact=True).first).to_be_visible()
                tour_close = page.locator(".driver-popover-close-btn")
                try:
                    tour_close.wait_for(state="visible", timeout=3000)
                except TimeoutError:
                    pass
                else:
                    tour_close.click()
                page.locator(".driver-overlay").wait_for(state="hidden")
                page.screenshot(path=out / f"questionnaire-{screenshot}.png", full_page=True)
            result["browser_import_and_language_switch"] = "passed"
        except Exception:
            page.screenshot(path=out / "failure.png", full_page=True)
            raise
        finally:
            browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, help="Translation repository; omit to check the tooling fixture."
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="Empty directory for reports and screenshots."
    )
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        parser.error("--out must be empty to avoid mixing results from different runs")
    if args.repo_root:
        repo = args.repo_root.resolve()
        config = load_translation_repository_config(repo / "translation-config.yml")
        paths = version_paths(config)
        km_path, po_path, package_id = (
            repo / paths.source_km_path,
            repo / paths.final_po_path,
            paths.package_id,
        )
        source, target = config.translation.source_language, config.translation.target_language
    else:
        km_path = ROOT / "tests/fixtures/source_inputs/dsw_root_2.7.0.km"
        po_path = ROOT / "tests/fixtures/source_inputs/common_dsw_zh_Hant.po"
        package_id, source, target = "dsw:root:2.7.0", "en", "zh_Hant"
    result = {
        "status": "failed",
        "package_id": package_id,
        "po_sha256": hashlib.sha256(po_path.read_bytes()).hexdigest(),
    }
    with tempfile.TemporaryDirectory(prefix="dsw-native-locale-") as temp:
        compose_path = Path(temp) / "compose.yml"
        compose_path.write_bytes(COMPOSE.read_bytes())
        with ExitStack() as stack:
            sockets = [stack.enter_context(socket.socket()) for _ in range(3)]
            for item in sockets:
                item.bind(("127.0.0.1", 0))
            api_port, client_port, minio_port = [item.getsockname()[1] for item in sockets]
        api = f"http://127.0.0.1:{api_port}/wizard-api"
        client = f"http://127.0.0.1:{client_port}/wizard"
        minio = f"http://127.0.0.1:{minio_port}"
        config_path = Path(temp) / "application.yml"
        key = subprocess.check_output(["openssl", "genrsa", "-traditional", "2048"], text=True)
        settings = {
            "general": {
                "clientUrl": client,
                "secret": secrets.token_hex(16),
                "rsaPrivateKey": key,
            },
            "database": {
                "connectionString": "postgresql://postgres:test-password@postgres:5432/engine-wizard"
            },
            "s3": {
                "url": "http://minio:9000",
                "username": "test-user",
                "password": "test-password",
                "bucket": "engine-wizard",
            },
            "mail": {"enabled": False},
        }
        config_path.write_text(yaml.safe_dump(settings), encoding="utf-8")
        env = {
            **os.environ,
            "DSW_TEST_CONFIG": str(config_path),
            "DSW_TEST_API_URL": api,
            "DSW_TEST_API_PORT": str(api_port),
            "DSW_TEST_CLIENT_PORT": str(client_port),
            "DSW_TEST_MINIO_PORT": str(minio_port),
        }
        command = [
            "docker",
            "compose",
            "-f",
            str(compose_path),
            "-p",
            f"dsw-locale-{uuid.uuid4().hex[:12]}",
        ]

        def compose(*arguments):
            return subprocess.run(
                [*command, *arguments],
                env=env,
                check=True,
                text=True,
                timeout=300,
            )

        try:
            compose("up", "-d")
            result["images"] = {
                name: service["image"]
                for name, service in yaml.safe_load(compose_path.read_text())["services"].items()
            }
            verify_browser(
                api,
                client,
                minio,
                km_path,
                po_path,
                package_id,
                source,
                target,
                out,
                result,
            )
            result["status"] = "passed"
        finally:
            try:
                compose("down", "--volumes", "--remove-orphans")
            finally:
                (out / "result.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                print(f"Native DSW acceptance: {result['status']}", flush=True)


if __name__ == "__main__":
    main()
