"""
Tests for person2.hash_generator
─────────────────────────────────
Verifies deterministic SHA-256 fingerprinting:
 • identical data  → identical hash
 • changed text    → different hash
 • changed URL     → different hash
 • missing fields  → handled gracefully
 • local file hash → correct
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path

import pytest

# Ensure imports work regardless of working directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from person2.hash_generator import (
    canonicalize,
    generate_fingerprint,
    hash_image,
)

# ── Sample data ──────────────────────────────────────────────

SAMPLE_POST = {
    "post_url": "https://example.com/sample-post-12345",
    "post_image": "nonexistent.jpg",
    "post_text": "Sample content for blockchain verification testing",
    "metadata": {"source": "development-test", "platform": "example"},
    "similarity": 0.91,
}


# ── Determinism ──────────────────────────────────────────────

class TestDeterminism:
    """The same logical data must always produce the same fingerprint."""

    def test_identical_data_identical_hash(self):
        fp1 = generate_fingerprint(SAMPLE_POST)
        fp2 = generate_fingerprint(SAMPLE_POST)
        assert fp1["sha256"] == fp2["sha256"]

    def test_dict_key_order_irrelevant(self):
        """Python dicts are insertion-ordered, but our canonical form
        must be independent of that."""
        reversed_post = dict(reversed(list(SAMPLE_POST.items())))
        fp1 = generate_fingerprint(SAMPLE_POST)
        fp2 = generate_fingerprint(reversed_post)
        assert fp1["sha256"] == fp2["sha256"]

    def test_metadata_key_order_irrelevant(self):
        post_a = {**SAMPLE_POST, "metadata": {"platform": "x", "source": "y"}}
        post_b = {**SAMPLE_POST, "metadata": {"source": "y", "platform": "x"}}
        assert generate_fingerprint(post_a)["sha256"] == generate_fingerprint(post_b)["sha256"]

    def test_whitespace_normalised(self):
        post_a = {**SAMPLE_POST, "post_text": "  hello   world  "}
        post_b = {**SAMPLE_POST, "post_text": "hello world"}
        assert generate_fingerprint(post_a)["sha256"] == generate_fingerprint(post_b)["sha256"]


# ── Sensitivity ──────────────────────────────────────────────

class TestSensitivity:
    """Changing any meaningful field must change the hash."""

    def test_changed_text(self):
        modified = {**SAMPLE_POST, "post_text": "Completely different text"}
        assert generate_fingerprint(SAMPLE_POST)["sha256"] != generate_fingerprint(modified)["sha256"]

    def test_changed_url(self):
        modified = {**SAMPLE_POST, "post_url": "https://other.com/different"}
        assert generate_fingerprint(SAMPLE_POST)["sha256"] != generate_fingerprint(modified)["sha256"]

    def test_changed_metadata(self):
        modified = {**SAMPLE_POST, "metadata": {"source": "tampered"}}
        assert generate_fingerprint(SAMPLE_POST)["sha256"] != generate_fingerprint(modified)["sha256"]

    def test_changed_image_ref(self):
        modified = {**SAMPLE_POST, "post_image": "other_image.jpg"}
        assert generate_fingerprint(SAMPLE_POST)["sha256"] != generate_fingerprint(modified)["sha256"]


# ── Missing / edge-case fields ───────────────────────────────

class TestEdgeCases:
    """Gracefully handle absent or empty fields."""

    def test_empty_post(self):
        fp = generate_fingerprint({})
        assert fp["sha256"]  # still produces a hash
        assert isinstance(fp["canonical_data"], str)

    def test_missing_text(self):
        post = {k: v for k, v in SAMPLE_POST.items() if k != "post_text"}
        fp = generate_fingerprint(post)
        assert fp["sha256"]

    def test_missing_url(self):
        post = {k: v for k, v in SAMPLE_POST.items() if k != "post_url"}
        fp = generate_fingerprint(post)
        assert fp["sha256"]

    def test_none_metadata(self):
        post = {**SAMPLE_POST, "metadata": None}
        fp = generate_fingerprint(post)
        assert fp["sha256"]

    def test_string_metadata(self):
        post = {**SAMPLE_POST, "metadata": "just a string"}
        fp = generate_fingerprint(post)
        assert fp["sha256"]


# ── Image hashing ────────────────────────────────────────────

class TestImageHashing:
    """hash_image must correctly handle files, missing files, and URLs."""

    def test_local_file(self):
        """Hash a real temp file and verify the digest."""
        content = b"test image content for hashing"
        expected = hashlib.sha256(content).hexdigest()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(content)
            tmp_path = f.name
        try:
            result = hash_image(tmp_path)
            assert result["status"] == "ok"
            assert result["sha256"] == expected
        finally:
            os.unlink(tmp_path)

    def test_missing_file(self):
        result = hash_image("definitely_does_not_exist_xyz.jpg")
        assert result["status"] == "unavailable"
        assert result["sha256"] == ""

    def test_empty_string(self):
        result = hash_image("")
        assert result["status"] == "unavailable"

    def test_none_value(self):
        result = hash_image(None)
        assert result["status"] == "unavailable"

    def test_image_info_in_fingerprint(self):
        """generate_fingerprint must expose image availability."""
        fp = generate_fingerprint(SAMPLE_POST)
        assert "image_info" in fp
        assert fp["image_info"]["status"] in ("ok", "unavailable")


# ── Canonical string format ──────────────────────────────────

class TestCanonical:
    def test_pipe_delimited(self):
        canonical = canonicalize(SAMPLE_POST)
        parts = canonical.split("|")
        assert len(parts) == 4, f"Expected 4 pipe-delimited parts, got {len(parts)}"

    def test_url_lowercased(self):
        post = {**SAMPLE_POST, "post_url": "HTTPS://EXAMPLE.COM/Test"}
        canonical = canonicalize(post)
        assert "https://example.com/test" in canonical
