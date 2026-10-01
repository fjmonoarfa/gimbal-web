/**
 * ============================================================================
 * KONFIGURASI PUSAT KPAB GIMBAL (CENTRAL THEME & LAYOUT ENGINE)
 * ============================================================================
 * CUKUP UBAH 2 VARIABEL UTAMA DI BAWAH INI UNTUK MENGUBAH SELURUH WEBSITE:
 * 
 * 1. GIMBAL_SITE_WIDTH:
 *    Mengatur lebar konten seluruh halaman web (landing, dashboard anggota, admin).
 *    Contoh nilai: '70%' | '80%' | '85%' | '1280px'
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
 * 
 * CATATAN TAMPILAN:
 * Seluruh antarmuka secara permanen menggunakan Mode Terang (Bright Mode)
 * default tanpa switch atau konfigurasi dark mode.
 * ============================================================================
 */

const GIMBAL_SITE_WIDTH = (typeof window !== 'undefined' && window.GIMBAL_SERVER_WIDTH) ? window.GIMBAL_SERVER_WIDTH : '85%';
const GIMBAL_THEME_COLOR = (typeof window !== 'undefined' && window.GIMBAL_SERVER_THEME) ? window.GIMBAL_SERVER_THEME : 'orange';

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
// Alias dukungan nama bahasa Indonesia
GIMBAL_THEME_PRESETS.oranye = GIMBAL_THEME_PRESETS.orange;

// ============================================================================
// PENEGAKAN STANDAR MODE TERANG (BRIGHT MODE PERMANEN)
// ============================================================================
function enforceBrightMode() {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;
    root.classList.remove('dark');
    root.setAttribute('data-theme', 'bright');
    root.style.colorScheme = 'light';
    try {
        localStorage.removeItem('gimbal_color_mode');
        localStorage.removeItem('gimbal_last_config_default');
    } catch (e) {}
}

// Stubs kompatibilitas aman
window.toggleGimbalColorMode = function () { enforceBrightMode(); };
window.setGimbalColorMode = function () { enforceBrightMode(); };
window.getActiveColorMode = function () { return 'bright'; };

