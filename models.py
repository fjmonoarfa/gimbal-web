from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(128), unique=True, nullable=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    avatar = db.Column(db.String(256), nullable=True)
    role = db.Column(db.String(20), default='member')  # 'admin', 'member'
    jabatan = db.Column(db.String(100), nullable=True)  # e.g., 'Ketua Umum', 'Sekretaris Jenderal', 'Anggota Biasa'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'active', 'rejected'
    
    # Penomoran NRA format: R-nn-YY
    nra = db.Column(db.String(20), unique=True, nullable=True)
    nra_year = db.Column(db.Integer, nullable=True)      # e.g., 26
    nra_sequence = db.Column(db.Integer, nullable=True)  # e.g., 1, 2, ...
    
    # Biodata Lengkap Petualang
    phone = db.Column(db.String(30), nullable=True)
    birth_place = db.Column(db.String(64), nullable=True)
    birth_date = db.Column(db.String(30), nullable=True)
    address = db.Column(db.Text, nullable=True)
    blood_type = db.Column(db.String(10), nullable=True)  # A, B, AB, O
    medical_history = db.Column(db.Text, nullable=True)   # Asma, alergi, riwayat patah tulang, dll.
    
    # Emergency Contact (Safety First)
    emergency_name = db.Column(db.String(100), nullable=True)
    emergency_relation = db.Column(db.String(50), nullable=True)  # Orang Tua, Pasangan, Saudara
    emergency_phone = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    
    # Langganan Google Pay / Google Play In-App Subscription (gimbal-maps)
    subscription_channel = db.Column(db.String(50), default='manual')  # 'manual', 'midtrans', 'google_pay'
    subscription_expiry = db.Column(db.DateTime, nullable=True)        # Batas aktif langganan Google Pay
    google_order_id = db.Column(db.String(100), nullable=True)        # GPA.xxxx-xxxx-xxxx-xxxxx
    google_purchase_token = db.Column(db.String(256), nullable=True)
    google_product_id = db.Column(db.String(100), nullable=True)      # e.g., 'gimbal_member_monthly'
    
    # Status approval
    rejection_reason = db.Column(db.Text, nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    # Sesi & Aktivitas Login
    last_login = db.Column(db.DateTime, nullable=True)
    last_seen = db.Column(db.DateTime, nullable=True)

    # Cloudflare Email Routing & Alias Organisasi (@gimbal.my.id)
    gimbal_alias_email = db.Column(db.String(128), unique=True, nullable=True)
    cloudflare_rule_id = db.Column(db.String(64), nullable=True)
    cloudflare_status = db.Column(db.String(32), default='pending')  # 'active', 'pending_verification', 'disabled'

    # Penugasan Wajib Sertifikasi Kesiapan Operasional / Akademi
    is_mandatory_certified = db.Column(db.Boolean, default=False)
    mandatory_tier_id = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_online(self):
        """Mengecek apakah pengguna aktif dalam 5 menit terakhir"""
        if not self.last_seen:
            return False
        return (datetime.utcnow() - self.last_seen).total_seconds() <= 300

    # Relasi
    payments = db.relationship('DuesPayment', foreign_keys='DuesPayment.user_id', backref='user', lazy='dynamic')
    uploaded_docs = db.relationship('Document', backref='uploader', lazy='dynamic')

    @property
    def is_admin(self):
        return self.role in ['admin', 'superadmin']

    @property
    def is_superadmin(self):
        return self.role == 'superadmin'

    @property
    def is_active_member(self):
        return self.status == 'active' and self.nra is not None

    @property
    def has_active_google_subscription(self):
        """Mengecek apakah pengguna memiliki langganan aktif via Google Pay"""
        if self.subscription_channel == 'google_pay' and self.subscription_expiry:
            return self.subscription_expiry > datetime.utcnow()
        return False

    @property
    def subscription_days_remaining(self):
        """Menghitung sisa hari aktif langganan Google Pay"""
        if self.has_active_google_subscription:
            delta = self.subscription_expiry - datetime.utcnow()
            return max(0, delta.days)
        return 0

    @property
    def is_profile_complete(self):
        """Mengecek apakah informasi biodata wajib keanggotaan sudah terisi lengkap"""
        return bool(
            self.phone and str(self.phone).strip() and
            self.birth_place and str(self.birth_place).strip() and
            self.birth_date and str(self.birth_date).strip() and
            self.blood_type and str(self.blood_type).strip() and
            self.address and str(self.address).strip() and
            self.emergency_name and str(self.emergency_name).strip() and
            self.emergency_phone and str(self.emergency_phone).strip()
        )

    @property
    def latest_dues_payment(self):
        """Mengambil rekaman pembayaran iuran terakhir calon anggota"""
        return self.payments.order_by(DuesPayment.id.desc()).first()

    @property
    def is_dues_paid(self):
        """Mengecek apakah iuran keanggotaan sudah diverifikasi lunas/approved oleh admin"""
        if self.has_active_google_subscription:
            return True
        return self.payments.filter_by(status='approved').count() > 0

    @property
    def is_current_month_dues_paid(self):
        """
        Mengecek apakah anggota lunas iuran pada bulan berjalan.
        Admin / Superadmin otomatis aktif.
        Langganan Google Pay aktif jika belum expired.
        Anggota biasa aktif jika ada pembayaran berstatus 'approved' dalam 31 hari terakhir
        atau pada bulan dan tahun berjalan.
        """
        if self.is_admin:
            return True
        if self.has_active_google_subscription:
            return True
        now = datetime.utcnow()
        latest = self.payments.filter_by(status='approved').order_by(DuesPayment.id.desc()).first()
        if not latest:
            return False
        if latest.payment_date:
            diff_days = (now - latest.payment_date).days
            if diff_days <= 31:
                return True
            if latest.payment_date.year == now.year and latest.payment_date.month == now.month:
                return True
        return False

    @property
    def certifications_list(self):
        """Daftar sertifikat keahlian akademi yang telah diraih anggota"""
        return UserCertification.query.filter_by(user_id=self.id, status='active').order_by(UserCertification.id.desc()).all()

    @property
    def is_mandatory_certification_pending(self):
        """Mengecek apakah anggota wajib menyelesaikan sertifikasi awal tapi belum lulus"""
        if not self.is_mandatory_certified:
            return False
        target_tier = self.mandatory_tier_id or 1
        has_cert = UserCertification.query.filter_by(user_id=self.id, tier_id=target_tier, status='active').first()
        return has_cert is None


def generate_next_nra():
    """
    Menghasilkan nomor anggota dengan format R-nn-YY
    - YY: 2 digit tahun saat approval (misal: 26)
    - nn: nomor urut persetujuan pada tahun YY tersebut, reset ke 1 setiap tahun baru.
    """
    current_year_2digit = int(datetime.now().strftime('%y')) # misal 26
    
    max_seq = db.session.query(func.max(User.nra_sequence)).filter(
        User.nra_year == current_year_2digit
    ).scalar()
    
    next_seq = (max_seq or 0) + 1
    nra_code = f"R-{next_seq:02d}-{current_year_2digit}"
    
    return nra_code, current_year_2digit, next_seq


class Dues(db.Model):
    """Master Iuran Organisasi"""
    __tablename__ = 'dues'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)  # e.g., 'Iuran Wajib Maret 2026'
    category = db.Column(db.String(50), default='wajib')  # 'wajib', 'kegiatan', 'sukarela'
    amount = db.Column(db.Float, nullable=False, default=15000.0)
    due_date = db.Column(db.String(30), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payments = db.relationship('DuesPayment', backref='dues', lazy='dynamic', cascade='all, delete-orphan')


class DuesPayment(db.Model):
    """Pencatatan & Bukti Pembayaran Iuran Anggota"""
    __tablename__ = 'dues_payments'

    id = db.Column(db.Integer, primary_key=True)
    dues_id = db.Column(db.Integer, db.ForeignKey('dues.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    bank_name = db.Column(db.String(50), nullable=True)
    proof_image = db.Column(db.String(256), nullable=True)  # Path file bukti transfer (opsional jika Midtrans)
    order_id = db.Column(db.String(64), unique=True, nullable=True)  # Midtrans Order ID
    snap_token = db.Column(db.String(128), nullable=True)  # Midtrans Snap Token
    payment_type = db.Column(db.String(50), default='manual_transfer')  # 'midtrans', 'manual_transfer'
    transaction_status = db.Column(db.String(50), nullable=True)  # 'settlement', 'pending', 'expire', 'deny'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    notes = db.Column(db.Text, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Document(db.Model):
    """Dokumen Internal Organisasi (AD/ART, SOP, Materi Pelatihan)"""
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'ad_art', 'sop', 'materi', 'sk_resmi'
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(256), nullable=False)
    file_type = db.Column(db.String(20), default='pdf')
    file_size_fmt = db.Column(db.String(30), default='1.2 MB')
    is_public_to_members = db.Column(db.Boolean, default=True)
    is_shared_to_timeline = db.Column(db.Boolean, default=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Activity(db.Model):
    """Agenda Kegiatan & Ekspedisi Petualang"""
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    activity_date = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), default='Menengah') # Santai, Menengah, Ekstrem
    category = db.Column(db.String(80), default='Gunung Hutan') # Gunung Hutan, Panjat Tebing, Susur Gua, Arung Jeram, Konservasi, Diksar, Camp & Wisata
    quota = db.Column(db.Integer, default=20)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(256), nullable=True)
    is_open = db.Column(db.Boolean, default=True)
    is_shared_to_timeline = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ROL & Lifecycle Fields
    phase = db.Column(db.String(30), default='open')  # 'planning', 'open', 'in_progress', 'completed', 'archived'
    budget_json = db.Column(db.Text, default='{}')
    route_plan = db.Column(db.Text, nullable=True)
    map_repo_id = db.Column(db.Integer, db.ForeignKey('map_repositories.id'), nullable=True)
    gear_json = db.Column(db.Text, default='{}')
    evaluation_notes = db.Column(db.Text, nullable=True)

    participants = db.relationship('ActivityParticipant', backref='activity', lazy='dynamic', cascade='all, delete-orphan')
    field_logs = db.relationship('ActivityFieldLog', backref='activity', lazy='dynamic', cascade='all, delete-orphan', order_by='ActivityFieldLog.recorded_at.desc()')
    map_repo = db.relationship('MapRepository', foreign_keys=[map_repo_id])

    @property
    def budget_data(self):
        try:
            import json
            return json.loads(self.budget_json) if self.budget_json else {}
        except Exception:
            return {}

    @property
    def gear_data(self):
        try:
            import json
            return json.loads(self.gear_json) if self.gear_json else {}
        except Exception:
            return {}

    @property
    def confirmed_participants(self):
        return [p for p in self.participants if p.status == 'confirmed']

    @property
    def total_confirmed(self):
        return len(self.confirmed_participants)

    @property
    def lead_person(self):
        for p in self.participants:
            if p.role == 'Pimpinan Perjalanan' and p.status == 'confirmed':
                return p
        for p in self.participants:
            if p.status == 'confirmed':
                return p
        return None

    @property
    def documentation_media(self):
        """Mengumpulkan seluruh foto dan video dokumentasi dari postingan anggota yang ditautkan ke ekspedisi ini"""
        items = []
        for post in self.posts.order_by(Post.created_at.desc()):
            for m in post.media_items:
                items.append({
                    'media_url': m.media_url,
                    'media_type': getattr(m, 'media_type', 'image'),
                    'caption': getattr(m, 'caption', None),
                    'post_id': post.id,
                    'content': post.content,
                    'location': post.location,
                    'user_name': post.user.name if post.user else 'Anggota GIMBAL',
                    'user_avatar': post.user.avatar if (post.user and post.user.avatar) else '/static/pics/cartoon/avatar_sekjen.jpg',
                    'user_nra': post.user.nra if post.user else None,
                    'created_at': post.created_at
                })
        return items


