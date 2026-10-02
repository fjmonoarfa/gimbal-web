import unittest
import json
import io
from app import app
from models import db, User, Activity, ActivityParticipant, ActivityFieldLog

class TestRolAndSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()
        cls.app_context = app.app_context()
        cls.app_context.push()

        # Bersihkan data uji jika ada
        for act in Activity.query.filter(Activity.title.like('Uji Ekspedisi%')).all():
            ActivityFieldLog.query.filter_by(activity_id=act.id).delete()
            ActivityParticipant.query.filter_by(activity_id=act.id).delete()
            db.session.delete(act)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        for act in Activity.query.filter(Activity.title.like('Uji Ekspedisi%')).all():
            ActivityFieldLog.query.filter_by(activity_id=act.id).delete()
            ActivityParticipant.query.filter_by(activity_id=act.id).delete()
            db.session.delete(act)
        db.session.commit()
        cls.app_context.pop()

    def _login_admin(self):
        with self.client.session_transaction() as sess:
            admin = User.query.filter_by(role='superadmin').first()
            if not admin:
                admin = User.query.filter_by(role='admin').first()
            sess['user_id'] = admin.id
            sess['_fresh'] = True
            return admin

    def test_complete_rol_workflow_and_mobile_sync(self):
        """Pengujian Siklus Lengkap ROL: Preset Kategori, Full Page Create, Manage ROL, Print Ready, & Mobile Sync"""
        admin = self._login_admin()

        # 1. Cek endpoint API Preset ROL untuk seluruh kategori
        categories = ['Gunung Hutan', 'Panjat Tebing', 'Susur Gua', 'Arung Jeram', 'Konservasi & LH', 'Pendidikan Dasar', 'Camp & Wisata Alam']
        for cat in categories:
            resp = self.client.get(f'/admin/activity/preset-rol?category={cat}')
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data['status'], 'success')
            self.assertIn('preset', data)
            preset = data['preset']
            self.assertIn('route_plan', preset)
            self.assertIn('team_gear', preset)
            self.assertIn('personal_gear', preset)
            self.assertIn('food_ration', preset)
            self.assertIn('medical_kit', preset)

        # 2. Buat Ekspedisi Baru via Full-Page Add dengan Kategori 'Susur Gua'
        resp_create = self.client.post('/admin/activity/new', data={
            'title': 'Uji Ekspedisi Karst Oluhuta 2026',
            'location': 'Kawasan Karst Bone Bolango',
            'activity_date': '10 - 13 November 2026',
            'difficulty': 'Menengah',
            'category': 'Susur Gua',
            'quota': '12',
            'phase': 'planning',
            'description': 'Eksplorasi speleologi lorong berair dan pemetaan sistem hidrologi bawah tanah'
        }, follow_redirects=True)
        self.assertEqual(resp_create.status_code, 200)

        act = Activity.query.filter_by(title='Uji Ekspedisi Karst Oluhuta 2026').first()
        self.assertIsNotNone(act)
        self.assertEqual(act.category, 'Susur Gua')
        self.assertEqual(act.phase, 'planning')
        self.assertIn('SRT', act.route_plan)
        self.assertIn('Tali Statis', act.gear_json)

        # Admin otomatis terdaftar sebagai Pimpinan Perjalanan
        part = ActivityParticipant.query.filter_by(activity_id=act.id, user_id=admin.id).first()
        self.assertIsNotNone(part)
        self.assertEqual(part.role, 'Pimpinan Perjalanan')

        # 3. Update Dokumen ROL (RAB, Rute, Logistik & Medis)
        resp_rol = self.client.post(f'/admin/activity/{act.id}/update-rol', data={
            'expense_transport': '750000',
            'expense_permit': '150000',
            'expense_food': '600000',
            'expense_gear': '300000',
            'expense_med': '100000',
            'expense_emergency': '200000',
            'fee_per_person': '175000',
            'income_subsidy': '500000',
            'income_sponsor': '0',
            'route_plan': 'Pitch 1 Entrance 30m -> Lorong Kering -> Sump Utama',
            'team_gear': 'Tali statis 150m, spit hanger, karabiner',
            'personal_gear': 'Helm caving, coverall, sepatu boot',
            'food_ration': 'Nasi bakar, madu sachet, biskuit',
            'medical_kit': 'Thermal blanket, kassa steril, bidai'
        }, follow_redirects=True)
        self.assertEqual(resp_rol.status_code, 200)

        db.session.refresh(act)
        self.assertEqual(act.budget_data.get('expense_transport'), 750000.0)
        self.assertEqual(act.gear_data.get('team_gear'), 'Tali statis 150m, spit hanger, karabiner')

        # 4. Transisi Fase ke 'in_progress' (Mulai Operasi Lapangan)
        resp_phase = self.client.post(f'/admin/activity/{act.id}/update-phase', data={
            'phase': 'in_progress'
        }, follow_redirects=True)
        self.assertEqual(resp_phase.status_code, 200)
        db.session.refresh(act)
        self.assertEqual(act.phase, 'in_progress')

        # 5. Uji Print-ready HTML/CSS preview (Ctrl+P -> Save as PDF)
        resp_print = self.client.get(f'/admin/activity/{act.id}/print')
        self.assertEqual(resp_print.status_code, 200)
        self.assertIn(b'RENCANA OPERASIONAL LAPANGAN (ROL)', resp_print.data)
        self.assertIn(b'KPAB GIMBAL', resp_print.data)
        self.assertIn(b'Susur Gua', resp_print.data)
        self.assertIn(b'window.print()', resp_print.data)
        self.assertIn(b'Sesuaikan Penandatangan', resp_print.data)
        self.assertIn(b'Pimpinan Perjalanan', resp_print.data)
        self.assertIn(b'Ketua Umum', resp_print.data)
        self.assertIn(b'Kepala Divisi Susur Gua', resp_print.data)

        # 6. Integrasi Mobile gimbal-maps: Login Google (Hanya Akun Aktif)
        # 6a. Tolak user tidak terdaftar
        resp_unreg = self.client.post('/api/v1/auth/google-login', json={'email': 'unregistered@google.com'})
        self.assertEqual(resp_unreg.status_code, 404)

        # 6b. Tolak user berstatus pending
        pending_user = User.query.filter_by(email='pending_map@gmail.com').first()
        if not pending_user:
            pending_user = User(email='pending_map@gmail.com', name='Pending User', status='pending', role='member')
            db.session.add(pending_user)
            db.session.commit()
        else:
            pending_user.status = 'pending'
            db.session.commit()
        resp_pending = self.client.post('/api/v1/auth/google-login', json={'email': 'pending_map@gmail.com'})
        self.assertEqual(resp_pending.status_code, 403)

        # 6c. Terima user aktif
        resp_login = self.client.post('/api/v1/auth/google-login', json={
            'email': admin.email
        })
        self.assertEqual(resp_login.status_code, 200)
        login_data = resp_login.get_json()
        self.assertEqual(login_data['status'], 'success')
        self.assertIn('auth_token', login_data)

        # 7. Integrasi Mobile gimbal-maps: Get Active Activities
        resp_acts = self.client.get('/api/v1/activities/active')
        self.assertEqual(resp_acts.status_code, 200)
        acts_data = resp_acts.get_json()
        self.assertEqual(acts_data['status'], 'success')
        self.assertGreaterEqual(len(acts_data['activities']), 1)

        # 8. Integrasi Mobile gimbal-maps: Field Sync Titik POI & File GPX
        gpx_dummy = """<?xml version="1.0"?>
        <gpx version="1.1" creator="gimbal-maps">
            <wpt lat="0.54321" lon="123.09876">
                <name>Entrance Pit Gua</name>
                <desc>Mulut vertikal kedalaman 30m</desc>
                <ele>320</ele>
            </wpt>
        </gpx>
        """

        data_sync = {
            'email': admin.email,
            'file': (io.BytesIO(gpx_dummy.encode('utf-8')), 'survey_test.gpx')
        }
        resp_sync = self.client.post(
            f'/api/v1/activities/{act.id}/field-sync',
            data=data_sync,
            content_type='multipart/form-data'
        )
        self.assertEqual(resp_sync.status_code, 200)
        sync_result = resp_sync.get_json()
        self.assertEqual(sync_result['status'], 'success')

        # Verifikasi catatan log lapangan tersimpan
        field_log = ActivityFieldLog.query.filter_by(activity_id=act.id, source='gimbal_maps').first()
        self.assertIsNotNone(field_log)
        self.assertIn('gimbal_maps', field_log.source)

if __name__ == '__main__':
    unittest.main()
