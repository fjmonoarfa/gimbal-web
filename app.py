import os
import json
import base64
from datetime import datetime
from flask import (
    Flask, render_template, request,
    redirect, session, send_from_directory,
    jsonify, send_file
)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from models import (
    db, User, Dues, DuesPayment, Activity, ActivityParticipant,
    ActivityFieldLog, GalleryItem, SystemSetting, Position, ChatMessage, MapRepository,
    Sponsor, SponsorProduct,
    AcademyTier, AcademyCourse, AcademyLesson, AcademyQuiz, QuizQuestion, QuizOption,
    UserLessonProgress, UserQuizAttempt, UserCertification, Inquiry
)
from cloudflare_email import sync_cloudflare_email_routing, clean_username_for_alias
from helpers import (
    get_current_user, login_required, admin_required,
    check_member_access, render_gimbal_page,
    render_gimbal_template, render_gimbal_modal
)

# ========== FLASK APP & CORE CONFIGURATION =======================================

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gimbal-adventure-secret-key-2026')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///gimbal.db')
if database_url.startswith('mysql://'):
    database_url = database_url.replace('mysql://', 'mysql+pymysql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Shared session cookie domain for *.gimbal.my.id in production
if 'mysql' in database_url or os.environ.get('SESSION_COOKIE_DOMAIN'):
    app.config['SESSION_COOKIE_DOMAIN'] = os.environ.get('SESSION_COOKIE_DOMAIN', '.gimbal.my.id')

UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(os.path.join(UPLOAD_FOLDER, 'proofs'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'docs'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'gallery'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'posts'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'avatars'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'expeditions'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'sponsors'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'products'), exist_ok=True)

db.init_app(app)

# Flask-Minify Optimization (HTML, CSS, Inline JS Compression)
try:
    from flask_minify import Minify
    Minify(app=app, html=True, js=True, cssless=True, fail_safe=True)
except ImportError:
    pass

@app.before_request
def update_user_last_seen():
    """Memperbarui last_seen pengguna login untuk status online (throttled tiap 60 detik)"""
    try:
        user = get_current_user()
        if user:
            now = datetime.utcnow()
            if not user.last_seen or (now - user.last_seen).total_seconds() > 60:
                user.last_seen = now
                db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

@app.after_request
def apply_htmx_cache_headers(response):
    """
    Menjamin browser (terutama Chrome) tidak menggunakan cache fragment HTMX
    saat user menekan Ctrl+U (View Page Source).
    Dengan Vary: HX-Request, browser selalu membedakan request biasa vs HTMX.
    """
    response.headers['Vary'] = 'HX-Request, HX-Target'
    if request.headers.get('HX-Request'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# ========== DATABASE INITIALIZATION & MIGRATIONS =================================

def init_database_and_defaults():
    """Inisialisasi tabel, migrasi kolom baru, superadmin fitra, dan pengaturan bawaan"""
    with app.app_context():
        db.create_all()
        engine = db.engine
        try:
            with engine.connect() as conn:
                for col, col_type in [
                    ('order_id', 'VARCHAR(64)'),
                    ('snap_token', 'VARCHAR(255)'),
                    ('payment_type', 'VARCHAR(32)'),
                    ('transaction_status', 'VARCHAR(32)')
                ]:
                    try:
                        conn.execute(db.text(f"ALTER TABLE dues_payments ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass
                
                # Migrasi kolom tabel users
                user_cols = [
                    ('jabatan', 'VARCHAR(100)'),
                    ('last_login', 'DATETIME'),
                    ('last_seen', 'DATETIME'),
                    ('gimbal_alias_email', 'VARCHAR(128)'),
                    ('cloudflare_rule_id', 'VARCHAR(64)'),
                    ('cloudflare_status', "VARCHAR(32) DEFAULT 'pending'"),
                    ('is_mandatory_certified', 'BOOLEAN DEFAULT 0'),
                    ('mandatory_tier_id', 'INTEGER')
                ]
                for col, col_type in user_cols:
                    try:
                        conn.execute(db.text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass

                # Migrasi kolom tabel chat_messages (Private Direct Message)
                chat_cols = [
                    ('recipient_id', 'INTEGER'),
                    ('is_read', 'BOOLEAN DEFAULT 0')
                ]
                for col, col_type in chat_cols:
                    try:
                        conn.execute(db.text(f"ALTER TABLE chat_messages ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass

                # Migrasi kolom tabel posts (Tautan ke Ekspedisi, Dokumen, Peta Repo, Sponsor & Jenis Postingan)
                post_cols = [
                    ('activity_id', 'INTEGER'),
                    ('document_id', 'INTEGER'),
                    ('map_repo_id', 'INTEGER'),
                    ('sponsor_id', 'INTEGER'),
                    ('post_type', "VARCHAR(30) DEFAULT 'general'")
                ]
                for col, col_type in post_cols:
                    try:
                        conn.execute(db.text(f"ALTER TABLE posts ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass

                # Migrasi kolom tabel gallery_items (Tautan ke Postingan Lini Masa)
                gallery_cols = [
                    ('post_id', 'INTEGER')
                ]
                for col, col_type in gallery_cols:
                    try:
                        conn.execute(db.text(f"ALTER TABLE gallery_items ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass

                # Migrasi kolom tabel documents (Toggle Share ke Linimasa)
                doc_cols = [
                    ('is_shared_to_timeline', 'BOOLEAN DEFAULT 0')
                ]
                for col, col_type in doc_cols:
                    try:
                        conn.execute(db.text(f"ALTER TABLE documents ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass

                # Migrasi kolom tabel map_repositories (Toggle Share ke Linimasa)
                map_cols = [
                    ('is_shared_to_timeline', 'BOOLEAN DEFAULT 0')
                ]
                for col, col_type in map_cols:
                    try:
                        conn.execute(db.text(f"ALTER TABLE map_repositories ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass

                # Migrasi kolom tabel activities (ROL & Lifecycle & Share Linimasa)
                activity_cols = [
                    ('category', "VARCHAR(80) DEFAULT 'Gunung Hutan'"),
                    ('phase', "VARCHAR(30) DEFAULT 'open'"),
                    ('budget_json', "TEXT DEFAULT '{}'"),
                    ('route_plan', 'TEXT'),
                    ('map_repo_id', 'INTEGER'),
                    ('gear_json', "TEXT DEFAULT '{}'"),
                    ('evaluation_notes', 'TEXT'),
                    ('is_shared_to_timeline', 'BOOLEAN DEFAULT 0')
                ]
                for col, col_type in activity_cols:
                    try:
                        conn.execute(db.text(f"ALTER TABLE activities ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass

                # Migrasi kolom tabel activity_participants (Peran Operasional ROL)
                part_cols = [
                    ('role', "VARCHAR(50) DEFAULT 'Anggota'")
                ]
                for col, col_type in part_cols:
                    try:
                        conn.execute(db.text(f"ALTER TABLE activity_participants ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass

                # Migrasi kolom tabel posts (sponsor_id)
                try:
                    conn.execute(db.text("ALTER TABLE posts ADD COLUMN sponsor_id INT NULL"))
                    conn.commit()
                except Exception:
                    pass

                # Migrasi kolom tabel sponsors (Toggle Share ke Linimasa)
                sponsor_cols = [
                    ('is_shared_to_timeline', 'BOOLEAN DEFAULT 0')
                ]
                for col, col_type in sponsor_cols:
                    try:
                        conn.execute(db.text(f"ALTER TABLE sponsors ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass
        except Exception as e:
            app.logger.warning(f"Column migration check note: {e}")

        # Pastikan Master Jabatan Organisasi terinisialisasi
        if Position.query.count() == 0:
            default_positions = [
                ('Ketua Umum', 'Pengurus Harian', 1, 'Memimpin jalannya roda organisasi dan bertanggung jawab penuh secara internal & eksternal.'),
                ('Wakil Ketua Umum', 'Pengurus Harian', 2, 'Mendampingi Ketua Umum dan mengoordinasikan bidang internal & eksternal.'),
                ('Sekretaris Jenderal', 'Pengurus Harian', 3, 'Bertanggung jawab atas administrasi, kesekretariatan, dan persuratan resmi.'),
                ('Bendahara Umum', 'Pengurus Harian', 4, 'Mengelola sirkulasi keuangan, pembukuan kas, dan verifikasi iuran organisasi.'),
                ('Kepala Divisi Gunung Hutan', 'Divisi Operasional', 5, 'Mengoordinasikan ekspedisi, navigasi darat, jungle survival, dan pendakian gunung.'),
                ('Kepala Divisi Panjat Tebing', 'Divisi Operasional', 6, 'Mengoordinasikan pelatihan rock climbing, vertical rescue, dan wall climbing.'),
                ('Kepala Divisi Susur Gua (Caving)', 'Divisi Operasional', 7, 'Mengoordinasikan eksplorasi speleologi, pemetaan gua, dan single rope technique.'),
                ('Kepala Divisi Arung Jeram (Rafting)', 'Divisi Operasional', 8, 'Mengoordinasikan river running, keselamatan jeram, dan arung sungai.'),
                ('Kepala Divisi Konservasi & LH', 'Divisi Operasional', 9, 'Mengoordinasikan aksi pelestarian alam, reboisasi, dan advokasi lingkungan hidup.'),
                ('Kepala Divisi Humas & Publikasi', 'Divisi Pendukung', 10, 'Mengelola komunikasi media, publikasi kegiatan, dokumentasi, dan relasi mitra.'),
                ('Kepala Divisi Logistik & Alat', 'Divisi Pendukung', 11, 'Mengelola inventaris perlengkapan outdoor, perawatan alat, dan sarana organisasi.'),
                ('Dewan Penasehat Organisasi', 'Dewan Kehormatan', 12, 'Memberikan arahan, pertimbangan, dan pengawasan strategis bagi pengurus.'),
                ('Anggota Penuh (Reguler)', 'Keanggotaan', 13, 'Anggota resmi ber-NRA yang telah menyelesaikan seluruh tahapan pendidikan dasar.'),
                ('Anggota Muda', 'Keanggotaan', 14, 'Calon anggota yang sedang menempuh masa bimbingan dan pemantapan.')
            ]
            for name, cat, order, desc in default_positions:
                p = Position(name=name, category=cat, order_index=order, description=desc, is_active=True)
                db.session.add(p)
            db.session.commit()

        # Inisialisasi akun Superadmin 'fitra' hanya jika belum pernah ditandai dihapus oleh admin
        is_fitra_deleted = SystemSetting.get('fitra_deleted') == 'true'
        if not is_fitra_deleted:
            fitra = User.query.filter((User.email == 'fitra@gimbal.org') | (db.func.lower(User.name) == 'fitra')).first()
            if not fitra:
                fitra = User(
                    email='fitra@gimbal.org',
                    name='Fitra',
                    role='superadmin',
                    jabatan='Sekretaris Jenderal',
                    status='active',
                    nra='R-00-98',
                    phone='08114300001',
                    birth_place='Gorontalo',
                    birth_date='1985-05-15',
                    blood_type='O',
                    address='Basecamp KPAB GIMBAL Gorontalo',
                    medical_history='Tidak Ada',
                    emergency_name='Sekretariat GIMBAL',
                    emergency_relation='Organisasi',
                    emergency_phone='08114300000',
                    avatar='/static/pics/cartoon/avatar_sekjen.jpg',
                    password_hash='P4ssw0rd!?!'
                )
                db.session.add(fitra)
                db.session.commit()
            else:
                if not fitra.role:
                    fitra.role = 'superadmin'
                if not fitra.status:
                    fitra.status = 'active'
                if not fitra.jabatan:
                    fitra.jabatan = 'Sekretaris Jenderal'
                db.session.commit()

        # Pastikan akun kepengurusan bawaan memiliki jabatan jika belum disetel
        admin_user = User.query.filter_by(email='admin@gimbal.org').first()
        if admin_user and not admin_user.jabatan:
            admin_user.jabatan = 'Ketua Umum'
            db.session.commit()

        budi_user = User.query.filter_by(email='budi.pendaki@gmail.com').first()
        if budi_user and not budi_user.jabatan:
            budi_user.jabatan = 'Bendahara Umum'
            db.session.commit()

        # Inisialisasi pengaturan sistem jika belum ada
        if not SystemSetting.query.filter_by(key='monthly_dues_amount').first():
            SystemSetting.set('monthly_dues_amount', '15000')
        if not SystemSetting.query.filter_by(key='midtrans_is_production').first():
            SystemSetting.set('midtrans_is_production', 'false')
        if not SystemSetting.query.filter_by(key='midtrans_client_key').first():
            SystemSetting.set('midtrans_client_key', 'SB-Mid-client-demo12345678')
        if not SystemSetting.query.filter_by(key='midtrans_server_key').first():
            SystemSetting.set('midtrans_server_key', 'SB-Mid-server-demo12345678')
        if not SystemSetting.query.filter_by(key='midtrans_merchant_id').first():
            SystemSetting.set('midtrans_merchant_id', 'G123456789')

        # Rekening resmi organisasi bawaan
        if not SystemSetting.query.filter_by(key='bank_primary_name').first():
            SystemSetting.set('bank_primary_name', 'Bank Mandiri')
        if not SystemSetting.query.filter_by(key='bank_primary_number').first():
            SystemSetting.set('bank_primary_number', '131-00-1829-3321')
        if not SystemSetting.query.filter_by(key='bank_primary_holder').first():
            SystemSetting.set('bank_primary_holder', 'KPAB GIMBAL KAS PUSAT')
        if not SystemSetting.query.filter_by(key='bank_secondary_name').first():
            SystemSetting.set('bank_secondary_name', 'Bank BCA')
        if not SystemSetting.query.filter_by(key='bank_secondary_number').first():
            SystemSetting.set('bank_secondary_number', '593-019-4821')
        if not SystemSetting.query.filter_by(key='bank_secondary_holder').first():
            SystemSetting.set('bank_secondary_holder', 'KPAB GIMBAL KAS PUSAT')

        # Profil organisasi & tema bawaan
        if not SystemSetting.query.filter_by(key='theme_color').first():
            SystemSetting.set('theme_color', 'orange')
        if not SystemSetting.query.filter_by(key='site_width').first():
            SystemSetting.set('site_width', '85%')
        if not SystemSetting.query.filter_by(key='org_name').first():
            SystemSetting.set('org_name', 'KPAB GIMBAL Provinsi Gorontalo')
        if not SystemSetting.query.filter_by(key='org_phone').first():
            SystemSetting.set('org_phone', '+62 812-3456-7890')
        if not SystemSetting.query.filter_by(key='org_email').first():
            SystemSetting.set('org_email', 'sekretariat@gimbal.org')
        if not SystemSetting.query.filter_by(key='org_address').first():
            SystemSetting.set('org_address', 'Jl. Pangeran Hidayat No. 45, Kota Gorontalo')

        # Pengaturan Cloudflare Email Routing (@gimbal.my.id)
        if not SystemSetting.query.filter_by(key='cloudflare_enabled').first():
            SystemSetting.set('cloudflare_enabled', 'false', 'Aktifkan otomatisasi Cloudflare Email Routing API')
        if not SystemSetting.query.filter_by(key='cloudflare_api_token').first():
            SystemSetting.set('cloudflare_api_token', '', 'API Token Cloudflare dengan izin Zone.Email Routing')
        if not SystemSetting.query.filter_by(key='cloudflare_zone_id').first():
            SystemSetting.set('cloudflare_zone_id', '', 'Zone ID domain gimbal.my.id di Cloudflare')
        if not SystemSetting.query.filter_by(key='cloudflare_domain').first():
            SystemSetting.set('cloudflare_domain', 'gimbal.my.id', 'Domain organisasi untuk email forwarding')

        # Sinkronkan tarif iuran bulanan default jika belum ada master iuran sama sekali
        if Dues.query.count() == 0:
            d = Dues(
                title='Iuran Bulanan Anggota',
                amount=float(SystemSetting.get('monthly_dues_amount', '15000')),
                category='wajib',
                description='Iuran kas rutin bulanan keanggotaan KPAB GIMBAL Gorontalo',
                is_active=True
            )
            db.session.add(d)
            db.session.commit()

        # Inisialisasi Kurikulum & SOP Akademi jika masih kosong
        if AcademyTier.query.count() == 0:
            # Level 1: Calon Anggota & Diksar
            t1 = AcademyTier(
                name='Level 1 - Tingkat Dasar (Calon Anggota & Diksar)',
                slug='level-1-dasar',
                badge_name='Brevet Kesiapan Rimba & SAR Dasar',
                badge_icon='fa-shield-halved',
                badge_color='#10b981',
                order_index=1,
                passing_grade=75,
                description='Kualifikasi wajib bagi seluruh calon anggota dan anggota muda KPAB GIMBAL untuk memastikan kesiapan fisik, mental, etika rimba, dan standar keselamatan operasional sebelum diterjunkan ke lapangan.'
            )
            db.session.add(t1)
            db.session.flush()

            c1_1 = AcademyCourse(
                tier_id=t1.id,
                title='SOP Packing & Perlengkapan Lapangan (Carrier & Layering)',
                category='diksar',
                description='Tata cara menyusun beban ransel, distribusi gravitasi carrier, perlindungan anti-air, serta sistem pakaian tiga lapis penangkal cuaca ekstrem.',
                order_index=1,
                target_duration_mins=25
            )
            c1_2 = AcademyCourse(
                tier_id=t1.id,
                title='Pertolongan Pertama Gawat Darurat (PPGD) & Anti-Hipotermia',
                category='ppgd',
                description='Protokol penanganan darurat hipotermia akut di pegunungan, pembalutan luka fraktur/dislokasi, dan evakuasi mandiri.',
                order_index=2,
                target_duration_mins=35
            )
            c1_3 = AcademyCourse(
                tier_id=t1.id,
                title='Dasar Navigasi Darat (Peta Topografi & Kompas Prisma)',
                category='navigasi',
                description='Membaca morfologi garis kontur, menghitung interval kontur peta RBI, serta teknik bidik kompas resection dan intersection.',
                order_index=3,
                target_duration_mins=30
            )
            db.session.add_all([c1_1, c1_2, c1_3])
            db.session.flush()

            # Lessons Level 1
            l1_1_1 = AcademyLesson(
                course_id=c1_1.id,
                title='Prinsip ABC Packing & Manajemen Titik Berat Ransel',
                content_type='article',
                content_body="""### Prinsip Dasar Packing Ransel Petualang (Prinsip ABC)
Dalam penjelajahan rimba dan gunung lebat tropis, carrier bukan sekadar wadah pembawa barang, melainkan penopang keselamatan fisik tulang belakang anggota.

#### 1. Aturan ABC Packing:
- **A - Accessibility (Kemudahan Akses):** Letakkan peralatan darurat yang sewaktu-waktu dibutuhkan (Jas hujan ponco, P3K, survival kit, senter/headlamp) di kantong atas (*top lid*) atau bagian yang paling mudah dijangkau tanpa membongkar ransel.
- **B - Balance (Keseimbangan):** Pastikan beban kiri dan kanan seimbang sempurna. Carrier yang berat sebelah akan menguras energi otot dan berisiko fatal terpeleset di igir jurang.
- **C - Compactness (Kerapatan & Kekompakan):** Manfaatkan setiap rongga kosong. Masukkan kaus kaki atau nesting ke dalam ruang kosong sepatu cadangan atau panci. Hindari menggantung nesting, matras, atau sandal di luar carrier karena rawan tersangkut duri rotan hutan basah.

#### 2. Distribusi Titik Berat Gravitasi:
- **Bagian Bawah:** Barang ringan namun bervolume besar (Sleeping bag, pakaian tidur kering, matras tiup).
- **Bagian Tengah Menempel ke Punggung:** Barang paling berat (Bahan makanan kaleng/beras, air cadangan, tenda/flysheet, kompor/gas).
- **Bagian Atas & Luar:** Barang berbobot sedang (Pakaian ganti, jaket isolasi, piring makan).

#### 3. Waterproofing Wajib:
Gunakan **trash bag tebal (polyethylene)** sebagai pelapis dalam (*inner liner*) carrier sebelum memasukkan barang apapun. Jangan hanya mengandalkan rain cover luar!""",
                order_index=1
            )
            l1_1_2 = AcademyLesson(
                course_id=c1_1.id,
                title='Sistem Tiga Lapis Pakaian (3-Layering System) Mencegah Hipotermia',
                content_type='article',
                content_body="""### Sistem Pakaian Tiga Lapis (Layering System)
Di hutan tropis pegunungan seperti Tilongkabila dan Batusinggo, ancaman pembunuh nomor satu bukanlah satwa liar, melainkan **Hipotermia** akibat angin dingin dan pakaian basah.

#### Layer 1: Base Layer (Pengatur Kelembapan Kulit)
- **Fungsi:** Mengalirkan keringat menjauh dari kulit (*moisture wicking*) agar badan tetap kering.
- **Bahan Wajib:** Polyester, nylon teknis, atau wol merino.
- **PANTANGAN MUTLAK:** Dilarang keras memakai kaos katun dan celana jeans denim tebal! Katun menyerap air hingga 27 kali lipat bobotnya dan menahan dingin ke kulit (*cotton kills*).

#### Layer 2: Mid Layer (Penjaga Suhu Panas Tubuh / Insulation)
- **Fungsi:** Memerangkap udara hangat yang dihasilkan oleh radiasi tubuh.
- **Bahan:** Jaket fleece (polar), jaket bulu angsa (*down jacket*), atau jaket sintetis primaloft.

#### Layer 3: Outer Layer (Pelindung Angin & Badai / Hardshell)
- **Fungsi:** Menahan terpaan angin badai kencang (*windproof*) dan guyuran hujan lebat (*waterproof*).
- **Bahan:** Jaket membran waterproof (Gore-Tex, Taslan coating) dengan ventilasi ketiak (*pit zips*).""",
                order_index=2
            )
            l1_2_1 = AcademyLesson(
                course_id=c1_2.id,
                title='SOP Penanganan Hipotermia Akut di Ketinggian (Burrito Wrap Protocol)',
                content_type='article',
                content_body="""### Protokol Tanggap Darurat Hipotermia KPAB GIMBAL
Hipotermia terjadi saat suhu inti tubuh manusia turun di bawah 35°C.

#### Tahapan & Gejala:
1. **Ringan (35°C - 32°C):** Menggigil tak terkendali, bicara terbata-bata (*mumbles*), koordinasi tangan kaku (*fumbles*), langkah kaki tersandung (*stumbles*).
2. **Sedang - Berat (< 32°C):** Berhenti menggigil, delirium/halusinasi, tindakan membuka baju karena rasa panas semu (*paradoxical undressing*), penurunan kesadaran hingga koma.

#### Langkah Penyelamatan Cepat (Golden Rules):
1. **Cegah Kehilangan Panas Lanjutan:**
   - Segera bawa korban masuk ke dalam tenda darurat terlindung dari terpaan angin.
   - Ganti seluruh pakaian basah dengan pakaian kering tebal.
2. **Isolasi dari Tanah:**
   - Jangan letakkan korban langsung di atas tanah dingin. Alasi dengan minimal 2 lapis matras busa atau foil thermal blanket.
3. **Teknik Bungkusan Burrito (Burrito Wrap):**
   - Masukkan korban ke dalam sleeping bag hangat.
   - Tempelkan botol air hangat (yang dibungkus kaos kaki tebal) pada area titik nadi besar tubuh: **Ketiak (*axilla*), pangkal paha (*groin*), dan leher**.
   - JANGAN menggosok atau memijat kaki/tangan korban karena dapat memompa darah dingin asam dari ujung kaki kembali ke jantung yang memicu henti jantung (*cardiac arrest*).
4. **Rehidrasi Hangat Manis:**
   - Jika korban masih sadar penuh dan dapat menelan, berikan minuman hangat bergula tinggi (teh manis, jahe manis).""",
                order_index=1
            )
            l1_2_2 = AcademyLesson(
                course_id=c1_2.id,
                title='Penanganan Fraktur, Dislokasi & Pemasangan Bidai Darurat',
                content_type='article',
                content_body="""### Bidai Darurat & Penanganan Cedera Tulang
Ketika anggota mengalami patah tulang (*fraktur*) atau dislokasi sendi di lokasi yang jauh dari fasilitas medis:

#### 1. Prinsip Pembidaian (Splinting):
- Bidai harus mencakup **dua sendi**, yaitu satu sendi di atas patahan tulang dan satu sendi di bawahnya.
- Jangan pernah mencoba meluruskan atau memaksa mendorong tulang yang mencuat keluar (*open fracture*). Tutup dengan kassa steril yang dibasahi larutan antiseptik/infus.
- Periksa denyut nadi distal, sensasi rasa, dan sirkulasi jari (*capillary refill time*) sebelum dan sesudah bidai dipasang.

#### 2. Material Alam & Alat Petualang yang Dapat Dijadikan Bidai:
- Trekking pole (tongkat pendaki) yang diatur panjangnya.
- Dahan kayu atau bilah bambu lurus yang dilapisi busa matras.
- Gulungan matras spons tebal dilipat membentuk huruf U menopang kaki.
- Ikat bidai menggunakan kain mitella segitiga atau potongan webbing tubular.""",
                order_index=2
            )
            l1_3_1 = AcademyLesson(
                course_id=c1_3.id,
                title='Membaca Garis Kontur, Interval Ketinggian & Morfologi Medan',
                content_type='article',
                content_body="""### Membaca Peta Topografi Rupa Bumi Indonesia (RBI)
Peta topografi menggambarkan relief permukaan bumi 3 dimensi ke atas lembaran kertas 2 dimensi menggunakan garis kontur (*contour lines*).

#### 1. Sifat-Sifat Garis Kontur:
- Garis kontur menghubungkan titik-titik yang memiliki ketinggian sama di atas permukaan laut.
- Garis kontur tidak pernah saling berpotongan atau bercabang.
- **Renggang:** Menunjukkan lereng landai (*gentle slope*).
- **Rapat:** Menunjukkan lereng curam atau tebing terjal (*cliff*).

#### 2. Menghitung Interval Kontur (IK):
Rumus standar peta topografi geospasial:
IK = 1 / 2000 x Skala Peta
- Peta skala 1 : 25.000 memiliki Interval Kontur = 25.000 / 2.000 = 12.5 meter.
- Peta skala 1 : 50.000 memiliki Interval Kontur = 50.000 / 2.000 = 25 meter.

#### 3. Morfologi Bentang Alam:
- **Punggungan (Ridge):** Garis kontur berbentuk huruf V atau U yang ujung lancipnya menunjuk ke arah ketinggian yang lebih rendah.
- **Lembahan / Alur Sungai (Valley):** Garis kontur berbentuk V yang ujung lancipnya menunjuk ke arah ketinggian yang lebih tinggi.""",
                order_index=1
            )
            l1_3_2 = AcademyLesson(
                course_id=c1_3.id,
                title='Teknik Resection & Intersection Menggunakan Kompas Bidik Prisma',
                content_type='article',
                content_body="""### Orientasi Lapangan: Resection & Intersection

#### 1. Resection (Menentukan Posisi Kita di Peta):
Teknik untuk mengetahui koordinat posisi kita sendiri saat tersesat di lapangan dengan membidik minimal 2 tanda medan yang dikenal:
1. Bidik tanda medan A yang mencolok (misal: puncak gunung yang diketahui di peta), catat sudut bidikan kompas (Azimuth A).
2. Hitung **Back-Azimuth (Sudut Balik)**:
   - Jika sudut < 180°: tambahkan 180°
   - Jika sudut > 180°: kurangkan 180°
3. Tarik garis lurus sudut balik dari tanda medan A pada peta.
4. Bidik tanda medan B (misal: tanjung atau puncak kedua), hitung sudut baliknya, dan tarik garis kedua di peta.
5. **Titik temu perpotongan kedua garis** tersebut adalah posisi kita berdiri di atas peta.

#### 2. Intersection (Menentukan Posisi Sasaran Jauh):
Teknik untuk mengetahui posisi koordinat objek yang tidak terjangkau (misal: titik asap atau korban yang terlihat di lereng seberang) dengan mengamati objek tersebut dari dua titik berbeda yang koordinatnya telah kita ketahui di peta.""",
                order_index=2
            )
            db.session.add_all([l1_1_1, l1_1_2, l1_2_1, l1_2_2, l1_3_1, l1_3_2])
            db.session.flush()

            # Quiz Tier 1
            q1 = AcademyQuiz(
                tier_id=t1.id,
                title='Ujian Sertifikasi Kesiapan Rimba & SAR Dasar (Level 1)',
                description='Evaluasi komprehensif uji kompetensi packing ransel, penanganan medis darurat, anti-hipotermia, dan navigasi peta kompas. Syarat mutlak kelulusan Diksar KPAB GIMBAL.',
                passing_score=75,
                time_limit_mins=15,
                is_active=True
            )
            db.session.add(q1)
            db.session.flush()

            # Questions Level 1
            qq1 = QuizQuestion(
                quiz_id=q1.id,
                question_text='Menurut kaidah ABC Packing ransel ekspedisi, di manakah letak ideal perlengkapan berat seperti beras, tenda basah, dan air cadangan?',
                points=15,
                order_index=1,
                explanation='Beban berat wajib diletakkan di bagian tengah sedekat mungkin dengan punggung dan di atas pinggul agar pusat gravitasi sejajar dengan tulang belakang.'
            )
            db.session.add(qq1)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq1.id, option_text='Di bagian dasar ransel paling bawah', is_correct=False, order_index=1),
                QuizOption(question_id=qq1.id, option_text='Di bagian tengah menempel sedekat mungkin ke punggung', is_correct=True, order_index=2),
                QuizOption(question_id=qq1.id, option_text='Di kantong atas (top lid) carrier', is_correct=False, order_index=3),
                QuizOption(question_id=qq1.id, option_text='Digantung di luar sisi kiri carrier', is_correct=False, order_index=4)
            ])

            qq2 = QuizQuestion(
                quiz_id=q1.id,
                question_text='Mengapa pakaian berbahan katun (seperti kaos katun biasa dan celana jeans) sangat dilarang digunakan saat mendaki gunung berhawa dingin?',
                points=15,
                order_index=2,
                explanation='Katun menahan air dan keringat sangat lama dan kehilangan daya isolasi saat basah, menyebabkan hilangnya panas tubuh secara drastis (cotton kills).'
            )
            db.session.add(qq2)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq2.id, option_text='Karena katun mudah terbakar saat didekatkan ke api unggun', is_correct=False, order_index=1),
                QuizOption(question_id=qq2.id, option_text='Karena katun menyerap keringat/air lama dan mengalirkan dingin ke tubuh memicu hipotermia', is_correct=True, order_index=2),
                QuizOption(question_id=qq2.id, option_text='Karena serat katun mudah dimakan serangga hutan tropis', is_correct=False, order_index=3),
                QuizOption(question_id=qq2.id, option_text='Karena katun membuat warna pakaian cepat memudar di bawah terik matahari', is_correct=False, order_index=4)
            ])

            qq3 = QuizQuestion(
                quiz_id=q1.id,
                question_text='Tindakan apa yang PALING BERBAHAYA dan HARUS DIHINDARI saat menangani korban hipotermia berat?',
                points=20,
                order_index=3,
                explanation='Menggosok atau merendam kaki/tangan korban dapat memicu afterdrop dan memompa darah asam/dingin kembali ke organ vital jantung yang menyebabkan ventrikel fibrilasi atau henti jantung mendadak.'
            )
            db.session.add(qq3)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq3.id, option_text='Mengganti pakaian basah korban dengan pakaian kering di dalam tenda', is_correct=False, order_index=1),
                QuizOption(question_id=qq3.id, option_text='Menggosok keras tangan dan kaki korban atau memaksa merendamnya di air panas mendadak', is_correct=True, order_index=2),
                QuizOption(question_id=qq3.id, option_text='Menaruh botol air hangat di ketiak dan pangkal paha korban', is_correct=False, order_index=3),
                QuizOption(question_id=qq3.id, option_text='Membungkus korban dengan matras dan kantung tidur (burrito wrap)', is_correct=False, order_index=4)
            ])

            qq4 = QuizQuestion(
                quiz_id=q1.id,
                question_text='Pada peta topografi Rupa Bumi Indonesia (RBI) dengan skala 1 : 25.000, berapakah nilai Interval Kontur (IK) antar garis kontur?',
                points=15,
                order_index=4,
                explanation='IK dihitung dengan rumus 1/2000 x Skala = 25.000 / 2.000 = 12.5 meter.'
            )
            db.session.add(qq4)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq4.id, option_text='50 meter', is_correct=False, order_index=1),
                QuizOption(question_id=qq4.id, option_text='25 meter', is_correct=False, order_index=2),
                QuizOption(question_id=qq4.id, option_text='12.5 meter', is_correct=True, order_index=3),
                QuizOption(question_id=qq4.id, option_text='10 meter', is_correct=False, order_index=4)
            ])

            qq5 = QuizQuestion(
                quiz_id=q1.id,
                question_text='Jika Anda membidik puncak Gunung Tilongkabila dengan kompas bidik prisma dan memperoleh sudut Azimuth 40°, berapakah sudut Back-Azimuth (sudut balik)-nya?',
                points=20,
                order_index=5,
                explanation='Karena sudut bidik awal 40° (< 180°), maka Back-Azimuth dihitung dengan menambahkan 180°: 40° + 180° = 220°.'
            )
            db.session.add(qq5)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq5.id, option_text='140°', is_correct=False, order_index=1),
                QuizOption(question_id=qq5.id, option_text='220°', is_correct=True, order_index=2),
                QuizOption(question_id=qq5.id, option_text='320°', is_correct=False, order_index=3),
                QuizOption(question_id=qq5.id, option_text='200°', is_correct=False, order_index=4)
            ])

            qq6 = QuizQuestion(
                quiz_id=q1.id,
                question_text='Manakah dari tanda berikut yang mencirikan bentang alam "Punggungan" (Ridge) pada peta topografi kontur?',
                points=15,
                order_index=6,
                explanation='Punggungan dicirikan dengan garis kontur berbentuk huruf V atau U yang ujung lengkungannya menunjuk ke arah ketinggian yang lebih rendah (menuruni bukit).'
            )
            db.session.add(qq6)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq6.id, option_text='Bentuk garis kontur U atau V yang ujung lancipnya menunjuk ke arah ketinggian lebih rendah', is_correct=True, order_index=1),
                QuizOption(question_id=qq6.id, option_text='Bentuk garis kontur V yang ujungnya menunjuk ke arah ketinggian lebih tinggi', is_correct=False, order_index=2),
                QuizOption(question_id=qq6.id, option_text='Garis kontur yang membentuk lingkaran tertutup dengan garis bergerigi ke dalam', is_correct=False, order_index=3),
                QuizOption(question_id=qq6.id, option_text='Garis kontur yang lurus sejajar tanpa kelokan', is_correct=False, order_index=4)
            ])

            # Level 2: Pra-Penuh (Lanjutan)
            t2 = AcademyTier(
                name='Level 2 - Tingkat Lanjutan (Menuju Anggota Penuh)',
                slug='level-2-lanjutan',
                badge_name='Brevet Navigator Rimba & Survival Lapangan',
                badge_icon='fa-mountain-sun',
                badge_color='#3b82f6',
                order_index=2,
                passing_grade=80,
                description='Kualifikasi penjelajahan mandiri rimba lebat, penguasaan peta digital GeoPDF Avenza, teknik bertahan hidup tanpa logistik (survival), serta Search and Rescue (ESAR) jalur terisolasi.'
            )
            db.session.add(t2)
            db.session.flush()

            c2_1 = AcademyCourse(
                tier_id=t2.id,
                title='Navigasi Digital & GeoPDF Studio Lapangan',
                category='navigasi',
                description='Integrasi peta topografi GeoPDF resolusi tinggi di smartphone dengan aplikasi Avenza Maps secara offline tanpa sinyal internet.',
                order_index=1,
                target_duration_mins=30
            )
            c2_2 = AcademyCourse(
                tier_id=t2.id,
                title='Jungle Survival & Shelter Darurat Hutan Tropis',
                category='survival',
                description='Teknik mencari sumber air murni di alam, identifikasi flora konsumsi hutan Sulawesi/Gorontalo, serta shelter bivak cepat tanggap badai.',
                order_index=2,
                target_duration_mins=40
            )
            db.session.add_all([c2_1, c2_2])
            db.session.flush()

            l2_1 = AcademyLesson(
                course_id=c2_1.id,
                title='Pemanfaatan Peta Topografi GeoPDF Offline di Avenza Maps',
                content_type='article',
                content_body="""### Navigasi Geospatial Offline dengan GeoPDF
KPAB GIMBAL memfasilitasi setiap anggota dengan generator peta cetak & digital standar ISO 32000 melalui GeoPDF Studio (mapgen.gimbal.my.id).

#### 1. Keunggulan Format GeoPDF:
- Mengandung metadata spasial georeferensi langsung (*geotagged projection*) di dalam berkas PDF.
- Dapat dibuka langsung di aplikasi smartphone (Avenza Maps) tanpa membutuhkan koneksi internet atau sinyal seluler.
- GPS internal smartphone akan menampilkan titik biru posisi anggota secara akurat di atas garis kontur peta resolusi tinggi 300 DPI.

#### 2. Prosedur Lapangan:
1. Unduh berkas GeoPDF dari Studio Peta GIMBAL sebelum ekspedisi dimulai.
2. Impor berkas ke Avenza Maps saat masih berada di Basecamp berfasilitas WiFi.
3. Aktifkan GPS smartphone saat berada di titik awal (*starting point*).""",
                order_index=1
            )
            l2_2 = AcademyLesson(
                course_id=c2_2.id,
                title='Sumber Air Darurat & Tumbuhan Konsumsi Hutan Basah',
                content_type='article',
                content_body="""### Jungle Survival: Water & Food Procurement

#### 1. Sumber Air Bersih Darurat:
- **Rotan Air (*Calamus sp.*):** Potong batang rotan miring pada bagian atas terlebih dahulu, kemudian potong bagian bawah dekat akar. Air yang menetes jernih dan dapat langsung diminum tanpa dimasak.
- **Pohon Pisang Hutan:** Tebang pohon pisang liar setinggi 30 cm dari tanah, buat cekungan di tengah tunggul, buang getah pahit lapis pertama, biarkan terisi air bersih dalam 15-30 menit.
- **Kondensasi Embun Tumbuhan:** Bungkus daun lebat menggunakan kantong plastik bening transparan di bawah sinar matahari.

#### 2. Aturan Uji Makanan Tumbuhan Liar (Universal Edibility Test):
1. Jangan memakan jamur liar berpayung dengan cincin di batangnya.
2. Hindari getah putih kental seperti susu (kecuali nangka/ficus yang telah teruji).
3. Gosokkan sedikit getah daun pada punggung tangan dan bibir, tunggu 15 menit. Jika timbul rasa terbakar, gatal, atau mati rasa, jangan dikonsumsi!""",
                order_index=1
            )
            db.session.add_all([l2_1, l2_2])
            db.session.flush()

            # Quiz Tier 2
            q2 = AcademyQuiz(
                tier_id=t2.id,
                title='Ujian Kualifikasi Navigator Rimba & Survival Lapangan (Level 2)',
                description='Uji kompetensi navigasi digital GPS/GeoPDF, penentuan posisi koordinat UTM, manajemen air darurat, dan survival rimba.',
                passing_score=80,
                time_limit_mins=20,
                is_active=True
            )
            db.session.add(q2)
            db.session.flush()

            qq2_1 = QuizQuestion(
                quiz_id=q2.id,
                question_text='Bagaimana cara yang benar memotong batang tanaman rotan di hutan tropis agar mengeluarkan air minum darurat jernih?',
                points=25,
                order_index=1,
                explanation='Potong bagian atas terlebih dahulu agar udara masuk membuka tarikan gravitasi kapiler, kemudian potong bagian bawah.'
            )
            db.session.add(qq2_1)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq2_1.id, option_text='Potong bagian atas terlebih dahulu baru potong bagian bawah dekat akar', is_correct=True, order_index=1),
                QuizOption(question_id=qq2_1.id, option_text='Potong langsung dari akarnya tanpa memotong atas', is_correct=False, order_index=2),
                QuizOption(question_id=qq2_1.id, option_text='Bakar batang rotan dengan api unggun terlebih dahulu', is_correct=False, order_index=3),
                QuizOption(question_id=qq2_1.id, option_text='Kupas kulit luar rotan kemudian remas serabutnya', is_correct=False, order_index=4)
            ])

            qq2_2 = QuizQuestion(
                quiz_id=q2.id,
                question_text='Apa keistimewaan utama dokumen peta berformat GeoPDF (ISO 32000) dibanding format gambar JPEG/PNG biasa saat digunakan di lapangan?',
                points=25,
                order_index=2,
                explanation='GeoPDF menyimpan metadata koordinat proyeksi peta secara tertanam sehingga GPS smartphone dapat langsung memetakan posisi tanpa sinyal internet di aplikasi seperti Avenza Maps.'
            )
            db.session.add(qq2_2)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq2_2.id, option_text='Ukurannya selalu lebih kecil dari 10 Kilobyte', is_correct=False, order_index=1),
                QuizOption(question_id=qq2_2.id, option_text='Memiliki metadata spasial terkalibrasi sehingga posisi GPS muncul akurat di Avenza Maps tanpa sinyal seluler', is_correct=True, order_index=2),
                QuizOption(question_id=qq2_2.id, option_text='Dapat menyala sendiri dalam kondisi gelap gulita', is_correct=False, order_index=3),
                QuizOption(question_id=qq2_2.id, option_text='Tidak bisa dibuka di komputer biasa', is_correct=False, order_index=4)
            ])

            qq2_3 = QuizQuestion(
                quiz_id=q2.id,
                question_text='Jika seorang petualang tersesat dan kehabisan air namun menemukan tanaman dengan getah putih pekat seperti susu dan berbau almond pahit, apa tindakannya?',
                points=25,
                order_index=3,
                explanation='Getah putih susu dan bau almond pahit pada tanaman liar umumnya mengindikasikan senyawa alkaloid beracun atau asam hidrosianat yang sangat mematikan.'
            )
            db.session.add(qq2_3)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq2_3.id, option_text='Dilarang keras dikonsumsi karena indikasi kuat mengandung racun sianida/alkaloid', is_correct=True, order_index=1),
                QuizOption(question_id=qq2_3.id, option_text='Dapat langsung diminum karena getah putih kaya akan protein nabati', is_correct=False, order_index=2),
                QuizOption(question_id=qq2_3.id, option_text='Direbus selama 2 menit lalu diminum', is_correct=False, order_index=3),
                QuizOption(question_id=qq2_3.id, option_text='Diteteskan ke mata sebagai obat penahan kantuk', is_correct=False, order_index=4)
            ])

            qq2_4 = QuizQuestion(
                quiz_id=q2.id,
                question_text='Pada metode pencarian korban tersesat (ESAR), teknik sapuan jalur terkoordinasi berjarak seragam dengan panduan kompas disebut metode apa?',
                points=25,
                order_index=4,
                explanation='Line Search (Sweep Search) adalah teknik pencarian sistematis di mana personil berjajar dengan interval jarak terukur menyapu area medan.'
            )
            db.session.add(qq2_4)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq2_4.id, option_text='Line Sweep Search (Sapuan Garis Berbanjar)', is_correct=True, order_index=1),
                QuizOption(question_id=qq2_4.id, option_text='Random Roaming (Pencarian Acak Bebas)', is_correct=False, order_index=2),
                QuizOption(question_id=qq2_4.id, option_text='Bivouac Waiting (Menunggu di Bivak)', is_correct=False, order_index=3),
                QuizOption(question_id=qq2_4.id, option_text='Helicopter Hoist', is_correct=False, order_index=4)
            ])

            # Level 3: Senior (Komandan Lapangan & Instruktur)
            t3 = AcademyTier(
                name='Level 3 - Tingkat Senior (Komandan Lapangan & Instruktur)',
                slug='level-3-senior',
                badge_name='Wing Komandan Ekspedisi & Master Rescue',
                badge_icon='fa-award',
                badge_color='#f59e0b',
                order_index=3,
                passing_grade=85,
                description='Kualifikasi tertinggi keanggotaan KPAB GIMBAL untuk memimpin operasi ekspedisi skala besar, Incident Command System (ICS), analisis risiko RAMS, dan evakuasi tebing terjal (Vertical Rescue).'
            )
            db.session.add(t3)
            db.session.flush()

            c3_1 = AcademyCourse(
                tier_id=t3.id,
                title='Incident Command System (ICS) & Manajemen Risiko RAMS',
                category='manajemen',
                description='Manajemen komando darurat lapangan, alur komunikasi posko pangkalan, serta matriks keputusan Go / No-Go ekspedisi.',
                order_index=1,
                target_duration_mins=45
            )
            c3_2 = AcademyCourse(
                tier_id=t3.id,
                title='Vertical Rescue & Mechanical Advantage (Sistem Katrol)',
                category='vertical',
                description='Teknik evakuasi tebing curam, pembuatan multiple equalized anchors, dan sistem hauling 3:1 Z-Rig.',
                order_index=2,
                target_duration_mins=45
            )
            db.session.add_all([c3_1, c3_2])
            db.session.flush()

            l3_1 = AcademyLesson(
                course_id=c3_1.id,
                title='Struktur Komando Posko ICS & Matriks Keputusan RAMS',
                content_type='article',
                content_body="""### Incident Command System (ICS) & Analisis Risiko Ekspedisi
Sebagai Komandan Lapangan (*Incident Commander*), keselamatan seluruh personel regu berada di pundak Anda.

#### 1. Struktur Komando Dasar:
- **Incident Commander (IC):** Pemegang komando tertinggi yang mengambil keputusan taktis dan Go / No-Go.
- **Safety Officer:** Bertanggung jawab memantau faktor bahaya cuaca, kestabilan tebing, dan kelelahan fisik anggota regu. Berhak menghentikan operasi secara sepihak jika ancaman bahaya jiwa muncul.
- **Operations Section:** Regu pelaksana di medan lapangan (Searcher, Rescuer, Navigator).
- **Logistics Section:** Penjamin pasokan ransum makanan, bahan bakar, baterai radio, dan tali-temali.

#### 2. RAMS Matrix (Risk Assessment and Management System):
Tingkat Risiko dihitung berdasarkan:
Risk Score = Likelihood (Kemungkinan Terjadi) x Consequence (Tingkat Keparahan)
Jika skor berada pada level **Extreme Red (Merah Ekstrem)**, ekspedisi wajib dialihkan ke jalur alternatif (*Bailout Route*) atau dibatalkan.""",
                order_index=1
            )
            db.session.add(l3_1)
            db.session.flush()

            q3 = AcademyQuiz(
                tier_id=t3.id,
                title='Ujian Komando Operasi Ekspedisi & Manajemen Risiko Senior (Level 3)',
                description='Sertifikasi kualifikasi Komandan Lapangan. Nilai minimal 85% untuk berhak memimpin ekspedisi resmi dan melatih calon anggota KPAB GIMBAL.',
                passing_score=85,
                time_limit_mins=25,
                is_active=True
            )
            db.session.add(q3)
            db.session.flush()

            qq3_1 = QuizQuestion(
                quiz_id=q3.id,
                question_text='Dalam struktur Incident Command System (ICS), siapakah pejabat operasi yang memiliki wewenang menghentikan kegiatan lapangan secara mutlak jika menemukan kondisi bahaya yang mengancam keselamatan jiwa?',
                points=35,
                order_index=1,
                explanation='Safety Officer memegang mandat independen untuk menghentikan operasi secara instan jika mendeteksi bahaya keselamatan jiwa tanpa harus menunggu persetujuan birokratis.'
            )
            db.session.add(qq3_1)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq3_1.id, option_text='Safety Officer (Petugas Keselamatan Operasi)', is_correct=True, order_index=1),
                QuizOption(question_id=qq3_1.id, option_text='Seksi Konsumsi / Logistik Makanan', is_correct=False, order_index=2),
                QuizOption(question_id=qq3_1.id, option_text='Humas Publikasi Dokumentasi', is_correct=False, order_index=3),
                QuizOption(question_id=qq3_1.id, option_text='Sopir Kendaraan Angkutan', is_correct=False, order_index=4)
            ])

            qq3_2 = QuizQuestion(
                quiz_id=q3.id,
                question_text='Pada sistem penarikan tandu tebing (Vertical Rescue), sistem katrol mekanis sederhana yang memberikan keuntungan mekanis 3 banding 1 dikenal dengan nama apa?',
                points=35,
                order_index=2,
                explanation='Sistem 3:1 Z-Rig (atau Piggyback 3:1) adalah sistem hauling standar paling populer dalam Vertical Rescue untuk menaikkan tandu evakuasi dengan sepertiga tenaga tarikan.'
            )
            db.session.add(qq3_2)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq3_2.id, option_text='Z-Rig Hauling System (3:1 Mechanical Advantage)', is_correct=True, order_index=1),
                QuizOption(question_id=qq3_2.id, option_text='Single Pulley Direct 1:1', is_correct=False, order_index=2),
                QuizOption(question_id=qq3_2.id, option_text='Static Belay Knot', is_correct=False, order_index=3),
                QuizOption(question_id=qq3_2.id, option_text='Prusik Loop Friction Only', is_correct=False, order_index=4)
            ])

            qq3_3 = QuizQuestion(
                quiz_id=q3.id,
                question_text='Kapan seorang Komandan Ekspedisi diwajibkan mengambil keputusan "Bailout / No-Go" (pembatalan/evakuasi keluar jalur)?',
                points=30,
                order_index=3,
                explanation='Ketika tingkat risiko keselamatan regu melampaui batas toleransi risiko (RAMS skor ekstrem), seperti badai petir berkepanjangan di punggungan terbuka, hipotermia anggota ganda, atau cedera struktural fatal.'
            )
            db.session.add(qq3_3)
            db.session.flush()
            db.session.add_all([
                QuizOption(question_id=qq3_3.id, option_text='Ketika analisis risiko RAMS mencapai level ekstrem membahayakan jiwa anggota regu', is_correct=True, order_index=1),
                QuizOption(question_id=qq3_3.id, option_text='Hanya jika baterai ponsel habis', is_correct=False, order_index=2),
                QuizOption(question_id=qq3_3.id, option_text='Jika tidak ada pemandangan awan matahari terbit', is_correct=False, order_index=3),
                QuizOption(question_id=qq3_3.id, option_text='Ketika anggota regu merasa bosan', is_correct=False, order_index=4)
            ])

            db.session.commit()

