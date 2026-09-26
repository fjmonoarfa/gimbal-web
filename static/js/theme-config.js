/**
 * ============================================================================
 * KONFIGURASI PUSAT KPAB GIMBAL (CENTRAL THEME & LAYOUT ENGINE)
 * ============================================================================
 * CUKUP UBAH 2 VARIABEL UTAMA DI BAWAH INI UNTUK MENGUBAH SELURUH WEBSITE:
 * 
 * 1. GIMBAL_SITE_WIDTH:
 *    Mengatur lebar konten seluruh halaman web (landing, dashboard anggota, admin).
 *    Contoh nilai: '85%' | '80%' | '90%' | '1280px'
 * 
 * 2. GIMBAL_THEME_COLOR:
 *    Mengatur monotone warna utama organisasi.
 *    Pilihan preset tahunan:
 *    - 'orange'   : Oranye GIMBAL resmi (Default)
 *    - 'emerald'  : Hijau Rimba & Konservasi
 *    - 'blue'     : Biru Tirta & Arung Jeram
 *    - 'amber'    : Kuning Emas Petualang
 *    - 'rose'     : Merah Terracotta Tebing
 *    - 'teal'     : Toska Danau Gunung
 * ============================================================================
 */

const GIMBAL_SITE_WIDTH = '85%';    /* <-- 1 VARIABEL UTAMA: LEBAR KONTEN (85%) */
const GIMBAL_THEME_COLOR = 'orange'; /* <-- 1 VARIABEL UTAMA: WARNA TAHUNAN */

/**
 * PALET MONOTONE PRESET TAHUNAN
 */
const GIMBAL_THEME_PRESETS = {
    orange: {
        50: '#fff7ed',
        100: '#ffedd5',
        200: '#fed7aa',
        300: '#fdba74',
        400: '#fb923c',
        500: '#f97316',
        600: '#ea580c', // Oranye Logo GIMBAL
        700: '#c2410c',
        800: '#9a3412',
        900: '#7c2d12',
        950: '#431407',
        rgb500: '249, 115, 22',
        rgb600: '234, 88, 12',
        rgb700: '194, 65, 12',
        rgb800: '154, 52, 18',
        rgb900: '124, 45, 18',
        rgb950: '67, 20, 7',
    },
    emerald: {
        50: '#ecfdf5',
        100: '#d1fae5',
        200: '#a7f3d0',
        300: '#6ee7b7',
        400: '#34d399',
        500: '#10b981',
        600: '#059669',
        700: '#047857',
        800: '#065f46',
        900: '#064e3b',
        950: '#022c22',
        rgb500: '16, 185, 129',
        rgb600: '5, 150, 105',
        rgb700: '4, 120, 87',
        rgb800: '6, 95, 70',
        rgb900: '6, 78, 59',
        rgb950: '2, 44, 34',
    },
    blue: {
        50: '#eff6ff',
        100: '#dbeafe',
        200: '#bfdbfe',
        300: '#93c5fd',
        400: '#60a5fa',
        500: '#3b82f6',
        600: '#2563eb',
        700: '#1d4ed8',
        800: '#1e40af',
        900: '#1e3a8a',
        950: '#172554',
        rgb500: '59, 130, 246',
        rgb600: '37, 99, 235',
        rgb700: '29, 78, 216',
        rgb800: '30, 64, 175',
        rgb900: '30, 58, 138',
        rgb950: '23, 37, 84',
    },
    amber: {
        50: '#fffbeb',
        100: '#fef3c7',
        200: '#fde68a',
        300: '#fcd34d',
        400: '#fbbf24',
        500: '#f59e0b',
        600: '#d97706',
        700: '#b45309',
        800: '#92400e',
        900: '#78350f',
        950: '#451a03',
        rgb500: '245, 158, 11',
        rgb600: '217, 119, 6',
        rgb700: '180, 83, 9',
        rgb800: '146, 64, 14',
        rgb900: '120, 53, 15',
        rgb950: '69, 26, 3',
    },
    rose: {
        50: '#fff1f2',
        100: '#ffe4e6',
        200: '#fecdd3',
        300: '#fda4af',
        400: '#fb7185',
        500: '#f43f5e',
        600: '#e11d48',
        700: '#be123c',
        800: '#9f1239',
        900: '#881337',
        950: '#4c0519',
        rgb500: '244, 63, 94',
        rgb600: '225, 29, 72',
        rgb700: '190, 18, 60',
        rgb800: '159, 18, 57',
        rgb900: '136, 19, 55',
        rgb950: '76, 5, 25',
    },
    teal: {
        50: '#f0fdfa',
        100: '#ccfbf1',
        200: '#99f6e4',
        300: '#5eead4',
        400: '#2dd4bf',
        500: '#14b8a6',
        600: '#0d9488',
        700: '#0f766e',
        800: '#115e59',
        900: '#134e4a',
        950: '#042f2e',
        rgb500: '20, 184, 166',
        rgb600: '13, 148, 136',
        rgb700: '15, 118, 110',
        rgb800: '17, 94, 89',
        rgb900: '19, 78, 74',
        rgb950: '4, 47, 46',
    }
};

// Inisialisasi tema aktif
(function initGimbalTheme() {
    const selectedTheme = GIMBAL_THEME_PRESETS[GIMBAL_THEME_COLOR] || GIMBAL_THEME_PRESETS.orange;
    const root = document.documentElement;

    // 1. Terapkan variabel CSS ke :root
    root.style.setProperty('--site-content-width', GIMBAL_SITE_WIDTH);

    const shades = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
    shades.forEach(function(shade) {
        if (selectedTheme[shade]) {
            root.style.setProperty('--brand-' + shade, selectedTheme[shade]);
        }
        if (selectedTheme['rgb' + shade]) {
            root.style.setProperty('--brand-' + shade + '-rgb', selectedTheme['rgb' + shade]);
        }
    });

    // 2. Hubungkan dengan Tailwind CSS Configuration (dibaca otomatis oleh CDN)
    window.tailwind = window.tailwind || {};
    window.tailwind.config = {
        theme: {
            extend: {
                colors: {
                    brand: selectedTheme,
                    orange: selectedTheme // Otomatis meng-override kelas orange-* sesuai tema tahunan!
                },
                width: {
                    site: 'var(--site-content-width, 85%)',
                },
                maxWidth: {
                    site: 'var(--site-content-width, 85%)',
                }
            }
        }
    };
})();
