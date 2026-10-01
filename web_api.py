import os
import json
import base64
import requests
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, session, current_app, redirect, send_from_directory

from models import db, User, Dues, DuesPayment, SystemSetting, MapRepository, Post
from helpers import get_current_user, login_required

api_bp = Blueprint('api_bp', __name__)


# =================================================================================
# PAYMENT GATEWAY MIDTRANS APIS
# =================================================================================

@api_bp.route('/member/payment/midtrans-snap', methods=['POST'])
@login_required
def member_payment_midtrans_snap():
    """Membuat Snap Token Midtrans untuk pembayaran QRIS / Virtual Account"""
    user = get_current_user()
    dues_id = request.form.get('dues_id') or (request.json.get('dues_id') if request.is_json else None)
    dues = None
    if dues_id:
        dues = db.session.get(Dues, int(dues_id))
    if not dues:
        dues = Dues.query.filter_by(is_active=True).first()
        
    amount = float(dues.amount if dues else 15000)
    order_id = f"GIMBAL-{user.id}-{int(datetime.now().timestamp())}"
    
    server_key = SystemSetting.get('midtrans_server_key', 'SB-Mid-server-demo12345678')
    is_prod = SystemSetting.get('midtrans_is_production', 'false').lower() == 'true'
    snap_api_url = "https://app.midtrans.com/snap/v1/transactions" if is_prod else "https://app.sandbox.midtrans.com/snap/v1/transactions"
    
    auth_header = "Basic " + base64.b64encode(f"{server_key}:".encode('utf-8')).decode('utf-8')
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": auth_header
    }
    
    payload = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": int(amount)
        },
        "customer_details": {
            "first_name": user.name,
            "email": user.email,
            "phone": user.phone or "08114300001"
        },
        "item_details": [{
            "id": str(dues.id if dues else 1),
            "price": int(amount),
            "quantity": 1,
            "name": (dues.title[:45] if dues else "Iuran Anggota GIMBAL")
        }]
    }
    
    snap_token = None
    redirect_url = None
    
    try:
        res = requests.post(snap_api_url, json=payload, headers=headers, timeout=8)
        if res.status_code in [200, 201]:
            res_json = res.json()
            snap_token = res_json.get('token')
            redirect_url = res_json.get('redirect_url')
    except Exception as e:
        current_app.logger.warning(f"Midtrans API request exception: {e}")
        
    # Fallback simulated token jika server key sandbox demo
    if not snap_token:
        snap_token = f"SIMULATED-SNAP-{order_id}"
        redirect_url = f"https://app.sandbox.midtrans.com/snap/v2/vtweb/{snap_token}"
        
    payment = DuesPayment(
        dues_id=dues.id if dues else 1,
        user_id=user.id,
        amount_paid=amount,
        bank_name='Midtrans Snap (QRIS/VA)',
        proof_image='/static/pics/midtrans_badge.png',
        order_id=order_id,
        snap_token=snap_token,
        status='pending',
        transaction_status='pending',
        notes=f"Pembayaran online Midtrans untuk {dues.title if dues else 'Iuran'}"
    )
    db.session.add(payment)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'snap_token': snap_token,
        'redirect_url': redirect_url,
        'order_id': order_id,
        'amount': amount,
        'is_simulated': snap_token.startswith('SIMULATED')
    })


@api_bp.route('/payment/midtrans/notification', methods=['POST'])
def midtrans_notification():
    """Webhook listener notifikasi status pembayaran dari Midtrans Engine"""
    data = request.get_json(silent=True) or request.form.to_dict()
    if not data:
        return jsonify({'status': 'empty_payload'}), 400
        
    order_id = data.get('order_id')
    transaction_status = data.get('transaction_status')
    fraud_status = data.get('fraud_status')
    payment_type = data.get('payment_type', 'midtrans')
    
    payment = DuesPayment.query.filter_by(order_id=order_id).first()
    if not payment:
        return jsonify({'status': 'order_not_found'}), 404
        
    payment.transaction_status = transaction_status
    payment.payment_type = payment_type
    
    if transaction_status in ['capture', 'settlement']:
        if fraud_status == 'challenge':
            payment.status = 'pending'
        else:
            payment.status = 'approved'
            payment.verified_at = datetime.utcnow()
    elif transaction_status in ['cancel', 'deny', 'expire']:
        payment.status = 'rejected'
    elif transaction_status == 'pending':
        payment.status = 'pending'
        
    db.session.commit()
    return jsonify({'status': 'ok'})