try:
    init_database_and_defaults()
except Exception as _e:
    print(f"Warning on init_database_and_defaults: {_e}")


@app.context_processor
def inject_global_settings():
    """Menyediakan variabel pengaturan tema, rekening, dan organisasi ke seluruh template Jinja2"""
    try:
        return {
            'server_theme_color': SystemSetting.get('theme_color', 'orange'),
            'server_site_width': SystemSetting.get('site_width', '85%'),
            'bank_primary_name': SystemSetting.get('bank_primary_name', 'Bank Mandiri'),
            'bank_primary_number': SystemSetting.get('bank_primary_number', '131-00-1829-3321'),
            'bank_primary_holder': SystemSetting.get('bank_primary_holder', 'KPAB GIMBAL KAS PUSAT'),
            'bank_secondary_name': SystemSetting.get('bank_secondary_name', 'Bank BCA'),
            'bank_secondary_number': SystemSetting.get('bank_secondary_number', '593-019-4821'),
            'bank_secondary_holder': SystemSetting.get('bank_secondary_holder', 'KPAB GIMBAL KAS PUSAT'),
            'org_name': SystemSetting.get('org_name', 'KPAB GIMBAL Provinsi Gorontalo'),
            'org_phone': SystemSetting.get('org_phone', '+62 812-3456-7890'),
            'org_email': SystemSetting.get('org_email', 'sekretariat@gimbal.org'),
            'org_address': SystemSetting.get('org_address', 'Jl. Pangeran Hidayat No. 45, Kota Gorontalo'),
            'app_tagline': SystemSetting.get('app_tagline', 'Generasi Indonesia Menyatu Bersama Alam'),
            'payment_instructions': SystemSetting.get('payment_instructions', 'Silakan transfer tepat sejumlah tarif iuran, lalu simpan dan lampirkan bukti transfer.')
        }
    except Exception:
        return {
            'server_theme_color': 'orange',
            'server_site_width': '85%',
            'bank_primary_name': 'Bank Mandiri',
            'bank_primary_number': '131-00-1829-3321',
            'bank_primary_holder': 'KPAB GIMBAL KAS PUSAT',
            'bank_secondary_name': 'Bank BCA',
            'bank_secondary_number': '593-019-4821',
            'bank_secondary_holder': 'KPAB GIMBAL KAS PUSAT',
            'org_name': 'KPAB GIMBAL Provinsi Gorontalo',
            'org_phone': '+62 812-3456-7890',
            'org_email': 'sekretariat@gimbal.org',
            'org_address': 'Jl. Pangeran Hidayat No. 45, Kota Gorontalo',
            'app_tagline': 'Generasi Indonesia Menyatu Bersama Alam',
            'payment_instructions': 'Silakan transfer tepat sejumlah tarif iuran, lalu simpan dan lampirkan bukti transfer.'
        }


