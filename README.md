# KPAB GIMBAL Web Application
**Generasi Indonesia Menyatu Bersama Alam**

Aplikasi web modern untuk organisasi petualang alam bebas **KPAB GIMBAL**, dibangun dengan arsitektur **Python Flask + Full HTMX (Dual-Layer) + SQLite Database**.

---

## 🌟 Fitur Utama yang Telah Diimplementasikan

### 1. Arsitektur Dual-Layer HTMX (Sesuai Standar Koperasi STU)
* **Layer 1 (`index.html`)**: Outer Shell Frame dengan Tailwind CSS lokal, HTMX lokal, Alpine.js lokal, FontAwesome icons, dan Google Fonts.
* **Layer 2 (`shell.html`)**: Application Shell bernuansa outdoor dengan Header navigasi sticky, indikator loading (`#loading`), status badge keanggotaan, modal container (`#modal-container`), dan wadah utama `#main-content`.
* **SPA Feel**: Navigasi antar halaman menggunakan HTMX swap instan tanpa *page reload*, disertai pembaruan URL otomatis (`hx-push-url="true"`).

### 2. Autentikasi Google OAuth & Mode Cepat Pengujian (Dev Switcher)
* Pendaftaran 1-klik dengan Akun Google resmi.
* **Dev Mode Switcher**: Memungkinkan pengujian instan berganti peran tanpa harus setup Google Cloud credentials terlebih dahulu:
  * Masuk sebagai **Pengurus Admin** (`admin@gimbal.org` / `R-01-26`)
  * Masuk sebagai **Anggota Aktif** (`budi.pendaki@gmail.com` / `R-02-26`)
  * Masuk sebagai **Calon Anggota Pending** (`calon.petualang@gmail.com`)

### 3. Logika Penomoran Anggota Resmi (`R-nn-YY`)
* **Format**: `R-nn-YY` (contoh: `R-01-26`, `R-02-26`, `R-03-26`).
* **Aturan Khusus**:
  * `YY` = 2 digit tahun saat admin menyetujui pendaftaran (misal tahun 2026 -> `26`).
  * `nn` = nomor urut persetujuan admin pada tahun tersebut (dimulai dari `01`).
  * **Reset tahunan**: Nomor urut `nn` otomatis kembali ke `01` pada pergantian tahun baru.
  * Calon anggota yang baru mendaftar berstatus `PENDING` (belum memiliki NRA). Begitu admin menekan tombol **"Setujui & Terbitkan R-nn-YY"**, sistem mengkalkulasi urutan persetujuan tertinggi dan mengalokasikan nomor NRA resmi secara atomik.

### 4. KTA Digital & QR Code Validasi Lapangan
* Desain fisik kartu digital bernuansa outdoor khas GIMBAL (Nama, NRA `R-nn-YY`, Gol. Darah, Foto Profil, Status).
* **QR Code Interaktif**: Mengarah ke halaman validasi publik `/verify-kta/<nra>` untuk pembuktian keabsahan keanggotaan di pos perizinan pendakian (Simaksi) atau di lapangan.

### 5. Manajemen Iuran Kas & Verifikasi Pembayaran
* **Anggota**: Memantau status iuran bulanan dan mengunggah foto/screenshot slip bukti transfer via modal HTMX.
* **Admin**: Verifikasi bukti transfer (Setujui / Tolak), rekapitulasi total kas masuk, dan pembuatan master tagihan iuran baru.

### 6. CRUD Dokumen Resmi Organisasi (Backend Admin)
* Pengurus dapat menambah, mengedit, dan menghapus dokumen internal:
  * **AD / ART & Legalitas**
  * **SOP Keselamatan & Pendakian**
  * **Modul Navigasi & Survival Rimba**
* Anggota aktif dapat mengunduh dokumen langsung dari portal anggota.

### 7. Agenda Ekspedisi & Kegiatan
* Menampilkan daftar kegiatan petualangan (tingkat kesulitan, kuota peserta, tanggal, lokasi).
* Anggota dapat mendaftarkan diri secara instan.

### 8. Konfigurasi Terpusat Lebar Konten & Warna Monotone Tahunan
* **File Konfigurasi Utama**: [static/js/theme-config.js](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/js/theme-config.js) & [static/css/theme.css](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/css/theme.css)
* **Pengaturan 1 Variabel untuk Lebar Konten**:
  * Cukup ubah `GIMBAL_SITE_WIDTH = '70%';` untuk mengatur lebar seluruh halaman website (Landing, Portal Anggota, Admin, Header, Footer).
