from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Event, Thread
import unittest
from unittest.mock import patch

import host


@contextmanager
def serve(handler):
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02})
        thread.start()
        try:
            yield server.server_port
        finally:
            server.shutdown()
            thread.join()


class StreamingTests(unittest.TestCase):
    def check_response(self, second, expected, mime="text/event-stream"):
        first = b'data: {"choices":[{"delta":{"content":"Halo "}}]}\r\n\r\n'
        release = Event()
        received = []

        class Provider(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                received.append((self.headers["Authorization"], payload))
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.end_headers()
                if mime == "text/event-stream":
                    self.wfile.write(first)
                    self.wfile.flush()
                    release.wait(3)
                self.wfile.write(second)

        def request(port, path, payload=None):
            conn = HTTPConnection("127.0.0.1", port, timeout=3)
            self.addCleanup(conn.close)
            conn.request("GET" if payload is None else "POST", path,
                         None if payload is None else json.dumps(payload),
                         {"Host": "127.0.0.1:4173", "Content-Type": "application/json"})
            return conn.getresponse()

        with serve(Provider) as upstream, serve(host.Handler) as downstream, patch(
            "host.SESSION", (f"http://127.0.0.1:{upstream}/chat/completions", "test", "fixture-key")
        ):
            self.addCleanup(release.set)
            try:
                response = request(downstream, "/api/ai/stream", {"input": "Ringkas", "context": "sampel"})
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), "application/x-ndjson")
                if mime == "text/event-stream":
                    self.assertEqual(json.loads(response.readline()), {"delta": "Halo "})
                    health = request(downstream, "/api/health")
                    self.assertTrue(json.load(health)["aiStreaming"])
                release.set()
                self.assertEqual([json.loads(line) for line in response], expected)
                key, payload = received[0]
                self.assertEqual(key, "Bearer fixture-key")
                self.assertIs(payload["stream"], True)
                self.assertEqual(json.loads(payload["messages"][1]["content"])["documentContext"], "sampel")
            finally:
                release.set()

    def test_stream_flushes_deltas_and_signals_completion(self):
        self.check_response(
            b'data: {"choices":[{"delta":{"content":"dunia"}}]}\n\n'
            b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
            b'data: [DONE]\n\n',
            [{"delta": "dunia"}, {"done": True}],
        )

    def test_interrupted_stream_is_not_marked_complete(self):
        self.check_response(b'', [{"error": host.AI_ERROR}])

    def test_length_limited_response_is_not_marked_complete(self):
        self.check_response(
            b'data: {"choices":[{"delta":{},"finish_reason":"length"}]}\n\ndata: [DONE]\n\n',
            [{"error": host.AI_ERROR}],
        )

    def test_json_provider_works_as_single_delta(self):
        self.check_response(
            b'{"choices":[{"message":{"content":"Halo dunia"},"finish_reason":"stop"}]}',
            [{"delta": "Halo dunia"}, {"done": True}],
            mime="application/json",
        )

    def test_connection_check_uses_a_fixed_prompt_without_document_or_returned_secret(self):
        received = []

        class Provider(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"choices":[{"message":{"content":"OK"},"finish_reason":"stop"}]}')

        with serve(Provider) as upstream, serve(host.Handler) as downstream, patch(
            "host.SESSION", (f"http://127.0.0.1:{upstream}/chat/completions", "test", "fixture-key")
        ):
            conn = HTTPConnection("127.0.0.1", downstream, timeout=3)
            self.addCleanup(conn.close)
            conn.request("POST", "/api/ai/check", json.dumps({"context": "never sent"}),
                         {"Host": "127.0.0.1:4173", "Content-Type": "application/json"})
            response = conn.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response), {"reachable": True})
            context = json.loads(received[0]["messages"][1]["content"])
            self.assertEqual(context["documentContext"], "")
            self.assertEqual(context["instruction"], "Reply briefly with OK.")

    def test_changing_endpoint_requires_a_new_explicit_key(self):
        with serve(host.Handler) as port, patch(
            "host.SESSION", ("https://initial.example/chat", "old", "initial-key")
        ):
            conn = HTTPConnection("127.0.0.1", port, timeout=3)
            self.addCleanup(conn.close)
            for url, has_key in [("https://initial.example/chat", True), ("https://new.example/chat", False)]:
                conn.request("POST", "/api/ai/settings", json.dumps({"url": url, "model": "new", "apiKey": ""}),
                             {"Host": "127.0.0.1:4173", "Content-Type": "application/json"})
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                self.assertIs(json.load(response)["hasApiKey"], has_key)