# ========== GOOGLE OAUTH CONFIGURATION ===========================================

import glob
GOOGLE_OAUTH_FILE = None
_client_secret_files = glob.glob(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'client_secret*.json'))
if _client_secret_files:
    GOOGLE_OAUTH_FILE = _client_secret_files[0]

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'https://www.gimbal.my.id')

if GOOGLE_OAUTH_FILE and os.path.exists(GOOGLE_OAUTH_FILE):
    try:
        with open(GOOGLE_OAUTH_FILE, 'r', encoding='utf-8') as _f:
            _oauth_data = json.load(_f)
            _web_cfg = _oauth_data.get('web', {})
            GOOGLE_CLIENT_ID = _web_cfg.get('client_id', GOOGLE_CLIENT_ID)
            GOOGLE_CLIENT_SECRET = _web_cfg.get('client_secret', GOOGLE_CLIENT_SECRET)
            _redirects = _web_cfg.get('redirect_uris', [])
            if _redirects:
                GOOGLE_REDIRECT_URI = _redirects[0]
    except Exception:
        pass


# ========== CONTEXT PROCESSOR ====================================================

@app.context_processor
def inject_global():
    user = get_current_user()
    pending_count = 0
    if user and user.is_admin:
        pending_count = User.query.filter_by(status='pending').count()
    return {
        'current_user': user,
        'pending_count': pending_count,
        'google_client_id': GOOGLE_CLIENT_ID,
        'now_str': datetime.now().strftime('%d %B %Y %H:%M WIB')
    }


