import os
import io
import csv
import json
from datetime import datetime
from flask import Blueprint, request, redirect, render_template, make_response, current_app, flash, jsonify
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from models import (
    db, User, Dues, DuesPayment, Document, Activity,
    ActivityParticipant, ActivityFieldLog, GalleryItem, Post, PostMedia,
    PostComment, PostLike, ChatMessage, SystemSetting, AdminAuditLog,
    MapRepository, Position, generate_next_nra, Sponsor, SponsorProduct,
    AcademyTier, AcademyCourse, AcademyLesson, AcademyQuiz, QuizQuestion, QuizOption,
    UserLessonProgress, UserQuizAttempt, UserCertification, Inquiry
)
from cloudflare_email import delete_cloudflare_email_rule, sync_cloudflare_email_routing
from helpers import get_current_user, login_required, admin_required, render_gimbal_page

admin_bp = Blueprint('admin_pages', __name__)

# ========== ADMIN DASHBOARD & APPROVALS ==========================================

@admin_bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    pending_members = User.query.filter_by(status='pending').order_by(User.id.desc()).all()
    active_count = User.query.filter_by(status='active').count()
    doc_count = Document.query.count()
    
    approved_payments = DuesPayment.query.filter_by(status='approved').all()
    total_cash = sum(p.amount_paid for p in approved_payments)
    
    pending_payments = DuesPayment.query.filter_by(status='pending').order_by(DuesPayment.id.desc()).all()
    current_year_2digit = int(datetime.now().strftime('%y'))
    
    # Perpesanan & Pengawalan Masuk dari Landing Page
    recent_inquiries = Inquiry.query.order_by(Inquiry.id.desc()).limit(6).all()
    pending_inquiries_count = Inquiry.query.filter_by(status='pending').count()
    guiding_inquiries_count = Inquiry.query.filter_by(category='guiding').count()

    data = {
        'pending_members': pending_members,
        'pending_count': len(pending_members),
        'active_count': active_count,
        'total_cash': total_cash,
        'doc_count': doc_count,
        'pending_payments': pending_payments,
        'pending_payments_count': len(pending_payments),
        'current_year_2digit': current_year_2digit,
        'recent_inquiries': recent_inquiries,
        'pending_inquiries_count': pending_inquiries_count,
        'guiding_inquiries_count': guiding_inquiries_count
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_dashboard', data, active_page='admin_dashboard')


@admin_bp.route('/admin/approvals')
@login_required
@admin_required
def admin_approvals():
    pending_members = User.query.filter_by(status='pending').order_by(User.id.desc()).all()
    current_year_2digit = int(datetime.now().strftime('%y'))
    
    from sqlalchemy import func
    max_seq = db.session.query(func.max(User.nra_sequence)).filter(User.nra_year == current_year_2digit).scalar() or 0
    next_seq_preview = f"{(max_seq + 1):02d}"

    dues_enabled = (SystemSetting.get('dues_enabled', 'true').lower() == 'true')
    data = {
        'pending_members': pending_members,
        'current_year_2digit': current_year_2digit,
        'next_seq_preview': next_seq_preview,
        'dues_enabled': dues_enabled
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_approvals', data, active_page='admin_approvals')


@admin_bp.route('/admin/member/approve/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_approve_member(user_id):
    """
    Approval Calon Anggota & Penerbitan NRA Resmi:
    - Format: R-nn-YY (nn urut dalam tahun YY)
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

        # Otomatis verifikasi pembayaran iuran calon anggota menjadi approved
        pending_payments = DuesPayment.query.filter_by(user_id=user.id, status='pending').all()
        for p in pending_payments:
            p.status = 'approved'
            p.verified_by = admin.id
            p.verified_at = datetime.utcnow()

        log = AdminAuditLog(
            admin_id=admin.id,
            action='approve_member',
            target_type='User',
            target_id=user.id,
            details=f"Menyetujui anggota {user.name} dan menerbitkan NRA {nra_code}"
        )
        db.session.add(log)
        db.session.commit()

    return admin_approvals()


@admin_bp.route('/admin/member/reject/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_reject_member(user_id):
    admin = get_current_user()
    user = User.query.get_or_404(user_id)
    user.status = 'rejected'
    
    log = AdminAuditLog(
        admin_id=admin.id,
        action='reject_member',
        target_type='User',
        target_id=user.id,
        details=f"Menolak pendaftaran anggota: {user.name} ({user.email})"
    )
    db.session.add(log)
    db.session.commit()
    return admin_approvals()


# ========== MEMBER MANAGEMENT & CRUD =============================================

@admin_bp.route('/admin/members')
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


@admin_bp.route('/admin/members/create-modal')
@login_required
@admin_required
def admin_create_member_modal():
    positions = Position.query.filter_by(is_active=True).order_by(Position.order_index.asc(), Position.id.asc()).all()
    return render_template('components/modals.html', modal_type='create_member', positions=positions)


@admin_bp.route('/admin/members/create', methods=['POST'])
@admin_bp.route('/admin/member/create', methods=['POST'])
@login_required
@admin_required
def admin_create_member():
    admin = get_current_user()
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    status = request.form.get('status', 'pending')
    password = request.form.get('password', '').strip() or 'gimbal123'
    
    role = request.form.get('role', 'member').strip()
    if role == 'superadmin' and not admin.is_superadmin:
        role = 'member'
        flash("Hanya Superadmin yang berhak membuat akun dengan hak akses Superadmin.", "error")
        
    if not name or not email:
        flash("Nama dan email wajib diisi.", "error")
        return admin_members()
        
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash(f"Email '{email}' sudah terdaftar dalam sistem.", "error")
        return admin_members()
        
    avatar_file = request.files.get('avatar_file')
    avatar_url = request.form.get('avatar_url', '').strip()
    avatar_path = '/static/pics/cartoon/avatar_sekjen.jpg'
    if avatar_file and avatar_file.filename:
        orig_filename = secure_filename(avatar_file.filename)
        ext = os.path.splitext(orig_filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
            safe_name = f"avatar_member_{int(datetime.utcnow().timestamp())}{ext}"
            save_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
            os.makedirs(save_dir, exist_ok=True)
            avatar_file.save(os.path.join(save_dir, safe_name))
            avatar_path = f"/uploads/avatars/{safe_name}"
    elif avatar_url:
        avatar_path = avatar_url
        
    jabatan = request.form.get('jabatan', '').strip()
    member = User(
        name=name,
        email=email,
        phone=phone,
        jabatan=jabatan,
        role=role,
        status=status,
        password_hash=password,
        avatar=avatar_path
    )
    if status == 'active':
        nra_code, year_2digit, seq_num = generate_next_nra()
        member.nra = nra_code
        member.nra_year = year_2digit
        member.nra_sequence = seq_num
        member.approved_by = admin.id
        member.approved_at = datetime.utcnow()
        
    db.session.add(member)
    log = AdminAuditLog(
        admin_id=admin.id,
        action='create_member',
        target_type='User',
        details=f"Pendaftaran manual anggota: {name} ({email}) peran {role}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Akun pengguna baru '{name}' ({role.upper()}) berhasil didaftarkan.", "success")
    return admin_members()


@admin_bp.route('/admin/member/edit-modal/<int:user_id>')
@login_required
@admin_required
def admin_edit_member_modal(user_id):
    target_member = User.query.get_or_404(user_id)
    positions = Position.query.filter_by(is_active=True).order_by(Position.order_index.asc(), Position.id.asc()).all()
    from_activity = request.args.get('from_activity', '').strip()
    from_tab = request.args.get('from_tab', 'manifest').strip()
    return render_template('components/modals.html', modal_type='edit_member', target_member=target_member, positions=positions, from_activity=from_activity, from_tab=from_tab)


@admin_bp.route('/admin/member/edit/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_edit_member(user_id):
    admin = get_current_user()
    member = User.query.get_or_404(user_id)
    
    member.name = request.form.get('name', member.name).strip()
    member.email = request.form.get('email', member.email).strip().lower()
    member.phone = request.form.get('phone', member.phone).strip()
    member.jabatan = request.form.get('jabatan', member.jabatan or '').strip()
    new_status = request.form.get('status', member.status)
    new_role = request.form.get('role', member.role)
    
    # Upload Foto Profil / Avatar Anggota Baru
    avatar_file = request.files.get('avatar_file')
    avatar_url = request.form.get('avatar_url', '').strip()
    if avatar_file and avatar_file.filename:
        orig_filename = secure_filename(avatar_file.filename)
        ext = os.path.splitext(orig_filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
            safe_name = f"avatar_{member.id}_{int(datetime.utcnow().timestamp())}{ext}"
            save_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
            os.makedirs(save_dir, exist_ok=True)
            avatar_file.save(os.path.join(save_dir, safe_name))
            member.avatar = f"/uploads/avatars/{safe_name}"
    elif avatar_url:
        member.avatar = avatar_url
    
    # Pengaturan Peran / Hak Akses (Superadmin, Admin, Member)
    if new_role:
        if member.email == 'fitra@gimbal.org':
            member.role = 'superadmin'
        elif admin.is_superadmin:
            member.role = new_role
        elif admin.is_admin:
            if new_role == 'superadmin':
                flash("Akses Terbatas: Hanya Superadmin yang berhak mengangkat akun menjadi Superadmin.", "error")
            else:
                member.role = new_role
    
    nra_input = request.form.get('nra', '').strip()
    if nra_input:
        member.nra = nra_input
    elif new_status == 'active' and not member.nra:
        nra_code, year_2digit, seq_num = generate_next_nra()
        member.nra = nra_code
        member.nra_year = year_2digit
        member.nra_sequence = seq_num
        member.approved_by = admin.id
        member.approved_at = datetime.utcnow()
        
    member.status = new_status
    member.birth_place = request.form.get('birth_place', member.birth_place)
    member.birth_date = request.form.get('birth_date', member.birth_date)
    member.blood_type = request.form.get('blood_type', member.blood_type)
    member.address = request.form.get('address', member.address)
    member.medical_history = request.form.get('medical_history', member.medical_history)
    member.emergency_name = request.form.get('emergency_name', member.emergency_name)
    member.emergency_relation = request.form.get('emergency_relation', member.emergency_relation)
    member.emergency_phone = request.form.get('emergency_phone', member.emergency_phone)
    
    log = AdminAuditLog(
        admin_id=admin.id,
        action='update_member',
        target_type='User',
        target_id=member.id,
        details=f"Memperbarui biodata, avatar & peran anggota: {member.name} ({member.email}) peran '{member.role}'"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Data dan hak akses anggota '{member.name}' berhasil diperbarui.", "success")
    from_activity = request.form.get('from_activity', '').strip()
    from_tab = request.form.get('from_tab', 'manifest').strip()
    if from_activity and from_activity.isdigit():
        return admin_activity_manage(int(from_activity), tab=from_tab)
    return admin_members()


@admin_bp.route('/admin/member/reset-password-modal/<int:user_id>')
@login_required
@admin_required
def admin_reset_member_password_modal(user_id):
    target_member = User.query.get_or_404(user_id)
    return render_template('components/modals.html', modal_type='reset_member_password', target_member=target_member)


@admin_bp.route('/admin/member/reset-password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_reset_member_password(user_id):
    admin = get_current_user()
    member = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', 'gimbal123').strip()
    member.password_hash = new_password
    
    log = AdminAuditLog(
        admin_id=admin.id,
        action='reset_password',
        target_type='User',
        target_id=member.id,
        details=f"Mereset kata sandi anggota: {member.name} ({member.email})"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Kata sandi untuk '{member.name}' berhasil direset.", "success")
    return admin_members()


@admin_bp.route('/admin/member/toggle-status/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_member_status(user_id):
    """Opsi Proper: Menonaktifkan/mengarsipkan akun tanpa menghapus relasi kas/data (Soft Deactivation)"""
    admin = get_current_user()
    member = User.query.get_or_404(user_id)

    if member.id == admin.id:
        flash(f"Gagal mengubah status '{member.name}': Anda tidak dapat menonaktifkan akun Anda sendiri.", "error")
        return admin_members()

    if member.role == 'superadmin' and not admin.is_superadmin and member.email != 'fitra@gimbal.org':
        flash(f"Status akun Superadmin dilindungi sistem.", "error")
        return admin_members()

    # Toggle antara 'active' dan 'inactive' (nonaktif)
    if member.status == 'active':
        member.status = 'inactive'
        action_text = "dinonaktifkan (akses portal diblokir)"
    else:
        member.status = 'active'
        action_text = "diaktifkan kembali"

    log = AdminAuditLog(
        admin_id=admin.id,
        action='toggle_member_status',
        target_type='User',
        target_id=member.id,
        details=f"Mengubah status akun {member.name} menjadi: {member.status}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Akun pengguna '{member.name}' berhasil {action_text}. Seluruh data iuran kas dan dokumen tetap aman.", "success")
    return admin_members()


@admin_bp.route('/admin/member/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_member(user_id):
    admin = get_current_user()
    member = User.query.get_or_404(user_id)
    
    # 1. Lindungi diri sendiri
    if member.id == admin.id:
        flash(f"Gagal menghapus '{member.name}': Anda tidak dapat menghapus akun Anda sendiri saat sedang aktif digunakan.", "error")
        return admin_members()

    # 2. Lindungi akun Superadmin
    if member.role == 'superadmin' and member.email != 'fitra@gimbal.org':
        flash(f"Gagal menghapus '{member.name}': Akun Superadmin dilindungi sistem dan tidak dapat dihapus.", "error")
        return admin_members()

    # 3. Batasi jika target adalah admin namun penghapus bukan superadmin
    if member.is_admin and not admin.is_superadmin and member.email != 'fitra@gimbal.org':
        flash(f"Gagal menghapus '{member.name}': Akun pengurus admin hanya dapat dikelola atau dihapus oleh Superadmin melalui menu Pengaturan.", "error")
        return admin_members()
        
    try:
        # Bersihkan seluruh relasi foreign key terkait user ini secara hierarkis & menyeluruh
        # A. Postingan pengguna: Hapus semua komentar & like pada postingan milik pengguna ini terlebih dahulu
        user_posts = Post.query.filter_by(user_id=member.id).all()
        for p in user_posts:
            GalleryItem.query.filter_by(post_id=p.id).update({'post_id': None})
            PostMedia.query.filter_by(post_id=p.id).delete()
            PostComment.query.filter_by(post_id=p.id).delete()
            PostLike.query.filter_by(post_id=p.id).delete()
            db.session.delete(p)
        
        # B. Komentar & Like yang dibuat pengguna pada postingan anggota lain
        PostLike.query.filter_by(user_id=member.id).delete()
        PostComment.query.filter_by(user_id=member.id).delete()
        
        # C. Obrolan & Pesan (Publik Basecamp & Private DM, baik sebagai pengirim maupun penerima)
        ChatMessage.query.filter(
            (ChatMessage.user_id == member.id) | 
            (ChatMessage.recipient_id == member.id)
        ).delete()
        
        # D. Ekspedisi & Partisipasi Kegiatan
        ActivityParticipant.query.filter_by(user_id=member.id).delete()
        ActivityFieldLog.query.filter_by(user_id=member.id).update({'user_id': None})
        
        # F. Iuran & Keuangan
        DuesPayment.query.filter_by(user_id=member.id).delete()
        DuesPayment.query.filter_by(verified_by=member.id).update({'verified_by': None})
        
        # G. Relasi Foreign Key Nullable Lainnya
        User.query.filter_by(approved_by=member.id).update({'approved_by': None})
        Document.query.filter_by(uploaded_by=member.id).update({'uploaded_by': None})
        MapRepository.query.filter_by(uploaded_by=member.id).update({'uploaded_by': None})
        AdminAuditLog.query.filter_by(admin_id=member.id).update({'admin_id': None})
        Sponsor.query.filter_by(owner_user_id=member.id).update({'owner_user_id': None})
        
        # Jika akun fitra yang dihapus, simpan flag permanen agar startup app.py tidak membuat ulang
        if member.email == 'fitra@gimbal.org' or (member.name and member.name.lower() == 'fitra'):
            SystemSetting.set('fitra_deleted', 'true')

        # H. Bersihkan Rule Cloudflare Email Routing jika terpasang
        try:
            delete_cloudflare_email_rule(member)
        except Exception:
            pass

        log = AdminAuditLog(
            admin_id=admin.id,
            action='delete_member',
            target_type='User',
            target_id=member.id,
            details=f"Menghapus data anggota/user: {member.name} ({member.email})"
        )
        db.session.add(log)
        db.session.delete(member)
        db.session.commit()
        flash(f"Data user '{member.name}' ({member.email}) berhasil dihapus secara permanen beserta seluruh riwayat relasinya.", "success")
    except IntegrityError as ie:
        db.session.rollback()
        err_detail = str(ie.orig) if hasattr(ie, 'orig') else str(ie)
        flash(
            f"Gagal menghapus '{member.name}' karena kendala integritas relasi data (Foreign Key Cascade): {err_detail}. "
            f"Pilihan yang proper: Gunakan tombol 'Nonaktifkan Akun' jika Anda ingin memblokir akses pengguna "
            f"namun tetap mempertahankan akuntabilitas catatan kas dan dokumen organisasi.", 
            "error"
        )
    except Exception as e:
        db.session.rollback()
        flash(f"Gagal menghapus data user '{member.name}' karena kesalahan sistem: {str(e)}", "error")

    return admin_members()


@admin_bp.route('/admin/members/export-csv')
@login_required
@admin_required
def admin_export_csv():
    """Ekspor seluruh data anggota ke format CSV lengkap dengan status login & email forwarding"""
    members = User.query.order_by(User.id.asc()).all()
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow([
        'ID', 'NRA', 'Nama Lengkap', 'Email Asli', 'Email Forwarding (@gimbal.my.id)', 
        'No. WhatsApp', 'Jabatan', 'Peran', 'Status', 'Gol. Darah', 
        'Terakhir Masuk (Last Login)', 'Kontak Darurat', 'Hubungan', 'No. Telp Darurat', 'Tgl Bergabung'
    ])
    
    for m in members:
        last_login_str = m.last_login.strftime('%Y-%m-%d %H:%M:%S WIB') if m.last_login else 'Belum pernah'
        cw.writerow([
            m.id,
            m.nra or '',
            m.name,
            m.email,
            m.gimbal_alias_email or '',
            m.phone or '',
            m.jabatan or '',
            m.role or 'member',
            m.status,
            m.blood_type or '',
            last_login_str,
            m.emergency_name or '',
            m.emergency_relation or '',
            m.emergency_phone or '',
            m.created_at.strftime('%Y-%m-%d') if m.created_at else ''
        ])
    
    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = f"attachment; filename=gimbal_members_{datetime.now().strftime('%Y%m%d')}.csv"
    response.headers['Content-type'] = 'text/csv; charset=utf-8'
    return response


# ========== DUES MANAGEMENT ======================================================

@admin_bp.route('/admin/dues')
@login_required
@admin_required
def admin_dues():
    payments = DuesPayment.query.order_by(DuesPayment.id.desc()).all()
    all_dues = Dues.query.order_by(Dues.id.desc()).all()
    data = {'payments': payments, 'all_dues': all_dues}
    return render_gimbal_page('admin/admin_pages.html', 'admin_dues', data, active_page='admin_dues')


@admin_bp.route('/admin/dues/create-modal')
@login_required
@admin_required
def admin_create_dues_modal():
    return render_template('components/modals.html', modal_type='create_dues')


@admin_bp.route('/admin/dues/create', methods=['POST'])
@login_required
@admin_required
def admin_create_dues():
    admin = get_current_user()
    title = request.form.get('title', '').strip() or 'Tagihan Iuran Baru'
    amount = float(request.form.get('amount', 15000))
    category = request.form.get('category', 'wajib')
    due_date = request.form.get('due_date', '')
    description = request.form.get('description', '')
    is_active = bool(int(request.form.get('is_active', 1)))

    new_dues = Dues(
        title=title,
        amount=amount,
        category=category,
        due_date=due_date,
        description=description,
        is_active=is_active
    )
    db.session.add(new_dues)
    log = AdminAuditLog(
        admin_id=admin.id,
        action='create_dues',
        target_type='Dues',
        details=f"Menambahkan jenis iuran baru '{title}' (Rp {amount:,.0f}) kategori {category}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Jenis iuran '{title}' berhasil ditambahkan.", "success")
    if request.referrer and 'settings' in request.referrer:
        return admin_settings(initial_tab='dues')
    return admin_dues()


@admin_bp.route('/admin/dues/edit-modal/<int:dues_id>')
@login_required
@admin_required
def admin_edit_dues_modal(dues_id):
    dues = Dues.query.get_or_404(dues_id)
    return render_template('components/modals.html', modal_type='edit_dues', dues=dues)


@admin_bp.route('/admin/dues/edit/<int:dues_id>', methods=['POST'])
@login_required
@admin_required
def admin_edit_dues(dues_id):
    admin = get_current_user()
    dues = Dues.query.get_or_404(dues_id)
    dues.title = request.form.get('title', dues.title).strip()
    dues.amount = float(request.form.get('amount', dues.amount))
    dues.category = request.form.get('category', dues.category)
    dues.due_date = request.form.get('due_date', dues.due_date)
    dues.is_active = bool(int(request.form.get('is_active', 1)))
    dues.description = request.form.get('description', dues.description).strip()
    
    if dues.category == 'wajib' and dues.is_active:
        SystemSetting.set('monthly_dues_amount', str(int(dues.amount)))
        
    log = AdminAuditLog(
        admin_id=admin.id,
        action='edit_dues',
        target_type='Dues',
        target_id=dues.id,
        details=f"Mengubah tarif iuran '{dues.title}' menjadi Rp {dues.amount:,.0f} oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Data iuran '{dues.title}' berhasil diperbarui.", "success")
    if request.referrer and 'settings' in request.referrer:
        return admin_settings(initial_tab='dues')
    return admin_dues()


@admin_bp.route('/admin/dues/toggle-active/<int:dues_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_dues_active(dues_id):
    admin = get_current_user()
    dues = Dues.query.get_or_404(dues_id)
    dues.is_active = not dues.is_active
    db.session.commit()
    
    status_label = "Diaktifkan" if dues.is_active else "Dinonaktifkan"
    log = AdminAuditLog(
        admin_id=admin.id,
        action='toggle_dues_active',
        target_type='Dues',
        target_id=dues.id,
        details=f"Status iuran '{dues.title}' diubah menjadi: {status_label} oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Status iuran '{dues.title}' berhasil {status_label.lower()}.", "success")
    if request.referrer and 'settings' in request.referrer:
        return admin_settings(initial_tab='dues')
    return admin_dues()


@admin_bp.route('/admin/dues/delete/<int:dues_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_dues(dues_id):
    admin = get_current_user()
    dues = Dues.query.get_or_404(dues_id)
    title = dues.title
    
    DuesPayment.query.filter_by(dues_id=dues.id).delete()
    db.session.delete(dues)
    
    log = AdminAuditLog(
        admin_id=admin.id,
        action='delete_dues',
        target_type='Dues',
        target_id=dues_id,
        details=f"Menghapus jenis iuran '{title}' secara permanen oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Jenis iuran '{title}' berhasil dihapus.", "success")
    if request.referrer and 'settings' in request.referrer:
        return admin_settings(initial_tab='dues')
    return admin_dues()


@admin_bp.route('/admin/dues/verify/<int:payment_id>', methods=['POST'])
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


# ========== ADMIN SETTINGS & MANAGEMENT ROUTES ===================================

@admin_bp.route('/admin/settings')
@login_required
@admin_required
def admin_settings(initial_tab=None, active_page='admin_settings'):
    """Portal Pengaturan Sistem, Web Admin CRUD, Member Management, Dues, Midtrans, Rekening & Tema"""
    active_tab = initial_tab or request.args.get('tab', 'organization')
    admins = User.query.filter(User.role.in_(['admin', 'superadmin'])).order_by(User.id.asc()).all()
    members = User.query.order_by(User.id.desc()).all()
    active_dues = Dues.query.filter_by(category='wajib').order_by(Dues.id.desc()).first() or Dues.query.order_by(Dues.id.desc()).first()
    dues_enabled = (SystemSetting.get('dues_enabled', 'true').lower() == 'true')
    all_dues = Dues.query.order_by(Dues.id.desc()).all()
    positions = Position.query.order_by(Position.order_index.asc(), Position.id.asc()).all()
    audit_logs = AdminAuditLog.query.order_by(AdminAuditLog.id.desc()).limit(100).all()
    sponsors = Sponsor.query.order_by(Sponsor.order_index.asc(), Sponsor.id.desc()).all()
    
    is_prod = SystemSetting.get('midtrans_is_production', 'false').lower() == 'true'
    settings = {
        'dues_enabled': dues_enabled,
        'midtrans_mode': 'production' if is_prod else 'sandbox',
        'midtrans_client_key': SystemSetting.get('midtrans_client_key', ''),
        'midtrans_server_key': SystemSetting.get('midtrans_server_key', ''),
        'midtrans_merchant_id': SystemSetting.get('midtrans_merchant_id', ''),
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
        'payment_instructions': SystemSetting.get('payment_instructions', 'Silakan transfer tepat sejumlah tarif iuran, lalu simpan dan lampirkan bukti transfer.'),
        'theme_color': SystemSetting.get('theme_color', 'orange'),
        'site_width': SystemSetting.get('site_width', '85%'),
        'app_tagline': SystemSetting.get('app_tagline', 'Generasi Indonesia Menyatu Bersama Alam'),
        'cloudflare_enabled': (SystemSetting.get('cloudflare_enabled', 'false').lower() == 'true'),
        'cloudflare_api_token': SystemSetting.get('cloudflare_api_token', ''),
        'cloudflare_zone_id': SystemSetting.get('cloudflare_zone_id', ''),
        'cloudflare_domain': SystemSetting.get('cloudflare_domain', 'gimbal.my.id'),
        'gemini_api_key': SystemSetting.get('gemini_api_key', os.environ.get('GEMINI_API_KEY', ''))
    }
    data = {
        'active_tab': active_tab,
        'initial_tab': active_tab,
        'admins': admins,
        'members': members,
        'active_dues': active_dues,
        'all_dues': all_dues,
        'positions': positions,
        'sponsors': sponsors,
        'dues_enabled': dues_enabled,
        'settings': settings,
        'audit_logs': audit_logs
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_settings', data, active_page=active_page)


@admin_bp.route('/admin/sponsors')
@login_required
@admin_required
def admin_sponsors():
    """Halaman Penuh Mandiri: Manajemen Sponsorship & Kemitraan Korporat Organisasi"""
    tier_filter = request.args.get('tier')
    category_filter = request.args.get('category')

    query = Sponsor.query.filter_by(is_member_business=False)
    if tier_filter:
        query = query.filter_by(tier=tier_filter)
    if category_filter:
        query = query.filter_by(category=category_filter)
    official_sponsors = query.order_by(Sponsor.order_index.asc(), Sponsor.id.desc()).all()

    member_businesses = Sponsor.query.filter_by(is_member_business=True).order_by(Sponsor.id.desc()).all()

    total_sponsors = Sponsor.query.filter_by(is_member_business=False).count()
    active_timeline_count = Sponsor.query.filter_by(is_shared_to_timeline=True).count()
    total_products = SponsorProduct.query.count()
    total_member_businesses = len(member_businesses)

    data = {
        'sponsors': official_sponsors,
        'member_businesses': member_businesses,
        'total_sponsors': total_sponsors,
        'active_timeline_count': active_timeline_count,
        'total_products': total_products,
        'total_member_businesses': total_member_businesses,
        'selected_tier': tier_filter,
        'selected_category': category_filter
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_sponsors', data, active_page='admin_sponsors')


@admin_bp.route('/admin/settings/cloudflare', methods=['POST'])
@login_required
@admin_required
def admin_settings_cloudflare():
    """Pengaturan Otomatisasi Cloudflare Email Routing API (@gimbal.my.id)"""
    admin = get_current_user()
    if not admin.is_superadmin:
        flash("Hanya Superadmin yang berhak mengubah konfigurasi Cloudflare API.", "error")
        if request.headers.get('HX-Request'):
            return admin_settings(initial_tab='cloudflare')
        return redirect('/admin/settings?tab=cloudflare')

    cloudflare_enabled = 'true' if request.form.get('cloudflare_enabled') else 'false'
    api_token = request.form.get('cloudflare_api_token', '').strip()
    zone_id = request.form.get('cloudflare_zone_id', '').strip()
    domain = request.form.get('cloudflare_domain', 'gimbal.my.id').strip() or 'gimbal.my.id'

    SystemSetting.set('cloudflare_enabled', cloudflare_enabled, 'Status aktif Cloudflare Email Routing')
    SystemSetting.set('cloudflare_api_token', api_token, 'API Token Cloudflare')
    SystemSetting.set('cloudflare_zone_id', zone_id, 'Zone ID Cloudflare')
    SystemSetting.set('cloudflare_domain', domain, 'Domain email forwarding')

    gemini_key = request.form.get('gemini_api_key', '').strip()
    if gemini_key:
        SystemSetting.set('gemini_api_key', gemini_key, 'Gemini API Key untuk Moderasi AI')
        os.environ['GEMINI_API_KEY'] = gemini_key

    log = AdminAuditLog(
        admin_id=admin.id,
        action='update_cloudflare_settings',
        target_type='SystemSetting',
        details=f"Memperbarui konfigurasi Cloudflare & API Integrasi: enabled={cloudflare_enabled}, domain={domain}"
    )
    db.session.add(log)
    db.session.commit()
    flash("Konfigurasi Cloudflare Email Forwarding (@gimbal.my.id) berhasil disimpan.", "success")
    if request.headers.get('HX-Request'):
        return admin_settings(initial_tab='cloudflare')
    return redirect('/admin/settings?tab=cloudflare')


@admin_bp.route('/admin/settings/organization', methods=['POST'])
@login_required
@admin_required
def admin_settings_organization():
    """Pengaturan Informasi Rekening Resmi & Profil Organisasi KPAB GIMBAL"""
    admin = get_current_user()
    
    bank_primary_name = request.form.get('bank_primary_name', 'Bank Mandiri').strip()
    bank_primary_number = request.form.get('bank_primary_number', '131-00-1829-3321').strip()
    bank_primary_holder = request.form.get('bank_primary_holder', 'KPAB GIMBAL KAS PUSAT').strip()
    
    bank_secondary_name = request.form.get('bank_secondary_name', 'Bank BCA').strip()
    bank_secondary_number = request.form.get('bank_secondary_number', '593-019-4821').strip()
    bank_secondary_holder = request.form.get('bank_secondary_holder', 'KPAB GIMBAL KAS PUSAT').strip()
    
    org_name = request.form.get('org_name', 'KPAB GIMBAL Provinsi Gorontalo').strip()
    org_phone = request.form.get('org_phone', '+62 812-3456-7890').strip()
    org_email = request.form.get('org_email', 'sekretariat@gimbal.org').strip()
    org_address = request.form.get('org_address', 'Jl. Pangeran Hidayat No. 45, Kota Gorontalo').strip()
    payment_instructions = request.form.get('payment_instructions', '').strip()
    
    SystemSetting.set('bank_primary_name', bank_primary_name)
    SystemSetting.set('bank_primary_number', bank_primary_number)
    SystemSetting.set('bank_primary_holder', bank_primary_holder)
    SystemSetting.set('bank_secondary_name', bank_secondary_name)
    SystemSetting.set('bank_secondary_number', bank_secondary_number)
    SystemSetting.set('bank_secondary_holder', bank_secondary_holder)
    SystemSetting.set('org_name', org_name)
    SystemSetting.set('org_phone', org_phone)
    SystemSetting.set('org_email', org_email)
    SystemSetting.set('org_address', org_address)
    if payment_instructions:
        SystemSetting.set('payment_instructions', payment_instructions)
        
    log = AdminAuditLog(
        admin_id=admin.id,
        action='update_organization_settings',
        target_type='SystemSetting',
        details=f"Memperbarui rekening bank & profil organisasi oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash("Pengaturan rekening kas dan identitas organisasi berhasil disimpan.", "success")
    if request.headers.get('HX-Request'):
        return admin_settings(initial_tab='organization')
    return redirect('/admin/settings?tab=organization')


@admin_bp.route('/admin/settings/theme', methods=['POST'])
@login_required
@admin_required
def admin_settings_theme():
    """Pengaturan Warna Tema Organisasi & Lebar Konten Layar"""
    admin = get_current_user()
    theme_color = request.form.get('theme_color', 'orange').strip().lower()
    site_width = request.form.get('site_width', '85%').strip()
    app_tagline = request.form.get('app_tagline', '').strip()
    
    valid_colors = ['orange', 'emerald', 'blue', 'amber', 'rose', 'teal']
    if theme_color in valid_colors:
        SystemSetting.set('theme_color', theme_color)
    if site_width:
        SystemSetting.set('site_width', site_width)
    if app_tagline:
        SystemSetting.set('app_tagline', app_tagline)
        
    log = AdminAuditLog(
        admin_id=admin.id,
        action='update_theme_settings',
        target_type='SystemSetting',
        details=f"Tema warna diset ke '{theme_color}' dan lebar situs ke '{site_width}' oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Pengaturan skema warna tema dan tampilan berhasil diperbarui: Tema '{theme_color.upper()}', Lebar '{site_width}'.", "success")
    if request.headers.get('HX-Request'):
        return admin_settings(initial_tab='theme')
    return redirect('/admin/settings?tab=theme')


@admin_bp.route('/admin/settings/dues', methods=['POST'])
@login_required
@admin_required
def admin_settings_dues():
    admin = get_current_user()
    title = request.form.get('dues_title', 'Iuran Wajib Bulanan Anggota').strip()
    amount = float(request.form.get('dues_amount', 15000))
    due_date = request.form.get('due_date', '').strip()
    description = request.form.get('description', '').strip()
    is_active = request.form.get('is_active', '1') in ['1', 'true', 'on', 'yes']
    
    SystemSetting.set('monthly_dues_amount', str(int(amount)))
    SystemSetting.set('dues_enabled', 'true' if is_active else 'false')
    
    active_dues = Dues.query.filter_by(category='wajib').order_by(Dues.id.desc()).first() or Dues.query.order_by(Dues.id.desc()).first()
    if active_dues:
        active_dues.title = title
        active_dues.amount = amount
        active_dues.is_active = is_active
        if due_date:
            active_dues.due_date = due_date
        if description:
            active_dues.description = description
    else:
        active_dues = Dues(
            title=title,
            amount=amount,
            category='wajib',
            due_date=due_date,
            description=description,
            is_active=is_active
        )
        db.session.add(active_dues)
    
    status_label = "Aktif (Enabled)" if is_active else "Nonaktif (Disabled)"
    log = AdminAuditLog(
        admin_id=admin.id,
        action='update_dues_setting',
        target_type='Dues',
        target_id=active_dues.id if active_dues else None,
        details=f"Pengaturan iuran bulanan diperbarui: Status={status_label}, Nominal=Rp {amount:,.0f} oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Pengaturan iuran berhasil disimpan! Status: {status_label}, Nominal: Rp {amount:,.0f}.", "success")
    if request.headers.get('HX-Request'):
        return admin_settings(initial_tab='organization')
    return redirect('/admin/settings?tab=organization')


@admin_bp.route('/admin/settings/midtrans', methods=['POST'])
@login_required
@admin_required
def admin_settings_midtrans():
    admin = get_current_user()
    mode = request.form.get('midtrans_mode', 'sandbox').strip().lower()
    client_key = request.form.get('midtrans_client_key', '').strip()
    server_key = request.form.get('midtrans_server_key', '').strip()
    merchant_id = request.form.get('midtrans_merchant_id', '').strip()
    
    SystemSetting.set('midtrans_is_production', 'true' if mode == 'production' else 'false')
    if client_key:
        SystemSetting.set('midtrans_client_key', client_key)
    if server_key:
        SystemSetting.set('midtrans_server_key', server_key)
    if merchant_id:
        SystemSetting.set('midtrans_merchant_id', merchant_id)
        
    log = AdminAuditLog(
        admin_id=admin.id,
        action='update_midtrans_config',
        target_type='SystemSetting',
        details=f"Konfigurasi Midtrans diperbarui (Mode: {mode.upper()}) oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash("Konfigurasi Midtrans berhasil disimpan.", "success")
    if request.headers.get('HX-Request'):
        return admin_settings(initial_tab='midtrans')
    return redirect('/admin/settings?tab=midtrans')


@admin_bp.route('/admin/admins/create-modal')
@login_required
@admin_required
def admin_create_admin_modal():
    return render_template('components/modals.html', modal_type='create_admin')


@admin_bp.route('/admin/admins/create', methods=['POST'])
@login_required
@admin_required
def admin_create_admin():
    admin = get_current_user()
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    role = request.form.get('role', 'admin').strip()
    password = request.form.get('password', '').strip()
    
    if not email or not name or not password:
        flash("Gagal: Mohon lengkapi seluruh kolom wajib nama, email, dan kata sandi.", "error")
        return redirect('/admin/members')
        
    existing = User.query.filter_by(email=email).first()
    if existing:
        existing.role = role
        existing.password_hash = password
        existing.status = 'active'
    else:
        new_user = User(
            name=name,
            email=email,
            role=role,
            status='active',
            password_hash=password,
            avatar='/static/pics/cartoon/avatar_sekjen.jpg'
        )
        db.session.add(new_user)
    
    log = AdminAuditLog(
        admin_id=admin.id,
        action='create_admin',
        target_type='User',
        details=f"Menambahkan akun admin baru: {name} ({email}) peran {role}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Akun administrator '{name}' ({role.upper()}) berhasil dibuat.", "success")
    return redirect('/admin/members')


@admin_bp.route('/admin/admins/edit-modal/<int:user_id>')
@login_required
@admin_required
def admin_edit_admin_modal(user_id):
    target_admin = User.query.get_or_404(user_id)
    return render_template('components/modals.html', modal_type='edit_admin', target_admin=target_admin)


@admin_bp.route('/admin/admins/edit/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_edit_admin(user_id):
    admin = get_current_user()
    target = User.query.get_or_404(user_id)
    
    if target.email == 'fitra@gimbal.org' and target.id != admin.id:
        flash("Akses Ditolak: Akun Superadmin utama tidak dapat diubah oleh admin lain.", "error")
        return redirect('/admin/members')
        
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    role = request.form.get('role', target.role)
    status = request.form.get('status', target.status)
    new_password = request.form.get('new_password', '').strip()
    
    if name:
        target.name = name
    if email:
        target.email = email
    if role:
        if target.email == 'fitra@gimbal.org':
            target.role = 'superadmin'
        else:
            target.role = role
    if status:
        target.status = status
    if new_password:
        target.password_hash = new_password
        
    log = AdminAuditLog(
        admin_id=admin.id,
        action='update_admin',
        target_type='User',
        target_id=target.id,
        details=f"Memperbarui profil admin {target.name} ({target.email})"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Data administrator '{target.name}' berhasil diperbarui.", "success")
    return redirect('/admin/members')


@admin_bp.route('/admin/admins/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_admin(user_id):
    admin = get_current_user()
    target = User.query.get_or_404(user_id)
    
    if target.id == admin.id:
        if not request.headers.get('HX-Request'):
            return "Gagal: Anda tidak dapat mencabut hak akses akun Anda sendiri saat sedang aktif digunakan.", 400
        flash("Gagal: Anda tidak dapat mencabut hak akses akun Anda sendiri saat sedang aktif digunakan.", "error")
        return redirect('/admin/members')
        
    if target.role == 'superadmin' and not admin.is_superadmin and target.email != 'fitra@gimbal.org':
        flash("Akses Terbatas: Hanya Superadmin yang berhak mencabut hak akses Superadmin lain.", "error")
        return redirect('/admin/members')
        
    log = AdminAuditLog(
        admin_id=admin.id,
        action='delete_admin',
        target_type='User',
        target_id=target.id,
        details=f"Menghapus hak admin: {target.name} ({target.email})"
    )
    db.session.add(log)
    target.role = 'member'
    db.session.commit()
    flash(f"Hak akses admin untuk '{target.name}' telah dicabut (kembali menjadi Anggota biasa).", "success")
    return redirect('/admin/members')


# ========== JABATAN & STRUKTUR ORGANISASI CRUD ===================================

@admin_bp.route('/admin/positions/create-modal')
@login_required
@admin_required
def admin_create_position_modal():
    return render_template('components/modals.html', modal_type='create_position')


@admin_bp.route('/admin/positions/create', methods=['POST'])
@login_required
@admin_required
def admin_create_position():
    admin = get_current_user()
    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'Pengurus Harian').strip()
    order_index = int(request.form.get('order_index', 0) or 0)
    description = request.form.get('description', '').strip()
    is_active = request.form.get('is_active', '1') in ['1', 'true', 'on', 'yes']

    if not name:
        flash("Gagal: Nama jabatan tidak boleh kosong.", "error")
        return admin_settings(initial_tab='positions')

    existing = Position.query.filter_by(name=name).first()
    if existing:
        flash(f"Gagal: Jabatan '{name}' sudah terdaftar dalam sistem.", "error")
        return admin_settings(initial_tab='positions')

    pos = Position(
        name=name,
        category=category,
        order_index=order_index,
        description=description,
        is_active=is_active
    )
    db.session.add(pos)
    log = AdminAuditLog(
        admin_id=admin.id,
        action='create_position',
        target_type='Position',
        details=f"Menambahkan master jabatan: '{name}' ({category}) oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Master Jabatan '{name}' berhasil ditambahkan ke struktur organisasi.", "success")
    if request.headers.get('HX-Request'):
        return admin_settings(initial_tab='positions')
    return redirect('/admin/settings?tab=positions')


@admin_bp.route('/admin/positions/edit-modal/<int:pos_id>')
@login_required
@admin_required
def admin_edit_position_modal(pos_id):
    target_pos = Position.query.get_or_404(pos_id)
    return render_template('components/modals.html', modal_type='edit_position', position=target_pos, target_pos=target_pos)


@admin_bp.route('/admin/positions/edit/<int:pos_id>', methods=['POST'])
@login_required
@admin_required
def admin_edit_position(pos_id):
    admin = get_current_user()
    pos = Position.query.get_or_404(pos_id)

    old_name = pos.name
    name = request.form.get('name', pos.name).strip()
    category = request.form.get('category', pos.category).strip()
    order_index = int(request.form.get('order_index', pos.order_index) or 0)
    description = request.form.get('description', '').strip()
    is_active = request.form.get('is_active', '1') in ['1', 'true', 'on', 'yes']

    if not name:
        flash("Gagal: Nama jabatan tidak boleh kosong.", "error")
        return admin_settings(initial_tab='positions')

    if name != old_name:
        dup = Position.query.filter(Position.name == name, Position.id != pos.id).first()
        if dup:
            flash(f"Gagal: Nama jabatan '{name}' sudah digunakan.", "error")
            return admin_settings(initial_tab='positions')
        User.query.filter_by(jabatan=old_name).update({'jabatan': name})

    pos.name = name
    pos.category = category
    pos.order_index = order_index
    pos.description = description
    pos.is_active = is_active

    log = AdminAuditLog(
        admin_id=admin.id,
        action='update_position',
        target_type='Position',
        target_id=pos.id,
        details=f"Memperbarui data jabatan '{name}' ({category}) oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Data jabatan '{name}' berhasil diperbarui.", "success")
    if request.headers.get('HX-Request'):
        return admin_settings(initial_tab='positions')
    return redirect('/admin/settings?tab=positions')


@admin_bp.route('/admin/positions/toggle-active/<int:pos_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_position_active(pos_id):
    admin = get_current_user()
    pos = Position.query.get_or_404(pos_id)
    pos.is_active = not pos.is_active

    status_str = "Diaktifkan" if pos.is_active else "Dinonaktifkan"
    log = AdminAuditLog(
        admin_id=admin.id,
        action='toggle_position_status',
        target_type='Position',
        target_id=pos.id,
        details=f"Status jabatan '{pos.name}' diubah menjadi {status_str} oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Jabatan '{pos.name}' berhasil {status_str}.", "success")
    if request.headers.get('HX-Request'):
        return admin_settings(initial_tab='positions')
    return redirect('/admin/settings?tab=positions')


@admin_bp.route('/admin/positions/delete/<int:pos_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_position(pos_id):
    admin = get_current_user()
    pos = Position.query.get_or_404(pos_id)
    pos_name = pos.name

    User.query.filter_by(jabatan=pos_name).update({'jabatan': None})

    db.session.delete(pos)
    log = AdminAuditLog(
        admin_id=admin.id,
        action='delete_position',
        target_type='Position',
        target_id=pos_id,
        details=f"Menghapus jabatan '{pos_name}' dari struktur organisasi oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Jabatan '{pos_name}' berhasil dihapus dari struktur organisasi.", "success")
    if request.headers.get('HX-Request'):
        return admin_settings(initial_tab='positions')
    return redirect('/admin/settings?tab=positions')


# ========== DOCUMENTS MANAGEMENT =================================================

@admin_bp.route('/admin/documents')
@login_required
@admin_required
def admin_documents():
    CATEGORY_METAS = {
        'ad_art': {'name': 'AD / ART & Dasar Hukum Organisasi', 'icon': 'fa-landmark', 'color': 'text-amber-500'},
        'sop': {'name': 'SOP Keselamatan & Teknis Lapangan', 'icon': 'fa-shield-alt', 'color': 'text-rose-500'},
        'materi': {'name': 'Materi & Modul Pelatihan', 'icon': 'fa-graduation-cap', 'color': 'text-blue-500'},
        'sk_resmi': {'name': 'Surat Keputusan (SK) & Notulensi', 'icon': 'fa-stamp', 'color': 'text-emerald-500'},
    }

    docs = Document.query.order_by(Document.created_at.desc()).all()

    grouped_docs = {}
    for k, meta in CATEGORY_METAS.items():
        grouped_docs[k] = {
            'key': k,
            'name': meta['name'],
            'icon': meta['icon'],
            'color': meta['color'],
            'docs': []
        }

    for doc in docs:
        cat_key = doc.category or 'lainnya'
        if cat_key not in grouped_docs:
            grouped_docs[cat_key] = {
                'key': cat_key,
                'name': cat_key.replace('_', ' ').title(),
                'icon': 'fa-folder',
                'color': 'text-amber-500',
                'docs': []
            }
        grouped_docs[cat_key]['docs'].append(doc)

    data = {
        'documents': docs,
        'grouped_docs': list(grouped_docs.values()),
        'total_docs': len(docs)
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_documents', data, active_page='admin_documents')


@admin_bp.route('/admin/documents/create-modal')
@login_required
@admin_required
def admin_create_doc_modal():
    return render_template('components/modals.html', modal_type='create_document')


@admin_bp.route('/admin/documents/create', methods=['POST'])
@login_required
@admin_required
def admin_create_doc():
    admin = get_current_user()
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'ad_art')
    description = request.form.get('description', '').strip()
    is_public = bool(request.form.get('is_public_to_members', 1))

    file = request.files.get('doc_file') or request.files.get('file')
    file_path = '/static/docs/ad_art_gimbal.pdf'
    file_size_fmt = '2.4 MB'
    file_type = 'pdf'

    if file and file.filename:
        filename = secure_filename(file.filename)
        docs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'docs')
        os.makedirs(docs_dir, exist_ok=True)
        safe_name = f"doc_{int(datetime.now().timestamp())}_{filename}"
        save_path = os.path.join(docs_dir, safe_name)
        file.save(save_path)
        file_path = f"/uploads/docs/{safe_name}"

        file_size_bytes = os.path.getsize(save_path)
        if file_size_bytes > 1024 * 1024:
            file_size_fmt = f"{round(file_size_bytes / (1024 * 1024), 1)} MB"
        else:
            file_size_fmt = f"{round(file_size_bytes / 1024, 1)} KB"

        if '.' in filename:
            file_type = filename.rsplit('.', 1)[1].lower()

    new_doc = Document(
        title=title,
        category=category,
        file_path=file_path,
        file_size_fmt=file_size_fmt,
        file_type=file_type,
        uploaded_by=admin.id,
        is_public_to_members=is_public,
        description=description
    )
    db.session.add(new_doc)

    log = AdminAuditLog(
        admin_id=admin.id,
        action='upload_document',
        target_type='document',
        target_id=str(title),
        details=f"Mengunggah dokumen organisasi '{title}' format {file_type.upper()} ({file_size_fmt})",
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    return admin_documents()


@admin_bp.route('/admin/documents/edit-modal/<int:doc_id>')
@login_required
@admin_required
def admin_edit_doc_modal(doc_id):
    doc = Document.query.get_or_404(doc_id)
    return render_template('components/modals.html', modal_type='edit_document', document=doc)


@admin_bp.route('/admin/documents/edit/<int:doc_id>', methods=['POST'])
@login_required
@admin_required
def admin_edit_doc(doc_id):
    admin = get_current_user()
    doc = Document.query.get_or_404(doc_id)
    doc.title = request.form.get('title', doc.title).strip()
    doc.category = request.form.get('category', doc.category)
    doc.description = request.form.get('description', doc.description).strip()
    doc.is_public_to_members = bool(request.form.get('is_public_to_members', 1))

    file = request.files.get('doc_file') or request.files.get('file')
    if file and file.filename:
        filename = secure_filename(file.filename)
        docs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'docs')
        os.makedirs(docs_dir, exist_ok=True)
        safe_name = f"doc_{int(datetime.now().timestamp())}_{filename}"
        save_path = os.path.join(docs_dir, safe_name)
        file.save(save_path)
        doc.file_path = f"/uploads/docs/{safe_name}"

        file_size_bytes = os.path.getsize(save_path)
        if file_size_bytes > 1024 * 1024:
            doc.file_size_fmt = f"{round(file_size_bytes / (1024 * 1024), 1)} MB"
        else:
            doc.file_size_fmt = f"{round(file_size_bytes / 1024, 1)} KB"

        if '.' in filename:
            doc.file_type = filename.rsplit('.', 1)[1].lower()

    log = AdminAuditLog(
        admin_id=admin.id,
        action='edit_document',
        target_type='document',
        target_id=str(doc.id),
        details=f"Memperbarui dokumen '{doc.title}' format {(doc.file_type or 'pdf').upper()}",
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    return admin_documents()


@admin_bp.route('/admin/documents/delete/<int:doc_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_doc(doc_id):
    doc = Document.query.get_or_404(doc_id)
    # Hapus juga postingan linimasa jika terkait
    Post.query.filter_by(document_id=doc.id).delete()
    db.session.delete(doc)
    db.session.commit()
    return admin_documents()


@admin_bp.route('/admin/documents/toggle-share/<int:doc_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_doc_share(doc_id):
    """Toggle publikasi dokumen resmi ke Linimasa / Feed Anggota (ON/OFF)"""
    doc = Document.query.get_or_404(doc_id)
    doc.is_shared_to_timeline = not bool(doc.is_shared_to_timeline)
    admin = get_current_user()

    if doc.is_shared_to_timeline:
        existing = Post.query.filter_by(document_id=doc.id).first()
        if not existing:
            post = Post(
                user_id=admin.id,
                content=(
                    f"📄 PUBLIKASI DOKUMEN RESMI GIMBAL: {doc.title}\n\n"
                    f"Kategori: {doc.category.replace('_', ' ').upper()} • Format: .{doc.file_type.upper()} ({doc.file_size_fmt})\n\n"
                    f"{doc.description or 'Dokumen pedoman dan arsip resmi organisasi telah tersedia di Pustaka Dokumen Anggota.'}"
                ),
                document_id=doc.id,
                post_type='document'
            )
            db.session.add(post)
    else:
        Post.query.filter_by(document_id=doc.id).delete()

    db.session.commit()

    if doc.is_shared_to_timeline:
        return f"""
        <button type="button"
                hx-post="/admin/documents/toggle-share/{doc.id}"
                hx-swap="outerHTML"
                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 hover:bg-emerald-200 transition shadow-xs cursor-pointer"
                title="Dokumen aktif di Linimasa (Klik untuk matikan)">
            <i class="fas fa-toggle-on text-emerald-600 text-xs"></i>
            <span>Linimasa: ON</span>
        </button>
        """
    else:
        return f"""
        <button type="button"
                hx-post="/admin/documents/toggle-share/{doc.id}"
                hx-swap="outerHTML"
                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200 transition cursor-pointer"
                title="Dokumen belum dibagikan ke Linimasa (Klik untuk bagikan)">
            <i class="fas fa-toggle-off text-slate-400 text-xs"></i>
            <span>Linimasa: OFF</span>
        </button>
        """


# ========== ACTIVITIES MANAGEMENT ================================================

@admin_bp.route('/admin/activities')
@login_required
@admin_required
def admin_activities():
    activities = Activity.query.order_by(Activity.created_at.desc()).all()
    data = {'activities': activities}
    return render_gimbal_page('admin/admin_pages.html', 'admin_activities', data, active_page='admin_activities')


def get_rol_category_presets():
    """
    Koleksi template ROL (Rencana Operasional Lapangan) terstandarisasi KPAB GIMBAL
    berdasarkan ragam jenis kegiatan kepetualangan & kepecintaalaman.
    """
    return {
        'Gunung Hutan': {
            'label': 'Gunung Hutan (Mountaineering / Trekking)',
            'icon': 'fa-mountain',
            'route_plan': (
                "Jalur Pendakian & Checkpoint Standar:\n"
                "• Checkpoint 1 (KM 0): Pos Perizinan / Basecamp SIMAKSI & Briefing Medis\n"
                "• Checkpoint 2 (KM 2.5): Pintu Rimba / Batas Kawasan Konservasi\n"
                "• Checkpoint 3 (KM 5.0): Pos 2 (Sumber Air Terakhir / Water Point)\n"
                "• Checkpoint 4 (KM 7.8): Shelter Pos 3 / Area Bivak & Camp Utama\n"
                "• Checkpoint 5 (KM 9.5): Puncak Sasaran (Summit Attack) & Dokumentasi Patok Triangulasi\n"
                "• Jalur Evakuasi: Lintas punggungan barat menuju Posko Desa Penyangga (Kontingensi)"
            ),
            'team_gear': (
                "• Tenda Dome 4P (2 unit, frame alloy)\n"
                "• Flysheet Pelindung 4x6 meter & Tali Guyline\n"
                "• Kompor Lapangan Windproof & Nesting DS-300 (2 set)\n"
                "• Tabung Gas Butane / Canister (6 kaleng)\n"
                "• Parang Tebas & Tali Webbing Tubular 20 meter\n"
                "• Radio Komunikasi HT VHF 5W (3 unit) + Baterai Cadangan\n"
                "• GPS Handheld / Smartphone dengan Peta Offline Gimbal Maps"
            ),
            'personal_gear': (
                "• Carrier 60-80 Liter + Raincover Waterproof\n"
                "• Sleeping Bag Suhu Ekstrem + Matras Spon/Aluminium\n"
                "• Jaket Windproof/Goretex, Pakaian Hangat Polar, Jas Hujan\n"
                "• Sepatu Trekking Sol Grip + Kaos Kaki Cadangan (3 pasang)\n"
                "• Headlamp LED Waterproof + Baterai Cadangan\n"
                "• Piring, Sendok, Tumbler Air Minum 2L & Peluit Darurat"
            ),
            'food_ration': (
                "• Hari 1: Nasi liwet rempah, kornet daging, telur, sambal botol\n"
                "• Hari 2: Bubur instan, sarden saus tomat, tumis sayur kering\n"
                "• Logistik Jalan: Energy bar, cokelat batangan, biskuit gandum, madu sachet\n"
                "• Minuman Penghangat: Kopi jahe, sari temulawak, susu sachet, teh manis"
            ),
            'medical_kit': (
                "• Tabung Oksigen Portable (Oxycan 500cc - 2 kaleng)\n"
                "• Emergency Thermal Blanket Aluminium (4 lembar)\n"
                "• Kasa steril, verban elastis (Elastic Bandage), mitela segitiga\n"
                "• Povidone Iodine (Betadine), Alkohol 70%, Rivanol\n"
                "• Obat Hipotermia, Penurun Panas (Paracetamol), Anti Maag, Oralit\n"
                "• Salep Otot (Counterpain), Minyak Kayu Putih, Tabir Surya SPF 50"
            ),
            'recommended_roles': ['Pimpinan Perjalanan', 'Navigator', 'Logistik & Konsumsi', 'Medis / P3K', 'Sweeper', 'Dokumentasi & Publikasi']
        },
        'Panjat Tebing': {
            'label': 'Panjat Tebing (Rock Climbing / Big Wall)',
            'icon': 'fa-mountain-city',
            'route_plan': (
                "Pola Lintasan & Rigging Tebing:\n"
                "• Base Staging: Basecamp Kaki Tebing & Verifikasi Kelayakan Alat\n"
                "• Pitch 1 (Grade 5.8 / 25m): Face climbing menuju Hanging Belay Stance 1\n"
                "• Pitch 2 (Grade 5.10a / 30m - Crux): Crack climbing & runner aktif\n"
                "• Pitch 3 (Grade 5.9 / 20m): Slab runout menuju Anchor Station Puncak Tebing\n"
                "• Rute Turun (Extraction): Sistem Rapelling ganda via Anchor Ring Hanger utama\n"
                "• Jalur Darurat: Jalur setapak kontur belakang tebing menuju basecamp"
            ),
            'team_gear': (
                "• Tali Karmantel Dinamis 10.2mm 60 meter (1 rol UIAA)\n"
                "• Tali Karmantel Statis 10.5mm 100 meter (1 rol hauling/safety)\n"
                "• Quickdraw Set / Runner Panjang (16 set)\n"
                "• Webbing Tubular 30 meter & Prusik Cord 6mm (3 set)\n"
                "• Hammer Climbing, Hanger Plate & Bolt Expansion Cadangan (4 set)\n"
                "• Tarp Alas Tali (Rope Bag Tarp) & Haul Bag 50L"
            ),
            'personal_gear': (
                "• Helm Panjat Standar UIAA (Climbing Helmet)\n"
                "• Seat Harness Ergonomis (dilengkapi gear loops)\n"
                "• Sepatu Panjat Tebing (Rock Climbing Shoes)\n"
                "• Belay Device (ATC Guide / Petzl GriGri) & Figure-of-Eight\n"
                "• Carabiner Screw-Lock HMS (minimal 4 pcs)\n"
                "• Chalk Bag + Magnesium Karbonat Padat/Bubuk\n"
                "• Sarung Tangan Belaying Kulit Sintetis (Belay Gloves)"
            ),
            'food_ration': (
                "• Makanan Padat Kalori: Protein bar, roti isi selai kacang, kurma, kismis\n"
                "• Hidrasi: Minuman elektrolit/isotonik 3L per person (Hydration pack)\n"
                "• Makanan Hangat di Basecamp: Sup daging, mie rebus, telur rebus, pisang ambon"
            ),
            'medical_kit': (
                "• Sam Splint (Bidai Busa Aluminium untuk fraktur/patah tulang)\n"
                "• Kasa Kompres Trauma, Perban Elastis 4 inch & 6 inch\n"
                "• Plester Zinc Oxide / Strapping Tape jari & telapak tangan\n"
                "• Antiseptik Cair, Painkiller (Asam Mefenamat/Ibuprofen)\n"
                "• Obat Tetes Mata Steril (Eyewash untuk serpihan debu batu)\n"
                "• Gunting Medis Emergency Trauma Shears & Sarung Tangan Nitril"
            ),
            'recommended_roles': ['Pimpinan Perjalanan', 'Safety Belayer & Rigging Master', 'Equipment Inspector', 'Medis Lapangan', 'Dokumentasi Ekstrem', 'Anggota Tim']
        },
        'Susur Gua': {
            'label': 'Susur Gua (Caving / Speleologi)',
            'icon': 'fa-dungeon',
            'route_plan': (
                "Topografi Karst & Lintasan Gua:\n"
                "• Entrance Pit (Mulut Gua Vertikal): Titik Rigging Utama Pohon/Anchor Alam\n"
                "• Pitch 1 (Drop 35 meter): Single Rope Technique (SRT) Descent & Intermediate Re-belay\n"
                "• Lorong Utama (Horizontal Cave): Sump Area, Stalakmit Hall, Chamber Kelelawar\n"
                "• Sump & Water Flow: Pemetaan aliran sungai bawah tanah & siphon\n"
                "• Titik Exit: Lubang terobosan tembus karst utara atau ascending rute awal\n"
                "• Prosedur Banjir: Evakuasi ke High Ground Chamber jika hujan lebat di hulu"
            ),
            'team_gear': (
                "• Tali Statis Low Stretch 10.5mm 150 meter (2 rol)\n"
                "• SRT Rigging Kit (Spit, Hanger, Webbing, Anchor Pad/Protector)\n"
                "• Tackle Bag Heavy Duty PVC Anti Robek (4 unit)\n"
                "• Peta Gua Speleologi, Kompas Klinometer Suunto, Laser Disto\n"
                "• Pelindung Gesekan Tali (Rope Protector Kanvas & Roller)\n"
                "• Gas Detector / Lilin Penguji Oksigen Ruang Bawah Tanah"
            ),
            'personal_gear': (
                "• Caving Suit / Coverall Tahan Air & Gesekan Karst\n"
                "• Helm Caving + Headlamp Waterproof IPX8 (Dua Sumber Cahaya Independen)\n"
                "• Sepatu Boot Karet (Wellington Boot) dengan Grip Dalam\n"
                "• SRT Set Lengkap: Sit & Chest Harness, Jammer (Croll + Basic), Descender Stop/Simple, Footloop, Cowstail Dinamis\n"
                "• Tas Kedap Air Caving (Drybag 10L) & Peluit"
            ),
            'food_ration': (
                "• Makanan Siap Santap Kedap Air: Nasi bakar aluminium foil, biskuit kaleng\n"
                "• Pemanis Instan: Permen jahe, cokelat pasta, madu murni\n"
                "• Air Minum Botol Keras 2L (Dilarang membuang sisa makanan di dalam gua / LNT)"
            ),
            'medical_kit': (
                "• Thermal Foil Blanket Tebal (Gua basah sangat rentan hipotermia)\n"
                "• Kassa steril, pembalut cepat, antiseptik povidone\n"
                "• Salep luka robek & antibiotik topikal\n"
                "• Splint jari dan lengan, obat anti kram otot, paracetamol\n"
                "• Lampu penerangan cadangan medis & baterai alkaline"
            ),
            'recommended_roles': ['Pimpinan Perjalanan', 'Rigging Master', 'Surveyor Gua / Pemetaan', 'Medis Evakuasi', 'Sweeper Tim', 'Anggota Tim']
        },
        'Arung Jeram': {
            'label': 'Arung Jeram (Rafting / Water Rescue)',
            'icon': 'fa-water',
            'route_plan': (
                "Lintasan Sungai & Jeram:\n"
                "• Put-In Area (KM 0): Safety Talk, Pengenalan Komando Dayung & Flip Drill\n"
                "• Rapid 1 (Grade II): Jeram Pemanasan & Kalibrasi Kekompakan Awak\n"
                "• Rapid 2 (Grade III+ - Jeram Buaya): Undercut rock scouted & penempatan Rescue Rope\n"
                "• Rest Area (KM 6): Pantai Pasir Kali, Pengecekan Tekanan Tabung Perahu\n"
                "• Rapid 3 (Grade IV - Jeram Air Terjun): Drop 1.5m & Standing Waves\n"
                "• Take-Out Area (KM 12): Titik Pendaratan Perahu & Bongkar Muat Armada"
            ),
            'team_gear': (
                "• Perahu Karet Rafting Heavy Duty Self Bailing (2 armada)\n"
                "• Pompa Injak / Tangan Tekanan Tinggi + Manometer\n"
                "• Rescue Throw Bag (Tali Lempar Apung 20m - 2 unit)\n"
                "• Flip Line (Tali Pembalik Perahu) & Carabiner HMS Snag-Free\n"
                "• Repair Kit Lem PVC, Patch Tambalan & Valve Wrench\n"
                "• Dayung Cadangan T-Grip (2 pcs) & Dry Bag Besar (30L)"
            ),
            'personal_gear': (
                "• Pelampung Arung Jeram (Life Jacket Type V / USCG Approved, Buoyancy 22 lbs)\n"
                "• Helm Arung Jeram / Kayak Helmets dengan Ventilasi Air\n"
                "• Dayung Tunggal Ergonomis (Aluminium Shaft & Nylon Blade)\n"
                "• Sepatu Neoprene / Sandal Gunung Tali Tumit Kokoh\n"
                "• Pakaian Cepat Kering (Rashguard / Celana Cepat Kering, Hindari Jeans)\n"
                "• Peluit Tanpa Bola Pea-less (Bekerja maksimal saat basah)"
            ),
            'food_ration': (
                "• Di Perahu (Dry Bag): Gula aren, cokelat bar, biskuit asin, air isotonik\n"
                "• Di Titik Take-Out / Basecamp: Prasmanan sup panas, ikan bakar, teh manis hangat"
            ),
            'medical_kit': (
                "• Pocket Mask CPR Resusitasi Pernapasan Kedap Air\n"
                "• Emergency Thermal Blanket (Mencegah hipotermia air dingin)\n"
                "• Plester Tahan Air (Waterproof Dressing) & Kasa Steril\n"
                "• Minyak Angin Penghangat, Balsem Otot Kram, Antihistamin sengatan air\n"
                "• Tabung Oksigen Siaga di Mobil Pengangkut / Rescue Darat"
            ),
            'recommended_roles': ['Pimpinan Perjalanan', 'Skipper / River Guide Utama', 'Rescue Master & Thrower', 'Logistik Perahu', 'Sweeper Boat Guide', 'Medis Air']
        },
        'Konservasi & LH': {
            'label': 'Konservasi & Lingkungan Hidup (Reboisasi / Riset Flora-Fauna)',
            'icon': 'fa-seedling',
            'route_plan': (
                "Plot Kawasan & Titik Konservasi:\n"
                "• Posko Bibit / Induk: Registrasi Relawan & Serah Terima Bibit Endemik\n"
                "• Plot 1 (Zona Kritis / 2 Hektar): Pembuatan Lubang Tanam & Pemupukan Dasar\n"
                "• Plot 2 (Koridor Perlindungan Mata Air): Penanaman Pohon Beringin/Bambu Penghijau\n"
                "• Jalur Inventarisasi Flora-Fauna: Transek Garis 1.5 KM untuk Identifikasi Spesies\n"
                "• Pos Penimbangan Sampah: Sortir sampah pendaki organik & anorganik (Bersih Gunung)"
            ),
            'team_gear': (
                "• Bibit Pohon Kayu & Buah Hutan (200 - 500 bibit polybag)\n"
                "• Cangkul Kecil, Sekop Mini & Linggis Tanam (10 unit)\n"
                "• Meteran Gulung 50m, Tali Patok & Patok Kayu Label Tanam\n"
                "• Trash Bag Tebal 80x100 cm (10 pack) & Sarung Tangan Safety\n"
                "• Timbangan Gantung Digital (Kapasitas 100 kg untuk audit sampah)\n"
                "• GPS Tracker & Kamera Dokumentasi Titik Koordinat Penanaman"
            ),
            'personal_gear': (
                "• Sarung Tangan Katun/Karet Berlapis Grip Tahan Tusuk\n"
                "• Sepatu Boot Karet / Trekking Lapangan Tahan Lumpur\n"
                "• Topi Rimba Lebar & Kacamata Pelindung Debu/Ranting\n"
                "• Raincoat / Ponco Hujan Lapangan\n"
                "• Buku Catatan Tahan Air (Rite in the Rain) & Spidol Permanen"
            ),
            'food_ration': (
                "• Nasi Kotak / Dapur Lapangan Bersama Panitia\n"
                "• Galon Air Mineral + Gelas Reusable (Bebas Sampah Plastik Sekali Pakai)\n"
                "• Pisang Rebus, Ubi Manis, Kopi & Teh Tubruk"
            ),
            'medical_kit': (
                "• Venom Extractor Pump (Penanganan awal gigitan serangga/hewan berbisa)\n"
                "• Salep Kortikosteroid (Gatal ulat bulu / tanaman jelatang), Antihistamin\n"
                "• Obat Tetes Mata Steril, Betadine, Perban Steril, Hansaplast\n"
                "• Paracetamol, Oralit Cair, Masker Kain/Medis Lapangan"
            ),
            'recommended_roles': ['Pimpinan Perjalanan', 'Koordinator Teknis Penanaman', 'Surveyor Plotting GPS', 'Koordinator Logistik & Bibit', 'Medis Lapangan', 'Dokumentasi & Kampanye']
        },
        'Pendidikan Dasar': {
            'label': 'Pendidikan Dasar & Diklat Petualang (Diksar KPAB)',
            'icon': 'fa-graduation-cap',
            'route_plan': (
                "Pos Lapangan & Rangkaian Materi Latsar:\n"
                "• Pos Induk / Lapangan Utama: Upacara Pembukaan, Apel Disiplin & Cek Kesiapan Perlengkapan\n"
                "• Pos 1 (Navigasi Darat): Pembacaan Peta RBI, Resection/Intersection, Kompas Azimuth\n"
                "• Pos 2 (Jungle Survival): Identifikasi Tumbuhan Makanan, Jebakan Satwa & Air Bersih\n"
                "• Pos 3 (Bivak & Campcraft): Pembuatan Bivak Alami Ponco, Manajemen Sanitasi Camp\n"
                "• Pos 4 (Tali Temali & Pioneering): Anchor, Simpul Dasar & Jembatan Tali Darurat\n"
                "• Rute Long March / Caraka Malam: Jalur Uji Mental Sepanjang 8 KM Jalur Lembah\n"
                "• Lapangan Pengukuhan: Penyematan Brevet / Syal Anggota Muda"
            ),
            'team_gear': (
                "• Tenda Pleton Militer / Barak Panitia & Tenda Medis Lapangan\n"
                "• Sound System Megaphone / Toa Portable (2 unit)\n"
                "• Peta Topografi Lembar Kerja Skala 1:25.000 (15 eksemplar laminasi)\n"
                "• Kompas Bidik Prisma Komando (8 unit), Douglas Protractor, Busur Derajat\n"
                "• Tali Webbing, Tali Karmantel Safety, Parang Tebas (4 bilah)\n"
                "• Peluit Instruktur, Bendera Merah Putih & Bendera KPAB GIMBAL"
            ),
            'personal_gear': (
                "• Ransel Punggung Standar Diksar (Minimal 50L)\n"
                "• Ponco Militer Hijau (Multi-fungsi tenda bivak & jas hujan)\n"
                "• Pakaian Dinas Lapangan PDL (2 setel) + Sepatu Lapangan Kuat\n"
                "• Matras & Sleeping Bag Standar Hangat\n"
                "• Pisau Saku Lipat, Korek Api Kedap Air & Senter Kepala / Senter Tangan\n"
                "• Peluit Sinyal Darurat, Tumbler Air Minum 2 Botol & Perlengkapan Makan Logam"
            ),
            'food_ration': (
                "• Dapur Umum Terpusat: Beras, Sayur Asem, Tahu Tempe, Ikan Asin, Sambal Terasi\n"
                "• Ransum Lapangan Siswa: Biskuit survival padat gizi, mie mentah, telur asin, gula kelapa\n"
                "• Minuman Vitalitas: Susu kental manis hangat, wedang jahe sereh"
            ),
            'medical_kit': (
                "• Tandu Lipat Lapangan (Emergency Stretcher - 2 unit)\n"
                "• Tabung Oksigen Portable 500cc (4 unit)\n"
                "• Kassa steril balut luka, perban gulung, splint patah tulang, mitela segitiga (6 unit)\n"
                "• Rivanol, Alkohol 70%, Povidone Iodine 1 Liter\n"
                "• Obat Maag Kronis, Paracetamol, Dexamethasone, Obat Hipotermia\n"
                "• Larutan Elektrolit & Oralit Massal (1 ember dispenser steril)"
            ),
            'recommended_roles': ['Komandan Latihan (Danlat)', 'Koordinator Instruktur', 'Seksi Medis & Evakuasi', 'Seksi Logistik Dapur Umum', 'Tim Keamanan Jalur & Sweeper', 'Seksi Dokumentasi']
        },
        'Camp & Wisata Alam': {
            'label': 'Camp & Wisata Alam (Family Camp / Eksplorasi Santai)',
            'icon': 'fa-campground',
            'route_plan': (
                "Itinerary & Titik Kumpul Santai:\n"
                "• Meeting Point: Titik Kumpul Parkir Kendaraan / Sekretariat\n"
                "• Camping Ground: Area Tenda Tepi Sungai / Bukit Berumput\n"
                "• Exploration Walk: Jalan Santai Menuju Curug / Spot Sunset\n"
                "• Campfire Area: Titik Api Unggun & Silaturahmi Keluarga Besar\n"
                "• Clean-Up: Operasi Semut Bersih Sampah Bersama Sebelum Pulang"
            ),
            'team_gear': (
                "• Tenda Dome Rekreasi / Keluarga (4-6 Orang)\n"
                "• Flysheet Peneduh Meja Makan & Lampu Gantung LED\n"
                "• Meja & Kursi Lipat Camping Praktis\n"
                "• Kompor Portable Gas Kaleng + Wajan Grill BBQ\n"
                "• Speaker Bluetooth Portable, Gitar Akustik, Trash Bag"
            ),
            'personal_gear': (
                "• Daypack / Ransel Santai 30-40L\n"
                "• Pakaian Santai Outdoor + Jaket Hangat Malam Hari\n"
                "• Sandal Gunung / Sepatu Kets yang Nyaman\n"
                "• Selimut / Sleeping Bag Santai & Bantal Angin\n"
                "• Powerbank Kapasitas Besar & Perlengkapan Mandi"
            ),
            'food_ration': (
                "• Daging Ayam Marinasi BBQ, Jagung Bakar, Sosis, Marshmallow\n"
                "• Nasi Putih / Nasi Kuning Kotak, Kopi Espresso Sachet, Teh Manis\n"
                "• Buah Segar: Semangka, Melon, Pisang"
            ),
            'medical_kit': (
                "• Kotak P3K Standar Keluarga (Hansaplast, Betadine, Minyak Kayu Putih)\n"
                "• Obat Masuk Angin (Tolak Angin), Paracetamol Anak & Dewasa\n"
                "• Lotion Anti Nyamuk / Serangga (Soffell / Autan), Salep Kulit"
            ),
            'recommended_roles': ['Pimpinan Perjalanan', 'Koordinator Konsumsi & BBQ', 'Pemandu Rute Santai', 'Medis P3K Santai', 'Dokumentasi Keluarga & Foto']
        }
    }


@admin_bp.route('/admin/activity/preset-rol', methods=['GET'])
@login_required
@admin_required
def admin_activity_preset_rol():
    """Mengambil template dokumen ROL berdasarkan jenis kegiatan yang dipilih"""
    category = request.args.get('category', 'Gunung Hutan').strip()
    presets = get_rol_category_presets()
    preset = presets.get(category) or presets.get('Gunung Hutan')
    return jsonify({
        'status': 'success',
        'category': category,
        'preset': preset
    })


@admin_bp.route('/admin/activity/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_activity_new():
    """Halaman Full Page untuk membuka agenda ekspedisi baru & inisialisasi ROL"""
    if request.method == 'POST':
        admin = get_current_user()
        title = request.form.get('title', '').strip()
        location = request.form.get('location', '').strip()
        activity_date = request.form.get('activity_date', '').strip()
        difficulty = request.form.get('difficulty', 'Menengah')
        category = request.form.get('category', 'Gunung Hutan').strip()
        quota = int(request.form.get('quota', 20))
        description = request.form.get('description', '').strip()
        phase = request.form.get('phase', 'planning')
        is_open = (phase == 'open')

        image_file = request.files.get('image_file')
        image_url_input = request.form.get('image_url', '').strip()
        image_url = '/static/pics/cartoon/hero.jpg'

        if image_file and image_file.filename:
            safe_name = f"act_{int(datetime.now().timestamp())}_{secure_filename(image_file.filename)}"
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'gallery', safe_name)
            image_file.save(save_path)
            image_url = f"/uploads/gallery/{safe_name}"
        elif image_url_input:
            image_url = image_url_input

        # Ambil template preset bawaan sesuai kategori kegiatan
        presets = get_rol_category_presets()
        active_preset = presets.get(category) or presets.get('Gunung Hutan')

        default_budget = {
            'expense_transport': 0,
            'expense_permit': 0,
            'expense_food': 0,
            'expense_gear': 0,
            'expense_med': 0,
            'expense_emergency': 0,
            'fee_per_person': 0,
            'income_subsidy': 0,
            'income_sponsor': 0
        }
        default_gear = {
            'team_gear': active_preset.get('team_gear', ''),
            'personal_gear': active_preset.get('personal_gear', ''),
            'food_ration': active_preset.get('food_ration', ''),
            'medical_kit': active_preset.get('medical_kit', '')
        }

        new_act = Activity(
            title=title,
            location=location,
            activity_date=activity_date,
            difficulty=difficulty,
            category=category,
            quota=quota,
            description=description,
            image_url=image_url,
            is_open=is_open,
            phase=phase,
            route_plan=active_preset.get('route_plan', ''),
            budget_json=json.dumps(default_budget),
            gear_json=json.dumps(default_gear)
        )
        db.session.add(new_act)
        db.session.commit()

        # Otomatis daftarkan admin pembuat sebagai Pimpinan Perjalanan
        if admin:
            leader_part = ActivityParticipant(
                activity_id=new_act.id,
                user_id=admin.id,
                status='confirmed',
                role='Pimpinan Perjalanan'
            )
            db.session.add(leader_part)
            db.session.commit()

        flash(f'Agenda ekspedisi "{new_act.title}" ({new_act.category}) berhasil dibuat! Silakan lengkapi dokumen ROL.', 'success')
        return redirect(f'/admin/activity/{new_act.id}/manage')

    repo_maps = MapRepository.query.order_by(MapRepository.created_at.desc()).all()
    presets = get_rol_category_presets()
    data = {
        'repo_maps': repo_maps,
        'rol_presets': presets
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_activity_new', data, active_page='admin_activities')


@admin_bp.route('/admin/activity/<int:activity_id>/manage')
@login_required
@admin_required
def admin_activity_manage(activity_id, tab=None):
    """Workspace Terpadu Ekspedisi & ROL (Full Page Command Hub)"""
    act = Activity.query.get_or_404(activity_id)
    participants = ActivityParticipant.query.filter_by(activity_id=act.id).all()
    all_members = User.query.filter_by(status='active').order_by(User.name.asc()).all()
    repo_maps = MapRepository.query.order_by(MapRepository.created_at.desc()).all()
    field_logs = ActivityFieldLog.query.filter_by(activity_id=act.id).order_by(ActivityFieldLog.recorded_at.desc()).all()
    
    if not tab:
        tab = request.args.get('tab') or request.form.get('tab') or 'overview'

    data = {
        'activity': act,
        'participants': participants,
        'all_members': all_members,
        'repo_maps': repo_maps,
        'field_logs': field_logs,
        'rol_presets': get_rol_category_presets(),
        'active_tab': tab
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_activity_manage', data, active_page='admin_activities')


@admin_bp.route('/admin/activity/<int:activity_id>/update-basic', methods=['POST'])
@login_required
@admin_required
def admin_activity_update_basic(activity_id):
    """Memperbarui informasi dasar ekspedisi"""
    act = Activity.query.get_or_404(activity_id)
    act.title = request.form.get('title', act.title).strip()
    act.location = request.form.get('location', act.location).strip()
    act.activity_date = request.form.get('activity_date', act.activity_date).strip()
    act.difficulty = request.form.get('difficulty', act.difficulty)
    act.category = request.form.get('category', act.category or 'Gunung Hutan').strip()
    act.quota = int(request.form.get('quota', act.quota or 20))
    act.is_open = bool(request.form.get('is_open'))
    act.description = request.form.get('description', act.description).strip()

    image_file = request.files.get('image_file')
    image_url_input = request.form.get('image_url', '').strip()
    if image_file and image_file.filename:
        safe_name = f"act_{int(datetime.now().timestamp())}_{secure_filename(image_file.filename)}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'gallery', safe_name)
        image_file.save(save_path)
        act.image_url = f"/uploads/gallery/{safe_name}"
    elif image_url_input:
        act.image_url = image_url_input

    db.session.commit()
    flash('Informasi dasar ekspedisi berhasil diperbarui.', 'success')
    tab = request.args.get('tab') or request.form.get('tab') or 'overview'
    return admin_activity_manage(activity_id, tab=tab)


@admin_bp.route('/admin/activity/<int:activity_id>/update-rol', methods=['POST'])
@login_required
@admin_required
def admin_activity_update_rol(activity_id):
    """Menyimpan Rencana Operasional Lapangan: RAB, Rute, Logistik & Medis"""
    act = Activity.query.get_or_404(activity_id)

    # 1. Budgeting / RAB
    budget = {
        'expense_transport': float(request.form.get('expense_transport', 0) or 0),
        'expense_permit': float(request.form.get('expense_permit', 0) or 0),
        'expense_food': float(request.form.get('expense_food', 0) or 0),
        'expense_gear': float(request.form.get('expense_gear', 0) or 0),
        'expense_med': float(request.form.get('expense_med', 0) or 0),
        'expense_emergency': float(request.form.get('expense_emergency', 0) or 0),
        'fee_per_person': float(request.form.get('fee_per_person', 0) or 0),
        'income_subsidy': float(request.form.get('income_subsidy', 0) or 0),
        'income_sponsor': float(request.form.get('income_sponsor', 0) or 0)
    }
    act.budget_json = json.dumps(budget)

    # 2. Rencana Rute & Pustaka Peta
    act.route_plan = request.form.get('route_plan', act.route_plan)
    map_repo_id = request.form.get('map_repo_id')
    act.map_repo_id = int(map_repo_id) if (map_repo_id and map_repo_id.isdigit()) else None

    # 3. Logistik & Kotak Medis
    gear = {
        'team_gear': request.form.get('team_gear', ''),
        'personal_gear': request.form.get('personal_gear', ''),
        'food_ration': request.form.get('food_ration', ''),
        'medical_kit': request.form.get('medical_kit', '')
    }
    act.gear_json = json.dumps(gear)

    db.session.commit()
    flash('Dokumen ROL (RAB, Rute, Logistik & P3K) berhasil disimpan.', 'success')
    tab = request.args.get('tab') or request.form.get('tab') or 'rol_plan'
    return admin_activity_manage(activity_id, tab=tab)


@admin_bp.route('/admin/activity/<int:activity_id>/update-phase', methods=['POST'])
@login_required
@admin_required
def admin_activity_update_phase(activity_id):
    """Transisi Fase Siklus Hidup Ekspedisi (Planning -> Open -> In Progress -> Completed)"""
    act = Activity.query.get_or_404(activity_id)
    new_phase = request.form.get('phase', act.phase)
    act.phase = new_phase

    if new_phase == 'in_progress':
        act.is_open = False  # Pendaftaran ditutup otomatis saat tim sudah di lapangan
    elif new_phase == 'open':
        act.is_open = True
    elif new_phase == 'completed':
        eval_notes = request.form.get('evaluation_notes')
        if eval_notes:
            act.evaluation_notes = eval_notes.strip()

    db.session.commit()
    flash(f'Status ekspedisi kini diperbarui ke fase: {new_phase.upper()}', 'success')
    tab = request.args.get('tab') or request.form.get('tab')
    if not tab:
        tab = 'field_ops' if new_phase == 'in_progress' else ('close_out' if new_phase == 'completed' else 'overview')
    return admin_activity_manage(activity_id, tab=tab)


@admin_bp.route('/admin/activity/<int:activity_id>/add-participant', methods=['POST'])
@login_required
@admin_required
def admin_activity_add_participant(activity_id):
    """Menambahkan personil anggota ke manifest tim secara manual"""
    act = Activity.query.get_or_404(activity_id)
    user_id = int(request.form.get('user_id'))
    role = request.form.get('role', 'Anggota Tim')

    existing = ActivityParticipant.query.filter_by(activity_id=act.id, user_id=user_id).first()
    if existing:
        existing.status = 'confirmed'
        existing.role = role
    else:
        new_part = ActivityParticipant(
            activity_id=act.id,
            user_id=user_id,
            status='confirmed',
            role=role
        )
        db.session.add(new_part)

    db.session.commit()
    flash('Personil berhasil ditambahkan ke manifest tim.', 'success')
    tab = request.args.get('tab') or request.form.get('tab') or 'manifest'
    return admin_activity_manage(activity_id, tab=tab)


@admin_bp.route('/admin/activity/<int:activity_id>/participant-role/<int:part_id>', methods=['POST'])
@login_required
@admin_required
def admin_activity_update_participant_role(activity_id, part_id):
    """Mengubah peran penugasan personil lapangan"""
    part = ActivityParticipant.query.get_or_404(part_id)
    part.role = request.form.get('role', part.role)
    db.session.commit()
    flash(f'Peran personil {part.user.name if part.user else ""} diubah menjadi: {part.role}', 'success')
    tab = request.args.get('tab') or request.form.get('tab') or 'manifest'
    return admin_activity_manage(activity_id, tab=tab)


@admin_bp.route('/admin/activity/<int:activity_id>/delete-participant/<int:part_id>', methods=['POST'])
@login_required
@admin_required
def admin_activity_delete_participant(activity_id, part_id):
    """Menghapus personil dari manifest"""
    part = ActivityParticipant.query.get_or_404(part_id)
    db.session.delete(part)
    db.session.commit()
    flash('Personil dihapus dari manifest.', 'info')
    tab = request.args.get('tab') or request.form.get('tab') or 'manifest'
    return admin_activity_manage(activity_id, tab=tab)


@admin_bp.route('/admin/activity/<int:activity_id>/add-field-log', methods=['POST'])
@login_required
@admin_required
def admin_activity_add_field_log(activity_id):
    """Input manual laporan titik POI / situasi dari pos lapangan"""
    act = Activity.query.get_or_404(activity_id)
    admin = get_current_user()

    title = request.form.get('title', 'Titik Pantau Lapangan').strip()
    description = request.form.get('description', '').strip()
    lat = float(request.form.get('latitude')) if request.form.get('latitude') else None
    lon = float(request.form.get('longitude')) if request.form.get('longitude') else None
    elevation = float(request.form.get('elevation')) if request.form.get('elevation') else None

    photo_file = request.files.get('photo_file')
    photo_url = None
    if photo_file and photo_file.filename:
        safe_name = f"field_{act.id}_{int(datetime.now().timestamp())}_{secure_filename(photo_file.filename)}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'expeditions', safe_name)
        photo_file.save(save_path)
        photo_url = f"/uploads/expeditions/{safe_name}"

    log = ActivityFieldLog(
        activity_id=act.id,
        user_id=admin.id if admin else None,
        log_type='poi',
        title=title,
        description=description,
        latitude=lat,
        longitude=lon,
        elevation=elevation,
        photo_url=photo_url,
        source='manual'
    )
    db.session.add(log)
    db.session.commit()
    flash(f'Laporan titik POI "{title}" berhasil dicatat.', 'success')
    tab = request.args.get('tab') or request.form.get('tab') or 'field_ops'
    if request.headers.get('HX-Request'):
        return admin_activity_manage(activity_id, tab=tab)
    return redirect(f'/admin/activity/{activity_id}/manage?tab={tab}')


@admin_bp.route('/admin/activity/<int:activity_id>/upload-gimbal-maps', methods=['POST'])
@login_required
@admin_required
def admin_activity_upload_gimbal_maps(activity_id):
    """Unggah berkas GPX / GeoJSON / KMZ hasil ekspor Gimbal-Maps untuk melampirkan titik & track"""
    act = Activity.query.get_or_404(activity_id)
    admin = get_current_user()
    file_upload = request.files.get('geodata_file')

    tab = request.args.get('tab') or request.form.get('tab') or 'field_ops'
    if not file_upload or not file_upload.filename:
        flash('Silakan pilih berkas spasial hasil ekspor Gimbal-Maps (.gpx, .geojson, .kmz)', 'error')
        if request.headers.get('HX-Request'):
            return admin_activity_manage(activity_id, tab=tab)
        return redirect(f'/admin/activity/{activity_id}/manage?tab={tab}')

    safe_name = f"gmaps_{act.id}_{int(datetime.now().timestamp())}_{secure_filename(file_upload.filename)}"
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'expeditions', safe_name)
    file_upload.save(save_path)

    synced_points = 0
    if safe_name.lower().endswith('.gpx'):
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(save_path)
            root = tree.getroot()
            for elem in root.iter():
                if elem.tag.endswith('wpt'):
                    w_lat = elem.attrib.get('lat')
                    w_lon = elem.attrib.get('lon')
                    w_name = 'Waypoint Survei'
                    w_desc = ''
                    w_ele = None
                    for child in elem:
                        if child.tag.endswith('name') and child.text:
                            w_name = child.text
                        elif child.tag.endswith('desc') and child.text:
                            w_desc = child.text
                        elif child.tag.endswith('ele') and child.text:
                            try:
                                w_ele = float(child.text)
                            except Exception:
                                pass
                    log = ActivityFieldLog(
                        activity_id=act.id,
                        user_id=admin.id if admin else None,
                        log_type='poi',
                        title=w_name,
                        description=w_desc,
                        latitude=float(w_lat) if w_lat else None,
                        longitude=float(w_lon) if w_lon else None,
                        elevation=w_ele,
                        source='gimbal_maps'
                    )
                    db.session.add(log)
                    synced_points += 1
        except Exception as e:
            current_app.logger.warning(f"Error parsing GPX: {e}")

    # Simpan file track log
    track_log = ActivityFieldLog(
        activity_id=act.id,
        user_id=admin.id if admin else None,
        log_type='track',
        title=f"Lintasan Peta: {file_upload.filename}",
        description=f"Berkas rekaman spasial diunggah dari Gimbal-Maps ({round(os.path.getsize(save_path)/1024, 1)} KB)",
        photo_url=f"/uploads/expeditions/{safe_name}",
        source='gimbal_maps'
    )
    db.session.add(track_log)
    db.session.commit()

    flash(f'Berkas Gimbal-Maps berhasil diimpor! ({synced_points} titik waypoint diekstrak)', 'success')
    if request.headers.get('HX-Request'):
        return admin_activity_manage(activity_id, tab=tab)
    return redirect(f'/admin/activity/{activity_id}/manage?tab={tab}')


@admin_bp.route('/admin/activity/<int:activity_id>/delete-field-log/<int:log_id>', methods=['POST'])
@login_required
@admin_required
def admin_activity_delete_field_log(activity_id, log_id):
    """Menghapus catatan lapangan / titik POI"""
    log = ActivityFieldLog.query.get_or_404(log_id)
    db.session.delete(log)
    db.session.commit()
    flash('Catatan lapangan berhasil dihapus.', 'info')
    tab = request.args.get('tab') or request.form.get('tab') or 'field_ops'
    if request.headers.get('HX-Request'):
        return admin_activity_manage(activity_id, tab=tab)
    return redirect(f'/admin/activity/{activity_id}/manage?tab={tab}')


@admin_bp.route('/admin/activity/<int:activity_id>/pin-field-photo/<int:log_id>', methods=['POST'])
@login_required
@admin_required
def admin_activity_pin_field_photo(activity_id, log_id):
    """Pin foto dokumentasi lapangan langsung ke Galeri Ekspedisi Landing Page"""
    act = Activity.query.get_or_404(activity_id)
    log = ActivityFieldLog.query.get_or_404(log_id)
    tab = request.args.get('tab') or request.form.get('tab') or 'field_ops'
    if not log.photo_url:
        flash('Catatan lapangan ini tidak memiliki lampiran foto.', 'error')
        if request.headers.get('HX-Request'):
            return admin_activity_manage(activity_id, tab=tab)
        return redirect(f'/admin/activity/{activity_id}/manage?tab={tab}')

    gallery_item = GalleryItem(
        title=log.title,
        caption=log.description or f"Dokumentasi lapangan resmi ekspedisi {act.title} di {act.location}.",
        image_url=log.photo_url,
        activity_id=act.id,
        is_pinned=True
    )
    db.session.add(gallery_item)
    db.session.commit()
    flash(f'Foto "{log.title}" berhasil di-pin ke Galeri Utama Landing Page!', 'success')
    if request.headers.get('HX-Request'):
        return admin_activity_manage(activity_id, tab=tab)
    return redirect(f'/admin/activity/{activity_id}/manage?tab={tab}')


@admin_bp.route('/admin/activity/<int:activity_id>/publish-to-feed', methods=['POST'])
@login_required
@admin_required
def admin_activity_publish_to_feed(activity_id):
    """Mempublikasikan agenda atau laporan ekspedisi ke Linimasa Komunitas / Feed Anggota"""
    act = Activity.query.get_or_404(activity_id)
    admin = get_current_user()

    custom_content = request.form.get('content', '').strip()
    if custom_content:
        content = custom_content
    elif act.phase in ['planning', 'open']:
        content = (
            f"📢 AGENDA EKSPEDISI MENDATANG: {act.title}!\n\n"
            f"KPAB GIMBAL membuka agenda petualangan baru di kawasan {act.location}.\n"
            f"🗓️ Waktu Pelaksanaan: {act.activity_date}\n"
            f"🧗 Kategori: {act.category}\n"
            f"⚡ Tingkat Kesulitan: {act.difficulty}\n"
            f"👥 Kuota Peserta: {act.total_confirmed} / {act.quota} personil terdaftar.\n\n"
            f"{(act.description or 'Ayo persiapkan fisik dan logistik tim untuk bergabung dalam petualangan ini!')}\n\n"
            f"👉 Anggota dapat mendaftarkan diri langsung melalui portal atau melihat ROL resmi."
        )
    elif act.phase == 'in_progress':
        content = (
            f"⛰️ OPERASI LAPANGAN SEDANG BERLANGSUNG: {act.title}!\n\n"
            f"Tim ekspedisi ({act.total_confirmed} personil) saat ini sedang beroperasi di kawasan {act.location} ({act.activity_date}).\n"
            f"Mari kita doakan kelancaran dan keselamatan seluruh personil tim hingga kembali ke Basecamp. Salam Lestari!"
        )
    else:
        content = (
            f"🚩 LAPORAN EKSPEDISI SELESAI: {act.title}!\n\n"
            f"Seluruh personil tim ({act.total_confirmed} orang) telah berhasil menyelesaikan operasi lapangan "
            f"di kawasan {act.location} ({act.activity_date}) dalam kondisi sehat dan selamat. "
            f"Dokumen ROL dan LPJ resmi telah disahkan oleh pengurus."
        )

    existing = Post.query.filter_by(activity_id=act.id, post_type='activity').first()
    if existing:
        post = existing
        post.content = content
        post.location = act.location
        post.image_url = act.image_url
        post.created_at = datetime.utcnow()
        PostMedia.query.filter_by(post_id=post.id).delete()
    else:
        post = Post(
            user_id=admin.id,
            content=content,
            location=act.location,
            activity_id=act.id,
            image_url=act.image_url,
            post_type='activity',
            created_at=datetime.utcnow()
        )
        db.session.add(post)
        db.session.flush()

    # Lampirkan foto-foto dokumentasi lapangan ke PostMedia jika ada
    logs_with_photo = ActivityFieldLog.query.filter_by(activity_id=act.id).filter(ActivityFieldLog.photo_url.isnot(None)).limit(6).all()
    for idx, plog in enumerate(logs_with_photo):
        media = PostMedia(
            post_id=post.id,
            media_url=plog.photo_url,
            media_type='image',
            caption=plog.title,
            order_index=idx
        )
        db.session.add(media)

    act.is_shared_to_timeline = True
    db.session.commit()
    flash('Agenda / dokumentasi ekspedisi berhasil dipublikasikan ke Linimasa Komunitas!', 'success')
    tab = request.args.get('tab') or request.form.get('tab') or ('overview' if act.phase in ['planning', 'open'] else 'close_out')
    if request.headers.get('HX-Request'):
        return admin_activity_manage(activity_id, tab=tab)
    return redirect(f'/admin/activity/{activity_id}/manage?tab={tab}')


@admin_bp.route('/admin/activity/<int:activity_id>/toggle-share', methods=['POST'])
@login_required
@admin_required
def admin_activity_toggle_feed_share(activity_id):
    """Toggle share agenda ekspedisi ke linimasa (ON/OFF)"""
    act = Activity.query.get_or_404(activity_id)
    admin = get_current_user()
    act.is_shared_to_timeline = not bool(act.is_shared_to_timeline)

    if act.is_shared_to_timeline:
        existing = Post.query.filter_by(activity_id=act.id, post_type='activity').first()
        if not existing:
            if act.phase in ['planning', 'open']:
                content = (
                    f"📢 AGENDA EKSPEDISI MENDATANG: {act.title}!\n\n"
                    f"KPAB GIMBAL membuka agenda petualangan baru di kawasan {act.location}.\n"
                    f"🗓️ Waktu Pelaksanaan: {act.activity_date}\n"
                    f"🧗 Kategori: {act.category}\n"
                    f"⚡ Tingkat Kesulitan: {act.difficulty}\n"
                    f"👥 Kuota Peserta: {act.total_confirmed} / {act.quota} personil terdaftar.\n\n"
                    f"{(act.description or 'Ayo persiapkan fisik dan logistik tim untuk bergabung dalam petualangan ini!')}"
                )
            elif act.phase == 'in_progress':
                content = (
                    f"⛰️ OPERASI LAPANGAN SEDANG BERLANGSUNG: {act.title}!\n\n"
                    f"Tim ekspedisi ({act.total_confirmed} personil) saat ini sedang bergerak di kawasan {act.location} ({act.activity_date}).\n"
                    f"Mari kita doakan kelancaran dan keselamatan personil tim. Salam Lestari!"
                )
            else:
                content = (
                    f"🚩 LAPORAN EKSPEDISI: {act.title}!\n\n"
                    f"Operasi lapangan di kawasan {act.location} ({act.activity_date}) telah selesai dengan {act.total_confirmed} personil selamat."
                )

            post = Post(
                user_id=admin.id,
                content=content,
                location=act.location,
                activity_id=act.id,
                image_url=act.image_url,
                post_type='activity'
            )
            db.session.add(post)
    else:
        # Hapus postingan pengumuman agenda ini dari linimasa
        Post.query.filter_by(activity_id=act.id, post_type='activity').delete()

    db.session.commit()

    if act.is_shared_to_timeline:
        return f"""
        <button type="button"
                hx-post="/admin/activity/{act.id}/toggle-share"
                hx-swap="outerHTML"
                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 hover:bg-emerald-200 transition shadow-xs cursor-pointer"
                title="Agenda aktif di Linimasa (Klik untuk matikan)">
            <i class="fas fa-toggle-on text-emerald-600 text-xs"></i>
            <span>Linimasa: ON</span>
        </button>
        """
    else:
        return f"""
        <button type="button"
                hx-post="/admin/activity/{act.id}/toggle-share"
                hx-swap="outerHTML"
                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200 transition cursor-pointer"
                title="Agenda belum dibagikan ke Linimasa (Klik untuk bagikan)">
            <i class="fas fa-toggle-off text-slate-400 text-xs"></i>
            <span>Linimasa: OFF</span>
        </button>
        """


def resolve_rol_signers(act):
    """
    Menemukan penandatangan sah berdasarkan jabatan di database anggota:
    1. Pimpinan Perjalanan (Field Leader) dari peserta terkonfirmasi dengan peran Leader
    2. Kepala Divisi Operasional sesuai jenis/kategori kegiatan
    3. Ketua Umum KPAB GIMBAL
    """
    # 1. Pimpinan Perjalanan
    leader_user = None
    if act.lead_person and act.lead_person.user:
        leader_user = act.lead_person.user
    else:
        first_confirmed = act.participants.filter_by(status='confirmed').first()
        if first_confirmed and first_confirmed.user:
            leader_user = first_confirmed.user

    # 2. Kepala Divisi Operasional berdasarkan jenis kegiatan
    category = act.category or 'Gunung Hutan'
    cat_to_pos = {
        'Gunung Hutan': 'Kepala Divisi Gunung Hutan',
        'Panjat Tebing': 'Kepala Divisi Panjat Tebing',
        'Susur Gua': 'Kepala Divisi Susur Gua (Caving)',
        'Susur Gua (Caving)': 'Kepala Divisi Susur Gua (Caving)',
        'Arung Jeram': 'Kepala Divisi Arung Jeram (Rafting)',
        'Arung Jeram (Rafting)': 'Kepala Divisi Arung Jeram (Rafting)',
        'Konservasi & LH': 'Kepala Divisi Konservasi & LH',
        'Pendidikan Dasar (Diksar)': 'Kepala Divisi Gunung Hutan',
        'Camp & Wisata Alam': 'Kepala Divisi Humas & Publikasi'
    }
    target_pos_name = cat_to_pos.get(category, f"Kepala Divisi {category}")

    # Query pejabat dari database
    kadiv_user = User.query.filter_by(jabatan=target_pos_name).first()
    if not kadiv_user:
        first_word = category.split()[0]
        kadiv_user = User.query.filter(User.jabatan.ilike(f"%{first_word}%")).first()
    if not kadiv_user:
        kadiv_user = User.query.filter(User.jabatan.ilike("%Kepala Divisi%")).first()

    # 3. Ketua Umum KPAB GIMBAL
    ketum_user = User.query.filter_by(jabatan='Ketua Umum').first()
    if not ketum_user:
        ketum_user = User.query.filter(User.role == 'superadmin').first()

    return {
        'leader': leader_user,
        'kadiv': kadiv_user,
        'kadiv_title': target_pos_name,
        'ketum': ketum_user,
        'ketum_title': 'Ketua Umum KPAB GIMBAL'
    }


@admin_bp.route('/admin/activity/<int:activity_id>/print')
@login_required
@admin_required
def admin_activity_print(activity_id):
    """Tampilan Cetak / Print-Ready HTML dokumen ROL & Laporan Ekspedisi (Ctrl+P -> PDF)"""
    act = Activity.query.get_or_404(activity_id)
    participants = ActivityParticipant.query.filter_by(activity_id=act.id).all()
    field_logs = ActivityFieldLog.query.filter_by(activity_id=act.id).all()

    budget = act.budget_data
    gear = act.gear_data

    total_expense = (
        float(budget.get('expense_transport', 0) or 0) +
        float(budget.get('expense_permit', 0) or 0) +
        float(budget.get('expense_food', 0) or 0) +
        float(budget.get('expense_gear', 0) or 0) +
        float(budget.get('expense_med', 0) or 0) +
        float(budget.get('expense_emergency', 0) or 0)
    )
    total_income = (
        (float(budget.get('fee_per_person', 0) or 0) * act.total_confirmed) +
        float(budget.get('income_subsidy', 0) or 0) +
        float(budget.get('income_sponsor', 0) or 0)
    )

    org_address = SystemSetting.get('org_address', 'Jl. Raja Eyato No. 45, Kota Gorontalo')
    org_phone = SystemSetting.get('org_phone', '0811-430-1982')

    signers = resolve_rol_signers(act)

    # Dukungan override via query parameter
    leader_id = request.args.get('leader_id', type=int)
    kadiv_id = request.args.get('kadiv_id', type=int)
    ketum_id = request.args.get('ketum_id', type=int)

    if leader_id:
        u = db.session.get(User, leader_id)
        if u:
            signers['leader'] = u
    if kadiv_id:
        u = db.session.get(User, kadiv_id)
        if u:
            signers['kadiv'] = u
            if u.jabatan:
                signers['kadiv_title'] = u.jabatan
    if ketum_id:
        u = db.session.get(User, ketum_id)
        if u:
            signers['ketum'] = u
            if u.jabatan:
                signers['ketum_title'] = u.jabatan

    all_members = User.query.filter(User.status == 'active').order_by(User.name.asc()).all()

    months_id = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    now = datetime.now()
    today_date_fmt = f"{now.day} {months_id[now.month]} {now.year}"

    return render_template(
        'admin/print_rol.html',
        activity=act,
        participants=participants,
        field_logs=field_logs,
        budget=budget,
        gear=gear,
        total_expense=total_expense,
        total_income=total_income,
        org_address=org_address,
        org_phone=org_phone,
        current_year=now.strftime('%Y'),
        today_date_fmt=today_date_fmt,
        signers=signers,
        all_members=all_members
    )


# ========== BACKWARD COMPATIBILITY MODAL HANDLERS ===============================

@admin_bp.route('/admin/activity/create-modal')
@login_required
@admin_required
def admin_create_activity_modal():
    return render_template('components/modals.html', modal_type='create_activity')


@admin_bp.route('/admin/activity/create', methods=['POST'])
@login_required
@admin_required
def admin_create_activity():
    admin = get_current_user()
    title = request.form.get('title')
    location = request.form.get('location')
    activity_date = request.form.get('activity_date')
    difficulty = request.form.get('difficulty', 'Menengah')
    quota = int(request.form.get('quota', 20))
    description = request.form.get('description', '')

    image_file = request.files.get('image_file')
    image_url_input = request.form.get('image_url', '').strip()

    image_url = ''
    if image_file and image_file.filename:
        safe_name = f"act_{int(datetime.now().timestamp())}_{secure_filename(image_file.filename)}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'gallery', safe_name)
        image_file.save(save_path)
        image_url = f"/uploads/gallery/{safe_name}"
    elif image_url_input:
        image_url = image_url_input
    else:
        image_url = '/static/pics/cartoon/hero.jpg'

    new_act = Activity(
        title=title,
        location=location,
        activity_date=activity_date,
        difficulty=difficulty,
        quota=quota,
        description=description,
        image_url=image_url,
        is_open=True,
        phase='open'
    )
    db.session.add(new_act)
    db.session.commit()
    return admin_activities()


@admin_bp.route('/admin/activity/edit-modal/<int:activity_id>')
@login_required
@admin_required
def admin_edit_activity_modal(activity_id):
    act = Activity.query.get_or_404(activity_id)
    return render_template('components/modals.html', modal_type='edit_activity', activity=act)


@admin_bp.route('/admin/activity/edit/<int:activity_id>', methods=['POST'])
@login_required
@admin_required
def admin_edit_activity(activity_id):
    act = Activity.query.get_or_404(activity_id)
    act.title = request.form.get('title', act.title).strip()
    act.location = request.form.get('location', act.location).strip()
    act.activity_date = request.form.get('activity_date', act.activity_date).strip()
    act.difficulty = request.form.get('difficulty', act.difficulty)
    act.quota = int(request.form.get('quota', act.quota or 20))
    act.is_open = bool(request.form.get('is_open'))
    act.description = request.form.get('description', act.description).strip()

    image_file = request.files.get('image_file')
    image_url_input = request.form.get('image_url', '').strip()
    if image_file and image_file.filename:
        safe_name = f"act_{int(datetime.now().timestamp())}_{secure_filename(image_file.filename)}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'gallery', safe_name)
        image_file.save(save_path)
        act.image_url = f"/uploads/gallery/{safe_name}"
    elif image_url_input:
        act.image_url = image_url_input

    db.session.commit()
    return admin_activities()


@admin_bp.route('/admin/activity/toggle-status/<int:activity_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_activity_status(activity_id):
    act = Activity.query.get_or_404(activity_id)
    act.is_open = not act.is_open
    if act.is_open and act.phase == 'planning':
        act.phase = 'open'
    db.session.commit()
    return admin_activities()


@admin_bp.route('/admin/activity/delete/<int:activity_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_activity(activity_id):
    act = Activity.query.get_or_404(activity_id)
    ActivityParticipant.query.filter_by(activity_id=act.id).delete()
    ActivityFieldLog.query.filter_by(activity_id=act.id).delete()
    db.session.delete(act)
    db.session.commit()
    return admin_activities()


@admin_bp.route('/admin/activity/participants/<int:activity_id>')
@login_required
@admin_required
def admin_activity_participants(activity_id):
    act = Activity.query.get_or_404(activity_id)
    participants = ActivityParticipant.query.filter_by(activity_id=act.id).all()
    return render_template('components/modals.html', modal_type='activity_participants', activity=act, participants=participants)


@admin_bp.route('/admin/activity/participant-status/<int:part_id>', methods=['POST'])
@login_required
@admin_required
def admin_update_participant_status(part_id):
    part = ActivityParticipant.query.get_or_404(part_id)
    status = request.args.get('status', 'confirmed')
    part.status = status
    db.session.commit()

    act = Activity.query.get(part.activity_id)
    if request.args.get('from') == 'manage' or request.args.get('tab'):
        tab = request.args.get('tab', 'manifest')
        return admin_activity_manage(act.id, tab=tab)
    participants = ActivityParticipant.query.filter_by(activity_id=act.id).all()
    return render_template('components/modals.html', modal_type='activity_participants', activity=act, participants=participants)


# ========== GALLERY & SOCIAL PIN MANAGEMENT =====================================

@admin_bp.route('/admin/post/pin-to-gallery/<int:post_id>', methods=['POST'])
@login_required
@admin_required
def admin_pin_post_to_gallery(post_id):
    """Admin kurasi foto postingan anggota langsung dipin ke Galeri Landing Page Utama (Mendukung Multi-Foto)"""
    post = Post.query.get_or_404(post_id)
    media_list = []
    if post.media_items:
        media_list = list(post.media_items)
    elif post.image_url:
        class DummyMedia:
            media_url = post.image_url
            media_type = 'image'
            caption = None
        media_list = [DummyMedia()]

    if not media_list:
        return "<span class='text-[10px] text-rose-500 font-bold'>Postingan tidak memiliki foto/media</span>"

    total = len(media_list)
    pinned_count = 0
    item_category = 'Ekspedisi'
    if post.activity and hasattr(post.activity, 'category') and post.activity.category:
        item_category = post.activity.category

    for idx, m in enumerate(media_list):
        m_url = getattr(m, 'media_url', None) or post.image_url
        if not m_url:
            continue

        existing = GalleryItem.query.filter_by(image_url=m_url).first()
        if existing:
            existing.is_pinned = True
            existing.post_id = post.id
            if post.activity_id and not existing.activity_id:
                existing.activity_id = post.activity_id
            pinned_count += 1
            continue

        item_title = f"Dokumentasi {post.location or 'Ekspedisi'}"
        if total > 1:
            item_title = f"{item_title} ({idx + 1}/{total})"

        item = GalleryItem(
            title=item_title,
            caption=getattr(m, 'caption', None) or post.content[:180],
            image_url=m_url,
            location=post.location or 'Provinsi Gorontalo',
            category=item_category,
            activity_id=post.activity_id,
            post_id=post.id,
            is_pinned=True
        )
        db.session.add(item)
        pinned_count += 1

    db.session.commit()
    
    label = f"{pinned_count} Foto Terpin di Galeri Web" if pinned_count > 1 else "Terpin di Galeri Web"
    return f"""
    <span class="px-2.5 py-1 bg-emerald-100 text-emerald-800 text-[10px] font-bold rounded-full flex items-center gap-1 shadow-sm">
        <i class="fas fa-check-circle text-emerald-600"></i> {label}
    </span>
    """


@admin_bp.route('/admin/gallery')
@login_required
@admin_required
def admin_gallery():
    selected_pinned = request.args.get('pinned')
    selected_activity_id = request.args.get('activity_id', type=int)

    query = GalleryItem.query
    if selected_pinned == '1':
        query = query.filter_by(is_pinned=True)
    elif selected_pinned == '0':
        query = query.filter_by(is_pinned=False)

    if selected_activity_id:
        query = query.filter_by(activity_id=selected_activity_id)

    items = query.order_by(GalleryItem.id.desc()).all()
    activities = Activity.query.order_by(Activity.title.asc()).all()
    total_count = GalleryItem.query.count()
    pinned_count = GalleryItem.query.filter_by(is_pinned=True).count()

    data = {
        'gallery_items': items,
        'activities': activities,
        'total_count': total_count,
        'pinned_count': pinned_count,
        'selected_pinned': selected_pinned,
        'selected_activity_id': selected_activity_id
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_gallery', data, active_page='admin_gallery')


@admin_bp.route('/admin/gallery/create-modal')
@login_required
@admin_required
def admin_create_gallery_modal():
    activities = Activity.query.order_by(Activity.title.asc()).all()
    return render_template('components/modals.html', modal_type='create_gallery', activities=activities)


@admin_bp.route('/admin/gallery/create', methods=['POST'])
@login_required
@admin_required
def admin_create_gallery():
    title = request.form.get('title', '').strip()
    caption = request.form.get('caption', '').strip()
    category = request.form.get('category', 'Pendakian')
    location = request.form.get('location', '').strip()
    activity_id = request.form.get('activity_id', type=int)
    is_pinned = bool(request.form.get('is_pinned'))
    
    image_file = request.files.get('image_file')
    image_url_input = request.form.get('image_url', '').strip()
    
    image_url = ''
    if image_file and image_file.filename:
        safe_name = f"gal_{int(datetime.now().timestamp())}_{secure_filename(image_file.filename)}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'gallery', safe_name)
        image_file.save(save_path)
        image_url = f"/uploads/gallery/{safe_name}"
    elif image_url_input:
        image_url = image_url_input
    else:
        image_url = '/static/pics/cartoon/divisi_mountaineer.jpg'
        
    new_item = GalleryItem(
        title=title or 'Dokumentasi Ekspedisi',
        caption=caption,
        image_url=image_url,
        category=category,
        location=location,
        activity_id=activity_id if activity_id and activity_id > 0 else None,
        is_pinned=is_pinned
    )
    db.session.add(new_item)
    db.session.commit()
    return admin_gallery()


@admin_bp.route('/admin/gallery/toggle-pin/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_pin_gallery(item_id):
    item = GalleryItem.query.get_or_404(item_id)
    item.is_pinned = not item.is_pinned
    db.session.commit()
    return admin_gallery()


@admin_bp.route('/admin/gallery/edit-modal/<int:item_id>')
@login_required
@admin_required
def admin_edit_gallery_modal(item_id):
    item = GalleryItem.query.get_or_404(item_id)
    activities = Activity.query.order_by(Activity.title.asc()).all()
    return render_template('components/modals.html', modal_type='edit_gallery', item=item, activities=activities)


@admin_bp.route('/admin/gallery/edit/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def admin_edit_gallery(item_id):
    item = GalleryItem.query.get_or_404(item_id)
    title = request.form.get('title', '').strip()
    if title:
        item.title = title
    item.caption = request.form.get('caption', '').strip()
    category = request.form.get('category')
    if category:
        item.category = category
    item.location = request.form.get('location', '').strip()
    
    activity_id_val = request.form.get('activity_id')
    try:
        item.activity_id = int(activity_id_val) if activity_id_val and int(activity_id_val) > 0 else None
    except (ValueError, TypeError):
        item.activity_id = None
        
    item.is_pinned = bool(request.form.get('is_pinned'))
    
    image_file = request.files.get('image_file')
    image_url_input = request.form.get('image_url', '').strip()
    if image_file and image_file.filename:
        safe_name = f"gal_{int(datetime.now().timestamp())}_{secure_filename(image_file.filename)}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'gallery', safe_name)
        image_file.save(save_path)
        item.image_url = f"/uploads/gallery/{safe_name}"
    elif image_url_input:
        item.image_url = image_url_input
        
    db.session.commit()
    return admin_gallery()


@admin_bp.route('/admin/gallery/delete/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_gallery(item_id):
    item = GalleryItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return admin_gallery()


# ========== ADMIN REPO PETA (GEODATA INTERNAL GIMBAL) ==========================

@admin_bp.route('/admin/repo-maps')
@login_required
@admin_required
def admin_repo_maps(alert_msg=None):
    category = request.args.get('category')
    region = request.args.get('region')
    query = MapRepository.query
    if category:
        query = query.filter_by(category=category)
    if region:
        query = query.filter_by(region=region)
    maps = query.order_by(MapRepository.id.desc()).all()
    data = {
        'maps': maps,
        'total_count': MapRepository.query.count(),
        'selected_category': category,
        'selected_region': region
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_repo_maps', data, active_page='admin_repo_maps', alert_msg=alert_msg)


@admin_bp.route('/admin/repo-maps/create-modal')
@login_required
@admin_required
def admin_create_repo_map_modal():
    return render_template('components/modals.html', modal_type='create_repo_map')


@admin_bp.route('/admin/repo-maps/create', methods=['POST'])
@login_required
@admin_required
def admin_create_repo_map():
    admin = get_current_user()
    title = request.form.get('title', '').strip()
    region = request.form.get('region', 'Gorontalo').strip()
    cat_raw = request.form.get('category', 'jalur_pendakian').strip()
    cat_map = {
        'topo': 'topografi', 'topografi': 'topografi',
        'trail': 'jalur_pendakian', 'jalur_pendakian': 'jalur_pendakian',
        'geopdf': 'geopdf',
        'conservation': 'cagar_alam', 'cagar_alam': 'cagar_alam',
        'water_source': 'sumber_air', 'watershed': 'sumber_air', 'sumber_air': 'sumber_air',
        'other': 'other'
    }
    category = cat_map.get(cat_raw, cat_raw)
    description = request.form.get('description', '').strip()
    file_type = request.form.get('file_type', 'gpx').strip().lower()
    total_waypoints = int(request.form.get('total_waypoints', 0) or 0)
    total_distance_km = float(request.form.get('total_distance_km', 0.0) or 0.0)
    is_exclusive_member = bool(request.form.get('is_exclusive_member', True))

    map_file = request.files.get('map_file')
    if not map_file or not map_file.filename:
        return admin_repo_maps(alert_msg="Peringatan: Berkas peta belum dipilih.")

    maps_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'maps')
    os.makedirs(maps_dir, exist_ok=True)

    filename_raw = map_file.filename or 'peta_geodata.pdf'
    filename_clean = secure_filename(filename_raw)
    if not filename_clean or '.' not in filename_clean:
        ext = filename_raw.rsplit('.', 1)[-1].lower() if '.' in filename_raw else 'pdf'
        filename_clean = f"map_file_{int(datetime.now().timestamp())}.{ext}"

    safe_name = f"map_{int(datetime.now().timestamp())}_{filename_clean}"
    save_path = os.path.join(maps_dir, safe_name)
    map_file.save(save_path)

    file_size_bytes = os.path.getsize(save_path)
    if file_size_bytes > 1024 * 1024:
        file_size_fmt = f"{round(file_size_bytes / (1024 * 1024), 1)} MB"
    else:
        file_size_fmt = f"{round(file_size_bytes / 1024, 1)} KB"

    if '.' in filename_clean:
        file_type = filename_clean.rsplit('.', 1)[1].lower()

    if file_type == 'pdf' and category in ('other', 'topografi'):
        category = 'geopdf'

    preview_file = request.files.get('preview_file')
    preview_image = None
    if preview_file and preview_file.filename:
        preview_clean = secure_filename(preview_file.filename) or f"prev_{int(datetime.now().timestamp())}.jpg"
        safe_preview = f"prev_{int(datetime.now().timestamp())}_{preview_clean}"
        preview_path = os.path.join(maps_dir, safe_preview)
        preview_file.save(preview_path)
        preview_image = f"/uploads/maps/{safe_preview}"

    repo_item = MapRepository(
        title=title,
        region=region,
        category=category,
        file_type=file_type,
        file_path=f"/uploads/maps/{safe_name}",
        file_size_fmt=file_size_fmt,
        preview_image=preview_image,
        description=description,
        total_waypoints=total_waypoints,
        total_distance_km=total_distance_km,
        is_exclusive_member=is_exclusive_member,
        uploaded_by=admin.id
    )
    db.session.add(repo_item)

    log = AdminAuditLog(
        admin_id=admin.id,
        action='upload_map_repo',
        target_type='map_repository',
        target_id=str(title),
        details=f"Mengunggah peta ekspedisi '{title}' format {file_type.upper()} ({file_size_fmt})",
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    return admin_repo_maps(alert_msg=f"Peta '{title}' berhasil diunggah ke repositori geodata!")


@admin_bp.route('/admin/repo-maps/edit-modal/<int:map_id>')
@login_required
@admin_required
def admin_edit_repo_map_modal(map_id):
    map_item = MapRepository.query.get_or_404(map_id)
    return render_template('components/modals.html', modal_type='edit_repo_map', map_item=map_item)


@admin_bp.route('/admin/repo-maps/edit/<int:map_id>', methods=['POST'])
@login_required
@admin_required
def admin_edit_repo_map(map_id):
    admin = get_current_user()
    map_item = MapRepository.query.get_or_404(map_id)

    map_item.title = request.form.get('title', map_item.title).strip()
    map_item.region = request.form.get('region', map_item.region).strip()
    cat_raw = request.form.get('category', map_item.category).strip()
    cat_map = {
        'topo': 'topografi', 'topografi': 'topografi',
        'trail': 'jalur_pendakian', 'jalur_pendakian': 'jalur_pendakian',
        'geopdf': 'geopdf',
        'conservation': 'cagar_alam', 'cagar_alam': 'cagar_alam',
        'water_source': 'sumber_air', 'watershed': 'sumber_air', 'sumber_air': 'sumber_air',
        'other': 'other'
    }
    map_item.category = cat_map.get(cat_raw, cat_raw)
    map_item.description = request.form.get('description', map_item.description).strip()
    map_item.total_waypoints = int(request.form.get('total_waypoints', map_item.total_waypoints) or 0)
    map_item.total_distance_km = float(request.form.get('total_distance_km', map_item.total_distance_km) or 0.0)
    map_item.is_exclusive_member = bool(request.form.get('is_exclusive_member'))

    maps_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'maps')
    os.makedirs(maps_dir, exist_ok=True)

    # File Peta Pengganti (Opsional)
    map_file = request.files.get('map_file')
    if map_file and map_file.filename:
        filename_clean = secure_filename(map_file.filename)
        safe_name = f"map_{int(datetime.now().timestamp())}_{filename_clean}"
        save_path = os.path.join(maps_dir, safe_name)
        map_file.save(save_path)

        file_size_bytes = os.path.getsize(save_path)
        if file_size_bytes > 1024 * 1024:
            map_item.file_size_fmt = f"{round(file_size_bytes / (1024 * 1024), 1)} MB"
        else:
            map_item.file_size_fmt = f"{round(file_size_bytes / 1024, 1)} KB"

        map_item.file_path = f"/uploads/maps/{safe_name}"
        if '.' in filename_clean:
            map_item.file_type = filename_clean.rsplit('.', 1)[1].lower()

    # File Preview Pengganti (Opsional)
    preview_file = request.files.get('preview_file')
    if preview_file and preview_file.filename:
        preview_clean = secure_filename(preview_file.filename)
        safe_preview = f"prev_{int(datetime.now().timestamp())}_{preview_clean}"
        preview_path = os.path.join(maps_dir, safe_preview)
        preview_file.save(preview_path)
        map_item.preview_image = f"/uploads/maps/{safe_preview}"

    log = AdminAuditLog(
        admin_id=admin.id,
        action='edit_map_repo',
        target_type='map_repository',
        target_id=str(map_item.id),
        details=f"Memperbarui arsip peta ekspedisi '{map_item.title}' format {map_item.file_type.upper()}",
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    return admin_repo_maps()


@admin_bp.route('/admin/repo-maps/delete/<int:map_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_repo_map(map_id):
    admin = get_current_user()
    map_item = MapRepository.query.get_or_404(map_id)
    title = map_item.title
    Post.query.filter_by(map_repo_id=map_item.id).delete()
    db.session.delete(map_item)

    log = AdminAuditLog(
        admin_id=admin.id,
        action='delete_map_repo',
        target_type='map_repository',
        target_id=str(map_id),
        details=f"Menghapus arsip peta ekspedisi '{title}'",
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    return admin_repo_maps()


@admin_bp.route('/admin/repo-maps/toggle-share/<int:map_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_repo_map_share(map_id):
    """Toggle publikasi berkas peta di repo ke linimasa / feed anggota (ON/OFF)"""
    map_item = MapRepository.query.get_or_404(map_id)
    map_item.is_shared_to_timeline = not bool(map_item.is_shared_to_timeline)
    admin = get_current_user()

    if map_item.is_shared_to_timeline:
        existing_post = Post.query.filter_by(map_repo_id=map_item.id).first()
        if not existing_post:
            stats_str = ""
            if map_item.total_distance_km and map_item.total_distance_km > 0:
                stats_str += f" • Jarak: {map_item.total_distance_km} km"
            if map_item.total_waypoints and map_item.total_waypoints > 0:
                stats_str += f" • {map_item.total_waypoints} Waypoints"

            post = Post(
                user_id=admin.id,
                content=(
                    f"🗺️ REPO PETA & GEODATA TERBARU: {map_item.title}!\n\n"
                    f"Kawasan: {map_item.region} • Format: .{map_item.file_type.upper()}{stats_str}\n\n"
                    f"{map_item.description or 'Rute dan data lintasan navigasi telah ditambahkan ke Pustaka Peta KPAB GIMBAL. Dapat disinkronkan langsung ke aplikasi Gimbal Maps.'}"
                ),
                map_repo_id=map_item.id,
                image_url=map_item.preview_image,
                location=f"{map_item.title}, {map_item.region}",
                post_type='map'
            )
            db.session.add(post)
    else:
        Post.query.filter_by(map_repo_id=map_item.id).delete()

    db.session.commit()

    if map_item.is_shared_to_timeline:
        return f"""
        <button type="button"
                hx-post="/admin/repo-maps/toggle-share/{map_item.id}"
                hx-swap="outerHTML"
                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 hover:bg-emerald-200 transition shadow-xs cursor-pointer"
                title="Peta aktif di Linimasa Anggota (Klik untuk matikan)">
            <i class="fas fa-toggle-on text-emerald-600 text-xs"></i>
            <span>Linimasa: ON</span>
        </button>
        """
    else:
        return f"""
        <button type="button"
                hx-post="/admin/repo-maps/toggle-share/{map_item.id}"
                hx-swap="outerHTML"
                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200 transition cursor-pointer"
                title="Peta belum dibagikan ke Linimasa (Klik untuk bagikan)">
            <i class="fas fa-toggle-off text-slate-400 text-xs"></i>
            <span>Linimasa: OFF</span>
        </button>
        """


# ========== SPONSORSHIP & MERCHANT PARTNER ADMIN ROUTES ==========================

@admin_bp.route('/admin/settings/gemini-api', methods=['POST'])
@login_required
@admin_required
def admin_settings_gemini_api():
    """Pengaturan Kunci API Gemini untuk AI Moderasi Linimasa & Fitur AI Lainnya"""
    admin = get_current_user()
    api_key = request.form.get('gemini_api_key', '').strip()
    if api_key:
        SystemSetting.set('gemini_api_key', api_key, 'Gemini API Key untuk Moderasi AI')
        os.environ['GEMINI_API_KEY'] = api_key

    log = AdminAuditLog(
        admin_id=admin.id,
        action='update_gemini_api',
        target_type='SystemSetting',
        details=f"Memperbarui kunci Google Gemini API oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash("Kunci Google Gemini API berhasil diperbarui untuk moderasi linimasa cerdas.", "success")
    if request.headers.get('HX-Request'):
        return admin_settings(initial_tab='cloudflare')
    return redirect('/admin/settings?tab=cloudflare')


@admin_bp.route('/admin/sponsors/create-modal')
@login_required
@admin_required
def admin_create_sponsor_modal():
    """Modal Tambah Mitra Sponsor Resmi Baru"""
    return render_template('components/modals.html', modal_type='create_sponsor')


@admin_bp.route('/admin/sponsors/create', methods=['POST'])
@login_required
@admin_required
def admin_create_sponsor():
    """Simpan Mitra Sponsor Korporat Baru dari Pengurus Admin"""
    admin = get_current_user()
    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'gear').strip()
    tier = request.form.get('tier', 'official_partner').strip()
    description = request.form.get('description', '').strip()
    promo_badge = request.form.get('promo_badge', '').strip()
    member_benefit = request.form.get('member_benefit', '').strip()
    website_url = request.form.get('website_url', '').strip()
    instagram_url = request.form.get('instagram_url', '').strip()
    whatsapp_number = request.form.get('whatsapp_number', '').strip()
    address = request.form.get('address', '').strip()
    maps_url = request.form.get('maps_url', '').strip()
    order_index = int(request.form.get('order_index', 0) or 0)
    is_active = request.form.get('is_active', '1') in ['1', 'true', 'on', 'yes']

    if not name:
        flash("Gagal: Nama mitra sponsor tidak boleh kosong.", "error")
        return admin_settings(initial_tab='sponsors')

    # Unggah berkas logo / banner mitra
    logo_file = request.files.get('logo_file')
    logo_url = '/static/pics/sample_sponsor.png'
    if logo_file and logo_file.filename:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'sponsors')
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"sponsor_{int(datetime.now().timestamp())}_{secure_filename(logo_file.filename)}"
        logo_file.save(os.path.join(upload_dir, safe_name))
        logo_url = f"/uploads/sponsors/{safe_name}"

    sponsor = Sponsor(
        name=name,
        logo_url=logo_url,
        category=category,
        tier=tier,
        description=description,
        promo_badge=promo_badge,
        member_benefit=member_benefit,
        website_url=website_url,
        instagram_url=instagram_url,
        whatsapp_number=whatsapp_number,
        address=address,
        maps_url=maps_url,
        owner_user_id=None,
        is_member_business=False,
        status='active',
        order_index=order_index,
        is_active=is_active
    )
    db.session.add(sponsor)

    log = AdminAuditLog(
        admin_id=admin.id,
        action='create_sponsor',
        target_type='Sponsor',
        details=f"Menambahkan mitra sponsor resmi: '{name}' ({category}) oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Mitra sponsor '{name}' berhasil didaftarkan.", "success")
    if request.headers.get('HX-Request'):
        return admin_sponsors()
    return redirect('/admin/sponsors')


@admin_bp.route('/admin/sponsors/edit-modal/<int:sponsor_id>')
@login_required
@admin_required
def admin_edit_sponsor_modal(sponsor_id):
    """Modal Edit Informasi Sponsor"""
    sponsor = Sponsor.query.get_or_404(sponsor_id)
    return render_template('components/modals.html', modal_type='edit_sponsor', sponsor=sponsor)


@admin_bp.route('/admin/sponsors/edit/<int:sponsor_id>', methods=['POST'])
@login_required
@admin_required
def admin_edit_sponsor(sponsor_id):
    """Perbarui Informasi Sponsor / Merchant"""
    admin = get_current_user()
    sponsor = Sponsor.query.get_or_404(sponsor_id)

    sponsor.name = request.form.get('name', sponsor.name).strip()
    sponsor.category = request.form.get('category', sponsor.category).strip()
    sponsor.tier = request.form.get('tier', sponsor.tier).strip()
    sponsor.description = request.form.get('description', '').strip()
    sponsor.promo_badge = request.form.get('promo_badge', '').strip()
    sponsor.member_benefit = request.form.get('member_benefit', '').strip()
    sponsor.website_url = request.form.get('website_url', '').strip()
    sponsor.instagram_url = request.form.get('instagram_url', '').strip()
    sponsor.whatsapp_number = request.form.get('whatsapp_number', '').strip()
    sponsor.address = request.form.get('address', '').strip()
    sponsor.maps_url = request.form.get('maps_url', '').strip()
    sponsor.order_index = int(request.form.get('order_index', sponsor.order_index) or 0)
    sponsor.is_active = request.form.get('is_active', '1') in ['1', 'true', 'on', 'yes']

    logo_file = request.files.get('logo_file')
    if logo_file and logo_file.filename:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'sponsors')
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"sponsor_{sponsor.id}_{int(datetime.now().timestamp())}_{secure_filename(logo_file.filename)}"
        logo_file.save(os.path.join(upload_dir, safe_name))
        sponsor.logo_url = f"/uploads/sponsors/{safe_name}"

    log = AdminAuditLog(
        admin_id=admin.id,
        action='update_sponsor',
        target_type='Sponsor',
        target_id=sponsor.id,
        details=f"Memperbarui data mitra sponsor: '{sponsor.name}'"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Data mitra sponsor '{sponsor.name}' berhasil diperbarui.", "success")
    if request.headers.get('HX-Request'):
        return admin_sponsors()
    return redirect('/admin/sponsors')


@admin_bp.route('/admin/sponsors/toggle-active/<int:sponsor_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_sponsor_active(sponsor_id):
    """Toggle On/Off Status Aktif Sponsor"""
    sponsor = Sponsor.query.get_or_404(sponsor_id)
    sponsor.is_active = not sponsor.is_active
    db.session.commit()
    status_str = "diaktifkan" if sponsor.is_active else "dinonaktifkan"
    flash(f"Mitra '{sponsor.name}' berhasil {status_str}.", "success")
    if request.headers.get('HX-Request'):
        return admin_sponsors()
    return redirect('/admin/sponsors')


@admin_bp.route('/admin/sponsors/verify/<int:sponsor_id>', methods=['POST'])
@login_required
@admin_required
def admin_verify_member_sponsor(sponsor_id):
    """Verifikasi pendaftaran usaha anggota (Setuju / Tolak)"""
    admin = get_current_user()
    sponsor = Sponsor.query.get_or_404(sponsor_id)
    action = request.form.get('action', 'active').strip()

    if action == 'active':
        sponsor.status = 'active'
        sponsor.is_active = True
        flash(f"Usaha anggota '{sponsor.name}' berhasil disetujui dan terverifikasi!", "success")
    else:
        sponsor.status = 'rejected'
        sponsor.rejection_reason = request.form.get('rejection_reason', 'Belum memenuhi kriteria kemitraan.').strip()
        flash(f"Pendaftaran usaha anggota '{sponsor.name}' ditolak.", "warning")

    log = AdminAuditLog(
        admin_id=admin.id,
        action='verify_member_sponsor',
        target_type='Sponsor',
        target_id=sponsor.id,
        details=f"Verifikasi usaha anggota '{sponsor.name}': status={sponsor.status}"
    )
    db.session.add(log)
    db.session.commit()
    if request.headers.get('HX-Request'):
        return admin_sponsors()
    return redirect('/admin/sponsors')


@admin_bp.route('/admin/sponsors/delete/<int:sponsor_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_sponsor(sponsor_id):
    """Hapus Mitra Sponsor / Usaha Anggota beserta seluruh produknya"""
    admin = get_current_user()
    sponsor = Sponsor.query.get_or_404(sponsor_id)
    name = sponsor.name

    # Lepas relasi postingan sponsor
    Post.query.filter_by(sponsor_id=sponsor.id).update({'sponsor_id': None})
    db.session.delete(sponsor)

    log = AdminAuditLog(
        admin_id=admin.id,
        action='delete_sponsor',
        target_type='Sponsor',
        details=f"Menghapus data mitra sponsor: '{name}' oleh {admin.name}"
    )
    db.session.add(log)
    db.session.commit()
    flash(f"Mitra sponsor '{name}' berhasil dihapus secara permanen.", "success")
    if request.headers.get('HX-Request'):
        return admin_sponsors()
    return redirect('/admin/sponsors')


@admin_bp.route('/admin/sponsors/products/<int:sponsor_id>')
@login_required
@admin_required
def admin_sponsor_products_modal(sponsor_id):
    """Modal Pengaturan Katalog Produk Sponsor / Usaha"""
    sponsor = Sponsor.query.get_or_404(sponsor_id)
    return render_template('components/modals.html', modal_type='sponsor_products', sponsor=sponsor)


@admin_bp.route('/admin/sponsors/products/create/<int:sponsor_id>', methods=['POST'])
@login_required
@admin_required
def admin_sponsor_product_create(sponsor_id):
    """Tambah Produk Baru ke Sponsor"""
    sponsor = Sponsor.query.get_or_404(sponsor_id)
    name = request.form.get('name', '').strip()
    price = float(request.form.get('price', 0) or 0)
    raw_discount = request.form.get('discount_price', '').strip()
    discount_price = float(raw_discount) if raw_discount else None
    description = request.form.get('description', '').strip()
    badge = request.form.get('badge', '').strip()

    image_file = request.files.get('image_file')
    image_url = None
    if image_file and image_file.filename:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products')
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"prod_{sponsor.id}_{int(datetime.now().timestamp())}_{secure_filename(image_file.filename)}"
        image_file.save(os.path.join(upload_dir, safe_name))
        image_url = f"/uploads/products/{safe_name}"

    prod = SponsorProduct(
        sponsor_id=sponsor.id,
        name=name,
        price=price,
        discount_price=discount_price,
        description=description,
        badge=badge,
        image_url=image_url,
        is_available=True
    )
    db.session.add(prod)
    db.session.commit()
    flash(f"Produk '{name}' berhasil ditambahkan ke katalog mitra '{sponsor.name}'.", "success")
    return render_template('components/modals.html', modal_type='sponsor_products', sponsor=sponsor)


@admin_bp.route('/admin/sponsors/products/delete/<int:prod_id>', methods=['POST'])
@login_required
@admin_required
def admin_sponsor_product_delete(prod_id):
    """Hapus Produk dari Sponsor"""
    prod = SponsorProduct.query.get_or_404(prod_id)
    sponsor = prod.sponsor
    prod_name = prod.name
    db.session.delete(prod)
    db.session.commit()
    flash(f"Produk '{prod_name}' berhasil dihapus dari katalog.", "success")
    return render_template('components/modals.html', modal_type='sponsor_products', sponsor=sponsor)


@admin_bp.route('/admin/sponsors/toggle-share/<int:sponsor_id>', methods=['POST'])
@login_required
@admin_required
def admin_sponsor_toggle_share(sponsor_id):
    """Toggle publikasi sorotan sponsor/mitra atau lapak anggota ke Linimasa (ON/OFF)"""
    admin = get_current_user()
    sponsor = Sponsor.query.get_or_404(sponsor_id)
    sponsor.is_shared_to_timeline = not bool(sponsor.is_shared_to_timeline)

    if sponsor.is_shared_to_timeline:
        benefit_str = f"\n\n🎁 Benefit Anggota GIMBAL: {sponsor.member_benefit}" if sponsor.member_benefit else ""
        promo_badge_str = f" [{sponsor.promo_badge}]" if sponsor.promo_badge else ""
        
        prod_highlights = []
        for p in sponsor.products[:3]:
            price_info = f"Rp {p.price:,.0f}"
            if p.discount_price:
                price_info += f" (Khusus KTA: Rp {p.discount_price:,.0f})"
            prod_highlights.append(f"• {p.name}: {price_info}")
        
        prod_str = "\n\nKatalog Pilihan:\n" + "\n".join(prod_highlights) if prod_highlights else ""

        title_prefix = "🏪 USAHA ANGGOTA" if sponsor.is_member_business else "🤝 SOROTAN MITRA RESMI"
        post_content = (
            f"{title_prefix}: {sponsor.name}{promo_badge_str}\n\n"
            f"{sponsor.description or 'Mendukung penjelajahan alam bebas dan kegiatan konservasi KPAB GIMBAL.'}"
            f"{benefit_str}"
            f"{prod_str}\n\n"
            f"Kunjungi gerai resmi atau hubungi untuk informasi lebih lanjut."
        )

        existing = Post.query.filter_by(sponsor_id=sponsor.id).first()
        if existing:
            existing.content = post_content
            existing.image_url = None
            existing.location = sponsor.address or f"{sponsor.name} Official"
            existing.post_type = 'sponsor'
            existing.created_at = datetime.utcnow()
        else:
            post = Post(
                user_id=admin.id,
                content=post_content,
                sponsor_id=sponsor.id,
                image_url=None,
                location=sponsor.address or f"{sponsor.name} Official",
                post_type='sponsor',
                created_at=datetime.utcnow()
            )
            db.session.add(post)
    else:
        Post.query.filter_by(sponsor_id=sponsor.id).delete()

    db.session.commit()

    if request.headers.get('HX-Request'):
        if sponsor.is_shared_to_timeline:
            return f"""
            <button type="button"
                    hx-post="/admin/sponsors/toggle-share/{sponsor.id}"
                    hx-swap="outerHTML"
                    class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 hover:bg-emerald-200 transition shadow-xs cursor-pointer"
                    title="Aktif di Linimasa (Klik untuk matikan)">
                <i class="fas fa-toggle-on text-emerald-600 text-xs"></i>
                <span>Linimasa: ON</span>
            </button>
            """
        else:
            return f"""
            <button type="button"
                    hx-post="/admin/sponsors/toggle-share/{sponsor.id}"
                    hx-swap="outerHTML"
                    class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200 transition cursor-pointer"
                    title="Belum di Linimasa (Klik untuk aktifkan & terbitkan di puncak linimasa)">
                <i class="fas fa-toggle-off text-slate-400 text-xs"></i>
                <span>Linimasa: OFF</span>
            </button>
            """

    flash(f"Status publikasi linimasa untuk '{sponsor.name}' berhasil diperbarui.", "success")
    return redirect('/admin/sponsors')


@admin_bp.route('/admin/sponsors/share-timeline/<int:sponsor_id>', methods=['POST'])
@login_required
@admin_required
def admin_sponsor_share_timeline(sponsor_id):
    """Kompatibilitas alias untuk toggle publikasi sponsor"""
    return admin_sponsor_toggle_share(sponsor_id)


# ==============================================================================
# ADMIN ACADEMY, SOP & MEMBER CERTIFICATION COMPLIANCE
# ==============================================================================

@admin_bp.route('/admin/academy')
@login_required
@admin_required
def admin_academy():
    """Pusat Kendali Admin Akademi, Kurikulum SOP & Kepatuhan Sertifikasi Anggota"""
    user = get_current_user()
    active_tab = request.args.get('tab', 'kurikulum')
    
    tiers = AcademyTier.query.order_by(AcademyTier.order_index.asc()).all()
    all_courses = AcademyCourse.query.order_by(AcademyCourse.order_index.asc()).all()
    all_docs = Document.query.order_by(Document.title.asc()).all()
    all_maps = MapRepository.query.order_by(MapRepository.title.asc()).all()
    
    # Data Anggota & Kepatuhan Sertifikasi
    members = User.query.order_by(User.status.desc(), User.name.asc()).all()
    
    # Statistik Kepatuhan Level 1
    total_members = len(members)
    level1_tier = AcademyTier.query.filter_by(order_index=1).first()
    level1_id = level1_tier.id if level1_tier else 1
    
    certified_level1_count = UserCertification.query.filter_by(tier_id=level1_id, status='active').count()
    mandatory_active_count = User.query.filter_by(is_mandatory_certified=True).count()
    
    # Hitung yang masih pending kewajiban
    pending_mandatory_count = sum(1 for m in members if m.is_mandatory_certification_pending)
    
    # Riwayat Sertifikasi & Ujian
    certifications = UserCertification.query.order_by(UserCertification.id.desc()).limit(100).all()
    recent_attempts = UserQuizAttempt.query.order_by(UserQuizAttempt.id.desc()).limit(50).all()

    data = {
        'user': user,
        'active_tab': active_tab,
        'tiers': tiers,
        'all_courses': all_courses,
        'all_docs': all_docs,
        'all_maps': all_maps,
        'members': members,
        'total_members': total_members,
        'certified_level1_count': certified_level1_count,
        'mandatory_active_count': mandatory_active_count,
        'pending_mandatory_count': pending_mandatory_count,
        'certifications': certifications,
        'recent_attempts': recent_attempts,
        'level1_tier': level1_tier
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_academy', data, active_page='admin_academy')


@admin_bp.route('/admin/academy/tier/create', methods=['POST'])
@login_required
@admin_required
def admin_academy_tier_create():
    """Tambah Tingkatan / Jenjang Baru Akademi"""
    name = request.form.get('name', '').strip()
    slug = request.form.get('slug', '').strip() or name.lower().replace(' ', '-')
    badge_name = request.form.get('badge_name', '').strip()
    badge_icon = request.form.get('badge_icon', 'fa-compass').strip()
    badge_color = request.form.get('badge_color', '#10b981').strip()
    description = request.form.get('description', '').strip()
    order_index = int(request.form.get('order_index', 1))
    passing_grade = int(request.form.get('passing_grade', 75))

    tier = AcademyTier(
        name=name,
        slug=slug,
        badge_name=badge_name,
        badge_icon=badge_icon,
        badge_color=badge_color,
        description=description,
        order_index=order_index,
        passing_grade=passing_grade,
        is_active=True
    )
    db.session.add(tier)
    db.session.commit()
    flash(f"Jenjang '{name}' berhasil ditambahkan ke kurikulum.", "success")
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/tier/edit/<int:tier_id>', methods=['POST'])
@login_required
@admin_required
def admin_academy_tier_edit(tier_id):
    """Ubah Data Tingkatan Akademi"""
    tier = db.session.get(AcademyTier, tier_id)
    if not tier:
        flash("Jenjang tidak ditemukan.", "error")
        return redirect('/admin/academy?tab=kurikulum')

    tier.name = request.form.get('name', tier.name).strip()
    tier.badge_name = request.form.get('badge_name', tier.badge_name).strip()
    tier.badge_icon = request.form.get('badge_icon', tier.badge_icon).strip()
    tier.badge_color = request.form.get('badge_color', tier.badge_color).strip()
    tier.description = request.form.get('description', tier.description).strip()
    tier.order_index = int(request.form.get('order_index', tier.order_index))
    tier.passing_grade = int(request.form.get('passing_grade', tier.passing_grade))

    db.session.commit()
    flash(f"Jenjang '{tier.name}' berhasil diperbarui.", "success")
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/tier/delete/<int:tier_id>', methods=['POST'])
@login_required
@admin_required
def admin_academy_tier_delete(tier_id):
    """Hapus Jenjang Tingkat Beserta Kursus & Kuis di Dalamnya"""
    tier = db.session.get(AcademyTier, tier_id)
    if tier:
        name = tier.name
        db.session.delete(tier)
        db.session.commit()
        flash(f"Jenjang '{name}' berhasil dihapus.", "success")
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/course/create', methods=['POST'])
@login_required
@admin_required
def admin_academy_course_create():
    """Tambah Mata Kursus / Pelatihan Baru"""
    tier_id = int(request.form.get('tier_id'))
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'diksar').strip()
    description = request.form.get('description', '').strip()
    target_duration_mins = int(request.form.get('target_duration_mins', 30))
    order_index = int(request.form.get('order_index', 1))

    course = AcademyCourse(
        tier_id=tier_id,
        title=title,
        category=category,
        description=description,
        target_duration_mins=target_duration_mins,
        order_index=order_index,
        is_published=True
    )
    db.session.add(course)
    db.session.commit()
    flash(f"Kursus '{title}' berhasil ditambahkan.", "success")
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/course/edit/<int:course_id>', methods=['POST'])
@login_required
@admin_required
def admin_academy_course_edit(course_id):
    """Edit Mata Kursus"""
    course = db.session.get(AcademyCourse, course_id)
    if not course:
        flash("Kursus tidak ditemukan.", "error")
        return redirect('/admin/academy?tab=kurikulum')

    course.title = request.form.get('title', course.title).strip()
    course.category = request.form.get('category', course.category).strip()
    course.description = request.form.get('description', course.description).strip()
    course.target_duration_mins = int(request.form.get('target_duration_mins', course.target_duration_mins))
    course.order_index = int(request.form.get('order_index', course.order_index))
    if 'tier_id' in request.form and request.form.get('tier_id').isdigit():
        course.tier_id = int(request.form.get('tier_id'))

    db.session.commit()
    flash(f"Kursus '{course.title}' berhasil diperbarui.", "success")
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/course/delete/<int:course_id>', methods=['POST'])
@login_required
@admin_required
def admin_academy_course_delete(course_id):
    """Hapus Mata Kursus"""
    course = db.session.get(AcademyCourse, course_id)
    if course:
        name = course.title
        db.session.delete(course)
        db.session.commit()
        flash(f"Kursus '{name}' berhasil dihapus.", "success")
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/lesson/create', methods=['POST'])
@login_required
@admin_required
def admin_academy_lesson_create():
    """Tambah Bab Materi / Dokumen SOP ke Kursus"""
    course_id = int(request.form.get('course_id'))
    title = request.form.get('title', '').strip()
    content_type = request.form.get('content_type', 'article')
    content_body = request.form.get('content_body', '').strip()
    media_url = request.form.get('media_url', '').strip() or None
    
    raw_doc_id = request.form.get('doc_id', '').strip()
    doc_id = int(raw_doc_id) if raw_doc_id and raw_doc_id.isdigit() and int(raw_doc_id) > 0 else None
    
    raw_map_id = request.form.get('map_repo_id', '').strip()
    map_repo_id = int(raw_map_id) if raw_map_id and raw_map_id.isdigit() and int(raw_map_id) > 0 else None
    
    order_index = int(request.form.get('order_index', 1))

    lesson = AcademyLesson(
        course_id=course_id,
        title=title,
        content_type=content_type,
        content_body=content_body,
        media_url=media_url,
        doc_id=doc_id,
        map_repo_id=map_repo_id,
        order_index=order_index
    )
    db.session.add(lesson)
    db.session.commit()
    flash(f"Materi '{title}' berhasil ditambahkan ke kursus.", "success")
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/lesson/edit-modal/<int:lesson_id>')
@login_required
@admin_required
def admin_academy_lesson_edit_modal(lesson_id):
    """Buka modal edit bab materi kurikulum pembelajaran"""
    lesson = db.session.get(AcademyLesson, lesson_id)
    if not lesson:
        return "<div class='p-4 text-rose-500 font-bold'>Materi tidak ditemukan.</div>", 404
    docs = Document.query.order_by(Document.title.asc()).all()
    maps = MapRepository.query.order_by(MapRepository.title.asc()).all()
    return render_template(
        'components/modals.html',
        modal_type='edit_academy_lesson',
        lesson=lesson,
        documents=docs,
        maps=maps
    )


@admin_bp.route('/admin/academy/lesson/edit/<int:lesson_id>', methods=['POST'])
@login_required
@admin_required
def admin_academy_lesson_edit(lesson_id):
    """Ubah Bab Materi / SOP"""
    lesson = db.session.get(AcademyLesson, lesson_id)
    if not lesson:
        flash("Materi tidak ditemukan.", "error")
        if request.headers.get('HX-Request'):
            return admin_academy()
        return redirect('/admin/academy?tab=kurikulum')

    lesson.title = request.form.get('title', lesson.title).strip()
    lesson.content_type = request.form.get('content_type', lesson.content_type)
    new_content = request.form.get('content_body') or request.form.get('content')
    if new_content is not None:
        lesson.content_body = new_content
    new_video = request.form.get('media_url') or request.form.get('video_url')
    lesson.media_url = new_video.strip() if new_video else None

    raw_doc_id = request.form.get('doc_id', '').strip()
    lesson.doc_id = int(raw_doc_id) if raw_doc_id and raw_doc_id.isdigit() and int(raw_doc_id) > 0 else None

    raw_map_id = request.form.get('map_repo_id', '').strip()
    lesson.map_repo_id = int(raw_map_id) if raw_map_id and raw_map_id.isdigit() and int(raw_map_id) > 0 else None

    lesson.order_index = int(request.form.get('order_index', lesson.order_index))

    db.session.commit()
    flash(f"Materi '{lesson.title}' berhasil diperbarui.", "success")
    if request.headers.get('HX-Request'):
        return admin_academy()
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/lesson/delete/<int:lesson_id>', methods=['POST'])
@login_required
@admin_required
def admin_academy_lesson_delete(lesson_id):
    """Hapus Bab Materi"""
    lesson = db.session.get(AcademyLesson, lesson_id)
    if lesson:
        title = lesson.title
        db.session.delete(lesson)
        db.session.commit()
        flash(f"Materi '{title}' berhasil dihapus.", "success")
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/quiz/create', methods=['POST'])
@login_required
@admin_required
def admin_academy_quiz_create():
    """Tambah Ujian / Kuis Sertifikasi Baru"""
    raw_tier_id = request.form.get('tier_id', '').strip()
    tier_id = int(raw_tier_id) if raw_tier_id and raw_tier_id.isdigit() else None
    
    raw_course_id = request.form.get('course_id', '').strip()
    course_id = int(raw_course_id) if raw_course_id and raw_course_id.isdigit() else None

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    passing_score = int(request.form.get('passing_score', 75))
    time_limit_mins = int(request.form.get('time_limit_mins', 20))

    quiz = AcademyQuiz(
        tier_id=tier_id,
        course_id=course_id,
        title=title,
        description=description,
        passing_score=passing_score,
        time_limit_mins=time_limit_mins,
        is_active=True
    )
    db.session.add(quiz)
    db.session.commit()
    flash(f"Ujian '{title}' berhasil dibuat.", "success")
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/quiz/edit/<int:quiz_id>', methods=['POST'])
@login_required
@admin_required
def admin_academy_quiz_edit(quiz_id):
    """Ubah Pengaturan Kuis"""
    quiz = db.session.get(AcademyQuiz, quiz_id)
    if not quiz:
        flash("Kuis tidak ditemukan.", "error")
        return redirect('/admin/academy?tab=kurikulum')

    quiz.title = request.form.get('title', quiz.title).strip()
    quiz.description = request.form.get('description', quiz.description).strip()
    quiz.passing_score = int(request.form.get('passing_score', quiz.passing_score))
    quiz.time_limit_mins = int(request.form.get('time_limit_mins', quiz.time_limit_mins))

    db.session.commit()
    flash(f"Ujian '{quiz.title}' berhasil diperbarui.", "success")
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/quiz/delete/<int:quiz_id>', methods=['POST'])
@login_required
@admin_required
def admin_academy_quiz_delete(quiz_id):
    """Hapus Kuis Beserta Butir Soal"""
    quiz = db.session.get(AcademyQuiz, quiz_id)
    if quiz:
        title = quiz.title
        db.session.delete(quiz)
        db.session.commit()
        flash(f"Ujian '{title}' berhasil dihapus.", "success")
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/question/create/<int:quiz_id>', methods=['POST'])
@login_required
@admin_required
def admin_academy_question_create(quiz_id):
    """Tambah Butir Soal & Pilihan Jawaban ke Ujian"""
    quiz = db.session.get(AcademyQuiz, quiz_id)
    if not quiz:
        flash("Ujian tidak ditemukan.", "error")
        return redirect('/admin/academy?tab=kurikulum')

    question_text = request.form.get('question_text', '').strip()
    explanation = request.form.get('explanation', '').strip()
    points = int(request.form.get('points', 20))
    correct_opt_idx = int(request.form.get('correct_option', 1))

    q = QuizQuestion(
        quiz_id=quiz.id,
        question_text=question_text,
        explanation=explanation,
        points=points,
        order_index=len(quiz.questions) + 1
    )
    db.session.add(q)
    db.session.flush()

    # Opsi A, B, C, D
    for i in range(1, 5):
        opt_text = request.form.get(f'option_{i}', '').strip()
        if opt_text:
            opt = QuizOption(
                question_id=q.id,
                option_text=opt_text,
                is_correct=(i == correct_opt_idx),
                order_index=i
            )
            db.session.add(opt)

    db.session.commit()
    flash("Soal baru berhasil ditambahkan ke ujian.", "success")
    return redirect('/admin/academy?tab=kurikulum')


@admin_bp.route('/admin/academy/question/delete/<int:question_id>', methods=['POST'])
@login_required
@admin_required
def admin_academy_question_delete(question_id):
    """Hapus Butir Soal"""
    q = db.session.get(QuizQuestion, question_id)
    if q:
        db.session.delete(q)
        db.session.commit()
        flash("Butir soal berhasil dihapus.", "success")
    return redirect('/admin/academy?tab=kurikulum')


# --- FITUR KEPATUHAN & PENUGASAN WAJIB SERTIFIKASI (MANDATORY ENFORCEMENT) ---

@admin_bp.route('/admin/academy/mandate/toggle/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_academy_mandate_toggle(user_id):
    """1-Click Toggle: Wajibkan / Bebaskan Anggota Tertentu untuk Sertifikasi"""
    target_user = db.session.get(User, user_id)
    if not target_user:
        return jsonify({'error': 'Anggota tidak ditemukan'}), 404

    target_user.is_mandatory_certified = not target_user.is_mandatory_certified
    if target_user.is_mandatory_certified:
        tier_choice = request.form.get('tier_id')
        target_user.mandatory_tier_id = int(tier_choice) if tier_choice and tier_choice.isdigit() else 1
    else:
        target_user.mandatory_tier_id = None

    db.session.commit()

    if request.headers.get('HX-Request'):
        # Kembalikan tombol HTMX baru
        status_text = "WAJIB" if target_user.is_mandatory_certified else "BEBAS"
        btn_class = "bg-rose-600 text-white hover:bg-rose-700" if target_user.is_mandatory_certified else "bg-slate-100 text-slate-700 hover:bg-slate-200"
        return f"""
        <button type="button"
                hx-post="/admin/academy/mandate/toggle/{target_user.id}"
                hx-swap="outerHTML"
                class="px-2.5 py-1 rounded-md text-[10px] font-bold transition flex items-center gap-1.5 shadow-2xs {btn_class}"
                title="Klik untuk mengubah status kewajiban sertifikasi">
            <i class="fas {'fa-exclamation-circle text-amber-300' if target_user.is_mandatory_certified else 'fa-shield-halved text-slate-400'}"></i>
            <span>{status_text}</span>
        </button>
        """

    flash(f"Status kewajiban sertifikasi untuk {target_user.name} berhasil diperbarui.", "success")
    return redirect('/admin/academy?tab=kepatuhan')


@admin_bp.route('/admin/academy/mandate/all-candidates', methods=['POST'])
@login_required
@admin_required
def admin_academy_mandate_all_candidates():
    """1-Click Instan: Memaksakan SELURUH Calon Anggota & Anggota Baru Wajib Lulus Level 1"""
    level1_tier = AcademyTier.query.filter_by(order_index=1).first()
    target_tier_id = level1_tier.id if level1_tier else 1

    # Anggota dengan status 'pending' atau yang belum memiliki sertifikat Level 1
    candidates = User.query.filter(User.role != 'superadmin').all()
    count_updated = 0

    for u in candidates:
        # Cek apakah sudah punya cert level 1
        has_l1 = UserCertification.query.filter_by(user_id=u.id, tier_id=target_tier_id, status='active').first()
        if not has_l1:
            u.is_mandatory_certified = True
            u.mandatory_tier_id = target_tier_id
            count_updated += 1

    db.session.commit()
    flash(f"Sukses! {count_updated} calon anggota / anggota aktif telah diwajibkan menyelesaikan Sertifikasi Level 1.", "success")
    return redirect('/admin/academy?tab=kepatuhan')


@admin_bp.route('/admin/academy/mandate/clear-all', methods=['POST'])
@login_required
@admin_required
def admin_academy_mandate_clear_all():
    """1-Click: Bebaskan Seluruh Anggota dari Kewajiban Sertifikasi Paksa"""
    User.query.update({User.is_mandatory_certified: False, User.mandatory_tier_id: None})
    db.session.commit()
    flash("Seluruh anggota telah dibebaskan dari kewajiban sertifikasi paksa.", "info")
    return redirect('/admin/academy?tab=kepatuhan')


@admin_bp.route('/admin/academy/cert/revoke/<int:cert_id>', methods=['POST'])
@login_required
@admin_required
def admin_academy_cert_revoke(cert_id):
    """Mencabut Sertifikat / Brevet Anggota Jika Terjadi Pelanggaran Kode Etik"""
    cert = db.session.get(UserCertification, cert_id)
    if cert:
        cert.status = 'revoked'
        db.session.commit()
        flash(f"Sertifikat '{cert.certificate_no}' atas nama {cert.user.name} berhasil dicabut.", "warning")
    return redirect('/admin/academy?tab=riwayat')


# ========== ADMIN INQUIRIES & PERMINTAAN PENGAWALAN ==============================

@admin_bp.route('/admin/inquiries')
@login_required
@admin_required
def admin_inquiries(alert_msg=None):
    category = request.args.get('category')
    status = request.args.get('status')
    query = Inquiry.query
    if category:
        query = query.filter_by(category=category)
    if status:
        query = query.filter_by(status=status)
    inquiries = query.order_by(Inquiry.id.desc()).all()
    guides = User.query.filter_by(status='active').order_by(User.name.asc()).all()
    data = {
        'inquiries': inquiries,
        'guides': guides,
        'selected_category': category,
        'selected_status': status,
        'total_count': Inquiry.query.count(),
        'pending_count': Inquiry.query.filter_by(status='pending').count(),
        'guiding_count': Inquiry.query.filter_by(category='guiding').count(),
        'sponsor_count': Inquiry.query.filter_by(category='sponsorship').count()
    }
    return render_gimbal_page('admin/admin_pages.html', 'admin_inquiries', data, active_page='admin_inquiries', alert_msg=alert_msg)


@admin_bp.route('/admin/inquiries/update-status/<int:inquiry_id>', methods=['POST'])
@login_required
@admin_required
def admin_inquiry_update_status(inquiry_id):
    inquiry = db.session.get(Inquiry, inquiry_id)
    if not inquiry:
        return admin_inquiries(alert_msg="Permintaan tidak ditemukan.")
    
    status = request.form.get('status', inquiry.status).strip()
    notes = request.form.get('admin_notes', inquiry.admin_notes or '').strip()
    guide_id_raw = request.form.get('assigned_guide_id')
    if guide_id_raw and guide_id_raw.isdigit():
        inquiry.assigned_guide_id = int(guide_id_raw)
    elif guide_id_raw == '':
        inquiry.assigned_guide_id = None
        
    inquiry.status = status
    inquiry.admin_notes = notes
    db.session.commit()
    return admin_inquiries(alert_msg=f"Status permohonan #{inquiry.id} dari '{inquiry.name}' berhasil diperbarui ({status.upper()}).")


@admin_bp.route('/admin/inquiries/delete/<int:inquiry_id>', methods=['POST'])
@login_required
@admin_required
def admin_inquiry_delete(inquiry_id):
    inquiry = db.session.get(Inquiry, inquiry_id)
    if inquiry:
        db.session.delete(inquiry)
        db.session.commit()
        return admin_inquiries(alert_msg=f"Pesan/permohonan #{inquiry_id} berhasil dihapus.")
    return admin_inquiries()




