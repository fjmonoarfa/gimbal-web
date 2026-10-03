import os
import io
import json
import base64
import qrcode
from datetime import datetime, timedelta
from flask import Blueprint, request, redirect, render_template, render_template_string, make_response, current_app, jsonify, flash
from werkzeug.utils import secure_filename
from models import (
    db, User, Dues, DuesPayment, Document, Activity,
    ActivityParticipant, GalleryItem, Post, PostComment,
    PostLike, ChatMessage, SystemSetting, MapRepository, PostMedia,
    Sponsor, SponsorProduct,
    AcademyTier, AcademyCourse, AcademyLesson, AcademyQuiz, QuizQuestion, QuizOption,
    UserLessonProgress, UserQuizAttempt, UserCertification
)
from helpers import get_current_user, login_required, check_member_access, render_gimbal_page, render_gimbal_modal

members_bp = Blueprint('members_page', __name__)

@members_bp.route('/member/onboarding-consent', methods=['GET', 'POST'])
@login_required
def member_onboarding_consent():
    """Halaman persetujuan AD/ART, Peraturan Organisasi, dan Kode Etik Pecinta Alam Indonesia"""
    user = get_current_user()
    if user.consent_agreed:
        if not user.is_profile_complete:
            return redirect('/member/complete-profile')
        if user.status != 'active':
            return redirect('/member/onboarding-status')
        return redirect('/member/dashboard')

    if request.method == 'POST':
        agree_rules = request.form.get('agree_rules')
        agree_ethics = request.form.get('agree_ethics')
        if not (agree_rules and agree_ethics):
            return render_gimbal_modal(
                'onboarding_consent',
                context={
                    'user': user,
                    'error_msg': 'Mohon centang persetujuan Peraturan Organisasi dan Kode Etik untuk melanjutkan proses pendaftaran.'
                },
                active_page='onboarding_consent'
            )
        user.consent_agreed = True
        user.consent_agreed_at = datetime.utcnow()
        db.session.commit()
        return redirect('/member/complete-profile')

    return render_gimbal_modal('onboarding_consent', context={'user': user}, active_page='onboarding_consent')


@members_bp.route('/member/complete-profile', methods=['GET', 'POST'])
@login_required
def member_complete_profile():
    """Formulir pengisian informasi wajib keanggotaan (biodata, medis & kontak darurat)"""
    user = get_current_user()
    if not user.consent_agreed and user.status != 'active':
        return redirect('/member/onboarding-consent')
    if user.is_profile_complete and user.status == 'active':
        return redirect('/member/dashboard')

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        birth_place = request.form.get('birth_place', '').strip()
        birth_date = request.form.get('birth_date', '').strip()
        blood_type = request.form.get('blood_type', '').strip()
        address = request.form.get('address', '').strip()
        medical_history = request.form.get('medical_history', '').strip() or 'Tidak Ada'
        emergency_name = request.form.get('emergency_name', '').strip()
        emergency_relation = request.form.get('emergency_relation', '').strip()
        emergency_phone = request.form.get('emergency_phone', '').strip()

        # Validasi seluruh kolom wajib
        if not (name and phone and birth_place and birth_date and blood_type and address and emergency_name and emergency_relation and emergency_phone):
            return render_gimbal_modal(
                'complete_profile',
                context={'user': user, 'error_msg': 'Mohon lengkapi seluruh kolom wajib bertanda bintang (*).'},
                active_page='complete_profile'
            )

        user.name = name
        user.phone = phone
        user.birth_place = birth_place
        user.birth_date = birth_date
        user.blood_type = blood_type
        user.address = address
        user.medical_history = medical_history
        user.emergency_name = emergency_name
        user.emergency_relation = emergency_relation
        user.emergency_phone = emergency_phone

        db.session.commit()
        return redirect('/member/onboarding-status')

    return render_gimbal_modal('complete_profile', context={'user': user}, active_page='complete_profile')


@members_bp.route('/member/onboarding-status')
@login_required
def member_onboarding_status():
    """Halaman pemantau status registrasi, panduan pembayaran iuran pokok, dan konfirmasi approval"""
    user = get_current_user()
    if not user.is_profile_complete:
        return redirect('/member/complete-profile')

    dues_enabled = SystemSetting.get('dues_enabled', 'true').lower() == 'true'
    target_dues = Dues.query.filter_by(is_active=True).first() if dues_enabled else None
    latest_payment = user.latest_dues_payment
    
    is_prod = SystemSetting.get('midtrans_is_production', 'false').lower() == 'true'
    midtrans_client_key = SystemSetting.get('midtrans_client_key', 'SB-Mid-client-demo12345678')

    is_dues_paid = (not dues_enabled) or (user.is_dues_paid) or (latest_payment is not None and latest_payment.status == 'approved')
    is_payment_pending = (dues_enabled and latest_payment is not None and latest_payment.status == 'pending')

    return render_gimbal_modal(
        'onboarding_status',
        context={
            'user': user,
            'target_dues': target_dues,
            'dues_enabled': dues_enabled,
            'latest_payment': latest_payment,
            'is_dues_paid': is_dues_paid,
            'is_payment_pending': is_payment_pending,
            'midtrans_client_key': midtrans_client_key,
            'midtrans_is_production': is_prod
        },
        active_page='onboarding_status'
    )


@members_bp.route('/member/onboarding/pay', methods=['POST'])
@login_required
def member_onboarding_pay():
    """Unggah bukti transfer manual pembayaran iuran pokok registrasi keanggotaan"""
    user = get_current_user()
    dues_id = request.form.get('dues_id')
    dues = db.session.get(Dues, int(dues_id)) if (dues_id and dues_id.isdigit()) else Dues.query.filter_by(is_active=True).first()
    
    bank_name = request.form.get('bank_name', 'Transfer Bank').strip()
    try:
        amount_paid = float(request.form.get('amount_paid', dues.amount if dues else 15000))
    except (ValueError, TypeError):
        amount_paid = float(dues.amount if dues else 15000)
    notes = request.form.get('notes', 'Iuran Pokok Registrasi Calon Anggota').strip()

    proof_file = request.files.get('proof_file')
    proof_filename = '/static/pics/sample_proof.jpg'
    if proof_file and proof_file.filename:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'proofs')
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"proof_reg_{user.id}_{int(datetime.now().timestamp())}_{secure_filename(proof_file.filename)}"
        save_path = os.path.join(upload_dir, safe_name)
        proof_file.save(save_path)
        proof_filename = f"/uploads/proofs/{safe_name}"

    payment = DuesPayment(
        dues_id=dues.id if dues else 1,
        user_id=user.id,
        amount_paid=amount_paid,
        bank_name=bank_name,
        proof_image=proof_filename,
        notes=notes,
        status='pending'
    )
    db.session.add(payment)
    db.session.commit()

    return redirect('/member/onboarding-status')


# ========== MEMBER PORTAL & TIMELINE ROUTES =====================================

@members_bp.route('/member/dashboard')
@login_required
def member_dashboard():
    user = get_current_user()
    access_guard = check_member_access(user)
    if access_guard:
        return access_guard
    open_activities = Activity.query.filter_by(is_open=True).order_by(Activity.created_at.desc()).limit(4).all()
    
    dues_enabled = SystemSetting.get('dues_enabled', 'true').lower() == 'true'
    active_dues_list = Dues.query.filter_by(is_active=True).all() if dues_enabled else []
    
    if not dues_enabled or not active_dues_list:
        unpaid_count = 0
    else:
        paid_dues_ids = [p.dues_id for p in DuesPayment.query.filter_by(user_id=user.id, status='approved').all()]
        active_ids = [d.id for d in active_dues_list]
        unpaid_count = Dues.query.filter(Dues.id.in_(active_ids), Dues.id.notin_(paid_dues_ids)).count() if paid_dues_ids else len(active_dues_list)

    posts = Post.query.order_by(Post.created_at.desc()).limit(25).all()
    recent_chats = ChatMessage.query.order_by(ChatMessage.created_at.asc()).limit(35).all()

    all_activities = Activity.query.order_by(Activity.created_at.desc()).all()
    user_businesses = Sponsor.query.filter_by(owner_user_id=user.id).order_by(Sponsor.id.desc()).all()

    data = {
        'user': user,
        'open_activities': open_activities,
        'all_activities': all_activities,
        'dues_enabled': dues_enabled,
        'unpaid_count': unpaid_count,
        'posts': posts,
        'recent_chats': recent_chats,
        'user_businesses': user_businesses,
        'user_certifications': user.certifications_list
    }
    return render_gimbal_page('member/member_pages.html', 'member_dashboard', data, active_page='member_dashboard')


