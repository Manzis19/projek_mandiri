import base64
import os
import sys
import time

import cv2
import numpy as np
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template_string,
    request,
    send_from_directory,
)

sys.path.insert(0, ".")
from core.recommender import HairstyleRecommender
from core.visualizer import get_processing_steps

app = Flask(__name__, static_folder="app/static")

rec = HairstyleRecommender()

UPLOAD_FOLDER = "data"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route("/data/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="theme-color" content="#09090b">
    <script>document.documentElement.classList.add('js');</script>
    <title>LOOKPAS &middot; Find the look that's pas for you.</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                        display: ['Fraunces', 'serif'],
                    },
                    colors: {
                        /* Palet barbershop mewah: merah barber, navy, krom/steel, cream */
                        barber: {
                            red: '#b3202b',
                            redlight: '#d64550',
                            reddark: '#7e161e',
                            navy: '#16233f',
                            navylight: '#26385e',
                            cream: '#f4efe6',
                            steel: '#c7ccd3'
                        }
                    }
                }
            }
        }
    </script>
    <style>
        html { scroll-behavior: smooth; }
        body { font-family: 'Inter', sans-serif; -webkit-tap-highlight-color: transparent; }
        .font-display { font-family: 'Fraunces', serif; }
        #webcam { transform: scaleX(-1); } /* Efek cermin */

        /* Latar charcoal mewah dengan sorotan merah & navy yang halus */
        body {
            background-color: #141317;
            background-image:
                radial-gradient(circle at 12% -8%, rgba(179, 32, 43, 0.10), transparent 42%),
                radial-gradient(circle at 88% 4%, rgba(22, 35, 63, 0.20), transparent 48%);
        }

        /* Teks aksen: gradient merah barber yang elegan */
        .aurora {
            background-image: linear-gradient(120deg, #d64550, #b3202b, #7e161e);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        /* Motif tiang barbershop (barber pole) beranimasi */
        .barber-stripe {
            background-image: linear-gradient(45deg,
                #b3202b 0 25%, #f4efe6 25% 50%, #16233f 50% 75%, #f4efe6 75% 100%);
            background-size: 42px 42px;
            animation: barberSpin 1.7s linear infinite;
        }
        @keyframes barberSpin { to { background-position: 0 -42px; } }

        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #4b4b52; border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #b3202b; }

        /* Animasi masuk & transisi UX (hanya transform/opacity → mulus di compositor) */
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes fadeInUp { from { opacity: 0; transform: translate3d(0, 16px, 0); } to { opacity: 1; transform: translate3d(0, 0, 0); } }
        @keyframes pulseGlow { 0%, 100% { box-shadow: 0 0 0 0 rgba(179, 32, 43, 0.5); } 50% { box-shadow: 0 0 0 10px rgba(179, 32, 43, 0); } }

        /* Reveal saat scroll (progressive enhancement: efek hanya aktif bila JS ada) */
        .js .reveal { opacity: 0; }
        .js .reveal.is-visible { animation: fadeInUp .5s cubic-bezier(.22, .61, .36, 1) both; }

        /* Fade-in gambar (opacity + scale halus, tanpa blur agar tidak berat) */
        .js .img-fade { opacity: 0; transform: scale(1.03); transition: opacity .5s ease, transform .5s cubic-bezier(.22, .61, .36, 1); }
        .js .img-fade.loaded { opacity: 1; transform: none; }

        /* Micro-interaction: angkat kartu saat hover */
        .lift { transition: transform .25s cubic-bezier(.22, .61, .36, 1), box-shadow .25s ease, border-color .25s ease; }
        .lift:hover { transform: translateY(-4px); }

        /* Meter akurasi (warna barber pole: merah - cream - navy) */
        .meter { height: 7px; border-radius: 9999px; background: rgba(255,255,255,.08); overflow: hidden; }
        .meter-fill { height: 100%; width: 0; border-radius: 9999px; background: linear-gradient(90deg, #b3202b, #f4efe6, #16233f); transition: width 1.1s cubic-bezier(.22, 1, .36, 1); }

        /* Efek frame kamera saat memproses */
        #cam-frame.processing { animation: pulseGlow 1.4s ease-in-out infinite; }

        /* Highlight dropzone saat file diseret ke atasnya */
        #dropzone.drag-over {
            background: rgba(179, 32, 43, 0.10);
            box-shadow: inset 0 0 0 2px rgba(179, 32, 43, 0.65);
        }

        /* Notifikasi toast bertema (pengganti alert bawaan browser) */
        #app-toast {
            position: fixed;
            top: 18px;
            left: 50%;
            z-index: 60;
            width: min(92vw, 440px);
            opacity: 0;
            transform: translateX(-50%) translateY(-16px);
            transition: opacity .3s ease, transform .35s cubic-bezier(.22, .61, .36, 1);
            pointer-events: none;
        }
        #app-toast.show { opacity: 1; transform: translateX(-50%) translateY(0); pointer-events: auto; }
        .app-toast-inner {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            background: rgba(20, 19, 23, 0.92);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-left-width: 4px;
            border-radius: 14px;
            padding: 14px 16px;
            box-shadow: 0 16px 44px -12px rgba(0, 0, 0, 0.7);
            color: #e4e4e7;
            font-size: 14px;
            line-height: 1.45;
        }
        .app-toast-inner.toast-error { border-left-color: #b3202b; }
        .app-toast-inner.toast-error .app-toast-icon { color: #d64550; }
        .app-toast-inner.toast-ok { border-left-color: #16a34a; }
        .app-toast-inner.toast-ok .app-toast-icon { color: #4ade80; }
        .app-toast-icon { font-size: 18px; margin-top: 1px; flex-shrink: 0; }
        .app-toast-body { flex: 1; min-width: 0; }
        .app-toast-title { font-weight: 700; color: #fff; margin-bottom: 2px; }
        .app-toast-close {
            background: none; border: 0; color: #71717a; cursor: pointer;
            font-size: 20px; line-height: 1; padding: 0 2px; flex-shrink: 0;
            transition: color .2s ease;
        }
        .app-toast-close:hover { color: #fff; }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: .001ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: .001ms !important;
            }
            html { scroll-behavior: auto; }
            .js .reveal { opacity: 1 !important; }
            .js .img-fade { opacity: 1 !important; transform: none !important; }
            .barber-stripe { animation: none !important; }
            .scanner-line { display: none !important; }
        }

        /* Scanner Line Animation */
        @keyframes scan {
            0% { top: 10%; opacity: 0; }
            10% { opacity: 1; }
            90% { opacity: 1; }
            100% { top: 90%; opacity: 0; }
        }
        .scanner-line {
            position: absolute;
            width: 80%;
            height: 2px;
            background: linear-gradient(90deg, transparent, #b3202b, #f4efe6, #b3202b, transparent);
            box-shadow: 0 0 14px 2px rgba(179, 32, 43, 0.45);
            left: 10%;
            animation: scan 3s infinite linear;
            z-index: 10;
        }

        /* CSS untuk Referensi Bentuk Wajah */
        .shape-ref {
            width: 80px;
            height: 100px;
            border: 3px dashed #c7ccd3;
            margin: 0 auto;
        }
        .shape-oval { border-radius: 50% / 60% 60% 40% 40%; }
        .shape-round { border-radius: 50%; width: 90px; height: 90px; }
        .shape-square { border-radius: 15%; width: 90px; height: 90px; }
        .shape-oblong { border-radius: 40px; height: 110px; width: 70px; }
        .shape-diamond { transform: rotate(45deg); width: 70px; height: 70px; margin: 15px auto; }
        .shape-heart {
            border-radius: 50% 50% 50% 50% / 30% 30% 70% 70%;
            clip-path: polygon(50% 100%, 100% 30%, 80% 0%, 50% 15%, 20% 0%, 0 30%);
            background: transparent;
            border: 3px dashed #c7ccd3;
        }
    </style>
</head>
<body class="text-zinc-200 min-h-screen flex flex-col antialiased selection:bg-barber-red selection:text-white">

    <!-- Garis tiang barbershop (barber pole) -->
    <div class="barber-stripe h-1.5 w-full"></div>

    <header class="bg-[#141317]/80 backdrop-blur border-b border-white/10 sticky top-0 z-30">
        <div class="max-w-5xl mx-auto px-4 sm:px-6 py-3 md:py-4 flex items-center justify-between gap-3">
            <div class="flex items-center gap-3 min-w-0">
                <div class="w-8 h-11 md:w-9 md:h-12 rounded-full overflow-hidden ring-2 ring-barber-steel/70 shadow-lg shadow-black/50 shrink-0 relative">
                    <div class="barber-stripe absolute inset-0"></div>
                    <div class="absolute inset-x-0 top-0 h-1.5 bg-gradient-to-b from-white/70 to-transparent"></div>
                    <div class="absolute inset-x-0 bottom-0 h-1.5 bg-gradient-to-t from-black/40 to-transparent"></div>
                </div>
                <div class="leading-tight min-w-0">
                    <h1 class="text-lg md:text-xl font-bold text-white tracking-tight font-display truncate">LOOKPAS</h1>
                    <p class="text-[11px] md:text-xs text-barber-steel/80 font-medium -mt-0.5 truncate tracking-wide uppercase">Find the look that's pas for you.</p>
                </div>
            </div>
            <span class="hidden sm:inline-flex items-center gap-2 text-[11px] md:text-xs font-semibold text-zinc-300 bg-white/5 border border-white/10 px-3 py-1.5 rounded-full shrink-0">
                <i class="fa-solid fa-microchip text-barber-red"></i> Pengolahan Citra Digital
            </span>
        </div>
    </header>

    <main class="max-w-5xl mx-auto px-4 sm:px-6 py-8 md:py-12 flex-grow w-full">
        <div class="text-center mb-8 md:mb-12">
            <span class="reveal inline-flex items-center gap-2 text-[11px] sm:text-xs font-semibold text-zinc-300 bg-white/5 border border-barber-red/25 px-4 py-1.5 rounded-full mb-5">
                <i class="fa-solid fa-wand-magic-sparkles text-barber-red"></i> Analisis Wajah Berbasis Computer Vision
            </span>
            <h2 class="reveal text-3xl sm:text-4xl md:text-6xl font-semibold text-white mb-4 tracking-tight leading-[1.08] font-display" style="animation-delay:.08s">
                Temukan Gaya Rambut <br class="hidden sm:block"> yang <span class="aurora italic">Paling Ideal</span>
            </h2>
            <p class="reveal text-zinc-400 max-w-2xl mx-auto text-sm md:text-lg px-1 leading-relaxed" style="animation-delay:.16s">
                Find the look that's pas for you. Sistem kami menganalisis struktur dan proporsi wajahmu menggunakan 468 titik landmark (MediaPipe FaceMesh), lalu merekomendasikan potongan rambut yang paling menonjolkan fiturmu.
            </p>
        </div>

        <!-- Strip Cara Kerja -->
        <div class="grid grid-cols-3 gap-2.5 sm:gap-4 mb-8 md:mb-12">
            <div class="reveal lift bg-white/[0.03] border border-white/10 rounded-2xl p-3 sm:p-5 text-center hover:border-barber-red/40" style="animation-delay:.05s">
                <div class="w-9 h-9 sm:w-10 sm:h-10 mx-auto mb-2 rounded-xl bg-white/[0.06] text-barber-steel border border-white/10 flex items-center justify-center">
                    <i class="fa-solid fa-image text-sm sm:text-base"></i>
                </div>
                <p class="text-xs sm:text-sm font-semibold text-white">1. Beri Foto</p>
                <p class="hidden sm:block text-[11px] md:text-xs text-zinc-500 mt-0.5 leading-snug">Upload atau pakai kamera</p>
            </div>
            <div class="reveal lift bg-white/[0.03] border border-white/10 rounded-2xl p-3 sm:p-5 text-center hover:border-barber-red/40" style="animation-delay:.13s">
                <div class="w-9 h-9 sm:w-10 sm:h-10 mx-auto mb-2 rounded-xl bg-white/[0.06] text-barber-steel border border-white/10 flex items-center justify-center">
                    <i class="fa-solid fa-draw-polygon text-sm sm:text-base"></i>
                </div>
                <p class="text-xs sm:text-sm font-semibold text-white">2. Deteksi Bentuk</p>
                <p class="hidden sm:block text-[11px] md:text-xs text-zinc-500 mt-0.5 leading-snug">AI memetakan geometri</p>
            </div>
            <div class="reveal lift bg-white/[0.03] border border-white/10 rounded-2xl p-3 sm:p-5 text-center hover:border-barber-red/40" style="animation-delay:.21s">
                <div class="w-9 h-9 sm:w-10 sm:h-10 mx-auto mb-2 rounded-xl bg-white/[0.06] text-barber-steel border border-white/10 flex items-center justify-center">
                    <i class="fa-solid fa-scissors text-sm sm:text-base"></i>
                </div>
                <p class="text-xs sm:text-sm font-semibold text-white">3. Rekomendasi</p>
                <p class="hidden sm:block text-[11px] md:text-xs text-zinc-500 mt-0.5 leading-snug">Gaya rambut terbaik</p>
            </div>
        </div>

        <div class="reveal bg-zinc-900/70 rounded-3xl shadow-2xl shadow-black/40 border border-white/10 p-5 md:p-8 mb-8 md:mb-12">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8 lg:divide-x lg:divide-y-0 divide-y divide-white/10">

                <div class="lg:pr-8 pt-6 lg:pt-0 first:pt-0 flex flex-col">
                    <div class="flex items-center gap-3 mb-5">
                        <div class="bg-barber-red/15 border border-barber-red/30 p-3 rounded-xl text-barber-redlight flex items-center justify-center">
                            <i class="fa-solid fa-cloud-arrow-up text-xl"></i>
                        </div>
                        <h3 class="text-lg md:text-xl font-bold text-white">Upload Foto</h3>
                    </div>

                    <form id="upload-form" method="POST" action="/" enctype="multipart/form-data" class="flex flex-col flex-grow space-y-5">
                        <div id="dropzone" class="relative flex-grow min-h-[200px] border-2 border-dashed border-white/15 rounded-2xl bg-black/30 hover:bg-barber-red/[0.06] hover:border-barber-red/50 transition-all duration-200 group overflow-hidden">

                            <input type="file" id="foto" name="foto" accept="image/jpeg, image/jpg, image/png" required
                                   class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                                   onchange="previewImage(this)">

                            <div id="drop-text" class="absolute inset-0 flex flex-col items-center justify-center text-center p-4 z-10 pointer-events-none transition-opacity">
                                <div class="w-16 h-16 mb-4 rounded-full bg-barber-red/10 shadow-sm border border-barber-red/20 flex items-center justify-center text-barber-redlight group-hover:text-white group-hover:scale-110 transition-all">
                                    <i class="fa-regular fa-image text-2xl"></i>
                                </div>
                                <p class="text-sm font-semibold text-zinc-200">Pilih file atau drag & drop di sini</p>
                                <p class="text-xs text-zinc-500 mt-1">Mendukung JPEG, JPG, PNG</p>
                            </div>

                            <div id="preview-container" class="absolute inset-0 z-10 hidden bg-black/40 flex items-center justify-center p-2">
                                <img id="image-preview" src="#" alt="Preview" class="max-h-full max-w-full rounded-xl object-contain shadow-sm border border-white/10 bg-black">
                                <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-2xl">
                                    <span class="bg-barber-red text-white text-sm font-semibold px-4 py-2 rounded-lg shadow-sm">Ganti Foto</span>
                                </div>
                            </div>
                        </div>

                        <button type="submit" id="submit-upload-btn" class="w-full py-3.5 md:py-4 px-4 bg-barber-red hover:bg-barber-reddark text-white rounded-xl font-semibold transition-all shadow-lg shadow-barber-red/25 active:scale-[0.98] flex justify-center items-center gap-2 text-sm md:text-base disabled:opacity-70 disabled:cursor-not-allowed">
                            <i class="fa-solid fa-magnifying-glass"></i> Analisis Wajah
                        </button>
                    </form>
                </div>

                <div class="lg:pl-8 pt-8 lg:pt-0 flex flex-col">
                    <div class="flex items-center gap-3 mb-5">
                        <div class="bg-barber-navy/40 border border-white/10 p-3 rounded-xl text-barber-steel flex items-center justify-center">
                            <i class="fa-solid fa-camera-viewfinder text-xl"></i>
                        </div>
                        <h3 class="text-lg md:text-xl font-bold text-white">Kamera Web Real-time</h3>
                    </div>

                    <div id="cam-frame" class="bg-black rounded-2xl overflow-hidden shadow-inner ring-1 ring-white/10 aspect-[4/3] mb-5 relative flex items-center justify-center flex-grow">
                        <video id="webcam" autoplay playsinline class="w-full h-full object-cover"></video>

                        <div id="video-overlay" class="absolute inset-0 flex items-center justify-center pointer-events-none">
                            <div class="absolute w-[60%] h-[70%] max-w-[250px] max-h-[300px]">
                                <div class="absolute top-0 left-0 w-8 h-8 border-t-4 border-l-4 border-barber-red rounded-tl-xl"></div>
                                <div class="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-barber-steel rounded-tr-xl"></div>
                                <div class="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-barber-steel rounded-bl-xl"></div>
                                <div class="absolute bottom-0 right-0 w-8 h-8 border-b-4 border-r-4 border-barber-red rounded-br-xl"></div>
                            </div>
                            <div class="scanner-line hidden" id="scanner"></div>
                        </div>
                    </div>

                    <button id="capture-btn" class="w-full py-3.5 md:py-4 px-4 bg-white/5 hover:bg-white/10 text-white rounded-xl font-semibold transition-all shadow-md border border-white/15 hover:border-barber-red/60 flex justify-center items-center gap-2 active:scale-[0.98] disabled:opacity-70 disabled:active:scale-100 text-sm md:text-base">
                        <i class="fa-solid fa-camera text-barber-redlight"></i> Scan &amp; Analisis
                    </button>
                    <p id="cam-status" class="text-center text-xs md:text-sm text-zinc-500 mt-3 font-medium flex items-center justify-center gap-2">
                        <i class="fa-solid fa-circle-notch fa-spin text-zinc-500"></i> Mengakses kamera...
                    </p>
                </div>
            </div>
        </div>

        {% if result %}
        <div id="post-result-card" class="bg-zinc-900/70 rounded-3xl shadow-2xl shadow-black/40 border border-white/10 overflow-hidden mb-10 transform transition-all animate-[fadeIn_0.5s_ease-out]">
            <div class="bg-gradient-to-r from-barber-reddark via-barber-red to-barber-reddark px-6 md:px-8 py-5">
                <h2 class="text-lg md:text-xl font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-square-poll-vertical"></i> Laporan Analisis Wajah
                </h2>
            </div>

            <div class="p-5 md:p-8">
                {% if result.success %}
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 md:gap-8 mb-10">

                    <div class="reveal lg:col-span-5 bg-black/30 p-5 sm:p-6 rounded-2xl border border-white/10 h-full flex flex-col">
                        <div class="mb-6 flex items-center justify-center lg:justify-start gap-4 sm:gap-6 flex-wrap">
                            <div class="text-center lg:text-left">
                                <span class="inline-block px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs font-bold text-zinc-400 uppercase tracking-wider mb-3">
                                    Bentuk Wajah Terdeteksi
                                </span>
                                <p class="aurora text-4xl md:text-5xl font-semibold font-display capitalize">
                                    {{ result.label }}
                                </p>
                            </div>

                            <div class="bg-black/40 p-3 rounded-xl border border-white/10 shadow-inner flex flex-col items-center justify-center min-w-[100px] hidden md:flex">
                                <div class="shape-ref shape-{{ result.label | lower }}"></div>
                                <span class="text-[10px] text-zinc-500 font-bold uppercase mt-2 tracking-widest">Pola Asli</span>
                            </div>
                        </div>

                        <div class="space-y-4 mb-6">
                            <div class="bg-white/5 p-4 rounded-xl border border-white/10">
                                <div class="flex justify-between items-center">
                                    <span class="text-zinc-400 text-sm font-semibold flex items-center gap-2"><i class="fa-solid fa-radar-relative text-zinc-500"></i> Akurasi AI</span>
                                    <span data-count="{{ result.confidence * 100 }}" class="font-bold text-barber-cream bg-white/5 border border-white/10 px-3 py-1 rounded-lg text-sm">
                                        {{ "%.1f"|format(result.confidence * 100) }}%
                                    </span>
                                </div>
                                <div class="meter mt-3"><div class="meter-fill" data-value="{{ result.confidence * 100 }}"></div></div>
                            </div>
                            <div class="bg-barber-red/[0.06] p-4 rounded-xl border border-barber-red/20">
                                <span class="text-barber-redlight text-xs font-bold uppercase tracking-wider block mb-1">Catatan Analisis:</span>
                                <p class="text-sm font-medium text-zinc-300 leading-relaxed">{{ result.reasoning }}</p>
                            </div>
                            {% if result.top3 %}
                            <div class="bg-white/5 p-4 rounded-xl border border-white/10">
                                <span class="text-zinc-400 text-xs font-bold uppercase tracking-wider flex items-center gap-2 mb-3"><i class="fa-solid fa-ranking-star text-barber-redlight"></i> Kandidat Teratas</span>
                                <div class="space-y-2">
                                    {% for t in result.top3 %}
                                    <div class="flex items-center gap-3">
                                        <span class="w-16 shrink-0 text-xs font-semibold text-zinc-300 capitalize">{{ t.label }}</span>
                                        <div class="meter flex-grow"><div class="meter-fill" data-value="{{ t.score * 100 }}"></div></div>
                                        <span class="w-9 shrink-0 text-right text-xs font-bold text-barber-cream">{{ "%.0f"|format(t.score * 100) }}%</span>
                                    </div>
                                    {% endfor %}
                                </div>
                            </div>
                            {% endif %}
                        </div>

                        <div class="mt-auto">
                            <h4 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                                <i class="fa-solid fa-ruler-combined"></i> Detail Geometri
                            </h4>
                            <ul class="grid grid-cols-2 gap-2 text-sm text-zinc-400">
                                {% for k, v in result.features.items() %}
                                    <li class="bg-black/40 px-3 py-2 rounded-lg border border-white/10 flex justify-between gap-2">
                                        <span class="truncate">{{ k }}</span>
                                        <span class="font-bold text-white shrink-0">{{ "%.2f"|format(v) if v is float else v }}</span>
                                    </li>
                                {% endfor %}
                            </ul>
                        </div>
                    </div>

                    <div class="reveal lg:col-span-7 flex flex-col" style="animation-delay:.12s">
                        <h4 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-3 text-center lg:text-left flex justify-center lg:justify-start items-center gap-2">
                            <i class="fa-solid fa-user-astronaut"></i> Visualisasi Deteksi
                        </h4>
                        <div class="bg-black rounded-2xl p-2 border border-white/10 flex-grow flex items-center justify-center min-h-[300px] overflow-hidden relative group">
                            <img src="/data/hasil_annotasi.jpg?t={{ timestamp }}" alt="Hasil Annotasi" class="img-fade max-h-[450px] w-auto rounded-xl shadow-sm object-contain group-hover:scale-105 transition-transform duration-500">
                        </div>
                    </div>
                </div>

               {% if steps %}
                               <div class="reveal mt-8 mb-10 pt-8 border-t border-white/10">
                                   <div class="text-center mb-6">
                                       <h3 class="text-lg md:text-xl font-bold text-white flex justify-center items-center gap-2">
                                           <i class="fa-solid fa-microchip text-zinc-400"></i> Tahapan Pemrosesan Citra Digital
                                       </h3>
                                       <p class="text-sm text-zinc-500 mt-1">Bagaimana AI melihat dan memetakan wajahmu</p>
                                   </div>

                                   <div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                                       <div class="flex flex-col items-center bg-black/30 p-2 rounded-xl border border-white/10">
                                           <span class="text-xs font-semibold text-zinc-400 mb-2">1. Original</span>
                                           <img src="data:image/jpeg;base64,{{ steps['1_original'] }}" class="rounded-lg shadow-sm border border-white/10 w-full object-cover">
                                       </div>
                                       <div class="flex flex-col items-center bg-black/30 p-2 rounded-xl border border-white/10">
                                           <span class="text-xs font-semibold text-zinc-400 mb-2">2. Grayscale</span>
                                           <img src="data:image/jpeg;base64,{{ steps['2_grayscale'] }}" class="rounded-lg shadow-sm border border-white/10 w-full object-cover">
                                       </div>
                                       <div class="flex flex-col items-center bg-black/30 p-2 rounded-xl border border-white/10">
                                           <span class="text-xs font-semibold text-zinc-400 mb-2">3. Smoothing (Blur)</span>
                                           <img src="data:image/jpeg;base64,{{ steps['3_smoothing'] }}" class="rounded-lg shadow-sm border border-white/10 w-full object-cover">
                                       </div>
                                       <div class="flex flex-col items-center bg-black/30 p-2 rounded-xl border border-white/10">
                                           <span class="text-xs font-semibold text-zinc-400 mb-2">4. CLAHE (Kontras)</span>
                                           <img src="data:image/jpeg;base64,{{ steps['4_clahe_enhancement'] }}" class="rounded-lg shadow-sm border border-white/10 w-full object-cover">
                                       </div>
                                       <div class="flex flex-col items-center bg-black/30 p-2 rounded-xl border border-white/10">
                                           <span class="text-xs font-semibold text-zinc-400 mb-2">5. Edge Detection</span>
                                           <img src="data:image/jpeg;base64,{{ steps['5_edge_detection'] }}" class="rounded-lg shadow-sm border border-white/10 w-full object-cover">
                                       </div>
                                       <div class="flex flex-col items-center bg-black/30 p-2 rounded-xl border border-white/10">
                                           <span class="text-xs font-semibold text-zinc-400 mb-2">6. Deteksi Wajah</span>
                                           <img src="data:image/jpeg;base64,{{ steps['6_face_detection'] }}" class="rounded-lg shadow-sm border border-white/10 w-full object-cover">
                                       </div>
                                       <div class="flex flex-col items-center bg-black/30 p-2 rounded-xl border border-white/10">
                                           <span class="text-xs font-semibold text-zinc-400 mb-2">7. Face Mesh (468 Titik)</span>
                                           <img src="data:image/jpeg;base64,{{ steps['7_landmarks'] }}" class="rounded-lg shadow-sm border border-white/10 w-full object-cover">
                                       </div>
                                       <div class="flex flex-col items-center bg-gradient-to-br from-barber-red/20 to-barber-navy/40 p-2 rounded-xl border border-barber-red/30">
                                           <span class="text-xs font-bold text-barber-redlight mb-2">8. Pola Geometri</span>
                                           <img src="data:image/jpeg;base64,{{ steps['8_shape_pattern'] }}" class="rounded-lg shadow-sm border border-barber-red/30 w-full object-cover">
                                       </div>
                                   </div>
                               </div>
                               {% endif %}

                <div class="border-t border-white/10 pt-8">
                    <div class="flex items-center justify-between mb-6">
                        <h3 class="text-xl md:text-2xl font-bold text-white flex items-center gap-3">
                            <div class="bg-gradient-to-br from-barber-red to-barber-reddark text-white p-2 rounded-xl text-lg shadow-lg shadow-barber-red/30">
                                <i class="fa-solid fa-wand-magic-sparkles"></i>
                            </div>
                            Top Rekomendasi Gaya Rambut
                        </h3>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6">
                        {% for h in result.hairstyles %}
                            <div class="reveal lift bg-black/30 border border-white/10 rounded-2xl overflow-hidden hover:shadow-xl hover:shadow-barber-red/15 hover:border-barber-red/40 group flex flex-col cursor-pointer" style="animation-delay:{{ loop.index0 * 0.08 + 0.05 }}s">
                                <div class="aspect-[4/5] bg-black overflow-hidden relative">
                                    <img src="/static/images/hairstyles/{{ result.face_shape }}/{{ h.name.lower().replace(' ', '_') }}/{{ h.name.lower().replace(' ', '_') }}_1.jpg"
                                         onerror="this.onerror=null; this.src='/static/images/hairstyles/diamond/fringe/fringe_1.jpg';"
                                         alt="{{ h.name }}"
                                         class="img-fade w-full h-full object-cover group-hover:scale-110 transition-transform duration-700">
                                    <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                                </div>
                                <div class="p-5 flex-grow flex flex-col justify-between z-10 relative">
                                    <div>
                                        <h4 class="text-lg font-bold text-white mb-2 capitalize group-hover:text-barber-redlight transition-colors">{{ h.name }}</h4>
                                        <p class="text-zinc-400 text-sm leading-relaxed">{{ h.description }}</p>
                                    </div>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                </div>
                {% else %}
                <div class="bg-red-500/10 border border-red-500/30 text-red-300 p-6 rounded-2xl flex flex-col items-center justify-center text-center gap-3">
                    <div class="w-16 h-16 bg-red-500/15 text-red-400 rounded-full flex items-center justify-center text-3xl mb-2">
                        <i class="fa-solid fa-face-frown-open"></i>
                    </div>
                    <h3 class="font-bold text-lg text-red-200">Gagal Menganalisis</h3>
                    <p class="font-medium text-red-300/90">{{ result.error }}</p>
                    <p class="text-sm text-red-300/60 mt-2">Pastikan wajah terlihat jelas, tidak terpotong, dan pencahayaan cukup.</p>
                </div>
                {% endif %}
            </div>
        </div>
        {% endif %}

        <div id="js-result-card" class="bg-zinc-900/70 rounded-3xl shadow-2xl shadow-black/40 border border-white/10 overflow-hidden mb-10 hidden">
            <div class="bg-gradient-to-r from-barber-navy via-barber-navylight to-barber-navy px-6 md:px-8 py-5">
                <h2 class="text-lg md:text-xl font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-bolt text-barber-redlight"></i> Laporan Analisis Kamera Real-time
                </h2>
            </div>

            <div class="p-5 md:p-8">
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 md:gap-8 mb-10">
                    <div class="lg:col-span-5 bg-black/30 p-5 sm:p-6 rounded-2xl border border-white/10 h-full flex flex-col" id="js-info">
                        </div>

                    <div class="lg:col-span-7 flex flex-col">
                        <h4 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-3 text-center lg:text-left flex justify-center lg:justify-start items-center gap-2">
                            <i class="fa-solid fa-user-astronaut"></i> Visualisasi Deteksi
                        </h4>
                        <div class="bg-black rounded-2xl p-2 border border-white/10 flex-grow flex items-center justify-center min-h-[300px] overflow-hidden group relative">
                            <img id="js-annotated" src="" alt="Annotasi Realtime" class="img-fade max-h-[450px] w-auto rounded-xl shadow-sm object-contain hidden group-hover:scale-105 transition-transform duration-500">
                        </div>
                    </div>
                </div>
                <div id="js-steps-container" class="mt-8 mb-10 pt-8 border-t border-white/10 hidden">
                                    <div class="text-center mb-6">
                                        <h3 class="text-lg md:text-xl font-bold text-white flex justify-center items-center gap-2">
                                            <i class="fa-solid fa-microchip text-zinc-400"></i> Tahapan Pemrosesan Citra Digital
                                        </h3>
                                        <p class="text-sm text-zinc-500 mt-1">Bagaimana AI melihat dan memetakan wajahmu</p>
                                    </div>

                                    <div id="js-steps-grid" class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                                    </div>
                                </div>

                <div class="border-t border-white/10 pt-8">
                    <div class="flex items-center justify-between mb-6">
                        <h3 class="text-xl md:text-2xl font-bold text-white flex items-center gap-3">
                            <div class="bg-gradient-to-br from-barber-red to-barber-reddark text-white p-2 rounded-xl text-lg shadow-lg shadow-barber-red/30">
                                <i class="fa-solid fa-wand-magic-sparkles"></i>
                            </div>
                            Top Rekomendasi Gaya Rambut
                        </h3>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6" id="js-hairstyle-grid">
                        </div>
                </div>
            </div>
        </div>

    </main>

    <footer class="bg-black/40 backdrop-blur border-t border-white/10 mt-auto py-8">
        <div class="max-w-5xl mx-auto px-4 text-center">
            <div class="flex items-center justify-center gap-2 mb-2 text-zinc-200">
                <i class="fa-solid fa-scissors text-barber-red"></i>
                <span class="font-semibold font-display">LOOKPAS</span>
            </div>
            <p class="text-zinc-500 text-sm font-medium">
                Proyek Pengolahan Citra Digital &middot; &copy; 2026 &middot; All rights reserved.
            </p>
        </div>
    </footer>
    <script src="{{ url_for('static', filename='script.js') }}"></script>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    result_data = None
    img_steps = None

    if request.method == "POST":
        upload_path = os.path.join(UPLOAD_FOLDER, "foto_upload_terakhir.jpeg")
        is_file_processed = False

        if "foto" in request.files:
            file = request.files["foto"]
            if file.filename != "":
                file.save(upload_path)
                is_file_processed = True

        if is_file_processed:
            result_data = rec.analyze(upload_path)
            if result_data["success"]:
                cv2.imwrite(
                    os.path.join(UPLOAD_FOLDER, "hasil_annotasi.jpg"),
                    result_data["annotated_img"],
                )
                img_steps = get_processing_steps(upload_path)

    return render_template_string(
        HTML_TEMPLATE, result=result_data, steps=img_steps, timestamp=int(time.time())
    )


@app.route("/analyze_capture", methods=["POST"])
def analyze_capture():
    data = request.get_json()
    if not data or "image" not in data:
        return jsonify({"success": False, "error": "Tidak ada data gambar."})

    try:
        header, encoded = data["image"].split(",", 1)
        img_bytes = base64.b64decode(encoded)
    except Exception:
        return jsonify({"success": False, "error": "Format base64 tidak valid."})

    upload_path = os.path.join(UPLOAD_FOLDER, "kamera_capture_terakhir.jpeg")
    with open(upload_path, "wb") as f:
        f.write(img_bytes)

    result = rec.analyze(upload_path)

    if result["success"]:
        cv2.imwrite(
            os.path.join(UPLOAD_FOLDER, "hasil_annotasi.jpg"),
            result["annotated_img"],
        )
        result.pop("annotated_img", None)

        result["steps"] = get_processing_steps(upload_path)
        result["timestamp"] = int(time.time())

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=False)
