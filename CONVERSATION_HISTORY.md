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
| 22 | *“setelah hosting di 10.75.0.51 (ubuntu_) hang saat login sebagai admin”* | Investigasi komprehensif log Gunicorn & remote Ubuntu: (1) Mengidentifikasi penyebab utama hang di mana berkas vendor `static/vendor/htmx/htmx.min.js` belum ter-upload di remote server (status 404), menyebabkan HTMX loader di Layer 1 (`templates/index.html`) tidak dapat mentrigger request HTMX swap ke `/admin/dashboard`, sehingga layar terkunci permanen pada animasi skeleton *“Memuat portal petualang...”*. (2) Mengunggah berkas vendor lokal yang hilang (`htmx.min.js`, `tailwind.js`, dan dokumen SOP), serta menambahkan auto-fallback CDN + safety-net timeout timer di `templates/index.html` dan `templates/login.html` agar tidak terjadi hang tak terduga. (3) Menambahkan `load_dotenv` di [app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/app.py) dan membuat konfigurasi `/root/gimbal-web/.env` terpusat agar server otomatis tersambung ke MySQL baik dijalankan via Systemd maupun terminal manual. (4) Memperbarui [deploy_remote.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/deploy_remote.py) agar otomatis men-sinkronisasi seluruh berkas `static/` dan `assets/`. (5) Menutup proses manual rogue, merestart `gimbal.service`, dan memverifikasi end-to-end status login admin sukses 200 OK. |
| 23 | *“masih bermasalah klik menu di user profile belum bisa.... sehingga tidak bisa logout”* | (1) Mengidentifikasi bahwa saat HTMX me-load `shell.html` secara dinamis ke `#app-shell`, instance Alpine.js tidak otomatis menginisialisasi directive `x-data` dan `@click` pada DOM baru karena belum adanya pemanggilan `Alpine.initTree()` pada event `htmx:load` dan `htmx:afterSwap`, ditambah atribut `x-cloak` dengan styling `display: none !important` yang membuat dropdown profil terkunci permanen. (2) Menghilangkan duplikasi script loader Alpine yang sebelumnya dipicu oleh evaluasi inline prematur `document.write`, menggantinya dengan fallback bersih `onerror`. (3) Mengintegrasikan listener siklus hidup `htmx:load` dan `htmx:afterSwap` dengan `Alpine.initTree()`. (4) Membangun handler vanilla JS mandiri (`window.toggleUserProfileMenu` & `window.toggleMobileMenu`) dengan dismiss klik luar dokumen sehingga menu profil dan mobile menu dapat dibuka/tutup dengan andal baik menggunakan Alpine maupun JavaScript murni. (5) Menyediakan tombol logout langsung 1-klik di 4 titik strategis: Top Nav Action Bar (header kanan), menu User Profile Hub, Mobile Dropdown, serta Admin Left Sidebar (Pane Kiri) untuk kenyamanan pengguna. |
| 24 | *“di dash anggota, top menu pindahkan semuanya ke sub menu di user name per kelompok”* | Mengorganisasi ulang navigasi dashboard anggota: (1) Membersihkan deretan link horizontal top menu di header anggota dan menggantinya dengan badge elegan *“Portal Anggota Resmi GIMBAL”* yang ringkas. (2) Memindahkan seluruh menu anggota ke dalam Google-Style Account Hub Dropdown di user name dengan sistem pengelompokan (kategorisasi) yang rapi dan terstruktur: **Kelompok 1: Kartu Identitas & Status Anggota** (Avatar, Nama, Email, NRA, Badge, Tombol Pusat Akun), **Kelompok 2: Layanan Anggota** (Beranda Petualang, KTA Digital Resmi, Iuran & Kas Saya, Arsip Dokumen & SOP), **Kelompok 3: Data Pribadi & Keamanan** (Shortcut langsung tab Biodata, Riwayat Medis/Darurat, Keamanan/Sandi), dan **Kelompok 4: Pengaturan & Sesi** (Simulasi Dev Mode, Logout). (3) Menambahkan handler auto-close `window.closeUserProfileMenu()` agar dropdown tertutup halus saat item menu diklik. (4) Menyelaraskan struktur kelompok menu yang sama pada navigasi mobile dan mendeploy pembaruan ke server `10.75.0.51`. |
| 25 | *“modifikasi ulang aplikasi web supaya semua template tidak ada mode dark atau bright, defaultkan bright mode saja tanpa ada switch atau seing/config dark mode lagi, lalu deploy ulang ke server”* | Menghapus seluruh sistem konfigurasi dan toggle switch mode gelap/terang di semua layer antarmuka: (1) Menghapus variabel `GIMBAL_COLOR_MODE`, menghapus injeksi dark CSS, dan mengunci fungsi `enforceBrightMode()` di `static/js/theme-config.js`. (2) Menghapus seluruh override CSS `html.dark` dan switch styling di `static/css/theme.css`. (3) Membersihkan tombol switch mode dari `landing.html`, `login.html`, `shell.html`, `verify_kta.html`, `modals.html`, dan `index.html`. (4) Menghapus kelas `dark:` yang tersisa agar tampilan 100% konsisten dalam bright mode yang bersih dan elegan. (5) Menjalankan test suite dan redeploy ke remote server. |
| 26 | *“tambahkan fitur daftar/login dengan google, kode oauth google ada di file client_secret_*.json, untuk link htps://www.gimbal.my.id”* | Mengimplementasikan sistem integrasi Google OAuth 2.0 untuk pendaftaran anggota baru dan login pengguna resmi: (1) Mengambil konfigurasi dari file `client_secret_*.json` dengan fallback environment variables untuk Client ID (`GOOGLE_CLIENT_ID`), Client Secret (`GOOGLE_CLIENT_SECRET`), dan Redirect URI (`https://www.gimbal.my.id`). (2) Membangun endpoint `/auth/google-login` yang mengarahkan user ke Google Accounts dengan state token pengaman. (3) Menangani callback authorization code baik langsung di root `@app.route('/')` (sesuai redirect_uris Google Console `https://www.gimbal.my.id`) maupun di `/auth/google/callback`. (4) Menambahkan fungsi `process_google_oauth` dan `login_or_register_google_user` yang otomatis membuat akun calon anggota berstatus `pending` bagi pendaftar baru, atau menyinkronkan avatar/google_id dan login langsung bagi anggota existing. (5) Menambahkan endpoint `/auth/google/credential` untuk dukungan Google Identity Services (GIS). (6) Memperbarui `templates/login.html` dan `templates/landing.html` dengan tombol "Daftar / Masuk dengan Google" yang mencolok di navbar, hero, dan modal. (7) Menambahkan `test_13_google_oauth_flow` ke `test_app.py` (100% pass) dan menyinkronkan file ke server remote. |
| 27 | *“untuk pendaftaran dengan google, buat supaya wajib mengisikan informasi wajib untuk keanggotaan, dan harus menunggu aproval dari admin stelah melakukan pembayaran/iuran keanggotaan lunas maka berhak untuk masuk ke linimasa/dashboard anggota dan menjadi anggota aktif”* | Mengimplementasikan alur pendaftaran berjenjang (Gated Onboarding & Dues Payment): (1) Menambahkan properti `is_profile_complete`, `latest_dues_payment`, dan `is_dues_paid` pada model `User` di `models.py`. (2) Membangun halaman formulir wajib kelengkapan profil `/member/complete-profile` (`templates/complete_profile.html`) mencakup nomor WhatsApp, tempat & tanggal lahir, golongan darah, alamat domisili, riwayat medis/alergi, dan kontak darurat. (3) Membangun halaman pemantau status pendaftaran `/member/onboarding-status` (`templates/onboarding_status.html`) dengan stepper 4 tahap dan form upload bukti transfer iuran pokok registrasi (`/member/onboarding/pay`). (4) Memasang route guard `check_member_access(user)` di dashboard, timeline, KTA digital, dan chat obrolan sehingga calon anggota berstatus pending atau belum melengkapi profil dilarang masuk ke linimasa sebelum disetujui pengurus. (5) Menghubungkan alur approval admin `/admin/member/approve/<id>` sehingga saat admin menyetujui calon anggota, status pengguna berubah menjadi `active`, diterbitkan nomor registrasi anggota (NRA format `R-nn-YY`), dan pembayaran iuran pending otomatis disetujui (`approved`). (6) Menambahkan penampil status iuran calon anggota pada antrean verifikasi admin di `admin_pages.html`. (7) Menguji skenario siklus hidup lengkap pendaftaran di `test_app.py` (13/13 tes 100% lulus) dan deploy ke remote server. |
| 28 | *“untuk nominal seharusnya bisa di atur dari menu admin, tetapkan 15000 dulu perbulan untuk demo, juga untuk login test sebelumnya hilangkan, buat untuk superadmin adalah fitra dengan password P4ssw0rd!?!, dan tambahkan di menu pengaturan saat admin login ada crud untuk admin web serta crud/manajemen untuk anggota”* | Mengimplementasikan konfigurasi nominal iuran dinamis (default Rp 15.000 / bulan), menghapus dev switcher/bypass login, membuat akun superadmin `fitra` berpassword `P4ssw0rd!?!`, serta menambahkan tab Pengaturan & Akses mencakup CRUD Admin Web (dengan proteksi superadmin), CRUD Member (biodata, NRA, status, reset password), pengaturan tarif kas, dan audit trail log. |
| 29 | *“kita pakai gateway midtrans”* | Mengintegrasikan payment gateway Midtrans Snap & Webhook Notification untuk pembayaran iuran registrasi keanggotaan (QRIS & Bank VA) lengkap dengan simulasi fallback sandbox dan pembaruan otomatis status transaksi di database. |
| 30 | *“coba pisahkan dari app.py route2 untuk admin ke admin_pages.py dan route2 untuk member ke members_page.py, di app.py hanyalah konfigurasi utama dan untuk payment gateway serta api2 lainnya”* | Melakukan refactoring modular: mengekstrak route admin ke Blueprint `admin_bp` di `admin_pages.py`, route member ke Blueprint `members_bp` di `members_page.py`, fungsi utilitas/dekorator/render ke `helpers.py`, dan merampingkan `app.py` hanya untuk inisialisasi app, db, Google OAuth, Midtrans gateway callback, serta registrasi blueprint. |
| 31 | *“modifikasi tampilan admin dash, buat supaya menu2 admin ada di menu utama 'Pengaturan' disebelah kiri menu user paling kanan atas... lalu deploy ulang ke server”* | Memodifikasi tata letak navigasi admin: (1) Menghapus sidebar kiri pane ganda admin dari `templates/shell.html` sehingga konten dashboard admin kini tampil penuh (full-width container). (2) Menambahkan dropdown menu "Pengaturan" (icon gear + badge pending verifikasi) di header atas, tepat di sebelah kiri tombol profil user. Dropdown memuat seluruh 9 menu admin (Dashboard, Verifikasi, Data Anggota, Iuran & Kas, Dokumen, Ekspedisi, Galeri, Repo Peta, Pengaturan & Akses) serta shortcut ke beranda anggota. (3) Menambahkan handler interaksi dropdown dan integrasi listener `htmx:afterSwap` untuk highlight menu aktif. (4) Melakukan deploy ulang dan sinkronisasi ke server `10.75.0.51`. |
| 32 | *“modifikasi langkah pembayaran iuran awal saat user baru mendaftar.... buat pilihan 2 pembayaran transfer dengan melampirkan file/foto bukti dan pembayaran melalui qris (yang belum diimplementasikan)”* | Memodifikasi antarmuka dan alur pembayaran iuran pokok awal registrasi keanggotaan (onboarding): (1) Memperbarui `members_page.py` pada handler `/member/onboarding-status` untuk menyuplai status `is_dues_paid` dan `is_payment_pending`, serta memastikan penanganan direktori upload bukti transfer (`/uploads/proofs/`) aman. (2) Mengganti tombol tunggal di `templates/components/modals.html` (`onboarding_status`) menjadi sistem selektor interaktif 2 metode pembayaran: **Metode 1: Transfer Bank Manual** dengan rincian rekening resmi KPAB GIMBAL (Bank Mandiri `131-00-1829-3321` & BCA `593-019-4821` a.n. KPAB GIMBAL KAS PUSAT), tombol copy nomor rekening otomatis dengan feedback "Tersalin!", formulir input bank pengirim, nominal, dropzone upload bukti foto struk transfer dengan live image preview instan sebelum kirim, dan catatan opsional. **Metode 2: Pembayaran QRIS (Belum Diimplementasikan)** dengan mockup frame QRIS ber-overlay badge "Belum Diimplementasikan / Segera Hadir", notice box penjelasan bahwa fitur QRIS otomatis masih dalam tahap sertifikasi merchant perbankan, dan tombol beralih ke Transfer Bank. (3) Menambahkan kartu status interaktif bila calon anggota sudah mengunggah bukti bayar (`status == 'pending'`) dengan thumbnail foto bukti dan opsi unggah ulang. (4) Menyelaraskan seluruh elemen antarmuka dengan estetika minimalis Monotone Oranye (`rounded-lg` untuk kontainer dan `rounded-md` untuk tombol/input). (5) Deploy dan sinkronisasi ke remote server `10.75.0.51:8082`. |
| 33 | *“- saat hapus user tdak bisa tetapi tidak ada flash message error penyebab, tambahkan fitur flash message untuk keterangan kesalahan...<br>- buat crud anggota supaya ada pengaturan sebagai superadmin<br>- di menu pengaturan superadmin buat supaya ada pengaturan informasi rekening, dan lain2 untuk organisasi<br>- di menu pengaturan superadmin buat supaya ada pengaturan warna tema dan lain2 yg perlu”* | Mengimplementasikan 4 fitur utama admin dan superadmin: (1) **Flash Message & Penanganan Hapus User**: Memperbaiki kegagalan hapus pengguna dengan menambahkan pembersihan cascade dependensi foreign key (`DuesPayment`, `ActivityParticipant`, `Post`, `ChatMessage`, dll.) dalam blok transaksi aman, mencegah penghapusan akun superadmin dan akun diri sendiri, mengganti return error HTTP mentah menjadi Flash Message elegan berstatus 200 via `render_gimbal_page` agar HTMX otomatis menampilkan alert box merah informatif di layar. (2) **Peran Superadmin pada CRUD Anggota**: Menambahkan dropdown pilihan peran (`superadmin`, `admin`, `member`) pada form Tambah Anggota dan Edit Anggota di `templates/components/modals.html` serta menambahkan badge label peran (`SUPERADMIN` / `ADMIN`) pada tabel master anggota di `admin_pages.html`. (3) **Pengaturan Rekening & Organisasi**: Menambahkan tab baru `organization` pada menu Pengaturan Superadmin dengan form konfigurasi nomor rekening bank utama (Mandiri), rekening cadangan (BCA), atas nama kas, nama resmi organisasi, kontak WhatsApp, email resmi, dan alamat sekretariat yang tersimpan di `SystemSetting` dan diinjeksi secara global ke seluruh template modal dan cetak dokumen. (4) **Pengaturan Tema Warna & Lebar Tampilan**: Menambahkan tab `theme` pada Pengaturan Superadmin dengan 6 pilihan warna preset tema (`orange`, `emerald`, `blue`, `amber`, `rose`, `teal`) dan 4 pilihan lebar kontainer situs (`80%`, `85%`, `90%`, `100%`) yang tersinkronisasi langsung dengan `theme-config.js` dan CSS variables. |
| 34 | *“- di chrome browser di host yang berbeda, kenapa tampilan bagian pengaturan ini berbeda?<br>- deploy ulang ke server setelah perbaikan<br>- tambahkan pengaturan enable/disable iuran dibagian pengaturan iuran bulanan”* | (1) Menginvestigasi perbedaan tampilan pengaturan antar host/browser di mana kegagalan/keterlambatan Alpine.js (misal akibat ekstensi ad-blocker) menyebabkan tab HTML tanpa atribut `x-cloak` dan initial style tampil bertumpuk ke bawah sekaligus. (2) Menerapkan perbaikan defensif pada `templates/admin/admin_pages.html` dengan server-side styling rendering pada tab aktif (`curr_tab`), atribut `x-cloak`, server-side `display: none` untuk tab inaktif, serta vanilla JS fallback switcher (`window.switchAdminTab`). (3) Memperkuat pemanggilan `Alpine.initTree` dan fallback dinamis di `templates/index.html`. (4) Menambahkan fitur konfigurasi **Enable / Disable Iuran Bulanan** di tab pengaturan iuran (`/admin/settings` tab `dues`) lengkap dengan sakelar radio interaktif, badge status penagihan real-time, pencatatan audit log, dan persistensi `Dues.is_active` serta `SystemSetting('dues_enabled')`. (5) Memverifikasi 18/18 tes unit & integrasi 100% lulus, lalu melakukan sinkronisasi dan deploy ulang ke server `10.75.0.51:8082`. |
| 35 | *“optimasi lagi bagian pengelolaan rol, saat setelah edit anggota tampilan masih kembali ke tab awal, buat supaya halaman refresh proof”* | (1) Memperbarui `admin_activity_manage` di `admin_pages.py` untuk menerima dan memprioritaskan parameter `tab`, menyuplai `active_tab` ke template, serta memperbarui seluruh rute POST operasional ROL (`update-basic`, `add-participant`, `participant-role`, `delete-participant`, `update-status`, `update-rol`, `update-phase`, `add-field-log`, `upload-gimbal-maps`, `delete-field-log`, `pin-field-photo`, `publish-to-feed`) agar mempertahankan tab aktif via parameter URL dan respons HTMX langsung tanpa round-trip redirect. (2) Menambahkan dukungan `from_activity` dan `from_tab` pada modal edit anggota (`admin_edit_member_modal` & `admin_edit_member`) sehingga setelah admin mengedit biodata anggota dari manifest tim ROL, sistem langsung kembali ke tab `manifest` kegiatan tersebut. (3) Menjadikan seluruh 5 tab ROL (`overview`, `manifest`, `rol_plan`, `field_ops`, `close_out`) refresh-proof melalui implementasi sinkronisasi URL tanpa reload (`window.history.replaceState`), atribut `x-cloak`, server-side conditional rendering, class `.rol-tab-panel`, dan vanilla JS tab switcher (`window.switchRolTab` & `window.autoSelectRolTab`) yang otomatis dipicu saat inisialisasi awal, DOM ready, maupun pasca-swap HTMX (`htmx:afterSwap`). |
| 36 | *“modifikasi lagi bagian print pdf, signer area buat 2 kolom, untuk mengetahui ada di bagian bawah kanan”* | Memodifikasi tata letak lembar pengesahan pada dokumen cetak PDF ROL & Laporan Ekspedisi ([`templates/admin/print_rol.html`](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/print_rol.html)): (1) Mengubah tata letak 3 kolom sebelumnya menjadi format 2 kolom proporsional standar organisasi (`grid grid-cols-2`). (2) Baris 1 memuat tanda tangan Pimpinan Perjalanan (kiri) dan Kepala Divisi Operasional (kanan). (3) Baris 2 menempatkan tanda tangan pengesahan organisasi *"Mengetahui, Ketua Umum KPAB GIMBAL"* di kolom kanan bawah dengan kolom kiri bawah dikosongkan untuk stempel resmi/legalitas. (4) Menambahkan proteksi `style="page-break-inside: avoid; break-inside: avoid;"` agar lembar pengesahan tidak terpotong antar halaman kertas A4 saat dicetak/diekspor ke PDF. (5) Menambahkan test unit `test_05_print_rol_renders_2_columns_signer_area` (100% lolos) dan mendeploy ke server `10.75.0.51:8082`. |
| 37 | *“ok, sekarang migrasi semua database dan aplikasi dari server lama ke 10.75.0.16 dengan ssh user root password R4h4514!?!”* | Melakukan migrasi penuh (Full Migration) database MySQL, berkas upload, dan aplikasi web dari server lama (`10.75.0.51`) ke server baru berkinerja tinggi (`10.75.0.16`, Proxmox VE Container x86_64, 2GB RAM): (1) Men-dump database MySQL `gimbal-web` dan mengompresi seluruh berkas `uploads/` dari server lama. (2) Menginstal MariaDB, Python venv, dan dependensi sistem di server baru. (3) Mengimpor dump database, membuat user database `gimbal-web`, serta memulihkan seluruh struktur dan file direktori `uploads/`. (4) Mengunggah kode aplikasi terbaru ke `/root/gimbal-web`, menyetel venv pip, file `.env`, dan mengonfigurasi systemd unit `gimbal.service` (3 gunicorn workers) pada port 8082. (5) Memverifikasi seluruh endpoint publik, auth, KTA, API aktif via curl (status 200 OK) dan memperbarui `deploy_remote.py` agar mengarah ke host baru `10.75.0.16`. |
| 38 | *“- optimasi lagi saat ada di beranda member setelah mengakses menu manage kegiatan/rol dan kembali ke lini masa, menu2 landing page tiba2 muncul di top nav bar<br>- juga buat supaya status member yang sedang online terlihat di samping nama user di char private atau di samping nama user di public chat sebagai bulatan hijau<br>- juga perbaiki untuk print rol, gunakan file logo kpab gimbal yang ada di folder /assets/logo.png<br>- jika sudah deploy ke server baru”* | (1) **Navigasi Header Landing Menu**: Memperbaiki `templates/shell.html` dengan mengubah link logo brand agar mengarah ke `/member/dashboard` saat login, menambahkan proteksi `style="display: none !important;"` pada `#landing-desktop-nav`, dan menyempurnakan `window.syncActiveNavItems` agar mengecek `isLanding = (path === '/' || path === '') && !!document.getElementById('landing-layer')` sehingga menu landing page tidak muncul di beranda member atau workspace admin. (2) **Logo Kop Surat Print ROL**: Mengganti logo di `templates/admin/print_rol.html` menjadi `/assets/logo.png`, menyetel route static `/assets/<path:filename>` via Flask, dan menyinkronkan folder `assets/` ke server. (3) **Indikator Online Member (Bulatan Hijau)**: Menambahkan kolom `last_seen` dan property `is_online` ke model `User` di `models.py`, middleware `@app.before_request` throttled di `app.py`, indikator bulatan hijau (`bg-emerald-500`) pada macro `render_chat_messages` (chat publik), daftar kontak direct message (`member_chat_contacts`), bubble pesan privat (`member_chat_messages` & `member_chat_send`), serta header DM room di `templates/components/float_chat.html`. (4) **Deploy ke Server Baru**: Memverifikasi unit test lolos 100%, melakukan deployment ke server baru `10.75.0.16:8082`, dan memverifikasi service `gimbal.service` dan `cloudflared.service` berjalan aktif (200 OK). |

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


