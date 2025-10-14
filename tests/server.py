import os
from http.server import BaseHTTPRequestHandler, HTTPServer

class HelloHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = os.getenv("CONTENT", "(default content)")  
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    server_address = ("", port)
    httpd = HTTPServer(server_address, HelloHandler)
    httpd.serve_forever()
