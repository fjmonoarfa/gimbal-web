import os
import sys
import paramiko
import time

SERVER_IP = '10.75.0.51'
USERNAME = 'root'
PASSWORD = 'P4ssw0rd!'
REMOTE_DIR = '/root/gimbal-web'
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

DB_NAME = 'gimbal-web'
DB_USER = 'gimbal-web'
DB_PASS = 'P4ssw0rd!'
PORT = 8082

EXCLUDE_DIRS = {'.git', '__pycache__', 'venv', '.idea', '.vscode', '.system_generated', '.tempmediaStorage', '.user_uploaded'}
EXCLUDE_FILES = {'inspect_remote.py', 'deploy_remote.py', 'check_status.py', 'check_ps.py', 'check_templates.py', 'check_static.py', 'instance', 'gimbal.db'}

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def run_ssh_cmd(client, cmd, check=True):
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

def upload_templates_and_missing(client):
    log("Checking and uploading code, templates, static, and assets...")
    sftp = client.open_sftp()
    
    # Sync folders: templates, static, assets
    for folder in ['templates', 'static', 'assets']:
        local_folder = os.path.join(LOCAL_DIR, folder)
        if not os.path.exists(local_folder):
            continue
        for root, dirs, files in os.walk(local_folder):
            rel = os.path.relpath(root, LOCAL_DIR).replace('\\', '/')
            rem_dir = f"{REMOTE_DIR}/{rel}"
            sftp_mkdir_p(sftp, rem_dir)
            for f in files:
                lp = os.path.join(root, f)
                rp = f"{rem_dir}/{f}"
                try:
                    rstat = sftp.stat(rp)
                    lstat = os.stat(lp)
                    if rstat.st_size != lstat.st_size or int(lstat.st_mtime) > int(rstat.st_mtime):
                        sftp.put(lp, rp)
                        log(f"Updated: {rp}")
                except IOError:
                    sftp.put(lp, rp)
                    log(f"Uploaded: {rp}")
                    
    # Ensure core files are always up to date
    for fname in ['app.py', 'helpers.py', 'web_api.py', 'admin_pages.py', 'members_page.py', 'models.py', 'cloudflare_email.py', 'seed.py', 'requirements.txt', 'test_rol_and_sync.py', 'CONVERSATION_HISTORY.md']:
        lp = os.path.join(LOCAL_DIR, fname)
        if os.path.exists(lp):
            rp = f"{REMOTE_DIR}/{fname}"
            sftp.put(lp, rp)
            log(f"Updated core file: {fname}")
        
    # Create / update .env file on remote server
    env_content = f"""DATABASE_URL=mysql+pymysql://{DB_USER}:{DB_PASS}@localhost/{DB_NAME}?charset=utf8mb4
PORT={PORT}
SECRET_KEY=gimbal-adventure-secret-key-2026
FLASK_ENV=production
"""
    with sftp.open(f"{REMOTE_DIR}/.env", 'w') as f:
        f.write(env_content)
    log("Updated remote .env configuration file.")
        
    sftp.close()

def setup_mysql(client):
    log("Verifying MySQL database and user...")
    sql_script = f"""
CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '{DB_USER}'@'localhost' IDENTIFIED BY '{DB_PASS}';
ALTER USER '{DB_USER}'@'localhost' IDENTIFIED BY '{DB_PASS}';
GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{DB_USER}'@'localhost';

CREATE USER IF NOT EXISTS '{DB_USER}'@'%' IDENTIFIED BY '{DB_PASS}';
ALTER USER '{DB_USER}'@'%' IDENTIFIED BY '{DB_PASS}';
GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{DB_USER}'@'%';

FLUSH PRIVILEGES;
"""
    cmd = f"cat << 'EOF' > /tmp/setup_gimbal.sql\n{sql_script}\nEOF\nmysql -u root -pP4ssw0rd! < /tmp/setup_gimbal.sql\nrm -f /tmp/setup_gimbal.sql"
    run_ssh_cmd(client, cmd)
    run_ssh_cmd(client, f"mysql -u {DB_USER} -p{DB_PASS} {DB_NAME} -e 'SELECT 1 AS connection_test;'")
    log("MySQL connection test: SUCCESS")

