import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx


def load_phase3_script() -> ModuleType:
    script_path = Path(__file__).resolve().parents[4] / "scripts" / "phase3_run_all_pipeline.py"
    spec = importlib.util.spec_from_file_location("phase3_run_all_pipeline_for_test", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load script spec: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeStreamResponse:
    def __init__(self, status_code: int, body: bytes = b"") -> None:
        self.request = httpx.Request("GET", "https://example.test/file.lzh")
        self.response = httpx.Response(status_code, request=self.request, content=body)
        self.status_code = status_code
        self.body = body

    def __enter__(self) -> "FakeStreamResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        self.response.raise_for_status()

    def iter_bytes(self) -> list[bytes]:
        return [self.body]


def test_retryable_status_code_policy():
    module = load_phase3_script()

    assert module.is_retryable_status_code(429)
    assert module.is_retryable_status_code(500)
    assert module.is_retryable_status_code(504)
    assert not module.is_retryable_status_code(404)
    assert not module.is_retryable_status_code(403)


def test_retry_delay_seconds_uses_exponential_backoff():
    module = load_phase3_script()

    assert module.retry_delay_seconds(2.0, 0) == 2.0
    assert module.retry_delay_seconds(2.0, 1) == 4.0
    assert module.retry_delay_seconds(2.0, 2) == 8.0


def test_download_to_path_retries_503_then_writes_file(tmp_path, monkeypatch):
    module = load_phase3_script()
    calls: list[int] = []

    def fake_stream(*args: Any, **kwargs: Any) -> FakeStreamResponse:
        calls.append(1)
        if len(calls) == 1:
            return FakeStreamResponse(503)
        return FakeStreamResponse(200, b"ok")

    monkeypatch.setattr(module.httpx, "stream", fake_stream)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)

    destination = tmp_path / "file.lzh"
    retry_config = module.DownloadRetryConfig(
        retries=1,
        backoff_seconds=0,
        timeout_seconds=1,
    )

    assert module.download_to_path("https://example.test/file.lzh", destination, retry_config)
    assert calls == [1, 1]
    assert destination.read_bytes() == b"ok"
    assert not destination.with_name("file.lzh.part").exists()


def test_download_to_path_does_not_retry_404(tmp_path, monkeypatch):
    module = load_phase3_script()
    calls: list[int] = []

    def fake_stream(*args: Any, **kwargs: Any) -> FakeStreamResponse:
        calls.append(1)
        return FakeStreamResponse(404)

    monkeypatch.setattr(module.httpx, "stream", fake_stream)

    destination = tmp_path / "missing.lzh"
    retry_config = module.DownloadRetryConfig(
        retries=3,
        backoff_seconds=0,
        timeout_seconds=1,
    )

    assert not module.download_to_path(
        "https://example.test/missing.lzh", destination, retry_config
    )
    assert calls == [1]
    assert not destination.exists()
