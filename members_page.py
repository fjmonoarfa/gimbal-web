import os
import io
import base64
import qrcode
from datetime import datetime
from flask import Blueprint, request, redirect, render_template, render_template_string, make_response, current_app, jsonify
from werkzeug.utils import secure_filename
from models import (
    db, User, Dues, DuesPayment, Document, Activity,
    ActivityParticipant, GalleryItem, Post, PostComment,
    PostLike, ChatMessage, SystemSetting, MapRepository, PostMedia
)
from helpers import get_current_user, login_required, check_member_access, render_gimbal_page, render_gimbal_modal

members_bp = Blueprint('members_page', __name__)

# ========== MEMBER ONBOARDING & PROFILE COMPLETION ===============================

@members_bp.route('/member/complete-profile', methods=['GET', 'POST'])
@login_required
def member_complete_profile():
    """Formulir pengisian informasi wajib keanggotaan (biodata, medis & kontak darurat)"""
    user = get_current_user()
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

    data = {
        'user': user,
        'open_activities': open_activities,
        'all_activities': all_activities,
        'dues_enabled': dues_enabled,
        'unpaid_count': unpaid_count,
        'posts': posts,
        'recent_chats': recent_chats
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

    new_post = Post(
        user_id=user.id,
        content=content,
        location=location,
        activity_id=activity_id,
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
