import re
import json
import os
import requests

DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

# 1. Pola Heuristik Komersial / Penjualan Langsung
COMMERCIAL_HEURISTIC_PATTERNS = [
    r'\bdijual\b',
    r'\bjual\s+(cepat|murah|santai|rugi|second|baru|tenda|carrier|sepatu|jaket|alat|kopi)\b',
    r'\bready\s+stock\b',
    r'\bopen\s+po\b',
    r'\bpre-?order\b',
    r'\b(hubungi|chat|order|pesan|minat)\s*(via)?\s*(wa|whatsapp|dm|pm)\b',
    r'\b(harga|price)\s*[:=]?\s*(rp\.?|\d+)',
    r'\brp\.?\s*\d{2,3}[\.\,]?\d{3}\b',
    r'\bdiskon\s*\d+%',
    r'\b(bisa\s+cod|free\s+ongkir|ongkir)\b',
    r'\b(no\s+minus|kondisi\s*\d+%\s*mulus)\b',
    r'\b(wa|whatsapp)\s*[:=]?\s*08\d{8,12}\b',
]

# 2. Pola Heuristik Pelanggaran Etika Pecinta Alam, SARA, Kata Kotor & Norma
ETHICS_HEURISTIC_PATTERNS = [
    # Kata makian / kasar / SARA / pelecehan
    r'\b(kontol|memek|anjing|bangsat|bajingan|pantek|pepek|tolol|goblok|babi|kampret|asu|brengsek)\b',
    r'\b(lonte|perek|jablay|ngentot|colmek|bokep|porno)\b',
    # Vandalisme & perusakan alam
    r'\b(coret[- ]?coret|pilox|pylox|vandalisme|batu dicoret|pohon diukir|ukir pohon)\b',
    # Perburuan satwa & eksploitasi flora dilindungi (edelweis, anggrek, maleo, anoa)
    r'\bedelweis\b',
    r'\b(petik|ambil|cabut|kantong)\s+(\w+\s+)?(edelweis|anggrek)\b',
    r'\b(tembak|buru|jerat|racun|tangkap)\s+(\w+\s+)?(satwa|burung|anoa|maleo|babirusa|tarsius|rusa)\b',
    # Perusakan habitat / kebakaran hutan / buang sampah
    r'\b(bakar\s+semak|tebang\s+pohon\s+hidup|buang\s+sampah\s+di\s+jurang|tinggal\s+sampah)\b',
    # Narkoba, miras berlebihan di gunung, judi
    r'\b(slot\s+gacor|judi\s+online|zeus\s+slot|sabu[- ]?sabu|ganja|inex|pesta\s+miras\s+di\s+puncak)\b',
    # Pelanggaran aturan pendakian berbahaya / ilegal
    r'\b(jalur\s+ilegal|terobos\s+pos\s+tutup|kabur\s+dari\s+ranger|tanpa\s+simaksi)\b',
]

def get_gemini_api_key():
    """Mengambil Gemini API Key dari SystemSetting DB, Environment, atau default fallback"""
    try:
        from models import SystemSetting
        db_key = SystemSetting.get('gemini_api_key')
        if db_key and db_key.strip():
            return db_key.strip()
    except Exception:
        pass
    return os.environ.get('GEMINI_API_KEY', DEFAULT_GEMINI_KEY).strip()


