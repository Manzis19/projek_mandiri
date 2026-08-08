import cv2
import numpy as np
import mediapipe as mp


class LandmarkDetector:
    """
    Deteksi 468 landmark wajah menggunakan MediaPipe FaceMesh.

    Menggantikan dlib 68-titik: MediaPipe memberi kontur wajah yang jauh lebih
    padat DAN mencakup area dahi, sehingga tinggi wajah bisa diukur langsung
    (dahi→dagu) tanpa perlu ekstrapolasi.
    """

    # Indeks landmark canonical MediaPipe FaceMesh untuk pengukuran wajah
    IDX_FOREHEAD_TOP = 10   # puncak dahi (≈ garis rambut tengah)
    IDX_CHIN         = 152  # ujung dagu
    IDX_CHEEK_L      = 234  # sisi wajah terlebar kiri (tulang pipi/pelipis)
    IDX_CHEEK_R      = 454  # sisi wajah terlebar kanan
    IDX_JAW_L        = 172  # sudut rahang kiri
    IDX_JAW_R        = 397  # sudut rahang kanan
    IDX_FOREHEAD_L   = 21   # pelipis/dahi kiri
    IDX_FOREHEAD_R   = 251  # pelipis/dahi kanan

    def __init__(self, *args, **kwargs):
        # *args/**kwargs diabaikan agar tetap kompatibel dengan pemanggilan
        # lama yang mengirim path model dlib.
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )

    def detect(self, image_bgr, debug=False):
        """
        Deteksi landmark dari citra BGR.

        Return:
        - points (N,2) piksel bila debug=False, atau None jika tak ada wajah.
        - dict {points, annotated, bbox} bila debug=True (None jika tak ada wajah).
        """
        h, w = image_bgr.shape[:2]
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return None

        face = results.multi_face_landmarks[0]
        points = np.array(
            [[int(lm.x * w), int(lm.y * h)] for lm in face.landmark],
            dtype=np.int32,
        )

        if not debug:
            return points

        annotated = self._draw(image_bgr.copy(), face, points)
        bbox = self._bbox_from_points(points, w, h)
        return {"points": points, "annotated": annotated, "bbox": bbox}

    def extract_features(self, points):
        """
        Hitung fitur geometri dari landmark MediaPipe.
        Rasio yang dipakai classifier:
          length_width : tinggi / lebar wajah      → oblong/oval vs round/square
          jaw_forehead : lebar rahang / lebar dahi  → heart (rahang sempit)
          cheek_jaw    : lebar pipi / lebar rahang  → diamond (pipi menonjol)
        """
        face_width     = self._dist(points[self.IDX_CHEEK_L],     points[self.IDX_CHEEK_R])
        face_height    = self._dist(points[self.IDX_FOREHEAD_TOP], points[self.IDX_CHIN])
        jaw_width      = self._dist(points[self.IDX_JAW_L],        points[self.IDX_JAW_R])
        forehead_width = self._dist(points[self.IDX_FOREHEAD_L],   points[self.IDX_FOREHEAD_R])

        wh_ratio     = face_width  / face_height    if face_height    > 0 else 0
        length_width = face_height / face_width      if face_width     > 0 else 0
        jaw_forehead = jaw_width   / forehead_width  if forehead_width > 0 else 0
        cheek_jaw    = face_width  / jaw_width        if jaw_width      > 0 else 0

        return {
            "face_width":     round(float(face_width),     2),
            "face_height":    round(float(face_height),    2),
            "jaw_width":      round(float(jaw_width),       2),
            "forehead_width": round(float(forehead_width), 2),
            "wh_ratio":       round(float(wh_ratio),       4),
            "length_width":   round(float(length_width),   4),
            "jaw_forehead":   round(float(jaw_forehead),   4),
            "cheek_jaw":      round(float(cheek_jaw),      4),
        }

    # ── Helper ────────────────────────────────────────────────

    def _dist(self, p1, p2):
        return np.linalg.norm(np.array(p1, dtype=float) - np.array(p2, dtype=float))

    def _bbox_from_points(self, points, w, h, pad=0.06):
        x0, y0 = int(points[:, 0].min()), int(points[:, 1].min())
        x1, y1 = int(points[:, 0].max()), int(points[:, 1].max())
        px, py = int((x1 - x0) * pad), int((y1 - y0) * pad)
        x0 = max(0, x0 - px)
        y0 = max(0, y0 - py)
        x1 = min(w, x1 + px)
        y1 = min(h, y1 + py)
        return (x0, y0, x1 - x0, y1 - y0)

    def _draw(self, img, face_landmarks, points):
        """Gambar jaring FaceMesh + kontur + bounding box di atas foto."""
        self.mp_drawing.draw_landmarks(
            image=img,
            landmark_list=face_landmarks,
            connections=self.mp_face_mesh.FACEMESH_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=self.mp_styles.get_default_face_mesh_tesselation_style(),
        )
        self.mp_drawing.draw_landmarks(
            image=img,
            landmark_list=face_landmarks,
            connections=self.mp_face_mesh.FACEMESH_CONTOURS,
            landmark_drawing_spec=None,
            connection_drawing_spec=self.mp_styles.get_default_face_mesh_contours_style(),
        )
        x, y, bw, bh = self._bbox_from_points(points, img.shape[1], img.shape[0])
        cv2.rectangle(img, (x, y), (x + bw, y + bh), (0, 255, 100), 2)
        cv2.putText(
            img, "Face detected", (x, max(20, y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 100), 2,
        )
        return img
