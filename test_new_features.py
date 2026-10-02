import os
import unittest
from datetime import datetime, timedelta
from app import app, db
from models import User, Activity, ChatMessage

class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()
            
            # Buat user online
            u1 = User(
                name='User Online',
                email='test_online_1@example.com',
                status='active',
                role='member',
                last_seen=datetime.utcnow()
            )
            # Buat user offline
            u2 = User(
                name='User Offline',
                email='test_offline_2@example.com',
                status='active',
                role='member',
                last_seen=datetime.utcnow() - timedelta(minutes=10)
            )
            # Admin user
            admin = User.query.filter_by(role='superadmin').first()
            if not admin:
                admin = User(
                    name='Admin Test Custom',
                    email='test_admin_unique@example.com',
                    status='active',
                    role='admin',
                    last_seen=datetime.utcnow()
                )
                db.session.add(admin)
            db.session.add_all([u1, u2])
            db.session.commit()

            # Buat activity untuk ROL
            act = Activity(
                title='Ekspedisi Uji ROL',
                location='Gunung Tilongkabila',
                activity_date='2026-10-10',
                difficulty='Sedang',
                quota=15,
                is_open=True
            )
            db.session.add(act)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_user_is_online_property(self):
        with app.app_context():
            u_online = User.query.filter_by(email='test_online_1@example.com').first()
            u_offline = User.query.filter_by(email='test_offline_2@example.com').first()
            self.assertTrue(u_online.is_online)
            self.assertFalse(u_offline.is_online)

    def test_serve_assets_route(self):
        resp = self.client.get('/assets/logo.png')
        self.assertEqual(resp.status_code, 200)

    def test_print_rol_uses_assets_logo(self):
        with app.app_context():
            admin = User.query.filter(User.role.in_(['admin', 'superadmin'])).first()
            act = Activity.query.first()
            act_id = act.id
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id

        resp = self.client.get(f'/admin/activity/{act_id}/print')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'/assets/logo.png', resp.data)

    def test_shell_brand_and_landing_nav(self):
        with app.app_context():
            admin = User.query.filter(User.role.in_(['admin', 'superadmin'])).first()
            admin_id = admin.id
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin_id

        resp = self.client.get('/member/dashboard', headers={'HX-Request': 'true', 'HX-Target': 'app-shell'})
        self.assertEqual(resp.status_code, 200)
        # Brand link diarahkan ke /member/dashboard untuk logged in user
        self.assertIn(b'hx-get="/member/dashboard"', resp.data)
        # landing-desktop-nav memiliki display none !important
        self.assertIn(b'display: none !important;', resp.data)

    def test_online_indicator_in_chat(self):
        with app.app_context():
            admin = User.query.filter(User.role.in_(['admin', 'superadmin'])).first()
            admin_id = admin.id
            u1 = User.query.filter_by(email='test_online_1@example.com').first()
            u1_id = u1.id
            
            chat = ChatMessage(user_id=u1_id, message='Halo kawan!')
            db.session.add(chat)
            db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin_id

        # Public chat messages
        resp = self.client.get('/member/chat/messages?mode=public')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'bg-emerald-500', resp.data)

        # Contacts list
        resp_contacts = self.client.get('/member/chat/contacts')
        self.assertEqual(resp_contacts.status_code, 200)
        self.assertIn(b'bg-emerald-500', resp_contacts.data)

if __name__ == '__main__':
    unittest.main()
