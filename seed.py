import os
import json
from datetime import datetime
from flask import Flask
from models import (
    db, User, Dues, DuesPayment, Document, Activity,
    GalleryItem, Post, PostComment, PostLike, ChatMessage,
    SystemSetting, AdminAuditLog, Position
)

def create_sample_app():
    app = Flask(__name__)
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///gimbal.db')
    if database_url.startswith('mysql://'):
        database_url = database_url.replace('mysql://', 'mysql+pymysql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def seed_database():
    app = create_sample_app()
    with app.app_context():
        db.create_all()
        
        # Migrasi kolom dinamis jika tabel sudah ada (MySQL / SQLite)
        try:
            with db.engine.connect() as conn:
                user_cols = [
                    ('jabatan', 'VARCHAR(100)'),
                    ('last_login', 'DATETIME NULL'),
                    ('gimbal_alias_email', 'VARCHAR(128) NULL'),
                    ('cloudflare_rule_id', 'VARCHAR(64) NULL'),
                    ('cloudflare_status', "VARCHAR(32) DEFAULT 'pending'")
                ]
                for col, col_type in user_cols:
                    try:
                        conn.execute(db.text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass

                chat_cols = [
                    ('recipient_id', 'INTEGER NULL'),
                    ('is_read', 'BOOLEAN DEFAULT 0')
                ]
                for col, col_type in chat_cols:
                    try:
                        conn.execute(db.text(f"ALTER TABLE chat_messages ADD COLUMN {col} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass
        except Exception:
            pass

        # 1. Superadmin & Admin & Users
        fitra = User.query.filter((User.email == 'fitra@gimbal.org') | (User.name == 'Fitra')).first()
        if not fitra:
            fitra = User(
                email='fitra@gimbal.org',
                name='Fitra',
                role='superadmin',
                status='active',
                nra='SA-01-26',
                nra_year=26,
                nra_sequence=0,
                phone='081234567800',
                birth_place='Gorontalo',
                birth_date='1990-01-01',
                address='Sekretariat KPAB GIMBAL, Kota Gorontalo, Provinsi Gorontalo',
                blood_type='O',
                medical_history='Sehat jasmani dan rohani',
                emergency_name='Sekretariat GIMBAL',
                emergency_relation='Organisasi',
                emergency_phone='081234567800',
                password_hash='P4ssw0rd!?!',
                avatar='https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80',
                approved_at=datetime.utcnow()
            )
            db.session.add(fitra)
        else:
            fitra.role = 'superadmin'
            fitra.password_hash = 'P4ssw0rd!?!'
            fitra.status = 'active'
            fitra.jabatan = 'Sekretaris Jenderal'
        admin = User.query.filter_by(email='admin@gimbal.org').first()
        if not admin:
            admin = User(
                email='admin@gimbal.org',
                name='Ketua Umum GIMBAL',
                role='admin',
                jabatan='Ketua Umum',
                status='active',
                nra='R-01-26',
                nra_year=26,
                nra_sequence=1,
                phone='081234567890',
                birth_place='Gorontalo',
                birth_date='1995-05-12',
                address='Sekretariat KPAB GIMBAL, Kota Gorontalo, Provinsi Gorontalo',
                blood_type='O',
                medical_history='Tidak ada riwayat alergi',
                emergency_name='Siti Rahmawati',
                emergency_relation='Keluarga',
                emergency_phone='081298765432',
                password_hash='gimbal123',
                avatar='https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80',
                approved_at=datetime.utcnow()
            )
            db.session.add(admin)
        else:
            admin.jabatan = 'Ketua Umum'

        member1 = User.query.filter_by(email='budi.pendaki@gmail.com').first()
        if not member1:
            member1 = User(
                email='budi.pendaki@gmail.com',
                name='Budi Santoso',
                role='member',
                jabatan='Bendahara Umum',
                status='active',
                nra='R-02-26',
                nra_year=26,
                nra_sequence=2,
                phone='081345678901',
                birth_place='Gorontalo',
                birth_date='1998-08-17',
                address='Jl. Nani Wartabone No. 12, Kota Gorontalo',
                blood_type='A',
                medical_history='Alergi dingin ringan',
                emergency_name='Dewi Lestari',
                emergency_relation='Ibu',
                emergency_phone='081398761234',
                password_hash='gimbal123',
                avatar='https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=200&q=80',
                approved_at=datetime.utcnow()
            )
            db.session.add(member1)
        else:
            member1.jabatan = 'Bendahara Umum'

        if not User.query.filter_by(email='calon.petualang@gmail.com').first():
            pending_user = User(
                email='calon.petualang@gmail.com',
                name='Rian Pratama',
                role='member',
                status='pending',
                nra=None,
                phone='081567890123',
                birth_place='Limboto',
                birth_date='2001-11-20',
                address='Jl. Trans Sulawesi, Limboto, Kabupaten Gorontalo',
                blood_type='B',
                medical_history='Pernah cedera engkel kanan (sudah pulih)',
                emergency_name='Bambang Supriyanto',
                emergency_relation='Ayah',
                emergency_phone='081512345678',
                password_hash='gimbal123',
                avatar='https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=200&q=80'
            )
            db.session.add(pending_user)

        db.session.commit()

        # 2. Master Iuran
        # Bersihkan record legacy 'Iuran Perawatan Tenda & Alat Outdoor' jika ada
        legacy_tenda = Dues.query.filter(Dues.title.ilike('%Perawatan Tenda%')).all()
        for lt in legacy_tenda:
            DuesPayment.query.filter_by(dues_id=lt.id).delete()
            db.session.delete(lt)
        if legacy_tenda:
            db.session.commit()

        dues_monthly = Dues.query.filter_by(category='wajib').first()
        if not dues_monthly:
            dues1 = Dues(
                title='Iuran Wajib Anggota (Bulanan)',
                category='wajib',
                amount=15000.0,
                due_date='2026-03-31',
                description='Iuran operasional bulanan, perawatan basecamp, dan kas sekretariat.'
            )
            db.session.add(dues1)
            db.session.commit()
        else:
            dues_monthly.amount = 15000.0
            db.session.commit()

            # Buat sample pembayaran lunas untuk Budi
            admin_user = User.query.filter_by(email='admin@gimbal.org').first()
            budi_user = User.query.filter_by(email='budi.pendaki@gmail.com').first()
            if budi_user and admin_user:
                p1 = DuesPayment(
                    dues_id=dues_monthly.id,
                    user_id=budi_user.id,
                    amount_paid=25000.0,
                    bank_name='Bank Mandiri / QRIS',
                    proof_image='/static/pics/sample_proof.jpg',
                    status='approved',
                    notes='Iuran wajib bulan Maret lunas via transfer',
                    verified_by=admin_user.id,
                    verified_at=datetime.utcnow()
                )
                db.session.add(p1)
                db.session.commit()

        # 3. Dokumen Organisasi Internal (CRUD)
        if Document.query.count() == 0:
            doc1 = Document(
                title='AD/ART KPAB GIMBAL (Revisi 2024–2027)',
                category='ad_art',
                description='Anggaran Dasar dan Anggaran Rumah Tangga resmi Generasi Indonesia Menyatu Bersama Alam.',
                file_path='/static/docs/ad_art_gimbal.pdf',
                file_type='pdf',
                file_size_fmt='2.4 MB',
                is_public_to_members=True
            )
            doc2 = Document(
                title='SOP Pendakian & Manajemen Risiko Rimba Gunung',
                category='sop',
                description='Standar operasional prosedur keselamatan kegiatan alam bebas, checklist perlengkapan, dan jalur evakuasi.',
                file_path='/static/docs/sop_pendakian.pdf',
                file_type='pdf',
                file_size_fmt='1.8 MB',
                is_public_to_members=True
            )
            doc3 = Document(
                title='Modul Navigasi Darat, Peta & Kompas Bidik',
                category='materi',
                description='Panduan teknis orientasi medan, resection, intersection, dan membaca kontur topografi.',
                file_path='/static/docs/modul_navigasi.pdf',
                file_type='pdf',
                file_size_fmt='4.1 MB',
                is_public_to_members=True
            )
            db.session.add_all([doc1, doc2, doc3])
            db.session.commit()

        # 4. Kegiatan & Ekspedisi (ambil dari json jika ada)
        if Activity.query.count() == 0:
            kegiatan_file = os.path.join(os.path.dirname(__file__), 'assets', 'data', 'kegiatan.json')
            if os.path.exists(kegiatan_file):
                try:
                    with open(kegiatan_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for item in data.get('kegiatan', []):
                            act = Activity(
                                title=item.get('nama', 'Ekspedisi GIMBAL'),
                                location=item.get('lokasi', 'Jawa Barat'),
                                activity_date=item.get('tanggal', '2026-10-10'),
                                difficulty='Menengah',
                                quota=25,
                                description=item.get('deskripsi', ''),
                                image_url=item.get('image', 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80')
                            )
                            db.session.add(act)
                        db.session.commit()
                except Exception as e:
                    print("Error loading kegiatan.json:", e)
            
            # Default jika kosong
            if Activity.query.count() == 0:
                act1 = Activity(
                    title='Ekspedisi Puncak Rimba Gn. Slamet',
                    location='Jawa Tengah (Via Bambangan)',
                    activity_date='24 - 27 Oktober 2026',
                    difficulty='Ekstrem',
                    quota=20,
                    description='Pendakian resmi tahunan GIMBAL melintasi jalur vegetasi rapat dan batas vegetasi puncak pasir.',
                    image_url='https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80'
                )
                act2 = Activity(
                    title='Aksi Konservasi & Kemah Hijau Rimba',
                    location='Hutan Lindung Gunung Geulis, Bogor',
                    activity_date='14 - 15 November 2026',
                    difficulty='Santai',
                    quota=40,
                    description='Penanaman 500 bibit pohon endemik dan edukasi prinsip Leave No Trace bagi anggota muda.',
                    image_url='https://images.unsplash.com/photo-1510312305653-8ed496efae75?auto=format&fit=crop&w=800&q=80'
                )
                db.session.add_all([act1, act2])
                db.session.commit()

        # 5. Galeri
        if GalleryItem.query.count() == 0:
            galeri_file = os.path.join(os.path.dirname(__file__), 'assets', 'data', 'galeri.json')
            if os.path.exists(galeri_file):
                try:
                    with open(galeri_file, 'r', encoding='utf-8') as f:
                        items = json.load(f)
                        for item in items:
                            gid = item.get('id', '1')
                            caption = item.get('caption', 'Dokumentasi Ekspedisi')
                            g = GalleryItem(
                                title=f"Petualangan {gid}",
                                caption=caption,
                                image_url=f"/assets/pics/galeri/{gid}.jpg",
                                category='Ekspedisi'
                            )
                            db.session.add(g)
                        db.session.commit()
                except Exception as e:
                    print("Error loading galeri.json:", e)
            
            if GalleryItem.query.count() == 0:
                sample_photos = [
                    ("Puncak Tertinggi", "Keluarga besar GIMBAL di batas cakrawala", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80"),
                    ("Menembus Kabut", "Navigasi rimba basah jalur punggungan", "https://images.unsplash.com/photo-1486870591958-9b9d0d1dda99?auto=format&fit=crop&w=800&q=80"),
                    ("Hangatnya Api Unggun", "Malam keakraban dan sharing pengalaman survival", "https://images.unsplash.com/photo-1510312305653-8ed496efae75?auto=format&fit=crop&w=800&q=80"),
                    ("Susur Lembah & Tebing", "Latihan dasar pemanjatan tebing alam", "https://images.unsplash.com/photo-1522163182402-834f871fd851?auto=format&fit=crop&w=800&q=80")
                ]
                for title, cap, url in sample_photos:
                    db.session.add(GalleryItem(title=title, caption=cap, image_url=url, category='Dokumentasi'))
                db.session.commit()

        # 6. Lini Masa Petualang (Posts & Chats)
        if Post.query.count() == 0:
            admin = User.query.filter_by(email='admin@gimbal.org').first()
            budi = User.query.filter_by(email='budi.pendaki@gmail.com').first()
            rian = User.query.filter_by(email='calon.petualang@gmail.com').first()
            if admin and budi:
                p1 = Post(
                    user_id=budi.id,
                    content='Alhamdulillah tim advance GIMBAL berhasil menembus punggungan puncak Gn. Tilongkabila, Bone Bolango! Kondisi jalur di pos 3 agak licin karena kabut basah, tapi pemandangan lembah Gorontalo benar-benar luar biasa. Salam Lestari!',
                    location='Puncak Gn. Tilongkabila, Gorontalo',
                    image_url='https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80'
                )
                p2 = Post(
                    user_id=admin.id,
                    content='Pengumuman: Gladi navigasi darat peta kontur & kompas bidik akan digelar akhir pekan ini di kawasan penyangga Hutan Nantu. Seluruh anggota muda wajib melengkapi data medis dan kontak darurat di profil akun.',
                    location='Sekretariat Pusat, Kota Gorontalo',
                    image_url='https://images.unsplash.com/photo-1510312305653-8ed496efae75?auto=format&fit=crop&w=800&q=80'
                )
                db.session.add_all([p1, p2])
                db.session.commit()

                db.session.add(PostLike(post_id=p1.id, user_id=admin.id))
                if rian:
                    db.session.add(PostLike(post_id=p1.id, user_id=rian.id))
                    db.session.add(PostLike(post_id=p2.id, user_id=budi.id))

                c1 = PostComment(post_id=p1.id, user_id=admin.id, content='Luar biasa tim! Dokumentasikan jalur water point sebelum pos 4 ya.')
                db.session.add(c1)
                if rian:
                    c2 = PostComment(post_id=p1.id, user_id=rian.id, content='Keren sekali pemandangannya abang-abang! Semoga lekas bisa ikut trip ke sana.')
                    db.session.add(c2)
                db.session.commit()

        if ChatMessage.query.count() == 0:
            admin = User.query.filter_by(email='admin@gimbal.org').first()
            budi = User.query.filter_by(email='budi.pendaki@gmail.com').first()
            rian = User.query.filter_by(email='calon.petualang@gmail.com').first()
            if admin and budi:
                chats = [
                    ChatMessage(user_id=budi.id, message='Salam lestari rekan-rekan petualang!'),
                    ChatMessage(user_id=admin.id, message='Lestari! Besok kumpul malam di basecamp Gorontalo jam 20.00 WITA untuk briefing logistik trip.'),
                    ChatMessage(user_id=budi.id, message='Siap Dan, kompor lapangan dan nesting sudah selesai dicek.'),
                ]
                if rian:
                    chats.append(ChatMessage(user_id=rian.id, message='Izin memantau bang, besok saya siap bawa kopi Pinogu Gorontalo untuk teman ngobrol di sekretariat!'))
                    chats.append(ChatMessage(user_id=admin.id, message='Mantap Rian, ditunggu di basecamp!'))
                db.session.add_all(chats)
                db.session.commit()

        # 6. Pengaturan Global & Gateway Midtrans
        SystemSetting.set('monthly_dues_amount', '15000', 'Nominal iuran bulanan wajib keanggotaan (Demo)')
        SystemSetting.set('midtrans_mode', 'sandbox', 'Mode Midtrans: sandbox atau production')
        SystemSetting.set('midtrans_client_key', os.environ.get('MIDTRANS_CLIENT_KEY', 'SB-Mid-client-demo'), 'Midtrans Client Key')
        SystemSetting.set('midtrans_server_key', os.environ.get('MIDTRANS_SERVER_KEY', 'SB-Mid-server-demo'), 'Midtrans Server Key')
        SystemSetting.set('midtrans_merchant_id', os.environ.get('MIDTRANS_MERCHANT_ID', 'GIMBAL-MERCHANT'), 'Midtrans Merchant ID')
        # 7. Master Jabatan Organisasi
        if Position.query.count() == 0:
            default_positions = [
                ('Ketua Umum', 'Pengurus Harian', 1, 'Memimpin jalannya roda organisasi dan bertanggung jawab penuh secara internal & eksternal.'),
                ('Wakil Ketua Umum', 'Pengurus Harian', 2, 'Mendampingi Ketua Umum dan mengoordinasikan bidang internal & eksternal.'),
                ('Sekretaris Jenderal', 'Pengurus Harian', 3, 'Bertanggung jawab atas administrasi, kesekretariatan, dan persuratan resmi.'),
                ('Bendahara Umum', 'Pengurus Harian', 4, 'Mengelola sirkulasi keuangan, pembukuan kas, dan verifikasi iuran organisasi.'),
                ('Kepala Divisi Gunung Hutan', 'Divisi Operasional', 5, 'Mengoordinasikan ekspedisi, navigasi darat, jungle survival, dan pendakian gunung.'),
                ('Kepala Divisi Panjat Tebing', 'Divisi Operasional', 6, 'Mengoordinasikan pelatihan rock climbing, vertical rescue, dan wall climbing.'),
                ('Kepala Divisi Susur Gua (Caving)', 'Divisi Operasional', 7, 'Mengoordinasikan eksplorasi speleologi, pemetaan gua, dan single rope technique.'),
                ('Kepala Divisi Arung Jeram (Rafting)', 'Divisi Operasional', 8, 'Mengoordinasikan river running, keselamatan jeram, dan arung sungai.'),
                ('Kepala Divisi Konservasi & LH', 'Divisi Operasional', 9, 'Mengoordinasikan aksi pelestarian alam, reboisasi, dan advokasi lingkungan hidup.'),
                ('Kepala Divisi Humas & Publikasi', 'Divisi Pendukung', 10, 'Mengelola komunikasi media, publikasi kegiatan, dokumentasi, dan relasi mitra.'),
                ('Kepala Divisi Logistik & Alat', 'Divisi Pendukung', 11, 'Mengelola inventaris perlengkapan outdoor, perawatan alat, dan sarana organisasi.'),
                ('Dewan Penasehat Organisasi', 'Dewan Kehormatan', 12, 'Memberikan arahan, pertimbangan, dan pengawasan strategis bagi pengurus.'),
                ('Anggota Penuh (Reguler)', 'Keanggotaan', 13, 'Anggota resmi ber-NRA yang telah menyelesaikan seluruh tahapan pendidikan dasar.'),
                ('Anggota Muda', 'Keanggotaan', 14, 'Calon anggota yang sedang menempuh masa bimbingan dan pemantapan.')
            ]
            for name, cat, order, desc in default_positions:
                p = Position(name=name, category=cat, order_index=order, description=desc, is_active=True)
                db.session.add(p)
            db.session.commit()

        print(">>> Database GIMBAL seeded successfully!")

if __name__ == '__main__':
    seed_database()
