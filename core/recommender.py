import json
import os

import cv2

from core.classifier import FaceShapeClassifier
from core.face_detector import FaceDetector
from core.landmark import LandmarkDetector
from core.preprocessor import Preprocessor


class HairstyleRecommender:
    def __init__(self, data_path="data/hairstyles.json"):

        self.prep = Preprocessor()
        self.detector = FaceDetector()
        self.landmark = LandmarkDetector()
        self.classifier = FaceShapeClassifier()

        with open(data_path, encoding="utf-8") as f:
            self.hairstyles = json.load(f)

    def analyze(self, image_source, top_n=5):
        """
        Pipeline lengkap: foto → rekomendasi hairstyle.

        Return dict:
        {
            "success"      : True/False,
            "error"        : str | None,
            "face_shape"   : "oval" | ...,
            "label"        : "Oval" | ...,
            "confidence"   : 0.85,
            "reasoning"    : "...",
            "scores"       : { "oval": 0.4, ... },
            "features"     : { "wh_ratio": ..., ... },
            "hairstyles"   : [ { name, description, images, tags }, ... ],
            "annotated_img": np.ndarray (BGR),
        }
        """
        try:
            img_bgr = self.prep.load_image(image_source)
            img_bgr = self.prep.resize(img_bgr)  # normalisasi ukuran (lebar 500px)
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            # 1. Deteksi 468 landmark (MediaPipe FaceMesh) langsung dari citra warna.
            #    MediaPipe adalah gerbang utama: wajah yang terdeteksi TIDAK ditolak
            #    walau sedikit buram/gelap.
            lm_result = self.landmark.detect(img_bgr, debug=True)

            # 2. Kalau wajah tak terdeteksi, baru cek kualitas foto agar pesannya
            #    lebih membantu (buram / gelap / resolusi terlalu kecil).
            if lm_result is None:
                is_valid, msg = self.detector.validate_photo(gray)
                if not is_valid:
                    return {"success": False, "error": msg}
                return {
                    "success": False,
                    "error": "Tidak ada wajah terdeteksi. Pastikan foto frontal, "
                    "wajah terlihat jelas, dan pencahayaan cukup.",
                }

            # 3. Ekstraksi fitur geometri & klasifikasi bentuk wajah
            features = self.landmark.extract_features(lm_result["points"])
            result = self.classifier.predict(features)

            # 4. Rekomendasi hairstyle
            shape = result["shape"]
            hairstyles = self._get_recommendations(shape, top_n)

            # 5. Foto annotated (mesh FaceMesh + bounding box)
            annotated = lm_result["annotated"]

            return {
                "success": True,
                "error": None,
                "face_shape": shape,
                "label": result["label"],
                "confidence": result["confidence"],
                "reasoning": result["reasoning"],
                "scores": result["scores"],
                "top3": result["top3"],
                "features": features,
                "hairstyles": hairstyles,
                "annotated_img": annotated,
            }

        except Exception as e:
            return {"success": False, "error": f"Terjadi kesalahan: {str(e)}"}

    def _get_recommendations(self, shape: str, top_n: int):
        """Ambil top N hairstyle dari JSON database."""
        all_styles = self.hairstyles.get(shape, [])
        return all_styles[:top_n]
