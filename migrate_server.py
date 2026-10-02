import os
import sys
import time
import paramiko

OLD_IP = '10.75.0.51'
OLD_USER = 'root'
OLD_PASS = 'P4ssw0rd!'
OLD_DIR = '/root/gimbal-web'

NEW_IP = '10.75.0.16'
NEW_USER = 'root'
NEW_PASS = 'R4h4514!?!'
NEW_DIR = '/root/gimbal-web'

DB_NAME = 'gimbal-web'
DB_USER = 'gimbal-web'
DB_PASS = 'P4ssw0rd!'
PORT = 8082

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_SQL = os.path.join(LOCAL_DIR, 'migration_gimbal.sql')
TMP_UPLOADS = os.path.join(LOCAL_DIR, 'migration_uploads.tar.gz')

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def run_cmd(client, cmd, check=True):
    log(f">> [EXEC]: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        try:
            print(f"STDOUT:\n{out}", flush=True)
        except UnicodeEncodeError:
            print(f"STDOUT:\n{out.encode('ascii', 'replace').decode('ascii')}", flush=True)
    if err:
        try:
            print(f"STDERR:\n{err}", flush=True)
        except UnicodeEncodeError:
            print(f"STDERR:\n{err.encode('ascii', 'replace').decode('ascii')}", flush=True)
    if check and exit_status != 0:
        raise RuntimeError(f"Command failed with exit code {exit_status}: {cmd}\n{err}")
    return exit_status, out, err

def sftp_mkdir_p(sftp, remote_dir):
    parts = remote_dir.strip('/').split('/')
    cur = ''
    for p in parts:
        cur += '/' + p
        try:
            sftp.stat(cur)
        except IOError:
            try:
                sftp.mkdir(cur)
            except Exception:
                pass

def dump_old_server():
    log(f"=== STEP 1: Dumping data from OLD SERVER ({OLD_IP}) ===")
    c_old = paramiko.SSHClient()
    c_old.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c_old.connect(OLD_IP, username=OLD_USER, password=OLD_PASS, timeout=10)

    # 1. Dump database
    log("Dumping MySQL database from old server...")
    dump_cmd = f"mysqldump -u root -pP4ssw0rd! --databases '{DB_NAME}' --add-drop-database > /tmp/gimbal_migration.sql"
    run_cmd(c_old, dump_cmd)

    # 2. Archive uploads
    log("Creating archive of uploads folder from old server...")
    run_cmd(c_old, f"tar -czf /tmp/gimbal_uploads.tar.gz -C {OLD_DIR} uploads || tar -czf /tmp/gimbal_uploads.tar.gz -T /dev/null")

    # 3. Download dump and uploads to local
    sftp = c_old.open_sftp()
    log("Downloading SQL dump to local...")
    sftp.get('/tmp/gimbal_migration.sql', TMP_SQL)
    log(f"SQL dump size: {os.path.getsize(TMP_SQL)} bytes")

    log("Downloading uploads archive to local...")
    sftp.get('/tmp/gimbal_uploads.tar.gz', TMP_UPLOADS)
    log(f"Uploads archive size: {os.path.getsize(TMP_UPLOADS)} bytes")

    sftp.close()
    c_old.close()
    log("Dump from old server completed successfully.")

def setup_new_server():
    log(f"=== STEP 2: Preparing NEW SERVER ({NEW_IP}) ===")
    c_new = paramiko.SSHClient()
    c_new.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c_new.connect(NEW_IP, username=NEW_USER, password=NEW_PASS, timeout=10)

    # 1. Install MariaDB and required system packages
    log("Updating apt and installing MariaDB + Python packages...")
    run_cmd(c_new, "export DEBIAN_FRONTEND=noninteractive; apt-get update -qq && apt-get install -y -qq mariadb-server mariadb-client python3-venv python3-pip python3-pymysql python3-pillow python3-cryptography curl git tar gzip")
    run_cmd(c_new, "systemctl enable --now mariadb")

    # 2. Setup MySQL user and import database
    log("Configuring database and importing SQL dump...")
    sftp = c_new.open_sftp()
    sftp.put(TMP_SQL, '/tmp/gimbal_migration.sql')
    sftp.put(TMP_UPLOADS, '/tmp/gimbal_uploads.tar.gz')

    # Import dump
    run_cmd(c_new, "mariadb < /tmp/gimbal_migration.sql || mysql < /tmp/gimbal_migration.sql")

    # Ensure user privileges
    sql_user = f"""
CREATE USER IF NOT EXISTS '{DB_USER}'@'localhost' IDENTIFIED BY '{DB_PASS}';
ALTER USER '{DB_USER}'@'localhost' IDENTIFIED BY '{DB_PASS}';
GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{DB_USER}'@'localhost';

CREATE USER IF NOT EXISTS '{DB_USER}'@'%' IDENTIFIED BY '{DB_PASS}';
ALTER USER '{DB_USER}'@'%' IDENTIFIED BY '{DB_PASS}';
GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{DB_USER}'@'%';

FLUSH PRIVILEGES;
"""
    cmd_user = f"cat << 'EOF' > /tmp/setup_user.sql\n{sql_user}\nEOF\nmariadb < /tmp/setup_user.sql || mysql < /tmp/setup_user.sql\nrm -f /tmp/setup_user.sql"
    run_cmd(c_new, cmd_user)

    # Test database connection with gimbal-web user
    run_cmd(c_new, f"mariadb -u {DB_USER} -p{DB_PASS} {DB_NAME} -e 'SELECT COUNT(*) AS total_users FROM users; SELECT COUNT(*) AS total_activities FROM activities;'")

    # 3. Upload application files from local
    log(f"=== STEP 3: Deploying application to {NEW_DIR} ===")
    run_cmd(c_new, f"mkdir -p {NEW_DIR}")

    # Sync folders: templates, static, assets
    for folder in ['templates', 'static', 'assets']:
        local_folder = os.path.join(LOCAL_DIR, folder)
        if not os.path.exists(local_folder):
            continue
        for root, dirs, files in os.walk(local_folder):
            rel = os.path.relpath(root, LOCAL_DIR).replace('\\', '/')
            rem_dir = f"{NEW_DIR}/{rel}"
            sftp_mkdir_p(sftp, rem_dir)
            for f in files:
                lp = os.path.join(root, f)
                rp = f"{rem_dir}/{f}"
                sftp.put(lp, rp)

    # Core python files
    core_files = [
        'app.py', 'helpers.py', 'web_api.py', 'admin_pages.py', 'members_page.py',
        'models.py', 'cloudflare_email.py', 'seed.py', 'requirements.txt',
        'test_rol_and_sync.py', 'test_rol_tabs.py', 'CONVERSATION_HISTORY.md'
    ]
    for fname in core_files:
        lp = os.path.join(LOCAL_DIR, fname)
        if os.path.exists(lp):
            rp = f"{NEW_DIR}/{fname}"
            sftp.put(lp, rp)

    # Upload Google OAuth credentials
    import glob, json
    g_cid = ""
    g_csec = ""
    g_ruri = "https://www.gimbal.my.id"
    for cfile in glob.glob(os.path.join(LOCAL_DIR, 'client_secret*.json')):
        cfname = os.path.basename(cfile)
        sftp.put(cfile, f"{NEW_DIR}/{cfname}")
        log(f"Uploaded OAuth credential: {cfname}")
        try:
            with open(cfile, 'r', encoding='utf-8') as cf:
                cdata = json.load(cf).get('web', {})
                g_cid = cdata.get('client_id', g_cid)
                g_csec = cdata.get('client_secret', g_csec)
                if cdata.get('redirect_uris'):
                    g_ruri = cdata['redirect_uris'][0]
        except Exception:
            pass

    # 4. Extract uploads archive
    log("Restoring uploads directory...")
    run_cmd(c_new, f"tar -xzf /tmp/gimbal_uploads.tar.gz -C {NEW_DIR}/ || mkdir -p {NEW_DIR}/uploads")
    run_cmd(c_new, f"mkdir -p {NEW_DIR}/uploads/proofs {NEW_DIR}/uploads/docs {NEW_DIR}/uploads/gallery {NEW_DIR}/uploads/posts {NEW_DIR}/uploads/avatars {NEW_DIR}/uploads/maps {NEW_DIR}/uploads/expeditions")

    # 5. Create .env configuration
    env_content = f"""DATABASE_URL=mysql+pymysql://{DB_USER}:{DB_PASS}@localhost/{DB_NAME}?charset=utf8mb4
PORT={PORT}
SECRET_KEY=gimbal-adventure-secret-key-2026
FLASK_ENV=production
GOOGLE_CLIENT_ID={g_cid}
GOOGLE_CLIENT_SECRET={g_csec}
GOOGLE_REDIRECT_URI={g_ruri}
"""
    with sftp.open(f"{NEW_DIR}/.env", 'w') as f:
        f.write(env_content)
    log("Created .env configuration file on new server.")

    sftp.close()

    # 6. Setup Python virtual environment
    log("Setting up Python virtual environment...")
    run_cmd(c_new, f"python3 -m venv --system-site-packages {NEW_DIR}/venv")
    run_cmd(c_new, f"{NEW_DIR}/venv/bin/pip install Flask Flask-SQLAlchemy SQLAlchemy qrcode Pillow requests python-dotenv PyMySQL gunicorn")

    # 7. Configure systemd service
    log(f"Configuring systemd service on port {PORT}...")
    service_content = f"""[Unit]
Description=KPAB GIMBAL WebApps (Gunicorn WSGI)
After=network.target mariadb.service mysql.service

[Service]
Type=simple
User=root
WorkingDirectory={NEW_DIR}
Environment="PATH={NEW_DIR}/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="FLASK_ENV=development"
Environment="FLASK_DEBUG=1"
Environment="DEBUG=True"
Environment="PORT={PORT}"
Environment="DATABASE_URL=mysql+pymysql://{DB_USER}:{DB_PASS}@localhost/{DB_NAME}?charset=utf8mb4"
ExecStart={NEW_DIR}/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:{PORT} --timeout 120 --access-logfile - --error-logfile - app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
    cmd_service = f"cat << 'EOF' > /etc/systemd/system/gimbal.service\n{service_content}\nEOF"
    run_cmd(c_new, cmd_service)
    run_cmd(c_new, "systemctl daemon-reload")
    run_cmd(c_new, "systemctl enable gimbal.service")
    run_cmd(c_new, "systemctl restart gimbal.service")
    time.sleep(3)
    run_cmd(c_new, "systemctl status gimbal.service --no-pager")

    # 8. Verify endpoints on new server
    log(f"=== STEP 4: Verifying service on NEW SERVER ({NEW_IP}) ===")
    run_cmd(c_new, f"curl -s -o /dev/null -w 'HTTP Status [GET /]: %{{http_code}}\\n' http://127.0.0.1:{PORT}/")
    run_cmd(c_new, f"curl -s -o /dev/null -w 'HTTP Status [GET /login]: %{{http_code}}\\n' http://127.0.0.1:{PORT}/login")
    run_cmd(c_new, f"curl -s -o /dev/null -w 'HTTP Status [GET /verify-kta/R-01-26]: %{{http_code}}\\n' http://127.0.0.1:{PORT}/verify-kta/R-01-26")
    run_cmd(c_new, f"curl -s -o /dev/null -w 'HTTP Status [GET /api/v1/activities/active]: %{{http_code}}\\n' http://127.0.0.1:{PORT}/api/v1/activities/active")
    run_cmd(c_new, f"curl -s -o /dev/null -w 'HTTP Status [GET /admin/activity/1/print]: %{{http_code}}\\n' 'http://127.0.0.1:{PORT}/admin/activity/1/print'")

    # Clean up temp files
    run_cmd(c_new, "rm -f /tmp/gimbal_migration.sql /tmp/gimbal_uploads.tar.gz")
    c_new.close()

    # Clean local temp files
    if os.path.exists(TMP_SQL):
        os.remove(TMP_SQL)
    if os.path.exists(TMP_UPLOADS):
        os.remove(TMP_UPLOADS)

    log("==========================================================================")
    log(f"MIGRATION COMPLETE! Application successfully running on http://{NEW_IP}:{PORT}")
    log("==========================================================================")

def main():
    dump_old_server()
    setup_new_server()

if __name__ == '__main__':
    main()
