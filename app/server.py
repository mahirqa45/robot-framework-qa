"""Loopback-only demonstration API; role fields simulate authorization, not real identity."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from app.service import DomainError, OrderService

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, code, value):
        data = json.dumps(value).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def dispatch(self):
        try:
            parts = urlsplit(self.path).path.strip("/").split("/")
            if self.command == "GET" and parts == ["health"]:
                return self.respond(200, {"status": "ok"})
            if len(parts) not in (3, 4) or parts[0] != "clients" or parts[2] != "orders":
                raise DomainError(404, "Route not found")
            if self.command == "POST" and len(parts) == 3:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    raise DomainError(400, "Invalid request size")
                payload = json.loads(self.rfile.read(length))
                return self.respond(201, self.server.service.create(parts[1], payload))
            if self.command == "GET" and len(parts) == 4:
                return self.respond(200, self.server.service.get(parts[1], int(parts[3])))
            raise DomainError(404, "Route not found")
        except DomainError as error:
            self.respond(error.status, {"error": error.message})
        except (ValueError, TypeError):
            self.respond(400, {"error": "Malformed request"})
        except Exception:
            self.respond(500, {"error": "Internal service error"})

    do_POST = dispatch
    do_GET = dispatch

class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, service, port=0):
        self.service = service
        super().__init__(("127.0.0.1", port), Handler)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--database", default="orders.sqlite")
    args = parser.parse_args()
    service = OrderService(args.database)
    with Server(service, args.port) as server:
        print(f"Demo API: http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    service.close()
