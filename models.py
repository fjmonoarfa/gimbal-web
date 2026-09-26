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
    
    # Status approval
    rejection_reason = db.Column(db.Text, nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relasi
    payments = db.relationship('DuesPayment', foreign_keys='DuesPayment.user_id', backref='user', lazy='dynamic')
    uploaded_docs = db.relationship('Document', backref='uploader', lazy='dynamic')

    @property
    def is_admin(self):
        return self.role in ['admin', 'superadmin']

    @property
    def is_active_member(self):
        return self.status == 'active' and self.nra is not None


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
    amount = db.Column(db.Float, nullable=False, default=20000.0)
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
    proof_image = db.Column(db.String(256), nullable=False)  # Path file bukti transfer
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
    quota = db.Column(db.Integer, default=20)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(256), nullable=True)
    is_open = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    participants = db.relationship('ActivityParticipant', backref='activity', lazy='dynamic', cascade='all, delete-orphan')


class ActivityParticipant(db.Model):
    """Pendaftaran Peserta Ekspedisi"""
    __tablename__ = 'activity_participants'

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='registered')  # 'registered', 'confirmed', 'cancelled'
    notes = db.Column(db.Text, nullable=True)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    activity = db.relationship('Activity', backref=db.backref('gallery_items', lazy='dynamic'))

