import os
import io
import csv
import json
import base64
import qrcode
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, render_template_string, request,
    redirect, url_for, session, send_from_directory, make_response,
    jsonify, Response, abort
)
from werkzeug.utils import secure_filename
from models import (
    db, User, Dues, DuesPayment, Document, Activity,
    ActivityParticipant, GalleryItem, generate_next_nra
)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gimbal-adventure-secret-key-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gimbal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(os.path.join(UPLOAD_FOLDER, 'proofs'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'docs'), exist_ok=True)

db.init_app(app)

# Google OAuth Config
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')


# ========== HELPERS & CONTEXT ====================================================

def get_current_user():
    """Mengambil user aktif dari session, atau default dev user jika belum login."""
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            # Jika belum login, redirect ke halaman login / dev login
            if request.headers.get('HX-Request'):
                return "<script>window.location.href = '/';</script>"
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_admin:
            if request.headers.get('HX-Request'):
                return "<div class='p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs font-bold'>Akses Ditolak: Hanya Pengurus Admin.</div>"
            return redirect('/member/dashboard')
        return f(*args, **kwargs)
    return decorated

@app.context_processor
def inject_global():
    user = get_current_user()
    pending_count = 0
    if user and user.is_admin:
        pending_count = User.query.filter_by(status='pending').count()
    return {
        'current_user': user,
        'pending_count': pending_count,
        'now_str': datetime.now().strftime('%d %B %Y %H:%M WIB')
    }


# ========== DUAL-LAYER HTMX RENDER ENGINE ========================================

def render_gimbal_page(macro_file, macro_name, data_context, active_page=None, alert_msg=None):
    """
    Dual-Layer Rendering Engine (Identik dengan arsitektur Koperasi STU):
    1. Direct browser hit: Return Layer 1 (index.html) with shell_url pointing to this URL.
    2. HTMX targeting #app-shell: Return Layer 2 (shell.html) containing the active page macro.
    3. Normal HTMX targeting #main-content: Return only the active macro fragment.
    """
    user = get_current_user()
    pending_count = User.query.filter_by(status='pending').count() if (user and user.is_admin) else 0

    data_context.update({
        'user': user,
        'current_user': user,
        'pending_count': pending_count,
        'active_page': active_page or macro_name
    })

    # HTMX Request
    if request.headers.get('HX-Request'):
        tmpl = f"{{% import '{macro_file}' as pages %}}{{{{ pages.{macro_name}(data) }}}}"
        macro_html = render_template_string(tmpl, data=data_context, current_user=user)

        # Jika menargetkan outer app-shell
        if request.headers.get('HX-Target') == 'app-shell':
            resp = make_response(render_template(
                'shell.html',
                active_page=active_page or macro_name,
                active_macro_content=macro_html,
                current_user=user,
                pending_count=pending_count,
                alert_msg=alert_msg
            ))
            resp.headers['X-Active-Page'] = active_page or macro_name
            return resp

        # Normal HTMX targeting #main-content
        resp = make_response(macro_html)
        resp.headers['X-Active-Page'] = active_page or macro_name
        return resp

    # Direct browser GET: return Layer 1 outer shell frame pointing to this URL
    return render_template('index.html', shell_url=request.full_path)


# ========== STATIC & ASSET ROUTES ================================================

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)

@app.route('/index.js')
def serve_index_js():
    return send_from_directory('.', 'index.js')

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ========== PUBLIC ROUTES ========================================================

@app.route('/')
def landing():
    """Halaman publik utama GIMBAL"""
    user = get_current_user()
    activities = Activity.query.filter_by(is_open=True).order_by(Activity.created_at.desc()).limit(6).all()
    gallery_items = GalleryItem.query.order_by(GalleryItem.id.desc()).limit(8).all()
    active_members_count = User.query.filter_by(status='active').count()

    return render_template(
        'landing.html',
        current_user=user,
        activities=activities,
        gallery_items=gallery_items,
        active_members_count=active_members_count
    )

