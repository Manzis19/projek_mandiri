import base64
import math

import cv2
import numpy as np
import mediapipe as mp

# Muat FaceMesh sekali saja (hindari re-init tiap upload)
_mp_face_mesh = mp.solutions.face_mesh
_mp_drawing = mp.solutions.drawing_utils
_mp_styles = mp.solutions.drawing_styles
_face_mesh = _mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
)

# Indeks pengukuran (harus sama dengan core/landmark.py)
IDX_FOREHEAD_TOP = 10
IDX_CHIN = 152
IDX_CHEEK_L = 234
IDX_CHEEK_R = 454
IDX_JAW_L = 172
IDX_JAW_R = 397


def encode_image_to_base64(image_array):
    ret, buffer = cv2.imencode(".jpg", image_array)
    return base64.b64encode(buffer).decode("utf-8")


def get_processing_steps(image_path, predictor_path=None):
    """
    Hasilkan 8 tahapan pemrosesan citra sebagai base64 (JPEG).
    Nama key WAJIB sesuai template di app.py:
    1_original, 2_grayscale, 3_smoothing, 4_clahe_enhancement,
    5_edge_detection, 6_face_detection, 7_landmarks, 8_shape_pattern.
    (Parameter predictor_path dipertahankan demi kompatibilitas, tidak dipakai.)
    """
    steps = {}

    img = cv2.imread(image_path)
    if img is None:
        return None

    # 1. ORIGINAL
    steps["1_original"] = encode_image_to_base64(img)

    # 2. GRAYSCALE
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    steps["2_grayscale"] = encode_image_to_base64(gray)

    # 3. SMOOTHING (Gaussian Blur 5x5)
    smoothed = cv2.GaussianBlur(gray, (5, 5), 0)
    steps["3_smoothing"] = encode_image_to_base64(smoothed)

    # 4. CLAHE — perataan kontras adaptif
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    steps["4_clahe_enhancement"] = encode_image_to_base64(enhanced)

    # 5. EDGE DETECTION (Canny)
    edges = cv2.Canny(smoothed, 50, 150)
    steps["5_edge_detection"] = encode_image_to_base64(edges)

    # Kanvas grayscale 3-channel untuk anotasi berwarna
    gray_canvas = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    h, w = gray.shape[:2]

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = _face_mesh.process(rgb)

    # Jika wajah tak terdeteksi, tetap kembalikan 8 langkah (beri catatan).
    if not results.multi_face_landmarks:
        note = gray_canvas.copy()
        cv2.putText(
            note, "Wajah tidak terdeteksi", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
        )
        steps["6_face_detection"] = encode_image_to_base64(note)
        steps["7_landmarks"] = encode_image_to_base64(note)
        steps["8_shape_pattern"] = encode_image_to_base64(note)
        return steps

    face = results.multi_face_landmarks[0]
    pts = np.array([[int(lm.x * w), int(lm.y * h)] for lm in face.landmark], dtype=np.int32)

    def P(idx):
        return (int(pts[idx][0]), int(pts[idx][1]))

    # 6. FACE DETECTION (bounding box dari sebaran landmark)
    x0, y0 = int(pts[:, 0].min()), int(pts[:, 1].min())
    x1, y1 = int(pts[:, 0].max()), int(pts[:, 1].max())
    img_bbox = gray_canvas.copy()
    cv2.rectangle(img_bbox, (x0, y0), (x1, y1), (0, 255, 0), 2)
    cv2.putText(img_bbox, "Face detected", (x0, max(20, y0 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    steps["6_face_detection"] = encode_image_to_base64(img_bbox)

    # 7. FACE MESH (468 titik) — jaring tesselation
    img_mesh = cv2.addWeighted(gray_canvas, 0.35, np.zeros_like(gray_canvas), 0, 0)
    _mp_drawing.draw_landmarks(
        image=img_mesh,
        landmark_list=face,
        connections=_mp_face_mesh.FACEMESH_TESSELATION,
        landmark_drawing_spec=None,
        connection_drawing_spec=_mp_styles.get_default_face_mesh_tesselation_style(),
    )
    _mp_drawing.draw_landmarks(
        image=img_mesh,
        landmark_list=face,
        connections=_mp_face_mesh.FACEMESH_CONTOURS,
        landmark_drawing_spec=None,
        connection_drawing_spec=_mp_styles.get_default_face_mesh_contours_style(),
    )
    steps["7_landmarks"] = encode_image_to_base64(img_mesh)

    # 8. GEOMETRI & EUCLIDEAN (pengukuran yang dipakai classifier)
    img_shape = gray_canvas.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX

    def draw_measure(p1, p2, color, label):
        dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        cv2.line(img_shape, p1, p2, color, 2, cv2.LINE_AA)
        cv2.circle(img_shape, p1, 4, color, -1)
        cv2.circle(img_shape, p2, 4, color, -1)
        mid = (int((p1[0] + p2[0]) / 2), int((p1[1] + p2[1]) / 2) - 8)
        text = f"{label}: {int(dist)}px"
        (tw, th), _ = cv2.getTextSize(text, font, 0.5, 2)
        cv2.rectangle(img_shape, (mid[0] - 2, mid[1] - th - 2), (mid[0] + tw + 2, mid[1] + 2), (0, 0, 0), -1)
        cv2.putText(img_shape, text, mid, font, 0.5, color, 2)

    draw_measure(P(IDX_CHEEK_L), P(IDX_CHEEK_R), (0, 255, 255), "Lebar (W)")     # Kuning
    draw_measure(P(IDX_JAW_L), P(IDX_JAW_R), (255, 100, 255), "Rahang (J)")      # Pink
    draw_measure(P(IDX_FOREHEAD_TOP), P(IDX_CHIN), (0, 255, 0), "Tinggi (H)")    # Hijau

    steps["8_shape_pattern"] = encode_image_to_base64(img_shape)

    return steps