---

## 12. Pemeriksaan & Deployment Edit Manual shell.html ke Server Produksi (10.75.0.51:8082)

- **Verifikasi Integritas File [templates/shell.html](file:///g:/My%20Drive/priv_web_apps/gimbal-web/templates/shell.html)**:
  1. **Sintaks Jinja2 & Struktur HTML**:
     - Dilakukan parsing Jinja2 dan validasi kelengkapan tag bersarang (HTML Parser) untuk memastikan seluruh tag `<div>`, `<header>`, `<nav>`, `<aside>`, `<main>` berpasangan sempurna tanpa unclosed/mismatched tags.
     - Pengujian unit test otomatis (`python test_app.py`) berhasil 100% (12/12 test OK).
  2. **Dropdown User Profile & Aksesibilitas**:
     - Mekanisme dropdown Google-Style Account Hub didukung sinkronisasi ganda: Alpine.js (`@click`, `@click.away`) dan vanilla JS fallback (`window.toggleUserProfileMenu`, `document.addEventListener('click')`) untuk mencegah hang atau unresponsive dropdown saat Alpine tree diinjeksi via HTMX.
     - Tombol Logout tersedia secara jelas di navbar, dropdown user, dan sidebar admin.
  3. **Sinkronisasi ke Server Produksi**:
     - File [templates/shell.html](file:///g:/My%20Drive/priv_web_apps/gimbal-web/templates/shell.html) telah diunggah langsung ke `/root/gimbal-web/templates/shell.html` pada server Ubuntu `10.75.0.51`.
     - `gimbal.service` telah direstart dan statusnya diverifikasi `active (running)`.
     - Permintaan HTTP ke endpoint `http://10.75.0.51:8082/` mengembalikan kode `200 OK`.

---

## 13. Reorganisasi Menu Anggota: Pemindahan Top Nav ke Sub-Menu User Name per Kelompok

- **Pembersihan Top Navigation Bar**:
  - Seluruh menu horizontal anggota (`[Beranda Anggota]`, `[KTA Digital]`, `[Iuran Saya]`, `[Arsip Dokumen]`) telah dihilangkan dari top header bar.
  - Digantikan dengan identitas visual minimalis: *"Portal Anggota KPAB-GIMBAL"*.
- **Sub-Menu Profil Pengguna (Google-Style Dropdown) Dikelompokkan Rapi**:
  - **Kelompok 1 (Identitas & Status)**: Foto Avatar, Nama Lengkap, Email, Chip NRA/Status, dan tombol utama *"Kelola Profil & Akun Hub"*.
  - **Kelompok 2 (Layanan Anggota)**:
    - 🧭 **Beranda Anggota**: Linimasa feed petualang & ekspedisi.
    - 🪪 **KTA Digital**: Kartu Tanda Anggota resmi & kode QR verifikasi (khusus anggota aktif).
    - 💰 **Iuran Saya**: Status kas & konfirmasi pembayaran iuran.
    - 📂 **Arsip Dokumen**: AD/ART, SOP pendakian, dan materi kepecintaalaman.
  - **Kelompok 3 (Data & Keamanan)**: Shortcut langsung ke modal Biodata Pribadi, Riwayat Medis & Darurat, dan Keamanan/Password.
  - **Kelompok 4 (Pengaturan & Sesi)**: Toggle mode tampilan Gelap/Terang, Simulasi Peran (Dev Mode), dan tombol Keluar (Logout).
- **Mobile Menu**: Disesuaikan dengan pengelompokan yang sama untuk konsistensi pengalaman pengguna di smartphone.
- **Validasi & Deployment**:
  - Semua unit test di [test_app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/test_app.py) lulus 100%.
  - Template telah diunggah ke `/root/gimbal-web/templates/shell.html` pada server Ubuntu `10.75.0.51`.
  - `gimbal.service` direstart dan merespons `200 OK`.

---

## 14. Pembersihan Elemen Redundan di Header & Welcome Banner Anggota (Berdasarkan Feedback Gambar)

- **Top Header Bar ([templates/shell.html](file:///g:/My%20Drive/priv_web_apps/gimbal-web/templates/shell.html))**:
  1. **Badge NRA Anggota di Samping Logo**: Dihilangkan untuk anggota non-admin, karena nomor anggota (NRA) sudah tampil jelas di tombol avatar profil di sisi kanan.
  2. **Badge Tengah (*Portal Anggota KPAB-GIMBAL*)**: Dihilangkan dari area navbar tengah sehingga header menjadi bersih, lega, dan minimalis.
- **Welcome Hero Banner Anggota ([templates/member/member_pages.html](file:///g:/My%20Drive/priv_web_apps/gimbal-web/templates/member/member_pages.html))**:
  1. **Badge Atas Nama**: Chip `[Anggota Resmi GIMBAL]` dan chip `[R-02-26]` di atas teks *"Salam Lestari, Budi Santoso Petualang!"* telah dihilangkan.
  2. **Tombol Aksi Kanan**: Tiga tombol horizontal `[Lihat KTA Digital]`, `[Iuran Kas Saya]`, dan `[Akun Saya]` telah dihilangkan dari hero banner, karena seluruh akses navigasi ini telah terpusat di dalam sub-menu profil pengguna.
- **Validasi & Deployment**:
  - Validasi sintaks Jinja2 & parsing HTML: Berhasil tanpa error.
  - Semua unit test di [test_app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/test_app.py): Lulus 100% (12/12 OK).
  - File `shell.html` dan `member_pages.html` telah diunggah ke server Ubuntu `10.75.0.51:8082` dan `gimbal.service` telah di-restart (`200 OK`).

---

## 15. Fitur Hapus Postingan Mandiri & Perbaikan Menyeluruh Kontras Teks Mode Dark/Bright

- **Fitur Hapus Postingan Milik Sendiri ([app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/app.py) & [templates/member/member_pages.html](file:///g:/My%20Drive/priv_web_apps/gimbal-web/templates/member/member_pages.html))**:
  - **Endpoint Backend**: Menambahkan route `@app.route('/member/post/delete/<int:post_id>', methods=['POST', 'DELETE'])` dengan otorisasi ketat:
    - Hanya pemilik postingan (`post.user_id == current_user.id`) atau administrator (`current_user.is_admin`) yang berhak menghapus (unauthorized menghasilkan status `403 Forbidden`).
    - Menghapus berkas foto lokal secara otomatis jika tersimpan di disk `/uploads/posts/`.
    - Mengembalikan respons `200 OK` (string kosong) agar elemen kartu postingan terhapus secara reaktif via HTMX tanpa reload halaman (`hx-swap="outerHTML swap:300ms"`).
  - **Antarmuka (Frontend)**:
    - Tombol aksi hapus (ikon tempat sampah berwarna merah `text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/40`) muncul pada kartu postingan jika pengguna adalah pemilik postingan atau admin.
    - Dilengkapi dialog konfirmasi bawaan `hx-confirm="Yakin ingin menghapus postingan ini?"`.

- **Perbaikan Menyeluruh Kontras Teks Dark & Bright Mode ([static/js/theme-config.js](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/js/theme-config.js) & [static/css/theme.css](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/css/theme.css))**:
  - **Identifikasi Akar Masalah**: Generator tema dinamis `theme-config.js` menginjeksikan aturan `.text-orange-950/900/800` berstatus `!important` secara global tanpa filter dark mode. Hal ini menyebabkan teks oranye pekat tetap cokelat gelap di atas latar belakang mode gelap `#151b26`, sehingga tidak terbaca.
  - **Penyesuaian `theme-config.js`**:
    - Membatasi shade teks gelap hanya aktif pada mode terang dengan selektor `:not(.dark)`.
    - Menambahkan aturan otomatis `html.dark .text-orange-950..700` dengan palet oranye cerah kontras tinggi (`#ffedd5`, `#fed7aa`, `#fdba74`, `#fb923c`).
  - **Penyesuaian `theme.css`**:
    - Menambahkan aturan kontras tinggi untuk seluruh teks mode gelap: `.text-slate-900` (`#ffffff`), `.text-slate-800` (`#f1f5f9`), `.text-slate-700` (`#e2e8f0`), `.text-slate-600` (`#cbd5e1`), `.text-slate-500` (`#94a3b8`).
    - Menambahkan pemulihan kontras teks aksen di mode gelap untuk amber, emerald, rose, dan blue.
    - Memperbaiki kontras mode terang: menaikkan rasio kontras teks slate-400 dan stone-400 agar memenuhi kriteria WCAG AA.
    - Mengoptimalkan feed, komentar, obrolan basecamp, dan kartu ekspedisi di [templates/member/member_pages.html](file:///g:/My%20Drive/priv_web_apps/gimbal-web/templates/member/member_pages.html) dengan kelas kontras ganda (`dark:text-white`, `dark:text-slate-100`, `dark:text-slate-200`).

- **Validasi & Deployment**:
  - Pengujian unit test di [test_app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/test_app.py): 12 dari 12 test berhasil (100% OK), mencakup otorisasi hapus postingan, linimasa feed, dan komponen terkait.
  - Berkas `app.py`, `static/css/theme.css`, `static/js/theme-config.js`, `templates/member/member_pages.html`, dan `templates/shell.html` berhasil disinkronkan ke server Ubuntu `10.75.0.51:8082`.
  - Service `gimbal.service` direstart dan verifikasi respons HTTP mengembalikan status `200 OK`.

---

## 16. Transformasi Top Nav Bar: Warna Tema Terang (Bukan Hitam) & Teks Putih Bersih

- **Latar Belakang Top Nav Bar Bertema Dinamis Terang**:
  - Mengubah latar belakang top nav bar (landing page, shell aplikasi dashboard anggota/admin, dan halaman login) dari hitam/gelap kusam menjadi **warna tema terang/vibrant** mengikuti warna tema aktif (`linear-gradient(135deg, var(--brand-600) 0%, var(--brand-500) 100%)`).
  - Jika tema **Oranye**: navbar berwarna oranye terang bernuansa petualang (`#ea580c` ke `#f97316`).
  - Jika tema diganti ke **Biru**, **Emerald**, **Amber**, **Rose**, atau **Teal**: navbar secara otomatis bertransformasi mengikuti warna tema terang yang dipilih.
  - Menghapus aturan lama di `theme.css` yang memaksa navbar menjadi gelap (`rgba(12, 15, 20, 0.95)`). Pada mode gelap (`html.dark`) sekalipun, top nav bar tetap mempertahankan warna tema terang ini (bukan hitam).

- **Tipografi & Elemen Navbar Putih Bersih (Ultra-High Contrast)**:
  - **Logo & Brand Identitas**: Teks "KPAB-GIMBAL" berwarna putih bersih beraksen tebal (`text-white font-black drop-shadow-sm`), sub-teks "REGENERASI" putih semi-transparan (`text-white/90`).
  - **Menu Navigasi Desktop**: Teks menu ("Tentang Kami", "Divisi Minat", "Ekspedisi", "Galeri", "Kode Etik", "Keanggotaan", "Pengurus") seluruhnya berwarna putih (`text-white`) dengan sentuhan hover `hover:bg-white/20`.
  - **Tombol Pengalih Mode Tampilan (Theme Toggle)**: Didesain elegan dengan efek *glassmorphism* (`bg-white/20 hover:bg-white/30 text-white border border-white/30 backdrop-blur-sm`).
  - **Mobile Menu**: Tombol hamburger dan seluruh link di dalam mobile dropdown disesuaikan dengan teks putih bersih (`text-white hover:bg-white/20`).
  - **Header Aplikasi ([templates/shell.html](file:///g:/My%20Drive/priv_web_apps/gimbal-web/templates/shell.html))**: Menyesuaikan logo, chip status admin, teks info pengguna, dan tombol dropdown trigger dengan teks putih di atas latar tema terang.

- **Validasi & Deployment**:
  - Semua unit test di [test_app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/test_app.py) lulus 100% (12/12 OK).
  - Berkas `theme.css`, `theme-config.js`, `landing.html`, `shell.html`, dan `login.html` telah disinkronkan ke server Ubuntu `10.75.0.51:8082`.
  - Service `gimbal.service` direstart dan verifikasi HTTP status mengembalikan `200 OK`.

---

## 17. Implementasi Penuh Dual-Layer HTMX pada Landing Page (View Source Hanya Menampilkan index.html)

- **Akar Masalah "View Source" Menampilkan landing.html**:
  - Sebelumnya, route `@app.route('/')` di [app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/app.py) langsung memanggil `render_template('landing.html', ...)` tanpa memeriksa keberadaan header `HX-Request`.
  - Akibatnya, ketika pengguna melakukan direct GET (misalnya saat membuka browser pertama kali atau menekan **"View Page Source"** / Ctrl+U), server langsung mengirimkan berkas mentah `landing.html` (900+ baris) alih-alih `index.html`.
  - Berkas `landing.html` sebelumnya juga masih memiliki tag `<!DOCTYPE html>`, `<html>`, `<head>`, dan `<body>` ganda.

- **Solusi & Perbaikan Dual-Layer HTMX**:
  - **Penyesuaian Route `/` ([app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/app.py))**:
    - Menambahkan percabangan `if not request.headers.get('HX-Request'): return render_template('index.html', shell_url='/')`.
    - Direct browser hit selalu mengembalikan **Layer 1** ([templates/index.html](file:///g:/My%20Drive/priv_web_apps/gimbal-web/templates/index.html)).
    - Saat browser mengeksekusi HTMX di `index.html`, elemen `<div id="app-shell" hx-get="/" hx-trigger="load" hx-swap="innerHTML">` memicu request AJAX ke `/` dengan header `HX-Request: true`.
    - Saat menerima `HX-Request: true`, server mengembalikan konten **Layer 2** ([templates/landing.html](file:///g:/My%20Drive/priv_web_apps/gimbal-web/templates/landing.html)) untuk di-swap ke dalam `#app-shell`.
  - **Refactoring [templates/landing.html](file:///g:/My%20Drive/priv_web_apps/gimbal-web/templates/landing.html) Menjadi Layer 2 Murni**:
    - Menghilangkan `<!DOCTYPE html>`, `<html>`, `<head>`, dan `<body>` yang redundan (seperti halnya [templates/shell.html](file:///g:/My%20Drive/priv_web_apps/gimbal-web/templates/shell.html)).
    - Membungkus seluruh halaman landing di dalam kontainer `#landing-layer` yang rapi.
    - Memindahkan utilitas animasi `.card-hover` ke [static/css/theme.css](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/css/theme.css).
    - Memastikan fungsi `window.openAuthModal`, `window.closeAuthModal`, dan `window.toggleMobileNav` terekspos secara global di objek `window`.
  - **Penyesuaian Tema Teal dari User**:
    - Memastikan konfigurasi `GIMBAL_THEME_COLOR = 'teal'` dari edit manual pengguna tersimpan dan aktif.

- **Validasi & Deployment**:
  - Unit test `test_01_landing_page` di [test_app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/test_app.py) diperluas untuk menguji kedua layer (direct GET mengembalikan `index.html` dan HTMX request mengembalikan `landing.html`). Seluruh 12 unit test lulus 100% OK.
  - Verifikasi langsung pada server produksi Ubuntu `10.75.0.51:8082`:
    - Direct GET `/`: mengembalikan `id="app-shell"` (Layer 1 `index.html`).
    - HTMX GET `/`: mengembalikan `id="landing-layer"` (Layer 2 `landing.html` tanpa doctype).
    - Ketika pengguna mengklik **"View Source"** di browser pada URL `/`, yang terlihat **HANYA `index.html`**.

---

## 18. Aktivasi & Integrasi Flask-Minify (Kompresi Otomatis HTML, CSS, & Inline JS)

- **Instalasi & Konfigurasi Flask-Minify**:
  - Menambahkan pustaka `flask-minify>=0.44` ke [requirements.txt](file:///g:/My%20Drive/priv_web_apps/gimbal-web/requirements.txt) dan menginstalnya di lingkungan lokal serta virtual environment server Ubuntu (`/root/gimbal-web/venv/`).
  - Menginisialisasi `Minify(app=app, html=True, js=True, cssless=True, fail_safe=True)` di [app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/app.py).
  - Mengaktifkan kompresi otomatis untuk seluruh respons HTML, inline CSS, dan inline JavaScript, yang memangkas ukuran payload HTTP serta mempercepat waktu muat halaman dan swapping HTMX.
  - Parameter `fail_safe=True` memastikan jika terjadi parsing error pada fragmen dinamis tertentu, Flask akan secara aman mengembalikan respons asli tanpa memicu error 500.

- **Validasi & Deployment**:
  - Semua unit test di [test_app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/test_app.py) lulus 100% (12/12 OK).
  - Berkas [app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/app.py) dan [requirements.txt](file:///g:/My%20Drive/priv_web_apps/gimbal-web/requirements.txt) telah disinkronkan ke server Ubuntu `10.75.0.51:8082`.
  - Service `gimbal.service` direstart, berstatus `active`, dan health check HTTP mengembalikan kode `200 OK`.
  - Respons HTML terverifikasi telah termanifikasi (whitespace dan baris kosong terpangkas secara optimal).

---

## 19. Pembersihan Navbar & Perbaikan Menyeluruh Kontras Teks Mode Terang (Bright Mode)

- **Penghapusan Badge Top Navbar yang Disilang Merah ([templates/shell.html](file:///g:/My%20Drive/priv_web_apps/gimbal-web/templates/shell.html))**:
  - Menghilangkan badge `[Panel Kendali Admin & Operasional]` dari top header navbar sehingga bagian tengah header menjadi bersih dan minimalis sesuai instruksi gambar.

- **Perbaikan Kontras Teks Dropdown Profil Pengguna (Area Biru Kanan)**:
  - **Akar Masalah**: Selektor global `.top-navbar-theme a, span, p` di mode terang sebelumnya memaksakan seluruh teks anak di dalam `<header>` berwarna putih (`#ffffff !important`). Karena dropdown profil berlatar belakang putih di mode terang, seluruh teks di dalam `<span>` ("Biodata Pribadi", "Riwayat Medis & Darurat", "Keamanan & Password") menjadi putih di atas putih sehingga tidak terlihat.
  - **Solusi**: Memperbaiki selektor di [static/css/theme.css](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/css/theme.css) dengan mengecualikan `#user-profile-dropdown` secara ketat: `:not(#user-profile-dropdown):not(#user-profile-dropdown *)`.
  - Menetapkan warna teks tegas `#1e293b` (slate-900) dan `#64748b` untuk item dropdown di mode terang.
  - Memperbaiki kotak **Simulasi Peran (Dev Mode)**: menggunakan latar belakang terang bersih `bg-stone-100/90 dark:bg-stone-800/90 border border-stone-200 dark:border-stone-700` dengan teks judul tebal dan link peran berwarna `#1e293b` (kontras tinggi).

- **Perbaikan Kontras Teks Sidebar Admin (Area Biru Kiri)**:
  - **Menu Navigasi Sidebar**: Menambahkan aturan CSS eksplisit `.admin-nav-item:not(.active)` di [static/css/theme.css](file:///g:/My%20Drive/priv_web_apps/gimbal-web/static/css/theme.css) dengan warna `#334155 !important` (slate-700 pekat dan tebal di mode terang) serta `#e2e8f0` di mode gelap. Ikon dan teks menu (`Verifikasi Anggota`, `Data Anggota`, `Iuran & Kas`, `Dokumen Resmi`, `Agenda Ekspedisi`, `Galeri Ekspedisi`) kini tampil sangat tegas dan jelas di atas kartu putih.
  - **Kotak Mode Sistem**: Mengganti latar kusam menjadi `bg-stone-100/90 dark:bg-stone-800/80 border border-stone-200 dark:border-stone-700/80` dengan teks gelap tegas `text-stone-800` dan pill status hijau emerald cerah.
  - **Link Aksi Cepat**: Teks "Beranda Publik" dan "Keluar (Logout)" di bawah sidebar kini beraksen font tebal dengan warna kontras tinggi.

- **Validasi & Deployment**:
  - Semua unit test di [test_app.py](file:///g:/My%20Drive/priv_web_apps/gimbal-web/test_app.py) lulus 100% (12/12 OK).
  - Seluruh berkas (`shell.html`, `theme.css`, `theme-config.js`, `app.py`) telah disinkronkan ke server Ubuntu `10.75.0.51:8082`.
  - Service `gimbal.service` direstart dan merespons `200 OK`.

---

## 18. Standarisasi Tampilan: Bright Mode Permanen Tanpa Switch / Config Dark Mode
- **Instruksi Pengguna**:
  *“modifikasi ulang aplikasi web supaya semua template tidak ada mode dark atau bright, defaultkan bright mode saja tanpa ada switch atau seing/config dark mode lagi, lalu deploy ulang ke server”*
- **Implementasi & Perubahan Arsitektur**:
  1. **Konfigurasi Tema Pusat ([static/js/theme-config.js](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/static/js/theme-config.js))**:
     - Menghapus variabel konfigurasi `GIMBAL_COLOR_MODE = 'bright'` sehingga sistem hanya menyisakan 2 variabel utama (`GIMBAL_SITE_WIDTH` & `GIMBAL_THEME_COLOR`).
     - Menghapus seluruh mekanisme pemilih/toggle tema (`updateToggleButtons`, `toggleGimbalColorMode`, `applyColorMode`, dsb.) dan menyediakan safe no-op stubs.
     - Membersihkan key preferensi tema di browser (`localStorage.removeItem('gimbal_color_mode')`).
     - Mengunci antarmuka secara permanen pada `light` (`data-theme="bright"`, `colorScheme = 'light'`, menghapus class `dark` dari `<html>`).
     - Menghapus aturan `darkMode: 'class'` pada Tailwind config.
  2. **Pembersihan CSS Global ([static/css/theme.css](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/static/css/theme.css))**:
     - Menghapus seluruh blok aturan `html.dark` (latar gelap, teks kontras gelap, border gelap, input gelap, tabel gelap, dan toggle tema).
     - Menetapkan warna latar dan teks bersih standar mode terang (`--color-bg-body: #fcfcfb`, `body { color: #0f172a }`, `.bg-white`, dropdown profil kontras tinggi).
  3. **Penghapusan Seluruh Tombol / Switch Mode di Semua Template**:
     - [templates/landing.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/landing.html): Menghapus tombol toggle tema pada navbar desktop dan mobile.
     - [templates/login.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/login.html): Menghapus tombol toggle tema di header navbar.
     - [templates/verify_kta.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/verify_kta.html): Menghapus floating toggle button mode di pojok kanan atas.
     - [templates/shell.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/shell.html): Menghapus tombol "Mode Tampilan" di dropdown akun pengguna dan di menu navigasi mobile.
     - [templates/components/modals.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/components/modals.html): Menghapus kotak "Mode Tampilan Aplikasi (Terang / Gelap)" dan tombol toggle di modal profil akun, serta mengubah tab menjadi "Afiliasi & Sesi".
     - [templates/index.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/index.html): Menghapus aturan scrollbar gelap `html.dark`.
  4. **Pengujian & Deployment ke Server**:
     - Seluruh unit test di [test_app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/test_app.py) lulus 100% (12/12 OK).
     - Sinkronisasi seluruh template, script, dan CSS ke server produksi `10.75.0.51:8082`.
     - Service `gimbal.service` berhasil direstart dan seluruh endpoint merespons `200 OK`.

---

## 19. Superadmin Fitra, Manajemen Iuran Rp 15.000, CRUD Admin & Member, dan Gateway Midtrans
- **Instruksi Pengguna**:
  1. *“untuk nominal seharusnya bisa di atur dari menu admin, tetapkan 15000 dulu perbulan untuk demo, juga untuk login test sebelumnya hilangkan, buat untuk superadmin adalah fitra dengan password P4ssw0rd!?!, dan tambahkan di menu pengaturan saat admin login ada crud untuk admin web serta crud/manajemen untuk anggota”*
  2. *“kita pakai gateway midtrans”*
- **Implementasi & Perubahan Teknis**:
  1. **Superadmin & Keamanan Akun**:
     - Menghapus dev switcher / bypass role switcher (`1-Klik Cepat` dan `/auth/switch-role`).
     - Menginisialisasi akun superadmin `fitra` (username `fitra`, email `fitra@gimbal.org`, password `P4ssw0rd!?!`, role `superadmin`).
     - Menambahkan proteksi khusus: akun superadmin `fitra` tidak dapat dihapus atau diturunkan rolenya oleh admin lain.
  2. **Pengaturan Tarif Iuran & Midtrans**:
     - Model `SystemSetting` untuk penyimpanan nilai dinamis berbasis key-value.
     - Default iuran diatur ke **Rp 15.000 / bulan** untuk demo, dapat diubah sewaktu-waktu oleh admin di `/admin/settings/dues`.
     - Konfigurasi Midtrans dinamis (Mode Sandbox/Production, Client Key, Server Key, Merchant ID) via `/admin/settings/midtrans`.
  3. **Manajemen Admin Web & Member (CRUD)**:
     - CRUD Admin: Tambah admin baru, edit nama/email/role, reset password, dan hapus admin (dengan proteksi fitra).
     - CRUD Member: Tambah anggota, edit biodata/NRA/status, reset password instan, dan hapus akun.
     - Audit Trail Log (`AdminAuditLog`): Mencatat setiap aksi approval, perubahan tarif, dan administrasi pengguna.
  4. **Payment Gateway Midtrans Snap**:
     - Endpoint `/member/payment/midtrans-snap` menghasilkan snap token pembayaran iuran via Midtrans API (QRIS, GoPay, Bank VA).
     - Webhook callback `/payment/midtrans/notification` untuk verifikasi signature key dan auto-update status pembayaran.
     - Fallback simulator otomatis jika key Midtrans demo/sandbox digunakan.

---

## 20. Pemisahan Rute Modular: helpers.py, admin_pages.py, members_page.py, dan app.py Lean
- **Instruksi Pengguna**:
  *“coba pisahkan dari app.py route2 untuk admin ke admin_pages.py dan route2 untuk member ke members_page.py, di app.py hanyalah konfigurasi utama dan untuk payment gateway serta api2 lainnya”*
- **Arsitektur Modular**:
  1. **[helpers.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/helpers.py)**:
     - Menyimpan utilitas bersama: `get_current_user`, `login_required`, `admin_required`, `check_member_access`, dan engine rendering `render_gimbal_page` (dengan `with context` agar macro Jinja dapat membaca variabel konteks global).
  2. **[admin_pages.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/admin_pages.py)**:
     - Menggunakan Flask Blueprint `admin_bp` (prefix terintegrasi).
     - Seluruh endpoint administrasi: Dashboard, Approval & Rejection Calon Anggota, Member CRUD, Dues CRUD, Admin Settings (Dues, Midtrans, Admin CRUD, Audit Trail), Agenda Ekspedisi CRUD (termasuk toggle status & peserta), Galeri Pin-down & CRUD, Arsip Dokumen.
  3. **[members_page.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/members_page.py)**:
     - Menggunakan Flask Blueprint `members_bp`.
     - Seluruh endpoint portal petualang: Onboarding biodata, pemantau status pendaftaran, pembayaran manual, linimasa ekspedisi (Post, Like, Comment, Delete), Basecamp live chat, KTA digital & verifikasi, riwayat & pembayaran iuran, arsip dokumen, serta profile hub modal.
  4. **[app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/app.py)** (Lean Core):
     - Konfigurasi aplikasi, database migration, inisialisasi superadmin default.
     - Integrasi Google OAuth 2.0 (login & callback).
     - Endpoint Payment Gateway Midtrans Snap (`/member/payment/midtrans-snap`, `/payment/midtrans/notification`, `/member/payment/midtrans-finish`).
     - Registrasi Blueprint `admin_bp`, `members_bp`, dan `api_bp`.
  5. **Pengujian & Validasi**:
     - Seluruh skenario pengujian di [test_app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/test_app.py) lulus 100% OK.

---

## Sesi: 29 September 2026 - Arsitektur Full HTMX Multi-Layer, Konsolidasi Modals, Perbaikan Dashboard, & Roadmap Otomasi Kas SeaBank

### 1. Arsitektur Full HTMX Multi-Layer SPA & View Source Protection
- **Outer Layer 1 (`templates/index.html`)**:
  - Skeleton dasar website: CDN scripts (Tailwind, Feather Icons, HTMX, Alpine.js, Google GIS client), indicator bar, dan `<div id="app-shell" hx-get="{{ shell_url or '/app-shell' }}" hx-trigger="load" hx-swap="innerHTML">`.
  - **Tujuan Utama Terpenuhi**: Di manapun posisi user di webapp ini (beranda `/`, login `/login`, validasi KTA `/verify-kta/...`, dashboard admin/member), saat menekan **`Ctrl+U` (View Page Source)** yang terlihat **HANYALAH isi skeleton dari `index.html`**.
- **App Shell Frame Layer 2 (`templates/shell.html`)**:
  - Sticky header monotone oranye dinamis (mendukung Guest & Member/Admin).
  - Google-style user profile dropdown & mobile drawer adaptif.
  - Layout dual-pane (sidebar navigasi kiri + main content kanan) untuk modul admin.
  - Kontainer `#main-content`, `#modal-container`, dan footer.
- **Content Fragment Layer 3 (`templates/admin/admin_pages.html`, `templates/member/member_pages.html`)**:
  - Potongan macro bersih yang di-swap oleh HTMX (`hx-target="#main-content"`) saat navigasi antar menu tanpa reload halaman/shell.

### 2. Penggabungan Template Lepas ke `templates/components/modals.html` (Dual-Mode)
- Mengkonsolidasikan 4 file template lepas yang redundan menjadi komponen modular:
  1. `modal_type == 'login'`: Tab Otentikasi Google SSO resmi & Login Manual.
  2. `modal_type == 'complete_profile'`: Langkah 1 Onboarding (Biodata, WhatsApp, Darurat, Medis).
  3. `modal_type == 'onboarding_status'`: Langkah 2 Onboarding (Panduan Iuran, Tombol Midtrans Snap, Status Approval).
  4. `modal_type == 'verify_kta'`: Halaman publik hasil scan QR validasi keaslian nomor registrasi anggota (NRA).
- **Dual-Mode System**:
  - Jika target `#modal-container` (`is_modal=True`): Ditampilkan sebagai modal popup dengan overlay gelap dan tombol tutup `×`.
  - Jika target `#main-content` (`is_modal=False`): Ditampilkan sebagai card konten halaman yang rapi dan menyatu dengan layout shell.
- File template lepas yang lama (`login.html`, `complete_profile.html`, `onboarding_status.html`, `verify_kta.html`) telah dihapus permanen di lokal dan remote server.

### 3. Perbaikan Tata Letak Admin Dashboard & Optimasi Cache HTTP
- **Bug Layout Dashboard Terselesaikan**:
  - Ditemukan tag penutup `</div>` ekstra di [templates/shell.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/shell.html) (sebelumnya di baris 242) yang menutup kontainer dropdown profil lebih dini sehingga tombol `Keluar (Logout)` bocor ke luar header dan seluruh kontainer utama tertutup sebelum waktunya (menciptakan ruang kosong putih raksasa vertikal).
  - Tag ekstra telah dihapus dan struktur tag div divalidasi seimbang sempurna (`balance = 0`). Sidebar admin dan kartu dashboard kini berdampingan rapat dan presisi di bawah navbar.
- **Pencegahan Cache Fragment HTMX pada View Source**:
  - Menambahkan middleware `@app.after_request` di [app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/app.py) dan header di [helpers.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/helpers.py):
    ```http
    Vary: HX-Request, HX-Target, Cookie
    Cache-Control: no-cache, no-store, must-revalidate, max-age=0
    Pragma: no-cache
    Expires: 0
    ```
  - Mencegah browser Chromium men-cache respons parsial HTMX sebagai konten halaman, sehingga `Ctrl+U` selalu memicu fresh GET yang mengembalikan `index.html`.

### 4. Roadmap & Rencana Implementasi Mendatang: Otomatisasi Kas SeaBank
- **Tantangan**: SeaBank tidak menyediakan Open Banking API Publik untuk nasabah reguler/perorangan.
- **Arsitektur Solusi Terpilih (Sangat Brilian & Aman)**:
  - **Email Transaction Webhook Parser (IMAP / Gmail API)**:
    1. Akun SeaBank organisasi diatur agar mengirim notifikasi bukti transaksi resmi ke email khusus (contoh: `keuangan.gimbal@gmail.com`).
    2. Server webapp GIMBAL menjalankan background worker berkala (tiap 2–5 menit) menggunakan modul Python `imaplib` via SSL dengan Google App Password.
    3. Worker menyaring email resmi SeaBank (`alert@seabank.co.id` / `noreply@seabank.co.id`), membedah (parse) tipe mutasi (Debit Keluar / Kredit Masuk), nominal, rekening tujuan/pengirim, tanggal/jam, serta Transaction Reference ID unik.
    4. Transaksi kas otomatis tercatat ke tabel buku kas organisasi di webapp GIMBAL tanpa Bendahara harus menginput manual atau membuka web.
  - **Status Roadmap**: Disimpan untuk diimplementasikan pada sesi pengembangan berikutnya.

### 5. Status Deployment Server Remote
- Host Remote: `10.75.0.51:8082` (User: `root`, Path: `/root/gimbal-web`, Service: `gimbal.service`).
- Health Check: `HTTP Status: 200`, `Service status: active`.
- Unit Testing: `17/17 tests OK` (100% lulus di [test_app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/test_app.py)).

---

## 19. Pembaruan Warna Tema Monotone Flat: Menu Pengaturan, Chat Box, Hero Banner, & Kartu KTA

### 1. Perbaikan Warna Teks & Status Selected/Hover Menu Navigasi
- **Akar Masalah**:
  - Di [static/css/theme.css](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/static/css/theme.css), aturan selector `.top-navbar-theme *:not(#user-profile-dropdown *) { color: #ffffff !important; }` memaksa seluruh teks di dalam dropdown admin `#admin-menu-dropdown` ("Pengaturan") menjadi putih di atas background putih, sehingga item menu terlihat kosong/hilang.
- **Solusi**:
  - Selector teks putih pada navbar dipersempit hanya ke tombol header langsung (`#user-profile-btn`, `#admin-menu-btn`, `#mobile-menu-btn`), sehingga isi dropdown menu tidak terpengaruh.
  - Ditambahkan styling terdedikasi untuk `.admin-nav-item` dan `.member-nav-item`:
    - **Normal**: Teks `#334155` (slate-700), ikon dalam box tema `var(--brand-50)` dengan warna `var(--brand-600)`.
    - **Hover**: Background tema muda `var(--brand-50)` (`#fff7ed`), teks dan ikon `var(--brand-600)` (`#ea580c`).
    - **Selected / Active**: Background flat tema penuh `var(--brand-600)` (`#ea580c`), teks putih tajam `#ffffff`, ikon dalam box semi-transparan `rgba(255, 255, 255, 0.25)`.
  - Reaktivitas HTMX: Script `htmx:afterSwap` di [templates/shell.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/shell.html) secara otomatis memperbarui class `.active` pada item menu yang bersesuaian dengan URL aktif saat navigasi dilakukan.

### 2. Standarisasi Warna Monotone Flat (Tanpa Gradien)
- **Top Navbar Header**: Diubah dari `linear-gradient` menjadi flat solid `var(--brand-600, #ea580c)`.
- **Hero Welcome Banner (Dashboard Anggota & Repo Peta)**:
  - Menggantikan gradien gelap (`from-orange-950 via-stone-900 to-orange-900`) dengan class `.member-hero-banner` bersolid flat `var(--brand-600)` dengan teks putih kontras tinggi dan aksen oranye terang.
- **Kartu Tanda Anggota (KTA Digital Mini & Penuh)**:
  - Menggantikan gradien gelap menuju `#0c0f14` dengan background flat tema `var(--brand-600)` yang konsisten di [theme.css](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/static/css/theme.css), [theme-config.js](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/static/js/theme-config.js), dan [member_pages.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/member/member_pages.html).
  - Header modal validasi KTA dan profile hub diubah menjadi flat `bg-orange-600`.

### 3. Pembersihan Latar Gelap di Obrolan Basecamp & Komentar
- Menghapus kelas-kelas dark mode override (`dark:bg-stone-900`, `dark:bg-stone-800`, `dark:bg-orange-950/40`) pada komponen obrolan dan linimasa di [templates/member/member_pages.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/member/member_pages.html):
  - **Pesan Chat Pengguna**: Background flat tema muda `bg-orange-50` berborder `border-orange-200/80`, teks pesan `text-slate-800`, nama `text-orange-900 font-bold`.
  - **Pesan Anggota Lain**: Background flat `bg-slate-50` berborder `border-slate-200`, teks pesan `text-slate-800`, nama `text-slate-900 font-bold`.
  - **Input Box**: Background `bg-white` berborder `border-slate-200`, teks `text-slate-900`.
  - **Tombol Kirim & Aksi**: Flat `bg-orange-600 hover:bg-orange-700 text-white`.
- Dropdown menu `#admin-menu-dropdown` dan `#user-profile-dropdown` distandarisasi ke latar belakang putih bersih (`bg-white`) dengan bayangan halus.

### 4. Sinkronisasi & Deployment ke Server Remote
- Menjalankan `sync_patch.py` untuk mengunggah seluruh template yang diperbarui, stylesheet, serta skrip konfigurasi tema ke `/root/gimbal-web` di server Ubuntu `10.75.0.51:8082`.
- `gimbal.service` direstart dan verifikasi respons HTTP `200 OK`.

---

## 20. Pembaruan Desain Minimalis: Standarisasi Radius Kotak (Minimalist Roundness) & Penyederhanaan Menu User Top-Right

### 1. Minimalist Roundness (Penurunan Tingkat Roundness Kotak)
- Menggantikan seluruh penggunaan kelas `rounded-3xl` (24px) yang dinilai terlalu bulat/kurang ramping menjadi `rounded-xl` (12px) yang modern, tegas, dan minimalis:
  - **Header & Hero**: Hero banner anggota (`.member-hero-banner`) dan repo peta diubah menjadi `rounded-xl`.
  - **Kartu Konten & Feed**: Kotak pembuat postingan (post creator), kartu postingan lini masa, kotak komentar, dan kartu KTA digital diubah menjadi `rounded-xl`.
  - **Basecamp Chat & Agenda**: Panel obrolan Basecamp, gelembung obrolan chat, dan kartu agenda ekspedisi terbuka diubah menjadi `rounded-xl`.
  - **Menu Dropdown**: Dropdown admin (*Pengaturan*) dan dropdown profil pengguna diubah menjadi `rounded-xl`.
  - **Modal Dialog & Halaman Publik**: Seluruh modal sistem (validasi KTA, formulir iuran, profil hub, login, unggah peta) dan kartu landing page diseragamkan ke `rounded-xl`.

### 2. Penyederhanaan Menu User Top-Right Navbar
- Pada tombol profil avatar pengguna (`#user-profile-btn`) di navigasi atas [templates/shell.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/shell.html):
  - Menghapus baris kedua nomor registrasi anggota / email (`{{ current_user.nra or current_user.email }}`).
  - Tombol kini hanya menampilkan foto profil avatar dan nama pengguna (`{{ current_user.name }}`) secara ringkas, elegan, dan bersih dalam format satu baris.
  - Border radius tombol diselaraskan ke `rounded-xl`.

### 3. Sinkronisasi & Deployment Server
- Menjalankan `sync_patch.py` dan memverifikasi integritas service `gimbal.service` di `10.75.0.51:8082`.

---

## 21. Perbaikan Tingkat Roundness Minimalis (rounded-lg / rounded-md), Kontras Warna Menu Dropdown & Presisi Ukuran Menu Pengaturan

### 1. Pengurangan Tingkat Roundness Kotak (Desain Minimalis Bersih)
- Menurunkan kelengkungan kotak secara menyeluruh dari `rounded-xl` / `rounded-2xl` menjadi `rounded-lg` (8px) untuk kontainer kartu, hero banner, dropdown panel, modal, dan `rounded-md` (6px) untuk tombol dan item menu:
  - **Dropdown Panel**: `#admin-menu-dropdown` dan `#user-profile-dropdown` kini menggunakan `rounded-lg` dengan item di dalamnya menggunakan `rounded-md`.
  - **Navbar Buttons**: Tombol Pengaturan (`#admin-menu-btn`) dan profil user (`#user-profile-btn`) menggunakan `rounded-lg`.
  - **Portal Anggota & Admin**: Seluruh kartu di [templates/member/member_pages.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/member/member_pages.html) dan [templates/admin/admin_pages.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/admin_pages.html) (hero banner, KTA card, post box, feed card, chat container, data table cards) telah diubah ke `rounded-lg`.
  - **Modal Dialog & Landing Page**: Seluruh modal dialog dan kartu landing page diseragamkan ke `rounded-lg`.

### 2. Perbaikan Kontras Warna & Keterbacaan Teks Menu Dropdown
- **Tombol "Kelola Profil & Akun Hub"**:
  - Diberikan styling eksplisit inline dan aturan CSS scoped ID `#user-profile-dropdown .theme-account-hub-btn`:
  - Background: tema muda lembut `bg-orange-50` / `#fff7ed`.
  - Border: `border-orange-200` / `#fed7aa`.
  - Ikon: Oranye terang `text-orange-600` / `#ea580c`.
  - Teks: Cokelat tua pekat / oranye tua pekat `#7c2d12 !important` (`text-orange-950`), menjamin kontras keterbacaan 100% tajam dan tidak lagi putih di atas putih.
- **Menu Navigasi Aktif ("Beranda Anggota", dsb.)**:
  - Item aktif menggunakan background tema `var(--brand-600, #ea580c)` dengan teks judul, subjudul (*"Linimasa petualang & ekspedisi"*), dan tanda panah chevron dipaksa secara inline dan scoped CSS ke warna putih bersih `#ffffff !important`, bebas dari gangguan styling gelap.
  - Item non-aktif menggunakan judul `#1e293b` (slate-800) dan subjudul `#64748b` (slate-500) untuk keterbacaan maksimal.
- **Kartu Profil Pengguna Teratas**:
  - Nama, email, dan nomor anggota diberikan styling warna putih tajam `#ffffff !important` di atas background tema oranye flat.
- **Cachebusting**: Versi stylesheet `theme.css` di [templates/index.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/index.html) dinaikkan ke `?v=20260930_4` untuk memaksa browser klien memuat aturan terbaru tanpa tertahan cache lawas.

### 3. Presisi Ukuran Kotak Menu Pengaturan
- Menyamakan dimensi kotak `#admin-menu-dropdown` agar persis identik dengan `#user-profile-dropdown`:
  - Lebar: disesuaikan dari `w-72` menjadi `w-80`.
  - Padding: `p-3`.
  - Border & Shadow: `border border-slate-200 shadow-2xl rounded-lg`.
  - Batas Tinggi & Scroll: `max-h-[85vh] overflow-y-auto`.

### 4. Sinkronisasi & Deployment ke Server Remote
- Menjalankan `sync_patch.py` ke remote server `10.75.0.51:8082`, me-restart `gimbal.service`, dan memverifikasi kelancaran aplikasi (HTTP 200).

---

## 22. Sinkronisasi Presisi Dimensi & Ketinggian Tombol Menu Navbar (Pengaturan & Profil User)

### 1. Masalah
- Tombol menu dropdown Pengaturan (`#admin-menu-btn`) memiliki tinggi natural ~32px (hanya ikon fa-cog + teks + padding kecil), sedangkan tombol profil pengguna (`#user-profile-btn`) memiliki tinggi ~42px karena membungkus foto avatar anggota 28px (`w-7 h-7`) + padding.
- Akibatnya, kedua kotak tombol menu yang berdampingan di navbar atas tampak tidak simetris dan berbeda tinggi serta lebarnya.

### 2. Solusi
- **Standarisasi Ketinggian Tepat 40px (`h-10`)**:
  - Di [templates/shell.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/shell.html), kedua tombol `#admin-menu-btn` dan `#user-profile-btn` diberikan class Tailwind `h-10` (40px) dan padding `px-3`.
  - Di [static/css/theme.css](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/static/css/theme.css), ditambahkan aturan strict `height: 40px !important; min-height: 40px !important; max-height: 40px !important; box-sizing: border-box !important;` untuk menjamin ketinggian 100% konsisten secara matematis.
- **Standarisasi Lebar & Tata Letak Elemen Internal**:
  - Pada layar desktop (`sm:`), kedua tombol diseragamkan dengan lebar `sm:w-[140px]` dan `justify-between`.
  - Sisi kiri: ikon / avatar sejajar dengan gap 8px terhadap teks judul ("Pengaturan" / nama pengguna).
  - Sisi kanan: ikon chevron panah bawah `⌄` (`fa-chevron-down`) terletak persis di posisi tepi kanan yang sama pada kedua tombol.
  - Border radius kedua tombol identik di `rounded-lg` (8px).
- **Cachebusting**: Menaikkan cachebuster `theme.css` di [templates/index.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/index.html) ke `?v=20260930_5`.

### 3. Sinkronisasi & Deployment Server
- Menjalankan `sync_patch.py` dan memverifikasi status `gimbal.service` di `10.75.0.51:8082`.

---

## 23. Perbaikan Interaktivitas Pemilihan Warna Tema & Lebar Layar di Pengaturan Superadmin

### 1. Masalah
- Di tab *Warna Tema & Tampilan* (`/admin/settings` tab `theme`), kartu opsi warna tema (`orange`, `emerald`, `blue`, `amber`, `rose`, `teal`) dan opsi lebar layar (`80%`, `85%`, `90%`, `100%`) tidak memberikan respons visual saat diklik oleh pengguna.
- Penyebab:
  1. Input radio disembunyikan menggunakan kelas `sr-only`, sementara styling status aktif (border, highlight background, checkmark) dievaluasi secara statis oleh Jinja2 di server. Saat kartu lain diklik di browser, kartu tersebut tidak memiliki reaktivitas client-side (Alpine.js state / `:class`), sehingga tampilan tidak berubah dan terkesan tombol/kartu macet/tidak bisa dipilih.
  2. Saat form di-submit via HTMX (`hx-post="/admin/settings/theme"`), rute backend me-render ulang `admin_settings()` tanpa meneruskan parameter tab aktif, sehingga tab kembali ke tab default (`admins`) dan pengguna mengira pilihannya hilang atau tidak tersimpan.

### 2. Solusi
- **Reaktivitas Alpine.js Lengkap**:
  - Pada form tab theme di [templates/admin/admin_pages.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/admin_pages.html), ditambahkan reactive state:
    `x-data="{ selectedTheme: '...', selectedWidth: '...', selectTheme(t), selectWidth(w) }"`
  - Setiap kartu tema dan kartu lebar layar kini memiliki interaktivitas penuh:
    - `@click="selectTheme('...')"` dan `@click="selectWidth('...')"`
    - Dynamic class binding `:class="selectedTheme === '...' ? 'border-orange-500 bg-orange-50/70 ring-2 ring-orange-500/40 shadow-sm' : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/70 bg-white'"`
    - Checkmark indikator bulat interaktif yang langsung berpindah seketika (`<i class="fas fa-check" x-show="..."></i>`).
    - Input radio `x-model="selectedTheme"` dan `x-model="selectedWidth"` untuk memastikan data form disubmit dengan benar ke backend.
- **Live Dynamic Engine & Pratinjau**:
  - Di [static/js/theme-config.js](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/static/js/theme-config.js), diekspos fungsi global `window.applyGimbalThemeDynamic(themeColor, siteWidth)`. Saat pengguna mengklik salah satu kartu tema atau persentase lebar, seluruh antarmuka web langsung menyesuaikan warnanya secara realtime sebagai live preview sebelum disimpan.
  - Ditambahkan **Live Preview Info Card** di atas tombol simpan yang menampilkan ringkasan status tema dan lebar layar yang sedang dipilih.
- **Konsistensi Navigasi Tab**:
  - Di [admin_pages.py](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/admin_pages.py), endpoint `admin_settings_theme()`, `admin_settings_dues()`, `admin_settings_midtrans()`, dan `admin_settings_organization()` kini mengembalikan `admin_settings(initial_tab='...')` saat menerima request HTMX.


---

## 24. Implementasi Pengaturan Foto Profil (Profile Picture) Anggota di Sisi Member & CRUD Admin

### 1. Kebutuhan Pengguna
- Anggota dapat mengubah foto profil mereka sendiri dari antarmuka portal anggota (Google-style Profile Hub Modal).
- Administrator dapat mengubah / mengatur foto profil anggota baik saat menambahkan anggota baru secara manual (`create_member`) maupun saat mengedit data anggota yang sudah ada (`edit_member`).
- Mendukung dua metode:
  1. Mengunggah berkas foto langsung dari perangkat (JPG, PNG, WEBP, maks 5 MB).
  2. Memilih karakter avatar petualang GIMBAL resmi (Ketua Rimba, Sekjen Rimba, Bendahara, Kadiv Alam, Petualang Pria, Srikandi Rimba).
- Terdapat pratinjau langsung (*live instant preview*) sebelum data disimpan ke database.

### 2. Implementasi Backend
- **Direktori Upload**: Folder penyimpanan avatar dipastikan selalu tersedia di `uploads/avatars/` dengan hak akses publik via endpoint Flask `GET /uploads/<path:filename>`.
- **Rute Sisi Member (`/member/profile-modal/update`)** di [members_page.py](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/members_page.py):
  - Memeriksa adanya upload berkas `avatar_file`. Jika ada, berkas disimpan dengan format aman `avatar_{user_id}_{timestamp}{ext}` ke `uploads/avatars/` dan field `user.avatar` diupdate ke `/uploads/avatars/{safe_name}`.
  - Memeriksa adanya pilihan avatar preset dari `avatar_url`.
- **Rute Sisi CRUD Admin (`/admin/members/create` & `/admin/member/edit/<id>`)** di [admin_pages.py](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/admin_pages.py):
  - Pada pembuatan anggota manual (`admin_create_member`), berkas `avatar_file` atau `avatar_url` langsung ditautkan ke record `User` baru.
  - Pada pengeditan anggota (`admin_edit_member`), avatar anggota diperbarui sesuai berkas yang diunggah atau preset yang dipilih oleh admin.

### 3. Implementasi Frontend & Komponen Modal
- **Pusat Profil Anggota (`profile_hub`)** di [templates/components/modals.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/components/modals.html):
  - Form dilengkapi atribut `hx-encoding="multipart/form-data"` untuk transmisi berkas via HTMX.
  - Ditambahkan Tab interaktif **"Foto Profil"** dengan icon kamera.
  - State reaktif Alpine.js (`previewAvatar`, `selectedPreset`, `handleFileChange`, `choosePreset`) membaca berkas via `FileReader` dan seketika memperbarui pratinjau avatar ukuran 112px.
  - Grid 6 kartu karakter petualang GIMBAL dengan indikator aktif border oranye.
- **Modal Tambah Anggota Manual Admin (`create_member`)**:
  - Dilengkapi state Alpine.js, `hx-encoding="multipart/form-data"`, pratinjau avatar live, tombol upload foto, dan chip preset avatar karakter petualang.
- **Modal Edit Anggota Admin (`edit_member`)**:
  - Dilengkapi state Alpine.js berinisialisasi avatar aktif anggota, `hx-encoding="multipart/form-data"`, pratinjau live, input penggantian berkas foto baru, dan chip preset avatar karakter petualang.

---

## 25. Dukungan Keanggotaan Berlangganan In-App Google Pay (Aplikasi gimbal-maps)

### 1. Kebutuhan Integrasi
- Mendukung anggota yang berlangganan langsung melalui **Google Pay / Google Play In-App Subscription** dari aplikasi mobile **gimbal-maps**.
- Status langganan Google Pay yang aktif secara otomatis diakui sebagai **Iuran Lunas Bulan Berjalan** di seluruh ekosistem GIMBAL (web portal dan aplikasi peta).
- Membuka hak akses fitur unggulan (*Org Member Featured Access*) di aplikasi `gimbal-maps` tanpa perlu verifikasi manual bukti transfer.

### 2. Implementasi Backend & Model Data
- **Model `User`** di [models.py](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/models.py):
  - Kolom baru: `subscription_channel` (`'manual'`, `'midtrans'`, `'google_pay'`), `subscription_expiry` (`DateTime`), `google_order_id` (format `GPA.xxxx`), `google_purchase_token`, dan `google_product_id`.
  - Properti `has_active_google_subscription`: Bernilai `True` jika saluran langganan adalah `'google_pay'` dan tanggal kedaluwarsa belum terlewati (`subscription_expiry > now`).
  - Properti `subscription_days_remaining`: Menghitung sisa hari aktif langganan.
  - Penyesuaian `is_current_month_dues_paid`: Jika `has_active_google_subscription` aktif, maka otomatis mengembalikan status lunas (`True`).
- **REST API** di [web_api.py](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/web_api.py):
  - **Endpoint Baru (`POST /api/v1/maps/subscription/google-pay`)**:
    - Menerima `email` / `google_id`, `order_id`, `purchase_token`, `product_id`, dan `duration_days` (default 30 hari).
    - Menghitung perpanjangan `subscription_expiry`, mencatat transaksi ke `DuesPayment` berstatus `approved` dengan metode `Google Pay (In-App Subscription)`.
    - Mengembalikan respons sukses dengan detail tier `member_active`, status limits unlimited, dan tanggal kadaluarsa.
  - **Endpoint Otorisasi Peta (`/api/v1/maps/check-access`)**:
    - Memeriksa keaktifan Google Pay subscriber, menyertakan metadata langganan pada `user` payload, dan langsung memberikan tier `member_active` dengan hak akses penuh (unlimited offline maps, import vektor, waypoint tak terbatas, dan unduh Repo Peta).

### 3. Tampilan Portal Anggota
- **Halaman Iuran Anggota (`member_iuran`)** di [templates/member/member_pages.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/member/member_pages.html):

## 26. Perbaikan Ketahanan Tab Pengaturan Antar Browser & Fitur Enable/Disable Iuran Bulanan

### 1. Investigasi & Akar Masalah Tampilan Tab Pengaturan
- **Gejala**: Pada browser Chrome di host tertentu (Gambar 1), seluruh 7 tab pengaturan organisasi (Kelola Admin Web, Manajemen Anggota, Rekening, Tema, Tarif Iuran, Gateway Midtrans, Audit Log) tampil bertumpuk ke bawah sekaligus tanpa highlight aktif pada tombol tab, sedangkan di host lain (Gambar 2) tampil normal hanya tab aktif.
- **Penyebab**:
  - Di [templates/admin/admin_pages.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/admin_pages.html), peralihan tab sepenuhnya mengandalkan direktif Alpine.js (`x-show` dan `:class`).
  - Elemen container tab HTML secara bawaan adalah *block element*. Tanpa adanya server-side initial style `display: none` dan atribut `x-cloak`, jika Alpine.js terhambat (misal karena ekstensi ad-blocker, keterlambatan download CDN, atau delay HTMX swap), browser merender seluruh konten tab sekaligus secara bertumpuk.
- **Solusi Defensif (Multi-Tier Resilience)**:
  - **Server-Side Render**: Menyuntikkan kelas aktif `bg-white text-orange-700 shadow-sm font-bold` dan menyembunyikan tab inaktif (`style="display: none;"` + `x-cloak`) langsung saat Jinja2 merender template berdasarkan `curr_tab` (`data.active_tab or 'admins'`). Dengan demikian, sebelum JavaScript dieksekusi, halaman sudah terisolasi dan rapi sempurna.
  - **Vanilla JS Fallback Switcher**: Menambahkan fungsi global `window.switchAdminTab(tabName)` yang dipanggil via `onclick` pada setiap tombol tab, menjamin pergantian tab tetap berfungsi 100% responsif bahkan jika Alpine.js dinonaktifkan atau diblokir ad-blocker di browser klien.
  - **Peningkatan Alpine Lifecycle & Fallback**: Memperbarui [templates/index.html](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/index.html) dengan pembuat elemen script dinamis pada `onerror` dan listener siklus hidup ganda (`htmx:load`, `htmx:afterSwap`, `alpine:init`, `alpine:initialized`, `window.onload`).

### 2. Fitur Enable / Disable Penagihan Iuran Bulanan
- **Antarmuka Pengaturan Admin (`/admin/settings` tab `dues`)**:
  - Menambahkan panel sakelar interaktif **Status Penagihan Iuran Bulanan** dengan pilihan radio button:
    - **Aktifkan Iuran (Enable)**: Status penagihan iuran aktif, wajib bayar bagi anggota dan syarat verifikasi anggota baru.
    - **Nonaktifkan Iuran (Disable)**: Bebas iuran / pembebasan kewajiban pembayaran kas sementara.
  - Menambahkan badge status penagihan real-time berindikator hijau (*Aktif*) / abu-abu (*Nonaktif*).
- **Backend & Model Data**:
  - Memperbarui `admin_settings_dues()` di [admin_pages.py](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/admin_pages.py) untuk membaca `is_active` dari form POST, memperbarui properti `Dues.is_active`, serta menyimpan konfigurasi `dues_enabled` di `SystemSetting`.
  - Memperbarui `admin_settings()` agar tidak kehilangan data form ketika iuran berstatus nonaktif (mengambil master dues kategori `'wajib'`).
  - Menambahkan pencatatan detail status enable/disable pada `AdminAuditLog`.
- **Pengujian**:
  - Menambahkan pengujian otomatis di `test_15_admin_settings_and_crud` pada [test_app.py](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/test_app.py). Seluruh 18/18 tes unit dan integrasi lulus 100% OK.

---

## 27. Penghapusan Fitur & Data Iuran Perawatan Tenda & Alat Outdoor

### 1. Deskripsi Perubahan
Sesuai arahan pengguna, tagihan/fitur sekunder **"Iuran Perawatan Tenda & Alat Outdoor"** (kategori `kegiatan`, nominal Rp 50.000) dihapus secara tuntas dari sistem agar penagihan iuran organisasi berfokus pada **Iuran Wajib Bulanan Anggota** (`wajib`).

### 2. Tindakan Teknis yang Dilakukan
1. **Pembersihan Database Seeding (`seed.py`)**:
   - Menghapus pembuatan instance `dues2` (`Iuran Perawatan Tenda & Alat Outdoor`).
   - Menambahkan mekanisme auto-purge idempoten yang mencari dan menghapus record `Dues` dengan judul serupa beserta seluruh relasi `DuesPayment` terkait.
2. **Pembersihan Database Lokal & Remote**:
   - **Database Lokal (`instance/gimbal.db`)**: Menjalankan penghapusan record iuran dan pembayaran terkait.
   - **Database Remote MySQL (`10.75.0.51:8082`)**: Mengeksekusi query pembersihan langsung:
     ```sql
     DELETE FROM dues_payments WHERE dues_id IN (SELECT id FROM dues WHERE title LIKE '%Perawatan Tenda%');
     DELETE FROM dues WHERE title LIKE '%Perawatan Tenda%';
     ```
3. **Verifikasi Tampilan Web**:
   - **Portal Anggota (`/member/iuran`)**: Hanya menampilkan tagihan Iuran Wajib Bulanan yang aktif.
   - **Panel Admin (`/admin/dues`)**: Daftar master tarif tagihan bersih dari entri perawatan alat.
4. **Verifikasi & Deployment**:
   - Menjalankan suite pengujian unit [test_app.py](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/test_app.py): 18/18 tes lulus (100% OK).
   - Sinkronisasi dan restart layanan remote `gimbal.service` via [sync_patch.py](file:///d:/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/sync_patch.py) berhasil dengan status HTTP 200 OK.

---

## 28. Penanganan Lengkap Status Iuran Disabled (Dashboard & Onboarding) serta Sistem CRUD Multi-Jenis Iuran

### 1. Latar Belakang & Masalah Pengguna
1. **Notifikasi "3 Tagihan Menunggu" di Dashboard Member Saat Iuran Dinonaktifkan**:
   - Pengguna melaporkan bahwa saat iuran di-disable dari menu pengaturan admin, widget **"Status Iuran Kas"** pada dashboard member masih memunculkan notifikasi merah *"3 Tagihan Menunggu"* dengan tombol *"Konfirmasi Iuran Sekarang"*.
   - **Akar Masalah**:
     - Di `app.py`, logika startup sebelumnya mencari `active_dues = Dues.query.filter_by(is_active=True).first()`. Ketika iuran dinonaktifkan (`is_active=False`), setiap kali server atau service direstart, `app.py` mengira belum ada data master iuran dan menambahkan record baru *"Iuran Bulanan Anggota"*. Akibatnya, tercipta beberapa duplikat iuran di database.
     - Di `members_page.py`, perhitungan `unpaid_count` belum memeriksa switch global `SystemSetting.get('dues_enabled')`.
2. **Kondisionalitas Pembayaran Iuran Saat Pendaftaran Awal (Onboarding)**:
   - Harus dipastikan bahwa setelah pendaftaran awal calon anggota, kewajiban/formulir pembayaran iuran muncul jika iuran di-enable, dan otomatis dibebaskan (*waived*) jika iuran di-disable.
3. **Penyempurnaan Tampilan & CRUD Multi-Jenis Iuran**:
   - Tampilan tab Pengaturan Iuran sebelumnya sempit dan terisolasi di sisi kiri (`max-w-2xl`).
   - Diperlukan antarmuka modern yang rapi serta mendukung CRUD penuh (Create, Read, Update, Delete, Toggle Active) untuk berbagai jenis iuran organisasi di masa depan (Iuran Bulanan, Iuran Ekspedisi/Trip, Dana Sarana & Alat, Iuran Sukarela, dll.).

### 2. Implementasi & Perubahan Teknis
1. **Pencegahan Duplikasi & Pembersihan Database**:
   - Di `app.py`, inisialisasi master iuran diubah menjadi `if Dues.query.count() == 0:` sehingga tidak akan pernah membuat duplikat record saat iuran dinonaktifkan dan server direstart.
   - Database remote MySQL dibersihkan dari duplikat iuran lama dan disatukan ke record master tunggal yang bersih.
2. **Sinkronisasi Status Disabled pada Dashboard & Halaman Member ([members_page.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/members_page.py) & [templates/member/member_pages.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/member/member_pages.html))**:
   - Pada `member_dashboard()`: Membaca status `dues_enabled`. Jika `false`, `unpaid_count` di-set ke `0`.
   - Widget "Status Iuran Kas" di dashboard member menampilkan indikator hijau lembut:
     - Judul: **Bebas Iuran Kas** (*Iuran Dinonaktifkan*).
     - Sub-teks: *"Penagihan iuran kas sedang dinonaktifkan oleh organisasi."*
     - Tombol diganti menjadi link sekunder *"Lihat Riwayat Kas"*.
   - Halaman `member_iuran()`: Menampilkan banner informatif hijau *"Kewajiban Iuran Dinonaktifkan (Bebas Iuran Kas)"* serta menyembunyikan tagihan aktif jika penagihan dimatikan.
3. **Kondisionalitas Alur Pendaftaran Baru ([templates/components/modals.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/components/modals.html) & [templates/admin/admin_pages.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/admin_pages.html))**:
   - Pada `member_onboarding_status()`: Jika `dues_enabled == False`, `is_dues_paid` dianggap `True` dan `is_payment_pending` dianggap `False`.
   - Pada stepper Langkah 2 onboarding:
     - Jika iuran disabled: Langkah 2 berstatus hijau centang *"Bebas Iuran (Dinonaktifkan)"*, formulir upload bukti transfer dan tombol Midtrans disembunyikan dan digantikan banner *"Kewajiban Iuran Keanggotaan Dibebaskan! Pendaftaran Anda diteruskan langsung ke pengurus admin."*
     - Jika iuran enabled: Menampilkan panduan nominal iuran dan formulir pembayaran seperti biasa.
   - Pada antrean verifikasi admin (`/admin/approvals`): Jika iuran disabled, calon anggota yang belum bayar diberi badge hijau *"Iuran Dinonaktifkan (Bebas Iuran)"* dan dapat disetujui langsung oleh admin.
4. **Desain Ulang & CRUD Penuh Jenis Iuran ([admin_pages.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/admin_pages.py) & [templates/admin/admin_pages.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/admin_pages.html))**:
   - Tampilan tab **Tarif Iuran Kas** diperbaiki menjadi full-width yang presisi, simetris, dan modern:
     - **Kartu 1 (Sakelar Global Penagihan)**: Toggle radio box Enable/Disable dengan indikator status aktif real-time.
     - **Kartu 2 (Daftar Master Jenis Iuran - Full CRUD)**:
       - Tabel data lengkap: Nama Iuran, Kategori (Badge Warna: Wajib, Kegiatan/Trip, Sarana & Alat, Sukarela), Nominal (Rp), Tanggal Jatuh Tempo, Status Aktif (Badge Hijau/Abu).
       - Tombol Aksi per baris:
         - **1-Klik Toggle Status**: Mengaktifkan atau menonaktifkan penagihan per jenis iuran via `/admin/dues/toggle-active/<id>`.
         - **Edit Modal**: Membuka modal edit data iuran dengan input nominal, kategori, dan deskripsi via `/admin/dues/edit/<id>`.
         - **Hapus (Delete)**: Menghapus jenis iuran dengan konfirmasi via `/admin/dues/delete/<id>` (dilengkapi cascade delete pada data relasi).
       - Tombol **"+ Tambah Jenis Iuran Baru"**: Membuka modal tambah jenis iuran baru (`/admin/dues/create`).

### 3. Validasi & Pengujian
- **Automated Tests ([test_app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/test_app.py))**:
  - Diperluas di `test_15_admin_settings_and_crud` untuk memvalidasi:
    - Status bebas iuran di `/member/dashboard` saat iuran dinonaktifkan.
    - Status bebas iuran di `/member/onboarding-status` saat iuran dinonaktifkan.
    - Siklus hidup CRUD iuran: Pembuatan iuran baru, toggle keaktifan, update data, dan penghapusan record.
  - Hasil: Seluruh 18/18 pengujian unit dan integrasi lulus 100% OK (`Ran 18 tests in 6.436s, OK`).
- **Penyebaran Remote**:
  - Seluruh berkas telah disinkronkan ke server Ubuntu `10.75.0.51:8082`.
  - Database remote telah dideduplikasi dan diatur ke status `dues_enabled = false`.
  - Service `gimbal.service` direstart dan verifikasi HTTP 200 OK.

---

## 29. Perbaikan Form/Modal Tab Pengaturan & Hak Akses Organisasi serta Penghapusan Tab Tarif Iuran Kas dari Menu Pengaturan

### 1. Masalah Pengguna
1. **Layar Putih Kosong pada Tab yang Dilingkari Merah di Halaman Pengaturan (`/admin/settings`)**:
   - Saat admin mengklik tab **Rekening & Organisasi**, **Warna Tema & Tampilan**, **Gateway Midtrans**, atau **Audit Trail Log**, tidak ada form atau modal yang muncul (tampilan di bawah bilah tab menjadi putih kosong melompong).
2. **Penghapusan Tab yang Disilang Merah**:
   - Pengguna menyilang tab **"Tarif Iuran Kas"** dengan tanda silang merah besar dan meminta bagian tersebut dihilangkan dari bilah navigasi tab Pengaturan.

### 2. Analisis & Akar Masalah
1. **Penyebab Layar Putih Kosong**:
   - Pada template [templates/admin/admin_pages.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/admin_pages.html), tag penutup kontainer `<div id="admin-panel-members">` sebelumnya terpotong/hilang.
   - Selain itu, blok panel iuran lama berada di dalam `admin_settings`. Akibat tidak adanya penutup tag `</div>` pada panel anggota, seluruh panel berikutnya (`admin-panel-midtrans`, `admin-panel-audit`, `admin-panel-organization`, `admin-panel-theme`) bersarang (*nested*) sebagai anak di dalam `#admin-panel-members`.
   - Ketika pengguna berpindah ke tab lain (`activeTab !== 'members'`), directive Alpine.js dan helper fallback JavaScript `switchAdminTab` menetapkan `display: none` pada `#admin-panel-members`. Karena seluruh panel lain terjebak di dalamnya, semuanya ikut tersembunyi sehingga layar menjadi putih kosong.

### 3. Solusi & Perbaikan yang Diterapkan
1. **Penghapusan Tab "Tarif Iuran Kas" dari Menu Pengaturan**:
   - Tombol tab `<button ... data-tab="dues">Tarif Iuran Kas</button>` dan panel `admin-panel-dues` dihapus sepenuhnya dari macro `admin_settings`.
   - Subtitle header diperbarui menjadi: *"Pusat kendali administrator web, manajemen data anggota, rekening resmi organisasi, tema tampilan, gateway pembayaran, dan audit log"*.
   - Seluruh pengelolaan tarif, switch enable/disable iuran, serta CRUD jenis iuran kini berada secara eksklusif dan terpusat pada menu **"Iuran & Kas"** (`/admin/dues`).
2. **Penataan Ulang Urutan Panel Sesuai Navigasi 1:1**:
   - Menutup `<div id="admin-panel-members">` secara tepat dan mandiri.
   - Mengurutkan ulang panel-panel di dalam `admin_settings` agar posisinya 1:1 identik dengan urutan tombol tab:
     1. `admin-panel-admins` (Kelola Admin Web)
     2. `admin-panel-members` (Manajemen Anggota)
     3. `admin-panel-organization` (Rekening & Organisasi)
     4. `admin-panel-theme` (Warna Tema & Tampilan)
     5. `admin-panel-midtrans` (Gateway Midtrans)
     6. `admin-panel-audit` (Audit Trail Log)
3. **Validasi Keseimbangan Tag HTML**:
   - Memvalidasi bahwa seluruh 6 panel berada pada level hierarki yang sama (*direct siblings*) di bawah kontainer `#admin-settings-container`.
   - Total tag `<div` sebanyak 109 dan tag `</div>` sebanyak 109 (keseimbangan tag sempurna = 0 selisih).
4. **Fungsi Switcher Tab Ganda (Alpine.js & Vanilla JS Fallback)**:
   - Setiap panel dilengkapi `x-show="activeTab === '...'"` dan atribut `data-tab` yang disinkronkan oleh fungsi `window.switchAdminTab()`, memastikan tab bekerja responsif baik dengan Alpine.js maupun vanilla JS.

### 4. Validasi & Pengujian
- **Unit Tests ([test_app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/test_app.py))**:
  - Seluruh 18/18 pengujian unit dan integrasi lulus 100% OK (`Ran 18 tests in 6.086s, OK`).
- **Penyebaran Remote Server (`10.75.0.51:8082`)**:
  - Seluruh berkas telah disinkronkan via [sync_patch.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/sync_patch.py).
  - Layanan `gimbal.service` direstart dan verifikasi kesehatan menghasilkan `HTTP Status: 200 (active)`.

---

## 30. Penghapusan Tab Kelola Admin Web dan Manajemen Anggota dari Halaman Pengaturan Organisasi

### 1. Masalah & Instruksi Pengguna
- **Instruksi Pengguna**:
  *“hilangkan menu Kelola Admin Web dan Manajemen Anggota karena sudah ada menu pengaturan>data nggota”*
- **Konteks**:
  - Pada halaman **Pengaturan & Hak Akses Organisasi** (`/admin/settings`), sebelumnya terdapat tab **"Kelola Admin Web"** dan **"Manajemen Anggota"**.
  - Karena seluruh akun pengurus, admin web, dan anggota organisasi telah dikelola secara terpusat, lengkap, dan fleksibel melalui menu navigasi utama **Pengaturan > Data Anggota** (`/admin/members`), maka kedua tab tersebut di dalam `/admin/settings` menjadi redundan dan dihapus agar fokus pada konfigurasi sistem organisasi.

### 2. Tindakan Teknis yang Dilakukan
1. **Pembersihan Template `admin_settings` ([templates/admin/admin_pages.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/admin_pages.html))**:
   - Menghapus tombol navigasi tab `Kelola Admin Web` (`data-tab="admins"`) dan `Manajemen Anggota` (`data-tab="members"`).
   - Menghapus blok kontainer panel `admin-panel-admins` dan `admin-panel-members`.
   - Mengubah inisialisasi tab aktif bawaan (`curr_tab`) dari `'admins'` menjadi `'organization'` (**Rekening & Organisasi**).
   - Memperbarui sub-judul header:
     *"Konfigurasi rekening resmi organisasi, skema warna tema antarmuka, gateway pembayaran online, dan audit log keamanan"*.
   - Menyusun 4 tab pengaturan yang bersih, simetris, dan fungsional:
     1. **Rekening & Organisasi** (`organization`) - Tab Default
     2. **Warna Tema & Tampilan** (`theme`)
     3. **Gateway Midtrans** (`midtrans`)
     4. **Audit Trail Log** (`audit`)
   - Memvalidasi tag HTML seimbang sempurna (92 tag `<div` dan 92 tag `</div>`).
2. **Penyelarasan Backend ([admin_pages.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/admin_pages.py))**:
   - Memperbarui nilai bawaan `active_tab` pada `admin_settings()` menjadi `'organization'`.
   - Menyelaraskan seluruh aksi create, edit, dan delete admin (`/admin/admins/...`) agar me-redirect kembali ke pusat manajemen pengguna di `/admin/members` (**Data Anggota**).
3. **Pengujian & Validasi ([test_app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/test_app.py))**:
   - Memperbarui asersi pengujian tab pengaturan di `test_15_admin_settings_and_crud` ke `Rekening & Organisasi`.
   - Seluruh 18/18 pengujian unit dan integrasi lulus 100% OK (`Ran 18 tests in 6.413s, OK`).
4. **Penyebaran Remote Server (`10.75.0.51:8082`)**:

---

## 31. Integrasi Jabatan Organisasi: Modal Edit Anggota & Tab Master CRUD Jabatan di Pengaturan (30 September 2026)

### 1. Deskripsi Kebutuhan Pengguna
- **Permintaan**:
  *“perbaiki lagi modal edit data anggota tambahkan jabatan, dan di menu pengaturan dan akses tambahkan tab crud jabatan”*
- **Konteks**:
  1. Pada modal edit data anggota (`edit_member` modal yang diakses dari menu **Pengaturan > Data Anggota**), pengurus membutuhkan kolom untuk memilih/menetapkan **Jabatan Organisasi** dari anggota tersebut.
  2. Begitu juga pada penambahan anggota manual (`create_member`), opsi pemilihan jabatan organisasi turut disediakan.
  3. Pada halaman **Pengaturan & Hak Akses Organisasi** (`/admin/settings`), pengurus memerlukan tab khusus berfitur CRUD lengkap untuk mengelola master **Struktur & Jabatan Organisasi** (nomenklatur jabatan, kategori hierarki BPH / Divisi Teknis Lapangan / Badan Pertimbangan, wewenang/tugas, urutan hierarki, dan status aktif).

### 2. Tindakan Teknis yang Dilakukan
1. **Model Data Baru ([models.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/models.py))**:
   - Menambahkan kolom `jabatan = db.Column(db.String(100), nullable=True)` pada model `User`.
   - Membuat model master baru `Position(db.Model)` dengan tabel `positions`:
     * `id`: Primary key
     * `name`: Nama jabatan (String 100, unik)
     * `category`: Kategori tingkatan (Pengurus Harian, Divisi Teknis, Badan Pertimbangan & Kehormatan, Struktur Khusus, Keanggotaan)
     * `order_index`: Urutan hierarki tampilan (Integer)
     * `description`: Ringkasan tugas & wewenang (Text)
     * `is_active`: Status aktif (Boolean)
     * `created_at`: Timestamp pembuatan
     * Property `member_count`: Menghitung jumlah anggota aktif pemegang jabatan tersebut.
2. **Migrasi Otomatis & Seeding Awal ([app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/app.py) & [seed.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/seed.py))**:
   - Menambahkan pengecekan otomatis migrasi DDL: `ALTER TABLE users ADD COLUMN jabatan VARCHAR(100)`.
   - Mengisi 14 master jabatan standar KPAB GIMBAL pada seeding:
     * *Pengurus Harian (BPH)*: Ketua Umum, Wakil Ketua Umum, Sekretaris Jenderal, Bendahara Umum.
     * *Divisi Teknis & Lapangan*: Kadiv Gunung Hutan (Mountaineering), Kadiv Panjat Tebing (Rock Climbing), Kadiv Caving (Susur Gua), Kadiv Rafting & Olahraga Arus Deras, Kadiv Konservasi & Lingkungan Hidup, Kadiv Humas & Kemitraan, Kadiv Logistik & Perlengkapan Operasional.
     * *Badan Pertimbangan & Anggota*: Dewan Penasehat Organisasi, Anggota Penuh (Bakti), Anggota Muda (Latsar).
   - Menetapkan jabatan bawaan Superadmin Fitra sebagai *'Sekretaris Jenderal'*.
3. **Backend Route & CRUD Jabatan ([admin_pages.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/admin_pages.py))**:
   - Mengambil daftar `positions` aktif dan menyalurkannya ke modal `create_member` dan `edit_member`.
   - Mengintegrasikan penyimpanan field `jabatan` pada `admin_create_member()` dan `admin_edit_member()`.
   - Menambahkan endpoint lengkap untuk Master Jabatan:
     * `GET /admin/positions/create-modal` (`admin_create_position_modal`)
     * `POST /admin/positions/create` (`admin_create_position`)
     * `GET /admin/positions/edit-modal/<id>` (`admin_edit_position_modal`)
     * `POST /admin/positions/edit/<id>` (`admin_edit_position` - mengalirkan perubahan nama jabatan secara otomatis ke data anggota terkait)
     * `POST /admin/positions/toggle-active/<id>` (`admin_toggle_position_active`)
     * `POST /admin/positions/delete/<id>` (`admin_delete_position` - aman tanpa merusak akun anggota, mengosongkan status jabatan terkait).
4. **Antarmuka Pengguna & Komponen Modal ([templates/components/modals.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/components/modals.html))**:
   - **Modal Edit Anggota (`edit_member`)**: Menyediakan dropdown pemilihan jabatan berstatus aktif dengan indikator kategori jabatan (`[Pengurus Harian]`, `[Divisi Teknis]`, dll.) serta opsi tanpa jabatan.
   - **Modal Tambah Anggota Manual (`create_member`)**: Dilengkapi input pemilih jabatan organisasi.
   - **Modal Tambah Jabatan (`create_position`)**: Formulir interaktif HTMX modal dengan input nama jabatan, kategori, urutan, deskripsi tugas, dan switch status aktif.
   - **Modal Edit Jabatan (`edit_position`)**: Formulir pengeditan data master jabatan.
5. **Tab Struktur & Jabatan di Halaman Pengaturan ([templates/admin/admin_pages.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/admin_pages.html))**:
   - Menambahkan tombol tab navigasi **Struktur & Jabatan (N)** di posisi kedua tab pengaturan (`data-tab="positions"`).
   - Menyediakan panel `admin-panel-positions` dengan kartu statistik ringkas (Total Jabatan, Jabatan Aktif, Pengurus Harian, Divisi Lapangan) serta tabel lengkap hierarki kepengurusan.
   - Menyediakan tombol aksi cepat: Toggle status aktif instan (1-klik), tombol Edit modal, dan tombol Hapus dengan konfirmasi aman.
   - Pada tabel **Data Anggota** (`admin_members`), menambahkan badge visual jabatan berwarna oranye dengan ikon `<i class="fas fa-sitemap"></i>` di bawah nama anggota.
6. **Pengujian Menyeluruh ([test_app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/test_app.py))**:
   - Menambahkan skenario uji baru `test_19_position_crud_and_member_jabatan`.
   - Menguji alur pembuatan jabatan, pemanggilan modal, penugasan jabatan ke anggota, pembaruan berantai (cascade update), toggle aktif, serta penghapusan aman.
   - Seluruh pengujian (19/19) lulus 100% OK.
7. **Penyebaran Remote Server (`10.75.0.51:8082`)**:
   - Menyinkronkan seluruh berkas backend dan template melalui [sync_patch.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/sync_patch.py).
   - Menjalankan migrasi remote, mengeksekusi seed data jabatan, me-restart layanan `gimbal.service`, dan memverifikasi status HTTP 200 OK.





---

## 32. Perbaikan Konsistensi & Auto-Select Tab Pengaturan serta Navigasi Admin Header

### Permasalahan yang Dihadapi:
1. **Ketidakkonsistenan Tab Pengaturan**:
   - Pemilihan tab di halaman `/admin/settings` (Rekening & Organisasi, Struktur & Jabatan, Tema & Tampilan, Midtrans, Audit Trail) sebelumnya hanya mengandalkan event binding Alpine `:class` saat tombol diklik.
   - Pada browser yang memuat script lebih lambat, cache agresif, atau saat halaman di-refresh / diakses via URL dengan parameter/hash (seperti `/admin/settings?tab=positions` atau `#positions`), tab aktif tidak otomatis terpilih dan panel yang tepat tidak terbuka secara konsisten.
2. **Sticky / Duplikasi Highlight Navigasi Header Admin**:
   - Pada templates/shell.html, Jinja sebelumnya menyuntikkan inline styling keras `style="background-color: var(--brand-600) !important; color: #ffffff !important;"` pada tautan aktif awal beserta elemen anaknya (`span`, `.nav-icon-box`, `i`, `.nav-arrow`).
   - Karena navigasi HTMX hanya menukar kontainer `#main-content`, `shell.html` luar tidak di-render ulang secara penuh. Akibatnya, inline `!important` tersebut tetap menempel pada menu lama saat pengguna berpindah halaman, menimbulkan tampilan di mana lebih dari satu menu tampak terseleksi atau menu baru tidak mendapatkan highlight secara konsisten.
3. **Mismatched Parameter pada Modal Edit Jabatan**:
   - Endpoint modal `admin_edit_position_modal` di `admin_pages.py` melewatkan variabel `target_pos` sedangkan template `templates/components/modals.html` merujuk ke `position.id`.

### Langkah Perbaikan & Solusi:
1. **Engine Tab Auto-Select & Sinkronisasi URL (templates/admin/admin_pages.html)**:
   - Membangun fungsi vanilla JavaScript mandiri `window.switchAdminTab(tabName, updateUrl)` dan `window.autoSelectAdminTab()`.
   - Engine ini secara cerdas membaca tab aktif dari 3 sumber dengan urutan prioritas:
     1. Parameter URL query `?tab=...`
     2. URL fragment hash `#...`
     3. Variabel server context `curr_tab` (fallback otomatis ke `'organization'`).
   - Secara instan membersihkan kelas aktif dari seluruh tombol tab, menerapkan styling aktif (`bg-white text-orange-700 shadow-sm font-bold active`), menyembunyikan panel lain (`admin-panel-*`), menghapus atribut `x-cloak`, dan menampilkan panel target.
   - Memutakhirkan URL peramban menggunakan `history.replaceState` tanpa me-reload halaman agar status tab tersimpan saat bookmark, reload, atau share link.
   - Mendaftarkan auto-select pada eksekusi langsung, event `DOMContentLoaded`, serta event `htmx:afterSwap`.
2. **Sinkronisasi Navigasi Header Admin & Member (templates/shell.html)**:
   - Menghapus seluruh suntikan inline style `style="... !important;"` dari seluruh link `.admin-nav-item` dan `.member-nav-item`.
   - Menggantinya dengan kelas CSS dinamis `.nav-active-item` dan handler `window.setActiveAdminNav(element)`.
   - Menambahkan engine sinkronisasi cerdas `window.syncActiveNavItems(explicitPath)` yang memetakan sub-route secara akurat (misal: `/admin/positions` atau `/admin/settings` -> aktifkan *Pengaturan & Akses*, `/admin/member/` -> aktifkan *Data Anggota*, `/admin/dues` -> aktifkan *Iuran & Kas*).
   - Menautkan sinkronisasi ke siklus hidup navigasi HTMX: `DOMContentLoaded`, `htmx:afterSwap`, `htmx:pushedIntoHistory`, dan event native `popstate`.
3. **Penyelarasan Backend Modal & Tab Fallback (admin_pages.py)**:
   - Menyediakan `position=target_pos` dan `target_pos=target_pos` pada `admin_edit_position_modal`.
   - Menyetel fallback tab default di `admin_settings_dues` ke `initial_tab='organization'` yang valid.
4. **Verifikasi & Deploy Remote Server**:
   - Memastikan tag HTML seimbang dan menjalankan seluruh rangkaian 19 unit test (`test_app.py`) dengan hasil 100% Lulus (OK).
   - Melakukan sinkronisasi patch ke remote server `10.75.0.51:8082`, me-restart `gimbal.service`, dan memverifikasi ketersediaan layanan dengan status HTTP 200 OK.


---

## 33. Perbaikan Sinkronisasi, Auto-Select & ScrollSpy Top Nav Bar Landing Page

### Permasalahan yang Dihadapi:
1. **Highlight Navigasi Tidak Dinamis / Sticky pada 'Beranda'**:
   - Tautan `Beranda` di navigasi desktop memiliki kondisi statis `{% if active_page == 'landing' %}bg-white/20{% endif %}` yang membuatnya selalu terseleksi, bahkan ketika pengguna mengklik atau menggulir ke bagian lain (*Tentang Kami*, *Divisi Minat*, *Ekspedisi*, *Galeri*, atau *Kode Etik*).
   - Tautan bagian lainnya (`/#tentang`, `/#divisi`, dll.) tidak memiliki kelas penanda aktif (`active`) maupun atribut pendukung penandaan posisi.
2. **Ketiadaan Auto-Select & ScrollSpy saat Halaman Digulir**:
   - Saat pengunjung membaca landing page dari atas ke bawah, navbar atas tidak merespons perubahan posisi scroll (scrollspy tidak ada). Pengguna tidak tahu bagian mana yang sedang aktif dibaca.
3. **Hilangnya Navigasi Landing untuk Pengguna yang Sudah Login**:
   - Tag `<nav>` sebelumnya dibungkus `{% if not current_user %}`. Jika anggota atau admin yang sedang login membuka landing page (`/`), navbar menu bagian landing page sama sekali tidak muncul (kosong).
4. **Keterbatasan Menu Mobile untuk Navigasi Bagian**:
   - Menu hamburger mobile sebelumnya hanya menyediakan tautan ke Beranda, Login, dan Validasi KTA, tanpa adanya pilihan eksplorasi langsung ke bagian *Tentang Kami*, *Divisi Minat*, *Ekspedisi*, *Galeri*, dan *Kode Etik*.

### Langkah Perbaikan & Solusi:
1. **Engine ScrollSpy & Auto-Select Navigasi Landing ([templates/shell.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/shell.html))**:
   - Membangun fungsi `window.setActiveLandingNav(sectionId)` yang menyinkronkan status aktif (`active bg-white/25 text-white font-extrabold shadow-sm`) baik pada item desktop (`.landing-nav-item`) maupun mobile (`.mobile-landing-nav-item`).
   - Menerapkan fungsi `window.initLandingScrollSpy()` menggunakan `IntersectionObserver` dipadukan dengan scroll listener untuk mendeteksi bagian halaman yang sedang terlihat di layar (`beranda`, `tentang`, `divisi`, `ekspedisi`, `galeri`, `kode-etik`) dan menggeser highlight navigasi secara real-time.
2. **Navigasi Halus (Smooth Scrolling) & Sinkronisasi URL Hash**:
   - Membangun `window.navigateLandingSection(evt, sectionId)`:
     * Mengkalkulasi offset tinggi navbar sticky (64px) secara akurat sehingga judul bagian tidak tertutup navbar.
     * Menggulir halaman secara halus (`behavior: 'smooth'`) dan memperbarui hash URL (`history.replaceState`) tanpa memicu reload halaman.
     * Jika tautan diklik dari halaman selain landing page (misal `/login` atau `/member/dashboard`), script memicu transisi HTMX ke `/` lalu menggulir ke bagian target.
   - Menambahkan aturan CSS native pada [templates/index.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/index.html): `html { scroll-behavior: smooth; scroll-padding-top: 5rem; }`.
3. **Dukungan Tampilan Desktop untuk Semua Pengguna ([templates/shell.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/shell.html))**:
   - Memperbarui desktop nav bar `#landing-desktop-nav` agar tampil saat `not current_user or active_page == 'landing'`.
   - Mengintegrasikan logika visibility ke `window.syncActiveNavItems()` sehingga saat berpindah via HTMX antara dashboard dan landing page, navigasi menyesuaikan secara otomatis.
4. **Penyempurnaan Navigasi Mobile**:
   - Menambahkan kelompok menu *Eksplorasi Halaman* pada dropdown mobile yang terhubung langsung dengan `window.navigateLandingSection()`.
5. **Verifikasi & Deployment Remote Server**:
   - Menjalankan 19 unit test (`test_app.py`) dan memastikan 100% lulus.
   - Menyinkronkan seluruh perubahan ke server remote `10.75.0.51:8082` melalui `sync_patch.py`, me-restart layanan `gimbal.service`, dan memverifikasi status HTTP 200 OK.


---

## 34. Integrasi Database untuk Section Dewan Pengurus Inti & Alamat Footer di Landing Page

### Permasalahan yang Dihadapi:
1. **Section Dewan Pengurus Inti Statis**:
   - Bagian *Dewan Pengurus Inti* (`#pengurus`) di [templates/landing.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/landing.html) sebelumnya berupa markup kartu HTML statis (hardcoded nama, jabatan, avatar, dan NRA).
   - Pengaturan hierarki kepengurusan pada Master Jabatan (`Position`) maupun penetapan jabatan anggota pada Data Anggota (`User.jabatan`) belum otomatis tercermin di landing page publik.
2. **Informasi Alamat Sekretariat & Kontak Footer Terisolasi**:
   - Blok *Sekretariat Basecamp* pada footer landing page sebelumnya memuat alamat, email, dan telepon statis.
   - Perubahan alamat, email, atau kontak organisasi yang dilakukan admin melalui menu *Pengaturan & Akses > Rekening & Organisasi* (`SystemSetting.org_address`, `org_phone`, `org_email`, `org_name`, `app_tagline`) tidak otomatis terbarui di footer landing page.

### Langkah Perbaikan & Solusi:
1. **Backend Route & Query Pengurus Inti ([app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/app.py))**:
   - Pada handler rute `landing()` (`/`), menambahkan query dinamis untuk mengambil daftar posisi aktif kategori `'Pengurus Harian'` dari tabel `positions` (`Position` model) yang diurutkan berdasarkan `order_index`.
   - Mengambil data anggota aktif (`User`) pemegang masing-masing jabatan tersebut (`User.query.filter_by(jabatan=pos.name, status='active')`).
   - Menyediakan fallback avatar kartun cerdas berdasarkan kata kunci nama jabatan jika anggota belum memiliki avatar kustom.
   - Menyalurkan koleksi data `board_members` ke dalam konteks render `landing.html`.
2. **Global Context Injection untuk Tagline & Kontak Organisasi ([app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/app.py))**:
   - Menambahkan `'app_tagline'` ke dalam `inject_system_settings()` context processor Jinja2 sehingga seluruh template memiliki akses langsung ke tagline resmi organisasi di samping `org_name`, `org_phone`, `org_email`, dan `org_address`.
3. **Template Dinamis Dewan Pengurus Inti ([templates/landing.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/landing.html))**:
   - Mengganti kartu statis dengan perulangan Jinja `{% for leader in board_members %}`:
     * Menampilkan nama jabatan (`position_name`), nama pejabat aktif (`member_name`), nomor NRA (`member_nra`), dan badge centang hijau aktif saat jabatan telah diemban anggota.
     * Jika posisi belum diemban anggota, menampilkan badge *'Amanah Terbuka'* dengan kategori hierarki.
     * Menampilkan ringkasan tugas dan deskripsi jabatan (`description`) yang diambil langsung dari database.
     * Menyertakan blok fallback jika tabel jabatan belum diisi.
4. **Koneksi Alamat & Kontak Footer Organisasi ([templates/landing.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/landing.html) & [templates/shell.html](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/templates/shell.html))**:
   - Menghubungkan alamat basecamp dengan `{{ org_address or 'Sekretariat KPAB GIMBAL, Provinsi Gorontalo' }}`.
   - Menghubungkan email resmi dengan `{{ org_email or 'sekretariat@gimbal.org' }}` beserta tautan `mailto:`.
   - Menghubungkan nomor telepon/WhatsApp basecamp dengan `{{ org_phone or '+62 812-3456-7890' }}`.
   - Menghubungkan nama organisasi dan deskripsi tagline di seluruh footer dengan `org_name` dan `app_tagline`.
5. **Seeding & Penyelarasan Otomatis ([seed.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/seed.py) & [app.py](file:///d:/GDrive/Projects/My%20Drive/priv_web_apps/gimbal/gimbal-web/app.py))**:
   - Memastikan akun kepengurusan bawaan (Ketua Umum, Sekretaris Jenderal, Bendahara Umum) memiliki nilai `jabatan` yang valid pada seed maupun saat inisialisasi aplikasi.
6. **Verifikasi & Deployment Remote Server**:
   - Seluruh 19 unit test pada `test_app.py` lulus 100%.
   - Menyinkronkan pembaruan ke server remote `10.75.0.51:8082` via `sync_patch.py`, me-restart `gimbal.service`, dan memverifikasi status HTTP 200 OK.


---

## 35. Penyembunyian Bottom Float Chat untuk Pengunjung Belum Login (Guest) di Landing Page

### Permasalahan:
- Komponen floating chat widget (templates/components/float_chat.html) sebelumnya di-include secara tanpa syarat di templates/shell.html.
- Akibatnya, pengunjung umum/guest yang belum login saat membuka landing page (/) melihat tombol widget chat mengambang di pojok kanan bawah yang aktif melakukan polling ke endpoint pesan serta meminta login jika diklik.

### Langkah Perbaikan:
1. **Pengondisian di Shell Template (templates/shell.html)**:
   - Membungkus tag {% include 'components/float_chat.html' %} di dalam blok {% if current_user %}.
   - Dengan begitu, jika pengguna belum login (current_user bernilai None), floating chat widget tidak akan dirender sama sekali ke dalam DOM.
2. **Pengondisian Komponen (templates/components/float_chat.html)**:
   - Membungkus seluruh markup DOM widget dan inisialisasi script client-side di dalam {% if current_user %} sebagai proteksi lapis ganda.
3. **Pengujian Unit (test_app.py)**:
   - Menambahkan assertion pada 	est_20_float_chat_soft_deactivation_and_cloudflare_email untuk memastikan bahwa saat unauthenticated/guest mengakses landing page, elemen #gimbal-float-chat-root, #float-chat-trigger-btn, dan #gimbal-chat-window tidak ada di respons HTML.
   - Seluruh 21 unit test lulus 100% (Ran 21 tests in 10.952s, OK).


---

## 36. Eliminasi Rolling Text Galeri & Integrasi Dinamis Divisi Operasional Landing Page

### Permasalahan:
1. **Rolling Text Marquee di Galeri**:
   - Pada section Galeri Jejak Petualangan (#galeri) di [templates/landing.html](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/templates/landing.html), terdapat animated infinite marquee ticker tape yang bergerak horizontal melintasi layar dan mengganggu fokus visual galeri foto.
2. **Section Divisi Lapangan Hardcoded**:
   - Section Divisi Operasional (#divisi) pada landing page sebelumnya berupa 4 kartu statis dengan teks deskripsi hardcoded.
   - Perubahan data jabatan, penambahan divisi operasional, atau penugasan anggota sebagai Kepala Divisi pada master database (positions dan users) tidak terhubung ke landing page maupun keterangan divisi di footer.
3. **Keterangan Footer Belum Sinkron**:
   - Bagian *Navigasi Cepat* pada footer masih memuat teks statis *'4 Divisi Minat Lapangan'* tanpa mencerminkan seluruh korps divisi operasional yang ada di database.

### Langkah Perbaikan & Solusi:
1. **Eliminasi Ticker Marquee Galeri**:
   - Menghapus blok markup .animate-marquee-infinite ticker tape dari section #galeri di 	emplates/landing.html.
   - Menghapus styling keyframes CSS @keyframes marqueeScroll dan rule .animate-marquee-infinite.
2. **Koneksi Database Divisi Operasional ke Landing Handler ([app.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/app.py))**:
   - Mengambil data posisi aktif kategori 'Divisi Operasional' dari tabel positions (Position model).
   - Menautkan nama pejabat aktif (User.jabatan == Position.name, status='active') untuk menampilkan penugasan Kadiv (atau 'Amanah Terbuka' jika belum ditugaskan).
   - Memetakan gambar kartun tematik, tag spesialisasi (Mountaineering, Rock Climbing, Speleology, River Running, Ecology & SAR), warna badge, dan ikon secara terstruktur.
   - Menyalurkan variabel operational_divisions ke dalam konteks template landing.html.
3. **Template Dinamis Section Divisi ([templates/landing.html](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/templates/landing.html))**:
   - Mengubah judul menjadi dinamis: {{ operational_divisions|length if operational_divisions else 5 }} Divisi Operasional GIMBAL.
   - Mengganti kartu hardcoded dengan loop {% for div in operational_divisions %} yang menampilkan foto tematik, tag spesialisasi, deskripsi langsung dari database, badge penugasan Kadiv + NRA, dan sorotan keahlian teknis lapangan.
4. **Penyelarasan Keterangan Divisi di Footer ([templates/landing.html](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/templates/landing.html))**:
   - Memperbarui tautan footer menjadi dinamis: {{ operational_divisions|length if operational_divisions else 5 }} Divisi Operasional Lapangan.
   - Menambahkan daftar divisi operasional tematik (• Gunung Hutan, • Panjat Tebing, • Susur Gua (Caving), • Arung Jeram (Rafting), • Konservasi & LH) di bawah tautan navigasi footer.
5. **Verifikasi & Deployment Remote Server**:
   - Seluruh 21 unit test pada 	est_app.py lulus 100%.
   - Menyinkronkan pembaruan ke server remote via deploy_remote.py, me-restart gimbal.service, dan memverifikasi endpoint kembali aktif (HTTP 200 OK).
---

## 37. Manajemen Ekspedisi & ROL Multi-Jenis Kegiatan, Full-Page Command Hub, Print-Ready Preview, dan Integrasi Mobile Gimbal-Maps

### 1. Latar Belakang & Kebutuhan Pengguna
- **Tampilan Card Ekspedisi**: Mengubah kartu daftar ekspedisi di panel admin menjadi lebih ringkas dan proporsional (grid 3-4 kolom dengan rasio cover kompak).
- **Full Page Add & Manage Ekspedisi**: Menggantikan modal pop-up sempit dengan halaman penuh (*Full-Page Command Hub*) untuk pengelolaan komprehensif agenda ekspedisi.
- **Detail ROL Menyesuaikan Ragam Jenis Kegiatan**:
  - Ekspedisi di organisasi petualang mencakup beragam divisi: **Gunung Hutan (Mountaineering)**, **Panjat Tebing (Rock Climbing)**, **Susur Gua (Caving / Speleologi)**, **Arung Jeram (Rafting / Water Rescue)**, **Konservasi & Lingkungan Hidup**, **Pendidikan Dasar (Diksar / Latsar KPAB)**, dan **Camp & Wisata Alam**.
  - Setiap jenis kegiatan memiliki spesifikasi checklist ROL unik (alur pos/rute checkpoint, perlengkapan tim, perlengkapan pribadi, ransum logistik konsumsi, kotak obat medis khusus, dan rekomendasi peran operasional tim).
- **Alur Siklus Hidup Ekspedisi**:
  - **Planning (Draft ROL)**: Penyusunan anggaran biaya (RAB), penentuan rute & tautan Repo Peta, checklist logistik, dan kotak medis.
  - **Open (Buka Pendaftaran)**: Penerimaan pendaftar, manajemen manifest tim, dan penunjukan peran operasional tim.
  - **In Progress (Operasi Lapangan Dimulai)**: Penguncian registrasi, hanya menerima entri titik survei POI, elevasi, rute spasial, dan foto dokumentasi baik secara manual di web maupun langsung dari aplikasi mobile gimbal-maps.
  - **Completed (Tutup Ekspedisi / LPJ)**: Evaluasi akhir, pembukuan realisasi RAB, penerbitan laporan LPJ resmi, publikasi rangkuman ke linimasa petualang anggota, dan pinning foto terbaik ke galeri beranda.
- **Laporan Cetak Print-Ready HTML/CSS**:
  - Pratinjau cetak resmi A4 portrait dengan kop surat resmi KPAB GIMBAL, identitas lengkap kegiatan & divisi, tabel manifest personil & peran, tabel RAB, checklist logistik & medis, log temuan lapangan, dan lembar pengesahan tanda tangan berjenjang.
  - Dilengkapi floating action toolbar dengan tombol instan window.print() yang langsung memicu dialog cetak browser Ctrl+P -> *Save as PDF*.
- **Integrasi Aplikasi Mobile gimbal-maps**:
  - Login Google OAuth/token langsung di aplikasi mobile yang terhubung ke database keanggotaan GIMBAL.
  - Sinkronisasi otomatis data lapangan (titik POI GPS, elevasi, foto base64, dan berkas jejak .gpx) langsung dari mobile canvas ke ekspedisi aktif di web.

### 2. Implementasi Teknis & Perubahan Kode
1. **Model Data ([models.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/models.py)) & Migrasi ([app.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/app.py))**:
   - Tabel ctivities: Menambahkan kolom category (default 'Gunung Hutan'), phase (planning, open, in_progress, completed, rchived), udget_json, 
oute_plan, map_repo_id, gear_json, dan evaluation_notes.
   - Tabel ctivity_participants: Menambahkan kolom 
ole (Pimpinan Perjalanan, Navigator, Logistik & Konsumsi, Medis / P3K, Dokumentasi & Publikasi, Sweeper, Anggota Tim).
   - Tabel baru ctivity_field_logs: Mencatat POI titik survei lapangan, elevasi, koordinat GPS, foto dokumentasi, dan tautan berkas geodata dengan field source ('manual' atau 'gimbal_maps').
2. **Preset ROL Multi-Jenis Kegiatan ([admin_pages.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/admin_pages.py))**:
   - Fungsi kamus get_rol_category_presets() memetakan 7 modul kegiatan petualang dengan template rute checkpoint, perlengkapan tim, perlengkapan pribadi, logistik konsumsi, dan kotak medis khusus.
   - Endpoint AJAX GET /admin/activity/preset-rol?category=<cat> yang mengembalikan JSON template rekomendasi secara asinkron.
   - Penyesuaian dmin_activity_new dan dmin_activity_update_basic untuk menyimpan dan menerapkan preset kategori kegiatan secara otomatis.
3. **Antarmuka Web Admin ([templates/admin/admin_pages.html](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/admin_pages.html))**:
   - Menampilkan kartu ekspedisi lebih kecil dengan grid responsif 3/4 kolom (grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4) disertai badge jenis kegiatan.
   - Halaman Full Page /admin/activity/new dengan selektor jenis kegiatan & divisi, tingkat kesulitan, kuota, dan status awal.
   - Halaman Full Page Command Hub /admin/activity/<id>/manage dengan 5 tab operasional: *Overview*, *Manifest Tim*, *Perencanaan ROL* (dilengkapi dropdown picker template preset + tombol AJAX auto-fill), *Operasi Lapangan*, dan *Tutup Kegiatan (LPJ)*.
4. **Template Cetak Print-Ready ([templates/admin/print_rol.html](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/print_rol.html))**:
   - Tata letak cetak A4 portrait standar KPAB GIMBAL dengan kop surat resmi, identitas kegiatan & jenis divisi, tabel manifest personil & peran, tabel RAB, rencana rute & logistik, daftar log POI lapangan, dan lembar tanda tangan pengesahan pimpinan perjalanan, pembina, serta ketua umum.
5. **REST API Mobile & Web ([web_api.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/web_api.py))**:
   - POST /api/v1/auth/google-login: Menerima email/token akun Google, mencocokkan keanggotaan, dan menerbitkan payload user serta auth token.
   - GET /api/v1/activities/active: Mengembalikan daftar agenda ekspedisi berfase aktif untuk dipilih surveyor.
   - POST /api/v1/activities/<id>/field-sync: Menerima titik survei lapangan (dengan decode foto base64) dan unggahan berkas spasial GPX/GeoJSON/KMZ dari mobile app.
6. **Aplikasi Mobile Gimbal-Maps (Flutter)**:
   - Menambahkan dependensi http: ^1.6.0 di [pubspec.yaml](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/pubspec.yaml).
   - Mengembangkan [lib/services/api_sync_service.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/services/api_sync_service.dart) untuk menangani Google Login, pengecekan keanggotaan/langganan in-app Google Pay, dan sinkronisasi data lapangan.
   - Mengembangkan dialog interaktif [lib/ui/widgets/expedition_sync_dialog.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/widgets/expedition_sync_dialog.dart).
   - Mengintegrasikan tombol aksi sinkronisasi ke [lib/ui/screens/export_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/export_screen.dart) dan AppBar [lib/ui/screens/map_list_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/map_list_screen.dart).

### 3. Verifikasi & Pengujian
- **Backend Gimbal-Web**: Seluruh alur diuji via [test_rol_and_sync.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/test_rol_and_sync.py) dan lulus 100% OK (Preset API, Full Page Create, Update ROL, Transisi Fase, Print-ready Preview, dan Mobile API sync).

### 4. Deployment ke Server Remote Production (10.75.0.51:8082)
- **Sinkronisasi Kode & Template**: Mengunggah seluruh berkas inti (`app.py`, `models.py`, `admin_pages.py`, `web_api.py`, `members_page.py`, `helpers.py`), template admin (`admin_pages.html`, [print_rol.html](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/print_rol.html)), dan direktori baru `uploads/expeditions`.
- **Migrasi Skema MySQL**: Berhasil memigrasi tabel `activity_field_logs`, kolom ROL pada `activities`, dan kolom peran pada `activity_participants`.
- **Eksekusi Pengujian Remote**: Menjalankan pengujian [test_rol_and_sync.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/test_rol_and_sync.py) langsung di atas runtime Python venv & database MySQL server produksi dan lulus 100% OK.
- **Status Layanan**: Service `gimbal.service` (Gunicorn WSGI) aktif dan beroperasi normal (HTTP 200 OK).
- **Penyesuaian Signer Lembar Pengesahan Sesuai Jabatan**: Menghapus data hardcoded pada lembar tanda tangan [print_rol.html](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/templates/admin/print_rol.html). Signer dihubungkan langsung secara otomatis ke tabel `users` & `positions` di database (Pimpinan Perjalanan, Kepala Divisi terkait kategori kegiatan, dan Ketua Umum KPAB GIMBAL) disertai drawer penyesuaian pejabat interaktif pada toolbar pratinjau cetak.
- **Kompilasi Biner Mobile Gimbal-Maps**: Berkas `.apk` rilis terbaru berhasil di-recompile (`flutter build apk --release`) dengan seluruh fitur integrasi (Google Login, cek keanggotaan, dan sinkronisasi titik survei/jejak GPX lapangan). Lokasi biner: `gimbal-maps/build/app/outputs/flutter-apk/app-release.apk` (25.5 MB).
- **Mobile Gimbal-Maps**: Seluruh 44 tes unit pada suite Flutter (lutter test) lulus 100% OK.

---

## 34. Implementasi Opsi 2: Integrasi Native Google Sign-In SDK pada Mobile Gimbal-Maps & Rilis APK

### 1. Konfigurasi Google Cloud Console & Keystore Fingerprint
- **Package Name Android**: `com.gimbalmaps.app.gimbal_maps` (sesuai `android/app/build.gradle.kts`).
- **Keystore SHA-1 Fingerprint**: `C3:63:31:2F:0E:3D:59:2F:7C:96:04:9A:43:C9:E0:D5:06:CA:54:F6` (diekstrak dari debug/release keystore lokal).
- **Google Client IDs**:
  - Web Client ID (backend verification & serverClientId): `192747044891-mjtv9db8063neuhkq6neivg7qlsillul.apps.googleusercontent.com`
  - Android Client ID: `192747044891-m20naqcune3ho5vf8pbi5v8rgpmgucvl.apps.googleusercontent.com`

### 2. Implementasi Teknis Opsi 2 (Native Google Sign-In SDK)
- **Dependensi Flutter**: Menambahkan `google_sign_in: ^6.2.2` pada [pubspec.yaml](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/pubspec.yaml) yang stabil, kompatibel dengan Dart 3.7 / Flutter 3.29, serta mendukung parameter `serverClientId`.
- **Izin Android ([AndroidManifest.xml](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/android/app/src/main/AndroidManifest.xml))**:
  - Menambahkan izin `android.permission.INTERNET` dan `android.permission.ACCESS_NETWORK_STATE`.
- **Layanan Sinkronisasi API ([lib/services/api_sync_service.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/services/api_sync_service.dart))**:
  - Inisialisasi `GoogleSignIn` dengan `serverClientId: webClientId` dan scope `['email', 'profile']`.
  - Method `signInWithGoogleNative()` yang memicu Google Account Picker dialog native di Android, mengambil ID Token dan Access Token, kemudian memanggil endpoint backend `/api/v1/auth/google-login`.
  - Default URL diarahkan ke server produksi `http://10.75.0.51:8082`.
- **Dialog Sinkronisasi Lapangan ([lib/ui/widgets/expedition_sync_dialog.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/widgets/expedition_sync_dialog.dart))**:
  - Mengubah tampilan dialog login menjadi 1-klik: tombol utama "Masuk dengan Akun Google" yang langsung membuka Google Account Picker bawaan sistem Android.
  - Menyediakan accordion fallback ("Atau Masuk dengan Email Manual / Konfigurasi Server") bagi pengguna tanpa Google Play Services atau keperluan dev lokal.
- **Pengujian Unit**: Seluruh 45 unit test pada `flutter test` lulus 100% OK.

### 3. Kompilasi & Verifikasi Biner Rilis APK
- **Perintah Kompilasi**: `flutter build apk --release` (Gradle `assembleRelease`).
- **Berkas Hasil Kompilasi**: `d:\Projects\My Drive\priv_web_apps\gimbal\gimbal-maps\build\app\outputs\flutter-apk\app-release.apk`
- **Ukuran File**: 26.915.785 bytes (~26.9 MB)
- **Git Commit**: Commit hash `d370ede` pada branch `feature/auth-and-subscription` di repo `gimbal-maps`.

- **Update Default Production Backend Endpoint**: Mengarahkan default server URL `_baseUrl` pada `ApiSyncService` langsung ke domain resmi produksi bersertifikat SSL `https://www.gimbal.my.id` (menggantikan IP internal staging `http://10.75.0.51:8082`).

---

## 35. Implementasi Unduh Repo Maps & Sinkronisasi Data Lapangan Terisolasi Spesifik Peta

### 1. Unduh Peta Langsung dari Repo Peta www.gimbal.my.id
- **Tombol Tambah Peta Terintegrasi**: Tombol FAB `+ Tambah Peta` di `map_list_screen.dart` kini menyajikan modal bottom sheet pilihan sumber:
  1. **Unduh dari Repo Peta GIMBAL (www.gimbal.my.id)**
  2. **Impor Berkas dari Memori Perangkat (GeoTIFF, MBTiles, GeoPDF)**
- **Widget Dialog Katalog Repo Peta ([repo_maps_dialog.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/widgets/repo_maps_dialog.dart))**:
  - Mengambil daftar paket peta resmi dari `GET /api/v1/maps/repo`.
  - Dilengkapi search filter, penampil badge format (MBTILES, GEOTIFF, GEOPDF, GPX, KML), ukuran file, dan ringkasan wilayah.
  - Pengunduhan stream berkas fisik via `ApiSyncService.downloadRepoMap()` dengan indikator progres persentase real-time.
  - Berkas raster yang terunduh langsung diproses ke piramida tile luring (`_processFileImport`), sedangkan berkas geodata vektor langsung diparsing dan dipasang ke basis data peta lokal.

### 2. Upload Data Terisolasi Spesifik Peta & Konfirmasi Jenis Kegiatan API
- **Endpoint Backend API ([web_api.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/web_api.py))**:
  - Memperbarui `GET /api/v1/activities/active` untuk menyertakan atribut `category` (Jenis Kegiatan), `description`, dan `route_plan`.
  - Perubahan telah disinkronkan dan dideploy ke server produksi `10.75.0.51:8082` (`https://www.gimbal.my.id`) dengan status service active (HTTP 200).
- **Dialog Sinkronisasi Ekspedisi ([expedition_sync_dialog.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/widgets/expedition_sync_dialog.dart))**:
  - **Pemilih Peta Spesifik**: Pengguna dapat memilih peta lokal mana yang datanya ingin diunggah dari daftar seluruh peta tersimpan.
  - **Isolasi Data Peta**: Sistem hanya memuat dan mengunggah titik POI dan trek spasial yang tercatat pada peta yang dipilih (`DatabaseService.getPointsForMap(selectedMap.id)`). Seluruh data dari peta lain di HP tidak akan disentuh atau terunggah.
  - **Konfirmasi Jenis Kegiatan dari API**: Menampilkan kartu konfirmasi visual dengan badge kategori warna dinamis (Gunung Hutan, Panjat Tebing, Susur Gua/Caving, Arung Jeram/Kayak, SAR & Konservasi), lokasi, tanggal, status fase, dan pimpinan perjalanan.
  - **Pratinjau Data Transparan**: Menampilkan hitungan titik POI, lintasan rute, foto lapangan, serta ringkasan chip nama titik sebelum pengguna menekan tombol konfirmasi upload final.

### 3. Kompilasi Biner APK
- Seluruh 45/45 tes unit Flutter lulus 100% OK.
- Berkas rilis APK berhasil dikompilasi: `gimbal-maps/build/app/outputs/flutter-apk/app-release.apk` (26.97 MB, timestamp 13:06:57).

---

## 36. Perbaikan UI G-Maps, Pembatasan Login Khusus Anggota Aktif, Pemisahan Raster/Vektor Repo

### 1. Perubahan UI & Navigasi Mobile Gimbal-Maps
- **Penamaan Header Brand**: Teks brand di pojok kiri atas [map_list_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/map_list_screen.dart) diubah menjadi **`G-Maps`** sesuai arahan visual pengguna.
- **Tombol Akun Google di Navbar (Login / Logoff)**:
  - Ikon sinkronisasi awan pada AppBar digantikan dengan tombol status Akun Google (`Icons.account_circle`).
  - Menampilkan modal akun Google: bila sudah masuk, menampilkan Nama, Email, NRA, status keanggotaan terverifikasi ("STATUS: AKTIF"), serta tombol **Logoff** untuk keluar dari sesi akun Google.
  - Bila belum masuk, menyediakan tombol masuk satu-klik Google Sign-In Native SDK serta fallback email terdaftar.
- **Pemusatan Sinkronisasi Lapangan**:
  - Tombol sinkronisasi ekspedisi di navbar utama ditiadakan agar lebih bersih, dan difokuskan berada di dalam dialog **Data & Export** ([export_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/export_screen.dart)).

### 2. Validasi Keamanan API: Khusus Akun Google Berstatus "Aktif" di Webapps
- **Validasi Backend ([web_api.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/web_api.py))**:
  - Endpoint `POST /api/v1/auth/google-login`: Menolak akses (HTTP 404 / 403) bagi akun Google yang belum terdaftar di database anggota atau akun yang berstatus selain `active` (seperti `pending`, `suspended`, `inactive`).
  - Endpoint `POST /api/v1/maps/share-track`: Menambahkan pengecekan status keanggotaan aktif sebelum menerima sinkronisasi lintasan GPX ekspedisi.
  - Penambahan unit test verifikasi penolakan user pending dan unregistered pada [test_rol_and_sync.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/test_rol_and_sync.py) (100% Pass).
  - Sinkronisasi dan reload service berhasil diterapkan pada server remote produksi `https://www.gimbal.my.id`.

### 3. Filtrasi Khusus Raster pada Tambah Peta Awal & Filtrasi Khusus Vektor pada Layer Maps
- **Dialog Repo Peta ([repo_maps_dialog.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/widgets/repo_maps_dialog.dart))**:
  - Ditambahkan parameter filter: `rasterOnly`, `vectorOnly`, dan `customTitle`.
  - Ekstensi Raster/Tiles: `mbtiles`, `tif`, `tiff`, `geotiff`, `pdf`, `geopdf`.
  - Ekstensi Vektor: `gpx`, `kml`, `kmz`, `geojson`, `json`, `shp`, `gpkg`, `zip`.
- **Tambah Peta Awal ([map_list_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/map_list_screen.dart))**:
  - Menu `+ Tambah Peta -> Unduh dari Repo Peta GIMBAL` memanggil `RepoMapsDialog` dengan `rasterOnly: true`. Seluruh layer vektor disaring keluar agar hanya peta-peta raster/tiles yang muncul.
- **Impor Layer Vektor dalam Canvas Peta ([layer_manager_sheet.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/widgets/layer_manager_sheet.dart))**:
  - Tombol `+ Impor Layer` kini menampilkan modal pilihan sumber:
    1. **"Unduh dari Repo Web GIMBAL"**: Membuka katalog `RepoMapsDialog` dengan `vectorOnly: true` (hanya menampilkan GPX, KML, KMZ, GeoJSON, SHP). Berkas vektor yang diunduh langsung diimpor ke peta aktif sebagai layer vektor.
    2. **"Impor dari Memori Perangkat (HP)"**: Membuka pemilih berkas lokal seperti sebelumnya.

### 4. Hasil Pengujian & Kompilasi APK
- `flutter test`: 45/45 tes lulus 100%.
- Biner rilis APK dikompilasi ulang dan siap digunakan.

---

## 37. Implementasi Lisensi Free Tier vs Unlimited Pro pada Gimbal-Maps APK

### 1. Aturan Bisnis Lisensi & Batasan Akun
- **Kondisi Free Tier (Dibatasi)**:
  - Pengguna belum login akun Google, **ATAU**
  - Akun Google login tetapi tidak terdaftar atau tidak berstatus `active` di webapps GIMBAL (`https://www.gimbal.my.id`), **ATAU**
  - Akun belum berlangganan (subscription) ke Google Play.
- **Batasan Free Tier yang Diterapkan**:
  1. **Maksimal Peta Tersimpan**: Hanya diperbolehkan maksimal **2 peta** offline.
  2. **Jarak Rekam Rute Spasial (Tracking GPS)**: Maksimal **1.0 km (1.000 meter)** per rute.
  3. **Maksimal Titik POI (Placemark)**: Maksimal **5 titik POI per peta**.
- **Kondisi Unlimited Pro (Akses Penuh Tanpa Batas)**:
- **Klasifikasi Tingkat Lisensi & Hak Akses**:
  1. **Anggota Aktif Web GIMBAL** (Login Akun Google aktif di `https://www.gimbal.my.id`):
     - Fitur Penuh (Unlimited): Simpan peta tanpa batas, rute rekam GPS tanpa batas jarak, dan titik POI tanpa batas.
     - **Akses Cloud GIMBAL**: Unduh paket peta raster dari repo web, unduh layer vektor dari repo web, dan sinkronisasi data survei ekspedisi langsung ke webapps GIMBAL.
  2. **Akun Ter-Subskripsi Google Play** (Google Play Pro Standalone):
     - Fitur Penuh Mandiri (Unlimited): Simpan peta tanpa batas, rute rekam GPS tanpa batas jarak, dan titik POI tanpa batas.
     - **Tanpa Akses Cloud GIMBAL**: Tidak ada opsi/tombol unduh peta raster ataupun vektor dari web GIMBAL, serta tidak ada sinkronisasi/ekspor ke server web GIMBAL.
     - **Ekspor Lokal Penuh**: Menyimpan berkas hasil survei langsung ke folder lokal memori perangkat atau berbagi lokal dalam format **CSV (Tabel)**, **KMZ (Foto)**, **GeoJSON**, **GPX**, dan **KML**.
  3. **Free Tier (Gratis / Belum Langganan & Bukan Anggota)**:
     - Maksimal 2 peta tersimpan.
     - Jarak rekam rute GPS dibatasi maksimal 1.0 km (1.000 meter).
     - Maksimal 5 titik POI per peta.
     - Hanya ekspor lokal ke memori perangkat.

### 2. Modifikasi Layanan & Komponen UI/UX
- **`SubscriptionService` ([lib/services/subscription_service.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/services/subscription_service.dart))**:
  - Properti `canAccessGimbalCloud`: Hanya aktif untuk anggota Google aktif di web GIMBAL (`isActiveMember`).
  - Properti `isUnlimited`: Aktif jika `canAccessGimbalCloud` ATAU `isGooglePlaySubscribed`.
  - Badge label dan teks deskripsi status lisensi yang transparan membedakan hak akses ketiga tingkatan akun.
- **`ExportImportService` ([lib/services/export_import_service.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/services/export_import_service.dart))**:
  - Penambahan generator `generateCsv({required List<SurveyPoint> points})` untuk ekspor tabular titik survei (ID, Name, Code, Category, Lat, Lon, Elevation, Accuracy, Description, Time).
- **`export_screen.dart` ([lib/ui/screens/export_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/export_screen.dart))**:
  - Penambahan pill format **CSV (Tabel)** pada pemilih format ekspor.
  - Tombol **"Sinkronkan ke Ekspedisi GIMBAL Web"** hanya ditampilkan jika `SubscriptionService.instance.canAccessGimbalCloud == true`.
  - Penambahan tombol **"Simpan ke Folder"** yang memanfaatkan pemilihan direktori lokal perangkat via `FilePicker.getDirectoryPath()` untuk menyimpan file langsung ke folder penyimpanan lokal HP.
- **`map_list_screen.dart` ([lib/ui/screens/map_list_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/map_list_screen.dart))**:
  - Tombol "+ Tambah Peta": Jika akun non-anggota web GIMBAL (Google Play Pro / Free), langsung membuka pemilihan file lokal dari memori HP tanpa menampilkan opsi unduh dari repo web GIMBAL.
  - `_openRepoMapsCatalog`: Diberi proteksi hak akses `canAccessGimbalCloud`.
- **`layer_manager_sheet.dart` ([lib/ui/widgets/layer_manager_sheet.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/widgets/layer_manager_sheet.dart))**:
  - Tombol "+ Impor Layer": Jika akun non-anggota web GIMBAL, langsung membuka pemilihan berkas lokal dari memori HP tanpa menampilkan opsi unduh layer dari repo web GIMBAL.

### 3. Pengujian & Kompilasi Rilis APK
- **Unit Test Lisensi ([test/subscription_service_test.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/test/subscription_service_test.dart))**:
  - Menguji penegakan batas Free Tier, pembukaan akses Unlimited Pro pada Google Play Subscription tanpa hak akses cloud web GIMBAL (`canAccessGimbalCloud == false`), serta validitas generator CSV.
  - Seluruh 48/48 tes unit Flutter lulus 100% OK.
- **Kompilasi Rilis APK**:
  - Biner rilis Android APK berhasil dikompilasi ulang: `build/app/outputs/flutter-apk/app-release.apk`.

---

## 38. Standarisasi Identitas Publik "G-Maps", Pembersihan Rujukan Ekosistem Web, & Single-Button Google Sign-In dengan Deteksi Latar Belakang Senyap (02 Oktober 2026)

### 1. Tujuan & Latar Belakang Perubahan
- Mensterilkan antarmuka (UI/UX) aplikasi mobile dari seluruh informasi dan terminologi yang merujuk pada member/anggota webapps GIMBAL, domain internal, maupun API khusus, baik secara **TERSIRAT** maupun **TERSURAT**.
- Memposisikan aplikasi secara murni dan profesional sebagai produk GIS mandiri: **G-Maps** (Geospatial Field Survey & Offline Mapping System).
- Menyederhanakan alur otentikasi: Menghapus input manual email dan opsi server URL. Pengguna hanya disajikan satu tombol resmi: **"Masuk dengan Akun Google"**.
- Menerapkan **Deteksi Latar Belakang Senyap (Silent Background Detection)**: Saat pengguna masuk dengan Akun Google, sistem di balik layar otomatis memeriksa ke backend apakah akun tersebut terdaftar aktif di webapps atau tidak. Jika terdaftar aktif, fitur cloud repository dan ekspedisi terbuka otomatis secara transparan; jika tidak, pengguna tetap masuk secara lokal sebagai akun biasa (Free Tier atau Google Play Pro) tanpa pesan kesalahan kasar.

### 2. Modifikasi Komponen & Layanan Aplikasi
1. **Otentikasi & Layanan API ([lib/services/api_sync_service.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/services/api_sync_service.dart))**:
   - `userName`: Nilai default diubah dari `'Petualang GIMBAL'` menjadi netral `'Pengguna'`.
   - `loginWithGoogle`: Jika akun Google bukan member atau backend tidak terhubung, sistem tidak memunculkan pesan error "Gagal login ke server GIMBAL", melainkan otomatis menyimpan akun Google lokal dengan status `is_active_member = false` dan pesan ramah: `"Akun Google berhasil terhubung."`.
2. **Modal Akun & Status Lisensi ([lib/ui/screens/map_list_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/map_list_screen.dart))**:
   - Subtitle header: Diubah dari `'Khusus anggota berstatus aktif di www.gimbal.my.id'` menjadi netral: `'Kelola lisensi dan profil survei'`.
   - Menghapus box peringatan biru API backend GIMBAL.
   - Menghapus komponen `ExpansionTile` login email manual beserta field input `emailCtrl` dan tombol masuk manual.
   - Menyisakan tombol tunggal: **"Masuk dengan Akun Google"**.
   - Sederhanakan profil terhubung: Menghapus label `'Anggota GIMBAL'` dan nomor registrasi `'NRA: ...'`. Menampilkan Nama, Email, dan badge status netral: `'STATUS: TERVERIFIKASI PRO'`, `'STATUS: GOOGLE PLAY PRO'`, atau `'STATUS: FREE TIER'`.
   - Deskripsi lisensi diubah menjadi istilah cloud netral: *"Akses Penuh: Peta, rute & POI tanpa batas, katalog Cloud Repository, dan Sinkronisasi Cloud."*
   - Opsi Tambah Peta: Mengubah `'Unduh dari Repo Peta GIMBAL'` menjadi `'Unduh dari Cloud Repository'`.
   - Dialog Limit 2 Peta: Mengubah saran menjadi `'1. Masuk dengan Akun Google Pro\n2. Berlangganan Google Play Subscription'`.
3. **Halaman Tentang / About Screen ([lib/ui/screens/about_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/about_screen.dart))**:
   - Judul AppBar: `'Tentang G-Maps'`.
   - Subtitle: `'Geospatial Field Survey & Offline Mapping System'`.
   - Teks Overview: Diperbarui menjadi `'G-Maps adalah aplikasi Sistem Informasi Geografis (GIS) lapangan profesional...'`.
   - Copyright: Diubah menjadi `'© 2026 G-Maps Developer Team. Hak Cipta Dilindungi.'`.
   - Bebas 100% dari informasi webapps secara tersirat maupun tersurat.
4. **Dialog Sinkronisasi Ekspedisi & Layer ([lib/ui/widgets/expedition_sync_dialog.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/widgets/expedition_sync_dialog.dart), [lib/ui/widgets/layer_manager_sheet.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/widgets/layer_manager_sheet.dart), [lib/ui/screens/export_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/export_screen.dart))**:
   - `ExpeditionSyncDialog`: Menghapus opsi manual email dan konfigurasi server URL backend GIMBAL.
   - `LayerManagerSheet`: Mengubah opsi unduh menjadi `'Unduh dari Cloud Layers Repository'` dan deskripsi layer vektor standar.
   - `ExportScreen`: Mengubah label tombol menjadi `'Sinkronkan ke Cloud Ekspedisi'`.
   - `RepoMapsDialog`: Mengubah header menjadi `'Katalog Peta Raster / Tiles'` dan `'Katalog Layer Vektor GIS'`.
5. **Konfigurasi Android & Layanan Ekspor ([android/app/src/main/AndroidManifest.xml](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/android/app/src/main/AndroidManifest.xml), [lib/services/export_import_service.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/services/export_import_service.dart))**:
   - `AndroidManifest.xml`: Label aplikasi pada Android OS launcher diperbarui dari `android:label="GIMBAL-Maps"` menjadi `android:label="G-Maps"`.
   - `ExportImportService`: Generator GeoJSON, header KML, pembuat GPX, dan subject share disesuaikan menjadi `'G-Maps'`.

### 3. Pengujian & Kompilasi Akhir
- **Unit Test Flutter**: Seluruh 48/48 pengujian lulus 100% OK (`flutter test`).
- **Kompilasi Rilis APK**: Berhasil dibangun via `flutter build apk --release` (ukuran biner 25.8 MB) di `build/app/outputs/flutter-apk/app-release.apk`.

## 39. Perbaikan Persistensi Sesi Otentikasi & Pengembalian Akses Sinkronisasi Cloud Ekspedisi bagi Akun Pro (02 Oktober 2026)

### 1. Masalah & Analisis Akar Masalah
- **Pertanyaan Pengguna**: *"kenapa untuk login akun yang terdaftar full pro di web api hilang fitur sync ke webapps?"*
- **Akar Masalah yang Ditemukan**:
  1. **Perpindahan Lokasi Akses**: Pada penyesuaian tata letak sebelumnya, tombol sinkronisasi ekspedisi dipusatkan hanya di dalam dialog Data & Ekspor (`ExportScreen`). Hal ini menyebabkan pengguna yang masuk ke akun Pro tidak menemukan tombol sinkronisasi di halaman muka daftar peta maupun di dalam dialog profil akun Google.
  2. **Ketiadaan Persistensi Sesi Login**: `ApiSyncService` sebelumnya hanya menyimpan sesi login Google di dalam memori RAM (`_currentUser`). Saat aplikasi ditutup (force close) atau dibuka kembali, status login kembali menjadi `null` (Free Tier) sampai pengguna menekan tombol masuk ulang.
  3. **Reaktivitas UI Terlambat**: `SubscriptionService` belum memicu notifikasi perubahan (`refresh()`) secara otomatis saat status `ApiSyncService` berubah pasca proses login/logout.

### 2. Solusi & Perbaikan Komprehensif
1. **Penyimpanan Sesi Permanen ([lib/services/api_sync_service.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/services/api_sync_service.dart))**:
   - Menambahkan method `initialize()` yang memulihkan data sesi akun dari SQLite (`app_settings` via `DatabaseService.instance.getSetting`).
   - Menambahkan method internal `_persistSession()` yang otomatis menyimpan `auth_current_user` dan `auth_token` ke database lokal saat login berhasil, dan menghapusnya saat pengguna menekan Logoff.
   - Mengintegrasikan pemanggilan `SubscriptionService.instance.refresh()` secara otomatis saat sesi berhasil diverifikasi atau di-logoff.
2. **Inisialisasi Awal Aplikasi ([lib/main.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/main.dart))**:
   - Memanggil `await ApiSyncService.instance.initialize();` sebelum `runApp()` agar status akun Pro langsung aktif begitu aplikasi pertama kali dibuka.
3. **Pengembalian Akses Sinkronisasi Langsung ([lib/ui/screens/map_list_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/map_list_screen.dart))**:
   - **Ikon AppBar Langsung**: Jika akun terdeteksi Pro Cloud (`canAccessGimbalCloud == true`), ikon `Icons.cloud_sync` otomatis muncul kembali di AppBar halaman daftar peta dengan tooltip *"Sinkronisasi Ekspedisi (Pro Cloud)"*.
   - **Tombol Pintas di Dialog Profil**: Di dalam modal Akun Google (`_showGoogleAccountModal`), bagi akun terverifikasi Pro, ditambahkan tombol aksi terkemuka berwarna aksen neon: **"Sinkronkan ke Cloud Ekspedisi"** yang langsung memunculkan dialog pemilihan kegiatan dan peta untuk diunggah/diunduh.
   - **Tetap Tersedia di Halaman Ekspor**: Tombol sinkronisasi ekspedisi tetap dapat diakses di dalam dialog Data & Ekspor (`ExportScreen`).
4. **Pembaruan Reaktivitas Lisensi ([lib/services/subscription_service.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/services/subscription_service.dart))**:
   - Menambahkan fungsi `refresh()` yang memicu `notifyListeners()` sehingga seluruh widget di aplikasi (termasuk tombol unduh layer GIS, katalog cloud, dan sinkronisasi) bereaksi instan seketika otentikasi Google berhasil diverifikasi di latar belakang.

## 40. Pemurnian Dialog Login Murni Login/Logoff & Pemusatan Tombol Cloud Sync ke Dialog Data & Ekspor (02 Oktober 2026)

### 1. Tujuan & Penyesuaian Berdasarkan Permintaan Pengguna
- **Permintaan**:
  1. *Dialog login kembalikan seperti semula, pure hanya untuk login/logoff.*
  2. *Pindahkan sync cloud di halaman login ke dialog data & export.*
- **Perubahan yang Diterapkan**:
  1. **Pemurnian Modal Akun Google ([lib/ui/screens/map_list_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/map_list_screen.dart))**:
     - Menghapus tombol *"Sinkronkan ke Cloud Ekspedisi"* dari dalam modal profil Akun Google.
     - Menghapus ikon sinkronisasi dari AppBar beranda `MapListScreen`.
     - Modal Akun Google kini kembali bersih, murni dan fokus hanya untuk: Otentikasi Google (Masuk dengan Akun Google), Logoff, melihat ringkasan status lisensi, dan mengelola toggle langganan Google Play.
  2. **Pemusatan Tombol Sinkronisasi Cloud ke Dialog Data & Ekspor ([lib/ui/screens/export_screen.dart](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-maps/lib/ui/screens/export_screen.dart))**:
     - Menambahkan tombol aksi cepat ikon awan sinkronisasi (`Icons.cloud_sync`) di AppBar dialog Data & Ekspor bagi akun Pro Cloud.
     - Menampilkan tombol aksi terkemuka **"Sinkronkan ke Cloud Ekspedisi"** (`ElevatedButton`) di panel bawah pemilihan format ekspor bagi akun Pro Cloud.
     - Tombol ini langsung memunculkan `ExpeditionSyncDialog` dengan konteks peta aktif, pilihan kegiatan/ekspedisi, dan pemilihan data survei spesifik yang akan diunggah/diunduh.



---

## 41. Migrasi Penuh Database & Aplikasi Web ke Server Baru (10.75.0.16) (02 Oktober 2026)

### 1. Tujuan & Latar Belakang
- Pengguna meminta migrasi menyeluruh database MySQL dan seluruh berkas aplikasi web dari server lama (`10.75.0.51`, Rockchip armv7l) ke server baru yang lebih kencang (**`10.75.0.16`**, Proxmox VE container x86_64, 2GB RAM, 32GB Disk).
- Kredensial server baru: IP `10.75.0.16`, User `root`, Password `R4h4514!?!`.

### 2. Implementasi & Eksekusi Migrasi ([migrate_server.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/migrate_server.py))
1. **Penyedotan Database Lama (`10.75.0.51`)**:
   - Menjalankan `mysqldump` dengan `--add-drop-database` untuk database `gimbal-web` dan menyimpannya ke `/root/gimbal_db_dump.sql`.
   - Mengompresi seluruh isi folder media/berkas anggota `/root/gimbal-web/uploads` ke `/root/gimbal_uploads.tar.gz`.
   - Mengunduh kedua berkas cadangan ke lingkungan lokal via SFTP.
2. **Konfigurasi Server Baru (`10.75.0.16`)**:
   - Memasang server MariaDB, client, Python 3 venv, build tools, dan paket pendukung sistem.
   - Mengimpor penuh dump database `gimbal-web` ke MariaDB lokal server baru.
   - Mengonfigurasi hak akses user database `'gimbal-web'@'localhost'` dan `'gimbal-web'@'%'` dengan password `P4ssw0rd!`.
   - Mentransfer source code webapp terbaru beserta pemulihan struktur folder `uploads/` (`proofs`, `docs`, `gallery`, `avatars`, `maps`, `expeditions`).
   - Membuat virtual environment Python (`/root/gimbal-web/venv`) dan memasang dependensi `requirements.txt`.
   - Mengonfigurasi file `.env` dan unit systemd `/etc/systemd/system/gimbal.service` (Gunicorn 3 workers pada port `8082`).
   - Mengaktifkan dan me-restart service (`systemctl enable --now gimbal.service`).
3. **Penyelarasan Skrip Deploy Lokal ([deploy_remote.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/deploy_remote.py))**:
   - Mengarahkan `SERVER_IP = '10.75.0.16'` dan `PASSWORD = 'R4h4514!?!'`.

---

## 42. Instalasi & Migrasi Cloudflare Tunnel ke Server Baru (10.75.0.16) (02 Oktober 2026)

### 1. Tujuan
- Memasang dan mengonfigurasi Cloudflare Tunnel (`cloudflared`) pada server baru `10.75.0.16` agar domain publik `www.gimbal.my.id` langsung mengarah ke service Gunicorn `http://localhost:8082` di server baru.
- Mengalihkan trafik secara penuh dan menonaktifkan tunnel di server lama (`10.75.0.51`) untuk mencegah split-traffic.

### 2. Implementasi & Eksekusi ([install_cloudflared.py](file:///d:/Projects/My Drive/priv_web_apps/gimbal/gimbal-web/install_cloudflared.py))
1. **Pengambilan Konfigurasi & Token dari Server Lama**:
   - Mengambil token tunnel resmi dari `/etc/cloudflared/token` di `10.75.0.51` (Tunnel ID: `11014862-a294-4389-b50c-936b5f9de836`).
2. **Instalasi Paket Resmi Cloudflare di Server Baru (`10.75.0.16`)**:
   - Mengunduh paket resmi Debian/Ubuntu x86_64: `cloudflared-linux-amd64.deb` rilis terbaru (2026.9.3).
   - Memasang biner `cloudflared` ke `/usr/local/bin/cloudflared`.
   - Membuat direktori terlindungi `/etc/cloudflared` (mode `0700`) dan menyimpan token di `/etc/cloudflared/token` (mode `0600`).
3. **Penyusunan & Pengaktifan Systemd Service**:
   - Membuat unit service `/etc/systemd/system/cloudflared.service`:
     ```ini
     [Unit]
     Description=Cloudflare Tunnel client
     After=network-online.target
     Wants=network-online.target

     [Service]
     TimeoutStartSec=15
     Type=notify
     ExecStart=/usr/local/bin/cloudflared --no-autoupdate tunnel run --token-file /etc/cloudflared/token
     Restart=on-failure
     RestartSec=5s

     [Install]
     WantedBy=multi-user.target
     ```
   - Menjalankan `systemctl daemon-reload` dan `systemctl enable --now cloudflared`.
4. **Verifikasi Koneksi Tunnel**:
   - Layanan `cloudflared` aktif (*Active: active (running)*).
   - Tunnel berhasil mendaftarkan 4 koneksi QUIC aktif ke data center Cloudflare edge (Singapore: `sin12`, `sin15`, `sin19`, `sin21`).
   - Ingress rule otomatis memetakan hostname `www.gimbal.my.id` ke `http://localhost:8082`.
5. **Penonaktifan Tunnel Server Lama**:
   - Menjalankan `systemctl stop cloudflared` dan `systemctl disable cloudflared` pada `10.75.0.51`.
   - Status service pada server lama kini `inactive` dan `disabled`, sehingga 100% trafik kini ditangani server baru `10.75.0.16`.