class ActivityParticipant(db.Model):
    """Pendaftaran Peserta Ekspedisi"""
    __tablename__ = 'activity_participants'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='registered')  # 'registered', 'confirmed', 'cancelled'
    role = db.Column(db.String(50), default='Anggota')  # 'Pimpinan Perjalanan', 'Navigator', 'Logistik', 'Medis/P3K', 'Dokumentasi', 'Sweeper', 'Anggota'
    notes = db.Column(db.Text, nullable=True)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])


class ActivityFieldLog(db.Model):
    """Log Laporan Lapangan Ekspedisi (POI, Waypoint, Track, Catatan, Foto dari Web & Gimbal-Maps)"""
    __tablename__ = 'activity_field_logs'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    log_type = db.Column(db.String(30), default='poi')  # 'poi', 'track', 'situation_report', 'photo'
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    elevation = db.Column(db.Float, nullable=True)
    photo_url = db.Column(db.String(256), nullable=True)
    source = db.Column(db.String(30), default='manual')  # 'manual', 'gimbal_maps'
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])


class GalleryItem(db.Model):
    """Dokumentasi Foto Petualangan (Pin-down dari Ekspedisi)"""
    __tablename__ = 'gallery_items'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=True)
    caption = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(256), nullable=False)
    category = db.Column(db.String(50), default='Pendakian')
    location = db.Column(db.String(150), nullable=True)
    is_pinned = db.Column(db.Boolean, default=True)  # Pin-down ke Galeri Utama Landing Page
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    activity = db.relationship('Activity', backref=db.backref('gallery_items', lazy='dynamic'))
    post = db.relationship('Post', backref=db.backref('gallery_items', lazy='dynamic'))

    @property
    def album_json(self):
        """Kembalikan album serial JSON jika item ini berasal dari postingan multi-media"""
        if not self.post or not self.post.media_items or len(self.post.media_items) <= 1:
            return None
        import json
        items = []
        loc = self.location or (self.activity.title if self.activity else 'KPAB GIMBAL')
        for m in self.post.media_items:
            items.append({
                'media_url': m.media_url,
                'media_type': getattr(m, 'media_type', 'image'),
                'caption': getattr(m, 'caption', None) or self.post.content[:180],
                'subcaption': f"{loc} • {self.category}"
            })
        return json.dumps(items)


