"""Test-wide safety net: the suite must never reach a real AI provider.

* A fake API key is set before the app loads ``.env`` (python-dotenv does not
  override variables that already exist), so the real key is never used.
* Outbound socket connections are blocked. FastAPI's TestClient runs in-process
  and needs no sockets, so any connection attempt is a bug in a test.
"""

import os
import socket

import pytest

os.environ["LLM_API_KEY"] = "test-key-offline"
os.environ["GEMINI_API_KEY"] = "test-key-offline"
os.environ["LLM_PROVIDER"] = "google_genai"
os.environ["GROQ_API_KEY"] = "test-groq-key-offline"


class NetworkBlockedError(RuntimeError):
    pass


# Loopback stays open: on Windows, asyncio builds its internal socketpair by
# connecting to 127.0.0.1. Anything else (e.g. an AI provider) is refused.
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex


def _host_of(address) -> str:
    return address[0] if isinstance(address, tuple) and address else str(address)


def _guarded_connect(self, address):
    if _host_of(address) not in _LOOPBACK_HOSTS:
        raise NetworkBlockedError(f"Network access to {address!r} is disabled in tests (would spend real API quota).")
    return _real_connect(self, address)


def _guarded_connect_ex(self, address):
    if _host_of(address) not in _LOOPBACK_HOSTS:
        raise NetworkBlockedError(f"Network access to {address!r} is disabled in tests (would spend real API quota).")
    return _real_connect_ex(self, address)


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _guarded_connect_ex)
    yield