@members_bp.route('/member/profile-modal')
@login_required
def member_profile_modal():
    """Pusat Akun Anggota (Google Account Style Hub)"""
    user = get_current_user()
    initial_tab = request.args.get('tab', 'biodata')
    return render_template('components/modals.html', modal_type='profile_hub', user=user, initial_tab=initial_tab)


@members_bp.route('/member/profile-modal/update', methods=['POST'])
@login_required
def member_profile_modal_update():
    """Simpan perubahan profil anggota dari Google Account Hub Modal"""
    user = get_current_user()
    active_tab = request.form.get('active_tab', 'biodata')
    
    # 1. Handle upload file foto profil baru
    avatar_file = request.files.get('avatar_file')
    if avatar_file and avatar_file.filename:
        orig_filename = secure_filename(avatar_file.filename)
        ext = os.path.splitext(orig_filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
            safe_name = f"avatar_{user.id}_{int(datetime.utcnow().timestamp())}{ext}"
            save_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
            os.makedirs(save_dir, exist_ok=True)
            avatar_file.save(os.path.join(save_dir, safe_name))
            user.avatar = f"/uploads/avatars/{safe_name}"

    # 2. Handle preset avatar URL / direct custom URL jika dipilih
    avatar_url = request.form.get('avatar_url', '').strip()
    if avatar_url:
        user.avatar = avatar_url

    if 'name' in request.form:
        user.name = request.form.get('name', user.name).strip()
    if 'phone' in request.form:
        user.phone = request.form.get('phone', user.phone).strip()
    if 'birth_place' in request.form:
        user.birth_place = request.form.get('birth_place', user.birth_place).strip()
    if 'birth_date' in request.form:
        user.birth_date = request.form.get('birth_date', user.birth_date).strip()
    if 'address' in request.form:
        user.address = request.form.get('address', user.address).strip()
        
    if 'blood_type' in request.form:
        user.blood_type = request.form.get('blood_type', user.blood_type).strip()
    if 'medical_history' in request.form:
        user.medical_history = request.form.get('medical_history', user.medical_history).strip()
    if 'emergency_name' in request.form:
        user.emergency_name = request.form.get('emergency_name', user.emergency_name).strip()
    if 'emergency_relation' in request.form:
        user.emergency_relation = request.form.get('emergency_relation', user.emergency_relation).strip()
    if 'emergency_phone' in request.form:
        user.emergency_phone = request.form.get('emergency_phone', user.emergency_phone).strip()
        
    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    if new_password:
        if new_password == confirm_password:
            user.password_hash = new_password
        else:
            return render_template('components/modals.html', modal_type='profile_hub', user=user, initial_tab=active_tab, error_msg='Konfirmasi kata sandi baru tidak cocok!')

    db.session.commit()
    return render_template('components/modals.html', modal_type='profile_hub', user=user, initial_tab=active_tab, saved_success=True)


@members_bp.route('/member/activities')
@login_required
def member_activities():
    user = get_current_user()
    access_guard = check_member_access(user)
    if access_guard:
        return access_guard
    activities = Activity.query.order_by(Activity.created_at.desc()).all()
    my_part_ids = [p.activity_id for p in ActivityParticipant.query.filter_by(user_id=user.id).all()]
    data = {
        'activities': activities,
        'my_part_ids': my_part_ids
    }
    return render_gimbal_page('member/member_pages.html', 'member_activities', data, active_page='member_activities')


@members_bp.route('/member/activity/join/<int:activity_id>', methods=['POST'])
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


@members_bp.route('/member/post/create', methods=['POST'])
@login_required
def member_post_create():
    """Kirim postingan linimasa anggota beserta multi foto/video ekspedisi"""
    user = get_current_user()
    content = request.form.get('content', '').strip()
    location = request.form.get('location', '').strip()
    raw_activity_id = request.form.get('activity_id', '').strip()
    activity_id = int(raw_activity_id) if raw_activity_id and raw_activity_id.isdigit() and int(raw_activity_id) > 0 else None

    # Mengambil berkas media (multi-file)
    media_files = request.files.getlist('media_files')
    # Fallback kompatibilitas jika dikirim melalui field single 'image_file'
    single_image = request.files.get('image_file')
    if single_image and single_image.filename and single_image not in media_files:
        media_files.append(single_image)

    image_url_input = request.form.get('image_url', '').strip()

    valid_files = [f for f in media_files if f and f.filename]
    if not content and not valid_files and not image_url_input:
        return redirect('/member/dashboard')

    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'posts')
    os.makedirs(upload_dir, exist_ok=True)

    VIDEO_EXTS = {'.mp4', '.mov', '.webm', '.mkv'}
    IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

    created_media_entries = []
    primary_image_url = None

    idx = 0
    for f in valid_files:
        orig_name = secure_filename(f.filename)
        ext = os.path.splitext(orig_name)[1].lower()
        if ext in VIDEO_EXTS or ext in IMAGE_EXTS:
            m_type = 'video' if ext in VIDEO_EXTS else 'image'
            safe_name = f"post_{user.id}_{int(datetime.now().timestamp())}_{idx}_{orig_name}"
            save_path = os.path.join(upload_dir, safe_name)
            f.save(save_path)
            media_url = f"/uploads/posts/{safe_name}"
            created_media_entries.append((m_type, media_url, idx))
            if not primary_image_url:
                primary_image_url = media_url
            idx += 1

    if image_url_input:
        ext = os.path.splitext(image_url_input.split('?')[0])[1].lower()
        m_type = 'video' if ext in VIDEO_EXTS else 'image'
        created_media_entries.append((m_type, image_url_input, idx))
        if not primary_image_url:
            primary_image_url = image_url_input

    raw_sponsor_id = request.form.get('sponsor_id', '').strip()
    sponsor_id = int(raw_sponsor_id) if raw_sponsor_id and raw_sponsor_id.isdigit() and int(raw_sponsor_id) > 0 else None

    # Anti Double-Posting Linimasa: Cek duplikasi postingan identik dalam 24 jam terakhir (oleh member yang sama maupun admin/member lain)
    cleaned_input = " ".join(content.strip().split()).lower()
    if cleaned_input:
        recent_posts = Post.query.filter(Post.created_at >= datetime.utcnow() - timedelta(hours=24)).all()
        for rp in recent_posts:
            if rp.content and " ".join(rp.content.strip().split()).lower() == cleaned_input:
                flash(
                    "⚠️ Postingan dengan isi serupa atau sama persis sudah diterbitkan di linimasa dalam 24 jam terakhir (oleh Anda atau anggota/admin lain). "
                    "Mohon hindari duplikasi postingan.",
                    "warning"
                )
                if request.headers.get('HX-Request'):
                    return member_dashboard()
                return redirect('/member/dashboard')

    # Otomasi Moderasi AI (Etika Organisasi, Norma Komunitas & Komersial)
    from moderation import check_content_moderation
    is_blocked, violation_type, reason = check_content_moderation(content)
    if is_blocked:
        if violation_type == 'ethics':
            # Pelanggaran Etika & Norma diblokir mutlak untuk seluruh postingan
            flash(
                f"🚫 Postingan Ditolak (Moderasi Etika & Norma): {reason} "
                f"KPAB GIMBAL menjunjung tinggi Kode Etik Pencinta Alam Indonesia serta tata krama dan persaudaraan sesama petualang.",
                "error"
            )
            if request.headers.get('HX-Request'):
                return member_dashboard()
            return redirect('/member/dashboard')
        elif violation_type == 'commercial' and not sponsor_id:
            # Penjualan langsung tanpa melalui Lapak Resmi diarahkan ke portal Usaha Anggota
            flash(
                f"⚠️ Postingan Ditahan (Moderasi Komersial AI): {reason} "
                f"Linimasa utama diprioritaskan khusus untuk cerita ekspedisi, konservasi, dan kabar petualangan alam. "
                f"Silakan gunakan menu 'Usaha & Lapak Saya' agar produk Anda tampil resmi dengan badge mitra terverifikasi & fitur diskon KTA!",
                "warning"
            )
            if request.headers.get('HX-Request'):
                return member_dashboard()
            return redirect('/member/dashboard')

    new_post = Post(
        user_id=user.id,
        content=content,
        location=location,
        activity_id=activity_id,
        sponsor_id=sponsor_id,
        post_type='sponsor' if sponsor_id else 'general',
        image_url=primary_image_url
    )
    db.session.add(new_post)
    db.session.flush()

    for m_type, m_url, ord_idx in created_media_entries:
        p_media = PostMedia(
            post_id=new_post.id,
            media_type=m_type,
            media_url=m_url,
            order_index=ord_idx
        )
        db.session.add(p_media)

    db.session.commit()

    if request.headers.get('HX-Request'):
        return member_dashboard()

    return redirect('/member/dashboard')


