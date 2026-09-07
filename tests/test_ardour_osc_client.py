"""Regression tests for Issue #38: ArdourOSCClient.query_list()'s
overall_timeout budget wasn't actually enforced per-reply -- a single
gap between replies longer than the fixed per-socket self._timeout
aborted the whole call even when the overall_timeout budget had time
left.

These tests use a FakeSocket instead of a real Ardour/network
connection, so no live Ardour instance is required or assumed.

mcp-ardour/ardour_mcp depends on python-osc (see mcp-ardour/pyproject.toml),
which this repo's CI does not install (see .github/workflows/checks.yml --
it only byte-compiles mcp-*/ packages, never imports them). This module
therefore skips cleanly, not silently, when python-osc/mcp-ardour aren't
importable, rather than breaking `unittest discover` for everyone else.
"""

from __future__ import annotations

import pathlib
import socket as socket_module
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "mcp-ardour"))

try:
    from ardour_mcp.osc_client import ArdourOSCClient, ArdourOSCTimeout  # noqa: E402
    from pythonosc.osc_message_builder import OscMessageBuilder  # noqa: E402

    _IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - environment-dependent
    _IMPORT_ERROR = exc


def _build_reply(*args) -> bytes:
    builder = OscMessageBuilder(address="/reply")
    for arg in args:
        builder.add_arg(arg)
    return builder.build().dgram


class FakeSocket:
    """Stand-in for the real UDP socket, scripted as a sequence of
    (delay, message_bytes) pairs. recvfrom() raises socket.timeout if
    the *currently configured* settimeout() value is smaller than the
    next scripted message's delay -- simulating "this reply is still
    `delay` seconds away, which is longer than this call is willing to
    wait" without actually sleeping in the test.
    """

    def __init__(self, script: list[tuple[float, bytes]]) -> None:
        self._script = list(script)
        self._timeout: float | None = None

    def settimeout(self, value: float) -> None:
        self._timeout = value

    def sendto(self, data: bytes, addr: tuple) -> None:
        pass

    def recvfrom(self, bufsize: int):
        if not self._script:
            raise socket_module.timeout()
        delay, data = self._script[0]
        if self._timeout is not None and delay > self._timeout:
            self._script[0] = (delay - self._timeout, data)
            raise socket_module.timeout()
        self._script.pop(0)
        return data, ("127.0.0.1", 3819)

    def close(self) -> None:
        pass


@unittest.skipIf(_IMPORT_ERROR is not None, f"python-osc/ardour_mcp not importable: {_IMPORT_ERROR}")
class QueryListOverallTimeoutBudgetTests(unittest.TestCase):
    def _client_with_script(self, script: list[tuple[float, bytes]], timeout: float = 2.0) -> "ArdourOSCClient":
        client = ArdourOSCClient(timeout=timeout)
        client._sock.close()
        client._sock = FakeSocket(script)
        # __init__ already called settimeout(timeout) on the real socket
        # before we swapped it out -- replay that on the fake so its
        # starting state matches what the real client would have.
        client._sock.settimeout(timeout)
        return client

    def test_reply_gap_longer_than_per_call_timeout_still_succeeds_within_budget(self):
        # Each reply is 3s "away" -- longer than the 2.0s per-socket
        # timeout -- but the overall budget is 20s. Before the fix, the
        # first recvfrom() would time out at the fixed 2.0s and abort
        # the whole query_list() call.
        script = [
            (3.0, _build_reply("track-1")),
            (3.0, _build_reply("end_route_list")),
        ]
        client = self._client_with_script(script, timeout=2.0)
        results = client.query_list("/strip/list", "end_route_list", overall_timeout=20.0)
        self.assertEqual(results, [("track-1",)])

    def test_exceeding_the_overall_budget_raises_citing_the_overall_value_not_the_per_call_one(self):
        script = [(100.0, _build_reply("end_route_list"))]
        client = self._client_with_script(script, timeout=2.0)
        with self.assertRaises(ArdourOSCTimeout) as ctx:
            client.query_list("/strip/list", "end_route_list", overall_timeout=5.0)
        self.assertIn("5.0", str(ctx.exception))
        self.assertNotIn("2.0s.", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