// Helper untuk menyuntikkan override CSS dinamis ke DOM secara instan
function applyDynamicThemeColors(selectedTheme) {
    if (typeof document === 'undefined') return;
    const shades = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
    let css = '/* KPAB GIMBAL - Auto Generated Monotone Theme Overrides (Bright Mode) */\n';

    shades.forEach(function (s) {
        const val = selectedTheme[s];
        if (!val) return;
        // Text
        css += `.text-orange-${s}, .text-brand-${s} { color: ${val} !important; }\n`;
        // Background
        css += `.bg-orange-${s}, .bg-brand-${s} { background-color: ${val} !important; }\n`;
        // Border
        css += `.border-orange-${s}, .border-brand-${s} { border-color: ${val} !important; }\n`;
    });

    // Hover states
    if (selectedTheme[400]) {
        css += `.hover\\:text-orange-400:hover, .hover\\:text-brand-400:hover { color: ${selectedTheme[400]} !important; }\n`;
    }
    if (selectedTheme[500]) {
        css += `.hover\\:border-orange-500:hover, .hover\\:border-brand-500:hover { border-color: ${selectedTheme[500]} !important; }\n`;
    }
    if (selectedTheme[600]) {
        css += `.hover\\:text-orange-600:hover, .hover\\:text-brand-600:hover { color: ${selectedTheme[600]} !important; }\n`;
        css += `.hover\\:bg-orange-600:hover, .hover\\:bg-brand-600:hover { background-color: ${selectedTheme[600]} !important; }\n`;
    }
    if (selectedTheme[700]) {
        css += `.hover\\:text-orange-700:hover, .hover\\:text-brand-700:hover { color: ${selectedTheme[700]} !important; }\n`;
        css += `.hover\\:bg-orange-700:hover, .hover\\:bg-brand-700:hover { background-color: ${selectedTheme[700]} !important; }\n`;
    }
    if (selectedTheme[800]) {
        css += `.hover\\:bg-orange-800:hover, .hover\\:bg-brand-800:hover { background-color: ${selectedTheme[800]} !important; }\n`;
    }

    // Gradient stops otomatis agar elemen ber-gradasi mengikuti warna tema aktif
    shades.forEach(function (s) {
        const val = selectedTheme[s];
        if (!val) return;
        css += `.from-orange-${s}, .from-brand-${s} { --tw-gradient-from: ${val} var(--tw-gradient-from-position) !important; --tw-gradient-to: rgb(255 255 255 / 0) var(--tw-gradient-to-position) !important; --tw-gradient-stops: var(--tw-gradient-from), var(--tw-gradient-to) !important; }\n`;
        css += `.to-orange-${s}, .to-brand-${s} { --tw-gradient-to: ${val} var(--tw-gradient-to-position) !important; }\n`;
    });

    // Tombol & Komponen Brand Universal
    if (selectedTheme[600]) {
        css += `.btn-brand-primary { background-color: ${selectedTheme[600]} !important; color: #ffffff !important; }\n`;
        css += `.btn-brand-primary:hover { background-color: ${selectedTheme[700] || selectedTheme[600]} !important; }\n`;
        css += `.text-brand-primary { color: ${selectedTheme[600]} !important; }\n`;
        css += `.bg-brand-primary { background-color: ${selectedTheme[600]} !important; }\n`;
    }

    // Top Navigation Bar, KTA Card, & Hero (FLAT WARNA TEMA MONOTONE - TANPA GRADIENT)
    if (selectedTheme[600]) {
        css += `.top-navbar-theme, nav.top-navbar-theme, header.top-navbar-theme { background: ${selectedTheme[600]} !important; background-color: ${selectedTheme[600]} !important; border-bottom: 1px solid rgba(255, 255, 255, 0.22) !important; color: #ffffff !important; }\n`;
        css += `.kta-card { background: ${selectedTheme[600]} !important; background-color: ${selectedTheme[600]} !important; color: #ffffff !important; }\n`;
        css += `.member-hero-banner { background: ${selectedTheme[600]} !important; background-color: ${selectedTheme[600]} !important; color: #ffffff !important; }\n`;
    }

    // Section Call To Action & Footer Komunitas (100% Mengikuti Tema Monotone Aktif)
    if (selectedTheme[950] && selectedTheme[900]) {
        const glowColor = selectedTheme.rgb600 ? `rgba(${selectedTheme.rgb600}, 0.28)` : selectedTheme[600];
        css += `.cta-theme-section { background: radial-gradient(circle at 50% 25%, ${glowColor} 0%, transparent 65%), linear-gradient(135deg, ${selectedTheme[950]} 0%, ${selectedTheme[900]} 50%, #070a0f 100%) !important; }\n`;
        css += `.footer-theme-bg { background: linear-gradient(180deg, ${selectedTheme[950]} 0%, #070a0f 100%) !important; border-top: 1px solid ${selectedTheme[800] || selectedTheme[700]} !important; }\n`;
        css += `.kode-etik-section { background: radial-gradient(circle at center, ${selectedTheme[900]} 0%, #080a0f 100%) !important; }\n`;
        css += `.piagam-border { border-color: ${selectedTheme[500]} !important; background: radial-gradient(circle at center, ${selectedTheme[950]}, #080a0f) !important; }\n`;
    }

    // Variasi Transparansi Penting
    if (selectedTheme.rgb500) {
        css += `.bg-orange-500\\/30, .bg-brand-500\\/30 { background-color: rgba(${selectedTheme.rgb500}, 0.3) !important; }\n`;
        css += `.border-orange-500\\/50, .border-brand-500\\/50 { border-color: rgba(${selectedTheme.rgb500}, 0.5) !important; }\n`;
        css += `.border-orange-500\\/60, .border-brand-500\\/60 { border-color: rgba(${selectedTheme.rgb500}, 0.6) !important; }\n`;
    }
    if (selectedTheme.rgb600) {
        css += `.bg-orange-600\\/30, .bg-brand-600\\/30 { background-color: rgba(${selectedTheme.rgb600}, 0.3) !important; }\n`;
        css += `.border-orange-600\\/50, .border-brand-600\\/50 { border-color: rgba(${selectedTheme.rgb600}, 0.5) !important; }\n`;
    }
    if (selectedTheme.rgb700) {
        css += `.bg-orange-700\\/60, .bg-brand-700\\/60 { background-color: rgba(${selectedTheme.rgb700}, 0.6) !important; }\n`;
        css += `.hover\\:bg-orange-800\\/50:hover { background-color: rgba(${selectedTheme.rgb700}, 0.5) !important; }\n`;
        css += `.hover\\:bg-orange-800\\/60:hover { background-color: rgba(${selectedTheme.rgb700}, 0.6) !important; }\n`;
    }
    if (selectedTheme.rgb800) {
        css += `.bg-orange-800\\/80, .bg-brand-800\\/80 { background-color: rgba(${selectedTheme.rgb800}, 0.8) !important; }\n`;
        css += `.border-orange-800\\/40, .border-brand-800\\/40 { border-color: rgba(${selectedTheme.rgb800}, 0.4) !important; }\n`;
        css += `.border-orange-800\\/50, .border-brand-800\\/50 { border-color: rgba(${selectedTheme.rgb800}, 0.5) !important; }\n`;
        css += `.border-orange-800\\/60, .border-brand-800\\/60 { border-color: rgba(${selectedTheme.rgb800}, 0.6) !important; }\n`;
    }
    if (selectedTheme.rgb900) {
        css += `.bg-orange-900\\/50, .bg-brand-900\\/50 { background-color: rgba(${selectedTheme.rgb900}, 0.5) !important; }\n`;
        css += `.bg-orange-900\\/60, .bg-brand-900\\/60 { background-color: rgba(${selectedTheme.rgb900}, 0.6) !important; }\n`;
        css += `.bg-orange-900\\/80, .bg-brand-900\\/80 { background-color: rgba(${selectedTheme.rgb900}, 0.8) !important; }\n`;
    }
    if (selectedTheme.rgb950) {
        css += `.bg-orange-950\\/80, .bg-brand-950\\/80 { background-color: rgba(${selectedTheme.rgb950}, 0.8) !important; }\n`;
        css += `.bg-orange-950\\/60, .bg-brand-950\\/60 { background-color: rgba(${selectedTheme.rgb950}, 0.6) !important; }\n`;
    }

    let styleEl = document.getElementById('gimbal-dynamic-theme');
    if (!styleEl) {
        styleEl = document.createElement('style');
        styleEl.id = 'gimbal-dynamic-theme';
        const target = document.head || document.documentElement;
        if (target) target.appendChild(styleEl);
    }
    styleEl.textContent = css;
}