@members_bp.route('/member/activity/documentation/<int:activity_id>')
@login_required
def member_activity_documentation(activity_id):
    """Modal album galeri dokumentasi ekspedisi yang bersumber dari kiriman tim di linimasa"""
    activity = Activity.query.get_or_404(activity_id)
    doc_items = activity.documentation_media
    return render_template(
        'components/modals.html',
        modal_type='activity_documentation',
        activity=activity,
        doc_items=doc_items
    )


@members_bp.route('/member/post/like/<int:post_id>', methods=['POST'])
@login_required
def member_post_like(post_id):
    user = get_current_user()
    post = Post.query.get_or_404(post_id)
    existing_like = PostLike.query.filter_by(post_id=post.id, user_id=user.id).first()

    if existing_like:
        db.session.delete(existing_like)
    else:
        like = PostLike(post_id=post.id, user_id=user.id)
        db.session.add(like)
    db.session.commit()

    is_liked = not bool(existing_like)
    like_count = len(post.likes)

    return f"""
    <button class="flex items-center gap-1.5 transition text-xs font-semibold {'text-rose-600' if is_liked else 'text-slate-500 hover:text-rose-600'}"
            hx-post="/member/post/like/{post.id}"
            hx-target="this"
            hx-swap="outerHTML">
        <i class="{'fas fa-heart text-rose-600 scale-110' if is_liked else 'far fa-heart'} transition-transform"></i>
        <span>{like_count} Salam Lestari</span>
    </button>
    """


@members_bp.route('/member/post/comment/<int:post_id>', methods=['POST'])
@login_required
def member_post_comment(post_id):
    user = get_current_user()
    post = Post.query.get_or_404(post_id)
    comment_text = request.form.get('comment', '').strip()

    if comment_text:
        comm = PostComment(post_id=post.id, user_id=user.id, content=comment_text)
        db.session.add(comm)
        db.session.commit()
        
    tmpl = "{% import 'member/member_pages.html' as pages %}{{ pages.render_post_comments(post, current_user) }}"
    return render_template_string(tmpl, post=post, current_user=user)


@members_bp.route('/member/post/delete/<int:post_id>', methods=['POST', 'DELETE'])
@login_required
def member_post_delete(post_id):
    user = get_current_user()
    post = Post.query.get_or_404(post_id)
    if post.user_id != user.id and not user.is_admin:
        return "<span class='text-xs text-rose-500 font-bold'>Anda tidak memiliki izin menghapus postingan ini.</span>", 403

    if post.image_url and post.image_url.startswith('/uploads/posts/'):
        try:
            filename = post.image_url.replace('/uploads/posts/', '')
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'posts', filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            current_app.logger.warning(f"Gagal menghapus file gambar post: {e}")

    db.session.delete(post)
    db.session.commit()
    return ""


@members_bp.route('/member/chat/messages')
def member_chat_messages():
    user = get_current_user()
    mode = request.args.get('mode', 'public').strip()
    recipient_id = request.args.get('recipient_id')
    
    if mode == 'private' and recipient_id:
        if not user:
            return "<div class='p-6 text-center text-slate-400 space-y-2'><i class='fas fa-lock text-slate-300 text-xl'></i><p class='text-xs font-semibold'>Silakan masuk untuk membaca pesan pribadi.</p></div>"
        try:
            rec_id = int(recipient_id)
            recipient = User.query.get(rec_id)
            if not recipient:
                return "<div class='p-4 text-center text-slate-400 text-xs'>Anggota tidak ditemukan.</div>"
                
            # Tandai pesan masuk dari lawan bicara sebagai telah dibaca
            ChatMessage.query.filter_by(user_id=rec_id, recipient_id=user.id, is_read=False).update({'is_read': True})
            db.session.commit()
            
            chats = ChatMessage.query.filter(
                ((ChatMessage.user_id == user.id) & (ChatMessage.recipient_id == rec_id)) |
                ((ChatMessage.user_id == rec_id) & (ChatMessage.recipient_id == user.id))
            ).order_by(ChatMessage.created_at.asc()).limit(60).all()
            
            tmpl = """
            {% if not chats %}
            <div class="p-6 text-center text-slate-400 space-y-2">
                <i class="fas fa-lock text-slate-300 text-xl"></i>
                <p class="text-xs">Percakapan pribadi dengan <strong class="text-slate-800">{{ recipient.name }}</strong>
                    {% if recipient.is_online %}
                    <span class="inline-block w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-emerald-200 shrink-0 align-middle ml-1" title="Online"></span>
                    {% endif %}
                </p>
                <p class="text-[10px] text-slate-400">Pesan bersifat privat & hanya dapat dibaca oleh Anda berdua.</p>
            </div>
            {% else %}
                {% for chat in chats %}
                <div class="flex flex-col {% if chat.user_id == current_user.id %}items-end{% else %}items-start{% endif %} mb-2">
                    {% if chat.user_id != current_user.id %}
                    <div class="flex items-center gap-1.5 mb-0.5 px-1">
                        <span class="text-[10px] font-bold text-slate-700">{{ chat.user.name }}</span>
                        {% if chat.user.is_online %}
                        <span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 ring-1 ring-emerald-200 shrink-0" title="Online"></span>
                        {% endif %}
                    </div>
                    {% endif %}
                    <div class="max-w-[85%] p-2.5 rounded-2xl {% if chat.user_id == current_user.id %}bg-orange-600 text-white rounded-tr-none shadow-sm{% else %}bg-white border border-slate-200 text-slate-800 rounded-tl-none shadow-xs{% endif %}">
                        <p class="text-xs leading-relaxed break-words">{{ chat.message }}</p>
                    </div>
                    <span class="text-[9px] text-slate-400 font-mono mt-0.5 px-1">
                        {{ chat.created_at.strftime('%H:%M') }}
                        {% if chat.user_id == current_user.id %}
                            {% if chat.is_read %}<i class="fas fa-check-double text-blue-500 ml-0.5 text-[8px]" title="Dibaca"></i>{% else %}<i class="fas fa-check text-slate-400 ml-0.5 text-[8px]" title="Terkirim"></i>{% endif %}
                        {% endif %}
                    </span>
                </div>
                {% endfor %}
            {% endif %}
            """
            return render_template_string(tmpl, chats=chats, current_user=user, recipient=recipient)
        except Exception as e:
            return f"<div class='p-4 text-center text-rose-500 text-xs'>Gagal memuat pesan: {str(e)}</div>"

    # Default: Mode Publik (Basecamp Chat)
    recent_chats = ChatMessage.query.filter(ChatMessage.recipient_id.is_(None)).order_by(ChatMessage.created_at.asc()).limit(40).all()
    tmpl = "{% import 'member/member_pages.html' as pages %}{{ pages.render_chat_messages(chats, current_user) }}"
    return render_template_string(tmpl, chats=recent_chats, current_user=user)