def setup_python_env(client):
    log("Setting up Python virtual environment on server...")
    # First install any system packages if available for speed
    run_ssh_cmd(client, "apt-get update -qq && apt-get install -y -qq python3-venv python3-pip python3-pymysql python3-pillow python3-cryptography || true", check=False)
    
    # Create venv with system-site-packages
    run_ssh_cmd(client, f"test -d {REMOTE_DIR}/venv || python3 -m venv --system-site-packages {REMOTE_DIR}/venv")
    
    # Fast install of required packages in venv
    run_ssh_cmd(client, f"{REMOTE_DIR}/venv/bin/pip install Flask Flask-SQLAlchemy SQLAlchemy qrcode Pillow requests python-dotenv PyMySQL gunicorn")
    log("Python environment ready.")

def populate_database(client):
    log("Ensuring upload directories exist on server...")
    run_ssh_cmd(client, f"mkdir -p {REMOTE_DIR}/uploads/proofs {REMOTE_DIR}/uploads/docs {REMOTE_DIR}/uploads/gallery {REMOTE_DIR}/uploads/posts {REMOTE_DIR}/uploads/avatars {REMOTE_DIR}/uploads/maps {REMOTE_DIR}/uploads/expeditions")
    log("Upload directories ready.")

def setup_systemd(client):
    log(f"Configuring systemd service on port {PORT}...")
    service_content = f"""[Unit]
Description=KPAB GIMBAL WebApps (Gunicorn WSGI)
After=network.target mariadb.service mysql.service

[Service]
Type=simple
User=root
WorkingDirectory={REMOTE_DIR}
Environment="PATH={REMOTE_DIR}/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="FLASK_ENV=development"
Environment="FLASK_DEBUG=1"
Environment="DEBUG=True"
Environment="PORT={PORT}"
Environment="DATABASE_URL=mysql+pymysql://{DB_USER}:{DB_PASS}@localhost/{DB_NAME}?charset=utf8mb4"
ExecStart={REMOTE_DIR}/venv/bin/gunicorn --workers 2 --bind 0.0.0.0:{PORT} --timeout 120 --access-logfile - --error-logfile - app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
    cmd = f"cat << 'EOF' > /etc/systemd/system/gimbal.service\n{service_content}\nEOF"
    run_ssh_cmd(client, cmd)
    run_ssh_cmd(client, "systemctl daemon-reload")
    run_ssh_cmd(client, "systemctl enable gimbal.service")
    run_ssh_cmd(client, "systemctl restart gimbal.service")
    time.sleep(2)
    run_ssh_cmd(client, "systemctl status gimbal.service --no-pager")

def verify_deployment(client):
    log("Verifying endpoints on remote server...")
    run_ssh_cmd(client, f"curl -s -o /dev/null -w 'HTTP Status [GET /]: %{{http_code}}\\n' http://127.0.0.1:{PORT}/")
    run_ssh_cmd(client, f"curl -s -o /dev/null -w 'HTTP Status [GET /login]: %{{http_code}}\\n' http://127.0.0.1:{PORT}/login")
    run_ssh_cmd(client, f"curl -s -o /dev/null -w 'HTTP Status [GET /verify-kta/R-01-26]: %{{http_code}}\\n' http://127.0.0.1:{PORT}/verify-kta/R-01-26")
    run_ssh_cmd(client, f"curl -s -o /dev/null -w 'HTTP Status [GET /api/v1/activities/active]: %{{http_code}}\\n' http://127.0.0.1:{PORT}/api/v1/activities/active")
    run_ssh_cmd(client, f"curl -s -o /dev/null -w 'HTTP Status [GET /admin/activity/preset-rol]: %{{http_code}}\\n' 'http://127.0.0.1:{PORT}/admin/activity/preset-rol?category=Gunung%20Hutan'")

def main():
    log(f"Connecting to {SERVER_IP}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=10)
    log("Connected.")
    
    try:
        setup_mysql(client)
        upload_templates_and_missing(client)
        setup_python_env(client)
        populate_database(client)
        setup_systemd(client)
        verify_deployment(client)
        log("=======================================================")
        log(f"DEPLOYMENT SUCCEEDED! Service running on http://{SERVER_IP}:{PORT}")
        log("=======================================================")
    finally:
        client.close()

if __name__ == '__main__':
    main()
