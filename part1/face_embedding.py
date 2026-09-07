"""
part1/face_embedding.py
-------------------------
Step 3: Face Embedding Module (Part 1)

Generates a robust 128-dimensional face feature embedding vector
using OpenCV's deep neural SFace recognition model.

Guarantees normalized feature representation suitable for
Cosine Similarity comparison.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Union, Optional, Tuple, Any
import cv2
import numpy as np

# Safe UTF-8 console output for Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from part1.face_detection import FaceDetector

SFACE_MODEL_PATH = _ROOT / "part1" / "models" / "face_recognition_sface.onnx"


class FaceEmbedder:
    """
    Computes 128-d facial embeddings using OpenCV SFace.
    """

    def __init__(self, model_path: Path = SFACE_MODEL_PATH) -> None:
        self.model_path = model_path
        self.detector = FaceDetector()
        self._recognizer = None

    def _ensure_recognizer(self) -> Any:
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"SFace recognition model not found at: {self.model_path}\n"
                f"Run py download_models.py to fetch the model."
            )
        if self._recognizer is None:
            self._recognizer = cv2.FaceRecognizerSF_create(str(self.model_path), "")
        return self._recognizer

    def generate_embedding_from_face(
        self,
        image: np.ndarray,
        raw_face: np.ndarray,
    ) -> np.ndarray:
        """
        Aligns the face and generates the 128-d feature embedding.
        """
        recognizer = self._ensure_recognizer()
        aligned_face = recognizer.alignCrop(image, raw_face)
        feature = recognizer.feature(aligned_face)
        # Flatten and normalize
        vec = feature.flatten().astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 1e-8:
            vec = vec / norm
        return vec

    def generate_embedding(
        self,
        image_source: Union[str, Path, np.ndarray],
    ) -> np.ndarray:
        """
        Full pipeline: loads image, detects primary face, aligns, and embeds.
        """
        image = self.detector.load_image(image_source)
        primary = self.detector.get_primary_face(image)
        return self.generate_embedding_from_face(image, primary["raw_face"])


def get_face_embedding(image_path: Union[str, Path]) -> np.ndarray:
    """Convenience functional interface for Part 1 pipeline."""
    embedder = FaceEmbedder()
    return embedder.generate_embedding(image_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py part1/face_embedding.py <path_to_image>")
        sys.exit(1)

    image_arg = sys.argv[1]
    print("[1] Loading face image...")
    try:
        embedder = FaceEmbedder()
        face_info = embedder.detector.get_primary_face(image_arg)
        print("[✓] Face detected")
        print("[2] Generating face embedding...")
        image = embedder.detector.load_image(image_arg)
        emb = embedder.generate_embedding_from_face(image, face_info["raw_face"])
        print("[✓] Embedding generated")
        print(f"    Dimensions: {len(emb)}")
        print(f"    L2 Norm:    {float(np.linalg.norm(emb)):.4f}")
    except Exception as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)