@members_bp.route('/member/chat/send', methods=['POST'])
@login_required
def member_chat_send():
    user = get_current_user()
    message = request.form.get('message', '').strip()
    mode = request.form.get('mode', 'public').strip()
    recipient_id_val = request.form.get('recipient_id')
    
    rec_id = None
    if recipient_id_val:
        try:
            rec_id = int(recipient_id_val)
        except (ValueError, TypeError):
            rec_id = None

    if message:
        chat = ChatMessage(user_id=user.id, recipient_id=rec_id, message=message[:500])
        db.session.add(chat)
        db.session.commit()

    if mode == 'private' and rec_id:
        recipient = User.query.get(rec_id)
        chats = ChatMessage.query.filter(
            ((ChatMessage.user_id == user.id) & (ChatMessage.recipient_id == rec_id)) |
            ((ChatMessage.user_id == rec_id) & (ChatMessage.recipient_id == user.id))
        ).order_by(ChatMessage.created_at.asc()).limit(60).all()
        
        tmpl = """
        {% for chat in chats %}
        <div class="flex flex-col {% if chat.user_id == current_user.id %}items-end{% else %}items-start{% endif %} mb-2">
            {% if chat.user_id != current_user.id %}
            <div class="flex items-center gap-1.5 mb-0.5 px-1">
                <span class="text-[10px] font-bold text-slate-700">{{ chat.user.name }}</span>
                {% if chat.user.is_online %}
                <span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 ring-1 ring-emerald-200 shrink-0" title="Online"></span>
                {% endif %}
            </div>
            {% endif %}
            <div class="max-w-[85%] p-2.5 rounded-2xl {% if chat.user_id == current_user.id %}bg-orange-600 text-white rounded-tr-none shadow-sm{% else %}bg-white border border-slate-200 text-slate-800 rounded-tl-none shadow-xs{% endif %}">
                <p class="text-xs leading-relaxed break-words">{{ chat.message }}</p>
            </div>
            <span class="text-[9px] text-slate-400 font-mono mt-0.5 px-1">
                {{ chat.created_at.strftime('%H:%M') }}
                {% if chat.user_id == current_user.id %}
                    {% if chat.is_read %}<i class="fas fa-check-double text-blue-500 ml-0.5 text-[8px]"></i>{% else %}<i class="fas fa-check text-slate-400 ml-0.5 text-[8px]"></i>{% endif %}
                {% endif %}
            </span>
        </div>
        {% endfor %}
        """
        return render_template_string(tmpl, chats=chats, current_user=user, recipient=recipient)
        
    recent_chats = ChatMessage.query.filter(ChatMessage.recipient_id.is_(None)).order_by(ChatMessage.created_at.asc()).limit(40).all()
    tmpl = "{% import 'member/member_pages.html' as pages %}{{ pages.render_chat_messages(chats, current_user) }}"
    return render_template_string(tmpl, chats=recent_chats, current_user=user)


@members_bp.route('/member/chat/contacts')
def member_chat_contacts():
    """Daftar rekan anggota untuk fitur Direct Message (Privat)"""
    user = get_current_user()
    if not user:
        return "<div class='p-6 text-center text-slate-400 text-xs'><i class='fas fa-user-lock text-slate-300 text-2xl mb-1.5'></i><p>Silakan masuk terlebih dahulu untuk melihat kontak anggota.</p></div>"

    active_members = User.query.filter(
        User.id != user.id,
        User.status == 'active'
    ).order_by(User.name.asc()).all()

    contacts_data = []
    for m in active_members:
        unread_count = ChatMessage.query.filter_by(
            user_id=m.id,
            recipient_id=user.id,
            is_read=False
        ).count()

        # Ambil pesan terakhir (jika pernah ada percakapan)
        last_chat = ChatMessage.query.filter(
            ((ChatMessage.user_id == user.id) & (ChatMessage.recipient_id == m.id)) |
            ((ChatMessage.user_id == m.id) & (ChatMessage.recipient_id == user.id))
        ).order_by(ChatMessage.id.desc()).first()

        contacts_data.append({
            'user': m,
            'unread_count': unread_count,
            'last_message': last_chat.message if last_chat else 'Belum ada obrolan',
            'last_time': last_chat.created_at.strftime('%H:%M') if last_chat else ''
        })

    tmpl = """
    {% if not contacts %}
    <div class="p-8 text-center text-slate-400 text-xs">
        <i class="fas fa-user-friends text-slate-300 text-2xl mb-1.5"></i>
        <p>Belum ada rekan anggota aktif lainnya.</p>
    </div>
    {% else %}
        {% for c in contacts %}
        {% set m = c.user %}
        <div onclick="window.openDirectChat && window.openDirectChat({{ m.id }}, '{{ m.name | replace("'", "\\'") }}', '{{ m.nra or "" }}', '{{ m.jabatan or m.role }}', '{{ m.avatar or "" }}', {{ 'true' if m.is_online else 'false' }})"
             class="p-2.5 hover:bg-orange-50/60 rounded-xl cursor-pointer transition flex items-center justify-between gap-2.5 border-b border-slate-50 last:border-0 group">
            <div class="flex items-center gap-2.5 min-w-0">
                <div class="relative shrink-0">
                    <img src="{{ m.avatar or '/static/pics/cartoon/avatar_sekjen.jpg' }}"
                         alt="{{ m.name }}"
                         class="w-9 h-9 rounded-full object-cover border border-slate-200">
                    {% if m.is_online %}
                    <span class="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 border-2 border-white rounded-full shadow-xs" title="Online"></span>
                    {% endif %}
                    {% if c.unread_count > 0 %}
                    <span class="absolute -top-1 -right-1 w-4 h-4 bg-orange-600 text-white font-bold text-[9px] rounded-full flex items-center justify-center border border-white">
                        {{ c.unread_count }}
                    </span>
                    {% endif %}
                </div>
                <div class="min-w-0">
                    <div class="flex items-center gap-1.5">
                        <p class="text-xs font-bold text-slate-900 group-hover:text-orange-900 truncate">{{ m.name }}</p>
                        {% if m.is_online %}
                        <span class="inline-block w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-emerald-200 shadow-xs shrink-0" title="Online"></span>
                        {% endif %}
                        {% if m.nra %}
                        <span class="px-1 py-0.2 bg-orange-50 text-orange-800 text-[8px] font-mono font-bold rounded border border-orange-200 shrink-0">{{ m.nra }}</span>
                        {% endif %}
                    </div>
                    <p class="text-[10px] text-slate-500 truncate mt-0.5">
                        {% if m.jabatan %}<span class="text-orange-700 font-semibold">{{ m.jabatan }}</span> • {% endif %}{{ c.last_message }}
                    </p>
                </div>
            </div>
            <div class="text-right shrink-0">
                {% if c.last_time %}
                <span class="text-[9px] text-slate-400 font-mono block">{{ c.last_time }}</span>
                {% endif %}
                <span class="text-[10px] text-orange-600 font-semibold opacity-0 group-hover:opacity-100 transition flex items-center gap-1 mt-0.5">
                    Chat <i class="fas fa-chevron-right text-[8px]"></i>
                </span>
            </div>
        </div>
        {% endfor %}
    {% endif %}
    """
    return render_template_string(tmpl, contacts=contacts_data)


@members_bp.route('/member/chat/unread-count')
def member_chat_unread_count():
    """Mengembalikan badge kecil jumlah pesan unread untuk floating button"""
    user = get_current_user()
    if not user:
        return ''
    unread_count = ChatMessage.query.filter_by(
        recipient_id=user.id,
        is_read=False
    ).count()

    if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
        return jsonify({'total_unread': unread_count})

    if unread_count > 0:
        return f'<span class="absolute -top-1 -right-1 px-1.5 py-0.5 bg-rose-500 text-white font-bold text-[10px] rounded-full border-2 border-white shadow-sm animate-pulse leading-none">{unread_count}</span>'
    return ''


@members_bp.route('/member/kta')
@login_required
def member_kta():
    user = get_current_user()
    access_guard = check_member_access(user)
    if access_guard:
        return access_guard
    if user.status != 'active' or not user.nra:
        return redirect('/member/dashboard')

    qr_img = qrcode.make(f"{request.host_url}verify-kta/{user.nra}")
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    data = {
        'user': user,
        'qr_base64': qr_base64
    }
    return render_gimbal_page('member/member_pages.html', 'member_kta', data, active_page='member_kta')


