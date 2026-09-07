"""Minimal request/reply client for AbletonOSC.

AbletonOSC (https://github.com/ideoforms/AbletonOSC) is a Remote Script
that must be installed inside Ableton Live and selected as a Control
Surface (Preferences > Link / Tempo / MIDI). It listens for OSC messages
on port 11000 and sends replies on port 11001, at the *same* address as
the request (e.g. request `/live/song/get/tempo` gets a reply at
`/live/song/get/tempo`).

This module only implements the request/reply plumbing (send + wait for
the matching reply). It does not know about any specific address — see
server.py for the read-only addresses this package actually calls.
"""

from __future__ import annotations

import queue
import threading
from typing import Any

from pythonosc import dispatcher as osc_dispatcher
from pythonosc import osc_server
from pythonosc.udp_client import SimpleUDPClient

DEFAULT_HOST = "127.0.0.1"
DEFAULT_SEND_PORT = 11000
DEFAULT_RECEIVE_PORT = 11001
DEFAULT_TIMEOUT = 2.0


class AbletonOSCTimeout(RuntimeError):
    """Raised when Ableton Live doesn't reply within the timeout."""


class OSCQueryClient:
    """Sends one OSC message and waits for the reply at the same address.

    Not safe for concurrent overlapping queries to the *same* address from
    multiple threads (the second query's response could be delivered to
    the first caller); astra-daw-guard's tools call this sequentially, one
    query at a time, which is enough for a read-only status adapter.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        send_port: int = DEFAULT_SEND_PORT,
        receive_port: int = DEFAULT_RECEIVE_PORT,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._client = SimpleUDPClient(host, send_port)
        self._timeout = timeout
        self._queues: dict[str, "queue.Queue[tuple]"] = {}
        self._lock = threading.Lock()

        dispatcher = osc_dispatcher.Dispatcher()
        dispatcher.set_default_handler(self._on_message)
        self._server = osc_server.ThreadingOSCUDPServer((host, receive_port), dispatcher)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def _on_message(self, address: str, *args: Any) -> None:
        with self._lock:
            q = self._queues.get(address)
        if q is not None:
            q.put(args)

    def query(self, address: str, *args: Any) -> tuple:
        """Send `address` with `args` and return the reply's argument tuple."""
        q: "queue.Queue[tuple]" = queue.Queue()
        with self._lock:
            self._queues[address] = q
        try:
            self._client.send_message(address, list(args))
            try:
                return q.get(timeout=self._timeout)
            except queue.Empty as exc:
                raise AbletonOSCTimeout(
                    f"No reply from Ableton Live for {address} within "
                    f"{self._timeout}s. Is Live running with AbletonOSC "
                    "selected as the Control Surface? See README.md."
                ) from exc
        finally:
            with self._lock:
                self._queues.pop(address, None)

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
