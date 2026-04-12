#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Server example - Simple HTTP server that exposes rtop stats as JSON.
Requires: Flask (pip install flask)
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from rtop import rtop


class RtopHandler(BaseHTTPRequestHandler):
    """HTTP request handler that serves rtop stats."""

    def do_GET(self):
        rockchip = rtop(open_client=True)
        if not rockchip.ok():
            self.send_error(503, "rtop service not available")
            return

        stats = {
            'cpu': dict(rockchip.cpu),
            'gpu': dict(rockchip.gpu) if rockchip.gpu else None,
            'npu': dict(rockchip.npu) if rockchip.npu else None,
            'memory': dict(rockchip.memory) if rockchip.memory else None,
            'temperature': dict(rockchip.temperature) if rockchip.temperature else None,
            'hardware': dict(rockchip.hardware) if rockchip.hardware else None,
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(stats, default=str).encode())


def main():
    server = HTTPServer(('0.0.0.0', 8080), RtopHandler)
    print("rtop stats server running on http://0.0.0.0:8080")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