# ========== STATIC & ASSET ROUTES ================================================

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    assets_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'assets')
    return send_from_directory(assets_dir, filename)

@app.route('/index.js')
def serve_index_js():
    return send_from_directory('.', 'index.js')

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ========== PUBLIC ROUTES ========================================================

@app.route('/')
def landing():
    """
    Halaman publik utama GIMBAL:
    Multi-Layer HTMX Architecture
    """
    code = request.args.get('code')
    if code:
        return process_google_oauth(code, redirect_uri=GOOGLE_REDIRECT_URI)

    activities = Activity.query.filter_by(is_open=True).order_by(Activity.created_at.desc()).limit(6).all()
    gallery_items = GalleryItem.query.filter_by(is_pinned=True).order_by(GalleryItem.id.desc()).limit(24).all()
    if len(gallery_items) < 8:
        additional = GalleryItem.query.order_by(GalleryItem.id.desc()).limit(24).all()
        seen_ids = {g.id for g in gallery_items}
        for g in additional:
            if g.id not in seen_ids:
                gallery_items.append(g)

    # Ekstrak kategori unik untuk filter tab galeri
    gallery_categories = []
    for g in gallery_items:
        if g.category and g.category not in gallery_categories:
            gallery_categories.append(g.category)

    active_members_count = User.query.filter_by(status='active').count()

    # Dewan Pengurus Inti dari Database (Position & User)
    board_positions = Position.query.filter_by(is_active=True, category='Pengurus Harian').order_by(Position.order_index.asc()).all()
    if not board_positions:
        board_positions = Position.query.filter_by(is_active=True).order_by(Position.order_index.asc()).limit(4).all()

    board_members = []
    for pos in board_positions:
        member = User.query.filter_by(jabatan=pos.name, status='active').first()
        default_avatar = '/static/pics/cartoon/avatar_kadiv.jpg'
        pos_lower = pos.name.lower()
        if 'ketua' in pos_lower:
            default_avatar = '/static/pics/cartoon/avatar_ketua.jpg'
        elif 'sekretaris' in pos_lower:
            default_avatar = '/static/pics/cartoon/avatar_sekjen.jpg'
        elif 'bendahara' in pos_lower:
            default_avatar = '/static/pics/cartoon/avatar_bendahara.jpg'

        board_members.append({
            'position_name': pos.name,
            'category': pos.category,
            'description': pos.description or 'Amanah Kepengurusan Organisasi KPAB GIMBAL',
            'order_index': pos.order_index,
            'member_name': member.name if member else None,
            'member_nra': member.nra if member else None,
            'avatar': (member.avatar if (member and member.avatar) else default_avatar),
            'is_assigned': bool(member)
        })

    # Divisi Operasional Lapangan dari Database (Position & User)
    op_positions = Position.query.filter_by(is_active=True, category='Divisi Operasional').order_by(Position.order_index.asc()).all()
    if not op_positions:
        op_positions = Position.query.filter(Position.name.ilike('%divisi%')).order_by(Position.order_index.asc()).all()

    operational_divisions = []
    for pos in op_positions:
        member = User.query.filter_by(jabatan=pos.name, status='active').first()
        pos_lower = pos.name.lower()

        # Pemetaan gambar kartun, tag, badge, highlight spesialisasi & icon
        img = '/static/pics/cartoon/divisi_mountaineer.jpg'
        tag = 'Mountaineering'
        badge_color = 'bg-orange-700'
        feature_highlight = 'Latihan Rutin & Navigasi Darat'
        icon = 'fas fa-mountain'
        clean_name = pos.name.replace('Kepala Divisi ', '').replace('Divisi ', '').strip()

        if any(k in pos_lower for k in ['panjat', 'tebing', 'climbing', 'rock']):
            img = '/static/pics/cartoon/divisi_climbing.jpg'
            tag = 'Rock Climbing'
            badge_color = 'bg-orange-600'
            feature_highlight = 'Sertifikasi Alat & Vertical Rescue'
            icon = 'fas fa-mountain-sun'
        elif any(k in pos_lower for k in ['gua', 'caving', 'speleo']):
            img = '/static/pics/cartoon/divisi_caving.jpg'
            tag = 'Speleology'
            badge_color = 'bg-orange-800'
            feature_highlight = 'Single Rope Technique & Pemetaan Gua'
            icon = 'fas fa-dungeon'
        elif any(k in pos_lower for k in ['arung', 'jeram', 'rafting', 'sungai', 'river', 'water']):
            img = '/static/pics/cartoon/divisi_conservation.jpg'
            tag = 'River Running'
            badge_color = 'bg-sky-700'
            feature_highlight = 'River Rescue & Keselamatan Jeram'
            icon = 'fas fa-water'
        elif any(k in pos_lower for k in ['konservasi', 'lingkungan', 'lh', 'sar', 'alam', 'ecology']):
            img = '/static/pics/cartoon/divisi_conservation.jpg'
            tag = 'Ecology & SAR'
            badge_color = 'bg-amber-600'
            feature_highlight = 'Konservasi Alam & Tanggap Bencana'
            icon = 'fas fa-tree'
        elif any(k in pos_lower for k in ['gunung', 'hutan', 'mountaineer']):
            img = '/static/pics/cartoon/divisi_mountaineer.jpg'
            tag = 'Mountaineering'
            badge_color = 'bg-orange-700'
            feature_highlight = 'Navigasi Darat & Jungle Survival'
            icon = 'fas fa-mountain'

        operational_divisions.append({
            'id': pos.id,
            'name': pos.name,
            'clean_name': clean_name,
            'description': pos.description or 'Setiap anggota dibekali keahlian teknis sesuai minat penjelajahan alam bebas.',
            'category': pos.category,
            'order_index': pos.order_index,
            'tag': tag,
            'badge_color': badge_color,
            'image': img,
            'icon': icon,
            'feature_highlight': feature_highlight,
            'member_name': member.name if member else None,
            'member_nra': member.nra if member else None,
            'avatar': (member.avatar if (member and member.avatar) else None),
            'is_assigned': bool(member)
        })

    repo_maps = MapRepository.query.order_by(MapRepository.id.desc()).limit(4).all()

    # Data Sponsorship & Usaha Anggota untuk Landing Page
    sponsors = Sponsor.query.filter_by(is_active=True).order_by(Sponsor.order_index.asc(), Sponsor.id.asc()).all()
    corporate_sponsors = [s for s in sponsors if not s.is_member_business]
    member_businesses = [s for s in sponsors if s.is_member_business and s.status == 'active']

    return render_gimbal_template(
        'landing.html',
        context={
            'activities': activities,
            'gallery_items': gallery_items,
            'gallery_categories': gallery_categories,
            'active_members_count': active_members_count,
            'board_members': board_members,
            'operational_divisions': operational_divisions,
            'repo_maps': repo_maps,
            'sponsors': sponsors,
            'corporate_sponsors': corporate_sponsors,
            'member_businesses': member_businesses
        },
        active_page='landing'
    )

