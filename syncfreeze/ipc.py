import json
import socket
import threading

IPC_PORT = 49152
IPC_HOST = "127.0.0.1"


class IPCServer:
    """TCP server that listens for commands from CLI invocations."""

    def __init__(self, handler):
        """
        Args:
            handler: Callable that takes a dict command and returns a dict response.
        """
        self._handler = handler
        self._server_socket = None
        self._thread = None
        self._running = False

    def start(self):
        """Start the IPC server. Raises OSError if port is already in use."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((IPC_HOST, IPC_PORT))
        self._server_socket.listen(5)
        self._server_socket.settimeout(1.0)  # Allow periodic check for shutdown
        self._running = True

        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the IPC server."""
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass

    def _serve(self):
        """Main server loop."""
        while self._running:
            try:
                conn, _ = self._server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn):
        """Handle a single client connection."""
        try:
            conn.settimeout(5.0)
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break

            if data:
                command = json.loads(data.decode("utf-8").strip())
                response = self._handler(command)
                conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
        except (json.JSONDecodeError, socket.timeout, OSError):
            try:
                error_resp = json.dumps({"error": "Invalid request"}) + "\n"
                conn.sendall(error_resp.encode("utf-8"))
            except OSError:
                pass
        finally:
            conn.close()


def send_command(command):
    """
    Send a command to the running SyncFreeze instance.

    Args:
        command: Dict to send (e.g., {"action": "pause", "minutes": 5})

    Returns:
        Dict response from the server.

    Raises:
        ConnectionRefusedError: If no instance is running.
        OSError: If the port is unreachable.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    try:
        sock.connect((IPC_HOST, IPC_PORT))
        sock.sendall((json.dumps(command) + "\n").encode("utf-8"))

        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break

        return json.loads(data.decode("utf-8").strip())
    finally:
        sock.close()


def is_instance_running():
    """Check if another SyncFreeze instance is already running."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect((IPC_HOST, IPC_PORT))
        sock.close()
        return True
    except (ConnectionRefusedError, OSError):
        return False
