import paramiko
import time

SERVER_IP = '10.75.0.51'
USERNAME = 'root'
PASSWORD = 'P4ssw0rd!'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SERVER_IP, username=USERNAME, password=PASSWORD, timeout=10)

migration_py = """
import os
import sys
sys.path.insert(0, '/root/gimbal-web')
os.chdir('/root/gimbal-web')

from app import app, db
from sqlalchemy import text

with app.app_context():
    cols = [
        ('subscription_channel', "VARCHAR(50) DEFAULT 'manual'"),
        ('subscription_expiry', 'DATETIME NULL'),
        ('google_order_id', 'VARCHAR(100) NULL'),
        ('google_purchase_token', 'VARCHAR(256) NULL'),
        ('google_product_id', 'VARCHAR(100) NULL')
    ]
    for col_name, col_type in cols:
        try:
            db.session.execute(text(f'ALTER TABLE users ADD COLUMN {col_name} {col_type}'))
            db.session.commit()
            print(f'Added column {col_name}')
        except Exception as e:
            db.session.rollback()
            print(f'Column {col_name}: {e}')
"""

sftp = client.open_sftp()
with sftp.file('/root/gimbal-web/run_migration.py', 'w') as f:
    f.write(migration_py)
sftp.close()

stdin, stdout, stderr = client.exec_command('/root/gimbal-web/venv/bin/python3 /root/gimbal-web/run_migration.py')
print("Migration stdout:")
print(stdout.read().decode('utf-8'))
print("Migration stderr:")
print(stderr.read().decode('utf-8'))

print("Restarting gimbal.service...")
client.exec_command('systemctl restart gimbal.service')
time.sleep(2)

stdin, stdout, stderr = client.exec_command('curl -s -o /dev/null -w "HTTP Status: %{http_code}" http://127.0.0.1:8082/')
print("Health check:", stdout.read().decode('utf-8'))

client.close()
