import urllib.request
from pathlib import Path
import requests

models_dir = Path("person1/models")
models_dir.mkdir(parents=True, exist_ok=True)

yunet_url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
sface_url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

headers = {"User-Agent": "Mozilla/5.0 RecallX-Verifier/1.0"}

print("Checking/downloading YuNet...")
yunet_path = models_dir / "face_detection_yunet.onnx"
if not yunet_path.is_file() or yunet_path.stat().st_size < 10000:
    r = requests.get(yunet_url, headers=headers, timeout=30)
    yunet_path.write_bytes(r.content)
    print("YuNet downloaded:", yunet_path.stat().st_size, "bytes")
else:
    print("YuNet already present:", yunet_path.stat().st_size, "bytes")

print("Checking/downloading SFace...")
sface_path = models_dir / "face_recognition_sface.onnx"
if not sface_path.is_file() or sface_path.stat().st_size < 10000:
    r = requests.get(sface_url, headers=headers, timeout=60)
    sface_path.write_bytes(r.content)
    print("SFace downloaded:", sface_path.stat().st_size, "bytes")
else:
    print("SFace already present:", sface_path.stat().st_size, "bytes")