@app.route('/download/gimbal-maps.apk')
@app.route('/download/gimbal-maps')
def download_gimbal_maps():
    """Endpoint pengunduhan berkas APK aplikasi Android GIMBAL-Maps"""
    apk_path = os.path.join(app.root_path, 'static', 'downloads', 'gimbal-maps.apk')
    if os.path.exists(apk_path):
        return send_file(
            apk_path,
            as_attachment=True,
            download_name='gimbal-maps-v1.0.apk',
            mimetype='application/vnd.android.package-archive'
        )
    return redirect('/static/downloads/gimbal-maps.apk')

@app.route('/app-shell')
def app_shell():
    """Layer 2 Application Shell provider jika app-shell di-load langsung"""
    user = get_current_user()
    if not user:
        return redirect('/')
    if user.is_admin:
        return redirect('/admin/dashboard')
    if not user.is_profile_complete:
        return redirect('/member/complete-profile')
    if user.status != 'active':
        return redirect('/member/onboarding-status')
    return redirect('/member/dashboard')

@app.route('/verify-kta/<nra>')
def verify_kta(nra):
    """Halaman publik verifikasi keabsahan KTA digital (hasil scan QR)"""
    member = User.query.filter_by(nra=nra).first()
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M WIB')
    return render_gimbal_modal(
        'verify_kta',
        context={
            'member': member,
            'nra_queried': nra,
            'now_str': now_str
        },
        active_page='verify_kta'
    )


