import paramiko
import time
import os

SERVER_IP = '10.75.0.51'
USERNAME = 'root'
PASSWORD = 'P4ssw0rd!'
REMOTE_DIR = '/root/gimbal-web'
PORT = 8082

import glob
_local_secrets = glob.glob('client_secret*.json')
_secret_tuple = [(_local_secrets[0], f'{REMOTE_DIR}/{_local_secrets[0]}')] if _local_secrets else []

FILES_TO_SYNC = _secret_tuple + [
    ('app.py', f'{REMOTE_DIR}/app.py'),
    ('helpers.py', f'{REMOTE_DIR}/helpers.py'),
    ('web_api.py', f'{REMOTE_DIR}/web_api.py'),
    ('admin_pages.py', f'{REMOTE_DIR}/admin_pages.py'),
    ('members_page.py', f'{REMOTE_DIR}/members_page.py'),
    ('models.py', f'{REMOTE_DIR}/models.py'),
    ('deploy_remote.py', f'{REMOTE_DIR}/deploy_remote.py'),
    ('test_app.py', f'{REMOTE_DIR}/test_app.py'),
    ('CONVERSATION_HISTORY.md', f'{REMOTE_DIR}/CONVERSATION_HISTORY.md'),
    ('README.md', f'{REMOTE_DIR}/README.md'),
    ('static/css/theme.css', f'{REMOTE_DIR}/static/css/theme.css'),
    ('static/js/theme-config.js', f'{REMOTE_DIR}/static/js/theme-config.js'),
    ('templates/index.html', f'{REMOTE_DIR}/templates/index.html'),
    ('templates/landing.html', f'{REMOTE_DIR}/templates/landing.html'),
    ('templates/shell.html', f'{REMOTE_DIR}/templates/shell.html'),
    ('templates/components/modals.html', f'{REMOTE_DIR}/templates/components/modals.html'),
    ('templates/components/float_chat.html', f'{REMOTE_DIR}/templates/components/float_chat.html'),
    ('templates/member/member_pages.html', f'{REMOTE_DIR}/templates/member/member_pages.html'),
    ('templates/admin/admin_pages.html', f'{REMOTE_DIR}/templates/admin/admin_pages.html'),
    ('seed.py', f'{REMOTE_DIR}/seed.py'),
    ('requirements.txt', f'{REMOTE_DIR}/requirements.txt'),
]

def get_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=15)
    return client

def main():
    print(f"Connecting to {SERVER_IP}...")
    client = get_client()
    sftp = client.open_sftp()
    
    print("Uploading updated files...")
    for local_path, remote_path in FILES_TO_SYNC:
        if not os.path.exists(local_path):
            print(f"Warning: {local_path} not found locally!")
            continue
            
        uploaded = False
        for attempt in range(3):
            try:
                print(f"Uploading {local_path} -> {remote_path} (attempt {attempt+1})")
                sftp.put(local_path, remote_path)
                uploaded = True
                break
            except Exception as e:
                print(f"Upload error: {e}. Reconnecting...")
                time.sleep(2)
                try:
                    sftp.close()
                    client.close()
                except Exception:
                    pass
                client = get_client()
                sftp = client.open_sftp()
                
        if not uploaded:
            raise RuntimeError(f"Failed to upload {local_path} after 3 attempts.")
            
    try:
        sftp.close()
    except Exception:
        pass
    
    print("Cleaning obsolete templates on remote server...")
    client.exec_command(f"rm -f {REMOTE_DIR}/templates/login.html {REMOTE_DIR}/templates/verify_kta.html {REMOTE_DIR}/templates/complete_profile.html {REMOTE_DIR}/templates/onboarding_status.html")

    print("Purging legacy 'Iuran Perawatan Tenda' and deduplicating Dues from remote database...")
    clean_py = f"cd {REMOTE_DIR} && DATABASE_URL='mysql+pymysql://gimbal-web:P4ssw0rd!@localhost/gimbal-web?charset=utf8mb4' {REMOTE_DIR}/venv/bin/python << 'EOF'\n" + """
from app import app
from models import db, Dues, DuesPayment

with app.app_context():
    tenda = Dues.query.filter(Dues.title.ilike('%Perawatan Tenda%')).all()
    for t in tenda:
        DuesPayment.query.filter_by(dues_id=t.id).delete()
        db.session.delete(t)
    db.session.commit()
    monthly = Dues.query.filter((Dues.title.ilike('%Bulanan%')) | (Dues.category == 'wajib')).order_by(Dues.id.asc()).all()
    if len(monthly) > 1:
        keeper = monthly[0]
        for dup in monthly[1:]:
            for p in DuesPayment.query.filter_by(dues_id=dup.id).all():
                p.dues_id = keeper.id
            db.session.delete(dup)
        db.session.commit()
        print(f"Deduplicated monthly dues. Kept ID: {keeper.id}")
    for d in Dues.query.all():
        print(f"Dues in DB: ID={d.id}, Title={d.title}, Active={d.is_active}, Amount={d.amount}")
EOF
"""
    stdin, stdout, stderr = client.exec_command(clean_py)
    clean_out = stdout.read().decode('utf-8').strip()
    clean_err = stderr.read().decode('utf-8').strip()
    if clean_out:
        print(clean_out)
    if clean_err:
        print(f"Cleanup stderr: {clean_err}")

    print("Running seed.py with updated master dues...")
    stdin, stdout, stderr = client.exec_command(
        f"cd {REMOTE_DIR} && DATABASE_URL='mysql+pymysql://gimbal-web:P4ssw0rd!@localhost/gimbal-web?charset=utf8mb4' {REMOTE_DIR}/venv/bin/python seed.py"
    )
    stdout.channel.recv_exit_status()

    print("Restarting gimbal.service on remote server...")
    stdin, stdout, stderr = client.exec_command("systemctl restart gimbal.service")
    stdout.channel.recv_exit_status()
    
    time.sleep(3)
    stdin, stdout, stderr = client.exec_command(f"curl -s -o /dev/null -w 'HTTP Status: %{{http_code}}' http://127.0.0.1:{PORT}/")
    status_out = stdout.read().decode('utf-8').strip()
    print(f"Health Check: {status_out}")
    
    stdin, stdout, stderr = client.exec_command("systemctl is-active gimbal.service")
    service_status = stdout.read().decode('utf-8').strip()
    print(f"Service status: {service_status}")
    
    client.close()
    print("Sync & Restart completed successfully!")

if __name__ == '__main__':
    main()