@members_bp.route('/member/iuran')
@login_required
def member_iuran():
    user = get_current_user()
    dues_enabled = SystemSetting.get('dues_enabled', 'true').lower() == 'true'
    active_dues = Dues.query.filter_by(is_active=True).all() if dues_enabled else []
    my_payments = DuesPayment.query.filter_by(user_id=user.id).order_by(DuesPayment.id.desc()).all()

    data = {
        'user': user,
        'dues_enabled': dues_enabled,
        'active_dues': active_dues,
        'my_payments': my_payments
    }
    return render_gimbal_page('member/member_pages.html', 'member_iuran', data, active_page='member_iuran')


@members_bp.route('/member/iuran/pay-modal/<int:dues_id>')
@login_required
def member_iuran_modal(dues_id):
    dues = Dues.query.get_or_404(dues_id)
    return render_template('components/modals.html', modal_type='pay_dues', dues=dues)


@members_bp.route('/member/iuran/pay/<int:dues_id>', methods=['POST'])
@login_required
def member_iuran_pay(dues_id):
    user = get_current_user()
    dues = Dues.query.get_or_404(dues_id)
    
    bank_name = request.form.get('bank_name', 'Transfer Bank')
    amount_paid = float(request.form.get('amount_paid', dues.amount))
    notes = request.form.get('notes', '')
    
    proof_file = request.files.get('proof_file')
    proof_filename = '/static/pics/sample_proof.jpg'
    if proof_file and proof_file.filename:
        safe_name = f"proof_{user.id}_{int(datetime.now().timestamp())}_{secure_filename(proof_file.filename)}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'proofs', safe_name)
        proof_file.save(save_path)
        proof_filename = f"/uploads/proofs/{safe_name}"

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


@members_bp.route('/member/documents')
@login_required
def member_documents():
    user = get_current_user()
    access_guard = check_member_access(user)
    if access_guard:
        return access_guard
    docs = Document.query.filter_by(is_public_to_members=True).order_by(Document.created_at.desc()).all()
    data = {'documents': docs}
    return render_gimbal_page('member/member_pages.html', 'member_documents', data, active_page='member_documents')


@members_bp.route('/documents/read/<int:doc_id>')
@members_bp.route('/member/documents/read/<int:doc_id>')
@login_required
def read_document(doc_id):
    """Full-screen interactive web reader untuk dokumen resmi (PDF, EPUB, DOCX, DOC, teks)"""
    user = get_current_user()
    doc = Document.query.get_or_404(doc_id)
    if not doc.is_public_to_members and not (user and user.is_admin):
        flash("Dokumen ini bersifat internal pengurus dan tidak dapat diakses publik.", "error")
        return redirect('/member/documents')
    return render_template('document_reader.html', document=doc, user=user)


@members_bp.route('/member/profile', methods=['GET', 'POST'])
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


@members_bp.route('/member/repo-maps')
@login_required
def member_repo_maps():
    user = get_current_user()
    access_guard = check_member_access(user)
    if access_guard:
        return access_guard
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
        'user': user,
        'selected_category': category,
        'selected_region': region
    }
    return render_gimbal_page('member/member_pages.html', 'member_repo_maps', data, active_page='member_repo_maps')


@members_bp.route('/member/repo-maps/toggle-share/<int:map_id>', methods=['POST'])
@login_required
def member_toggle_repo_map_share(map_id):
    """Toggle publikasi peta repo dari portal member (oleh Admin atau Uploader)"""
    user = get_current_user()
    map_item = MapRepository.query.get_or_404(map_id)
    if not (user.is_admin or map_item.uploaded_by == user.id):
        return "<span class='text-[10px] text-rose-500 font-bold'>Akses Ditolak</span>", 403

    map_item.is_shared_to_timeline = not bool(map_item.is_shared_to_timeline)
    if map_item.is_shared_to_timeline:
        existing = Post.query.filter_by(map_repo_id=map_item.id).first()
        if not existing:
            stats_str = ""
            if map_item.total_distance_km and map_item.total_distance_km > 0:
                stats_str += f" • Jarak: {map_item.total_distance_km} km"
            if map_item.total_waypoints and map_item.total_waypoints > 0:
                stats_str += f" • {map_item.total_waypoints} Waypoints"
            post = Post(
                user_id=user.id,
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
                hx-post="/member/repo-maps/toggle-share/{map_item.id}"
                hx-swap="outerHTML"
                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 hover:bg-emerald-200 transition shadow-xs cursor-pointer"
                title="Peta aktif di Linimasa (Klik untuk matikan)">
            <i class="fas fa-toggle-on text-emerald-600 text-xs"></i>
            <span>Linimasa: ON</span>
        </button>
        """
    else:
        return f"""
        <button type="button"
                hx-post="/member/repo-maps/toggle-share/{map_item.id}"
                hx-swap="outerHTML"
                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200 transition cursor-pointer"
                title="Peta belum dibagikan ke Linimasa (Klik untuk bagikan)">
            <i class="fas fa-toggle-off text-slate-400 text-xs"></i>
            <span>Linimasa: OFF</span>
        </button>
        """


@members_bp.route('/member/documents/toggle-share/<int:doc_id>', methods=['POST'])
@login_required
def member_toggle_doc_share(doc_id):
    """Toggle publikasi dokumen dari portal member (khusus Pengurus/Admin)"""
    user = get_current_user()
    if not user.is_admin:
        return "<span class='text-[10px] text-rose-500 font-bold'>Akses Ditolak</span>", 403
    doc = Document.query.get_or_404(doc_id)
    doc.is_shared_to_timeline = not bool(doc.is_shared_to_timeline)
    if doc.is_shared_to_timeline:
        existing = Post.query.filter_by(document_id=doc.id).first()
        if not existing:
            post = Post(
                user_id=user.id,
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
                hx-post="/member/documents/toggle-share/{doc.id}"
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
                hx-post="/member/documents/toggle-share/{doc.id}"
                hx-swap="outerHTML"
                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 hover:bg-slate-200 transition cursor-pointer"
                title="Dokumen belum dibagikan ke Linimasa (Klik untuk bagikan)">
            <i class="fas fa-toggle-off text-slate-400 text-xs"></i>
            <span>Linimasa: OFF</span>
        </button>
        """


@members_bp.route('/member/activity/share-to-timeline/<int:activity_id>', methods=['POST'])
@login_required
def member_activity_share_to_timeline(activity_id):
    """Membagikan agenda ekspedisi mendatang ke linimasa petualang dari dashboard member"""
    user = get_current_user()
    act = Activity.query.get_or_404(activity_id)

    # Buat postingan agenda ekspedisi
    if act.phase in ['planning', 'open']:
        content = (
            f"📢 AGENDA EKSPEDISI MENDATANG: {act.title}!\n\n"
            f"🗓️ Waktu Pelaksanaan: {act.activity_date}\n"
            f"📍 Kawasan: {act.location}\n"
            f"🧗 Kategori: {act.category} ({act.difficulty})\n"
            f"👥 Kuota Peserta: {act.total_confirmed} / {act.quota} personil.\n\n"
            f"{(act.description or 'Ayo bergabung dalam petualangan ini! Persiapkan fisik dan peralatan tim.')}"
        )
    elif act.phase == 'in_progress':
        content = (
            f"⛰️ OPERASI LAPANGAN SEDANG BERLANGSUNG: {act.title}!\n\n"
            f"Tim ekspedisi ({act.total_confirmed} personil) saat ini sedang beroperasi di kawasan {act.location} ({act.activity_date}).\n"
            f"Mari kita doakan kelancaran dan keselamatan personil tim. Salam Lestari!"
        )
    else:
        content = (
            f"🚩 LAPORAN EKSPEDISI: {act.title}!\n\n"
            f"Operasi lapangan di kawasan {act.location} ({act.activity_date}) telah selesai dengan {act.total_confirmed} personil selamat."
        )

    existing = Post.query.filter_by(activity_id=act.id, post_type='activity').first()
    if existing:
        existing.content = content
        existing.location = act.location
        existing.image_url = act.image_url
        existing.created_at = datetime.utcnow()
    else:
        post = Post(
            user_id=user.id,
            content=content,
            location=act.location,
            activity_id=act.id,
            image_url=act.image_url,
            post_type='activity'
        )
        db.session.add(post)
    act.is_shared_to_timeline = True
    db.session.commit()

    return f"""
    <span class="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-1 rounded-md border border-emerald-200">
        <i class="fas fa-check-circle text-emerald-600"></i> Terbagikan ke Linimasa
    </span>
    """


# ========== MEMBER BUSINESS DIRECTORY (USAHA ANGGOTA) ROUTES =====================

@members_bp.route('/member/business')
@login_required
def member_business():
    """Halaman Usaha & Lapak Anggota: Pendaftaran Usaha, Manajemen Produk & Promosi Resmi"""
    user = get_current_user()
    access_guard = check_member_access(user)
    if access_guard:
        return access_guard

    my_businesses = Sponsor.query.filter_by(owner_user_id=user.id).order_by(Sponsor.id.desc()).all()
    all_active_businesses = Sponsor.query.filter_by(is_active=True, status='active').order_by(Sponsor.order_index.asc()).all()

    data = {
        'user': user,
        'my_businesses': my_businesses,
        'has_business': len(my_businesses) > 0,
        'primary_business': my_businesses[0] if my_businesses else None,
        'all_active_businesses': all_active_businesses
    }
    return render_gimbal_page('member/member_pages.html', 'member_business', data, active_page='member_business')


@members_bp.route('/member/business/register', methods=['POST'])
@login_required
def member_business_register():
    """Formulir Pendaftaran Usaha Mandiri oleh Anggota (Maksimal 1 Usaha per Anggota)"""
    user = get_current_user()

    # Pembatasan Kebijakan: 1 Anggota hanya boleh mendaftarkan 1 Lapak / Usaha
    existing_biz = Sponsor.query.filter_by(owner_user_id=user.id).first()
    if existing_biz:
        flash(
            f"Pendaftaran Ditolak: Anda telah memiliki usaha terdaftar ('{existing_biz.name}'). "
            f"Setiap anggota dibatasi maksimal 1 lapak usaha resmi. Silakan gunakan tombol 'Edit Profil Usaha' untuk memperbarui data.",
            "warning"
        )
        if request.headers.get('HX-Request'):
            return member_business()
        return redirect('/member/business')

    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'cafe').strip()
    description = request.form.get('description', '').strip()
    promo_badge = request.form.get('promo_badge', 'Diskon KTA GIMBAL').strip()
    member_benefit = request.form.get('member_benefit', '').strip()
    address = request.form.get('address', '').strip()
    maps_url = request.form.get('maps_url', '').strip()
    whatsapp_number = request.form.get('whatsapp_number', '').strip()
    instagram_url = request.form.get('instagram_url', '').strip()

    if not name:
        flash("Gagal: Nama usaha/toko/cafe tidak boleh kosong.", "error")
        if request.headers.get('HX-Request'):
            return member_business()
        return redirect('/member/business')

    logo_file = request.files.get('logo_file')
    logo_url = '/static/pics/sample_sponsor.png'
    if logo_file and logo_file.filename:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'sponsors')
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"biz_user_{user.id}_{int(datetime.now().timestamp())}_{secure_filename(logo_file.filename)}"
        logo_file.save(os.path.join(upload_dir, safe_name))
        logo_url = f"/uploads/sponsors/{safe_name}"

    new_biz = Sponsor(
        name=name,
        logo_url=logo_url,
        category=category,
        tier='community_partner',
        description=description,
        promo_badge=promo_badge,
        member_benefit=member_benefit,
        address=address,
        maps_url=maps_url,
        whatsapp_number=whatsapp_number,
        instagram_url=instagram_url,
        owner_user_id=user.id,
        is_member_business=True,
        status='active',  # Auto-active dengan lencana Usaha Anggota Terverifikasi
        is_active=True
    )
    db.session.add(new_biz)
    db.session.commit()

    flash(f"Selamat! Usaha '{name}' berhasil didaftarkan dan mendapatkan lencana Usaha Rekanan Anggota GIMBAL.", "success")
    if request.headers.get('HX-Request'):
        return member_business()
    return redirect('/member/business')


