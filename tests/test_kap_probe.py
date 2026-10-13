"""Synthetic offline tests: NEVER contact MKK during CI."""
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request
from ieai.kap_probe import DEV_URL, NoRedirects, probe_members


class FakeResponse:
    status = 200
    headers = {"Content-Type": "application/json; charset=utf-8"}

    def __init__(self, raw=b'[{"id":"TEST001","stockCode":"TEST"}]', url=DEV_URL):
        self.raw = raw
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def read(self, count):
        return self.raw[:count]


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response = response or FakeResponse()
        self.error = error
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error:
            raise self.error
        return self.response


class KapDevProbeTests(unittest.TestCase):
    def test_one_request_no_auth_and_no_empirical_promotion(self):
        with tempfile.TemporaryDirectory() as temp:
            client = FakeOpener()
            report = probe_members(Path(temp) / "test-output", opener=client)
            self.assertEqual(len(client.calls), 1)
            request, timeout = client.calls[0]
            self.assertEqual(request.full_url, DEV_URL)
            self.assertEqual(request.get_method(), "GET")
            self.assertIsNone(request.get_header("Authorization"))
            self.assertNotIn("apiKey", request.full_url)
            self.assertEqual(report["status"], "DEV_CONNECTIVITY_ONLY")
            self.assertFalse(report["allowed_for_empirical_research"])
            self.assertFalse(report["research_dataset_complete"])
            output = Path(temp) / "test-output"
            self.assertEqual(json.loads((output / "members-dev.json").read_text())[0]["id"], "TEST001")
            with self.assertRaisesRegex(ValueError, "already exists"):
                probe_members(output, opener=client)
            self.assertEqual(len(client.calls), 1)

    def test_no_cross_host_redirects(self):
        self.assertIsNone(NoRedirects().redirect_request(
            Request(DEV_URL), None, 302, "Moved", {}, "https://evil.example/collect"
        ))

    def test_http_error_does_not_log_response_or_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "failed"
            fake_error = HTTPError(DEV_URL, 401, "SECRET_RESPONSE_TEXT", {}, None)
            with self.assertRaisesRegex(ValueError, "HTTP 401") as caught:
                probe_members(output, opener=FakeOpener(error=fake_error))
            self.assertNotIn("SECRET_RESPONSE_TEXT", str(caught.exception))
            self.assertFalse(output.exists())

    def test_invalid_json_and_redirect_url_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "valid JSON"):
                probe_members(Path(temp) / "bad", opener=FakeOpener(response=FakeResponse(b"not-json")))
            with self.assertRaisesRegex(ValueError, "Unexpected response URL"):
                probe_members(Path(temp) / "wrong", opener=FakeOpener(
                    response=FakeResponse(url="https://evil.example/data")))
            self.assertFalse((Path(temp) / "wrong").exists())

    def test_limit_rejects_oversize(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "exceeds"):
                probe_members(Path(temp) / "big", opener=FakeOpener(
                    response=FakeResponse(b'{"much":"larger"}')), max_bytes=5)


if __name__ == "__main__":
    unittest.main()
