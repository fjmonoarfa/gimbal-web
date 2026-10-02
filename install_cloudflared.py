import paramiko
import time
import os

OLD_IP = '10.75.0.51'
OLD_USER = 'root'
OLD_PASS = 'P4ssw0rd!'

NEW_IP = '10.75.0.16'
NEW_USER = 'root'
NEW_PASS = 'R4h4514!?!'

def run_ssh(client, cmd, ignore_error=False):
    print(f"[{client._host}] Running: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        for line in out.splitlines():
            print(f"  {line.encode('ascii', errors='replace').decode('ascii')}")
    if err and not ignore_error:
        for line in err.splitlines():
            print(f"  ERR: {line.encode('ascii', errors='replace').decode('ascii')}")
    if exit_status != 0 and not ignore_error:
        raise Exception(f"Command failed ({exit_status}): {cmd}")
    return out

def main():
    print("=== 1. Mengambil token Cloudflare dari Server Lama (10.75.0.51) ===")
    old_ssh = paramiko.SSHClient()
    old_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    old_ssh.connect(OLD_IP, username=OLD_USER, password=OLD_PASS, timeout=10)
    old_ssh._host = OLD_IP
    
    token = run_ssh(old_ssh, 'cat /etc/cloudflared/token').strip()
    print(f"Token didapatkan (panjang: {len(token)})")

    print("\n=== 2. Menghubungkan ke Server Baru (10.75.0.16) ===")
    new_ssh = paramiko.SSHClient()
    new_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    new_ssh.connect(NEW_IP, username=NEW_USER, password=NEW_PASS, timeout=10)
    new_ssh._host = NEW_IP

    print("\n=== 3. Mengunduh dan Memasang cloudflared binary (amd64) ===")
    # Unduh cloudflared deb atau binary
    run_ssh(new_ssh, 'curl -fsSL -o /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb')
    run_ssh(new_ssh, 'dpkg -i /tmp/cloudflared.deb || apt-get install -f -y')
    
    cf_path = run_ssh(new_ssh, 'which cloudflared').strip()
    print(f"cloudflared terpasang di: {cf_path}")
    run_ssh(new_ssh, f'{cf_path} --version')

    # Buat symlink di /usr/local/bin/cloudflared jika terpasang di /usr/bin/cloudflared
    if cf_path != '/usr/local/bin/cloudflared':
        run_ssh(new_ssh, f'ln -sf {cf_path} /usr/local/bin/cloudflared')

    print("\n=== 4. Menyiapkan Direktori & Token Cloudflare ===")
    run_ssh(new_ssh, 'mkdir -p /etc/cloudflared && chmod 700 /etc/cloudflared')
    
    # Tulis token
    sftp = new_ssh.open_sftp()
    with sftp.open('/etc/cloudflared/token', 'w') as f:
        f.write(token + '\n')
    sftp.chmod('/etc/cloudflared/token', 0o600)
    sftp.close()
    print("Token disimpan di /etc/cloudflared/token dengan hak akses 0600")

    print("\n=== 5. Membuat & Mengaktifkan Systemd Service cloudflared ===")
    service_content = """[Unit]
Description=Cloudflare Tunnel client
After=network-online.target
Wants=network-online.target

[Service]
TimeoutStartSec=15
Type=notify
ExecStart=/usr/local/bin/cloudflared --no-autoupdate tunnel run --token-file /etc/cloudflared/token
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
"""
    sftp = new_ssh.open_sftp()
    with sftp.open('/etc/systemd/system/cloudflared.service', 'w') as f:
        f.write(service_content)
    sftp.close()

    run_ssh(new_ssh, 'systemctl daemon-reload')
    run_ssh(new_ssh, 'systemctl enable --now cloudflared')
    
    time.sleep(3)
    print("\n=== 6. Status Service cloudflared di Server Baru (10.75.0.16) ===")
    run_ssh(new_ssh, 'systemctl status cloudflared --no-pager', ignore_error=True)
    run_ssh(new_ssh, 'journalctl -u cloudflared -n 15 --no-pager', ignore_error=True)

    print("\n=== 7. Menghentikan cloudflared di Server Lama (10.75.0.51) agar trafik beralih penuh ===")
    run_ssh(old_ssh, 'systemctl stop cloudflared', ignore_error=True)
    run_ssh(old_ssh, 'systemctl disable cloudflared', ignore_error=True)
    print("cloudflared di server lama (10.75.0.51) telah dihentikan dan didisable.")

    old_ssh.close()
    new_ssh.close()
    print("\n[SUCCESS] Instalasi dan migrasi Cloudflare Tunnel ke 10.75.0.16 selesai!")

if __name__ == '__main__':
    main()
