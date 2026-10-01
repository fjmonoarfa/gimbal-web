# KPAB GIMBAL Web Application & Ecosystem
**Generasi Indonesia Menyatu Bersama Alam**

Aplikasi web modern dan portal terintegrasi organisasi petualang alam bebas **KPAB GIMBAL**, dibangun dengan arsitektur **Python Flask + Modular Blueprints + Full Dual-Layer HTMX + Tailwind CSS + Alpine.js**, serta mendukung database **SQLite** (lokal) dan **MySQL / PostgreSQL** (produksi).

---

## 🌟 Fitur Utama & Ekosistem Aplikasi

### 1. Arsitektur Dual-Layer HTMX (Modular Blueprints)
* **Layer 1 (`templates/index.html`)**: Outer Shell Frame dengan skeleton loader, Tailwind CSS, Alpine.js, HTMX lokal, FontAwesome, dan Google Fonts.
* **Layer 2 (`templates/shell.html`)**: Application Frame bernuansa outdoor dengan Header navigasi responsif, Google-Style Account Hub, dropdown Pengaturan Admin, wadah modal terpusat (`#modal-container`), dan kontainer utama `#main-content`.
* **Modular Flask Architecture**:
  * `app.py`: Inisialisasi aplikasi, Google OAuth 2.0 SSO, Jinja context processors, dan public landing handler.
  * `admin_pages.py` (`admin_bp`): Dashboard admin, persetujuan anggota (approval), verifikasi iuran kas, manajemen dokumen, agenda ekspedisi, kurasi galeri, master jabatan/struktur organisasi, serta pengaturan sistem.
  * `members_page.py` (`members_bp`): Portal anggota, linimasa petualangan (feed), KTA digital interaktif, riwayat kas & iuran, live chat room & private message, serta pembaruan profil & kontak darurat.
  * `web_api.py` (`api_bp`): Gateway pembayaran Midtrans (Snap Token & Webhook Notification), sinkronisasi langganan Google Pay, Gimbal Maps GIS API, dan realtime polling chat.
  * `helpers.py`: Route guards (`login_required`, `admin_required`, `check_member_access`) dan dual-layer rendering engine.
  * `cloudflare_email.py`: Sinkronisasi otomatis alias email resmi organisasi `@gimbal.my.id` melalui Cloudflare Email Routing API.
* **Single Page Application (SPA) Feel**: Navigasi instan tanpa reload halaman penuh (`hx-push-url="true"`), transisi mulus, dan performa tinggi.

---

### 2. Autentikasi Google OAuth 2.0 & Alur Pendaftaran Berjenjang (Gated Onboarding)
* **Google Identity Services & OAuth 2.0**: Pendaftaran dan login 1-klik terintegrasi untuk domain produksi `https://www.gimbal.my.id` dan localhost.
* **Alur Pendaftaran Berjenjang**:
  1. **Google Sign-In**: Pengguna mendaftar dengan akun Google resmi.
  2. **Kelengkapan Profil Wajib (`/member/complete-profile`)**: Pengisian data wajib mencakup nomor WhatsApp, tempat & tanggal lahir, golongan darah, alamat domisili, riwayat medis/alergi, dan kontak darurat (*Safety First*).
  3. **Pembayaran Iuran Pokok Registrasi (`/member/onboarding-status`)**: Pilihan metode pembayaran via Transfer Bank Manual (dengan bukti transfer & live preview) atau QRIS.
  4. **Persetujuan Pengurus (Admin Approval)**: Admin memverifikasi data dan bukti pembayaran.
  5. **Aktivasi Akun & Penerbitan NRA**: Setelah disetujui, akun aktif dan nomor keanggotaan diterbitkan secara otomatis. Calon anggota berstatus *pending* dipagari oleh *route guard* dan tidak dapat mengakses linimasa atau fitur anggota sebelum verifikasi selesai.

---

### 3. Logika Penomoran Anggota Resmi Atomik (`R-nn-YY`)
* **Format**: `R-nn-YY` (contoh: `R-01-26`, `R-02-26`).
* **Aturan Atomik**:
  * `YY` = 2 digit tahun saat admin menyetujui pendaftaran (misal tahun 2026 -> `26`).
  * `nn` = nomor urut persetujuan admin pada tahun tersebut (dimulai dari `01`).
  * **Reset tahunan**: Nomor urut otomatis kembali ke `01` pada pergantian tahun baru kalender.

---

### 4. KTA Digital & QR Code Validasi Lapangan
* Desain kartu digital eksklusif petualang GIMBAL (Nama, NRA `R-nn-YY`, Golongan Darah, Foto Profil, Status Keanggotaan, dan Tanggal Terbit).
* **QR Code Dinamis**: Terhubung ke halaman verifikasi publik `/verify-kta/<nra>` untuk pembuktian keabsahan identitas di pos perizinan pendakian (Simaksi), posko SAR, atau kegiatan lapangan.

