import unittest
from app import app, db
from models import User, Activity, ActivityParticipant, ActivityFieldLog

class TestRolTabOptimization(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

        # Ambil atau buat admin
        self.admin = User.query.filter_by(role='admin').first()
        if not self.admin:
            self.admin = User(name='Admin Test', email='admintest@gimbal.org', role='admin', status='active')
            self.admin.set_password('password123')
            db.session.add(self.admin)
            db.session.commit()

        # Ambil atau buat member
        self.member = User.query.filter_by(role='member', status='active').first()
        if not self.member:
            self.member = User(name='Member Test', email='membertest@gimbal.org', role='member', status='active', nra='R-99-26')
            self.member.set_password('password123')
            db.session.add(self.member)
            db.session.commit()

        # Ambil atau buat kegiatan ekspedisi
        self.act = Activity.query.first()
        if not self.act:
            self.act = Activity(
                title='Ekspedisi Uji ROL',
                location='Gunung Tilongkabila',
                activity_date='10-15 Oktober 2026',
                difficulty='Menengah',
                category='Gunung Hutan',
                quota=10,
                phase='planning'
            )
            db.session.add(self.act)
            db.session.commit()

        # Login sebagai admin
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.admin.id

    def tearDown(self):
        self.ctx.pop()

    def test_01_manage_page_renders_with_tab_param(self):
        """Uji halaman manage ROL dengan query param tab: baik Direct GET (Layer 1) maupun HTMX (Layer 2)"""
        # Direct GET (Layer 1 index.html)
        resp_direct = self.client.get(f'/admin/activity/{self.act.id}/manage?tab=manifest')
        self.assertEqual(resp_direct.status_code, 200)
        self.assertIn(f'hx-get="/admin/activity/{self.act.id}/manage?tab=manifest"'.encode('utf-8'), resp_direct.data)

        # HTMX GET (Layer 2 macro template)
        resp_htmx = self.client.get(
            f'/admin/activity/{self.act.id}/manage?tab=manifest',
            headers={'HX-Request': 'true'}
        )
        self.assertEqual(resp_htmx.status_code, 200)
        self.assertIn(b'id="admin-activity-manage-container"', resp_htmx.data)
        self.assertIn(b'window.switchRolTab', resp_htmx.data)
        self.assertIn(b'id="rol-panel-manifest"', resp_htmx.data)
        self.assertIn(b'data-tab="manifest"', resp_htmx.data)

    def test_02_add_and_update_participant_preserves_manifest_tab(self):
        """Uji tambah dan update peran anggota di manifest tetap di tab manifest"""
        # Tambah peserta
        resp = self.client.post(
            f'/admin/activity/{self.act.id}/add-participant?tab=manifest',
            data={'user_id': self.member.id, 'role': 'Navigator Lapangan', 'tab': 'manifest'},
            headers={'HX-Request': 'true'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'id="rol-panel-manifest"', resp.data)

        part = ActivityParticipant.query.filter_by(activity_id=self.act.id, user_id=self.member.id).first()
        self.assertIsNotNone(part)

        # Update peran
        resp_role = self.client.post(
            f'/admin/activity/{self.act.id}/participant-role/{part.id}?tab=manifest',
            data={'role': 'Sweeper', 'tab': 'manifest'},
            headers={'HX-Request': 'true'}
        )
        self.assertEqual(resp_role.status_code, 200)
        self.assertIn(b'id="rol-panel-manifest"', resp_role.data)

    def test_03_edit_member_from_activity_redirects_back_to_manifest_tab(self):
        """Uji edit profil anggota dari ROL langsung kembali ke ROL tab manifest"""
        # Buka modal edit dengan from_activity
        resp_modal = self.client.get(f'/admin/member/edit-modal/{self.member.id}?from_activity={self.act.id}&from_tab=manifest')
        self.assertEqual(resp_modal.status_code, 200)
        self.assertIn(b'name="from_activity"', resp_modal.data)
        self.assertIn(b'name="from_tab"', resp_modal.data)

        # Submit edit member
        resp_edit = self.client.post(
            f'/admin/member/edit/{self.member.id}',
            data={
                'name': self.member.name,
                'email': self.member.email,
                'status': 'active',
                'from_activity': self.act.id,
                'from_tab': 'manifest'
            },
            headers={'HX-Request': 'true'}
        )
        self.assertEqual(resp_edit.status_code, 200)
        # Harus me-render halaman manage activity dengan tab manifest
        self.assertIn(b'id="admin-activity-manage-container"', resp_edit.data)
        self.assertIn(b'id="rol-panel-manifest"', resp_edit.data)

    def test_04_rol_plan_and_field_ops_preserve_tabs(self):
        """Uji update ROL plan dan field log tetap di tab masing-masing"""
        # Update ROL plan
        resp_rol = self.client.post(
            f'/admin/activity/{self.act.id}/update-rol?tab=rol_plan',
            data={
                'tab': 'rol_plan',
                'route_plan': 'Basecamp -> Pos 1 -> Puncak',
                'team_gear': 'Tenda Dome 2 unit',
                'fee_per_person': '50000'
            },
            headers={'HX-Request': 'true'}
        )
        self.assertEqual(resp_rol.status_code, 200)
        self.assertIn(b'id="rol-panel-rol_plan"', resp_rol.data)
        self.assertIn(b'Basecamp -&gt; Pos 1 -&gt; Puncak', resp_rol.data)

        # Add field log
        resp_log = self.client.post(
            f'/admin/activity/{self.act.id}/add-field-log?tab=field_ops',
            data={
                'tab': 'field_ops',
                'title': 'Pos 1 Lapor Uji',
                'latitude': '0.5123',
                'longitude': '123.1234',
                'description': 'Semua tim aman'
            },
            headers={'HX-Request': 'true'}
        )
        self.assertEqual(resp_log.status_code, 200)
        self.assertIn(b'id="rol-panel-field_ops"', resp_log.data)
        self.assertIn(b'Pos 1 Lapor Uji', resp_log.data)

if __name__ == '__main__':
    unittest.main()
