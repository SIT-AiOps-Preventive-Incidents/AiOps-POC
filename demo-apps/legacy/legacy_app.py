"""A 'legacy' app with NO OpenTelemetry: orders (port 8200) calls stock (port 8201). Stdlib only."""
import json, random, sys, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
ROLE, PORT = sys.argv[1], int(sys.argv[2])
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if ROLE == "orders":
            stock = json.loads(urllib.request.urlopen("http://127.0.0.1:8201/stock", timeout=5).read())
            body = {"order": random.randint(1000, 9999), "stock": stock["left"]}
        else:
            time.sleep(random.uniform(0.005, 0.03))
            body = {"left": random.randint(0, 50)}
        data = json.dumps(body).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(data)
ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
