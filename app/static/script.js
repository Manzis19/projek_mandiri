// === LOGIKA UNTUK UPLOAD & PREVIEW FOTO ===
const dropzone = document.getElementById("dropzone");
const uploadForm = document.getElementById("upload-form");
const submitUploadBtn = document.getElementById("submit-upload-btn");
const dropText = document.getElementById("drop-text");
const previewContainer = document.getElementById("preview-container");
const imagePreview = document.getElementById("image-preview");

function previewImage(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function (e) {
      imagePreview.src = e.target.result;
      dropText.classList.add("hidden");
      previewContainer.classList.remove("hidden");
      dropzone.classList.remove("border-dashed");
      dropzone.classList.add("border-solid", "border-white/40");
    };
    reader.readAsDataURL(input.files[0]);
  }
}

uploadForm.addEventListener("submit", function () {
  submitUploadBtn.disabled = true;
  submitUploadBtn.innerHTML =
    '<i class="fa-solid fa-spinner fa-spin"></i> Sedang Memproses...';
});

// === LOGIKA UNTUK KAMERA WEBCAM ===
const video = document.getElementById("webcam");
const captureBtn = document.getElementById("capture-btn");
const camStatus = document.getElementById("cam-status");
const scannerLine = document.getElementById("scanner");
const camFrame = document.getElementById("cam-frame");

const jsResultCard = document.getElementById("js-result-card");
const jsInfo = document.getElementById("js-info");
const jsAnnotated = document.getElementById("js-annotated");
const jsGrid = document.getElementById("js-hairstyle-grid");

const jsStepsContainer = document.getElementById("js-steps-container");
const jsStep1 = document.getElementById("js-step-1");
const jsStep2 = document.getElementById("js-step-2");
const jsStep3 = document.getElementById("js-step-3");
const jsStep4 = document.getElementById("js-step-4");
const jsStep5 = document.getElementById("js-step-5");

const isMobile = window.innerWidth < 768;
const videoConstraints = {
  width: isMobile ? { ideal: 480 } : { ideal: 640 },
  height: isMobile ? { ideal: 640 } : { ideal: 480 },
  facingMode: "user",
};

navigator.mediaDevices
  .getUserMedia({ video: videoConstraints })
  .then((stream) => {
    video.srcObject = stream;
    camStatus.innerHTML =
      '<span class="text-emerald-400 font-semibold"><i class="fa-solid fa-circle-check"></i> Kamera siap digunakan</span>';
  })
  .catch((err) => {
    camStatus.innerHTML = `<span class="text-red-400"><i class="fa-solid fa-circle-xmark"></i> Kamera tidak dapat diakses. Pastikan browser diizinkan mengakses kamera.</span>`;
    captureBtn.disabled = true;
  });

// === LOGIKA BARU: MEMBUAT KOTAK (SQUARE 1:1) DARI KAMERA ===
captureBtn.addEventListener("click", async () => {
  if (!video.videoWidth) return;

  const originalBtnText = captureBtn.innerHTML;
  captureBtn.disabled = true;
  captureBtn.innerHTML =
    '<i class="fa-solid fa-spinner fa-spin"></i> Menganalisis...';
  camStatus.innerHTML =
    '<span class="text-emerald-400"><i class="fa-solid fa-microchip fa-fade"></i> AI sedang bekerja...</span>';
  scannerLine.classList.remove("hidden");
  if (camFrame) camFrame.classList.add("processing");

  // 1. Cari ukuran sisi terpendek untuk dijadikan ukuran persegi
  const minSize = Math.min(video.videoWidth, video.videoHeight);

  // 2. Hitung titik potong X dan Y agar area yang diambil persis di tengah video
  const startX = (video.videoWidth - minSize) / 2;
  const startY = (video.videoHeight - minSize) / 2;

  // 3. Atur ukuran canvas menjadi persegi murni (1:1)
  const canvas = document.createElement("canvas");
  canvas.width = minSize;
  canvas.height = minSize;
  const ctx = canvas.getContext("2d");

  // 4. Efek cermin (Mirroring)
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);

  // 5. Gambar video ke canvas HANYA pada area kotak tengah yang sudah dihitung
  ctx.drawImage(
    video,
    startX,
    startY,
    minSize,
    minSize, // Koordinat & ukuran dari sumber (video)
    0,
    0,
    minSize,
    minSize, // Koordinat & ukuran tujuan (canvas)
  );

  // Hasilnya adalah base64 image dengan rasio murni 1:1
  const dataUrl = canvas.toDataURL("image/jpeg", 0.9);

  try {
    const res = await fetch("/analyze_capture", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: dataUrl }),
    });
    const result = await res.json();

    if (result.success) {
      updateResultUI(result);
      camStatus.innerHTML =
        '<span class="text-emerald-400 font-semibold"><i class="fa-solid fa-check-double"></i> Analisis berhasil!</span>';
    } else {
      showErrorUI(result.error);
    }
  } catch (e) {
    showErrorUI("Gagal terhubung ke server. Periksa koneksi internet.");
  }

  captureBtn.disabled = false;
  captureBtn.innerHTML = originalBtnText;
  scannerLine.classList.add("hidden");
  if (camFrame) camFrame.classList.remove("processing");
});

