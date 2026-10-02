import os
import unittest
from app import app, db
from models import User, Sponsor, SponsorProduct, Post
from moderation import check_content_moderation, check_commercial_intent

class SponsorshipAndModerationTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

        self.admin = User.query.filter(User.role.in_(['admin', 'superadmin'])).first()
        self.member = User.query.filter_by(role='member', status='active').first()
        if not self.member:
            self.member = User.query.filter_by(status='active').first()

        # Bersihkan data dummy test sebelumnya agar setiap test deterministik
        for sp in Sponsor.query.filter(Sponsor.name.like('%Test%')).all():
            Post.query.filter_by(sponsor_id=sp.id).delete()
            db.session.delete(sp)
        if self.member:
            for sp in Sponsor.query.filter_by(owner_user_id=self.member.id).all():
                Post.query.filter_by(sponsor_id=sp.id).delete()
                db.session.delete(sp)
        Post.query.filter(Post.content.like('%Tilongkabila%')).delete()
        Post.query.filter(Post.content.like('%Carrier%')).delete()
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        self.ctx.pop()

    def set_session_user(self, user):
        with self.client.session_transaction() as sess:
            sess['user_id'] = user.id

    def test_01_ai_moderation_logic(self):
        """Test heuristic + AI logic for detecting direct selling AND ethics violations"""
        # 1. Story post (not blocked)
        story = "Kemarin kami mendaki Gunung Tilongkabila, pemandangan kabutnya sangat indah luar biasa. Tiket simaksi Rp 20.000."
        is_blocked, vtype, reason = check_content_moderation(story)
        self.assertFalse(is_blocked)
        self.assertEqual(vtype, 'none')

        # 2. Direct selling post (blocked as commercial)
        selling = "Dijual cepat Carrier Osprey Atmos 50L kondisi mulus 95%, harga Rp 1.800.000 nego tipis. Minat hubungi WA 081234567890."
        is_blocked, vtype, reason = check_content_moderation(selling)
        self.assertTrue(is_blocked)
        self.assertEqual(vtype, 'commercial')
        print(f"\n>>> Moderation blocked commercial text: {reason}")

        # 3. Ethics violation - Vandalism
        vandalism = "Asyik banget kemarin malam kita bawa pilox buat coret-coret batu plang nama puncak."
        is_blocked, vtype, reason = check_content_moderation(vandalism)
        self.assertTrue(is_blocked)
        self.assertEqual(vtype, 'ethics')
        print(f">>> Moderation blocked vandalism: {reason}")

        # 4. Ethics violation - Flora exploitation (memetik edelweis)
        flora_poach = "Mumpung sampai puncak, kita petik bunga edelweis sekantong plastik buat oleh-oleh pacar."
        is_blocked, vtype, reason = check_content_moderation(flora_poach)
        self.assertTrue(is_blocked)
        self.assertEqual(vtype, 'ethics')
        print(f">>> Moderation blocked flora poaching: {reason}")

    def test_02_admin_sponsorship_crud(self):
        """Test Admin creating, editing, and managing corporate sponsors & products"""
        self.set_session_user(self.admin)

        # Create Official Sponsor
        resp = self.client.post('/admin/sponsors/create', data={
            'name': 'Consina Outdoor Gorontalo Test',
            'category': 'gear',
            'tier': 'gold',
            'description': 'Pusat perlengkapan pendakian dan petualangan alam terbuka.',
            'promo_badge': 'Diskon 15% Member KTA',
            'member_benefit': 'Potongan harga 15% setiap transaksi dengan KTA GIMBAL.',
            'whatsapp_number': '081299998888',
            'address': 'Jl. Nani Wartabone No. 10, Kota Gorontalo'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        sponsor = Sponsor.query.filter_by(name='Consina Outdoor Gorontalo Test').first()
        self.assertIsNotNone(sponsor)
        self.assertEqual(sponsor.tier, 'gold')
        self.assertFalse(sponsor.is_member_business)

        # Add Product to Sponsor
        resp = self.client.post(f'/admin/sponsors/products/create/{sponsor.id}', data={
            'name': 'Tenda Consina Magnum 4',
            'price': '850000',
            'discount_price': '722500',
            'badge': 'KTA Promo',
            'description': 'Tenda double layer kapasitas 4 orang waterproof.'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        prod = SponsorProduct.query.filter_by(sponsor_id=sponsor.id).first()
        self.assertIsNotNone(prod)
        self.assertEqual(prod.price, 850000)
        self.assertEqual(prod.discount_price, 722500)

        # Share to Timeline
        resp = self.client.post(f'/admin/sponsors/share-timeline/{sponsor.id}', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        timeline_post = Post.query.filter_by(sponsor_id=sponsor.id).first()
        self.assertIsNotNone(timeline_post)
        self.assertEqual(timeline_post.post_type, 'sponsor')

        # Verify standalone /admin/sponsors page rendering
        resp_page = self.client.get('/admin/sponsors', headers={'HX-Request': 'true'})
        self.assertEqual(resp_page.status_code, 200)
        self.assertIn(b'Manajemen Sponsorship & Kemitraan', resp_page.data)
        self.assertIn(b'Consina Outdoor Gorontalo Test', resp_page.data)
        self.assertNotIn(b'admin-panel-sponsors', resp_page.data)

        # Verify /admin/settings page does NOT contain sponsors tab panel
        resp_settings = self.client.get('/admin/settings', headers={'HX-Request': 'true'})
        self.assertEqual(resp_settings.status_code, 200)
        self.assertNotIn(b'admin-panel-sponsors', resp_settings.data)
        self.assertIn(b'admin-panel-organization', resp_settings.data)
        print(">>> Test 02: Admin Sponsorship CRUD, Catalog, Standalone Page & Timeline share 100% OK")

    def test_03_member_business_registration_and_moderation(self):
        """Test Member registering a cafe business, managing products, and timeline moderation"""
        self.set_session_user(self.member)

        # Member tries to post direct selling directly to general timeline -> BLOCKED by AI Moderation
        resp = self.client.post('/member/post/create', data={
            'content': 'Dijual Carrier Eiger 60L second, harga Rp 650.000 nego, hubungi WA 085240001111'
        }, headers={'HX-Request': 'true'}, follow_redirects=True)
        self.assertIn(b'Lapak', resp.data)  # Flash message advising member to use Lapak feature
        blocked_post = Post.query.filter(Post.content.like('%Dijual Carrier Eiger%')).first()
        self.assertIsNone(blocked_post, "Commercial post should NOT be persisted to DB without sponsor_id")

        # Member tries to post content violating ethics (e.g. coret-coret batu) -> BLOCKED by Ethics Moderation
        resp_ethics = self.client.post('/member/post/create', data={
            'content': 'Asyik banget kemarin malam kita bawa pilox buat coret-coret batu puncak.'
        }, headers={'HX-Request': 'true'}, follow_redirects=True)
        self.assertIn(b'Etika &amp; Norma', resp_ethics.data)  # Flash message indicating ethics rejection
        blocked_ethics = Post.query.filter(Post.content.like('%coret-coret batu%')).first()
        self.assertIsNone(blocked_ethics, "Ethics violating post should NOT be persisted to DB")

        # Member registers their business properly via /member/business/register
        resp = self.client.post('/member/business/register', data={
            'name': 'Basecamp Kopi Pinogu Hulontalangi Test',
            'category': 'cafe',
            'promo_badge': 'Diskon 10% KTA GIMBAL',
            'member_benefit': 'Free refill kopi hangat dan diskon 10% semua makanan bagi pemegang KTA aktif.',
            'whatsapp_number': '085240001111',
            'address': 'Kawasan Konservasi Pinogu, Bone Bolango'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        biz = Sponsor.query.filter_by(name='Basecamp Kopi Pinogu Hulontalangi Test').first()
        self.assertIsNotNone(biz)
        self.assertTrue(biz.is_member_business)
        self.assertEqual(biz.owner_user_id, self.member.id)

        # Member adds product to their business
        resp = self.client.post(f'/member/business/product/create/{biz.id}', data={
            'name': 'Kopi Robusta Pinogu 200g',
            'price': '45000',
            'discount_price': '40000',
            'badge': 'Best Seller',
            'description': 'Kopi organik khas hutan konservasi Bone Bolango.'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        prod = SponsorProduct.query.filter_by(sponsor_id=biz.id).first()
        self.assertIsNotNone(prod)

        # Member shares their business officially to timeline
        resp = self.client.post(f'/member/business/share-timeline/{biz.id}', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        post = Post.query.filter_by(sponsor_id=biz.id).first()
        self.assertIsNotNone(post)
        self.assertEqual(post.post_type, 'sponsor')
        # Member tries to register a second business -> REJECTED (Max 1 business per member)
        resp_sec = self.client.post('/member/business/register', data={
            'name': 'Usaha Kedua Member Ilegal',
            'category': 'rental',
            'whatsapp_number': '081299999999'
        }, headers={'HX-Request': 'true'}, follow_redirects=True)
        self.assertIn(b'dibatasi maksimal 1', resp_sec.data)
        biz_sec = Sponsor.query.filter_by(name='Usaha Kedua Member Ilegal').first()
        self.assertIsNone(biz_sec, "Member must not be allowed to register more than 1 business")

        # Member tests edit modal and updates their existing business
        resp_modal = self.client.get(f'/member/business/edit-modal/{biz.id}')
        self.assertEqual(resp_modal.status_code, 200)
        self.assertIn(b'Edit Profil Lapak', resp_modal.data)

        resp_edit = self.client.post(f'/member/business/edit/{biz.id}', data={
            'name': 'Basecamp Kopi Pinogu Updated',
            'category': 'cafe',
            'promo_badge': 'Diskon 15% KTA GIMBAL',
            'member_benefit': 'Free refill 2x dan diskon 15%',
            'whatsapp_number': '085240001111',
            'address': 'Kawasan Konservasi Pinogu, Bone Bolango'
        }, headers={'HX-Request': 'true'}, follow_redirects=True)
        self.assertEqual(resp_edit.status_code, 200)
        db.session.refresh(biz)
        self.assertEqual(biz.name, 'Basecamp Kopi Pinogu Updated')
        self.assertEqual(biz.promo_badge, 'Diskon 15% KTA GIMBAL')

        print(">>> Test 03: Member Business 1-Limit, Edit, Product Catalog & AI Moderation verified 100% OK!")

    def test_04_timeline_toggle_and_anti_duplicate(self):
        """Test Toggle Share (ON/OFF), Top Current Timeline behavior, and Anti Double-Posting"""
        self.set_session_user(self.member)

        # 1. Test Anti Double-Posting Linimasa (24 Hours cutoff)
        unique_post_text = "Jalur pendakian pos 3 Tilongkabila mata air mengalir jernih dan cuaca cerah berawan."
        resp_post1 = self.client.post('/member/post/create', data={
            'content': unique_post_text
        }, headers={'HX-Request': 'true'}, follow_redirects=True)
        self.assertEqual(resp_post1.status_code, 200)

        p1 = Post.query.filter_by(content=unique_post_text).first()
        self.assertIsNotNone(p1)

        # Attempt to post duplicate content with same text (even with differing whitespace or case)
        resp_post2 = self.client.post('/member/post/create', data={
            'content': f"  {unique_post_text.upper()}  "
        }, headers={'HX-Request': 'true'}, follow_redirects=True)
        self.assertIn(b'duplikasi postingan', resp_post2.data)
        
        post_count = Post.query.filter_by(content=unique_post_text).count()
        self.assertEqual(post_count, 1, "Duplicate post must be blocked!")

        # 2. Test Member Business Toggle Share (ON -> OFF -> ON to Top of Timeline)
        biz = Sponsor.query.filter_by(owner_user_id=self.member.id).first()
        if not biz:
            biz = Sponsor(
                name='Warung Kopi Puncak Tilongkabila Test',
                category='cafe',
                logo_url='/uploads/sponsors/default_business.png',
                owner_user_id=self.member.id,
                is_member_business=True,
                status='active',
                is_active=True,
                is_shared_to_timeline=False
            )
            db.session.add(biz)
            db.session.commit()

        # Ensure OFF initially
        biz.is_shared_to_timeline = False
        Post.query.filter_by(sponsor_id=biz.id).delete()
        db.session.commit()

        # Turn ON via toggle
        resp_toggle_on = self.client.post(f'/member/business/toggle-share/{biz.id}?style=compact', headers={'HX-Request': 'true'})
        self.assertEqual(resp_toggle_on.status_code, 200)
        self.assertIn(b'Linimasa: ON', resp_toggle_on.data)
        db.session.refresh(biz)
        self.assertTrue(biz.is_shared_to_timeline)

        post_biz = Post.query.filter_by(sponsor_id=biz.id).first()
        self.assertIsNotNone(post_biz)
        self.assertEqual(post_biz.post_type, 'sponsor')

        # Turn OFF via toggle
        resp_toggle_off = self.client.post(f'/member/business/toggle-share/{biz.id}?style=compact', headers={'HX-Request': 'true'})
        self.assertEqual(resp_toggle_off.status_code, 200)
        self.assertIn(b'Linimasa: OFF', resp_toggle_off.data)
        db.session.refresh(biz)
        self.assertFalse(biz.is_shared_to_timeline)
        self.assertIsNone(Post.query.filter_by(sponsor_id=biz.id).first(), "Post must be removed when toggled OFF")

        # Turn ON again -> post reappears at top of current timeline
        resp_toggle_on2 = self.client.post(f'/member/business/toggle-share/{biz.id}?style=full', headers={'HX-Request': 'true'})
        self.assertEqual(resp_toggle_on2.status_code, 200)
        self.assertIn(b'Linimasa: ON', resp_toggle_on2.data)
        db.session.refresh(biz)
        self.assertTrue(biz.is_shared_to_timeline)

        reappeared_post = Post.query.filter_by(sponsor_id=biz.id).first()
        self.assertIsNotNone(reappeared_post)
        
        # Verify it is at the top of the timeline query
        top_post = Post.query.order_by(Post.created_at.desc()).first()
        self.assertEqual(top_post.id, reappeared_post.id, "Re-enabled business post must be at the top of current timeline")

        # 3. Test Admin Sponsor Toggle Share (ON/OFF)
        self.set_session_user(self.admin)
        corp_sponsor = Sponsor.query.filter_by(is_member_business=False).first()
        if corp_sponsor:
            resp_admin_on = self.client.post(f'/admin/sponsors/toggle-share/{corp_sponsor.id}', headers={'HX-Request': 'true'})
            self.assertEqual(resp_admin_on.status_code, 200)
            self.assertIn(b'Linimasa: ON', resp_admin_on.data)
            
            resp_admin_off = self.client.post(f'/admin/sponsors/toggle-share/{corp_sponsor.id}', headers={'HX-Request': 'true'})
            self.assertEqual(resp_admin_off.status_code, 200)
            self.assertIn(b'Linimasa: OFF', resp_admin_off.data)

        print(">>> Test 04: Anti Double-Posting and Timeline Toggle ON/OFF/TOP verified 100% OK!")

if __name__ == '__main__':
    unittest.main()

