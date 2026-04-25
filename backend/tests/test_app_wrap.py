"""
Tests for the /api/wrap-text endpoint added to backend/app.py in this PR.
"""
import sys
import pathlib
import pytest

# Ensure the backend package root is on the path.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

# conftest.py mocks torch / VocalRemovalModelHandler before this import.
import app as flask_app


@pytest.fixture()
def client():
    """Return a Flask test client with TESTING mode enabled."""
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# /api/wrap-text  – error cases
# ---------------------------------------------------------------------------

class TestWrapTextEndpointErrors:

    def test_no_body_returns_400(self, client):
        res = client.post("/api/wrap-text", content_type="application/json")
        assert res.status_code == 400

    def test_empty_json_object_returns_400(self, client):
        res = client.post("/api/wrap-text",
                          json={})
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data

    def test_missing_text_key_returns_400(self, client):
        res = client.post("/api/wrap-text",
                          json={"font_size": 64})
        assert res.status_code == 400
        data = res.get_json()
        assert data["error"] == "text required"

    def test_wrong_content_type_returns_4xx(self, client):
        """Sending non-JSON body results in a 4xx client error.

        Flask 2.x returns 400 (get_json() → None → our handler returns 400).
        Flask 3.x returns 415 Unsupported Media Type before our handler runs.
        Either way the request is rejected with a client error status.
        """
        res = client.post("/api/wrap-text",
                          data="not json",
                          content_type="text/plain")
        assert 400 <= res.status_code < 500


# ---------------------------------------------------------------------------
# /api/wrap-text  – success cases
# ---------------------------------------------------------------------------

class TestWrapTextEndpointSuccess:

    def test_short_text_returns_single_line(self, client):
        res = client.post("/api/wrap-text",
                          json={"text": "Hello world"})
        assert res.status_code == 200
        data = res.get_json()
        assert "lines" in data
        assert isinstance(data["lines"], list)
        assert len(data["lines"]) >= 1

    def test_response_lines_are_strings(self, client):
        res = client.post("/api/wrap-text",
                          json={"text": "Some text"})
        assert res.status_code == 200
        for line in res.get_json()["lines"]:
            assert isinstance(line, str)

    def test_text_key_required_value_used(self, client):
        """The 'text' value should appear somewhere in the returned lines."""
        res = client.post("/api/wrap-text",
                          json={"text": "unique_word"})
        assert res.status_code == 200
        combined = " ".join(res.get_json()["lines"])
        assert "unique_word" in combined

    def test_long_text_returns_multiple_lines(self, client):
        """A very long string should be split into multiple lines."""
        long_text = "word " * 30  # definitely exceeds default chars_per_line
        res = client.post("/api/wrap-text",
                          json={"text": long_text.strip()})
        assert res.status_code == 200
        lines = res.get_json()["lines"]
        assert len(lines) > 1

    def test_custom_font_size_affects_wrapping(self, client):
        """A large font_size should produce more lines for the same text."""
        text = "one two three four five six seven eight nine ten"
        res_large = client.post("/api/wrap-text",
                                json={"text": text, "font_size": 256})
        res_small = client.post("/api/wrap-text",
                                json={"text": text, "font_size": 16})
        assert res_large.status_code == 200
        assert res_small.status_code == 200
        # Large font → fewer chars per line → more lines
        assert len(res_large.get_json()["lines"]) >= len(res_small.get_json()["lines"])

    def test_default_font_size_used_when_omitted(self, client):
        """Omitting font_size should not raise and should return a valid result."""
        res = client.post("/api/wrap-text",
                          json={"text": "test line"})
        assert res.status_code == 200
        data = res.get_json()
        assert "lines" in data
        assert len(data["lines"]) >= 1

    def test_numeric_text_coerced_to_string(self, client):
        """The endpoint calls str(data['text']), so integers should work."""
        res = client.post("/api/wrap-text",
                          json={"text": 12345})
        assert res.status_code == 200
        lines = res.get_json()["lines"]
        assert "12345" in "".join(lines)

    def test_empty_string_returns_list(self, client):
        """An empty text should return a list (possibly with one empty string)."""
        res = client.post("/api/wrap-text",
                          json={"text": ""})
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data["lines"], list)

    def test_lines_joined_reconstruct_original_words(self, client):
        """All words from the original text should appear in the wrapped output."""
        text = "alpha bravo charlie delta echo foxtrot golf hotel"
        res = client.post("/api/wrap-text", json={"text": text})
        assert res.status_code == 200
        combined = " ".join(res.get_json()["lines"])
        for word in text.split():
            assert word in combined

    def test_get_method_not_allowed(self, client):
        """The endpoint only accepts POST."""
        res = client.get("/api/wrap-text")
        assert res.status_code == 405