# ========== SPONSORSHIP & MEMBER BUSINESS DIRECTORY MODELS ========================

class Sponsor(db.Model):
    """Mitra Sponsor Korporat & Jaringan Usaha Anggota GIMBAL"""
    __tablename__ = 'sponsors'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    logo_url = db.Column(db.String(256), nullable=False)
    category = db.Column(db.String(50), default='gear')  # 'corporate', 'gear', 'cafe', 'ethnic_store', 'rental', 'homestay', 'media', 'other'
    tier = db.Column(db.String(50), default='official_partner')  # 'title_sponsor', 'official_partner', 'community_partner', 'media_partner'
    description = db.Column(db.Text, nullable=True)
    promo_badge = db.Column(db.String(80), nullable=True)  # e.g., 'Diskon 15% KTA', 'Official Basecamp'
    member_benefit = db.Column(db.Text, nullable=True)  # e.g., 'Diskon 15% semua menu kopi dengan KTA GIMBAL'
    website_url = db.Column(db.String(256), nullable=True)
    instagram_url = db.Column(db.String(256), nullable=True)
    whatsapp_number = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)
    maps_url = db.Column(db.String(512), nullable=True)

    # Ownership: None jika Managed Corporate Sponsor oleh Admin; terisi user_id jika Usaha Milik Anggota
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_member_business = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='active')  # 'pending', 'active', 'rejected', 'inactive'
    rejection_reason = db.Column(db.Text, nullable=True)

    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_shared_to_timeline = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship('User', foreign_keys=[owner_user_id], backref=db.backref('businesses', lazy='dynamic'))
    products = db.relationship('SponsorProduct', backref='sponsor', cascade='all, delete-orphan', order_by='SponsorProduct.order_index.asc()')


