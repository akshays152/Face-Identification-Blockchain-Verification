"""
tests/test_person1.py
---------------------
Unit tests for Person 1 modules:
  - Face detection (FaceDetector)
  - Face embedding (FaceEmbedder)
  - Face matching & similarity (FaceMatcher)
  - Web & social search (WebSearcher)
  - Candidate extraction (PostExtractor)
  - Handoff file creation
"""

import json
from pathlib import Path
import numpy as np
import pytest

import sys
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from person1.face_detection import FaceDetector, detect_face
from person1.face_embedding import FaceEmbedder, get_face_embedding
from person1.face_matching import FaceMatcher, cosine_similarity
from person1.web_search import WebSearcher
from person1.post_extractor import PostExtractor

SAMPLE_FACE = _ROOT / "data" / "sample_face.jpg"


class TestPerson1FaceDetection:
    def test_face_detected_in_sample(self):
        detector = FaceDetector()
        faces = detector.detect_faces(SAMPLE_FACE)
        assert len(faces) >= 1
        primary = detector.get_primary_face(SAMPLE_FACE)
        assert primary["box"][2] > 0  # width > 0
        assert primary["box"][3] > 0  # height > 0
        assert primary["confidence"] > 0.5
        assert primary["cropped_face"] is not None

    def test_detect_face_convenience(self):
        res = detect_face(SAMPLE_FACE)
        assert "box" in res
        assert "confidence" in res
        assert "cropped_face" in res


class TestPerson1FaceEmbedding:
    def test_embedding_shape_and_norm(self):
        embedder = FaceEmbedder()
        emb = embedder.generate_embedding(SAMPLE_FACE)
        assert emb.shape == (128,)
        # Normalized vector should have norm close to 1.0
        norm = float(np.linalg.norm(emb))
        assert abs(norm - 1.0) < 1e-3

    def test_self_similarity_is_one(self):
        emb = get_face_embedding(SAMPLE_FACE)
        sim = cosine_similarity(emb, emb)
        assert abs(sim - 1.0) < 1e-4


class TestPerson1FaceMatching:
    def test_face_matcher_matching_candidate(self):
        matcher = FaceMatcher()
        input_emb = matcher.embedder.generate_embedding(SAMPLE_FACE)

        candidates = [
            {
                "post_url": "https://example.com/match-post",
                "post_image": str(SAMPLE_FACE.resolve()),
                "post_text": "A verified social post containing this user.",
                "metadata": {"user": "alice", "platform": "web"},
            },
            {
                "post_url": "https://example.com/other-post",
                "post_image": "non_existent_image.jpg",
                "post_text": "Unrelated post",
                "metadata": {},
            }
        ]

        best_post, sim_score = matcher.find_best_match(input_emb, candidates)
        assert best_post is not None
        assert best_post["post_url"] == "https://example.com/match-post"
        assert sim_score >= 0.95

    def test_handoff_json_schema(self, tmp_path):
        matcher = FaceMatcher()
        test_post = {
            "post_url": "https://example.com/test",
            "post_image": str(SAMPLE_FACE.resolve()),
            "post_text": "Sample text",
            "metadata": {"key": "val"},
        }
        out_json = tmp_path / "post_result.json"
        handoff = matcher.create_handoff_file(test_post, similarity=0.917, output_path=out_json, sync_to_data=False)

        assert out_json.is_file()
        with open(out_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["post_url"] == "https://example.com/test"
        assert data["post_image"] == str(SAMPLE_FACE.resolve())
        assert data["post_text"] == "Sample text"
        assert data["metadata"] == {"key": "val"}
        assert data["similarity"] == 0.917


class TestPerson1WebSearchAndExtraction:
    def test_open_web_search_returns_candidates(self):
        searcher = WebSearcher()
        results = searcher.search_open_web(query="portrait", limit=3)
        assert len(results) > 0
        first = results[0]
        assert first["post_url"].startswith("http")
        assert first["post_image"].startswith("http")
        assert len(first["post_text"]) > 0

    def test_post_extractor(self, tmp_path):
        extractor = PostExtractor(cache_dir=tmp_path)
        candidates = [
            {
                "post_url": "https://example.com/post-1",
                "post_image": str(SAMPLE_FACE.resolve()),
                "post_text": "Local test post",
                "metadata": {"source": "test"},
            }
        ]
        extracted = extractor.extract_all(candidates)
        assert len(extracted) == 1
        assert extracted[0]["post_url"] == "https://example.com/post-1"
        assert extracted[0]["post_image"] == str(SAMPLE_FACE.resolve())