@members_bp.route('/member/business/edit-modal/<int:sponsor_id>')
@login_required
def member_business_edit_modal(sponsor_id):
    """Modal Edit Profil Usaha / Lapak Milik Anggota Sendiri"""
    user = get_current_user()
    biz = Sponsor.query.filter_by(id=sponsor_id, owner_user_id=user.id).first_or_404()
    return render_template('components/modals.html', modal_type='edit_member_business', sponsor=biz)


@members_bp.route('/member/business/edit/<int:sponsor_id>', methods=['POST'])
@login_required
def member_business_edit(sponsor_id):
    """Perbarui Profil Usaha Anggota oleh Pemiliknya"""
    user = get_current_user()
    biz = Sponsor.query.filter_by(id=sponsor_id, owner_user_id=user.id).first_or_404()

    biz.name = request.form.get('name', biz.name).strip()
    biz.category = request.form.get('category', biz.category).strip()
    biz.description = request.form.get('description', '').strip()
    biz.promo_badge = request.form.get('promo_badge', '').strip()
    biz.member_benefit = request.form.get('member_benefit', '').strip()
    biz.address = request.form.get('address', '').strip()
    biz.maps_url = request.form.get('maps_url', '').strip()
    biz.whatsapp_number = request.form.get('whatsapp_number', '').strip()
    biz.instagram_url = request.form.get('instagram_url', '').strip()

    logo_file = request.files.get('logo_file')
    if logo_file and logo_file.filename:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'sponsors')
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"biz_user_{user.id}_{int(datetime.now().timestamp())}_{secure_filename(logo_file.filename)}"
        logo_file.save(os.path.join(upload_dir, safe_name))
        biz.logo_url = f"/uploads/sponsors/{safe_name}"

    db.session.commit()
    flash(f"Profil usaha '{biz.name}' berhasil diperbarui.", "success")
    if request.headers.get('HX-Request'):
        return member_business()
    return redirect('/member/business')