class SponsorProduct(db.Model):
    """Katalog Produk / Menu / Paket Jasa dari Sponsor & Usaha Anggota"""
    __tablename__ = 'sponsor_products'

    id = db.Column(db.Integer, primary_key=True)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('sponsors.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, default=0.0)
    discount_price = db.Column(db.Float, nullable=True)  # Harga Spesial Anggota KTA GIMBAL
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(256), nullable=True)
    badge = db.Column(db.String(50), nullable=True)  # e.g., 'Best Seller', 'Khas Gorontalo', 'Menu Favorit'
    is_available = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ========== SOCIAL & COMMUNITY FEED MODELS (LINI MASA PETUALANG) ==================

class Post(db.Model):
    """Postingan Lini Masa / Adventure Feed Anggota GIMBAL"""
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(256), nullable=True)
    location = db.Column(db.String(150), nullable=True)  # e.g., 'Gunung Tilongkabila, Gorontalo'
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    map_repo_id = db.Column(db.Integer, db.ForeignKey('map_repositories.id'), nullable=True)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('sponsors.id'), nullable=True)
    post_type = db.Column(db.String(30), default='general')  # 'general', 'activity', 'document', 'map', 'sponsor'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])
    activity = db.relationship('Activity', backref=db.backref('posts', lazy='dynamic'))
    document = db.relationship('Document', backref=db.backref('posts', lazy='dynamic'))
    map_repo = db.relationship('MapRepository', backref=db.backref('posts', lazy='dynamic'))
    sponsor = db.relationship('Sponsor', foreign_keys=[sponsor_id], backref=db.backref('posts', lazy='dynamic'))
    comments = db.relationship('PostComment', backref='post', cascade='all, delete-orphan', order_by='PostComment.created_at.asc()')
    likes = db.relationship('PostLike', backref='post', cascade='all, delete-orphan')
    media = db.relationship('PostMedia', backref='post', cascade='all, delete-orphan', order_by='PostMedia.order_index.asc()')

    @property
    def media_items(self):
        """Mengembalikan daftar media: dari relasi post_media atau fallback dari image_url lama"""
        items = list(self.media)
        if items:
            return items
        if self.image_url:
            is_vid = any(self.image_url.lower().endswith(ext) for ext in ['.mp4', '.mov', '.webm', '.mkv'])
            class LegacyMedia:
                id = 0
                media_url = self.image_url
                media_type = 'video' if is_vid else 'image'
                caption = None
                order_index = 0
                def to_dict(self):
                    return {'id': 0, 'media_url': self.media_url, 'media_type': self.media_type, 'caption': None}
            return [LegacyMedia()]
        return []

    @property
    def like_count(self):
        return len(self.likes)

    def is_liked_by(self, user_id):
        if not user_id:
            return False
        return any(like.user_id == user_id for like in self.likes)


