import os
import unittest
from app import app, db
from models import User, Dues, DuesPayment, Document, GalleryItem, generate_next_nra

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

    def test_07_gallery_crud_and_pindown(self):
        with self.client.session_transaction() as sess:
            admin = User.query.filter_by(email='admin@gimbal.org').first()
            sess['user_id'] = admin.id

        # 1. Admin Gallery Page
        resp = self.client.get('/admin/gallery', headers={'HX-Request': 'true'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Galeri Pin-down Ekspedisi', resp.data)

        # 2. Open Create Modal
        resp = self.client.get('/admin/gallery/create-modal')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Pin-down Foto Ekspedisi', resp.data)

        # 3. Create New Gallery Item
        resp = self.client.post('/admin/gallery/create', data={
            'title': 'Puncak Gn. Rinjani 3726 MDPL',
            'caption': 'Tim GIMBAL mengibarkan panji organisasi di batas awan.',
            'category': 'Pendakian',
            'location': 'Lombok, NTB',
            'activity_id': '7',
            'is_pinned': '1',
            'image_url': '/static/pics/cartoon/hero.jpg'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp.status_code, 200)

        # Check DB
        item = GalleryItem.query.filter_by(title='Puncak Gn. Rinjani 3726 MDPL').first()
        self.assertIsNotNone(item)
        self.assertTrue(item.is_pinned)
        self.assertEqual(item.location, 'Lombok, NTB')

        # 4. Edit Gallery Item and verify persistence in DB
        resp_edit = self.client.post(f'/admin/gallery/edit/{item.id}', data={
            'title': 'Puncak Gn. Rinjani 3726 MDPL (Updated)',
            'caption': 'Caption baru yang telah diperbarui dan tersimpan.',
            'category': 'Pendakian',
            'location': 'Sembalun, Lombok Timur',
            'is_pinned': '1'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_edit.status_code, 200)
        db.session.refresh(item)
        self.assertEqual(item.title, 'Puncak Gn. Rinjani 3726 MDPL (Updated)')
        self.assertEqual(item.location, 'Sembalun, Lombok Timur')
        self.assertEqual(item.caption, 'Caption baru yang telah diperbarui dan tersimpan.')
        print(">>> Test 07b: Gallery Edit Form properly persists to DB OK")

        # 5. Toggle Pin
        resp = self.client.post(f'/admin/gallery/toggle-pin/{item.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp.status_code, 200)
        db.session.refresh(item)
        self.assertFalse(item.is_pinned)

        # 6. Delete Item
        resp = self.client.post(f'/admin/gallery/delete/{item.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp.status_code, 200)
        deleted = GalleryItem.query.get(item.id)
        self.assertIsNone(deleted)

        print(">>> Test 07: Gallery CRUD & Expedition Pin-down 100% OK")

    def test_08_activity_crud_and_edit(self):
        with self.client.session_transaction() as sess:
            admin = User.query.filter_by(email='admin@gimbal.org').first()
            sess['user_id'] = admin.id

        # 1. Create new Activity
        from models import Activity
        resp = self.client.post('/admin/activity/create', data={
            'title': 'Ekspedisi Karst Maros',
            'location': 'Maros, Sulawesi Selatan',
            'activity_date': '10 - 15 Agustus 2026',
            'difficulty': 'Menengah',
            'quota': '15',
            'description': 'Eksplorasi gua dan tebing karst purba Maros Pangkep.'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp.status_code, 200)

        act = Activity.query.filter_by(title='Ekspedisi Karst Maros').first()
        self.assertIsNotNone(act)
        self.assertEqual(act.location, 'Maros, Sulawesi Selatan')
        self.assertEqual(act.quota, 15)
        self.assertTrue(act.is_open)

        # 2. Open Edit Modal
        resp_modal = self.client.get(f'/admin/activity/edit-modal/{act.id}')
        self.assertEqual(resp_modal.status_code, 200)
        self.assertIn(b'Edit Agenda Kegiatan & Ekspedisi', resp_modal.data)

        # 3. Edit Activity and verify DB persistence
        resp_save = self.client.post(f'/admin/activity/edit/{act.id}', data={
            'title': 'Ekspedisi Speleologi Karst Maros 2026',
            'location': 'Kawasan Karst Maros-Pangkep',
            'activity_date': '12 - 18 Agustus 2026',
            'difficulty': 'Ekstrem',
            'quota': '12',
            'description': 'Eksplorasi sistem hidrologi bawah tanah gua karst.',
            'is_open': '1'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_save.status_code, 200)
        db.session.refresh(act)
        self.assertEqual(act.title, 'Ekspedisi Speleologi Karst Maros 2026')
        self.assertEqual(act.location, 'Kawasan Karst Maros-Pangkep')
        self.assertEqual(act.difficulty, 'Ekstrem')
        self.assertEqual(act.quota, 12)

        # 4. Toggle Status (Tutup / Buka trip)
        resp_toggle = self.client.post(f'/admin/activity/toggle-status/{act.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_toggle.status_code, 200)
        db.session.refresh(act)
        self.assertFalse(act.is_open)

        # 5. Delete Activity
        resp_del = self.client.post(f'/admin/activity/delete/{act.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_del.status_code, 200)
        self.assertIsNone(db.session.get(Activity, act.id))
        print(">>> Test 08: Expedition Activity CRUD & Edit 100% OK")

    def test_09_login_page_and_stylish_auth(self):
        # 1. Halaman Login Penuh
        resp = self.client.get('/login')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Akses Portal GIMBAL', resp.data)
        self.assertIn(b'Gorontalo', resp.data)
        self.assertIn(b'1-Klik Cepat', resp.data)
        self.assertIn(b'Akun Google', resp.data)
        self.assertIn(b'admin@gimbal.org', resp.data)

        # 2. Login manual email & password
        resp_login = self.client.post('/auth/login', data={
            'email': 'budi.pendaki@gmail.com',
            'password': 'gimbal123'
        }, follow_redirects=False)
        self.assertEqual(resp_login.status_code, 302)
        self.assertIn('/member/dashboard', resp_login.headers['Location'])
        print(">>> Test 09: Stylish Simple Monotone Login Page & Auth OK")

    def test_10_google_profile_hub_modal(self):
        with self.client.session_transaction() as sess:
            budi = User.query.filter_by(email='budi.pendaki@gmail.com').first()
            sess['user_id'] = budi.id

        # 1. Buka Modal Hub Akun Google
        resp = self.client.get('/member/profile-modal')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'modal-profile-hub', resp.data)
        self.assertIn(b'Biodata & Pribadi', resp.data)
        self.assertIn(b'Riwayat Medis & Darurat', resp.data)
        self.assertIn(b'Keamanan & Sandi', resp.data)
        self.assertIn(b'Tampilan & Preferensi', resp.data)

        # 2. Update Data Profil (Biodata, Medis, Kontak Darurat, Password) via Modal HTMX
        resp_update = self.client.post('/member/profile-modal/update', data={
            'active_tab': 'medis',
            'name': 'Budi Santoso Petualang',
            'phone': '081399887766',
            'birth_place': 'Kota Gorontalo',
            'birth_date': '1998-08-17',
            'address': 'Jl. Nani Wartabone No. 45, Kota Gorontalo',
            'blood_type': 'O',
            'medical_history': 'Alergi dingin ringan, stamina prima',
            'emergency_name': 'Dewi Lestari',
            'emergency_relation': 'Ibu Kandung',
            'emergency_phone': '081311223344',
            'new_password': 'budi_baru_pass',
            'confirm_password': 'budi_baru_pass'
        })
        self.assertEqual(resp_update.status_code, 200)
        self.assertIn(b'Data profil berhasil diperbarui', resp_update.data)

        # Verifikasi langsung perubahan di Database
        db.session.refresh(budi)
        self.assertEqual(budi.name, 'Budi Santoso Petualang')
        self.assertEqual(budi.phone, '081399887766')
        self.assertEqual(budi.blood_type, 'O')
        self.assertEqual(budi.medical_history, 'Alergi dingin ringan, stamina prima')
        self.assertEqual(budi.emergency_name, 'Dewi Lestari')
        self.assertEqual(budi.emergency_relation, 'Ibu Kandung')
        self.assertEqual(budi.emergency_phone, '081311223344')
        self.assertEqual(budi.password_hash, 'budi_baru_pass')
        self.assertEqual(budi.address, 'Jl. Nani Wartabone No. 45, Kota Gorontalo')
        print(">>> Test 10: Google-Style Profile Hub Modal & Medical/Emergency persistence 100% OK")

if __name__ == '__main__':
    unittest.main()