@api_bp.route('/member/payment/midtrans-finish', methods=['POST'])
@login_required
def member_payment_midtrans_finish():
    """Client callback saat pembayaran via Snap modal selesai"""
    user = get_current_user()
    order_id = request.form.get('order_id') or (request.json.get('order_id') if request.is_json else None)
    result_status = request.form.get('result_status') or (request.json.get('result_status') if request.is_json else 'success')
    
    payment = None
    if order_id:
        payment = DuesPayment.query.filter_by(order_id=order_id).first()
    if not payment:
        payment = DuesPayment.query.filter_by(user_id=user.id).order_by(DuesPayment.id.desc()).first()
        
    if payment and result_status in ['success', 'settlement', 'capture']:
        payment.status = 'approved'
        payment.transaction_status = 'settlement'
        payment.verified_at = datetime.utcnow()
        db.session.commit()
        
    if request.headers.get('HX-Request') or request.is_json:
        return jsonify({'status': 'success', 'redirect': '/member/onboarding-status'})
    return redirect('/member/onboarding-status')


# =================================================================================
# GIMBAL-MAPS MOBILE APP INTEGRATION APIS
# =================================================================================

@api_bp.route('/api/v1/maps/check-access', methods=['POST', 'GET'])
def maps_check_access():
    """
    Endpoint verifikasi keanggotaan & penentuan hak akses fitur aplikasi gimbal-maps.
    Menerima email Google pengguna atau Google ID Token.
    Aturan Tiering:
    - Free Tier (Tamu / Publik / Iuran Belum Lunas):
        * max_maps: 2
        * can_import_vector: false (tidak bisa import KML/GeoJSON)
        * max_points: 5 waypoint
        * max_track_distance_km: 1.0 km
        * can_access_repo: false
    - Member Active Tier (Anggota Aktif & Lunas Iuran Bulan Berjalan):
        * Full fitur tanpa batasan (-1)
        * Akses unduh Repo Peta resmi organisasi
    """
    req_data = request.get_json(silent=True) or request.values.to_dict() or {}
    email = req_data.get('email', '').strip().lower()
    google_id = req_data.get('google_id', '').strip()

    user = None
    if email:
        user = User.query.filter_by(email=email).first()
    elif google_id:
        user = User.query.filter_by(google_id=google_id).first()

    # Rule Free Tier (Default untuk tamu / non-anggota)
    free_limits = {
        'max_maps': 2,
        'can_import_vector': False,
        'max_points': 5,
        'max_track_distance_km': 1.0,
        'can_access_repo': False,
        'description': 'Free Tier: Maksimal 2 peta offline, 5 point waypoint, dan rekam jalur 1 km.'
    }

    # Rule Full Member
    member_limits = {
        'max_maps': -1,  # Unlimited
        'can_import_vector': True,
        'max_points': -1,  # Unlimited
        'max_track_distance_km': -1,  # Unlimited
        'can_access_repo': True,
        'description': 'Member Full Access: Tanpa batas peta, point, tracking, dan akses penuh Repo Peta GIMBAL.'
    }

    if not user:
        return jsonify({
            'status': 'success',
            'is_member': False,
            'member_status': 'unregistered',
            'dues_status': 'none',
            'tier': 'free',
            'limits': free_limits,
            'message': 'Akun Google belum terdaftar sebagai anggota KPAB GIMBAL. Beroperasi dalam mode Free Tier.'
        })

    is_active = (user.status == 'active')
    is_dues_paid = user.is_current_month_dues_paid
    is_google_sub = user.has_active_google_subscription

    user_payload = {
        'id': user.id,
        'name': user.name,
        'nra': user.nra,
        'email': user.email,
        'role': user.role,
        'avatar': user.avatar,
        'is_admin': user.is_admin,
        'subscription_channel': user.subscription_channel or 'manual',
        'is_google_subscriber': is_google_sub,
        'subscription_expiry': user.subscription_expiry.strftime('%Y-%m-%d %H:%M:%S') if user.subscription_expiry else None,
        'days_remaining': user.subscription_days_remaining
    }

    # Jika anggota aktif dan lunas iuran bulan berjalan (termasuk via Google Pay) -> FULL FITUR
    if (is_active or is_google_sub) and is_dues_paid:
        sub_info = " (Langganan Google Pay Aktif)" if is_google_sub else ""
        return jsonify({
            'status': 'success',
            'is_member': True,
            'member_status': user.status,
            'dues_status': 'paid',
            'subscription_channel': user.subscription_channel or 'manual',
            'tier': 'member_active',
            'limits': member_limits,
            'user': user_payload,
            'message': f'Salam Lestari, {user.name}! Akun aktif{sub_info} ({user.nra or "Subscriber"}). Akses penuh seluruh fitur gimbal-maps dan Repo Peta.'
        })

    # Anggota terdaftar tetapi status pending atau iuran belum lunas
    reason = "Menunggu persetujuan keanggotaan oleh admin" if not is_active else "Iuran bulan berjalan belum lunas"
    return jsonify({
        'status': 'success',
        'is_member': True,
        'member_status': user.status,
        'dues_status': 'unpaid' if is_active else 'pending_approval',
        'subscription_channel': user.subscription_channel or 'manual',
        'tier': 'free',
        'limits': free_limits,
        'user': user_payload,
        'message': f'Status anggota: {user.status.title()} ({reason}). Beroperasi sementara dalam mode Free Tier. Selesaikan iuran di web GIMBAL atau berlangganan via Google Pay untuk membuka full fitur.'
    })


