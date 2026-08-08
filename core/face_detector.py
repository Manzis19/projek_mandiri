import cv2
import numpy as np

class FaceDetector:
    def __init__(self):
        # Load model Haar Cascade bawaan OpenCV
        # File ini sudah ada otomatis saat install opencv-python
        self.cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        if self.cascade.empty():
            raise IOError("Gagal load Haar Cascade. Cek instalasi OpenCV.")

    def detect(self, gray_img, debug=False):
        """
        Deteksi wajah dari citra grayscale.
        
        Parameter penting:
        - scaleFactor : seberapa besar gambar dikecilkan per tahap (1.1 = 10%)
        - minNeighbors: berapa banyak tetangga yang harus ada → makin besar makin ketat
        - minSize     : ukuran wajah minimum dalam piksel
        
        Return: list of (x, y, w, h) atau None jika tidak ada wajah.
        """
        faces = self.cascade.detectMultiScale(
    gray_img,
    scaleFactor=1.1,
    minNeighbors=4,
    minSize=(40, 40),
    flags=cv2.CASCADE_SCALE_IMAGE
)

        if len(faces) == 0:
            return None, self._error("Tidak ada wajah terdeteksi. "
                                     "Pastikan foto frontal & pencahayaan cukup.")

        # Pilih wajah terbesar jika ada lebih dari 1
        if len(faces) > 1:
            faces = self._pick_largest(faces)

        x, y, w, h = faces[0]

        # Tambah sedikit padding agar landmark tidak terpotong di tepi
        x, y, w, h = self._add_padding(gray_img, x, y, w, h, pad=0.10)

        if debug:
            return {
                "bbox": (x, y, w, h),
                "face_crop": gray_img[y:y+h, x:x+w],
                "face_count_original": len(faces),
            }, None

        return (x, y, w, h), None

    def draw_bbox(self, img_bgr, bbox, color=(0, 255, 100), thickness=2):
        """Gambar bounding box di atas foto asli (BGR). Untuk debug/visualisasi."""
        x, y, w, h = bbox
        result = img_bgr.copy()
        cv2.rectangle(result, (x, y), (x+w, y+h), color, thickness)
        cv2.putText(result, "Face detected", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return result

    def validate_photo(self, gray_img):
        """
        Validasi foto sebelum diproses lebih lanjut.
        Return: (is_valid: bool, message: str)
        """
        h, w = gray_img.shape[:2]

        # Cek resolusi minimum
        if w < 100 or h < 100:
            return False, "Resolusi foto terlalu kecil. Minimal 100×100 piksel."

        # Cek blur — pakai variance of Laplacian.
        # Ambang rendah (10) karena citra sudah di-resize (500px) sehingga
        # detail frekuensi tinggi berkurang; cek ini hanya jalan bila MediaPipe
        # gagal mendeteksi wajah, jadi sekadar penjelas, bukan penolak utama.
        lap_var = cv2.Laplacian(gray_img, cv2.CV_64F).var()
        if lap_var < 10:
            return False, f"Foto terlalu buram (skor: {lap_var:.1f}). Gunakan foto yang lebih tajam."

        # Cek kecerahan rata-rata
        mean_brightness = gray_img.mean()
        if mean_brightness < 40:
            return False, "Foto terlalu gelap. Pastikan pencahayaan cukup."
        if mean_brightness > 220:
            return False, "Foto terlalu terang/overexposed."

        return True, "OK"

    # ── Helper methods ──────────────────────────────────────────

    def _pick_largest(self, faces):
        """Pilih wajah dengan area terbesar."""
        areas = [w * h for (x, y, w, h) in faces]
        idx = np.argmax(areas)
        return faces[idx:idx+1]

    def _add_padding(self, img, x, y, w, h, pad=0.10):
        """Tambah padding sekitar bounding box, clamp ke batas gambar."""
        ih, iw = img.shape[:2]
        px = int(w * pad)
        py = int(h * pad)
        x = max(0, x - px)
        y = max(0, y - py)
        w = min(iw - x, w + 2 * px)
        h = min(ih - y, h + 2 * py)
        return x, y, w, h

    def _error(self, msg):
        return {"error": msg}
