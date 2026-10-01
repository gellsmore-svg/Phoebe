"""Disposable opaque application. Only the harness knows injected ground truth."""
import http.server
import json
from pathlib import Path

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def do_GET(self):
        mode=Path('/tmp/fixture-mode').read_text().strip() if Path('/tmp/fixture-mode').exists() else 'normal'
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
        self.wfile.write(json.dumps({'ok':True if self.path=='/ready' else mode!='semantic-error','count':1}).encode())

http.server.ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
