#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright (c) 2026 Batuhan Berkay Aydın.
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

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
