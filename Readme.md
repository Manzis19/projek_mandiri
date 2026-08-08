# Hairstyle Recommender System

Aplikasi berbasis kecerdasan buatan (AI) dan *Computer Vision* yang dapat mendeteksi bentuk wajah seseorang dan memberikan rekomendasi gaya rambut paling ideal yang sesuai dengan proporsi wajah tersebut. Aplikasi ini menyediakan antarmuka web interaktif yang memungkinkan pengguna untuk mengunggah foto atau menggunakan kamera secara *real-time*.

## 🚀 Fitur Utama

- **Deteksi Bentuk Wajah Otomatis**: Mengenali berbagai bentuk wajah seperti Oval, Round (Bulat), Square (Persegi), Oblong (Panjang), Diamond (Wajik), dan Heart (Hati) menggunakan 468 titik landmark presisi dari MediaPipe FaceMesh.
- **Rekomendasi Gaya Rambut**: Memberikan saran potongan rambut terbaik berdasarkan hasil deteksi bentuk wajah.
- **Visualisasi Tahapan Pemrosesan Citra**: Menampilkan secara detail bagaimana AI melihat dan memproses gambar (mulai dari *Grayscale*, *Smoothing/Blur*, *CLAHE Enhancement*, *Edge Detection*, hingga pemetaan *468-point FaceMesh Landmarks* dan *Pola Geometri*).
- **Dukungan Kamera Real-time**: Pengguna dapat melakukan pemindaian wajah langsung dari *webcam* perangkat.
- **Antarmuka Modern dan Responsif**: Dibangun menggunakan TailwindCSS untuk pengalaman pengguna yang intuitif di berbagai perangkat.

## 🛠️ Teknologi yang Digunakan

- **Backend**: Python 3, Flask
- **Computer Vision & AI**: MediaPipe (FaceMesh 468 titik), OpenCV, Scikit-Learn, NumPy
- **Frontend**: HTML5, TailwindCSS, JavaScript

## 📂 Struktur Proyek

```
hairstyle-recommender/
│
├── app.py                  # File utama aplikasi Flask
├── core/                   # Modul inti untuk deteksi dan rekomendasi
│   ├── classifier.py       # Logika klasifikasi bentuk wajah
│   ├── face_detector.py    # Modul deteksi wajah
│   ├── landmark.py         # Ekstraksi 468 titik wajah (MediaPipe FaceMesh)
│   ├── recommender.py      # Logika sistem rekomendasi
│   └── visualizer.py       # Modul untuk visualisasi tahapan citra
├── data/                   # Direktori penyimpanan sementara foto yang diunggah
├── models/                 # Model AI / pre-trained weights yang digunakan
├── app/static/             # File statis frontend (CSS, JS, gambar)
│   ├── script.js
│   └── images/hairstyles/  # Koleksi gambar rekomendasi gaya rambut
├── requirements.txt        # Daftar library Python yang dibutuhkan
└── README.md               # Dokumentasi proyek
```

## ⚙️ Panduan Instalasi

Ikuti langkah-langkah di bawah ini untuk menjalankan aplikasi di lingkungan lokal Anda (khusus pengguna Windows dengan Python 3.12, sesuaikan jika menggunakan versi lain).

1. **Clone repository ini (atau pastikan Anda berada di direktori proyek):**
   ```bash
   cd hairstyle-recommender
   ```

2. **Buat Virtual Environment (Sangat Disarankan):**
   ```bash
   python -m venv venv
   # Aktivasi Virtual Environment di Windows:
   venv\Scripts\activate
   ```

3. **Install *dependencies* utama:**
   ```bash
   pip install -r requirements.txt
   ```
   *Catatan: Proyek ini kini memakai **MediaPipe FaceMesh** untuk deteksi landmark, sehingga **Dlib tidak lagi dibutuhkan** (tidak perlu CMake / Visual Studio build tools). Jika `mediapipe` menampilkan error protobuf `GetPrototype`, pastikan versi protobuf terkunci di `4.25.x` (`pip install "protobuf==4.25.3"`).*

4. **Jalankan Aplikasi:**
   ```bash
   python app.py
   ```

5. **Akses Aplikasi di Browser:**
   Buka web browser dan kunjungi: [http://localhost:7860](http://localhost:7860) atau [http://127.0.0.1:7860](http://127.0.0.1:7860)

## 💡 Catatan Tambahan

- Pastikan pencahayaan cukup dan wajah terlihat jelas saat menggunakan fitur kamera *real-time* atau saat mengunggah foto.
- Aplikasi membutuhkan akses kamera (izin browser) jika Anda ingin menggunakan fitur "Kamera Web Real-time".
