"""Minimal single-socket OSC client for Ardour's built-in OSC surface.

Ardour (https://ardour.org) has first-party, built-in OSC support (no
separate plugin or Remote Script needed) — enable it in Preferences >
Control Surfaces > Open Sound Control (OSC), leaving "Port Mode" on its
default "Auto" setting. In Auto mode, confirmed in Ardour's manual,
"Ardour will send OSC messages back to the port messages from that
surface are received from" — i.e. it replies to the exact address/port a
request came from. That means the client must send and receive on the
*same* UDP socket, which is what this module does (unlike AbletonOSC's
fixed send/receive port pair).

Default listen port is 3819 (documented in Ardour's manual).
"""

from __future__ import annotations

import socket
import time
from typing import Any

from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3819
DEFAULT_TIMEOUT = 2.0


class ArdourOSCTimeout(RuntimeError):
    """Raised when Ardour doesn't reply within the timeout."""


class ArdourOSCClient:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._addr = (host, port)
        self._timeout = timeout
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((host, 0))
        self._sock.settimeout(timeout)

    def _send(self, address: str, *args: Any) -> None:
        builder = OscMessageBuilder(address=address)
        for arg in args:
            builder.add_arg(arg)
        self._sock.sendto(builder.build().dgram, self._addr)

    def _recv_one(self) -> OscMessage:
        try:
            data, _ = self._sock.recvfrom(65536)
        except socket.timeout as exc:
            raise ArdourOSCTimeout(
                f"No reply from Ardour within {self._timeout}s. Is Ardour "
                "running with OSC enabled (Preferences > Control Surfaces "
                "> Open Sound Control (OSC), Port Mode = Auto)? See README.md."
            ) from exc
        return OscMessage(data)

    def query(self, address: str, *args: Any) -> tuple:
        """Send `address` and return the single reply's argument tuple."""
        self._send(address, *args)
        return tuple(self._recv_one().params)

    def query_list(
        self, address: str, end_marker: str, *args: Any, overall_timeout: float | None = None
    ) -> list[tuple]:
        """Send `address` and collect replies at the same address until one
        whose first argument equals `end_marker` arrives.

        Used for /strip/list, whose replies all arrive at "/reply": each
        track/bus is one message, followed by a terminator message whose
        first argument is the literal string "end_route_list".
        """
        deadline = time.monotonic() + (overall_timeout or self._timeout * 10)
        self._send(address, *args)
        results = []
        while True:
            if time.monotonic() > deadline:
                raise ArdourOSCTimeout(
                    f"Ardour did not send an {end_marker!r} terminator for "
                    f"{address} within {overall_timeout or self._timeout * 10}s."
                )
            msg = self._recv_one()
            params = tuple(msg.params)
            if params and params[0] == end_marker:
                return results
            results.append(params)

    def close(self) -> None:
        self._sock.close()
