import os
import json
from datetime import datetime
from flask import Flask
from models import db, User, Dues, DuesPayment, Document, Activity, GalleryItem

def create_sample_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gimbal.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def seed_database():
    app = create_sample_app()
    with app.app_context():
        db.create_all()
        
        # 1. Admin & Users
        if not User.query.filter_by(email='admin@gimbal.org').first():
            admin = User(
                email='admin@gimbal.org',
                name='Ketua Umum GIMBAL',
                role='admin',
                status='active',
                nra='R-01-26',
                nra_year=26,
                nra_sequence=1,
                phone='081234567890',
                birth_place='Bandung',
                birth_date='1995-05-12',
                address='Sekretariat KPAB GIMBAL, Jawa Barat',
                blood_type='O',
                medical_history='Tidak ada riwayat alergi',
                emergency_name='Siti Rahmawati',
                emergency_relation='Keluarga',
                emergency_phone='081298765432',
                avatar='https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80',
                approved_at=datetime.utcnow()
            )
            db.session.add(admin)

        if not User.query.filter_by(email='budi.pendaki@gmail.com').first():
            member1 = User(
                email='budi.pendaki@gmail.com',
                name='Budi Santoso',
                role='member',
                status='active',
                nra='R-02-26',
                nra_year=26,
                nra_sequence=2,
                phone='081345678901',
                birth_place='Jakarta',
                birth_date='1998-08-17',
                address='Jl. Rimba No. 12, Bogor',
                blood_type='A',
                medical_history='Alergi dingin ringan',
                emergency_name='Dewi Lestari',
                emergency_relation='Ibu',
                emergency_phone='081398761234',
                avatar='https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=200&q=80',
                approved_at=datetime.utcnow()
            )
            db.session.add(member1)

        if not User.query.filter_by(email='calon.petualang@gmail.com').first():
            pending_user = User(
                email='calon.petualang@gmail.com',
                name='Rian Pratama',
                role='member',
                status='pending',
                nra=None,
                phone='081567890123',
                birth_place='Semarang',
                birth_date='2001-11-20',
                address='Jl. Lereng Merbabu No. 45, Salatiga',
                blood_type='B',
                medical_history='Pernah cedera engkel kanan (sudah pulih)',
                emergency_name='Bambang Supriyanto',
                emergency_relation='Ayah',
                emergency_phone='081512345678',
                avatar='https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=200&q=80'
            )
            db.session.add(pending_user)

        db.session.commit()

        # 2. Master Iuran
        if Dues.query.count() == 0:
            dues1 = Dues(
                title='Iuran Kas Wajib Maret 2026',
                category='wajib',
                amount=25000.0,
                due_date='2026-03-31',
                description='Iuran operasional bulanan, perawatan basecamp, dan kas sekretariat.'
            )
            dues2 = Dues(
                title='Iuran Perawatan Tenda & Alat Outdoor',
                category='kegiatan',
                amount=50000.0,
                due_date='2026-04-15',
                description='Pemeliharaan tenda dome, waterproofing flysheet, dan tali karmantel.'
            )
            db.session.add_all([dues1, dues2])
            db.session.commit()

            # Buat sample pembayaran lunas untuk Budi
            admin_user = User.query.filter_by(email='admin@gimbal.org').first()
            budi_user = User.query.filter_by(email='budi.pendaki@gmail.com').first()
            if budi_user and admin_user:
                p1 = DuesPayment(
                    dues_id=dues1.id,
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

        print(">>> Database GIMBAL seeded successfully!")

if __name__ == '__main__':
    seed_database()
