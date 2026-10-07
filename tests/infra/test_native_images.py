"""Image preparation retries network failures, not invalid inputs or runtime checks."""

from __future__ import annotations

import subprocess
from unittest.mock import Mock

import pytest

from tests.native_locale import images

COMMAND = ["docker", "compose", "-f", "/tmp/compose.yml", "-p", "dsw-test"]
ENV = {"DSW_TEST_API_PORT": "12345"}
REGISTRY_ERROR = (
    "failed to solve: unexpected status from HEAD request to "
    "https://registry-1.docker.io/v2/library/debian/manifests/sha256:abcd: "
    "500 Internal Server Error\n"
)


def result(code=0, output=""):
    return subprocess.CompletedProcess(COMMAND, code, stdout=output)


@pytest.fixture
def runner(monkeypatch):
    run = Mock()
    monkeypatch.setattr(images.subprocess, "run", run)
    monkeypatch.setattr(images.time, "sleep", Mock())
    monkeypatch.setattr(images.time, "monotonic", lambda: 0)
    return run


def invocations(runner):
    return [call.args[0][len(COMMAND) :] for call in runner.call_args_list]


def test_preparation_pulls_before_building(runner):
    runner.side_effect = [result(), result()]
    images.prepare_images(COMMAND, env=ENV)
    assert invocations(runner) == [["pull", "--ignore-buildable"], ["build"]]
    assert all(call.kwargs["env"] == ENV for call in runner.call_args_list)
    assert all(call.kwargs["timeout"] == 300 for call in runner.call_args_list)
    assert all(call.kwargs["stderr"] == subprocess.STDOUT for call in runner.call_args_list)
    images.time.sleep.assert_not_called()


@pytest.mark.parametrize("stage", ["pull", "build"])
def test_registry_500_retries_only_the_failed_image_stage(runner, capsys, stage):
    runner.side_effect = (
        [result(1, REGISTRY_ERROR), result(), result()]
        if stage == "pull"
        else [result(), result(1, REGISTRY_ERROR), result()]
    )
    images.prepare_images(COMMAND, env=ENV)
    assert invocations(runner) == (
        [["pull", "--ignore-buildable"], ["pull", "--ignore-buildable"], ["build"]]
        if stage == "pull"
        else [["pull", "--ignore-buildable"], ["build"], ["build"]]
    )
    images.time.sleep.assert_called_once_with(5)
    assert REGISTRY_ERROR in capsys.readouterr().out


@pytest.mark.parametrize(
    "output",
    [
        "received unexpected HTTP status: 502 Bad Gateway",
        "unexpected status code 503 Service Unavailable",
        "HTTP/1.1 504 Gateway Timeout",
        "net/http: TLS handshake timeout",
        "read tcp: i/o timeout",
        "read: connection reset by peer",
        "failed to copy: unexpected EOF",
    ],
)
def test_recognized_transient_download_failures_retry(runner, output):
    runner.side_effect = [result(1, output), result(), result()]
    images.prepare_images(COMMAND, env=ENV)
    assert runner.call_count == 3
    images.time.sleep.assert_called_once_with(5)


@pytest.mark.parametrize(
    "output",
    [
        "unexpected status from HEAD request: 401 Unauthorized",
        "unexpected status from HEAD request: 403 Forbidden",
        "unexpected status from HEAD request: 404 Not Found",
        "unexpected status from HEAD request: 429 Too Many Requests",
        "manifest unknown",
        "checksum mismatch",
        "failed to solve: process dpkg-deb did not complete successfully: exit code: 2",
        "failed to read dockerfile: no such file or directory",
        "x509: certificate signed by unknown authority",
        "no space left on device",
        "unknown failure",
    ],
)
def test_non_transient_failures_stop_immediately(runner, output):
    runner.return_value = result(1, output)
    with pytest.raises(subprocess.CalledProcessError) as raised:
        images.prepare_images(COMMAND, env=ENV)
    assert raised.value.output == output
    assert runner.call_count == 1
    images.time.sleep.assert_not_called()


def test_repeated_registry_failure_stops_after_three_attempts(runner):
    runner.return_value = result(1, REGISTRY_ERROR)
    with pytest.raises(subprocess.CalledProcessError) as raised:
        images.prepare_images(COMMAND, env=ENV)
    assert raised.value.returncode == 1
    assert runner.call_count == 3
    assert [call.args for call in images.time.sleep.call_args_list] == [(5,), (10,)]
    assert all(args == ["pull", "--ignore-buildable"] for args in invocations(runner))


def test_pull_and_build_share_the_same_deadline(runner, monkeypatch):
    runner.side_effect = [result(), result()]
    monkeypatch.setattr(images.time, "monotonic", Mock(side_effect=[0, 100, 240]))
    images.prepare_images(COMMAND, env=ENV)
    assert [call.kwargs["timeout"] for call in runner.call_args_list] == [200, 60]


def test_expired_retry_budget_does_not_sleep_or_run_again(runner, monkeypatch):
    runner.return_value = result(1, REGISTRY_ERROR)
    monkeypatch.setattr(images.time, "monotonic", Mock(side_effect=[0, 0, 301]))
    with pytest.raises(subprocess.TimeoutExpired):
        images.prepare_images(COMMAND, env=ENV)
    assert runner.call_count == 1
    images.time.sleep.assert_not_called()


def test_expired_budget_prevents_starting_another_stage(runner, monkeypatch):
    runner.return_value = result()
    monkeypatch.setattr(images.time, "monotonic", Mock(side_effect=[0, 0, 300]))
    with pytest.raises(subprocess.TimeoutExpired):
        images.prepare_images(COMMAND, env=ENV)
    assert runner.call_count == 1


def test_subprocess_timeout_is_not_retried(runner):
    runner.side_effect = subprocess.TimeoutExpired(COMMAND, 300)
    with pytest.raises(subprocess.TimeoutExpired):
        images.prepare_images(COMMAND, env=ENV)
    assert runner.call_count == 1
    images.time.sleep.assert_not_called()