* **Pengaturan 1 Variabel untuk Warna Monotone Tahunan**:
  * Cukup ubah `GIMBAL_THEME_COLOR = 'orange';` dengan preset tahunan:
    * `'orange'` (Oranye Resmi GIMBAL)
    * `'emerald'` (Hijau Rimba / Konservasi)
    * `'blue'` (Biru Tirta / Air)
    * `'amber'` (Emas Fajar)
    * `'rose'` (Merah Terracotta Tebing)
    * `'teal'` (Toska Danau Gunung)
  * Seluruh komponen tombol, kartu KTA, badge, gradasi hero, dan aksen navigasi akan otomatis berubah seragam.
* **Pengaturan 1 Variabel untuk Mode Tampilan (Bright & Dark Mode)**:
  * Cukup ubah `GIMBAL_COLOR_MODE = 'bright';` (`'bright'` atau `'dark'`) sebagai default mode utama seluruh web.
  * Dilengkapi tombol toggle interaktif (ikon Matahari / Bulan) di navigasi desktop & mobile pada semua bagian website.
* **Section Hero Sinematik**:
  * Lebar gambar latar belakang membentang penuh 100% (*edge-to-edge*).
  * Konten teks, judul, tombol, dan metrik di dalamnya otomatis mengikuti lebar kontainer (`.site-container`).

### 9. Modul CRUD Galeri Ekspedisi (Pin-Down System)
* **Pusat Kurasi Foto**: Mengumpulkan dokumentasi dari seluruh agenda ekspedisi dan perjalanan petualang.
* **Sistem Pin-down**: Pengurus dapat menentukan foto mana saja yang di-pin ke etalase galeri landing page utama atau disimpan sebagai arsip ekspedisi.
* **Fitur**: Upload foto lokal ke `uploads/gallery/` atau URL gambar, hubungkan ke agenda ekspedisi, pilih kategori divisi, edit, toggle pin instan via HTMX, dan hapus foto.

### 10. Ilustrasi Visual Cartoonized & 3D Character Avatars
* Seluruh visual di landing page menggunakan gaya ilustrasi anime adventure / Ghibli landscape dan avatar pengurus 3D Pixar-style yang tersimpan di `static/pics/cartoon/`.

---

## 📜 Rekam Jejak Percakapan & Keputusan Arsitektur
Seluruh kronologi instruksi, keputusan arsitektural, dan spesifikasi teknis telah didokumentasikan secara lengkap dalam file:
👉 **[CONVERSATION_HISTORY.md](file:///g:/My%20Drive/priv_web_apps/gimbal-web/CONVERSATION_HISTORY.md)**

---

## 🚀 Cara Menjalankan Aplikasi

1. **Jalankan Seeder Database (Inisialisasi SQLite)**:
   ```bash
   python seed.py
   ```

2. **Jalankan Server Flask**:
   ```bash
   python app.py
   ```
   Aplikasi akan berjalan di: `http://127.0.0.1:8083`

3. **Menjalankan Automated Unit Tests**:
   ```bash
   python test_app.py
   ```

---

## 📁 Struktur Direktori

```text
gimbal-web/
├── app.py                     # Entrypoint & routing Flask (Dual-Layer HTMX Engine)
├── models.py                  # Model SQLAlchemy SQLite & generator auto R-nn-YY
├── seed.py                    # Seeder data awal admin, anggota, iuran, dokumen
├── test_app.py                # 7 Unit test suite pengujian otomatis
├── requirements.txt           # Dependensi Python
├── CONVERSATION_HISTORY.md    # Rekam jejak seluruh percakapan & referensi arsitektur
├── instance/
│   └── gimbal.db              # Database SQLite
├── uploads/
│   ├── proofs/                # File upload bukti transfer iuran
│   ├── docs/                  # File upload dokumen PDF internal
│   └── gallery/               # File upload foto kurasi ekspedisi
├── templates/
│   ├── index.html             # LAYER 1: Outer Shell Frame
│   ├── shell.html             # LAYER 2: Application Shell (Header, Nav, Footer)
│   ├── landing.html           # Halaman Publik Utama KPAB GIMBAL
│   ├── verify_kta.html        # Halaman Publik Validasi QR KTA
│   ├── member/
│   │   └── member_pages.html  # Macros Halaman Anggota (Dashboard, KTA, Iuran, Dokumen, Profil)
│   ├── admin/
│   │   └── admin_pages.html   # Macros Halaman Admin (Approvals, Members, Dues, CRUD Dokumen, Galeri)
│   └── components/
│       └── modals.html        # Modals HTMX (Upload bukti bayar, Buat iuran, Dokumen, Pin Galeri)
└── static/
    ├── css/theme.css          # Desain sistem & variabel lebar konten / monotone
    ├── js/theme-config.js     # Variabel konfigurasi terpusat (lebar & preset warna)
    ├── vendor/                # HTMX, Tailwind, Alpine.js lokal
    ├── pics/cartoon/          # 10 Ilustrasi kartun petualang & avatar 3D pengurus
    └── docs/                  # File sampel PDF resmi
```