@app.route('/contact/send', methods=['POST'])
def contact_send():
    """Endpoint publik: Formulir Kontak, Permohonan Pengawalan Pendakian, Sponsorship & Pertanyaan Umum"""
    import urllib.parse
    category = request.form.get('category', 'general').strip()
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()

    destination = request.form.get('destination', '').strip()
    target_date = request.form.get('target_date', '').strip()
    participants_raw = request.form.get('participants_count', '1').strip()
    try:
        participants_count = max(1, int(participants_raw))
    except (ValueError, TypeError):
        participants_count = 1

    services_list = request.form.getlist('services_needed')
    services_needed = ", ".join(services_list) if services_list else request.form.get('services_needed', '').strip()

    if not name or not phone or not message:
        return """
        <div class="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs animate-shake">
            <p class="font-bold flex items-center gap-1.5"><i class="fas fa-exclamation-triangle text-rose-600"></i> Mohon Lengkapi Kolom Wajib</p>
            <p class="mt-1 text-[11px] text-rose-700">Nama lengkap, nomor WhatsApp aktif, dan pesan/keperluan wajib diisi agar pengurus dapat menghubungi Anda.</p>
        </div>
        """

    cat_titles = {
        'guiding': 'Pengawalan & Pemandu Pendakian',
        'membership': 'Pendaftaran Calon Anggota (Diksar)',
        'sponsorship': 'Kemitraan & Sponsorship',
        'general': 'Pertanyaan Umum / Info Jalur'
    }
    cat_label = cat_titles.get(category, category.title())

    inquiry = Inquiry(
        category=category,
        name=name,
        phone=phone,
        email=email,
        subject=subject or f"Permohonan {cat_label}: {name}",
        message=message,
        destination=destination,
        target_date=target_date,
        participants_count=participants_count,
        services_needed=services_needed,
        status='pending'
    )
    db.session.add(inquiry)
    db.session.commit()

    wa_text = f"Halo Admin KPAB GIMBAL, saya *{name}*. Saya telah mengirim permohonan melalui form di website perihal *{cat_label}*."
    if category == 'guiding' and destination:
        wa_text += f"\n- *Tujuan Gunung*: {destination}\n- *Rencana Tanggal*: {target_date or '-'}\n- *Peserta*: {participants_count} orang\n- *Kebutuhan*: {services_needed or 'Pemandu Jalur'}"
    wa_text += f"\n\nMohon konfirmasi dan informasinya, terima kasih! Salam Lestari."
    
    clean_org_phone = os.environ.get('ORG_PHONE', '6281234567890').replace(' ', '').replace('-', '').replace('+', '')
    wa_url = f"https://wa.me/{clean_org_phone}?text={urllib.parse.quote(wa_text)}"

    return f"""
    <div class="p-6 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-950 text-center space-y-3 animate-fade-in shadow-sm">
        <div class="w-12 h-12 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center mx-auto text-xl shadow-xs">
            <i class="fas fa-check-circle"></i>
        </div>
        <h4 class="font-bold text-base font-heading text-emerald-900">Permohonan Berhasil Terkirim!</h4>
        <p class="text-xs text-emerald-800 leading-relaxed max-w-md mx-auto">
            Terima kasih <strong>{name}</strong>. Permohonan Anda mengenai <strong>{cat_label}</strong> telah tercatat di sistem sekretariat KPAB GIMBAL.
        </p>
        <div class="pt-2 flex flex-col sm:flex-row items-center justify-center gap-2.5">
            <a href="{wa_url}" target="_blank"
               class="w-full sm:w-auto px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow-sm transition flex items-center justify-center gap-2">
                <i class="fab fa-whatsapp text-sm"></i> <span>Konfirmasi Cepat via WhatsApp</span>
            </a>
            <button type="button" onclick="if(window.resetContactForm) window.resetContactForm(); else location.reload();"
                    class="w-full sm:w-auto px-4 py-2.5 bg-white hover:bg-emerald-100/60 text-emerald-800 font-semibold text-xs rounded-lg border border-emerald-300 transition">
                Kirim Pesan Lainnya
            </button>
        </div>
    </div>
    """