class PostMedia(db.Model):
    """Lampiran Multi Foto & Video pada Postingan Lini Masa"""
    __tablename__ = 'post_media'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    media_type = db.Column(db.String(20), default='image')  # 'image', 'video'
    media_url = db.Column(db.String(256), nullable=False)
    caption = db.Column(db.String(200), nullable=True)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'media_type': self.media_type,
            'media_url': self.media_url,
            'caption': self.caption,
            'order_index': self.order_index
        }


class PostComment(db.Model):
    """Komentar Diskusi pada Postingan Lini Masa"""
    __tablename__ = 'post_comments'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])


class PostLike(db.Model):
    """Reaksi Salam Lestari / Like pada Postingan"""
    __tablename__ = 'post_likes'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='uq_post_user_like'),)


class ChatMessage(db.Model):
    """Obrolan Basecamp Bersama & Direct Message Pribadi"""
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # None = Obrolan Publik Basecamp; Integer = Pesan Pribadi DM
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])
    recipient = db.relationship('User', foreign_keys=[recipient_id])


class SystemSetting(db.Model):
    """Pengaturan Konfigurasi Global Aplikasi & Gateway"""
    __tablename__ = 'system_settings'

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, key, default=None):
        item = cls.query.filter_by(key=key).first()
        return item.value if item and item.value is not None else default

    @classmethod
    def set(cls, key, value, description=None):
        item = cls.query.filter_by(key=key).first()
        if not item:
            item = cls(key=key, value=str(value), description=description)
            db.session.add(item)
        else:
            item.value = str(value)
            if description:
                item.description = description
        db.session.commit()
        return item