function showErrorUI(message) {
  camStatus.innerHTML = `<span class="text-red-400 font-semibold"><i class="fa-solid fa-triangle-exclamation"></i> Gagal: ${message}</span>`;
  showToast(message, "error");
}

// === TOAST BERTEMA (pengganti alert bawaan browser) ===
let _toastTimer = null;
function showToast(message, type = "error") {
  let toast = document.getElementById("app-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "app-toast";
    document.body.appendChild(toast);
  }
  const isError = type !== "ok";
  const icon = isError ? "fa-triangle-exclamation" : "fa-circle-check";
  const title = isError ? "Terjadi Kesalahan" : "Berhasil";
  toast.innerHTML = `
    <div class="app-toast-inner ${isError ? "toast-error" : "toast-ok"}" role="alert">
      <i class="fa-solid ${icon} app-toast-icon"></i>
      <div class="app-toast-body">
        <div class="app-toast-title">${title}</div>
        <div>${message}</div>
      </div>
      <button type="button" class="app-toast-close" aria-label="Tutup">&times;</button>
    </div>`;
  toast.querySelector(".app-toast-close").addEventListener("click", hideToast);
  requestAnimationFrame(() => toast.classList.add("show"));
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(hideToast, 5000);
}

function hideToast() {
  const toast = document.getElementById("app-toast");
  if (toast) toast.classList.remove("show");
}