@members_bp.route('/member/business/product/create/<int:sponsor_id>', methods=['POST'])
@login_required
def member_business_product_create(sponsor_id):
    """Tambah Produk / Menu / Paket Jasa oleh Pemilik Usaha Anggota"""
    user = get_current_user()
    biz = Sponsor.query.filter_by(id=sponsor_id, owner_user_id=user.id).first_or_404()

    name = request.form.get('name', '').strip()
    price = float(request.form.get('price', 0) or 0)
    raw_disc = request.form.get('discount_price', '').strip()
    discount_price = float(raw_disc) if raw_disc else None
    description = request.form.get('description', '').strip()
    badge = request.form.get('badge', '').strip()

    if not name:
        flash("Gagal: Nama produk tidak boleh kosong.", "error")
        return redirect('/member/business')

    image_file = request.files.get('image_file')
    image_url = None
    if image_file and image_file.filename:
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products')
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"prod_biz_{biz.id}_{int(datetime.now().timestamp())}_{secure_filename(image_file.filename)}"
        image_file.save(os.path.join(upload_dir, safe_name))
        image_url = f"/uploads/products/{safe_name}"

    prod = SponsorProduct(
        sponsor_id=biz.id,
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
    flash(f"Produk '{name}' berhasil ditambahkan ke katalog usaha Anda.", "success")
    return redirect('/member/business')


@members_bp.route('/member/business/product/delete/<int:prod_id>', methods=['POST'])
@login_required
def member_business_product_delete(prod_id):
    """Hapus Produk Milik Usaha Anggota"""
    user = get_current_user()
    prod = SponsorProduct.query.get_or_404(prod_id)
    if prod.sponsor.owner_user_id != user.id and not user.is_admin:
        flash("Akses ditolak: Anda bukan pemilik produk ini.", "error")
        return redirect('/member/business')

    prod_name = prod.name
    db.session.delete(prod)
    db.session.commit()
    flash(f"Produk '{prod_name}' telah dihapus dari katalog.", "success")
    return redirect('/member/business')


def generate_business_post_content(biz, custom_caption=None):
    """Menyusun teks postingan resmi lapak usaha anggota & ringkasan katalog produk"""
    badge_str = f" [{biz.promo_badge}]" if biz.promo_badge else ""
    benefit_str = f"\n\n🎁 Diskon Spesial Anggota KTA: {biz.member_benefit}" if biz.member_benefit else ""

    prod_lines = []
    for p in biz.products[:3]:
        p_info = f"• {p.name} - Rp {p.price:,.0f}"
        if p.discount_price:
            p_info += f" (Khusus KTA: Rp {p.discount_price:,.0f})"
        prod_lines.append(p_info)

    prod_str = "\n\nKatalog Pilihan:\n" + "\n".join(prod_lines) if prod_lines else ""
    intro = custom_caption or f"Salam Petualang! Kunjungi gerai {biz.name}, rekanan resmi komunitas GIMBAL."

    return (
        f"🏪 USAHA ANGGOTA: {biz.name}{badge_str}\n\n"
        f"{intro}\n\n"
        f"{biz.description or ''}"
        f"{benefit_str}"
        f"{prod_str}\n\n"
        f"📍 Alamat: {biz.address or 'Gorontalo'}\n"
        f"Dukung sesama saudara petualang dengan berkunjung & berbelanja!"
    )


@members_bp.route('/member/business/toggle-share/<int:sponsor_id>', methods=['POST'])
@login_required
def member_business_toggle_share(sponsor_id):
    """Toggle publikasi profil & produk lapak anggota ke Linimasa Petualang (ON/OFF)"""
    user = get_current_user()
    biz = Sponsor.query.filter_by(id=sponsor_id).first_or_404()
    if not (user.is_admin or biz.owner_user_id == user.id):
        return "<span class='text-[10px] text-rose-500 font-bold'>Akses Ditolak</span>", 403

    biz.is_shared_to_timeline = not bool(biz.is_shared_to_timeline)
    btn_style = request.args.get('style', 'compact')

    if biz.is_shared_to_timeline:
        content = generate_business_post_content(biz, request.form.get('custom_caption', '').strip())
        existing = Post.query.filter_by(sponsor_id=biz.id).first()
        if existing:
            # Jika ON lagi, perbarui isi & letakkan di puncak timeline terkini (top current timeline)
            existing.content = content
            existing.location = biz.address or f"{biz.name}, Gorontalo"
            existing.image_url = None
            existing.post_type = 'sponsor'
            existing.created_at = datetime.utcnow()
        else:
            post = Post(
                user_id=user.id,
                content=content,
                sponsor_id=biz.id,
                location=biz.address or f"{biz.name}, Gorontalo",
                image_url=None,
                post_type='sponsor',
                created_at=datetime.utcnow()
            )
            db.session.add(post)
    else:
        # Saat OFF: otomatis hilang dari postingan linimasa
        Post.query.filter_by(sponsor_id=biz.id).delete()

    db.session.commit()

    # Respon HTMX langsung menggantikan tombol toggle tanpa merusak tampilan induk
    if request.headers.get('HX-Request'):
        if btn_style == 'full':
            if biz.is_shared_to_timeline:
                return f"""
                <button type="button"
                        hx-post="/member/business/toggle-share/{biz.id}?style=full"
                        hx-swap="outerHTML"
                        class="w-full sm:w-auto px-4 py-2 bg-emerald-100 hover:bg-emerald-200 text-emerald-800 border border-emerald-300 font-bold text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-2 cursor-pointer"
                        title="Lapak aktif di Linimasa (Klik untuk sembunyikan)">
                    <i class="fas fa-toggle-on text-emerald-600 text-sm"></i>
                    <span>Linimasa: ON</span>
                </button>
                """
            else:
                return f"""
                <button type="button"
                        hx-post="/member/business/toggle-share/{biz.id}?style=full"
                        hx-swap="outerHTML"
                        class="w-full sm:w-auto px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 font-semibold text-xs rounded-xl shadow-xs transition flex items-center justify-center gap-2 cursor-pointer"
                        title="Lapak belum di linimasa (Klik untuk aktifkan & terbitkan di puncak linimasa)">
                    <i class="fas fa-toggle-off text-slate-400 text-sm"></i>
                    <span>Linimasa: OFF</span>
                </button>
                """
        else:
            if biz.is_shared_to_timeline:
                return f"""
                <button type="button"
                        hx-post="/member/business/toggle-share/{biz.id}?style=compact"
                        hx-swap="outerHTML"
                        class="w-full py-1.5 px-2 bg-emerald-100 hover:bg-emerald-200 text-emerald-800 border border-emerald-300 rounded-lg text-[10px] font-bold transition flex items-center justify-center gap-1.5 cursor-pointer shadow-2xs"
                        title="Lapak aktif di Linimasa (Klik untuk sembunyikan)">
                    <i class="fas fa-toggle-on text-emerald-600 text-xs"></i>
                    <span>Linimasa: ON</span>
                </button>
                """
            else:
                return f"""
                <button type="button"
                        hx-post="/member/business/toggle-share/{biz.id}?style=compact"
                        hx-swap="outerHTML"
                        class="w-full py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-600 border border-slate-200 rounded-lg text-[10px] font-semibold transition flex items-center justify-center gap-1.5 cursor-pointer"
                        title="Lapak belum di linimasa (Klik untuk aktifkan & terbitkan di puncak linimasa)">
                    <i class="fas fa-toggle-off text-slate-400 text-xs"></i>
                    <span>Linimasa: OFF</span>
                </button>
                """

    flash(f"Status publikasi linimasa untuk usaha '{biz.name}' berhasil diperbarui.", "success")
    return redirect('/member/business')


@members_bp.route('/member/business/share-timeline/<int:sponsor_id>', methods=['POST'])
@login_required
def member_business_share_timeline(sponsor_id):
    """Kompatibilitas alias untuk toggle publikasi usaha anggota"""
    return member_business_toggle_share(sponsor_id)


# ==============================================================================
# PORTAL AKADEMI, SOP DIGITAL & SERTIFIKASI KESIAPAN LAPANGAN (MEMBER)
# ==============================================================================

@members_bp.route('/member/academy')
@login_required
def member_academy():
    """Beranda Portal E-Learning & Kurikulum SOP Digital Anggota"""
    user = get_current_user()
    access_guard = check_member_access(user)
    if access_guard:
        return access_guard

    tiers = AcademyTier.query.filter_by(is_active=True).order_by(AcademyTier.order_index.asc()).all()
    
    # Progress bacaan materi anggota
    completed_progress = UserLessonProgress.query.filter_by(user_id=user.id, is_completed=True).all()
    completed_lesson_ids = set(p.lesson_id for p in completed_progress)
    
    # Sertifikasi resmi yang diraih anggota
    certifications = UserCertification.query.filter_by(user_id=user.id, status='active').all()
    certified_tier_ids = set(c.tier_id for c in certifications)

    # Riwayat ujian terakhir
    recent_attempts = UserQuizAttempt.query.filter_by(user_id=user.id).order_by(UserQuizAttempt.id.desc()).limit(10).all()

    # Target tier wajib
    mandatory_tier = None
    if user.is_mandatory_certified:
        target_id = user.mandatory_tier_id or 1
        mandatory_tier = db.session.get(AcademyTier, target_id)

    data = {
        'user': user,
        'tiers': tiers,
        'completed_lesson_ids': completed_lesson_ids,
        'certified_tier_ids': certified_tier_ids,
        'certifications': certifications,
        'recent_attempts': recent_attempts,
        'mandatory_tier': mandatory_tier,
        'is_mandatory_pending': user.is_mandatory_certification_pending
    }
    return render_gimbal_page('member/member_pages.html', 'member_academy', data, active_page='member_academy')


@members_bp.route('/member/academy/lesson/<int:lesson_id>')
@login_required
def member_academy_lesson(lesson_id):
    """Pembaca Materi / SOP Digital (Teks SOP, PDF Reader, Video Embed & Peta GPX)"""
    user = get_current_user()
    access_guard = check_member_access(user)
    if access_guard:
        return access_guard

    lesson = db.session.get(AcademyLesson, lesson_id)
    if not lesson:
        flash("Materi pelajaran tidak ditemukan.", "error")
        return redirect('/member/academy')

    course = lesson.course
    tier = course.tier

    # Cari materi sebelum & sesudah dalam kursus
    all_lessons = list(course.lessons)
    current_idx = all_lessons.index(lesson) if lesson in all_lessons else 0
    prev_lesson = all_lessons[current_idx - 1] if current_idx > 0 else None
    next_lesson = all_lessons[current_idx + 1] if current_idx < len(all_lessons) - 1 else None

    # Status baca anggota
    prog = UserLessonProgress.query.filter_by(user_id=user.id, lesson_id=lesson.id).first()
    is_completed = bool(prog and prog.is_completed)

    data = {
        'user': user,
        'lesson': lesson,
        'course': course,
        'tier': tier,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'is_completed': is_completed
    }
    return render_gimbal_page('member/member_pages.html', 'member_lesson_view', data, active_page='member_academy')


@members_bp.route('/member/academy/lesson/<int:lesson_id>/complete', methods=['POST'])
@login_required
def member_academy_lesson_complete(lesson_id):
    """Menandai bab materi / SOP telah dipelajari dan diselesaikan anggota"""
    user = get_current_user()
    lesson = db.session.get(AcademyLesson, lesson_id)
    if not lesson:
        return jsonify({'success': False, 'message': 'Materi tidak ditemukan'}), 404

    prog = UserLessonProgress.query.filter_by(user_id=user.id, lesson_id=lesson.id).first()
    if not prog:
        prog = UserLessonProgress(user_id=user.id, lesson_id=lesson.id, is_completed=True, completed_at=datetime.utcnow())
        db.session.add(prog)
        db.session.commit()

    flash(f"Materi '{lesson.title}' telah berhasil diselesaikan!", "success")
    
    # Cari next lesson jika ada
    all_lessons = list(lesson.course.lessons)
    current_idx = all_lessons.index(lesson) if lesson in all_lessons else 0
    if current_idx < len(all_lessons) - 1:
        next_l = all_lessons[current_idx + 1]
        return redirect(f"/member/academy/lesson/{next_l.id}")
    
    # Jika bab terakhir dalam kursus, cek apakah kursus ini atau tier punya kuis
    quiz = lesson.course.quiz or lesson.course.tier.quizzes[0] if lesson.course.tier.quizzes else None
    if quiz:
        return redirect(f"/member/academy/quiz/{quiz.id}")

    return redirect('/member/academy')


@members_bp.route('/member/academy/quiz/<int:quiz_id>')
@login_required
def member_academy_quiz(quiz_id):
    """Lembar Ujian / Kuis Sertifikasi Kesiapan Operasional"""
    user = get_current_user()
    access_guard = check_member_access(user)
    if access_guard:
        return access_guard

    quiz = db.session.get(AcademyQuiz, quiz_id)
    if not quiz:
        flash("Ujian sertifikasi tidak ditemukan.", "error")
        return redirect('/member/academy')

    # Riwayat pengerjaan sebelumnya
    attempts = UserQuizAttempt.query.filter_by(user_id=user.id, quiz_id=quiz.id).order_by(UserQuizAttempt.id.desc()).all()
    latest_attempt = attempts[0] if attempts else None
    
    # Cek apakah sudah lulus
    has_passed = any(a.passed for a in attempts)
    user_cert = UserCertification.query.filter_by(user_id=user.id, tier_id=quiz.tier_id, status='active').first() if quiz.tier_id else None

    is_exam_mode = request.args.get('exam') == '1' or request.args.get('retake') == '1'

    data = {
        'user': user,
        'quiz': quiz,
        'attempts': attempts,
        'latest_attempt': latest_attempt,
        'has_passed': has_passed,
        'user_cert': user_cert,
        'is_exam_mode': is_exam_mode
    }
    return render_gimbal_page('member/member_pages.html', 'member_quiz_view', data, active_page='member_academy')


@members_bp.route('/member/academy/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
def member_academy_quiz_submit(quiz_id):
    """Kalkulasi Hasil Ujian, Penilaian Jawaban & Penerbitan Sertifikat Digital Otomatis"""
    user = get_current_user()
    quiz = db.session.get(AcademyQuiz, quiz_id)
    if not quiz:
        flash("Ujian tidak ditemukan.", "error")
        return redirect('/member/academy')

    total_questions = len(quiz.questions)
    if total_questions == 0:
        flash("Ujian ini belum memiliki butir soal.", "warning")
        return redirect(f"/member/academy/quiz/{quiz.id}")

    correct_count = 0
    total_points_earned = 0
    max_possible_points = sum(q.points for q in quiz.questions) or 100
    user_answers = {}

    for q in quiz.questions:
        ans_opt_id = request.form.get(f'question_{q.id}')
        if ans_opt_id and ans_opt_id.isdigit():
            chosen_opt = db.session.get(QuizOption, int(ans_opt_id))
            if chosen_opt and chosen_opt.question_id == q.id:
                user_answers[str(q.id)] = chosen_opt.id
                if chosen_opt.is_correct:
                    correct_count += 1
                    total_points_earned += q.points

    score_percentage = round((total_points_earned / max_possible_points) * 100, 1)
    passed = score_percentage >= quiz.passing_score

    attempt = UserQuizAttempt(
        user_id=user.id,
        quiz_id=quiz.id,
        score=score_percentage,
        passed=passed,
        total_questions=total_questions,
        correct_answers=correct_count,
        answers_json=json.dumps(user_answers),
        completed_at=datetime.utcnow()
    )
    db.session.add(attempt)
    db.session.flush()

    # Jika Lulus Ujian Sertifikasi Tingkat
    new_cert = None
    if passed and quiz.tier_id:
        existing_cert = UserCertification.query.filter_by(
            user_id=user.id,
            tier_id=quiz.tier_id,
            status='active'
        ).first()

        if not existing_cert:
            tier = quiz.tier
            cert_no = f"CERT-GIMBAL-{tier.order_index:02d}-{user.id:04d}-{datetime.utcnow().strftime('%y%m%d')}"
            new_cert = UserCertification(
                user_id=user.id,
                tier_id=tier.id,
                certificate_no=cert_no,
                status='active',
                score_achieved=score_percentage,
                issued_at=datetime.utcnow()
            )
            db.session.add(new_cert)

    db.session.commit()

    if passed:
        flash(f"LULUS! Selamat, Anda meraih skor {score_percentage}% pada ujian '{quiz.title}'. Lencana keahlian resmi telah disematkan di profil Anda!", "success")
    else:
        flash(f"Skor Anda {score_percentage}%. Batas minimal kelulusan adalah {quiz.passing_score}%. Silakan pelajari kembali materi dan coba lagi.", "warning")

    return redirect(f"/member/academy/quiz/{quiz.id}")


@members_bp.route('/member/academy/certificate/<cert_no>')
def member_academy_certificate(cert_no):
    """Tampilan Resmi Piagam Sertifikat Digital & Verifikasi QR Code"""
    cert = UserCertification.query.filter_by(certificate_no=cert_no).first_or_404()
    verify_url = f"{request.host_url}verify-cert/{cert.certificate_no}"
    
    qr_img = qrcode.make(verify_url)
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    data = {
        'cert': cert,
        'user': cert.user,
        'tier': cert.tier,
        'qr_base64': qr_base64,
        'verify_url': verify_url
    }
    return render_gimbal_page('member/member_pages.html', 'member_certificate_view', data, active_page='member_academy')


@members_bp.route('/verify-cert/<cert_no>')
def verify_cert_public(cert_no):
    """Halaman Verifikasi Publik Keaslian Sertifikat Kesiapan Lapangan"""
    cert = UserCertification.query.filter_by(certificate_no=cert_no).first()
    data = {
        'cert': cert,
        'cert_no': cert_no,
        'is_valid': bool(cert and cert.status == 'active')
    }
    return render_template('components/modals.html', modal_type='verify_cert_public', data=data)


