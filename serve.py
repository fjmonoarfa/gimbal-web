from flask import Flask, send_from_directory, render_template_string, request
import os
import csv
from datetime import datetime

# Path to your static folder (contains index.html and assets)
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), '.')
LOG_FILE = os.path.join(STATIC_FOLDER, 'connections.csv')

app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='')

# ------------------------------------------------------------------
# INIT CSV FILE (write header if not exists)
# ------------------------------------------------------------------
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp',
            'remote_addr',
            'method',
            'path',
            'user_agent'
        ])

# ------------------------------------------------------------------
# LOG EVERY CONNECTION
# ------------------------------------------------------------------
@app.before_request
def log_connection():
    try:
        with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(timespec='seconds'),
                request.headers.get('X-Forwarded-For', request.remote_addr),
                request.method,
                request.path,
                request.headers.get('User-Agent')
            ])
    except Exception as e:
        # Jangan sampai logging bikin app crash
        print("Logging error:", e)

# ------------------------------------------------------------------
# ROUTES
# ------------------------------------------------------------------
@app.route('/')
def serve_index():
    index_path = os.path.join(STATIC_FOLDER, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(STATIC_FOLDER, 'index.html')
    else:
        return render_template_string("<h1>index.html not found.</h1>"), 404

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

# ------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8083, debug=True)
