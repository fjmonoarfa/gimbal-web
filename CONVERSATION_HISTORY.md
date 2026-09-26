# Dokumentasi & Rekam Jejak Percakapan Pengembangan KPAB GIMBAL Web
**Generasi Indonesia Menyatu Bersama Alam**
*Dokumen ini menyimpan seluruh referensi instruksi, keputusan arsitektur, konfigurasi teknis, dan evolusi fitur selama sesi pengembangan.*

---

## 📋 Daftar Isi
1. [Kronologi Permintaan Pengguna (User Requests Timeline)](#1-kronologi-permintaan-pengguna)
2. [Arsitektur Sistem & Prinsip Desain](#2-arsitektur-sistem--prinsip-desain)
3. [Konfigurasi Terpusat 1 Variabel (Lebar & Monotone Tema)](#3-konfigurasi-terpusat-1-variabel)
4. [Sistem Keanggotaan & Aturan Penomoran Atomik R-nn-YY](#4-sistem-keanggotaan--aturan-penomoran-atomik-r-nn-yy)
5. [Modul Galeri Ekspedisi (Pin-Down System)](#5-modul-galeri-ekspedisi-pin-down-system)
6. [Katalog Aset Visual Cartoonized Landing Page](#6-katalog-aset-visual-cartoonized-landing-page)
7. [Daftar Rute Endpoint & Hak Akses](#7-daftar-rute-endpoint--hak-akses)
8. [Struktur Skema Database SQLite](#8-struktur-skema-database-sqlite)
9. [Automated Unit Test Suite](#9-automated-unit-test-suite)
10. [Riwayat Commit Git](#10-riwayat-commit-git)

---

## 1. Kronologi Permintaan Pengguna

| No | Instruksi Pengguna | Ringkasan Tindakan & Implementasi Teknis |
|:---|:---|:---|
| 1 | *“untuk validasi kta juga layout masig berantakan”* | Memperbaiki tampilan kartu KTA digital (gradient burnt-orange, QR code base64, status badge), dan merapikan halaman publik verifikasi `/verify-kta/<nra>`. |
| 2 | *“untuk layout landing page mungkin ada saran yang lebih propeg untuk sebuah website kelompok pencinta alam?”* | Menyusun rancangan arsitektur landing page standar organisasi pencinta alam dengan 9 section: Hero sinematik, Filosofi & Semboyan, 4 Divisi Petualang, Agenda Ekspedisi, Galeri, Piagam Kode Etik Pencinta Alam, Kepengurusan, dan Footer. |
| 3 | *“ok, sekarang buat ulang sesuai layout baru dan kontenn baru”* | Mengimplementasikan seluruh rancangan konten ke dalam `templates/landing.html`. |
| 4 | *“tema warna sesuai logo yaitu oranye”* | Menerapkan palet warna brand logo GIMBAL (HEX `#ea580c`, `#c2410c`, `#9a3412`) secara seragam. |
| 5 | *“buat monotone oranye untuk semua”* | Menyelaraskan seluruh elemen antarmuka (portal anggota, admin dashboard, modal, form, badge, tabel kas) ke dalam monotone oranye. |
| 6 | *“untuk lebar konten di landing dan dashboard buat supaya 85% dari lebar layar”* | Mengimplementasikan kontainer terpusat `.site-container` dengan lebar 85% untuk seluruh halaman. |
| 7 | *“section hero jangan buat 100% lebar”* | Membatasi kontainer teks, CTA, dan metrik di dalam hero section ke 85%. |
| 8 | *“lebar gambar di section hero 100% tetapi konten text sesuai 85%, dan buat 85% ini sekali seting di 1 variabel utama akan berlaku untuk semua halaman yang ada dalam web ini supaya mudah konfigurasinya, demikian juga untuk monotone warna oranye ada dalam 1 variabel utama, ada kemungkinan tiap tahun warna utama berubah”* | Membangun sistem tema terpusat: `static/css/theme.css` (`--site-content-width: 85%`) dan `static/js/theme-config.js` (`GIMBAL_SITE_WIDTH`, `GIMBAL_THEME_COLOR`) dengan 6 preset tema warna tahunan. |
| 9 | *“jika sudah, push ke github di https://github.com/fjmonoarfa/gimbal-web”* | Menginisialisasi repositori Git, membuat `.gitignore` yang aman (mengabaikan SQLite & cache), dan push commit ke remote GitHub `main`. |
| 10 | *“regenerate ulang image2 di landing page dengan style cartoonized”* | Menghasilkan 10 ilustrasi baru bergaya kartun petualang (Ghibli/anime landscape & 3D character avatars pengurus) menggunakan AI dan menghubungkannya ke template. |
| 11 | *“dimana crud atau pengaturan foto2 galery?”* | Menjelaskan struktur file foto fisik (`assets/pics/galeri/`), metadata JSON, tabel model `GalleryItem`, dan mengidentifikasi belum tersedianya modul CRUD di admin. |
| 12 | *“yaa, galeri adalah kumpulan pin-down dari foto2 dari semua ekspedisi”* | Mengembangkan modul CRUD lengkap Galeri Ekspedisi (`/admin/gallery`): integrasi relasi ke agenda ekspedisi, upload gambar fisik/URL, tombol cepat *Toggle Pin-down*, filter status, dan penyesuaian landing page. |
| 13 | *“simpan semua referensi percakapan”* | Membuat dokumentasi komprehensif `CONVERSATION_HISTORY.md`, memperbarui `README.md`, dan melakukan push ke repositori GitHub. |
| 14 | *“kenapa merubah bagian ini: --site-content-width: 70%; di theme.css tidak mempengaruhi lebar konten landing page?”* | Menjelaskan hierarki CSS di mana `theme-config.js` menimpa nilai via inline style DOM `root.style.setProperty`, dan mengarahkan pengaturan ke `GIMBAL_SITE_WIDTH`. |
| 15 | *“buat supaya ada dark dan bright mode untuk semua bagian, default mode bright dari 1 variabel utama”* | Mengimplementasikan sistem Dark & Bright Mode terintegrasi penuh yang dikontrol dari 1 variabel utama `GIMBAL_COLOR_MODE = 'bright'` di `theme-config.js`, Tailwind `darkMode: 'class'`, token CSS dinamis di `theme.css`, dan tombol toggle sun/moon di semua navigasi & halaman. |
| 16 | *“tob nav bar hilangkan tombol login masuk, cukup menggunakan tombol login dibagian footer, untuk tombol dark/bright buat ada di paling kanan top nav bar”* | Menghapus tombol login di navbar atas, memindahkan tombol toggle Dark/Bright mode ke posisi paling kanan navbar, serta memperkuat tombol login portal di bagian footer. |
| 17 | *“bagian section hero terlalu tinggi sehingga banyak ruang kosong, dan text masih ada yang tidak terbaca karena sama dengan latar warnanya”* | Mengompres padding & min-height hero section agar proporsional, serta memperbaiki kontras teks (warna putih-stone tegas, drop-shadow tajam, dan penyempurnaan gradient overlay) sehingga 100% terbaca jelas. |
| 18 | *“kenapa pergantian warna tema semua text masih tetap warna oranye?”* | Mengidentifikasi bahwa Tailwind CDN Play parser gagal meng-override palette default `orange` karena adanya key `rgb*` non-standar, lalu mengimplementasikan Dynamic CSS Theme Generator di `theme-config.js` yang secara otomatis menyuntikkan override instan untuk seluruh kelas `text-orange-*`, `bg-orange-*`, dan `border-orange-*` sesuai preset tahunan aktif (`rose`, `emerald`, `blue`, dsb). |
| 19 | *“bagian ini masi fix warna tidak sesuai tema (melampirkan screenshot section CTA & Footer)”* | Memperbaiki latar belakang section CTA (`.cta-theme-section`) dan Footer (`.footer-theme-bg`) yang sebelumnya menggunakan fallback warna oranye/cokelat tetap, mengintegrasikannya dengan injeksi CSS dinamis preset warna aktif di `theme-config.js` (dengan radial glow monotone aktif), mengubah seluruh tombol pendaftaran & login portal menggunakan `.btn-brand-primary` adaptif, menambahkan override otomatis untuk gradient stops Tailwind (`from-orange-*`, `to-orange-*`), serta menambahkan query string cache buster (`?v=20260926_3`) pada tag CSS & JS agar perubahan langsung aktif seketika di browser tanpa tersangkut cache lama. |
| 20 | *“untuk admin dash buat supaya menu di pane kiri”* | Mengubah arsitektur navigasi admin dari top header horizontal menjadi Left Pane Sidebar (`<aside>`) di sisi kiri halaman, merapikan top header admin agar tidak penuh sesak, mengintegrasikan 7 menu utama admin dengan badge penghitung verifikasi dinamis, menambahkan sinkronisasi status aktif otomatis via listener `htmx:afterSwap`, serta mengoptimalkan lebar responsif mobile via media query di `theme.css`. |
| 21 | *“perbaiki lagi: edit form galeri belum tersimpan di database, dan bagian agenda expedisi belum bisa diedit”* | (1) Memperbaiki form modal edit galeri yang gagal menyimpan perubahan karena pembersihan prematur elemen form DOM oleh atribut `onsubmit` sebelum serialisasi HTMX selesai, menggantinya dengan listener siklus hidup `hx-on::after-request`, serta memperkuat penanganan form di backend `admin_edit_gallery()`. (2) Mengembangkan fungsionalitas CRUD lengkap untuk Agenda Ekspedisi: endpoint modal edit (`/admin/activity/edit-modal/<id>`), endpoint simpan edit (`/admin/activity/edit/<id>`), endpoint hapus (`/admin/activity/delete/<id>`), endpoint toggle status pendaftaran (`/admin/activity/toggle-status/<id>`), modal antarmuka `edit_activity`, tombol aksi Edit/Status/Hapus pada kartu ekspedisi di `admin_pages.html`, serta pengujian otomatis di `test_app.py`. |

---

## 2. Arsitektur Sistem & Prinsip Desain

Aplikasi mengadopsi pola arsitektur **Dual-Layer Rendering**:
1. **Layer 1 (`templates/index.html`)**: Outer frame yang dimuat saat browser melakukan request langsung (Direct GET). Menyediakan skeleton loader, memuat dependensi vendor lokal (HTMX, Alpine.js, Tailwind), dan memanggil Layer 2 via `hx-get="/app-shell"`.
2. **Layer 2 (`templates/shell.html`)**: Application Shell yang membungkus Header, Navigasi Desktop & Mobile, Toast Alert, Modal Container (`#modal-container`), dan Wadah Konten Utama (`#main-content`).
3. **Partial Swaps (`templates/admin/admin_pages.html` & `templates/member/member_pages.html`)**: Berisi macro Jinja2 yang di-render secara modular ke dalam `#main-content` tanpa me-reload browser.

---

## 3. Konfigurasi Terpusat 1 Variabel

Konfigurasi tampilan dikendalikan secara sentral melalui dua file utama:

### A. Pengaturan Lebar Konten Seluruh Halaman
- **File CSS**: [`static/css/theme.css`](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/css/theme.css)
  ```css
  :root {
      --site-content-width: 85%; /* Cukup ubah angka ini untuk mengatur seluruh lebar web */
  }
  .site-container {
      width: var(--site-content-width);
      max-width: 1440px;
      margin-left: auto;
      margin-right: auto;
  }
  ```
- **File JS**: [`static/js/theme-config.js`](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/js/theme-config.js)
  ```javascript
  const GIMBAL_SITE_WIDTH = '85%';
  ```

### B. Pengaturan Warna Monotone Tahunan (1 Baris)
Untuk mengganti tema warna di tahun berikutnya, cukup ubah satu baris di [`static/js/theme-config.js`](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/js/theme-config.js):
```javascript
const GIMBAL_THEME_COLOR = 'orange'; 
// Pilihan preset bawaan: 'orange', 'emerald', 'blue', 'amber', 'rose', 'teal'
```
Preset warna yang tersedia:
- `'orange'` (Oranye Resmi GIMBAL)
- `'emerald'` (Hijau Rimba / Konservasi Alam)
- `'blue'` (Biru Tirta / Ekspedisi Arung Jeram)
- `'amber'` (Kuning Emas Fajar)
- `'rose'` (Merah Karang / Panjat Tebing)
- `'teal'` (Toska Danau Vulkanik)

### C. Pengaturan Mode Tampilan Terang & Gelap (Bright & Dark Mode)
Sistem tampilan terang dan gelap dikendalikan secara sentral melalui 1 variabel utama di [`static/js/theme-config.js`](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/js/theme-config.js):
```javascript
const GIMBAL_COLOR_MODE = 'bright'; // Pilihan: 'bright' (default) atau 'dark'
```
- **Hierarki & Sinkronisasi**:
  - Mengonfigurasi `darkMode: 'class'` pada Tailwind CSS CDN.
  - Memberikan transisi warna halus (`transition: background-color 0.25s, color 0.25s`).
  - Menyediakan token warna CSS dinamis (`--color-bg-body`, `--color-bg-card`, `--color-border`) dan override komponen otomatis di [`static/css/theme.css`](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/css/theme.css) sehingga seluruh halaman (Landing, Portal Anggota, Admin, Modals, KTA Verification) langsung kompatibel tanpa merusak warna kontras.
  - Tombol toggle Sun/Moon (`.gimbal-theme-toggle`) interaktif tersedia di Header Desktop & Mobile pada Landing Page, Shell Portal Anggota/Admin, serta halaman Validasi KTA Publik.
  - Pilihan pengguna disimpan di `localStorage` dan tersinkronisasi otomatis saat perpindahan halaman HTMX (`htmx:afterSwap`).

---

## 4. Sistem Keanggotaan & Aturan Penomoran Atomik R-nn-YY

- **Format Resmi**: `R-nn-YY` (contoh: `R-01-26`, `R-02-26`, `R-03-26`).
- **Aturan Bisnis**:
  - `YY`: 2 digit tahun kalender persetujuan admin berjalan (misal tahun 2026 -> `26`).
  - `nn`: Nomor urut berurutan 2 digit (dimulai dari `01`).
  - **Reset Otomatis**: Urutan `nn` otomatis kembali ke `01` saat memasuki tahun baru.
  - **Atomisitas Transaksi**: Fungsi `generate_next_nra()` di [`models.py`](file:///g:/My%20Drive/priv_web_apps/gimbal-web/models.py) mengunci nilai urutan tertinggi pada tahun berjalan untuk mencegah duplikasi nomor anggota.
- **KTA Digital & Verifikasi QR**:
  - Anggota aktif memiliki KTA digital berlatar gradasi monotone outdoor.
  - Setiap KTA memiliki QR Code dinamis yang merujuk ke rute publik `/verify-kta/<nra>`.

---

## 5. Modul Galeri Ekspedisi (Pin-Down System)

Galeri dibangun dengan konsep **Pin-down dari seluruh agenda ekspedisi**:
- **Tabel Database**: `gallery_items`
  - Kolom: `id`, `title`, `caption`, `image_url`, `category`, `location`, `is_pinned`, `activity_id`, `created_at`.
  - Relasi ke `activities` (`db.ForeignKey('activities.id')`).
- **Fitur Admin (`/admin/gallery`)**:
  - Statistik foto: Total foto, foto yang di-pin ke depan, total ekspedisi.
  - Filter kurasi berdasarkan status (Semua / Hanya Pinned / Arsip) dan berdasarkan Agenda Ekspedisi.
  - Tombol cepat **Toggle Pin-down** instan via HTMX.
  - Modal **Pin-down Foto Baru**: Mendukung upload file lokal (disimpan di `uploads/gallery/`) atau input URL gambar.
  - Modal **Edit** dan tombol **Hapus** foto.
- **Tampilan Landing Page**:
  - Section `#galeri` menampilkan foto-foto yang memiliki atribut `is_pinned = True`.
  - Menampilkan badge nama ekspedisi, kategori divisi, pin lokasi, judul, dan caption cerita petualangan.

---

## 6. Katalog Aset Visual Cartoonized Landing Page

Seluruh gambar landing page menggunakan gaya ilustrasi petualang (Ghibli / anime landscape & 3D character avatars) yang tersimpan di [`static/pics/cartoon/`](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/pics/cartoon/):

1. **`hero.jpg`**: Pegunungan tropis berkabut saat matahari terbit (dipasang pada `.hero-overlay` 100% full-width).
2. **`tentang.jpg`**: Perkemahan malam hari di depan api unggun dengan tenda dome oranye.
3. **`divisi_mountaineer.jpg`**: Pendaki menyusuri jalur hutan tropis dengan carrier dan trekking pole.
4. **`divisi_climbing.jpg`**: Pemanjat tebing karst dengan harness, carabiner, dan tali karmantel oranye.
5. **`divisi_caving.jpg`**: Penelusur gua (speleologi) dengan helm berlampu di sungai bawah tanah karst.
6. **`divisi_conservation.jpg`**: Relawan konservasi menanam bibit pohon di tepi aliran hutan hujan.
7. **`avatar_ketua.jpg`**: 3D Character: Pendaki wanita energik berbandana oranye (Ketua Umum).
8. **`avatar_sekjen.jpg`**: 3D Character: Petualang ramah berkacamata dan topi rimba (Sekretaris Jenderal).
9. **`avatar_bendahara.jpg`**: 3D Character: Petualang wanita berhijab dengan rompi outdoor oranye (Bendahara Umum).
10. **`avatar_kadiv.jpg`**: 3D Character: Pemandu lapangan tangguh dengan topi rimba bush hat (Kadiv Operasional Rimba).

---

## 7. Daftar Rute Endpoint & Hak Akses

### A. Rute Publik
- `GET /`: Landing page utama dengan 9 section, galeri ekspedisi pinned, agenda terbuka, dan form kontak.
- `GET /verify-kta/<nra>`: Validasi keabsahan nomor KTA digital resmi hasil scan QR code lapangan.
- `GET /app-shell`: Endpoint Layer 2 untuk memuat shell antarmuka.
- `GET /assets/<filename>` & `GET /uploads/<filename>`: Penyaji file statis, dokumen, dan foto galeri.

### B. Autentikasi & Dev Switcher
- `GET /auth/google-login`: Handler login Google OAuth 2.0 (fallback otomatis ke dev selector).
- `GET /auth/switch-role`: Pengganti peran instan (Admin, Anggota Aktif, Calon Pendaftar).
- `GET /auth/logout`: Membersihkan session dan kembali ke beranda.

### C. Portal Anggota (`/member/*`)
- `GET /member/dashboard`: Ringkasan profil, status keanggotaan, iuran, dan agenda trip.
- `GET /member/kta`: Kartu Tanda Anggota Digital & QR Code validator.
- `GET /member/iuran`: Daftar tagihan iuran aktif dan riwayat pembayaran pribadi.
- `POST /member/iuran/pay/<id>`: Unggah bukti transfer pembayaran iuran.
- `GET /member/documents`: Daftar dokumen organisasi yang dapat diunduh anggota.
- `POST /member/activity/join/<id>`: Pendaftaran peserta ekspedisi.

### D. Panel Pengurus Admin (`/admin/*`)
- `GET /admin/dashboard`: Statistik anggota pending, aktif, saldo kas, dan transfer menunggu cek.
- `GET /admin/approvals`: Antrean verifikasi calon anggota dan penerbitan nomor atomik `R-nn-YY`.
- `POST /admin/member/approve/<id>` & `POST /admin/member/reject/<id>`: Persetujuan / penolakan anggota.
- `GET /admin/members` & `GET /admin/members/export-csv`: Data master anggota dan ekspor CSV.
- `GET /admin/dues`: Master iuran dan verifikasi slip transfer.
- `GET /admin/documents`: Manajemen dokumen internal organisasi (AD/ART, SOP, Modul).
- `GET /admin/activities`: Buka pendaftaran agenda ekspedisi & pantau kuota rombongan.
- `GET /admin/gallery`: **Pusat kurasi galeri ekspedisi pin-down**.
- `GET /admin/gallery/create-modal`: Modal tambah foto ekspedisi.
- `POST /admin/gallery/create`: Simpan foto baru (file upload / URL).
- `POST /admin/gallery/toggle-pin/<id>`: Toggle status tampil di landing page.
- `GET /admin/gallery/edit-modal/<id>` & `POST /admin/gallery/edit/<id>`: Edit metadata foto.
- `POST /admin/gallery/delete/<id>`: Hapus foto dari galeri.

---

## 8. Struktur Skema Database SQLite

File database: `instance/gimbal.db` (dikelola melalui SQLAlchemy di [`models.py`](file:///g:/My%20Drive/priv_web_apps/gimbal-web/models.py)):

```text
+-------------------+       +---------------------+
|       users       |       |     activities      |
+-------------------+       +---------------------+
| id (PK)           |       | id (PK)             |
| nra (Unique)      |       | title               |
| nra_year          |       | location            |
| nra_sequence      |       | activity_date       |
| name, email, role |       | difficulty, quota   |
| status            |       | is_open             |
+-------------------+       +---------------------+
          │                            │
          ▼                            ▼
+-------------------+       +---------------------+
|   dues_payments   |       |    gallery_items    |
+-------------------+       +---------------------+
| id (PK)           |       | id (PK)             |
| dues_id (FK)      |       | title, caption      |
| user_id (FK)      |       | image_url, category |
| amount_paid       |       | location            |
| proof_image       |       | is_pinned (Boolean) |
| status            |       | activity_id (FK)    |
+-------------------+       +---------------------+
```

---

## 9. Automated Unit Test Suite

File pengujian: [`test_app.py`](file:///g:/My%20Drive/priv_web_apps/gimbal-web/test_app.py) mencakup 7 unit test otomatis:
1. `test_01_landing_page`: Memastikan beranda publik responsif HTTP 200 dengan konten lengkap.
2. `test_02_verify_kta`: Memastikan validasi publik KTA digital berjalan akurat.
3. `test_03_dual_layer_htmx_architecture`: Memverifikasi pemisahan Layer 1 outer shell vs Layer 2 HTMX fragment.
4. `test_04_atomic_nra_assignment`: Memvalidasi logika penomoran atomik `R-nn-YY` (contoh: penerbitan `R-03-26`).
5. `test_05_kta_digital_page`: Memvalidasi render KTA digital dan pembuatan QR code validasi.
6. `test_06_document_crud`: Memvalidasi listing dan pengelolaan dokumen resmi.
7. `test_07_gallery_crud_and_pindown`: Memvalidasi siklus hidup kurasi foto (tambah, toggle pin, edit, filter, hapus).

---

## 10. Riwayat Commit Git

- **Repository**: [https://github.com/fjmonoarfa/gimbal-web](https://github.com/fjmonoarfa/gimbal-web)
- **Branch**: `main`
- **Daftar Commit Utama**:
  1. `028dad6`: *“feat: inisialisasi aplikasi web KPAB GIMBAL dengan arsitektur Dual-Layer HTMX, KTA digital R-nn-YY, dan tema terpusat”*
  2. `520c1b2`: *“feat: perbarui visual landing page dengan ilustrasi cartoonized adventure dan pengurus 3D”*
  3. `5531b0a`: *“feat: tambahkan modul CRUD Galeri Ekspedisi dengan fitur pin-down kurasi foto landing page”*
  4. `bcf7a75`: *“feat: hadirkan Google-style Account Hub pada avatar profil anggota dan redesign total portal login stylish simpel monotone”*

---

## 11. Pembaruan Fitur: Google-Style Profile Hub & Stylish Monotone Login (Provinsi Gorontalo)

### A. Pusat Profil Anggota Google-Style (`modal_type == 'profile_hub'`)
- **Pembersihan Navigasi Utama**: Menu navigasi atas untuk anggota kini bersih dan berfokus pada layanan organisasi (`Beranda Anggota`, `KTA Digital`, `Iuran Saya`, `Arsip Dokumen`), tanpa tautan standalone *"Profil & Medis"* yang membebani navigasi.
- **Icon Profil Avatar (Top-Right)**:
  - Diklik menampilkan Google-style account dropdown dengan foto avatar, nama, email, NRA chip, dan tombol utama **"Kelola Profil & Akun"**.
  - Menyediakan shortcut langsung ke tab spesifik:
    1. 👤 **Biodata & Pribadi**: Nama lengkap, WhatsApp, Tempat & Tanggal Lahir, Alamat Domisili Provinsi Gorontalo.
    2. 🏥 **Riwayat Medis & Kontak Darurat (Safety Crucial)**: Golongan darah (A, B, AB, O), riwayat penyakit / alergi / cedera lapangan, nama keluarga kontak darurat, hubungan, dan nomor telepon 24 jam.
    3. 🔒 **Keamanan & Sandi**: Indikator status Google SSO, form ubah kata sandi / PIN untuk login manual.
    4. 🎨 **Tampilan & Preferensi**: Mode kontras Terang / Gelap (Bright / Dark Mode) dan info afiliasi basecamp Gorontalo.
- **Reaktivitas HTMX**: Form profil di-submit via HTMX ke `/member/profile-modal/update`, menyimpan data langsung ke SQLite tanpa reload halaman dan menampilkan badge konfirmasi sukses.

### B. Redesign Total Halaman & Modal Login: Stylish Simpel Monotone
- **Halaman Login Penuh (`/login`) & Popup Modal (`#auth-modal`)**:
  - Tampilan modern, minimalis, dan elegan dengan monotone glassmorphism card.
  - Tab 1: **1-Klik Cepat (Simulasi Peran)** dengan kartu interaktif untuk *Pengurus Admin*, *Anggota Aktif*, dan *Calon Anggota Pending*.
  - Tab 2: **Akun Google (OAuth Resmi)** dengan tombol Google SSO.
  - Tab 3: **Email & Sandi Manual** bagi pendaftar atau anggota yang menggunakan password.
  - Tombol switcher mode gelap/terang terintegrasi langsung di navbar login.

### C. Penyesuaian Identitas Wilayah Organisasi ke Provinsi Gorontalo
- Seluruh referensi basecamp pusat, kesekretariatan, domisili anggota, dan lokasi ekspedisi telah diselaraskan ke **Provinsi Gorontalo** (Kota Gorontalo, Kabupaten Gorontalo/Limboto).

