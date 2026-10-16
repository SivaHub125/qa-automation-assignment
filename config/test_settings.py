"""Unit tests for environment settings."""

import dataclasses
from pathlib import Path

import pytest

from config.settings import Settings

BASE = Settings(env="test", base_url="http://127.0.0.1:5055", api_base_url="https://example.test",
                headless=True, slow_mo_ms=0, default_timeout_ms=1000, start_app=True,
                self_heal=False, reports_dir=Path("reports"))


@pytest.mark.parametrize(
    "url, port",
    [("http://127.0.0.1:5055", 5055), ("http://emi.test", 80), ("https://emi.test", 443)],
)
def test_app_port_follows_url_and_scheme(url, port):
    assert dataclasses.replace(BASE, base_url=url).app_port == port
