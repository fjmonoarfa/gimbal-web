import os
import io
import unittest
from app import app, db
from models import (
    User, Dues, DuesPayment, Document, GalleryItem, Activity,
    Post, PostComment, PostLike, ChatMessage, MapRepository, generate_next_nra,
    SystemSetting, Position, PostMedia,
    AcademyTier, AcademyCourse, AcademyLesson, AcademyQuiz,
    UserLessonProgress, UserQuizAttempt, UserCertification
)

class GimbalWebTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_01_landing_page(self):
        # 1. Direct browser hit: returns Layer 1 (index.html) -> View Source shows ONLY index.html
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'id="app-shell"', resp.data)
        self.assertIn(b'hx-get="/"', resp.data)
        self.assertNotIn(b'id="landing-layer"', resp.data)
        self.assertIn(b'KPAB GIMBAL', resp.data)
        self.assertIn(b'Generasi Indonesia Menyatu Bersama Alam', resp.data)

        # 2. HTMX Load Trigger: returns Layer 2 (landing.html)
        resp_htmx = self.client.get('/', headers={'HX-Request': 'true'})
        self.assertEqual(resp_htmx.status_code, 200)
        self.assertIn(b'id="landing-layer"', resp_htmx.data)
        self.assertNotIn(b'<!DOCTYPE', resp_htmx.data)
        self.assertIn(b'hero-overlay', resp_htmx.data)
        print(">>> Test 01: Landing page Dual-Layer HTMX (Layer 1 Shell & Layer 2 Content) OK")

    def test_02_verify_kta_public(self):
        # 1. Direct browser hit: View Source shows ONLY index.html
        resp = self.client.get('/verify-kta/R-01-26')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'id="app-shell"', resp.data)
        self.assertIn(b'hx-get="/verify-kta/R-01-26"', resp.data)

        # 2. HTMX load trigger: returns verified KTA content from modals.html
        resp_htmx = self.client.get('/verify-kta/R-01-26', headers={'HX-Request': 'true'})
        self.assertEqual(resp_htmx.status_code, 200)
        self.assertIn(b'R-01-26', resp_htmx.data)
        self.assertIn(b'Keanggotaan Terverifikasi Sah', resp_htmx.data)
        print(">>> Test 02: Public KTA Verification Multi-Layer OK")

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

        # 1. List docs
        resp = self.client.get('/admin/documents', headers={'HX-Request': 'true'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Dokumen & Arsip Organisasi', resp.data)
        self.assertIn(b'AD/ART KPAB GIMBAL', resp.data)

        # 2. Test Create Document with dynamic file extension (.docx)
        doc_payload = io.BytesIO(b"Dummy DOCX content for testing")
        resp_create = self.client.post('/admin/documents/create', data={
            'title': 'SOP Pendakian Tebing 2026',
            'category': 'sop',
            'description': 'Standar operasional panjat tebing',
            'is_public_to_members': '1',
            'doc_file': (doc_payload, 'sop_tebing.docx')
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_create.status_code, 200)

        created_doc = Document.query.filter_by(title='SOP Pendakian Tebing 2026').first()
        self.assertIsNotNone(created_doc)
        self.assertEqual(created_doc.file_type, 'docx')
        self.assertTrue(created_doc.file_path.endswith('.docx'))

        # 3. Test Edit Document Modal
        resp_edit_modal = self.client.get(f'/admin/documents/edit-modal/{created_doc.id}')
        self.assertEqual(resp_edit_modal.status_code, 200)
        self.assertIn(b'Edit Dokumen Organisasi', resp_edit_modal.data)
        self.assertIn(b'SOP Pendakian Tebing 2026', resp_edit_modal.data)

        # 4. Test Edit Document Submission with new file (.xlsx)
        new_file_payload = io.BytesIO(b"Dummy XLSX content")
        resp_edit = self.client.post(f'/admin/documents/edit/{created_doc.id}', data={
            'title': 'SOP Pendakian Tebing Revisi Final',
            'category': 'materi',
            'description': 'Revisi modul peralatan dan SOP',
            'is_public_to_members': '1',
            'doc_file': (new_file_payload, 'tabel_peralatan.xlsx')
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_edit.status_code, 200)

        db.session.refresh(created_doc)
        self.assertEqual(created_doc.title, 'SOP Pendakian Tebing Revisi Final')
        self.assertEqual(created_doc.category, 'materi')
        self.assertEqual(created_doc.file_type, 'xlsx')
        self.assertTrue(created_doc.file_path.endswith('.xlsx'))

        # 5. Test Create .EPUB Document
        epub_payload = io.BytesIO(b"PK\x03\x04Dummy EPUB ebook container content")
        resp_epub = self.client.post('/admin/documents/create', data={
            'title': 'Buku Panduan Survival Edisi EPUB',
            'category': 'materi',
            'description': 'Modul survival rimba dalam format digital ebook EPUB',
            'is_public_to_members': '1',
            'doc_file': (epub_payload, 'buku_survival.epub')
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_epub.status_code, 200)

        epub_doc = Document.query.filter_by(title='Buku Panduan Survival Edisi EPUB').first()
        self.assertIsNotNone(epub_doc)
        self.assertEqual(epub_doc.file_type, 'epub')
        self.assertTrue(epub_doc.file_path.endswith('.epub'))

        # 6. Test Fullscreen Web Reader Endpoint (/documents/read/<id>)
        resp_reader = self.client.get(f'/documents/read/{epub_doc.id}')
        self.assertEqual(resp_reader.status_code, 200)
        self.assertIn(b'Buku Panduan Survival Edisi EPUB', resp_reader.data)
        self.assertIn(b'epubjs', resp_reader.data)
        self.assertIn(b'Pembaca Dokumen GIMBAL', resp_reader.data)

        # 7. Test Member Documents Page contains Baca Dokumen
        resp_mem_docs = self.client.get('/member/documents', headers={'HX-Request': 'true'})
        self.assertEqual(resp_mem_docs.status_code, 200)
        self.assertIn(b'Baca Dokumen', resp_mem_docs.data)
        self.assertIn(b'/documents/read/', resp_mem_docs.data)

        # 8. Test /admin/sponsors Route
        resp_sponsors = self.client.get('/admin/sponsors', headers={'HX-Request': 'true'})
        self.assertEqual(resp_sponsors.status_code, 200)
        self.assertIn(b'Mitra Sponsor', resp_sponsors.data)

        print(">>> Test 06: Document CRUD, .EPUB upload, Web Reader & /admin/sponsors 100% OK")

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
        act = Activity.query.first()
        act_id = str(act.id) if act else ''
        resp = self.client.post('/admin/gallery/create', data={
            'title': 'Puncak Gn. Rinjani 3726 MDPL',
            'caption': 'Tim GIMBAL mengibarkan panji organisasi di batas awan.',
            'category': 'Pendakian',
            'location': 'Lombok, NTB',
            'activity_id': act_id,
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
        # 1. Direct browser hit: View Source shows ONLY index.html
        resp = self.client.get('/login')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'id="app-shell"', resp.data)
        self.assertIn(b'hx-get="/login"', resp.data)

        # 2. HTMX Load Trigger: returns modal/page login content from modals.html
        resp_htmx = self.client.get('/login', headers={'HX-Request': 'true'})
        self.assertEqual(resp_htmx.status_code, 200)
        self.assertIn(b'Portal Akses KPAB GIMBAL', resp_htmx.data)
        self.assertIn(b'Gorontalo', resp_htmx.data)
        self.assertNotIn(b'1-Klik Cepat', resp_htmx.data)
        self.assertIn(b'Akun Google', resp_htmx.data)

        # 3. Login manual dengan superadmin fitra & password P4ssw0rd!?!
        resp_login = self.client.post('/auth/login', data={
            'email': 'fitra',
            'password': 'P4ssw0rd!?!'
        }, follow_redirects=False)
        self.assertEqual(resp_login.status_code, 302)
        self.assertIn('/admin/dashboard', resp_login.headers['Location'])
        print(">>> Test 09: Clean Login Page & Superadmin fitra Auth OK")

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
        self.assertIn(b'Afiliasi & Sesi', resp.data)

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

    def test_11_timeline_feed_and_social_features(self):
        with self.client.session_transaction() as sess:
            budi = User.query.filter_by(email='budi.pendaki@gmail.com').first()
            sess['user_id'] = budi.id

        # 1. Buat postingan cerita baru di Lini Masa
        import time
        unique_mark = f"ekspedisi-{int(time.time()*1000)}"
        resp_post = self.client.post('/member/post/create', data={
            'content': f'Tim regu 1 bersiap susur tebing karst dan snorkeling konservasi di Teluk Tomini {unique_mark}.',
            'location': 'Taman Laut Olele, Bone Bolango',
            'image_url': 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=800&q=80'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_post.status_code, 200)

        # Cek DB
        new_p = Post.query.filter(Post.content.like(f"%{unique_mark}%")).first()
        self.assertIsNotNone(new_p)
        self.assertEqual(new_p.user_id, budi.id)
        self.assertIn('Teluk Tomini', new_p.content)

        # 2. Like postingan
        resp_like = self.client.post(f'/member/post/like/{new_p.id}')
        self.assertEqual(resp_like.status_code, 200)
        self.assertIn(b'1 Salam Lestari', resp_like.data)
        self.assertEqual(new_p.like_count, 1)

        # 3. Tambah komentar
        resp_comm = self.client.post(f'/member/post/comment/{new_p.id}', data={
            'comment': 'Hati-hati arus bawah air dan bawa buoy penanda ya tim!'
        })
        self.assertEqual(resp_comm.status_code, 200)
        self.assertIn(b'Hati-hati arus bawah air', resp_comm.data)
        self.assertEqual(len(new_p.comments), 1)

        # 4. Hapus postingan oleh pemiliknya sendiri (user itu sendiri)
        resp_del = self.client.post(f'/member/post/delete/{new_p.id}')
        self.assertEqual(resp_del.status_code, 200)
        deleted_post = Post.query.filter_by(id=new_p.id).first()
        self.assertIsNone(deleted_post)
        print(">>> Test 11: Member Timeline Feed (Post, Like, Comment, Delete) 100% OK")

    def test_12_basecamp_chat_and_admin_pin(self):
        # 1. Obrolan Basecamp (Send & List)
        with self.client.session_transaction() as sess:
            budi = User.query.filter_by(email='budi.pendaki@gmail.com').first()
            sess['user_id'] = budi.id

        resp_chat = self.client.post('/member/chat/send', data={
            'message': 'Kamera aksi dan baterai cadangan sudah aman di dry bag!'
        })
        self.assertEqual(resp_chat.status_code, 200)
        self.assertIn(b'dry bag', resp_chat.data)

        # 2. Admin Pin Foto Postingan ke Galeri Utama
        with self.client.session_transaction() as sess:
            admin = User.query.filter_by(email='admin@gimbal.org').first()
            sess['user_id'] = admin.id

        post = Post.query.filter(Post.image_url.isnot(None)).first()
        if not post:
            post = Post(user_id=admin.id, content="Dokumentasi Puncak Tilongkabila", location="Puncak Gn. Tilongkabila", image_url="https://images.unsplash.com/photo-1464822759023-fed622ff2c3b")
            db.session.add(post)
            db.session.commit()
        self.assertIsNotNone(post)

        resp_pin = self.client.post(f'/admin/post/pin-to-gallery/{post.id}')
        self.assertEqual(resp_pin.status_code, 200)
        self.assertIn(b'Terpin di Galeri Web', resp_pin.data)

        # Cek GalleryItem di DB
        gallery_entry = GalleryItem.query.filter_by(image_url=post.image_url).first()
        self.assertIsNotNone(gallery_entry)
        self.assertTrue(gallery_entry.is_pinned)
        print(">>> Test 12: Basecamp Live Chat & Admin Pin-to-Gallery 100% OK")

    def test_13_google_oauth_flow(self):
        from app import login_or_register_google_user, GOOGLE_CLIENT_ID, GOOGLE_REDIRECT_URI

        # 1. Inisiasi /auth/google-login
        resp = self.client.get('/auth/google-login')
        self.assertEqual(resp.status_code, 302)
        redirect_target = resp.headers.get('Location', '')
        self.assertTrue(redirect_target.startswith('https://accounts.google.com/o/oauth2/v2/auth'))
        self.assertIn(GOOGLE_CLIENT_ID, redirect_target)
        self.assertIn('redirect_uri=https%3A%2F%2Fwww.gimbal.my.id', redirect_target)

        # Bersihkan data siti jika sudah ada dari run sebelumnya
        existing_siti = User.query.filter_by(email='siti.pendaki@gmail.com').first()
        if existing_siti:
            DuesPayment.query.filter_by(user_id=existing_siti.id).delete()
            db.session.delete(existing_siti)
            db.session.commit()

        # 2. Registrasi Calon Anggota Baru via Google SSO
        new_google_info = {
            'email': 'siti.pendaki@gmail.com',
            'sub': 'google_sub_99887766',
            'name': 'Siti Nurhaliza Pendaki',
            'picture': 'https://lh3.googleusercontent.com/a/sample_avatar.jpg'
        }
        with app.test_request_context('/'):
            reg_resp = login_or_register_google_user(new_google_info)
            self.assertEqual(reg_resp.status_code, 302)
            # Karena profil wajib belum terisi, harus diarahkan ke /member/complete-profile
            self.assertEqual(reg_resp.location, '/member/complete-profile')

        # Cek DB untuk user baru
        siti = User.query.filter_by(email='siti.pendaki@gmail.com').first()
        self.assertIsNotNone(siti)
        self.assertEqual(siti.role, 'member')
        self.assertEqual(siti.status, 'pending')
        self.assertFalse(siti.is_profile_complete)

        # 3. Pengisian Formulir Biodata Wajib Keanggotaan
        with self.client.session_transaction() as sess:
            sess['user_id'] = siti.id

        post_profile_resp = self.client.post('/member/complete-profile', data={
            'name': 'Siti Nurhaliza Pendaki',
            'phone': '081234567890',
            'birth_place': 'Gorontalo',
            'birth_date': '2000-05-12',
            'blood_type': 'O',
            'address': 'Jl. Pangeran Hidayat No. 45, Kota Gorontalo',
            'medical_history': 'Tidak ada riwayat alergi',
            'emergency_name': 'Ibu Aminah',
            'emergency_relation': 'Ibu Kandung',
            'emergency_phone': '081398765432'
        })
        self.assertEqual(post_profile_resp.status_code, 302)
        self.assertEqual(post_profile_resp.location, '/member/onboarding-status')

        db.session.refresh(siti)
        self.assertTrue(siti.is_profile_complete)

        # Calon pending dilarang masuk linimasa/dashboard sebelum disetujui admin
        dash_blocked = self.client.get('/member/dashboard')
        self.assertEqual(dash_blocked.status_code, 302)
        self.assertEqual(dash_blocked.location, '/member/onboarding-status')

        # 4. Calon Anggota Melakukan Pembayaran / Unggah Bukti Iuran Keanggotaan
        pay_resp = self.client.post('/member/onboarding/pay', data={
            'dues_id': '1',
            'bank_name': 'Bank BRI',
            'amount_paid': '15000',
            'notes': 'Iuran Pokok Registrasi Siti'
        })
        self.assertEqual(pay_resp.status_code, 302)
        self.assertEqual(pay_resp.location, '/member/onboarding-status')

        db.session.refresh(siti)
        self.assertIsNotNone(siti.latest_dues_payment)
        self.assertEqual(siti.latest_dues_payment.status, 'pending')

        # 5. Admin Memverifikasi Pembayaran & Menyetujui Calon Anggota
        with self.client.session_transaction() as sess:
            admin = User.query.filter_by(email='admin@gimbal.org').first()
            sess['user_id'] = admin.id

        appr_resp = self.client.post(f'/admin/member/approve/{siti.id}', headers={'HX-Request': 'true'})
        self.assertEqual(appr_resp.status_code, 200)

        db.session.refresh(siti)
        self.assertEqual(siti.status, 'active')
        self.assertTrue(siti.is_active_member)
        self.assertTrue(siti.is_dues_paid)

        # 6. Setelah Disetujui & Lunas, Siti Berhak Masuk ke Dashboard & Linimasa Anggota
        with self.client.session_transaction() as sess:
            sess['user_id'] = siti.id

        dash_ok = self.client.get('/member/dashboard', headers={'HX-Request': 'true'})
        self.assertEqual(dash_ok.status_code, 200)
        self.assertIn(b'Siti Nurhaliza Pendaki', dash_ok.data)

        # 7. Login User Existing via Google SSO (langsung ke dashboard)
        existing_google_info = {
            'email': 'budi.pendaki@gmail.com',
            'sub': 'google_sub_budi_12345',
            'name': 'Budi Pendaki Gorontalo',
            'picture': 'https://lh3.googleusercontent.com/a/budi_avatar.jpg'
        }
        with app.test_request_context('/'):
            login_resp = login_or_register_google_user(existing_google_info)
            self.assertEqual(login_resp.status_code, 302)
            self.assertEqual(login_resp.location, '/member/dashboard')

        budi = User.query.filter_by(email='budi.pendaki@gmail.com').first()
        self.assertEqual(budi.google_id, 'google_sub_budi_12345')
        print(">>> Test 13: Google OAuth Mandatory Onboarding, Dues & Admin Approval Flow 100% OK")

    def test_14_superadmin_fitra_and_bypass_disabled(self):
        """Uji akun superadmin fitra dengan kata sandi P4ssw0rd!?! dan nonaktifkan switch-role bypass"""
        # 1. Bypass role switch dinonaktifkan
        resp_switch = self.client.get('/auth/switch-role?email=admin@gimbal.org')
        self.assertEqual(resp_switch.status_code, 302)
        self.assertEqual(resp_switch.location, '/login')

        # 2. Login gagal dengan kata sandi salah
        resp_fail = self.client.post('/auth/login', data={
            'email': 'fitra',
            'password': 'wrong_password'
        })
        self.assertEqual(resp_fail.status_code, 302)
        self.assertIn('error=Kata+sandi+salah', resp_fail.location)

        # 3. Login sukses dengan username 'fitra' dan sandi 'P4ssw0rd!?!'
        resp_ok = self.client.post('/auth/login', data={
            'email': 'fitra',
            'password': 'P4ssw0rd!?!'
        })
        self.assertEqual(resp_ok.status_code, 302)
        self.assertEqual(resp_ok.location, '/admin/dashboard')

        # Cek Superadmin di DB
        fitra = User.query.filter_by(email='fitra@gimbal.org').first()
        self.assertIsNotNone(fitra)
        self.assertEqual(fitra.role, 'superadmin')
        self.assertTrue(fitra.is_superadmin)
        print(">>> Test 14: Superadmin fitra & Bypass Protection 100% OK")

    def test_15_admin_settings_and_crud(self):
        """Uji CRUD Admin Web, CRUD Member, Pengaturan Nominal Iuran & Midtrans"""
        fitra = User.query.filter_by(email='fitra@gimbal.org').first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = fitra.id

        # 1. Buka Admin Settings
        resp_set = self.client.get('/admin/settings', headers={'HX-Request': 'true'})
        self.assertEqual(resp_set.status_code, 200)
        self.assertIn(b'Konfigurasi Gateway Midtrans', resp_set.data)
        self.assertIn(b'Rekening & Organisasi', resp_set.data)

        # 2a. Update Dues: Disable iuran (is_active='0')
        resp_dues_off = self.client.post('/admin/settings/dues', data={
            'dues_title': 'Iuran Bulanan Demo',
            'dues_amount': '15000',
            'due_date': '2026-03-31',
            'description': 'Iuran rutin bulanan Rp 15.000',
            'is_active': '0'
        })
        self.assertEqual(resp_dues_off.status_code, 302)
        db.session.expire_all()
        dues_obj = Dues.query.filter_by(category='wajib').first()
        self.assertFalse(dues_obj.is_active)
        self.assertEqual(SystemSetting.get('dues_enabled'), 'false')

        # 2a-1. Verify member dashboard & onboarding status when dues disabled
        budi = User.query.filter_by(email='budi.pendaki@gmail.com').first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = budi.id
        resp_dash_disabled = self.client.get('/member/dashboard', headers={'HX-Request': 'true'})
        self.assertEqual(resp_dash_disabled.status_code, 200)
        self.assertIn(b'Bebas Iuran Kas', resp_dash_disabled.data)

        # Onboarding status when dues disabled
        cand = User.query.filter_by(email='calon.test.dues@gmail.com').first()
        if not cand:
            cand = User(name='Calon Test Dues', email='calon.test.dues@gmail.com', status='pending', phone='0811111111',
                        birth_place='Gorontalo', birth_date='2000-01-01', blood_type='O', address='Jl. Baru',
                        emergency_name='Darurat', emergency_relation='Kerabat', emergency_phone='0822222222')
            db.session.add(cand)
            db.session.commit()
        with self.client.session_transaction() as sess:
            sess['user_id'] = cand.id
        resp_onb_disabled = self.client.get('/member/onboarding-status', headers={'HX-Request': 'true'})
        self.assertEqual(resp_onb_disabled.status_code, 200)
        self.assertIn(b'Bebas Iuran (Dinonaktifkan)', resp_onb_disabled.data)
        self.assertIn(b'Kewajiban Iuran Keanggotaan Dibebaskan', resp_onb_disabled.data)

        # 2b. Re-login as fitra and re-enable iuran (is_active='1')
        with self.client.session_transaction() as sess:
            sess['user_id'] = fitra.id
        resp_dues_on = self.client.post('/admin/settings/dues', data={
            'dues_title': 'Iuran Bulanan Demo',
            'dues_amount': '20000',
            'due_date': '2026-03-31',
            'description': 'Iuran rutin bulanan Rp 20.000',
            'is_active': '1'
        })
        self.assertEqual(resp_dues_on.status_code, 302)
        db.session.expire_all()
        dues_obj = Dues.query.filter_by(category='wajib').first()
        self.assertTrue(dues_obj.is_active)
        self.assertEqual(dues_obj.amount, 20000.0)

        # 2c. Dues CRUD (Create, Toggle, Edit, Delete)
        resp_create_dues = self.client.post('/admin/dues/create', data={
            'title': 'Iuran Ekspedisi Rinjani',
            'category': 'kegiatan',
            'amount': '85000',
            'due_date': '2026-08-17',
            'description': 'Logistik pendakian massal',
            'is_active': '1'
        }, headers={'Referer': 'http://localhost/admin/settings?tab=dues'})
        self.assertEqual(resp_create_dues.status_code, 200)
        rinjani = Dues.query.filter_by(title='Iuran Ekspedisi Rinjani').first()
        self.assertIsNotNone(rinjani)
        self.assertEqual(rinjani.amount, 85000.0)
        self.assertTrue(rinjani.is_active)

        # Toggle status
        resp_toggle = self.client.post(f'/admin/dues/toggle-active/{rinjani.id}',
                                      headers={'Referer': 'http://localhost/admin/settings?tab=dues'})
        self.assertEqual(resp_toggle.status_code, 200)
        db.session.refresh(rinjani)
        self.assertFalse(rinjani.is_active)

        # Edit dues
        resp_edit_dues = self.client.post(f'/admin/dues/edit/{rinjani.id}', data={
            'title': 'Iuran Ekspedisi Rinjani 2026',
            'category': 'kegiatan',
            'amount': '90000',
            'due_date': '2026-08-20',
            'description': 'Logistik & Simaksi Rinjani',
            'is_active': '1'
        }, headers={'Referer': 'http://localhost/admin/settings?tab=dues'})
        self.assertEqual(resp_edit_dues.status_code, 200)
        db.session.refresh(rinjani)
        self.assertEqual(rinjani.title, 'Iuran Ekspedisi Rinjani 2026')
        self.assertEqual(rinjani.amount, 90000.0)

        # Delete dues
        resp_del_dues = self.client.post(f'/admin/dues/delete/{rinjani.id}',
                                        headers={'Referer': 'http://localhost/admin/settings?tab=dues'})
        self.assertEqual(resp_del_dues.status_code, 200)
        self.assertIsNone(Dues.query.filter_by(title='Iuran Ekspedisi Rinjani 2026').first())

        # 3. Update Midtrans Configuration
        resp_mid = self.client.post('/admin/settings/midtrans', data={
            'midtrans_mode': 'sandbox',
            'midtrans_client_key': 'SB-Mid-client-TESTKEY123',
            'midtrans_server_key': 'SB-Mid-server-TESTKEY123',
            'midtrans_merchant_id': 'TEST-MERCHANT'
        })
        self.assertEqual(resp_mid.status_code, 302)

        # 4. Tambah Admin Baru
        resp_new_admin = self.client.post('/admin/admins/create', data={
            'name': 'Admin Humas Baru',
            'email': 'humas@gimbal.org',
            'role': 'admin',
            'password': 'P4ssw0rdHumas!'
        })
        self.assertEqual(resp_new_admin.status_code, 302)
        humas = User.query.filter_by(email='humas@gimbal.org').first()
        self.assertIsNotNone(humas)
        self.assertEqual(humas.role, 'admin')

        # 5. Proteksi Superadmin fitra tidak boleh dihapus
        resp_del_fitra = self.client.post(f'/admin/admins/delete/{fitra.id}')
        self.assertEqual(resp_del_fitra.status_code, 400)
        db.session.refresh(fitra)
        self.assertEqual(fitra.role, 'superadmin')
        print(">>> Test 15: Admin Settings, Midtrans Config & Admin/Member CRUD 100% OK")

    def test_16_midtrans_payment_flow(self):
        """Uji Integrasi Midtrans Snap & Webhook Notification"""
        user = User.query.filter_by(email='budi.pendaki@gmail.com').first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id

        # 1. Request Snap Token
        snap_resp = self.client.post('/member/payment/midtrans-snap', json={
            'dues_id': '1'
        })
        self.assertEqual(snap_resp.status_code, 200)
        snap_data = snap_resp.get_json()
        self.assertEqual(snap_data['status'], 'success')
        self.assertIn('snap_token', snap_data)
        self.assertIn('order_id', snap_data)

        order_id = snap_data['order_id']

        # 2. Webhook Notification (Settlement / Lunas)
        notif_resp = self.client.post('/payment/midtrans/notification', json={
            'order_id': order_id,
            'transaction_status': 'settlement',
            'fraud_status': 'accept',
            'payment_type': 'qris'
        })
        self.assertEqual(notif_resp.status_code, 200)
        self.assertEqual(notif_resp.get_json()['status'], 'ok')

        # Verifikasi record pembayaran terupdate di DB
        payment = DuesPayment.query.filter_by(order_id=order_id).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, 'approved')
        self.assertEqual(payment.transaction_status, 'settlement')
        print(">>> Test 16: Midtrans Snap & Webhook Notification 100% OK")

    def test_17_maps_api_integration(self):
        """Uji Integrasi API Gimbal Maps: Cek Akses Tiering, Katalog Repo Peta & Download"""
        import io

        # 1. Cek Akses untuk Pengguna Tamu / Belum Terdaftar (Harus Free Tier)
        resp_guest = self.client.post('/api/v1/maps/check-access', json={
            'email': 'tamu.pendaki@gmail.com'
        })
        self.assertEqual(resp_guest.status_code, 200)
        guest_data = resp_guest.get_json()
        self.assertEqual(guest_data['tier'], 'free')
        self.assertEqual(guest_data['limits']['max_maps'], 2)
        self.assertFalse(guest_data['limits']['can_import_vector'])
        self.assertEqual(guest_data['limits']['max_points'], 5)
        self.assertEqual(guest_data['limits']['max_track_distance_km'], 1.0)
        self.assertFalse(guest_data['limits']['can_access_repo'])

        # 2. Cek Akses untuk Anggota Aktif & Lunas Iuran (Harus member_active Tier)
        budi = User.query.filter_by(email='budi.pendaki@gmail.com').first()
        self.assertIsNotNone(budi)
        resp_member = self.client.post('/api/v1/maps/check-access', json={
            'email': budi.email
        })
        self.assertEqual(resp_member.status_code, 200)
        member_data = resp_member.get_json()
        self.assertEqual(member_data['tier'], 'member_active')
        self.assertEqual(member_data['limits']['max_maps'], -1)
        self.assertTrue(member_data['limits']['can_import_vector'])
        self.assertEqual(member_data['limits']['max_points'], -1)
        self.assertEqual(member_data['limits']['max_track_distance_km'], -1)
        self.assertTrue(member_data['limits']['can_access_repo'])
        self.assertEqual(member_data['user']['nra'], budi.nra)

        # 3. Buat Data Dummy Repo Peta
        maps_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'maps')
        os.makedirs(maps_dir, exist_ok=True)
        sample_gpx_path = os.path.join(maps_dir, 'tilongkabila_trail.gpx')
        with open(sample_gpx_path, 'w', encoding='utf-8') as f:
            f.write("<?xml version='1.0'?><gpx version='1.1'><trk><name>Jalur Tilongkabila</name></trk></gpx>")

        repo_item = MapRepository(
            title="Peta Jalur Pendakian Gn. Tilongkabila",
            region="Gorontalo",
            category="jalur_pendakian",
            file_type="gpx",
            file_path="/uploads/maps/tilongkabila_trail.gpx",
            file_size_fmt="12.5 KB",
            description="Jalur resmi via Pos 1 Desa Daenaa sampai Puncak Tilongkabila",
            total_waypoints=14,
            total_distance_km=18.4,
            uploaded_by=budi.id
        )
        db.session.add(repo_item)
        db.session.commit()

        # 4. Ambil Katalog Repo Peta (/api/v1/maps/repo)
        resp_repo = self.client.get('/api/v1/maps/repo')
        self.assertEqual(resp_repo.status_code, 200)
        repo_data = resp_repo.get_json()
        self.assertEqual(repo_data['status'], 'success')
        self.assertGreaterEqual(repo_data['total_count'], 1)
        matched = [m for m in repo_data['maps'] if m['id'] == repo_item.id]
        self.assertTrue(len(matched) > 0)
        self.assertEqual(matched[0]['title'], "Peta Jalur Pendakian Gn. Tilongkabila")

        # 5. Download Berkas Peta (/api/v1/maps/repo/download/<id>)
        resp_dl = self.client.get(f"/api/v1/maps/repo/download/{repo_item.id}")
        self.assertEqual(resp_dl.status_code, 200)
        self.assertIn(b'Jalur Tilongkabila', resp_dl.data)
        db.session.refresh(repo_item)
        self.assertGreaterEqual(repo_item.downloads_count, 1)

        # 6. Share Track Lintasan dari Gimbal Maps ke Web (/api/v1/maps/share-track)
        gpx_payload = io.BytesIO(b"<?xml version='1.0'?><gpx><trk><name>Survey Danau Limboto</name></trk></gpx>")
        resp_share = self.client.post('/api/v1/maps/share-track', data={
            'email': budi.email,
            'title': 'Rute Kayak Danau Limboto',
            'location': 'Danau Limboto, Gorontalo',
            'distance_km': '7.2',
            'gpx_file': (gpx_payload, 'limboto_kayak.gpx')
        })
        self.assertEqual(resp_share.status_code, 200)
        share_json = resp_share.get_json()
        self.assertEqual(share_json['status'], 'success')

        # Verifikasi masuk ke linimasa dan repo
        new_repo = db.session.get(MapRepository, share_json['repo_id'])
        self.assertIsNotNone(new_repo)
        self.assertEqual(new_repo.title, 'Rute Kayak Danau Limboto')

        new_post = Post.query.filter(Post.content.like('%Rute Kayak Danau Limboto%')).first()
        self.assertIsNotNone(new_post)

        # 7. Uji Edit Repo Peta oleh Admin (/admin/repo-maps/edit-modal/<id> & /admin/repo-maps/edit/<id>)
        admin = User.query.filter_by(email='admin@gimbal.org').first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id

        resp_map_edit_modal = self.client.get(f'/admin/repo-maps/edit-modal/{new_repo.id}')
        self.assertEqual(resp_map_edit_modal.status_code, 200)
        self.assertIn(b'Edit Peta & Geodata Ekspedisi', resp_map_edit_modal.data)
        self.assertIn(b'Rute Kayak Danau Limboto', resp_map_edit_modal.data)

        # Submit edit dengan file format baru (.kml)
        kml_payload = io.BytesIO(b"<?xml version='1.0'?><kml><Placemark><name>Rute KML</name></Placemark></kml>")
        resp_map_edit = self.client.post(f'/admin/repo-maps/edit/{new_repo.id}', data={
            'title': 'Rute Kayak Danau Limboto - Jalur Timur',
            'region': 'Kab. Gorontalo',
            'category': 'water_source',
            'total_distance_km': '8.5',
            'total_waypoints': '12',
            'description': 'Jalur survei dermaga timur Danau Limboto',
            'is_exclusive_member': '1',
            'map_file': (kml_payload, 'limboto_timur.kml')
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_map_edit.status_code, 200)

        db.session.refresh(new_repo)
        self.assertEqual(new_repo.title, 'Rute Kayak Danau Limboto - Jalur Timur')
        self.assertEqual(new_repo.region, 'Kab. Gorontalo')
        self.assertEqual(new_repo.file_type, 'kml')
        self.assertTrue(new_repo.file_path.endswith('.kml'))
        self.assertEqual(new_repo.total_distance_km, 8.5)

        print(">>> Test 17: Gimbal Maps API (Access Check, Repo Catalog, Download, Track Share & Admin Edit) 100% OK")

    def test_18_member_deletion_and_superadmin_settings(self):
        """
        Pengujian Fungsionalitas:
        1. Flash message saat hapus user (proteksi superadmin & diri sendiri).
        2. CRUD anggota dengan hak akses peran / role (superadmin, admin, member).
        3. Simpan pengaturan rekening kas dan profil organisasi.
        4. Simpan pengaturan warna tema sistem dan lebar halaman.
        """
        admin = User.query.filter_by(role='superadmin').first() or User.query.filter_by(role='admin').first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id

        # Bersihkan data user uji jika sudah ada dari run sebelumnya
        existing_test_user = User.query.filter_by(email='test_role_user@gimbal.org').first()
        if existing_test_user:
            db.session.delete(existing_test_user)
            db.session.commit()

        # 1. Buat anggota uji coba dengan role 'admin'
        resp_create = self.client.post('/admin/member/create', data={
            'name': 'Test Role User',
            'email': 'test_role_user@gimbal.org',
            'phone': '089988776655',
            'status': 'active',
            'role': 'admin',
            'password': 'password123'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_create.status_code, 200)

        created_user = User.query.filter_by(email='test_role_user@gimbal.org').first()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.role, 'admin')

        # 2. Edit anggota menjadi 'superadmin'
        resp_edit = self.client.post(f'/admin/member/edit/{created_user.id}', data={
            'name': 'Test Superadmin User',
            'email': 'test_role_user@gimbal.org',
            'phone': '089988776655',
            'status': 'active',
            'role': 'superadmin'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_edit.status_code, 200)

        db.session.refresh(created_user)
        self.assertEqual(created_user.role, 'superadmin')

        # 3. Coba hapus superadmin: harus dicegah dengan flash error
        resp_del_super = self.client.post(f'/admin/member/delete/{created_user.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_del_super.status_code, 200)
        self.assertIn(b'Superadmin dilindungi', resp_del_super.data)
        
        # 4. Coba hapus akun diri sendiri: harus dicegah dengan flash error
        resp_del_self = self.client.post(f'/admin/member/delete/{admin.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_del_self.status_code, 200)
        self.assertIn(b'menghapus akun Anda sendiri', resp_del_self.data)

        # 5. Turunkan role created_user menjadi member biasa, lalu hapus: harus sukses
        created_user.role = 'member'
        db.session.commit()

        resp_del_ok = self.client.post(f'/admin/member/delete/{created_user.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_del_ok.status_code, 200)
        self.assertIn(b'berhasil dihapus', resp_del_ok.data)
        self.assertIsNone(User.query.filter_by(email='test_role_user@gimbal.org').first())

        # 6. Simpan Pengaturan Rekening & Profil Organisasi
        resp_org = self.client.post('/admin/settings/organization', data={
            'bank_primary_name': 'Bank Mandiri Kas Pusat',
            'bank_primary_number': '131-00-9999-8888',
            'bank_primary_holder': 'BENDAHARA KPAB GIMBAL',
            'bank_secondary_name': 'Bank BCA',
            'bank_secondary_number': '593-019-9999',
            'bank_secondary_holder': 'BENDAHARA KPAB GIMBAL',
            'org_name': 'KPAB GIMBAL PUSAT',
            'org_phone': '+62 811-2233-4455',
            'org_email': 'info@gimbal.org',
            'org_address': 'Jl. Danau Limboto No. 10 Gorontalo'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_org.status_code, 200)
        self.assertIn(b'Pengaturan rekening kas dan identitas organisasi berhasil disimpan', resp_org.data)

        # 7. Simpan Pengaturan Tema Warna & Lebar Konten
        resp_theme = self.client.post('/admin/settings/theme', data={
            'theme_color': 'emerald',
            'site_width': '90%'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_theme.status_code, 200)
        self.assertIn(b'Pengaturan skema warna tema dan tampilan berhasil diperbarui', resp_theme.data)
        print(">>> Test 18: Member Deletion Flash Alerts, Role Management, Org Bank & Theme Settings 100% OK")

    def test_19_position_crud_and_member_jabatan(self):
        # 1. Login as Superadmin
        admin = User.query.filter_by(email='admin@gimbal.org').first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id

        # 2. Access Admin Settings - Struktur & Jabatan Tab
        resp = self.client.get('/admin/settings?tab=positions', headers={'HX-Request': 'true'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Master Struktur & Jabatan Organisasi', resp.data)
        self.assertIn(b'admin-panel-positions', resp.data)

        # 3. Create Position Modal
        resp_modal = self.client.get('/admin/positions/create-modal')
        self.assertEqual(resp_modal.status_code, 200)
        self.assertIn(b'modal-create-position', resp_modal.data)
        self.assertIn(b'Tambah Jabatan Organisasi', resp_modal.data)

        # 4. Create New Position via POST
        pos_title = 'Kadiv Penjelajahan Rimba Unik'
        resp_create = self.client.post('/admin/positions/create', data={
            'name': pos_title,
            'category': 'Divisi Teknis',
            'order_index': '45',
            'description': 'Bertanggung jawab atas ekspedisi jalur rimba perintis',
            'is_active': '1'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_create.status_code, 200)
        self.assertIn(b'berhasil ditambahkan', resp_create.data)

        created_pos = Position.query.filter_by(name=pos_title).first()
        self.assertIsNotNone(created_pos)
        self.assertEqual(created_pos.category, 'Divisi Teknis')
        self.assertEqual(created_pos.order_index, 45)

        # 5. Member Edit Modal includes Jabatan dropdown and positions
        member = User.query.filter(User.role == 'member').first()
        resp_edit_modal = self.client.get(f'/admin/member/edit-modal/{member.id}')
        self.assertEqual(resp_edit_modal.status_code, 200)
        self.assertIn(b'Jabatan / Struktur Organisasi', resp_edit_modal.data)
        self.assertIn(pos_title.encode('utf-8'), resp_edit_modal.data)

        # 6. Assign Position to Member via Edit Member
        resp_edit_member = self.client.post(f'/admin/member/edit/{member.id}', data={
            'name': member.name,
            'email': member.email,
            'role': member.role,
            'status': member.status,
            'jabatan': pos_title,
            'phone': member.phone or '08123456789'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_edit_member.status_code, 200)
        
        # Verify user model has updated jabatan
        db.session.refresh(member)
        self.assertEqual(member.jabatan, pos_title)
        self.assertEqual(created_pos.member_count, 1)

        # Member list renders the jabatan badge
        resp_members = self.client.get('/admin/members', headers={'HX-Request': 'true'})
        self.assertEqual(resp_members.status_code, 200)
        self.assertIn(pos_title.encode('utf-8'), resp_members.data)

        # 7. Edit Position (Rename should cascade to member)
        updated_title = 'Kadiv Ekspedisi Rimba Perintis'
        resp_edit_pos = self.client.post(f'/admin/positions/edit/{created_pos.id}', data={
            'name': updated_title,
            'category': 'Divisi Teknis',
            'order_index': '40',
            'description': 'Deskripsi diperbarui',
            'is_active': '1'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_edit_pos.status_code, 200)

        db.session.refresh(member)
        self.assertEqual(member.jabatan, updated_title)

        # 8. Toggle Active Position
        resp_toggle = self.client.post(f'/admin/positions/toggle-active/{created_pos.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_toggle.status_code, 200)
        db.session.refresh(created_pos)
        self.assertFalse(created_pos.is_active)

        # 9. Delete Position (Safe deletion clears member.jabatan)
        resp_del = self.client.post(f'/admin/positions/delete/{created_pos.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_del.status_code, 200)
        self.assertIsNone(Position.query.get(created_pos.id))
        db.session.refresh(member)
        self.assertIn(member.jabatan, [None, ''])
        print(">>> Test 19: Master Jabatan CRUD & Member Jabatan Integration 100% OK")

    def test_20_float_chat_soft_deactivation_and_cloudflare_email(self):
        """
        Pengujian Fungsionalitas Modifikasi Baru:
        1. Bottom Float Chat (Basecamp Publik & Private DM 1-on-1, Kontak & Unread Count)
        2. Soft Deactivation Toggle (Pilihan Proper Nonaktifkan Akun Tanpa Merusak Cascades)
        3. Users Last Login Terdata di Tabel Master Anggota & Login Hook
        4. Cloudflare Email Forwarding API Helper & Konfigurasi Pengaturan Admin
        """
        from cloudflare_email import clean_username_for_alias
        from datetime import datetime

        admin = User.query.filter_by(role='superadmin').first() or User.query.filter_by(role='admin').first()
        budi = User.query.filter_by(email='budi.pendaki@gmail.com').first()
        self.assertIsNotNone(budi)

        # 1. Uji Helper Cloudflare Username Alias
        alias_1 = clean_username_for_alias("fitra.pendaki+outdoor@gmail.com")
        self.assertEqual(alias_1, "fitra_pendaki@gimbal.my.id")
        alias_2 = clean_username_for_alias("budi-santoso@yahoo.co.id")
        self.assertEqual(alias_2, "budi_santoso@gimbal.my.id")

        # 2. Uji Bottom Float Chat Contacts & Direct Messaging
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id

        # a. Fetch Contacts
        resp_contacts = self.client.get('/member/chat/contacts', headers={'HX-Request': 'true'})
        self.assertEqual(resp_contacts.status_code, 200)
        self.assertIn(b'Budi Santoso Petualang', resp_contacts.data)

        # b. Kirim Private Message ke Budi
        resp_send_dm = self.client.post('/member/chat/send', data={
            'message': 'Halo Budi, koordinasi logistik ekspedisi akhir pekan ya!',
            'mode': 'private',
            'recipient_id': str(budi.id)
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_send_dm.status_code, 200)
        self.assertIn(b'koordinasi logistik ekspedisi', resp_send_dm.data)

        # c. Ambil Riwayat Chat Private antara Admin & Budi
        resp_chat_hist = self.client.get(f'/member/chat/messages?mode=private&recipient_id={budi.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_chat_hist.status_code, 200)
        self.assertIn(b'koordinasi logistik ekspedisi', resp_chat_hist.data)

        # d. Ganti sesi ke Budi untuk cek unread count & pesan masuk
        with self.client.session_transaction() as sess:
            sess['user_id'] = budi.id

        resp_unread = self.client.get('/member/chat/unread-count', headers={'Accept': 'application/json'})
        self.assertEqual(resp_unread.status_code, 200)
        unread_data = resp_unread.get_json()
        self.assertIn('total_unread', unread_data)
        self.assertGreaterEqual(unread_data['total_unread'], 1)

        # e. Uji rendering Bottom Float Chat di shell & guest safety
        resp_shell = self.client.get('/', headers={'HX-Request': 'true', 'HX-Target': 'app-shell'})
        self.assertEqual(resp_shell.status_code, 200)
        self.assertIn(b'id="gimbal-float-chat-root"', resp_shell.data)
        self.assertIn(b'id="float-chat-trigger-btn"', resp_shell.data)
        self.assertIn(b'id="gimbal-chat-window"', resp_shell.data)
        self.assertIn(b'window.toggleGimbalChat', resp_shell.data)
        self.assertIn(b'bottom: 5.25rem !important;', resp_shell.data)
        # Pastikan tidak ada titik hijau online permanen di dalam trigger button floating chat
        trigger_btn_html = resp_shell.data.split(b'id="float-chat-trigger-btn"')[1].split(b'</button>')[0]
        self.assertNotIn(b'bg-emerald-500', trigger_btn_html)

        # f. Uji guest (unauthenticated) di landing page TIDAK menampilkan floating chat widget
        with self.client.session_transaction() as sess:
            sess.clear()
        resp_landing_guest = self.client.get('/', headers={'HX-Request': 'true', 'HX-Target': 'app-shell'})
        self.assertEqual(resp_landing_guest.status_code, 200)
        self.assertNotIn(b'id="gimbal-float-chat-root"', resp_landing_guest.data)
        self.assertNotIn(b'id="float-chat-trigger-btn"', resp_landing_guest.data)
        self.assertNotIn(b'id="gimbal-chat-window"', resp_landing_guest.data)

        # g. Uji guest (unauthenticated) unread-count kosong
        resp_guest_unread = self.client.get('/member/chat/unread-count')
        self.assertEqual(resp_guest_unread.status_code, 200)
        self.assertEqual(resp_guest_unread.data.decode('utf-8').strip(), '')

        # 3. Uji Soft Deactivation Toggle (Pilihan Proper Nonaktifkan Akun)
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id

        # Nonaktifkan akun Budi
        resp_toggle_off = self.client.post(f'/admin/member/toggle-status/{budi.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_toggle_off.status_code, 200)
        db.session.refresh(budi)
        self.assertEqual(budi.status, 'inactive')
        self.assertIn(b'dinonaktifkan', resp_toggle_off.data)

        # Aktifkan kembali akun Budi
        resp_toggle_on = self.client.post(f'/admin/member/toggle-status/{budi.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_toggle_on.status_code, 200)
        db.session.refresh(budi)
        self.assertEqual(budi.status, 'active')
        self.assertIn(b'diaktifkan kembali', resp_toggle_on.data)

        # 4. Uji Pengaturan Cloudflare Email Forwarding di Admin Settings
        resp_cf_settings = self.client.post('/admin/settings/cloudflare', data={
            'cloudflare_enabled': '1',
            'cloudflare_api_token': 'dummy_cf_api_token_12345',
            'cloudflare_zone_id': 'dummy_zone_abcde12345',
            'cloudflare_domain': 'gimbal.my.id'
        }, headers={'HX-Request': 'true'})
        self.assertEqual(resp_cf_settings.status_code, 200)
        self.assertIn(b'Konfigurasi Cloudflare Email', resp_cf_settings.data)

        self.assertEqual(SystemSetting.get('cloudflare_enabled'), 'true')
        self.assertEqual(SystemSetting.get('cloudflare_domain'), 'gimbal.my.id')

        # 5. Uji Last Login & Rendering di Data Tabel Anggota
        budi.password_hash = 'budi123'
        db.session.commit()

        # Login manual akun Budi
        resp_login = self.client.post('/auth/login', data={
            'email': 'budi.pendaki@gmail.com',
            'password': 'budi123'
        })
        self.assertEqual(resp_login.status_code, 302)
        db.session.refresh(budi)
        self.assertIsNotNone(budi.last_login)

        # Buka tabel anggota admin sebagai admin, periksa kolom 'Terakhir Masuk' & Cloudflare badge
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id

        resp_members_table = self.client.get('/admin/members', headers={'HX-Request': 'true'})
        self.assertEqual(resp_members_table.status_code, 200)
        self.assertIn(b'Terakhir Masuk', resp_members_table.data)
        self.assertIn(b'gimbal.my.id', resp_members_table.data)
        self.assertIn(b'Terdata', resp_members_table.data)

        print(">>> Test 20: Float Chat (Public & Private DM), Soft Deactivation, Last Login & Cloudflare Email 100% OK")

    def test_21_multimedia_post_and_expedition_documentation(self):
        """
        Menguji fitur:
        1. Pembuatan postingan multi foto/video (PostMedia) yang terhubung ke agenda Ekspedisi (Activity)
        2. Aggregasi galeri dokumentasi ekspedisi (Activity.documentation_media)
        3. Endpoint modal dokumentasi ekspedisi (/member/activity/documentation/<id>)
        4. Pin postingan multi-media ke galeri web (admin_pin_post_to_gallery)
        5. Filterable Masonry Grid dan Infinite Marquee di Landing Page
        """
        import io
        import time

        with self.client.session_transaction() as sess:
            budi = User.query.filter_by(email='budi.pendaki@gmail.com').first()
            sess['user_id'] = budi.id

        # Pastikan ada activity (ekspedisi) aktif
        act = Activity.query.first()
        if not act:
            act = Activity(
                title="Ekspedisi Puncak Tilongkabila 2026",
                description="Pendakian jalur rintis dan dokumentasi flora fauna",
                activity_type="Pendakian",
                location="Gunung Tilongkabila",
                start_date="2026-10-10",
                end_date="2026-10-14",
                status="open"
            )
            db.session.add(act)
            db.session.commit()

        unique_mark = f"ekspedisi-multi-{int(time.time()*1000)}"

        # 1. Buat postingan multi file (2 foto dan 1 video)
        data = {
            'content': f'Laporan visual regu lapangan jalur Tilongkabila {unique_mark}',
            'location': 'Pos 3 Shelter Mata Air Tilongkabila',
            'activity_id': str(act.id),
            'media_files': [
                (io.BytesIO(b'fake_photo_bytes_1'), 'shelter_pos3.jpg'),
                (io.BytesIO(b'fake_photo_bytes_2'), 'puncak_kabut.png'),
                (io.BytesIO(b'fake_video_bytes_1'), 'trekking_summit.mp4')
            ]
        }
        resp = self.client.post('/member/post/create', data=data, content_type='multipart/form-data', headers={'HX-Request': 'true'})
        self.assertEqual(resp.status_code, 200)

        # Cek DB Post & PostMedia
        post = Post.query.filter(Post.content.like(f"%{unique_mark}%")).first()
        self.assertIsNotNone(post)
        self.assertEqual(post.activity_id, act.id)
        self.assertEqual(len(post.media), 3)
        self.assertEqual(len(post.media_items), 3)

        # Cek tipe media yang tersimpan
        types = [m.media_type for m in post.media]
        self.assertEqual(types.count('image'), 2)
        self.assertEqual(types.count('video'), 1)

        # 2. Cek agregasi dokumentasi pada Activity
        doc_media = act.documentation_media
        self.assertGreaterEqual(len(doc_media), 3)
        doc_urls = [d['media_url'] for d in doc_media]
        for m in post.media:
            self.assertIn(m.media_url, doc_urls)

        # 3. Uji endpoint modal dokumentasi ekspedisi
        resp_doc_modal = self.client.get(f'/member/activity/documentation/{act.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_doc_modal.status_code, 200)
        self.assertIn(b'Dokumentasi Ekspedisi', resp_doc_modal.data)
        self.assertIn(b'activeFilter', resp_doc_modal.data)
        self.assertIn(b'shelter_pos3', resp_doc_modal.data)

        # 4. Uji Pin postingan multi-media ke Galeri Web
        with self.client.session_transaction() as sess:
            admin = User.query.filter_by(email='admin@gimbal.org').first()
            sess['user_id'] = admin.id

        resp_pin = self.client.post(f'/admin/post/pin-to-gallery/{post.id}')
        self.assertEqual(resp_pin.status_code, 200)
        self.assertIn(b'Foto Terpin di Galeri Web', resp_pin.data)

        # Seluruh media postingan (3 media) harus berhasil masuk ke GalleryItem
        all_pinned = GalleryItem.query.filter_by(post_id=post.id).all()
        self.assertEqual(len(all_pinned), 3)

        for m in post.media_items:
            g_item = GalleryItem.query.filter_by(image_url=m.media_url).first()
            self.assertIsNotNone(g_item)
            self.assertEqual(g_item.post_id, post.id)
            self.assertEqual(g_item.activity_id, act.id)
            self.assertIsNotNone(g_item.album_json)

        # 5. Uji Landing Page: Penghapusan Rolling Marquee & Integrasi Dinamis Divisi Operasional Database
        resp_landing = self.client.get('/', headers={'HX-Request': 'true'})
        self.assertEqual(resp_landing.status_code, 200)
        self.assertNotIn(b'animate-marquee-infinite', resp_landing.data)
        self.assertIn(b'Galeri Jejak Petualangan', resp_landing.data)
        self.assertIn(b'openSingleLightbox', resp_landing.data)
        self.assertIn(b'data-album', resp_landing.data)
        self.assertIn(b'3 Foto', resp_landing.data)
        self.assertIn(b'Divisi Operasional GIMBAL', resp_landing.data)
        self.assertIn(b'Gunung Hutan', resp_landing.data)
        self.assertIn(b'Panjat Tebing', resp_landing.data)
        self.assertIn(b'Susur Gua', resp_landing.data)

        print(">>> Test 21: Multi-media Post, Expedition Documentation Album & Animated Gallery 100% OK")

    def test_22_timeline_share_features(self):
        """
        Menguji fitur share linimasa:
        1. Agenda ekspedisi fase planning/open bisa dishare ke linimasa sebelum mulai
        2. Fitur toggle share linimasa untuk dokumen (admin & member)
        3. Fitur toggle share linimasa untuk repo peta geodata (admin & member)
        4. Verifikasi post type dan rendering di lini masa member
        """
        admin = User.query.filter_by(email='admin@gimbal.org').first()
        member = User.query.filter(User.role == 'member', User.status == 'active').first()
        if not member:
            member = User.query.filter_by(email='budi.pendaki@gmail.com').first()
        if not member:
            member = User(
                name="Anggota Aktif Test",
                email="member.aktif@gmail.com",
                role="member",
                status="active"
            )
            db.session.add(member)
            db.session.commit()

        # 1. Agenda ekspedisi fase 'open' (belum mulai)
        act = Activity(
            title="Ekspedisi Uji Linimasa Pra-Mulai",
            category="Pendakian Gunung",
            difficulty="Menengah",
            location="Gunung Dapi, Gorontalo Utara",
            activity_date="12-15 November 2026",
            description="Uji kesiapan fisik dan survival pra-ekspedisi",
            quota=15,
            phase="open",
            is_open=True
        )
        db.session.add(act)
        db.session.commit()

        # Admin toggle share ON
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id

        resp_act_share = self.client.post(f'/admin/activity/{act.id}/toggle-share')
        self.assertEqual(resp_act_share.status_code, 200)
        self.assertIn(b'Linimasa: ON', resp_act_share.data)

        # Cek Post dibuat dengan post_type='activity'
        post_act = Post.query.filter_by(activity_id=act.id, post_type='activity').first()
        self.assertIsNotNone(post_act)
        self.assertIn("AGENDA EKSPEDISI MENDATANG", post_act.content)
        self.assertIn("Gunung Dapi", post_act.content)

        # Admin toggle share OFF -> Post terhapus
        resp_act_unshare = self.client.post(f'/admin/activity/{act.id}/toggle-share')
        self.assertEqual(resp_act_unshare.status_code, 200)
        self.assertIn(b'Linimasa: OFF', resp_act_unshare.data)
        self.assertIsNone(Post.query.filter_by(activity_id=act.id, post_type='activity').first())

        # Member share upcoming activity ke timeline
        with self.client.session_transaction() as sess:
            sess['user_id'] = member.id

        resp_member_share = self.client.post(f'/member/activity/share-to-timeline/{act.id}')
        self.assertEqual(resp_member_share.status_code, 200)
        self.assertIn(b'Terbagikan ke Linimasa', resp_member_share.data)
        self.assertTrue(act.is_shared_to_timeline)

        # 2. Fitur toggle share linimasa Dokumen
        doc = Document(
            title="SOP Navigasi Rimba & GPS Standar GIMBAL",
            description="Panduan penggunaan aplikasi Gimbal Maps dan kompas bidik prisma",
            file_path="/uploads/docs/sop_navigasi_test.pdf",
            file_type="pdf",
            file_size_fmt="2.4 MB",
            category="sop_keselamatan",
            is_public_to_members=True
        )
        db.session.add(doc)
        db.session.commit()

        # Member biasa tidak bisa toggle share dokumen (403)
        resp_m_doc_fail = self.client.post(f'/member/documents/toggle-share/{doc.id}')
        self.assertEqual(resp_m_doc_fail.status_code, 403)

        # Admin toggle share dokumen ON
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id

        resp_doc_on = self.client.post(f'/admin/documents/toggle-share/{doc.id}')
        self.assertEqual(resp_doc_on.status_code, 200)
        self.assertIn(b'Linimasa: ON', resp_doc_on.data)

        # Cek Post dokumen terbentuk
        post_doc = Post.query.filter_by(document_id=doc.id, post_type='document').first()
        self.assertIsNotNone(post_doc)
        self.assertIn("PUBLIKASI DOKUMEN RESMI GIMBAL", post_doc.content)
        self.assertIn("SOP Navigasi Rimba", post_doc.content)

        # Admin toggle share dokumen OFF -> Post terhapus
        resp_doc_off = self.client.post(f'/admin/documents/toggle-share/{doc.id}')
        self.assertEqual(resp_doc_off.status_code, 200)
        self.assertIn(b'Linimasa: OFF', resp_doc_off.data)
        self.assertIsNone(Post.query.filter_by(document_id=doc.id, post_type='document').first())

        # Aktifkan kembali via member toggle (oleh admin)
        resp_m_doc_on = self.client.post(f'/member/documents/toggle-share/{doc.id}')
        self.assertEqual(resp_m_doc_on.status_code, 200)
        self.assertIn(b'Linimasa: ON', resp_m_doc_on.data)

        # 3. Fitur toggle share linimasa Repo Peta Geodata
        repo_map = MapRepository(
            title="Peta Topografi Tilongkabila 1:25.000",
            region="Bone Bolango",
            category="gunung_hutan",
            file_type="mbtiles",
            file_path="/uploads/repo_maps/tilongkabila_test.mbtiles",
            file_size_fmt="18.5 MB",
            total_distance_km=14.2,
            total_waypoints=12,
            uploaded_by=admin.id
        )
        db.session.add(repo_map)
        db.session.commit()

        # Admin toggle share peta ON
        resp_map_on = self.client.post(f'/admin/repo-maps/toggle-share/{repo_map.id}')
        self.assertEqual(resp_map_on.status_code, 200)
        self.assertIn(b'Linimasa: ON', resp_map_on.data)

        post_map = Post.query.filter_by(map_repo_id=repo_map.id, post_type='map').first()
        self.assertIsNotNone(post_map)
        self.assertIn("REPO PETA & GEODATA TERBARU", post_map.content)
        self.assertIn("14.2 km", post_map.content)
        self.assertIn("12 Waypoints", post_map.content)

        # Member uploader toggle share peta OFF lalu ON
        resp_map_off = self.client.post(f'/member/repo-maps/toggle-share/{repo_map.id}')
        self.assertEqual(resp_map_off.status_code, 200)
        self.assertIn(b'Linimasa: OFF', resp_map_off.data)
        self.assertIsNone(Post.query.filter_by(map_repo_id=repo_map.id, post_type='map').first())

        resp_map_on2 = self.client.post(f'/member/repo-maps/toggle-share/{repo_map.id}')
        self.assertEqual(resp_map_on2.status_code, 200)
        self.assertIn(b'Linimasa: ON', resp_map_on2.data)

        # 4. Rendering Dashboard Lini Masa Member
        with self.client.session_transaction() as sess:
            sess['user_id'] = member.id

        resp_dashboard = self.client.get('/member/dashboard', headers={'HX-Request': 'true'})
        self.assertEqual(resp_dashboard.status_code, 200)
        # Kartu Agenda Ekspedisi Terbuka
        self.assertIn(b'Agenda Ekspedisi Terbuka', resp_dashboard.data)
        self.assertIn(b'Gabung Ekspedisi', resp_dashboard.data)
        # Kartu Dokumen
        self.assertIn(b'Unduh Dokumen', resp_dashboard.data)
        self.assertIn(b'SOP Navigasi Rimba', resp_dashboard.data)
        # Kartu Peta Repo
        self.assertIn(b'Unduh Peta', resp_dashboard.data)
        self.assertIn(b'Tilongkabila', resp_dashboard.data)

        print(">>> Test 22: Timeline Sharing (Pre-Start Activity, Document Toggle, Map Repo Toggle) 100% OK")

    def test_23_academy_sop_and_certification_flow(self):
        """Uji menyeluruh E-Learning Academy, SOP Digital, Kuis, Sertifikasi Digital & Penugasan Wajib"""
        member = User.query.filter_by(email='budi.pendaki@gmail.com').first()
        admin = User.query.filter(User.role.in_(['admin', 'superadmin'])).first()
        self.assertIsNotNone(member)
        self.assertIsNotNone(admin)

        # 1. Member Akses Portal Akademi
        with self.client.session_transaction() as sess:
            sess['user_id'] = member.id

        resp_academy = self.client.get('/member/academy', headers={'HX-Request': 'true'})
        self.assertEqual(resp_academy.status_code, 200)
        self.assertIn(b'Akademi Rimba KPAB GIMBAL', resp_academy.data)
        self.assertIn(b'Brevet Kesiapan Rimba', resp_academy.data)

        # 2. Member Baca Pelajaran Pertama
        lesson = AcademyLesson.query.first()
        self.assertIsNotNone(lesson)
        resp_lesson = self.client.get(f'/member/academy/lesson/{lesson.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_lesson.status_code, 200)
        self.assertIn(b'Prinsip ABC Packing', resp_lesson.data)

        # 3. Member Selesaikan Pelajaran Pertama
        resp_complete = self.client.post(f'/member/academy/lesson/{lesson.id}/complete')
        self.assertEqual(resp_complete.status_code, 302)
        prog = UserLessonProgress.query.filter_by(user_id=member.id, lesson_id=lesson.id).first()
        self.assertIsNotNone(prog)
        self.assertTrue(prog.is_completed)

        # 4. Member Buka Kuis Sertifikasi Tingkat 1
        tier1 = AcademyTier.query.filter_by(order_index=1).first()
        self.assertIsNotNone(tier1)
        quiz = tier1.quizzes[0]
        self.assertIsNotNone(quiz)
        resp_quiz = self.client.get(f'/member/academy/quiz/{quiz.id}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_quiz.status_code, 200)
        self.assertIn(b'Ujian Sertifikasi Kesiapan Rimba', resp_quiz.data)

        # 5. Member Mengerjakan Kuis dengan 100% Jawaban Benar
        form_data = {}
        for q in quiz.questions:
            correct_opt = next(opt for opt in q.options if opt.is_correct)
            form_data[f'question_{q.id}'] = str(correct_opt.id)

        resp_submit = self.client.post(f'/member/academy/quiz/{quiz.id}/submit', data=form_data)
        self.assertEqual(resp_submit.status_code, 302)

        # Cek Hasil Ujian
        attempt = UserQuizAttempt.query.filter_by(user_id=member.id, quiz_id=quiz.id).order_by(UserQuizAttempt.id.desc()).first()
        self.assertIsNotNone(attempt)
        self.assertTrue(attempt.passed)
        self.assertEqual(attempt.score, 100.0)

        # Cek Sertifikat Digital Otomatis Terbit
        cert = UserCertification.query.filter_by(user_id=member.id, tier_id=tier1.id, status='active').first()
        self.assertIsNotNone(cert)
        self.assertTrue(cert.certificate_no.startswith('CERT-GIMBAL-01-'))
        self.assertEqual(cert.score_achieved, 100.0)

        # 6. Member Buka Piagam Sertifikat Digital & QR Code
        resp_cert = self.client.get(f'/member/academy/certificate/{cert.certificate_no}', headers={'HX-Request': 'true'})
        self.assertEqual(resp_cert.status_code, 200)
        self.assertIn(b'PIAGAM KOMPETENSI', resp_cert.data)
        self.assertIn(member.name.encode('utf-8'), resp_cert.data)
        self.assertIn(cert.certificate_no.encode('utf-8'), resp_cert.data)

        # 7. Verifikasi Keaslian Sertifikat Publik (/verify-cert/<cert_no>)
        resp_verify = self.client.get(f'/verify-cert/{cert.certificate_no}')
        self.assertEqual(resp_verify.status_code, 200)
        self.assertIn(b'SERTIFIKAT RESMI & TERVERIFIKASI', resp_verify.data)
        self.assertIn(member.name.encode('utf-8'), resp_verify.data)

        # 8. Cek Badge Terpasang di Properti Member (KTA & Profil)
        db.session.refresh(member)
        cert_names = [c.tier.badge_name for c in member.certifications_list]
        self.assertIn(tier1.badge_name, cert_names)

        # 9. Admin Kontrol: Buka Halaman Admin Akademi
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id

        resp_admin_acad = self.client.get('/admin/academy', headers={'HX-Request': 'true'})
        self.assertEqual(resp_admin_acad.status_code, 200)
        self.assertIn(b'Akademi Rimba', resp_admin_acad.data)

        # 10. Admin Toggle Wajib Sertifikasi untuk Member Tertentu
        other_user = User.query.filter(User.id != member.id, ~User.role.in_(['admin', 'superadmin'])).first()
        if not other_user:
            other_user = member

        initial_state = other_user.is_mandatory_certified
        resp_toggle = self.client.post(f'/admin/academy/mandate/toggle/{other_user.id}')
        self.assertEqual(resp_toggle.status_code, 302)
        db.session.refresh(other_user)
        self.assertEqual(other_user.is_mandatory_certified, not initial_state)

        # 11. Admin Batch Mandate All Candidates (1-Klik)
        resp_batch = self.client.post('/admin/academy/mandate/all-candidates')
        self.assertEqual(resp_batch.status_code, 302)

        # 12. Admin Reset Semua Mandat Wajib
        resp_clear = self.client.post('/admin/academy/mandate/clear-all')
        self.assertEqual(resp_clear.status_code, 302)

        print(">>> Test 23: Academy Rimba, SOP Digital, Kuis, Sertifikasi Digital & Penugasan Wajib 100% OK")

if __name__ == '__main__':
    unittest.main()