function updateResultUI(result) {
  const postResult = document.getElementById("post-result-card");
  if (postResult) postResult.style.display = "none";

  jsResultCard.classList.remove("hidden");

  let featuresHTML = "";
  for (const [k, v] of Object.entries(result.features || {})) {
    featuresHTML += `
                    <li class="bg-black/40 px-3 py-2 rounded-lg border border-white/10 flex justify-between gap-2">
                        <span class="truncate">${k}</span>
                        <span class="font-bold text-white shrink-0">${typeof v === "number" ? v.toFixed(2) : v}</span>
                    </li>`;
  }

  let top3HTML = "";
  if (result.top3 && result.top3.length) {
    const rows = result.top3
      .map(
        (t) => `
                        <div class="flex items-center gap-3">
                            <span class="w-16 shrink-0 text-xs font-semibold text-zinc-300 capitalize">${t.label}</span>
                            <div class="meter flex-grow"><div class="meter-fill" data-value="${t.score * 100}"></div></div>
                            <span class="w-9 shrink-0 text-right text-xs font-bold text-barber-cream">${Math.round(t.score * 100)}%</span>
                        </div>`,
      )
      .join("");
    top3HTML = `
                    <div class="bg-white/5 p-4 rounded-xl border border-white/10">
                        <span class="text-zinc-400 text-xs font-bold uppercase tracking-wider flex items-center gap-2 mb-3"><i class="fa-solid fa-ranking-star text-barber-redlight"></i> Kandidat Teratas</span>
                        <div class="space-y-2">${rows}</div>
                    </div>`;
  }

  jsInfo.innerHTML = `
                <div class="mb-6 flex items-center justify-center lg:justify-start gap-4 sm:gap-6 flex-wrap">
                    <div class="text-center lg:text-left">
                        <span class="inline-block px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs font-bold text-zinc-400 uppercase tracking-wider mb-3">
                            Bentuk Wajah Terdeteksi
                        </span>
                        <p class="aurora text-4xl md:text-5xl font-semibold font-display capitalize">
                            ${result.label}
                        </p>
                    </div>
                    <div class="bg-black/40 p-3 rounded-xl border border-white/10 shadow-inner flex flex-col items-center justify-center min-w-[100px] hidden md:flex">
                        <div class="shape-ref shape-${result.label.toLowerCase()}"></div>
                        <span class="text-[10px] text-zinc-500 font-bold uppercase mt-2 tracking-widest">Pola Asli</span>
                    </div>
                </div>
                <div class="space-y-4 mb-6">
                    <div class="bg-white/5 p-4 rounded-xl border border-white/10">
                        <div class="flex justify-between items-center">
                            <span class="text-zinc-400 text-sm font-semibold flex items-center gap-2"><i class="fa-solid fa-radar-relative text-zinc-500"></i> Akurasi AI</span>
                            <span data-count="${result.confidence * 100}" class="font-bold text-barber-cream bg-white/5 border border-white/10 px-3 py-1 rounded-lg text-sm">
                                ${(result.confidence * 100).toFixed(1)}%
                            </span>
                        </div>
                        <div class="meter mt-3"><div class="meter-fill" data-value="${result.confidence * 100}"></div></div>
                    </div>
                    <div class="bg-barber-red/[0.06] p-4 rounded-xl border border-barber-red/20">
                        <span class="text-barber-redlight text-xs font-bold uppercase tracking-wider block mb-1">Catatan Analisis:</span>
                        <p class="text-sm font-medium text-zinc-300 leading-relaxed">${result.reasoning}</p>
                    </div>
                    ${top3HTML}
                </div>
                <div class="mt-auto">
                    <h4 class="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                        <i class="fa-solid fa-ruler-combined"></i> Detail Geometri
                    </h4>
                    <ul class="grid grid-cols-2 gap-2 text-sm text-zinc-400">
                        ${featuresHTML}
                    </ul>
                </div>
            `;

  jsAnnotated.src = "/data/hasil_annotasi.jpg?t=" + result.timestamp;
  jsAnnotated.classList.remove("hidden");

  if (result.steps) {
    document.getElementById("js-steps-container").classList.remove("hidden");
    const grid = document.getElementById("js-steps-grid");
    grid.innerHTML = "";

    let stepIndex = 0;
    Object.keys(result.steps).forEach((key) => {
      let labelName = key.replace(/_/g, " ").toUpperCase();
      let isFinalStep = key.includes("shape_pattern");

      let bgColor = isFinalStep
        ? "bg-gradient-to-br from-barber-red/20 to-barber-navy/40 border-barber-red/30"
        : "bg-black/30 border-white/10";
      let textColor = isFinalStep ? "text-barber-redlight" : "text-zinc-400";

      let stepHtml = `
              <div class="reveal flex flex-col items-center p-2 rounded-xl border ${bgColor}" style="animation-delay:${(stepIndex * 0.06).toFixed(2)}s">
                  <span class="text-xs font-semibold ${textColor} mb-2">${labelName}</span>
                  <img src="data:image/jpeg;base64,${result.steps[key]}" class="img-fade rounded-lg shadow-sm border border-white/10 w-full object-cover">
              </div>
          `;
      grid.insertAdjacentHTML("beforeend", stepHtml);
      stepIndex++;
    });
  }

  jsGrid.innerHTML = result.hairstyles
    .map((h, i) => {
      const slug = h.name.toLowerCase().replace(/ /g, "_");
      return `
                    <div class="reveal lift bg-black/30 border border-white/10 rounded-2xl overflow-hidden hover:shadow-xl hover:shadow-barber-red/15 hover:border-barber-red/40 group flex flex-col cursor-pointer" style="animation-delay:${(i * 0.08 + 0.05).toFixed(2)}s">
                        <div class="aspect-[4/5] bg-black overflow-hidden relative">
                            <img src="/static/images/hairstyles/${result.face_shape}/${slug}/${slug}_1.jpg"
                                 onerror="this.onerror=null; this.src='/static/images/hairstyles/diamond/fringe/fringe_1.jpg';"
                                 alt="${h.name}"
                                 class="img-fade w-full h-full object-cover group-hover:scale-110 transition-transform duration-700">
                            <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                        </div>
                        <div class="p-5 flex-grow flex flex-col justify-between z-10 relative">
                            <div>
                                <h4 class="text-lg font-bold text-white mb-2 capitalize group-hover:text-barber-redlight transition-colors">${h.name}</h4>
                                <p class="text-zinc-400 text-sm leading-relaxed">${h.description}</p>
                            </div>
                        </div>
                    </div>`;
    })
    .join("");

  // Aktifkan animasi (reveal + count-up + meter + fade gambar) untuk konten baru
  activate(jsResultCard);

  const yOffset = -70;
  const y =
    jsResultCard.getBoundingClientRect().top + window.pageYOffset + yOffset;
  window.scrollTo({ top: y, behavior: prefersReduced ? "auto" : "smooth" });
}

