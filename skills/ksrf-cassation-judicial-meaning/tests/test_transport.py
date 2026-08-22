import shutil
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from judicial_meaning.collection import CurlTransport


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = "<html><body>Официальная fixture-страница</body></html>".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


@unittest.skipUnless(shutil.which("curl"), "optional system curl is unavailable")
class CurlTransportTests(unittest.TestCase):
    def test_curl_fallback_keeps_tls_verification_profile_and_records_helper(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            response = CurlTransport(timeout=5).get(
                f"http://127.0.0.1:{server.server_port}/fixture"
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(200, response.status)
        self.assertIn("Официальная", response.body.decode("utf-8"))
        self.assertEqual("curl", response.headers["x-judicial-meaning-transport"])
        self.assertNotIn("--insecure", response.headers["x-judicial-meaning-command-profile"])


if __name__ == "__main__":
    unittest.main()