class AdminAuditLog(db.Model):
    """Rekaman Log Aktivitas Admin (Keamanan & Akuntabilitas)"""
    __tablename__ = 'admin_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(64), nullable=False)
    target_type = db.Column(db.String(64), nullable=True)
    target_id = db.Column(db.String(64), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship('User', foreign_keys=[admin_id])


class MapRepository(db.Model):
    """Pustaka Geodata & Repo Peta Ekspedisi Internal GIMBAL"""
    __tablename__ = 'map_repositories'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    region = db.Column(db.String(100), default='Gorontalo')  # 'Gorontalo', 'Sulawesi', 'Nasional'
    category = db.Column(db.String(50), default='jalur_pendakian')  # 'jalur_pendakian', 'topografi', 'cagar_alam', 'watershed'
    file_type = db.Column(db.String(20), default='gpx')  # 'mbtiles', 'gpx', 'geojson', 'kml'
    file_path = db.Column(db.String(256), nullable=False)
    file_size_fmt = db.Column(db.String(30), default='1.2 MB')
    preview_image = db.Column(db.String(256), nullable=True)
    description = db.Column(db.Text, nullable=True)
    total_waypoints = db.Column(db.Integer, default=0)
    total_distance_km = db.Column(db.Float, default=0.0)
    is_exclusive_member = db.Column(db.Boolean, default=True)
    is_shared_to_timeline = db.Column(db.Boolean, default=False)
    downloads_count = db.Column(db.Integer, default=0)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploader = db.relationship('User', foreign_keys=[uploaded_by])


class Position(db.Model):
    """Master Jabatan & Struktur Organisasi KPAB GIMBAL"""
    __tablename__ = 'positions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50), default='Pengurus Harian')  # 'Pengurus Harian', 'Divisi Operasional', 'Divisi Pendukung', 'Dewan Kehormatan', 'Keanggotaan'
    order_index = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def member_count(self):
        """Menghitung jumlah anggota yang mengemban jabatan ini"""
        return User.query.filter_by(jabatan=self.name).count()


# ==============================================================================
# ACADEMY, E-LEARNING, SOP & SERTIFIKASI KESIAPAN OPERASIONAL
# ==============================================================================

class AcademyTier(db.Model):
    """Tingkatan / Jenjang Pendidikan Keanggotaan (Level 1: Calon, Level 2: Pra-Penuh, Level 3: Senior)"""
    __tablename__ = 'academy_tiers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    badge_name = db.Column(db.String(100), nullable=False)
    badge_icon = db.Column(db.String(50), default='fa-compass')
    badge_color = db.Column(db.String(30), default='#10b981')
    description = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, default=1)
    passing_grade = db.Column(db.Integer, default=75)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    courses = db.relationship('AcademyCourse', backref='tier', cascade='all, delete-orphan', order_by='AcademyCourse.order_index')
    quizzes = db.relationship('AcademyQuiz', backref='tier', cascade='all, delete-orphan')

    @property
    def total_lessons(self):
        return sum(len(c.lessons) for c in self.courses)

    @property
    def title(self):
        return self.name

    @title.setter
    def title(self, val):
        self.name = val

    @property
    def passing_score(self):
        return self.passing_grade

    @passing_score.setter
    def passing_score(self, val):
        self.passing_grade = val

    @property
    def target_audience(self):
        if self.order_index == 1:
            return 'Calon Anggota & Diksar'
        elif self.order_index == 2:
            return 'Menuju Anggota Penuh'
        return 'Komandan Lapangan & Instruktur'