# ========== AUTHENTICATION & GOOGLE SSO ==========================================

def login_or_register_google_user(user_info):
    """Mendaftarkan anggota baru atau login user berdasarkan profil Google OAuth resmi"""
    email = user_info.get('email', '').strip().lower()
    google_id = str(user_info.get('id') or user_info.get('sub', '')).strip()
    name = user_info.get('name') or user_info.get('given_name') or email.split('@')[0].replace('.', ' ').title()
    picture = user_info.get('picture')

    if not email:
        return redirect("/login?error=Email+Google+tidak+ditemukan")

    user = None
    if google_id:
        user = User.query.filter((User.google_id == google_id) | (User.email == email)).first()
    else:
        user = User.query.filter_by(email=email).first()

    if not user:
        user = User(
            google_id=google_id or None,
            email=email,
            name=name,
            role='member',
            status='pending',
            avatar=picture or '/static/pics/cartoon/avatar_sekjen.jpg',
            password_hash='google_sso_authenticated'
        )
        db.session.add(user)
        db.session.commit()
    else:
        if google_id and not user.google_id:
            user.google_id = google_id
        if picture and (not user.avatar or 'lh3.googleusercontent.com' in user.avatar or user.avatar.startswith('/static/')):
            user.avatar = picture
        db.session.commit()

    # Perbarui waktu terakhir masuk (Last Login) & Sinkronisasi Email Forwarding Cloudflare
    user.last_login = datetime.utcnow()
    try:
        sync_cloudflare_email_routing(user)
    except Exception as _e_cf:
        app.logger.warning(f"Cloudflare sync note: {_e_cf}")
    db.session.commit()

    session['user_id'] = user.id
    target = session.pop('login_next', None) or request.args.get('next') or request.form.get('next')
    if target and (target.startswith('/') or 'gimbal.my.id' in target) and not target.endswith('/login'):
        return redirect(target)
    if user.is_admin:
        return redirect('/admin/dashboard')
    if not user.is_profile_complete:
        return redirect('/member/complete-profile')
    if user.status != 'active':
        return redirect('/member/onboarding-status')
    return redirect('/member/dashboard')