---

### 5. Widget Obrolan Terapung (Bottom Float Chat) & Basecamp Live Chat
* **Dual Chat System**:
  * **Basecamp Public Room**: Ruang obrolan umum antar seluruh petualang aktif.
  * **Private Direct Message (DM)**: Percakapan privat antar anggota secara personal.
* **Bottom Float Widget (`templates/components/float_chat.html`)**:
  * Widget terapung di pojok kanan bawah dengan mesin ganda yang deterministik (**Alpine.js + Vanilla JS fallback**).
  * Dilengkapi tombol minimize, maximize, pemilih kontak DM, dan counter unread.
  * **Otomatis Tersembunyi untuk Guest**: Hanya aktif dan muncul setelah anggota masuk (login), menjaga landing page publik tetap bersih.

---

### 6. Manajemen Kas, Iuran Multi-Channel & Ekosistem Gimbal Maps
* **Multi-Channel Kas & Iuran**:
  * **Transfer Bank Manual**: Verifikasi slip transfer oleh bendahara dengan live modal preview.
  * **Midtrans Payment Gateway**: Pembayaran instan otomatis menggunakan Snap Token, QRIS, dan Bank Virtual Account.
  * **Google Pay / In-App Subscription**: Sinkronisasi otomatis langganan dari aplikasi mobile lapangan **gimbal-maps** (`/api/v1/maps/subscription/google-pay`).
* **Org Member Featured Access**: Status lunas iuran membuka akses penuh ke repositori peta offline, impor vektor KML/GeoJSON, rute navigasi tak terbatas, dan berbagi track GPX di aplikasi `gimbal-maps`.
* **Fitur Sakelar Iuran (Enable/Disable Dues)**: Pengurus dapat mengaktifkan atau menonaktifkan penagihan iuran sewaktu-waktu dari menu Pengaturan Admin.

---

### 7. Dewan Pengurus Inti & Divisi Operasional Dinamis di Landing Page
* **Dewan Pengurus Inti**: Terhubung langsung ke tabel master `positions` dan penetapan anggota aktif, menampilkan struktur amanah pengurus, foto, dan NRA di landing page.
* **Divisi Operasional Lapangan**: Menampilkan profil divisi petualangan resmi secara dinamis:
  * 🏔️ **Gunung Hutan** (*Mountaineering*)
  * 🧗 **Panjat Tebing** (*Rock Climbing*)
  * 🦇 **Susur Gua** (*Speleology / Caving*)
  * 🚣 **Arung Jeram** (*River Running / Rafting*)
  * 🌿 **Konservasi & LH** (*Ecology, Conservation & SAR*)
* **Footer Terintegrasi**: Alamat sekretariat basecamp, nomor telepon/WhatsApp, dan email resmi terhubung ke data `SystemSetting` yang dapat diubah dari dashboard admin.

---

### 8. Linimasa Petualangan (Adventure Community Feed) & Galeri Ekspedisi
* **Linimasa Komunitas**: Berbagi cerita perjalanan, catatan rute, foto lapangan, interaksi *likes*, dan komentar antar anggota.
* **Galeri Ekspedisi (Pin-Down System)**:
  * Pengurus mengunggah dokumentasi kegiatan dan menghubungkannya dengan agenda ekspedisi.
  * Tombol cepat **Pin-down**: Menampilkan foto kurasi terbaik langsung pada etalase galeri di landing page publik.

---

### 9. Konfigurasi Terpusat Tema Monotone & Pure Bright Mode
* **Konfigurasi 1 Variabel**:
  * Lebar Konten: `GIMBAL_SITE_WIDTH = '85%';` di `static/js/theme-config.js` dan `static/css/theme.css`.
  * Tema Monotone Tahunan: `GIMBAL_THEME_COLOR = 'orange';` dengan 6 pilihan preset warna (`orange`, `emerald`, `blue`, `amber`, `rose`, `teal`).
* **Pure Bright Mode Permanen**: Menghadirkan antarmuka bertaraf profesional, bersih, tajam, dan kontras tinggi tanpa distraksi dark mode.

---

## 📁 Struktur Direktori Proyek

