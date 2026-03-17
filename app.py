from waitress import serve
from datetime import timedelta
from flask import Flask
from config import SECRET_KEY, SESSION_TIMEOUT_MINUTES
from database import init_db, close_db

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['TEMPLATES_AUTO_RELOAD'] = True

app.teardown_appcontext(close_db)


# Jinja filter: format date → dd/mm/yyyy
@app.template_filter('fmtd')
def fmtd_filter(d):
    if d is None: return ''
    s = str(d)[:10]
    if '-' in s:
        p = s.split('-')
        return f'{p[2]}/{p[1]}/{p[0]}'
    return s

# Also make it available as a function in templates
app.jinja_env.globals['fmtd'] = fmtd_filter

@app.template_filter('fmtiso')
def fmtiso_filter(d):
    """Format date → yyyy-mm-dd for <input type=date>"""
    if d is None: return ''
    return str(d)[:10]

app.jinja_env.globals['fmtiso'] = fmtiso_filter


@app.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# Blueprints
from auth.routes import bp as auth_bp;       app.register_blueprint(auth_bp)
from dashboard import bp as dash_bp;         app.register_blueprint(dash_bp)
from admin import bp as admin_bp;            app.register_blueprint(admin_bp)
from analytics import bp as analytics_bp;    app.register_blueprint(analytics_bp)

# Report blueprints (mỗi báo cáo tự viết = 1 blueprint)
from reports import get_all_blueprints
for slug, report_bp in get_all_blueprints():
    app.register_blueprint(report_bp)

init_db()

if __name__ == '__main__':
    print('=' * 50)
    print('  VietAnh BI Dashboard')
    print('  http://localhost:5000')
    print('=' * 50)
    serve(app, host='0.0.0.0', port=5000, threads=8)  # ← thêm app vào đây