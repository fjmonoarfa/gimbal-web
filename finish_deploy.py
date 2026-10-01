import os
import sys
import paramiko
import time

SERVER_IP = '10.75.0.51'
USERNAME = 'root'
PASSWORD = 'P4ssw0rd!'
REMOTE_DIR = '/root/gimbal-web'

DB_NAME = 'gimbal-web'
DB_USER = 'gimbal-web'
DB_PASS = 'P4ssw0rd!'
PORT = 8082

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def run_ssh_cmd(client, cmd, check=True):
    log(f">> [EXEC]: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        print("STDOUT:\n" + out.encode('ascii', errors='replace').decode('ascii'), flush=True)
    if err:
        print("STDERR:\n" + err.encode('ascii', errors='replace').decode('ascii'), flush=True)
    if check and exit_status != 0:
        raise RuntimeError(f"Command failed with exit code {exit_status}: {cmd}\n{err}")
    return exit_status, out, err

def main():
    log(f"Connecting to {SERVER_IP}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=10)
    log("Connected.")
    
    try:
        # 1. Seeding Database
        log("--- [STEP 1]: Seeding MySQL Database with Demo Data ---")
        run_ssh_cmd(client, f"mkdir -p {REMOTE_DIR}/uploads/proofs {REMOTE_DIR}/uploads/docs {REMOTE_DIR}/uploads/gallery {REMOTE_DIR}/uploads/posts")
        env_vars = f'DATABASE_URL="mysql+pymysql://{DB_USER}:{DB_PASS}@localhost/{DB_NAME}?charset=utf8mb4"'
        run_ssh_cmd(client, f"cd {REMOTE_DIR} && {env_vars} {REMOTE_DIR}/venv/bin/python seed.py")
        log("Database seed completed successfully.")

        # 2. Setup Systemd Service on Port 8082
        log(f"--- [STEP 2]: Configuring systemd service on port {PORT} ---")
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
        time.sleep(3)
        run_ssh_cmd(client, "systemctl status gimbal.service --no-pager")

        # 3. Verification & Health Check
        log(f"--- [STEP 3]: Health check on port {PORT} ---")
        run_ssh_cmd(client, f"curl -s -o /dev/null -w 'HTTP Status [GET /]: %{{http_code}}\\n' http://127.0.0.1:{PORT}/")
        run_ssh_cmd(client, f"curl -s -o /dev/null -w 'HTTP Status [GET /login]: %{{http_code}}\\n' http://127.0.0.1:{PORT}/login")
        run_ssh_cmd(client, f"curl -s -o /dev/null -w 'HTTP Status [GET /verify-kta/R-01-26]: %{{http_code}}\\n' http://127.0.0.1:{PORT}/verify-kta/R-01-26")
        
        log("=======================================================")
        log(f"DEPLOYMENT SUCCEEDED! Service running on http://{SERVER_IP}:{PORT}")
        log("=======================================================")

    finally:
        client.close()

if __name__ == '__main__':
    main()