```text
gimbal-web/
├── app.py                     # Core Flask, Google OAuth 2.0 SSO, public landing & config
├── admin_pages.py             # Blueprint Admin: Approval, Kas, Anggota, Ekspedisi, Galeri, Jabatan
├── members_page.py            # Blueprint Member: Linimasa Feed, KTA, Iuran, Chat DM, Profil
├── web_api.py                 # Blueprint API: Midtrans Gateway, Gimbal Maps API, Live Chat Polling
├── helpers.py                 # Decorators, route guards, and dual-layer HTMX renderers
├── models.py                  # SQLAlchemy Models (User, Dues, Activity, Gallery, Position, Chat, dll.)
├── cloudflare_email.py        # Integrasi Cloudflare Email Routing API (@gimbal.my.id)
├── seed.py                    # Seeder data awal & migrasi otomatis kolom skema
├── test_app.py                # Suite pengujian otomatis (21 automated unit tests)
├── requirements.txt           # Dependensi Python
├── CONVERSATION_HISTORY.md    # Rekam jejak seluruh keputusan arsitektur & sesi pengembangan
├── deploy_remote.py           # Skrip otomatisasi deployment SSH/SCP ke remote Ubuntu server
├── instance/
│   └── gimbal.db              # Database SQLite (lingkungan development)
├── uploads/                   # Folder media upload (terlindungi .gitignore)
│   ├── proofs/                # Bukti transfer pembayaran iuran
│   ├── docs/                  # Berkas dokumen resmi / SOP PDF
│   ├── gallery/               # Foto galeri ekspedisi kurasi
│   ├── posts/                 # Foto lampiran postingan linimasa
│   ├── maps/                  # Berkas GPX / track rute navigasi
│   └── avatars/               # Foto profil anggota
├── templates/
│   ├── index.html             # LAYER 1: Outer Shell Frame & Fallback Loader
│   ├── shell.html             # LAYER 2: Application Shell (Header, Nav, Modal Container)
│   ├── landing.html           # Landing page publik (Hero, Filosofi, Divisi, Galeri, Pengurus)
│   ├── verify_kta.html        # Halaman publik verifikasi pemindaian QR KTA
│   ├── admin/
│   │   └── admin_pages.html   # Macro views portal admin
│   ├── member/
│   │   └── member_pages.html  # Macro views portal anggota
│   └── components/
│       ├── float_chat.html    # Widget floating chat (Basecamp Public & Private DM)
│       └── modals.html        # Kumpulan modal dialog responsif HTMX
└── static/
    ├── css/theme.css          # Sistem tema monotone, kontainer lebar situs & animasi
    ├── js/theme-config.js     # Variabel konfigurasi terpusat (lebar & preset warna tema)
    ├── vendor/                # HTMX, Tailwind CSS, Alpine.js (lokal)
    ├── pics/cartoon/          # Ilustrasi kartun petualang & avatar pengurus 3D
    └── docs/                  # Contoh dokumen SOP & modul materi
```

---

## 🚀 Panduan Menjalankan Aplikasi

### 1. Persiapan Lingkungan & Dependensi
Pastikan Python 3.10+ telah terpasang. Buat dan aktifkan virtual environment:
```bash
python -m venv venv
# Di Windows:
venv\Scripts\activate
# Di Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Inisialisasi Database (Development - SQLite)
Jalankan seeder untuk membuat tabel dan data awal akun pengurus, anggota, master jabatan, dan pengaturan:
```bash
python seed.py
```

### 3. Menjalankan Server Lokal
```bash
python app.py
```
Aplikasi akan aktif di: `http://localhost:5000` (atau port sesuai variabel `PORT`).

### 4. Menjalankan Automated Unit Tests
Seluruh 21 suite pengujian otomatis mencakup OAuth, alur onboarding, KTA QR, galeri, izin admin, dan API:
```bash
python test_app.py
```

---

## 🌐 Deployment Produksi (Remote Server)

Untuk mendeploy ke server produksi (misal Ubuntu Server dengan Gunicorn, Nginx, dan MySQL/PostgreSQL):
1. Konfigurasikan target server pada [deploy_remote.py](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/deploy_remote.py).
2. Jalankan skrip deployment:
   ```bash
   python deploy_remote.py
   ```
3. Skrip akan otomatis mengunggah seluruh berkas kode, aset static, template, menyinkronkan migrasi kolom database, dan me-restart service aplikasi di server.

---

## 🔒 Variabel Lingkungan (`.env`)

Contoh berkas konfigurasi `.env` pada lingkungan produksi:
```env
SECRET_KEY=kunci-rahasia-keamanan-gimbal-2026
PORT=8082
DATABASE_URL=mysql://gimbal-web:P4ssw0rd!@127.0.0.1/gimbal-web

# Google OAuth 2.0 Credentials
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://www.gimbal.my.id

# Midtrans Gateway (Opsional jika menggunakan payment gateway)
MIDTRANS_SERVER_KEY=SB-Mid-server-xxxxxx
MIDTRANS_CLIENT_KEY=SB-Mid-client-xxxxxx
MIDTRANS_IS_PRODUCTION=false

# Cloudflare Email Routing (Opsional untuk alias @gimbal.my.id)
CLOUDFLARE_API_TOKEN=your-cloudflare-api-token
CLOUDFLARE_ZONE_ID=your-zone-id
```

---

## 📜 Lisensi & Hak Cipta
Hak Cipta © 2026 **KPAB GIMBAL** (*Generasi Indonesia Menyatu Bersama Alam*). Seluruh hak dilindungi undang-undang.
