import re
import requests
import logging
from models import db, User, SystemSetting

logger = logging.getLogger('cloudflare_email')

def clean_username_for_alias(user, domain="gimbal.my.id"):
    """
    Menghasilkan alamat email alias resmi @gimbal.my.id yang bersih dan unik.
    Mendukung input berupa instance model User maupun string email.
    Contoh:
      - Email: 'budi.pendaki@gmail.com' -> 'budi_pendaki@gimbal.my.id'
      - Jika ada duplikat: 'budi_pendaki_2@gimbal.my.id'
    """
    user_id = getattr(user, 'id', None)
    email_str = user if isinstance(user, str) else (getattr(user, 'email', '') or '')
    name_str = '' if isinstance(user, str) else (getattr(user, 'name', '') or '')

    prefix = ""
    if email_str:
        raw_prefix = email_str.split('@')[0].split('+')[0]
        # Bersihkan titik, strip, plus, dan karakter non-alphanumeric
        prefix = re.sub(r'[^a-zA-Z0-9]+', '_', raw_prefix).strip('_').lower()
    
    if not prefix and name_str:
        prefix = re.sub(r'[^a-zA-Z0-9]+', '_', name_str).strip('_').lower()
        
    if not prefix:
        prefix = f"member_{user_id or 'new'}"

    base_alias = f"{prefix}@{domain}"
    candidate_alias = base_alias
    counter = 1

    # Cek apakah alias sudah digunakan oleh user lain
    while True:
        query = User.query.filter(User.gimbal_alias_email == candidate_alias)
        if user_id:
            query = query.filter(User.id != user_id)
        existing = query.first()
        if not existing:
            break
        counter += 1
        candidate_alias = f"{prefix}_{counter}@{domain}"

    return candidate_alias


def sync_cloudflare_email_routing(user):
    """
    Mendaftarkan atau memperbarui aturan Email Forwarding di Cloudflare API v4.
    Setiap user akan memiliki alias forwarding ke email asli (Gmail / email lain).
    """
    domain = SystemSetting.get('cloudflare_domain', 'gimbal.my.id') or 'gimbal.my.id'
    
    # 1. Pastikan alias lokal sudah dibuat
    if not user.gimbal_alias_email or not user.gimbal_alias_email.endswith(f"@{domain}"):
        user.gimbal_alias_email = clean_username_for_alias(user, domain=domain)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Error persisting alias for user {user.id}: {e}")

    enabled = (SystemSetting.get('cloudflare_enabled', 'false').lower() == 'true')
    api_token = SystemSetting.get('cloudflare_api_token', '').strip()
    zone_id = SystemSetting.get('cloudflare_zone_id', '').strip()

    if not enabled or not api_token or not zone_id:
        # Jika belum dikonfigurasi API Cloudflare, status tetap siap lokal
        if user.cloudflare_status != 'active':
            user.cloudflare_status = 'ready_local'
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        return {
            'success': True,
            'alias': user.gimbal_alias_email,
            'status': user.cloudflare_status,
            'message': 'Alias email lokal siap. Integrasi Cloudflare API belum diaktifkan.'
        }

    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    }

    try:
        # Step A: Daftarkan Destination Address (jika belum ada)
        addr_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/addresses"
        addr_payload = {'email': user.email}
        try:
            requests.post(addr_url, json=addr_payload, headers=headers, timeout=8)
        except Exception as _e_addr:
            logger.info(f"Destination address registration note: {_e_addr}")

        # Step B: Buat Routing Rule
        rules_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/rules"
        rule_name = f"GIMBAL Forwarding - {user.name} ({user.id})"
        rule_payload = {
            "name": rule_name,
            "enabled": True,
            "matchers": [
                {
                    "type": "literal",
                    "field": "to",
                    "value": user.gimbal_alias_email
                }
            ],
            "actions": [
                {
                    "type": "forward",
                    "value": [user.email]
                }
            ]
        }

        # Jika user sudah punya rule_id sebelumnya, update rule
        if user.cloudflare_rule_id:
            put_url = f"{rules_url}/{user.cloudflare_rule_id}"
            resp = requests.put(put_url, json=rule_payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                user.cloudflare_status = 'active'
                db.session.commit()
                return {'success': True, 'alias': user.gimbal_alias_email, 'status': 'active'}
        
        # Buat baru jika belum ada rule
        resp = requests.post(rules_url, json=rule_payload, headers=headers, timeout=10)
        data = resp.json() if resp.status_code in [200, 201] else {}
        
        if resp.status_code in [200, 201] and data.get('success'):
            rule_obj = data.get('result', {})
            user.cloudflare_rule_id = rule_obj.get('id')
            user.cloudflare_status = 'active'
            db.session.commit()
            return {'success': True, 'alias': user.gimbal_alias_email, 'status': 'active'}
        else:
            errors = data.get('errors', [])
            err_msg = errors[0].get('message') if errors else resp.text
            user.cloudflare_status = 'api_error'
            db.session.commit()
            return {'success': False, 'alias': user.gimbal_alias_email, 'status': 'api_error', 'error': err_msg}

    except Exception as e:
        logger.error(f"Cloudflare sync exception for user {user.id}: {e}")
        return {'success': False, 'alias': user.gimbal_alias_email, 'status': 'exception', 'error': str(e)}


def delete_cloudflare_email_rule(user):
    """
    Menghapus routing rule dari Cloudflare saat user dihapus permanen.
    """
    if not user.cloudflare_rule_id:
        return
    api_token = SystemSetting.get('cloudflare_api_token', '').strip()
    zone_id = SystemSetting.get('cloudflare_zone_id', '').strip()
    if not api_token or not zone_id:
        return

    try:
        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/rules/{user.cloudflare_rule_id}"
        headers = {'Authorization': f'Bearer {api_token}'}
        requests.delete(url, headers=headers, timeout=8)
    except Exception as e:
        logger.warning(f"Failed to delete Cloudflare rule {user.cloudflare_rule_id}: {e}")