// =============================================================
// === ENHANCEMENT UX: ANIMASI, REVEAL, COUNT-UP, DRAG & DROP ===
// =============================================================
const prefersReduced = window.matchMedia(
  "(prefers-reduced-motion: reduce)",
).matches;

// Count-up angka (mis. akurasi %)
function animateCount(el) {
  const target = parseFloat(el.dataset.count);
  if (isNaN(target)) return;
  if (prefersReduced) {
    el.textContent = target.toFixed(1) + "%";
    return;
  }
  const duration = 900;
  const start = performance.now();
  function tick(now) {
    const p = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
    el.textContent = (target * eased).toFixed(1) + "%";
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

// Isi meter/progress bar dengan animasi lebar
function fillMeter(el) {
  const v = parseFloat(el.dataset.value);
  if (isNaN(v)) return;
  const w = Math.max(0, Math.min(100, v)) + "%";
  if (prefersReduced) {
    el.style.width = w;
    return;
  }
  requestAnimationFrame(() => {
    el.style.width = w;
  });
}

// Fade-in gambar saat selesai dimuat (blur-up)
function initImageFade(img) {
  if (img.dataset.fadeInit) return;
  img.dataset.fadeInit = "1";
  if (img.complete && img.naturalWidth) {
    img.classList.add("loaded");
  } else {
    img.addEventListener("load", () => img.classList.add("loaded"), {
      once: true,
    });
    img.addEventListener("error", () => img.classList.add("loaded"), {
      once: true,
    });
  }
}

// Aktifkan seluruh efek pada sebuah bagian (dipakai untuk konten dinamis)
function activate(root) {
  if (!root) return;
  root.querySelectorAll(".reveal").forEach((el) => el.classList.add("is-visible"));
  root.querySelectorAll("[data-count]").forEach(animateCount);
  root.querySelectorAll(".meter-fill").forEach(fillMeter);
  root.querySelectorAll(".img-fade").forEach(initImageFade);
}

// Observer untuk reveal konten statis saat masuk viewport
const revealObserver =
  "IntersectionObserver" in window
    ? new IntersectionObserver(
        (entries, obs) => {
          entries.forEach((e) => {
            if (!e.isIntersecting) return;
            e.target.classList.add("is-visible");
            e.target.querySelectorAll?.("[data-count]").forEach(animateCount);
            e.target.querySelectorAll?.(".meter-fill").forEach(fillMeter);
            obs.unobserve(e.target);
          });
        },
        { threshold: 0.12, rootMargin: "0px 0px -40px 0px" },
      )
    : null;

// Interaksi drag & drop untuk dropzone upload
function initDragAndDrop() {
  if (!dropzone) return;
  const fotoInput = document.getElementById("foto");

  const highlight = () => dropzone.classList.add("drag-over");
  const unhighlight = () => dropzone.classList.remove("drag-over");

  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      highlight();
    }),
  );

  dropzone.addEventListener("dragleave", (e) => {
    e.preventDefault();
    if (dropzone.contains(e.relatedTarget)) return; // masih di dalam area
    unhighlight();
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    unhighlight();
    const files = e.dataTransfer && e.dataTransfer.files;
    if (files && files.length && fotoInput) {
      fotoInput.files = files;
      previewImage(fotoInput);
    }
  });
}

// Inisialisasi seluruh enhancement setelah DOM siap
function initEnhancements() {
  // Fade-in semua gambar statis (hasil server)
  document.querySelectorAll(".img-fade").forEach(initImageFade);

  // Reveal konten statis
  if (revealObserver) {
    document.querySelectorAll(".reveal").forEach((el) => revealObserver.observe(el));
  } else {
    document.querySelectorAll(".reveal").forEach((el) =>
      el.classList.add("is-visible"),
    );
  }

  initDragAndDrop();

  // Setelah upload (reload penuh): scroll halus ke laporan hasil
  const serverResult = document.getElementById("post-result-card");
  if (serverResult) {
    setTimeout(() => {
      const y =
        serverResult.getBoundingClientRect().top + window.pageYOffset - 70;
      window.scrollTo({ top: y, behavior: prefersReduced ? "auto" : "smooth" });
    }, 350);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initEnhancements);
} else {
  initEnhancements();
}
