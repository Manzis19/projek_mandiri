import numpy as np

class FaceShapeClassifier:
    # Label resmi + metadata
    SHAPES = {
        "oval": {"label": "Oval", "emoji": "🥚", "color": "#639922"},
        "round": {"label": "Round", "emoji": "⭕", "color": "#D85A30"},
        "square": {"label": "Square", "emoji": "🔲", "color": "#888780"},
        "heart": {"label": "Heart", "emoji": "🫀", "color": "#D4537E"},
        "oblong": {"label": "Oblong", "emoji": "📏", "color": "#378ADD"},
        "diamond": {"label": "Diamond", "emoji": "💎", "color": "#BA7517"},
    }

    def __init__(self):
        # Titik pusat ideal tiap bentuk wajah pada 3 rasio:
        # (length_width, jaw_forehead, cheek_jaw)
        #   length_width : panjang / lebar wajah
        #   jaw_forehead : lebar rahang / lebar dahi
        #   cheek_jaw    : lebar pipi / lebar rahang
        # Dikalibrasi untuk pengukuran MediaPipe FaceMesh (tinggi wajah asli
        # dahi→dagu, lebar bizygomatic 234↔454, rahang 172↔397, dahi 21↔251).
        self.centers = {
            "oval":    (1.35, 0.88, 1.20),
            "round":   (1.05, 0.95, 1.15),
            "square":  (1.05, 1.02, 1.08),
            "heart":   (1.30, 0.72, 1.28),
            "oblong":  (1.55, 0.95, 1.12),
            "diamond": (1.38, 0.90, 1.38),
        }

        # Bobot per fitur (rentang length_width jauh lebih lebar daripada dua
        # rasio lain, jadi kita naikkan bobot rasio dahi/pipi agar seimbang).
        self.weights = np.array([1.0, 1.6, 1.6])

        # Suhu softmax: makin besar makin "yakin" pada tebakan terdekat.
        self.temperature = 9.0

    def predict(self, features: dict) -> dict:
        """
        Klasifikasi bentuk wajah menggunakan jarak Euclidean berbobot + Softmax.
        """
        # 1. Ambil 3 fitur utama dari wajah user
        feat_vec = np.array([
            features["length_width"],
            features["jaw_forehead"],
            features["cheek_jaw"],
        ])

        # 2. Jarak berbobot ke tiap titik ideal
        distances = {
            s: float(np.sqrt(np.sum(self.weights * (feat_vec - np.array(c)) ** 2)))
            for s, c in self.centers.items()
        }

        # 3. Bentuk wajah dengan jarak TERDEKAT adalah tebakan utama
        predicted_shape = min(distances, key=distances.get)

        # 4. Confidence Score (Softmax dengan Temperature)
        exp_scores = {s: np.exp(-d * self.temperature) for s, d in distances.items()}
        total_exp = sum(exp_scores.values())

        scores = {s: round(v / total_exp, 3) for s, v in exp_scores.items()}
        confidence = round(scores[predicted_shape], 3)

        # 5. Top-3 kandidat (transparansi untuk user)
        top3 = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
        top3 = [
            {"shape": s, "label": self.SHAPES[s]["label"], "score": sc}
            for s, sc in top3
        ]

        return {
            "shape": predicted_shape,
            "label": self.SHAPES[predicted_shape]["label"],
            "confidence": confidence,
            "scores": scores,
            "top3": top3,
            "features": features,
            "reasoning": self._reasoning(predicted_shape, features),
        }

    def _reasoning(self, shape: str, features: dict) -> str:
        """Penjelasan singkat kenapa diklasifikasikan sebagai shape ini."""
        lw = features["length_width"]
        jf = features["jaw_forehead"]
        cj = features["cheek_jaw"]

        reasons = {
            "oval": f"Panjang wajah ~{lw:.2f}× lebarnya (proporsional), rahang sedikit lebih sempit dari dahi (rasio {jf:.2f}).",
            "round": f"Panjang wajah ~{lw:.2f}× lebar (mendekati 1:1), garis rahang membulat dan pipi penuh.",
            "square": f"Panjang ≈ lebar (~{lw:.2f}×) namun rahang hampir selebar dahi (rasio {jf:.2f}), garis rahang tegas.",
            "heart": f"Dahi lebih lebar dari rahang (rasio {jf:.2f}), wajah menyempit ke bawah menuju dagu.",
            "oblong": f"Wajah panjang: tinggi ~{lw:.2f}× lebar, dengan lebar dahi–pipi–rahang relatif merata.",
            "diamond": f"Tulang pipi menonjol (pipi ~{cj:.2f}× lebar rahang), dahi dan rahang relatif sempit.",
        }
        return reasons.get(shape, "")