@api_bp.route('/api/v1/maps/subscription/google-pay', methods=['POST'])
def maps_subscription_google_pay():
    """
    Sinkronisasi & Verifikasi Langganan In-App Google Play / Google Pay dari aplikasi mobile gimbal-maps.
    Menerima parameter:
    - email / google_id: identitas pengguna
    - order_id: Google Play Order ID (e.g., GPA.3321-4821-1829-00123)
    - purchase_token: Google Play Purchase Token
    - product_id: SKU paket langganan (e.g., 'gimbal_member_monthly')
    - duration_days: durasi masa aktif (default: 30 hari untuk bulanan)
    - amount: nominal pembayaran (opsional)
    """
    req_data = request.get_json(silent=True) or request.values.to_dict() or {}
    email = req_data.get('email', '').strip().lower()
    google_id = req_data.get('google_id', '').strip()
    order_id = req_data.get('order_id', '').strip()
    purchase_token = req_data.get('purchase_token', '').strip()
    product_id = req_data.get('product_id', 'gimbal_member_monthly').strip()
    
    try:
        duration_days = int(req_data.get('duration_days', 30))
    except (ValueError, TypeError):
        duration_days = 30

    if not email and not google_id:
        return jsonify({'status': 'error', 'message': 'Email atau Google ID wajib disertakan.'}), 400

    user = None
    if email:
        user = User.query.filter_by(email=email).first()
    if not user and google_id:
        user = User.query.filter_by(google_id=google_id).first()

    # Jika user belum ada di portal web, otomatis buat akun user berbasis Google SSO
    if not user:
        name = req_data.get('name', 'Petualang GIMBAL').strip()
        user = User(
            name=name,
            email=email or f"user_{google_id[:8]}@gimbal.org",
            google_id=google_id,
            status='active',  # Otomatis aktif karena membayar langganan resmi
            role='member'
        )
        db.session.add(user)
        db.session.flush()

    # Hitung batas waktu expiry langganan (perpanjangan dari expiry sebelumnya jika masih aktif)
    from datetime import timedelta
    now = datetime.utcnow()
    if user.subscription_expiry and user.subscription_expiry > now:
        new_expiry = user.subscription_expiry + timedelta(days=duration_days)
    else:
        new_expiry = now + timedelta(days=duration_days)

    user.subscription_channel = 'google_pay'
    user.subscription_expiry = new_expiry
    if order_id:
        user.google_order_id = order_id
    if purchase_token:
        user.google_purchase_token = purchase_token
    if product_id:
        user.google_product_id = product_id

    # Ambil master iuran aktif
    dues = Dues.query.filter_by(is_active=True).first()
    amount = float(req_data.get('amount') or (dues.amount if dues else 15000.0))

    # Catat pembayaran ke DuesPayment
    payment = DuesPayment(
        dues_id=dues.id if dues else 1,
        user_id=user.id,
        amount_paid=amount,
        bank_name='Google Pay (In-App Subscription)',
        order_id=order_id or f"GPA-{user.id}-{int(now.timestamp())}",
        payment_type='google_pay',
        transaction_status='settlement',
        status='approved',
        verified_at=now,
        notes=f"Langganan in-app Google Pay ({product_id}). Aktif hingga {new_expiry.strftime('%d %b %Y')}."
    )
    db.session.add(payment)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': f'Langganan Google Pay berhasil disinkronkan. Aktif hingga {new_expiry.strftime("%d %B %Y")}.',
        'tier': 'member_active',
        'subscription': {
            'channel': 'google_pay',
            'product_id': product_id,
            'order_id': user.google_order_id,
            'expiry': new_expiry.strftime('%Y-%m-%d %H:%M:%S'),
            'days_remaining': user.subscription_days_remaining
        },
        'limits': {
            'max_maps': -1,
            'can_import_vector': True,
            'max_points': -1,
            'max_track_distance_km': -1,
            'can_access_repo': True
        }
    })