@app.route('/app-shell')
def app_shell():
    """Layer 2 Application Shell provider jika app-shell di-load langsung"""
    user = get_current_user()
    if not user:
        # Default dev user jika session kosong saat testing
        user = User.query.filter_by(email='admin@gimbal.org').first()
        if user:
            session['user_id'] = user.id

    if user and user.is_admin:
        return redirect('/admin/dashboard')
    return redirect('/member/dashboard')

@app.route('/verify-kta/<nra>')
def verify_kta(nra):
    """Halaman publik verifikasi keabsahan KTA digital (hasil scan QR)"""
    member = User.query.filter_by(nra=nra).first()
    return render_template('verify_kta.html', member=member, nra_queried=nra)


# ========== AUTH & DEV SWITCHER ==================================================

@app.route('/auth/google-login')
def google_login():
    """
    Google OAuth 2.0 Handler.
    Jika credentials belum dikonfigurasi di environment, beri fallback ramah ke dev login.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        # Mode pengembangan: otomatis redirect ke pemilih akun simulasi
        return redirect('/auth/switch-role?email=calon.petualang@gmail.com')
    
    redirect_uri = url_for('google_callback', _external=True)
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&response_type=code&scope=openid%20email%20profile&"
        f"redirect_uri={redirect_uri}&prompt=select_account"
    )
    return redirect(google_auth_url)

@app.route('/auth/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        return redirect('/')
    # Code token exchange can be executed with requests
    return redirect('/member/dashboard')

@app.route('/auth/switch-role')
def switch_role():
    """
    Developer / Tester role switcher:
    Memungkinkan tester/owner langsung login sebagai Admin, Anggota Aktif, atau Calon Pendaftar
    """
    email = request.args.get('email', 'admin@gimbal.org')
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User.query.first()
    
    if user:
        session['user_id'] = user.id
        if user.is_admin:
            return redirect('/admin/dashboard')
        return redirect('/member/dashboard')
    return redirect('/')

@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect('/')


# ========== MEMBER PORTAL ROUTES =================================================

@app.route('/member/dashboard')
@login_required
def member_dashboard():
    user = get_current_user()
    open_activities = Activity.query.filter_by(is_open=True).order_by(Activity.created_at.desc()).limit(4).all()
    
    # Hitung tagihan yang belum dibayar
    paid_dues_ids = [p.dues_id for p in DuesPayment.query.filter_by(user_id=user.id, status='approved').all()]
    unpaid_count = Dues.query.filter(Dues.id.notin_(paid_dues_ids)).count() if paid_dues_ids else Dues.query.count()

    data = {
        'user': user,
        'open_activities': open_activities,
        'unpaid_count': unpaid_count
    }
    return render_gimbal_page('member/member_pages.html', 'member_dashboard', data, active_page='member_dashboard')

@app.route('/member/kta')
@login_required
def member_kta():
    user = get_current_user()
    if user.status != 'active' or not user.nra:
        return redirect('/member/dashboard')

    # Generate QR Code base64
    qr_img = qrcode.make(f"{request.host_url}verify-kta/{user.nra}")
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    data = {
        'user': user,
        'qr_base64': qr_base64
    }
    return render_gimbal_page('member/member_pages.html', 'member_kta', data, active_page='member_kta')

@app.route('/member/iuran')
@login_required
def member_iuran():
    user = get_current_user()
    active_dues = Dues.query.filter_by(is_active=True).all()
    my_payments = DuesPayment.query.filter_by(user_id=user.id).order_by(DuesPayment.id.desc()).all()

    data = {
        'user': user,
        'active_dues': active_dues,
        'my_payments': my_payments
    }
    return render_gimbal_page('member/member_pages.html', 'member_iuran', data, active_page='member_iuran')

@app.route('/member/iuran/pay-modal/<int:dues_id>')
@login_required
def member_iuran_modal(dues_id):
    dues = Dues.query.get_or_404(dues_id)
    return render_template('components/modals.html', modal_type='pay_dues', dues=dues)

@app.route('/member/iuran/pay/<int:dues_id>', methods=['POST'])
@login_required
def member_iuran_pay(dues_id):
    user = get_current_user()
    dues = Dues.query.get_or_404(dues_id)
    
    bank_name = request.form.get('bank_name', 'Transfer Bank')
    amount_paid = float(request.form.get('amount_paid', dues.amount))
    notes = request.form.get('notes', '')
    
    # Upload proof file
    proof_file = request.files.get('proof_file')
    proof_filename = 'sample_proof.jpg'
    if proof_file and proof_file.filename:
        safe_name = f"proof_{user.id}_{int(datetime.now().timestamp())}_{secure_filename(proof_file.filename)}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], 'proofs', safe_name)
        proof_file.save(save_path)
        proof_filename = f"/uploads/proofs/{safe_name}"
    else:
        proof_filename = '/static/pics/sample_proof.jpg'

    payment = DuesPayment(
        dues_id=dues.id,
        user_id=user.id,
        amount_paid=amount_paid,
        bank_name=bank_name,
        proof_image=proof_filename,
        notes=notes,
        status='pending'
    )
    db.session.add(payment)
    db.session.commit()

    return member_iuran()

@app.route('/member/documents')
@login_required
def member_documents():
    docs = Document.query.filter_by(is_public_to_members=True).order_by(Document.created_at.desc()).all()
    data = {'documents': docs}
    return render_gimbal_page('member/member_pages.html', 'member_documents', data, active_page='member_documents')

@app.route('/member/profile', methods=['GET', 'POST'])
@login_required
def member_profile():
    user = get_current_user()
    if request.method == 'POST':
        user.name = request.form.get('name', user.name)
        user.phone = request.form.get('phone', user.phone)
        user.birth_place = request.form.get('birth_place', user.birth_place)
        user.birth_date = request.form.get('birth_date', user.birth_date)
        user.address = request.form.get('address', user.address)
        user.blood_type = request.form.get('blood_type', user.blood_type)
        user.medical_history = request.form.get('medical_history', user.medical_history)
        user.emergency_name = request.form.get('emergency_name', user.emergency_name)
        user.emergency_relation = request.form.get('emergency_relation', user.emergency_relation)
        user.emergency_phone = request.form.get('emergency_phone', user.emergency_phone)
        db.session.commit()

    data = {'user': user}
    return render_gimbal_page('member/member_pages.html', 'member_profile', data, active_page='member_profile')

@app.route('/member/activity/join/<int:activity_id>', methods=['POST'])
@login_required
def member_activity_join(activity_id):
    user = get_current_user()
    act = Activity.query.get_or_404(activity_id)
    existing = ActivityParticipant.query.filter_by(activity_id=act.id, user_id=user.id).first()
    if not existing:
        part = ActivityParticipant(activity_id=act.id, user_id=user.id, status='registered')
        db.session.add(part)
        db.session.commit()
    return "<div class='text-xs text-emerald-600 font-bold'>Terdaftar!</div>"


# ========== ADMIN BACKEND ROUTES =================================================

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    pending_members = User.query.filter_by(status='pending').order_by(User.id.desc()).all()
    active_count = User.query.filter_by(status='active').count()
    doc_count = Document.query.count()
    
    # Kas masuk dari payments approved
    approved_payments = DuesPayment.query.filter_by(status='approved').all()
    total_cash = sum(p.amount_paid for p in approved_payments)
    
    pending_payments = DuesPayment.query.filter_by(status='pending').order_by(DuesPayment.id.desc()).all()

    current_year_2digit = int(datetime.now().strftime('%y'))
    
    data = {
        'pending_members': pending_members,
        'pending_count': len(pending_members),
        'active_count': active_count,
        'total_cash': total_cash,
        'doc_count': doc_count,
        'pending_payments': pending_payments,
        'pending_payments_count': len(pending_payments),
        'current_year_2digit': current_year_2digit
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_dashboard', data, active_page='admin_dashboard')

@app.route('/admin/approvals')
@login_required
@admin_required
def admin_approvals():
    pending_members = User.query.filter_by(status='pending').order_by(User.id.desc()).all()
    current_year_2digit = int(datetime.now().strftime('%y'))
    
    from sqlalchemy import func
    max_seq = db.session.query(func.max(User.nra_sequence)).filter(User.nra_year == current_year_2digit).scalar() or 0
    next_seq_preview = f"{(max_seq + 1):02d}"

    data = {
        'pending_members': pending_members,
        'current_year_2digit': current_year_2digit,
        'next_seq_preview': next_seq_preview
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_approvals', data, active_page='admin_approvals')

@app.route('/admin/member/approve/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_approve_member(user_id):
    """
    Logika Kesepakatan Approval:
    - nn: nomor urut persetujuan admin pada tahun YY berjalan
    - Reset ulang dari awal (01) di setiap tahun baru
    - Terbitkan nomor resmi R-nn-YY
    """
    user = User.query.get_or_404(user_id)
    admin = get_current_user()

    if user.status != 'active':
        nra_code, year_2digit, seq_num = generate_next_nra()
        user.nra = nra_code
        user.nra_year = year_2digit
        user.nra_sequence = seq_num
        user.status = 'active'
        user.approved_by = admin.id
        user.approved_at = datetime.utcnow()
        db.session.commit()

    return admin_approvals()

@app.route('/admin/member/reject/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_reject_member(user_id):
    user = User.query.get_or_404(user_id)
    user.status = 'rejected'
    db.session.commit()
    return admin_approvals()

@app.route('/admin/members')
@login_required
@admin_required
def admin_members():
    q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    
    query = User.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if q:
        query = query.filter(
            (User.name.ilike(f'%{q}%')) | 
            (User.nra.ilike(f'%{q}%')) | 
            (User.phone.ilike(f'%{q}%'))
        )
    
    members = query.order_by(User.id.desc()).all()
    data = {'members': members, 'q': q, 'status_filter': status_filter}
    return render_gimbal_page('admin/admin_pages.html', 'admin_members', data, active_page='admin_members')

@app.route('/admin/members/export-csv')
@login_required
@admin_required
def admin_export_csv():
    """Ekspor seluruh data anggota ke format CSV"""
    members = User.query.order_by(User.id.asc()).all()
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'NRA', 'Nama Lengkap', 'Email', 'No. WhatsApp', 'Gol. Darah', 'Status', 'Kontak Darurat', 'Hubungan', 'No. Telp Darurat', 'Tgl Bergabung'])
    
    for m in members:
        cw.writerow([
            m.id,
            m.nra or '',
            m.name,
            m.email,
            m.phone or '',
            m.blood_type or '',
            m.status,
            m.emergency_name or '',
            m.emergency_relation or '',
            m.emergency_phone or '',
            m.created_at.strftime('%Y-%m-%d') if m.created_at else ''
        ])
    
    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = f"attachment; filename=gimbal_members_{datetime.now().strftime('%Y%m%d')}.csv"
    response.headers['Content-type'] = 'text/csv; charset=utf-8'
    return response

@app.route('/admin/dues')
@login_required
@admin_required
def admin_dues():
    payments = DuesPayment.query.order_by(DuesPayment.id.desc()).all()
    all_dues = Dues.query.order_by(Dues.id.desc()).all()
    data = {'payments': payments, 'all_dues': all_dues}
    return render_gimbal_page('admin/admin_pages.html', 'admin_dues', data, active_page='admin_dues')

@app.route('/admin/dues/create-modal')
@login_required
@admin_required
def admin_create_dues_modal():
    return render_template('components/modals.html', modal_type='create_dues')

@app.route('/admin/dues/create', methods=['POST'])
@login_required
@admin_required
def admin_create_dues():
    title = request.form.get('title')
    amount = float(request.form.get('amount', 25000))
    category = request.form.get('category', 'wajib')
    due_date = request.form.get('due_date', '')
    description = request.form.get('description', '')

    new_dues = Dues(
        title=title,
        amount=amount,
        category=category,
        due_date=due_date,
        description=description,
        is_active=True
    )
    db.session.add(new_dues)
    db.session.commit()
    return admin_dues()

@app.route('/admin/dues/verify/<int:payment_id>', methods=['POST'])
@login_required
@admin_required
def admin_verify_dues(payment_id):
    pay = DuesPayment.query.get_or_404(payment_id)
    status = request.args.get('status', 'approved')
    admin = get_current_user()
    
    pay.status = status
    pay.verified_by = admin.id
    pay.verified_at = datetime.utcnow()
    db.session.commit()
    return admin_dues()

@app.route('/admin/documents')
@login_required
@admin_required
def admin_documents():
    docs = Document.query.order_by(Document.created_at.desc()).all()
    data = {'documents': docs}
    return render_gimbal_page('admin/admin_pages.html', 'admin_documents', data, active_page='admin_documents')

@app.route('/admin/documents/create-modal')
@login_required
@admin_required
def admin_create_doc_modal():
    return render_template('components/modals.html', modal_type='create_document')

@app.route('/admin/documents/create', methods=['POST'])
@login_required
@admin_required
def admin_create_doc():
    admin = get_current_user()
    title = request.form.get('title')
    category = request.form.get('category', 'ad_art')
    description = request.form.get('description', '')
    is_public = bool(request.form.get('is_public_to_members', 1))

    doc_file = request.files.get('doc_file')
    file_path = '/static/docs/ad_art_gimbal.pdf'
    file_size_fmt = '1.8 MB'

    if doc_file and doc_file.filename:
        filename = f"doc_{int(datetime.now().timestamp())}_{secure_filename(doc_file.filename)}"
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], 'docs', filename)
        doc_file.save(full_path)
        file_path = f"/uploads/docs/{filename}"
        file_size_fmt = f"{round(os.path.getsize(full_path) / (1024 * 1024), 1)} MB"

    new_doc = Document(
        title=title,
        category=category,
        description=description,
        file_path=file_path,
        file_size_fmt=file_size_fmt,
        is_public_to_members=is_public,
        uploaded_by=admin.id
    )
    db.session.add(new_doc)
    db.session.commit()
    return admin_documents()

@app.route('/admin/documents/delete/<int:doc_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_doc(doc_id):
    doc = Document.query.get_or_404(doc_id)
    db.session.delete(doc)
    db.session.commit()
    return admin_documents()

@app.route('/admin/activities')
@login_required
@admin_required
def admin_activities():
    acts = Activity.query.order_by(Activity.created_at.desc()).all()
    data = {'activities': acts}
    return render_gimbal_page('admin/admin_pages.html', 'admin_activities', data, active_page='admin_activities')

@app.route('/admin/activity/create-modal')
@login_required
@admin_required
def admin_create_activity_modal():
    return render_template('components/modals.html', modal_type='create_activity')

@app.route('/admin/activity/create', methods=['POST'])
@login_required
@admin_required
def admin_create_activity():
    title = request.form.get('title')
    location = request.form.get('location')
    activity_date = request.form.get('activity_date')
    difficulty = request.form.get('difficulty', 'Menengah')
    quota = int(request.form.get('quota', 20))
    image_url = request.form.get('image_url')
    description = request.form.get('description', '')

    new_act = Activity(
        title=title,
        location=location,
        activity_date=activity_date,
        difficulty=difficulty,
        quota=quota,
        image_url=image_url,
        description=description,
        is_open=True
    )
    db.session.add(new_act)
    db.session.commit()
    return admin_activities()


# =================================================================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print(">>> GIMBAL WebApps running on http://127.0.0.1:8083")
    app.run(host='0.0.0.0', port=8083, debug=True)