def process_google_oauth(code, redirect_uri):
    """Menukarkan authorization code dengan access token & profil Google"""
    import requests
    token_url = "https://oauth2.googleapis.com/token"
    token_payload = {
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }

    try:
        token_resp = requests.post(token_url, data=token_payload, timeout=12)
        if token_resp.status_code != 200:
            alt_uri = redirect_uri[:-1] if redirect_uri.endswith('/') else (redirect_uri + '/')
            token_payload['redirect_uri'] = alt_uri
            token_resp2 = requests.post(token_url, data=token_payload, timeout=10)
            if token_resp2.status_code == 200:
                token_resp = token_resp2
            else:
                return redirect(f"/login?error=Otentikasi+Google+gagal+({token_resp.status_code})")

        token_data = token_resp.json()
        access_token = token_data.get('access_token')
        if not access_token:
            return redirect("/login?error=Token+Google+tidak+valid")

        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        userinfo_resp = requests.get(
            userinfo_url,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
        )
        if userinfo_resp.status_code != 200:
            return redirect("/login?error=Gagal+mengambil+profil+Google")

        user_info = userinfo_resp.json()
        return login_or_register_google_user(user_info)
    except Exception as e:
        app.logger.error(f"Google OAuth Exception: {e}")
        return redirect("/login?error=Koneksi+Google+gagal")


@app.route('/auth/google-login')
def google_login():
    """Inisiasi Login / Pendaftaran Akun Google OAuth 2.0"""
    from urllib.parse import urlencode
    redirect_uri = GOOGLE_REDIRECT_URI

    state = base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8')
    session['oauth_state'] = state

    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'response_type': 'code',
        'scope': 'openid email profile',
        'redirect_uri': redirect_uri,
        'prompt': 'select_account',
        'state': state
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return redirect(google_auth_url)


@app.route('/auth/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        return redirect('/')
    return process_google_oauth(code, redirect_uri=GOOGLE_REDIRECT_URI)


@app.route('/auth/google/credential', methods=['POST'])
def google_credential_callback():
    """Callback untuk Google One Tap / Google Identity Services button"""
    credential = request.form.get('credential') or (request.json.get('credential') if request.is_json else None)
    if not credential:
        return redirect('/login?error=Kredensial+Google+kosong')

    try:
        import requests
        verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
        verify_resp = requests.get(verify_url, timeout=10)
        if verify_resp.status_code != 200:
            return redirect("/login?error=Kredensial+Google+tidak+valid")

        user_info = verify_resp.json()
        if user_info.get('aud') != GOOGLE_CLIENT_ID:
            return redirect("/login?error=Kredensial+Google+tidak+cocok")

        return login_or_register_google_user(user_info)
    except Exception as e:
        app.logger.error(f"Google Credential Verification Error: {e}")
        return redirect("/login?error=Gagal+verifikasi+Google")


@app.route('/auth/switch-role')
def switch_role():
    """Bypass dev role switcher telah dinonaktifkan permanen demi keamanan"""
    return redirect('/login')


@app.route('/login')
def login_page():
    """Halaman login & pendaftaran resmi KPAB GIMBAL Provinsi Gorontalo"""
    next_url = request.args.get('next')
    if next_url and (next_url.startswith('/') or 'gimbal.my.id' in next_url):
        session['login_next'] = next_url

    user = get_current_user()
    if user:
        target = session.pop('login_next', None) or next_url
        if target and (target.startswith('/') or 'gimbal.my.id' in target) and not target.endswith('/login'):
            return redirect(target)
        if user.is_admin:
            return redirect('/admin/dashboard')
        if not user.is_profile_complete:
            return redirect('/member/complete-profile')
        if user.status != 'active':
            return redirect('/member/onboarding-status')
        return redirect('/member/dashboard')
    error_msg = request.args.get('error')
    return render_gimbal_modal(
        'login',
        context={'google_client_id': GOOGLE_CLIENT_ID, 'error_msg': error_msg, 'next_url': next_url},
        active_page='login'
    )


@app.route('/auth/modal-login')
def modal_login():
    """Endpoint untuk membuka modal login via popup modal-container"""
    user = get_current_user()
    if user:
        if user.is_admin:
            return redirect('/admin/dashboard')
        return redirect('/member/dashboard')
    error_msg = request.args.get('error')
    return render_gimbal_modal(
        'login',
        context={'google_client_id': GOOGLE_CLIENT_ID, 'error_msg': error_msg},
        active_page='login'
    )


@app.route('/auth/login', methods=['POST'])
def auth_login():
    """Login manual email/username & password"""
    identifier = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    
    if not identifier:
        return redirect('/login?error=Username+atau+email+harus+diisi')

    ident_lower = identifier.lower()
    user = None
    if '@' in ident_lower:
        user = User.query.filter_by(email=ident_lower).first()
    else:
        if ident_lower == 'fitra':
            user = User.query.filter((User.email == 'fitra@gimbal.org') | (db.func.lower(User.name) == 'fitra')).first()
        else:
            user = User.query.filter(db.func.lower(User.name) == ident_lower).first()
            if not user:
                user = User.query.filter_by(email=f"{ident_lower}@gimbal.org").first()

    if not user:
        if '@' in ident_lower:
            if not password:
                return redirect('/login?error=Kata+sandi+harus+diisi+untuk+pendaftaran+baru')
            name = ident_lower.split('@')[0].replace('.', ' ').title()
            user = User(
                email=ident_lower,
                name=name,
                role='member',
                status='pending',
                password_hash=password,
                avatar='/static/pics/cartoon/avatar_sekjen.jpg'
            )
            db.session.add(user)
            db.session.commit()
        else:
            return redirect('/login?error=Akun+tidak+ditemukan')

    # Verifikasi Kata Sandi
    if user.password_hash and user.password_hash != password:
        return redirect('/login?error=Kata+sandi+salah')
        
    # Perbarui waktu terakhir masuk (Last Login) & Sinkronisasi Email Forwarding Cloudflare
    user.last_login = datetime.utcnow()
    try:
        sync_cloudflare_email_routing(user)
    except Exception as _e_cf:
        app.logger.warning(f"Cloudflare sync note: {_e_cf}")
    db.session.commit()

    session['user_id'] = user.id
    target = session.pop('login_next', None) or request.args.get('next') or request.form.get('next')
    if target and (target.startswith('/') or 'gimbal.my.id' in target) and not target.endswith('/login'):
        return redirect(target)
    if user.is_admin:
        return redirect('/admin/dashboard')
    if not user.is_profile_complete:
        return redirect('/member/complete-profile')
    if user.status != 'active':
        return redirect('/member/onboarding-status')
    return redirect('/member/dashboard')


@app.route('/logout')
@app.route('/auth/logout')
def logout():
    """Membersihkan sesi dan menghapus seluruh cookie sesi di semua variasi domain & host"""
    session.clear()
    next_dest = request.args.get('next', '/')
    resp = redirect(next_dest)
    
    # Hapus cookie session secara eksplisit di semua variasi domain & host
    cookie_name = app.config.get('SESSION_COOKIE_NAME', 'session')
    for d in [None, '.gimbal.my.id', 'www.gimbal.my.id', 'gimbal.my.id', 'mapgen.gimbal.my.id']:
        try:
            resp.delete_cookie(cookie_name, domain=d, path='/')
            resp.set_cookie(cookie_name, '', expires=0, max_age=0, domain=d, path='/')
        except Exception:
            pass
            
    # Pastikan jika request datang dari HTMX, browser diarahkan secara penuh
    if request.headers.get('HX-Request'):
        resp.headers['HX-Redirect'] = next_dest
        
    return resp


# ========== REGISTER MODULAR BLUEPRINTS ==========================================

from admin_pages import admin_bp
from members_page import members_bp
from web_api import api_bp

app.register_blueprint(admin_bp)
app.register_blueprint(members_bp)
app.register_blueprint(api_bp)


# =================================================================================
if __name__ == '__main__':
    print(">>> GIMBAL WebApps running")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
