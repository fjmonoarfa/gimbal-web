from functools import wraps
from flask import request, redirect, session, make_response, render_template, render_template_string
from models import db, User, now_wita, WITA_TZ

def get_current_user():
    """Mengambil user aktif dari session."""
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.headers.get('HX-Request'):
                return "<script>window.location.href = '/';</script>"
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_admin:
            if request.headers.get('HX-Request'):
                return "<div class='p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs font-bold'>Akses Ditolak: Hanya Pengurus Admin.</div>"
            return redirect('/member/dashboard')
        return f(*args, **kwargs)
    return decorated

def check_member_access(user):
    """
    Memastikan hanya anggota aktif yang berhak masuk ke linimasa / dashboard / KTA.
    Calon anggota pending wajib menyetujui kode etik, melengkapi biodata dan menyelesaikan iuran keanggotaan.
    """
    if not user:
        return redirect('/login')
    if user.is_admin:
        return None
    if not user.consent_agreed and user.status != 'active':
        if request.headers.get('HX-Request'):
            return "<script>window.location.href = '/member/onboarding-consent';</script>"
        return redirect('/member/onboarding-consent')
    if not user.is_profile_complete:
        if request.headers.get('HX-Request'):
            return "<script>window.location.href = '/member/complete-profile';</script>"
        return redirect('/member/complete-profile')
    if user.status != 'active':
        if request.headers.get('HX-Request'):
            return "<script>window.location.href = '/member/onboarding-status';</script>"
        return redirect('/member/onboarding-status')
    return None

def get_clean_shell_url():
    """Mengembalikan URL path bersih tanpa tanda tanya kosong di akhir"""
    url = request.full_path or '/'
    if url.endswith('?'):
        url = url[:-1]
    return url or '/'


def render_gimbal_content(content_html, active_page=None, alert_msg=None):
    """
    Core Multi-Layer HTMX Rendering Engine:
    1. Direct browser hit (bukan HTMX): Kembalikan Layer 1 (index.html) sehingga View Source di manapun selalu index.html!
    2. HTMX targeting #app-shell: Kembalikan Layer 2 (shell.html) yang membungkus konten ke dalam main-content.
    3. Normal HTMX targeting #main-content: Kembalikan Layer 3 (content_html) secara instan tanpa reload shell.
    """
    user = get_current_user()
    pending_count = User.query.filter_by(status='pending').count() if (user and user.is_admin) else 0

    if request.headers.get('HX-Request'):
        if request.headers.get('HX-Target') == 'app-shell':
            resp = make_response(render_template(
                'shell.html',
                active_page=active_page or '',
                active_macro_content=content_html,
                current_user=user,
                user=user,
                pending_count=pending_count,
                alert_msg=alert_msg
            ))
            resp.headers['X-Active-Page'] = active_page or ''
            resp.headers['Vary'] = 'HX-Request, HX-Target'
            resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            return resp

        resp = make_response(content_html)
        resp.headers['X-Active-Page'] = active_page or ''
        resp.headers['Vary'] = 'HX-Request, HX-Target'
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        return resp

    # Direct browser GET / View Source: SELALU kembalikan Layer 1 (index.html)
    resp = make_response(render_template('index.html', shell_url=get_clean_shell_url()))
    resp.headers['Vary'] = 'HX-Request, HX-Target'
    return resp


def render_gimbal_page(macro_file, macro_name, data_context, active_page=None, alert_msg=None):
    """
    Merender halaman berbasis Jinja2 Macro (admin & member pages)
    """
    if not request.headers.get('HX-Request'):
        return render_template('index.html', shell_url=get_clean_shell_url())

    user = get_current_user()
    pending_count = User.query.filter_by(status='pending').count() if (user and user.is_admin) else 0

    data_context.update({
        'user': user,
        'current_user': user,
        'pending_count': pending_count,
        'active_page': active_page or macro_name
    })

    tmpl = f"{{% import '{macro_file}' as pages with context %}}{{{{ pages.{macro_name}(data) }}}}"
    macro_html = render_template_string(tmpl, data=data_context, current_user=user, user=user)

    return render_gimbal_content(macro_html, active_page=active_page or macro_name, alert_msg=alert_msg)


def render_gimbal_template(template_name, context=None, active_page=None, alert_msg=None):
    """
    Merender halaman berbasis template partial (landing, login, complete_profile, onboarding_status, verify_kta)
    """
    if not request.headers.get('HX-Request'):
        return render_template('index.html', shell_url=get_clean_shell_url())

    context = context or {}
    user = get_current_user()
    pending_count = User.query.filter_by(status='pending').count() if (user and user.is_admin) else 0

    context.update({
        'user': user,
        'current_user': user,
        'pending_count': pending_count,
        'active_page': active_page or template_name
    })

    content_html = render_template(template_name, **context)
    return render_gimbal_content(content_html, active_page=active_page or template_name, alert_msg=alert_msg)


def render_gimbal_modal(modal_type, context=None, active_page=None, alert_msg=None):
    """
    Merender modal/halaman berbasis components/modals.html
    Bisa berupa modal popup (is_modal=True jika HX-Target == 'modal-container')
    atau halaman penuh di dalam #main-content (is_modal=False).
    """
    if not request.headers.get('HX-Request'):
        return render_template('index.html', shell_url=get_clean_shell_url())

    context = context or {}
    user = get_current_user()
    pending_count = User.query.filter_by(status='pending').count() if (user and user.is_admin) else 0

    hx_target = request.headers.get('HX-Target', '')
    is_modal = (hx_target == 'modal-container')

    context.update({
        'user': user,
        'current_user': user,
        'pending_count': pending_count,
        'active_page': active_page or modal_type,
        'modal_type': modal_type,
        'is_modal': is_modal
    })

    content_html = render_template('components/modals.html', **context)
    if is_modal:
        # Jika memang diminta ke modal-container, langsung kembalikan konten modalnya
        return content_html

    return render_gimbal_content(content_html, active_page=active_page or modal_type, alert_msg=alert_msg)

