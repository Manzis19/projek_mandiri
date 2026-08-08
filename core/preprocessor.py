import io

import cv2
import numpy as np
from PIL import Image


class Preprocessor:
    def __init__(self, target_size=(256, 256)):
        self.target_size = target_size
        # CLAHE: Contrast Limited Adaptive Histogram Equalization
        # clipLimit=2.0 → batas kontras, tileGridSize → ukuran grid lokal
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def load_image(self, source):
        """
        Terima input berupa:
        - path file (string)
        - bytes dari upload web
        - numpy array langsung
        """
        if isinstance(source, str):
            img = cv2.imread(source)
        elif isinstance(source, bytes):
            arr = np.frombuffer(source, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        elif isinstance(source, np.ndarray):
            img = source.copy()
        else:
            raise ValueError("Format input tidak dikenali")

        if img is None:
            raise ValueError("Gagal membaca gambar. Pastikan format JPG/PNG.")
        return img

    def resize(self, img):
        """Tahap 1: Resize dengan mempertahankan aspect ratio (mencegah distorsi wajah)"""
        h, w = img.shape[:2]

        # Patokan lebar 500 piksel agar komputasi ringan
        new_w = 500
        new_h = int((new_w / w) * h)

        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def to_grayscale(self, img):
        """Tahap 2: Konversi BGR → Grayscale"""
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def equalize_histogram(self, gray):
        """
        Tahap 3: CLAHE (lebih baik dari equalizeHist biasa)
        - equalizeHist → global, bisa over-expose
        - CLAHE → lokal per tile, hasil lebih natural
        """
        return self.clahe.apply(gray)

    def reduce_noise(self, gray, method="gaussian"):
        """
        Tahap 4: Noise reduction
        - gaussian → halus, cocok untuk foto normal
        - median  → lebih agresif, cocok untuk foto beresolusi rendah
        """
        if method == "gaussian":
            # kernel 5x5, sigmaX=0 → dihitung otomatis
            return cv2.GaussianBlur(gray, (5, 5), 0)
        elif method == "median":
            return cv2.medianBlur(gray, 5)
        else:
            raise ValueError("Method harus 'gaussian' atau 'median'")

    def run(self, source, noise_method="gaussian", debug=False):
        """
        Jalankan full pipeline sekaligus.
        Jika debug=True → kembalikan semua tahap untuk visualisasi.
        """
        img_original = self.load_image(source)
        img_resized = self.resize(img_original)
        img_gray = self.to_grayscale(img_resized)
        img_equalized = self.equalize_histogram(img_gray)
        img_denoised = self.reduce_noise(img_equalized, method=noise_method)

        if debug:
            return {
                "original": img_resized,  # BGR, untuk ditampilkan
                "grayscale": img_gray,
                "equalized": img_equalized,
                "denoised": img_denoised,  # ← hasil final
            }

        return img_denoised  # output utama: grayscale + bersih
