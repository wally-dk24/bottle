"""Adapter app: exposes bottle's static_file() over HTTP for the ProofDeploy demo.

Run with the bottle under test on the import path, e.g.:
    PYTHONPATH=/tmp/wt-buggy python3 demo/app.py

Endpoints:
  GET /health              -> {"status": "ok"}
  GET /files/<filename>    -> bottle.static_file(filename, root=demo/static)
"""
import os
from wsgiref.simple_server import make_server

import bottle

STATIC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
PORT = 8471

app = bottle.Bottle()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/files/<filename>")
def serve(filename):
    return bottle.static_file(filename, root=STATIC_ROOT)


if __name__ == "__main__":
    make_server("127.0.0.1", PORT, app).serve_forever()