class AcademyCourse(db.Model):
    """Mata Diklat / Kursus Pelatihan Spesifik (misal: SOP Navigasi, Survival, PPGD)"""
    __tablename__ = 'academy_courses'

    id = db.Column(db.Integer, primary_key=True)
    tier_id = db.Column(db.Integer, db.ForeignKey('academy_tiers.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='diksar') # 'sop', 'diksar', 'survival', 'ppgd', 'navigasi', 'manajemen'
    description = db.Column(db.Text, nullable=True)
    thumbnail = db.Column(db.String(256), nullable=True)
    target_duration_mins = db.Column(db.Integer, default=30)
    order_index = db.Column(db.Integer, default=1)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lessons = db.relationship('AcademyLesson', backref='course', cascade='all, delete-orphan', order_by='AcademyLesson.order_index')
    quiz = db.relationship('AcademyQuiz', backref='course', uselist=False, cascade='all, delete-orphan')


class AcademyLesson(db.Model):
    """Bab / Unit Materi Pelajaran Pembelajaran (Teks Panduan, PDF SOP, Video, Peta)"""
    __tablename__ = 'academy_lessons'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('academy_courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content_type = db.Column(db.String(30), default='article') # 'article', 'pdf_doc', 'video', 'map_link'
    content_body = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String(500), nullable=True)
    doc_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    map_repo_id = db.Column(db.Integer, db.ForeignKey('map_repositories.id'), nullable=True)
    order_index = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    doc = db.relationship('Document', foreign_keys=[doc_id])
    map_repo = db.relationship('MapRepository', foreign_keys=[map_repo_id])

    @property
    def content(self):
        return self.content_body or ''

    @content.setter
    def content(self, val):
        self.content_body = val

    @property
    def video_url(self):
        return self.media_url

    @video_url.setter
    def video_url(self, val):
        self.media_url = val

    @property
    def duration_minutes(self):
        return (self.course.target_duration_mins if self.course else 15) or 15

    @duration_minutes.setter
    def duration_minutes(self, val):
        pass

    @property
    def summary(self):
        if not self.content_body:
            return ''
        import re
        clean = re.sub(r'<[^>]+>', ' ', self.content_body).strip()
        return (clean[:90] + '...') if len(clean) > 90 else clean

    @summary.setter
    def summary(self, val):
        pass


class AcademyQuiz(db.Model):
    """Ujian / Kuis Sertifikasi Kesiapan Lapangan"""
    __tablename__ = 'academy_quizzes'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('academy_courses.id'), nullable=True)
    tier_id = db.Column(db.Integer, db.ForeignKey('academy_tiers.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    passing_score = db.Column(db.Integer, default=75) # Minimal persen benar (0-100)
    time_limit_mins = db.Column(db.Integer, default=20)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    questions = db.relationship('QuizQuestion', backref='quiz', cascade='all, delete-orphan', order_by='QuizQuestion.order_index')
    attempts = db.relationship('UserQuizAttempt', backref='quiz', cascade='all, delete-orphan')

    @property
    def time_limit_minutes(self):
        return self.time_limit_mins or 20

    @time_limit_minutes.setter
    def time_limit_minutes(self, val):
        self.time_limit_mins = val


class QuizQuestion(db.Model):
    """Butir Soal Evaluasi / Ujian"""
    __tablename__ = 'quiz_questions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('academy_quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='multiple_choice')
    explanation = db.Column(db.Text, nullable=True)
    points = db.Column(db.Integer, default=10)
    order_index = db.Column(db.Integer, default=1)

    options = db.relationship('QuizOption', backref='question', cascade='all, delete-orphan', order_by='QuizOption.order_index')


class QuizOption(db.Model):
    """Opsi Pilihan Jawaban Soal (A, B, C, D)"""
    __tablename__ = 'quiz_options'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_questions.id'), nullable=False)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    order_index = db.Column(db.Integer, default=1)


class UserLessonProgress(db.Model):
    """Rekam Jejak Bacaan / Bab yang Telah Diselesaikan Anggota"""
    __tablename__ = 'user_lesson_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('academy_lessons.id'), nullable=False)
    is_completed = db.Column(db.Boolean, default=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])
    lesson = db.relationship('AcademyLesson', foreign_keys=[lesson_id])


class UserQuizAttempt(db.Model):
    """Riwayat Pengerjaan Kuis Anggota"""
    __tablename__ = 'user_quiz_attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('academy_quizzes.id'), nullable=False)
    score = db.Column(db.Float, default=0.0) # 0 - 100
    passed = db.Column(db.Boolean, default=False)
    total_questions = db.Column(db.Integer, default=0)
    correct_answers = db.Column(db.Integer, default=0)
    answers_json = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])


class UserCertification(db.Model):
    """Sertifikat Kesiapan Lapangan & Lencana Keahlian Resmi GIMBAL"""
    __tablename__ = 'user_certifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tier_id = db.Column(db.Integer, db.ForeignKey('academy_tiers.id'), nullable=False)
    certificate_no = db.Column(db.String(64), unique=True, nullable=False)
    status = db.Column(db.String(20), default='active') # 'active', 'expired', 'revoked'
    score_achieved = db.Column(db.Float, default=100.0)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id])
    tier = db.relationship('AcademyTier', foreign_keys=[tier_id])

    @property
    def certificate_number(self):
        return self.certificate_no

    @certificate_number.setter
    def certificate_number(self, val):
        self.certificate_no = val


class Inquiry(db.Model):
    """Pesan Masuk, Permintaan Pengawalan Pendakian & Kemitraan Publik KPAB GIMBAL"""
    __tablename__ = 'inquiries'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), default='general')  # 'guiding', 'membership', 'sponsorship', 'general'
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    subject = db.Column(db.String(200), nullable=True)
    message = db.Column(db.Text, nullable=False)

    # Khusus Permintaan Pengawalan Pendakian (Guiding / Escort)
    destination = db.Column(db.String(150), nullable=True)
    target_date = db.Column(db.String(100), nullable=True)
    participants_count = db.Column(db.Integer, default=1)
    services_needed = db.Column(db.String(255), nullable=True)

    status = db.Column(db.String(30), default='pending')  # 'pending', 'contacted', 'assigned', 'completed', 'archived'
    admin_notes = db.Column(db.Text, nullable=True)
    assigned_guide_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assigned_guide = db.relationship('User', foreign_keys=[assigned_guide_id])