def check_content_moderation(text_content):
    """
    Evaluasi Moderasi Cerdas Terpadu (Heuristik Cepat + Google Gemini 3.5 Flash Lite):
    1. Kategori KOMERSIAL: Direct selling di linimasa umum tanpa melalui lapak resmi.
    2. Kategori ETIKA & NORMA:
       - Kode etik pencinta alam: vandalisme, memetik edelweis/flora langka, perburuan satwa,
         merusak alam, tebang pohon, kebakaran hutan, jalur pendakian ilegal.
       - Norma sosial & organisasi: kata-kata kotor, makian kasar, permusuhan/SARA,
         pornografi, miras/narkoba, dan judi online.

    Returns:
        (is_blocked: bool, violation_type: str, reason: str)
        violation_type: 'commercial' | 'ethics' | 'none'
    """
    if not text_content or not text_content.strip():
        return False, "none", ""

    text_lower = text_content.lower()

    # Tahap 1: Fast Regex Heuristic Check
    has_commercial_match = any(re.search(pat, text_lower) for pat in COMMERCIAL_HEURISTIC_PATTERNS)
    has_ethics_match = any(re.search(pat, text_lower) for pat in ETHICS_HEURISTIC_PATTERNS)

    # Jika sama sekali tidak ada kata mencurigakan, langsung lolos tanpa buang kuota/latensi
    if not has_commercial_match and not has_ethics_match:
        return False, "none", ""

    # Tahap 2: AI Evaluation dengan Gemini 3.5 Flash Lite
    api_key = get_gemini_api_key()
    if not api_key:
        # Fallback offline jika API key tidak tersedia
        if has_ethics_match:
            return True, "ethics", "Postingan terdeteksi memuat konten yang berpotensi melanggar etika pencinta alam, tata krama, atau norma sosial."
        if has_commercial_match and ('rp' in text_lower or 'wa' in text_lower or 'dijual' in text_lower):
            return True, "commercial", "Postingan terdeteksi memuat penawaran komersial langsung tanpa melalui pendaftaran Lapak Resmi."
        return False, "none", ""

    prompt = f"""Kamu adalah sistem AI kurasi dan moderasi linimasa resmi organisasi pencinta alam KPAB GIMBAL (Provinsi Gorontalo).
Tugasmu: Evaluasi teks postingan anggota berikut terhadap 2 kategori larangan:

1. Kategori 'commercial':
   - Menjual, menawarkan barang/jasa outdoor/makanan secara langsung di linimasa umum tanpa izin lapak resmi.
   - Pengecualian: Cerita pengalaman mendaki yang menyebutkan biaya tiket simaksi, retribusi pos resmi, atau ongkos logistik wajar adalah BUKAN jualan (is_blocked: false).

2. Kategori 'ethics':
   - Melanggar Kode Etik Pencinta Alam: vandalisme (coret batu/pohon/plang pos), memetik edelweis atau flora dilindungi, perburuan satwa liar, membuang sampah/merusak alam, ajakan menerobos jalur ilegal/tanpa simaksi.
   - Melanggar Norma Sosial/Moral/Hukum: makian, kata kotor, ujaran kebencian/SARA, provokasi permusuhan antar organisasi, pornografi/asusila, judi, atau narkoba/miras.

Teks postingan yang dievaluasi:
"{text_content}"

Format balasan HANYA JSON valid tanpa teks pengantar:
{{
  "is_blocked": true/false,
  "violation_type": "commercial" | "ethics" | "none",
  "reason": "Penjelasan sopan, objektif, dan edukatif dalam bahasa Indonesia (maksimal 2 kalimat)"
}}"""

    models_to_try = ['gemini-3.5-flash-lite', 'gemini-3.8-flash', 'gemini-flash-latest']
    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.1
                }
            }
            resp = requests.post(url, json=payload, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data['candidates'][0]['content']['parts'][0]['text']
                parsed = json.loads(raw_text)
                is_blocked = bool(parsed.get('is_blocked', False))
                violation_type = parsed.get('violation_type', 'none')
                reason = parsed.get('reason', '')
                if not is_blocked:
                    violation_type = 'none'
                return is_blocked, violation_type, reason
        except Exception:
            continue

    # Fallback offline jika request AI gagal:
    if has_ethics_match:
        return True, "ethics", "Postingan melanggar kode etik pencinta alam atau norma kesopanan komunitas."
    if has_commercial_match and ('dijual' in text_lower or 'ready stock' in text_lower):
        return True, "commercial", "Postingan memuat penawaran komersial langsung tanpa melalui Lapak Resmi."

    return False, "none", ""


def check_commercial_intent(text_content):
    """
    Helper kompatibilitas mundur untuk pengecekan komersial saja.
    Returns: (is_commercial: bool, reason: str)
    """
    is_blocked, vtype, reason = check_content_moderation(text_content)
    if is_blocked and vtype == 'commercial':
        return True, reason
    return False, ""