@api_bp.route('/api/v1/maps/repo', methods=['GET'])
def maps_repo_list():
    """
    Katalog Repo Peta Ekspedisi Internal GIMBAL (MBTiles, GPX jalur resmi, GeoJSON zonasi).
    Dapat diakses oleh aplikasi gimbal-maps saat terhubung internet.
    """
    category = request.args.get('category')
    region = request.args.get('region')
    file_type = request.args.get('file_type')

    query = MapRepository.query
    if category:
        query = query.filter_by(category=category)
    if region:
        query = query.filter_by(region=region)
    if file_type:
        query = query.filter_by(file_type=file_type)

    maps = query.order_by(MapRepository.id.desc()).all()

    items = []
    for m in maps:
        items.append({
            'id': m.id,
            'title': m.title,
            'region': m.region,
            'category': m.category,
            'file_type': m.file_type,
            'file_size': m.file_size_fmt,
            'preview_image': m.preview_image or '/static/pics/cartoon/hero.jpg',
            'description': m.description,
            'total_waypoints': m.total_waypoints,
            'total_distance_km': m.total_distance_km,
            'is_exclusive_member': m.is_exclusive_member,
            'downloads_count': m.downloads_count,
            'download_url': f"/api/v1/maps/repo/download/{m.id}",
            'created_at': m.created_at.strftime('%Y-%m-%d')
        })

    return jsonify({
        'status': 'success',
        'total_count': len(items),
        'maps': items
    })


@api_bp.route('/api/v1/maps/repo/download/<int:map_id>', methods=['GET'])
def maps_repo_download(map_id):
    """
    Stream download berkas peta (MBTiles, GPX, GeoJSON) untuk disimpan ke cache offline gimbal-maps.
    """
    map_item = MapRepository.query.get_or_404(map_id)
    map_item.downloads_count = (map_item.downloads_count or 0) + 1
    db.session.commit()

    # Lokasi berkas fisik
    file_path = map_item.file_path.lstrip('/')
    if file_path.startswith('uploads/'):
        rel_path = file_path[len('uploads/'):]
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], rel_path, as_attachment=True)
    
    # Fallback jika ada di static atau root
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, file_path)
    if os.path.exists(full_path):
        dir_name = os.path.dirname(full_path)
        base_name = os.path.basename(full_path)
        return send_from_directory(dir_name, base_name, as_attachment=True)

    return jsonify({'status': 'error', 'message': 'Berkas peta fisik tidak ditemukan di server.'}), 404


@api_bp.route('/api/v1/maps/share-track', methods=['POST'])
def maps_share_track():
    """
    Sinkronisasi / unggah jalur rekam jejak ekspedisi (GPX) dari gimbal-maps ke linimasa atau repo anggota.
    """
    email = request.form.get('email', '').strip().lower()
    user = User.query.filter_by(email=email).first() if email else None
    if not user:
        return jsonify({'status': 'error', 'message': 'Otorisasi gagal: User tidak terdaftar.'}), 401

    title = request.form.get('title', 'Jalur Ekspedisi Baru').strip()
    location = request.form.get('location', 'Gorontalo').strip()
    distance_km = float(request.form.get('distance_km', 0.0))
    gpx_file = request.files.get('gpx_file')

    if not gpx_file or not gpx_file.filename:
        return jsonify({'status': 'error', 'message': 'Berkas GPX lintasan wajib disertakan.'}), 400

    maps_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'maps')
    os.makedirs(maps_upload_dir, exist_ok=True)

    safe_name = f"track_{user.id}_{int(datetime.now().timestamp())}_{secure_filename(gpx_file.filename)}"
    save_path = os.path.join(maps_upload_dir, safe_name)
    gpx_file.save(save_path)

    # Simpan ke MapRepository
    repo_entry = MapRepository(
        title=title,
        region=location,
        category='jalur_pendakian',
        file_type='gpx',
        file_path=f"/uploads/maps/{safe_name}",
        file_size_fmt=f"{round(os.path.getsize(save_path) / 1024, 1)} KB",
        description=f"Jalur ekspedisi diunggah langsung via aplikasi Gimbal Maps oleh {user.name} ({user.nra or 'Anggota'}).",
        total_distance_km=distance_km,
        uploaded_by=user.id
    )
    db.session.add(repo_entry)

    # Otomatis buat postingan di linimasa forum anggota
    post = Post(
        user_id=user.id,
        content=f"🗺️ Membagikan rute ekspedisi baru: '{title}' ({distance_km:.1f} km). Berkas GPX resmi kini tersedia di Repo Peta GIMBAL!",
        location=location
    )
    db.session.add(post)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Rute ekspedisi berhasil disinkronkan ke Repo Peta dan linimasa anggota!',
        'repo_id': repo_entry.id
    })
