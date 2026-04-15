"""Websocket JSON-RPC 2.0 transport for communicating with Moonraker."""

from __future__ import annotations

import json
import threading

import websocket


class MoonrakerError(Exception):
    """JSON-RPC error returned by Moonraker."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Moonraker error {code}: {message}")


class MoonrakerDriver:
    """Synchronous websocket driver for the Moonraker JSON-RPC API.

    Provides a thread-safe interface for sending JSON-RPC 2.0 requests to a
    Moonraker instance and waiting for responses.  A background thread handles
    incoming messages and dispatches them to the appropriate callers.
    """

    def __init__(self, host: str, port: int = 7125) -> None:
        self._host = host
        self._port = port
        self._ws: websocket.WebSocket | None = None
        self._lock = threading.Lock()
        self._request_id: int = 0
        self._pending: dict[int, threading.Event] = {}
        self._responses: dict[int, dict] = {}
        self._recv_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def url(self) -> str:
        """Websocket URL for the Moonraker instance."""
        return f"ws://{self._host}:{self._port}/websocket"

    def open(self) -> None:
        """Connect to Moonraker and start the receive loop."""
        self._ws = websocket.create_connection(self.url)
        self._stop_event.clear()
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

    def close(self) -> None:
        """Disconnect from Moonraker and stop the receive loop."""
        self._stop_event.set()
        if self._ws is not None:
            self._ws.close()
        if self._recv_thread is not None:
            self._recv_thread.join()
        self._ws = None

    def _recv_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                raw = self._ws.recv()  # type: ignore[union-attr]
            except websocket.WebSocketConnectionClosedException:
                break
            except Exception:
                break

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_id = data.get("id")
            if msg_id is not None and msg_id in self._pending:
                self._responses[msg_id] = data
                self._pending[msg_id].set()

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def call_method(self, method: str, params: dict | None = None, timeout: float = 10.0) -> dict:
        """Send a JSON-RPC request and block until the response arrives.

        Args:
            method: The JSON-RPC method name.
            params: Optional parameters for the method.
            timeout: Seconds to wait for a response before raising ``TimeoutError``.

        Returns:
            The ``result`` field of the JSON-RPC response.

        Raises:
            MoonrakerError: If the response contains a JSON-RPC error.
            TimeoutError: If no response is received within *timeout* seconds.
        """
        req_id = self._next_id()
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": req_id,
        }

        event = threading.Event()
        self._pending[req_id] = event

        with self._lock:
            self._ws.send(json.dumps(request))  # type: ignore[union-attr]

        event.wait(timeout=timeout)

        self._pending.pop(req_id, None)

        if not event.is_set():
            self._responses.pop(req_id, None)
            raise TimeoutError(f"Timed out waiting for response to {method!r} (id={req_id})")

        response = self._responses.pop(req_id)

        if "error" in response:
            err = response["error"]
            raise MoonrakerError(code=err["code"], message=err["message"])

        return response["result"]

    # -- convenience methods --------------------------------------------------

    def query_objects(self, objects: dict[str, list[str] | None]) -> dict:
        """Query one or more printer objects for their current state."""
        return self.call_method("printer.objects.query", {"objects": objects})

    def list_objects(self) -> list[str]:
        """Return the list of available printer objects."""
        result = self.call_method("printer.objects.list")
        return result["objects"]

    def send_gcode(self, script: str) -> dict:
        """Execute a G-code script on the printer."""
        return self.call_method("printer.gcode.script", {"script": script})

    def get_printer_info(self) -> dict:
        """Retrieve general printer information."""
        return self.call_method("printer.info")

    def emergency_stop(self) -> dict:
        """Trigger an emergency stop."""
        return self.call_method("printer.emergency_stop")

    def start_print(self, filename: str) -> dict:
        """Start printing a file that has been uploaded to Moonraker."""
        return self.call_method("printer.print.start", {"filename": filename})
