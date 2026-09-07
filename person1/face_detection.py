"""
person1/face_detection.py
-------------------------
Step 3: Face Detection Module (Person 1)

Takes an input image, detects faces using OpenCV's neural YuNet model,
locates bounding boxes, and crops/normalizes the face region.

Complies with Section 2, Step 3 of the specification.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union
import cv2
import numpy as np

# Safe UTF-8 console output for Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

MODEL_PATH = _ROOT / "person1" / "models" / "face_detection_yunet.onnx"


class FaceDetector:
    """
    High-accuracy neural Face Detector using OpenCV YuNet.
    """

    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        self.model_path = model_path
        self._detector = None
        self._last_input_size = None

    def _ensure_detector(self, w: int, h: int) -> Any:
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Face detection model not found at: {self.model_path}\n"
                f"Run py download_models.py to fetch the model."
            )

        if self._detector is None:
            self._detector = cv2.FaceDetectorYN_create(
                model=str(self.model_path),
                config="",
                input_size=(w, h),
                score_threshold=0.5,
                nms_threshold=0.3,
                top_k=5000,
            )
            self._last_input_size = (w, h)
        elif self._last_input_size != (w, h):
            self._detector.setInputSize((w, h))
            self._last_input_size = (w, h)

        return self._detector

    def load_image(self, image_source: Union[str, Path, np.ndarray]) -> np.ndarray:
        """Loads an image from file path or verifies existing numpy ndarray."""
        if isinstance(image_source, np.ndarray):
            return image_source

        p = Path(image_source)
        if not p.is_file():
            raise FileNotFoundError(f"Image not found at path: {image_source}")

        image_bytes = p.read_bytes()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Failed to decode image from: {image_source}")
        return img

    def detect_faces(
        self,
        image_source: Union[str, Path, np.ndarray],
        margin: float = 0.1,
    ) -> List[dict[str, Any]]:
        """
        Detects all faces in the input image.

        Returns
        -------
        List of dicts:
            {
                "box": (x, y, w, h),
                "confidence": float,
                "raw_face": np.ndarray (YuNet output row),
                "cropped_face": np.ndarray,
            }
        """
        image = self.load_image(image_source)
        img_h, img_w = image.shape[:2]

        detector = self._ensure_detector(img_w, img_h)
        _, raw_faces = detector.detect(image)

        results = []
        if raw_faces is None or len(raw_faces) == 0:
            return results

        for face in raw_faces:
            x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
            score = float(face[-1])

            # Apply safe margin
            dx = int(w * margin)
            dy = int(h * margin)
            x1 = max(0, x - dx)
            y1 = max(0, y - dy)
            x2 = min(img_w, x + w + dx)
            y2 = min(img_h, y + h + dy)

            cropped = image[y1:y2, x1:x2]
            results.append({
                "box": (x, y, w, h),
                "expanded_box": (x1, y1, x2 - x1, y2 - y1),
                "confidence": round(score, 4),
                "raw_face": face,
                "cropped_face": cropped,
            })

        return results

    def get_primary_face(
        self,
        image_source: Union[str, Path, np.ndarray],
    ) -> dict[str, Any]:
        """Returns the primary (highest confidence / largest) face."""
        faces = self.detect_faces(image_source)
        if not faces:
            raise ValueError(f"No face detected in image: {image_source}")
        primary = max(faces, key=lambda f: f["box"][2] * f["box"][3] * f["confidence"])
        return primary


def detect_face(image_path: Union[str, Path]) -> dict[str, Any]:
    """Convenience functional interface for Person 1 pipeline."""
    detector = FaceDetector()
    return detector.get_primary_face(image_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py person1/face_detection.py <path_to_image>")
        sys.exit(1)

    image_arg = sys.argv[1]
    print("[1] Loading face image...")
    try:
        res = detect_face(image_arg)
        box = res["box"]
        conf = res["confidence"]
        print("[✓] Face detected")
        print(f"    Bounding Box: x={box[0]}, y={box[1]}, w={box[2]}, h={box[3]}")
        print(f"    Confidence:   {conf * 100:.1f}%")
    except Exception as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)
