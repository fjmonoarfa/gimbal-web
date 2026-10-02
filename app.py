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
    Sponsor, SponsorProduct
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
                    ('cloudflare_status', "VARCHAR(32) DEFAULT 'pending'")
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


@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect('/')


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
