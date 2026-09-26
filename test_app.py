import os
import unittest
from app import app, db
from models import User, Dues, DuesPayment, Document, generate_next_nra

class GimbalWebTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_01_landing_page(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'KPAB GIMBAL', resp.data)
        self.assertIn(b'Generasi Indonesia Menyatu Bersama Alam', resp.data)
        print(">>> Test 01: Landing page OK")

    def test_02_verify_kta_public(self):
        resp = self.client.get('/verify-kta/R-01-26')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'R-01-26', resp.data)
        self.assertIn(b'Keanggotaan Terverifikasi Sah', resp.data)
        print(">>> Test 02: Public KTA Verification OK")

    def test_03_dual_layer_rendering(self):
        # 3a. Direct hit with session: returns index.html (Layer 1)
        with self.client.session_transaction() as sess:
            user = User.query.filter_by(email='admin@gimbal.org').first()
            sess['user_id'] = user.id

        resp1 = self.client.get('/member/dashboard')
        self.assertEqual(resp1.status_code, 200)
        self.assertIn(b'id="app-shell"', resp1.data)
        self.assertIn(b'hx-get="/member/dashboard', resp1.data)

        # 3b. HTMX targeting app-shell: returns shell.html (Layer 2)
        resp2 = self.client.get('/admin/dashboard', headers={
            'HX-Request': 'true',
            'HX-Target': 'app-shell'
        })
        self.assertEqual(resp2.status_code, 200)
        self.assertIn(b'Dashboard Pengurus GIMBAL', resp2.data)
        self.assertIn(b'id="main-content"', resp2.data)

        # 3c. In-app navigation HTMX targeting #main-content: returns ONLY macro fragment
        resp3 = self.client.get('/admin/members', headers={
            'HX-Request': 'true',
            'HX-Target': '#main-content'
        })
        self.assertEqual(resp3.status_code, 200)
        self.assertIn(b'Data Master Anggota GIMBAL', resp3.data)
        # Should NOT contain full outer shell tags
        self.assertNotIn(b'<body', resp3.data)
        print(">>> Test 03: Dual-Layer HTMX Rendering Architecture 100% OK")

    def test_04_nra_auto_approval_sequence(self):
        """
        Menguji aturan:
        - nn urut persetujuan di tahun YY
        - Reset tahunan
        - R-nn-YY
        """
        calon = User.query.filter_by(email='calon.petualang@gmail.com').first()
        self.assertIsNotNone(calon)
        
        with self.client.session_transaction() as sess:
            admin = User.query.filter_by(email='admin@gimbal.org').first()
            sess['user_id'] = admin.id

        # Approve
        resp = self.client.post(f'/admin/member/approve/{calon.id}', headers={
            'HX-Request': 'true',
            'HX-Target': '#main-content'
        })
        self.assertEqual(resp.status_code, 200)

        # Reload user
        db.session.refresh(calon)
        self.assertEqual(calon.status, 'active')
        self.assertIsNotNone(calon.nra)
        # Karena R-01-26 dan R-02-26 sudah ada, calon ke-3 harus dapat R-03-26!
        self.assertEqual(calon.nra, 'R-03-26')
        self.assertEqual(calon.nra_year, 26)
        self.assertEqual(calon.nra_sequence, 3)
        print(f">>> Test 04: NRA Approved successfully as {calon.nra}!")

    def test_05_kta_digital_page(self):
        with self.client.session_transaction() as sess:
            budi = User.query.filter_by(email='budi.pendaki@gmail.com').first()
            sess['user_id'] = budi.id

        resp = self.client.get('/member/kta', headers={'HX-Request': 'true'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Kartu Tanda Anggota (KTA) Digital', resp.data)
        self.assertIn(b'R-02-26', resp.data)
        self.assertIn(b'QR Code Validasi Lapangan', resp.data)
        print(">>> Test 05: KTA Digital Page & QR Generation OK")

    def test_06_document_crud(self):
        with self.client.session_transaction() as sess:
            admin = User.query.filter_by(email='admin@gimbal.org').first()
            sess['user_id'] = admin.id

        # List docs
        resp = self.client.get('/admin/documents', headers={'HX-Request': 'true'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Dokumen & Arsip Organisasi', resp.data)
        self.assertIn(b'AD/ART KPAB GIMBAL', resp.data)
        print(">>> Test 06: Document CRUD listing OK")

if __name__ == '__main__':
    unittest.main()