// Inisialisasi tema aktif
(function initGimbalTheme() {
    const selectedTheme = GIMBAL_THEME_PRESETS[GIMBAL_THEME_COLOR] || GIMBAL_THEME_PRESETS.orange;
    const root = document.documentElement;

    // 1. Terapkan variabel CSS lebar konten ke :root
    root.style.setProperty('--site-content-width', GIMBAL_SITE_WIDTH);

    // 2. Terapkan warna brand dan orange ke variabel CSS :root
    const shades = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
    const cleanPalette = {};
    shades.forEach(function (shade) {
        if (selectedTheme[shade]) {
            cleanPalette[shade] = selectedTheme[shade];
            root.style.setProperty('--brand-' + shade, selectedTheme[shade]);
            root.style.setProperty('--orange-' + shade, selectedTheme[shade]);
        }
        if (selectedTheme['rgb' + shade]) {
            root.style.setProperty('--brand-' + shade + '-rgb', selectedTheme['rgb' + shade]);
            root.style.setProperty('--orange-' + shade + '-rgb', selectedTheme['rgb' + shade]);
        }
    });

    // 3. Terapkan Bright Mode permanen langsung pada saat init (mencegah kedipan dan dark mode)
    enforceBrightMode();

    // 4. Suntikkan aturan CSS dinamis agar seluruh kelas text-orange-*, bg-orange-*, border-orange-* langsung berganti warna
    applyDynamicThemeColors(selectedTheme);

    // 5. Hubungkan dengan Tailwind CSS Configuration (dibaca otomatis oleh CDN)
    const twConfig = {
        theme: {
            extend: {
                colors: {
                    brand: cleanPalette,
                    orange: cleanPalette
                },
                width: {
                    site: 'var(--site-content-width, 70%)',
                },
                maxWidth: {
                    site: 'var(--site-content-width, 70%)',
                }
            }
        }
    };
    window.tailwind = window.tailwind || {};
    window.tailwind.config = twConfig;
    if (typeof tailwind !== 'undefined') {
        try {
            tailwind.config = twConfig;
        } catch (e) { }
    }

    // 6. Listener sinkronisasi saat DOM selesai dimuat / pertukaran HTMX
    if (typeof document !== 'undefined') {
        const syncState = function () {
            enforceBrightMode();
            applyDynamicThemeColors(selectedTheme);
        };
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', syncState);
        } else {
            syncState();
        }
        document.addEventListener('htmx:afterSwap', syncState);
    }

    // 7. Ekspos fungsi global dinamis untuk live preview instan di panel admin
    window.applyGimbalThemeDynamic = function(themeColor, siteWidth) {
        if (siteWidth) {
            document.documentElement.style.setProperty('--site-content-width', siteWidth);
            window.GIMBAL_SERVER_WIDTH = siteWidth;
        }
        if (themeColor && GIMBAL_THEME_PRESETS[themeColor]) {
            window.GIMBAL_SERVER_THEME = themeColor;
            const targetTheme = GIMBAL_THEME_PRESETS[themeColor];
            const root = document.documentElement;
            const shadesList = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
            shadesList.forEach(function (shade) {
                if (targetTheme[shade]) {
                    root.style.setProperty('--brand-' + shade, targetTheme[shade]);
                    root.style.setProperty('--orange-' + shade, targetTheme[shade]);
                }
                if (targetTheme['rgb' + shade]) {
                    root.style.setProperty('--brand-' + shade + '-rgb', targetTheme['rgb' + shade]);
                    root.style.setProperty('--orange-' + shade + '-rgb', targetTheme['rgb' + shade]);
                }
            });
            applyDynamicThemeColors(targetTheme);
        }
    };
})();
