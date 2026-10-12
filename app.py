import csv
import io
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import secrets

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')
USERNAME = os.getenv('APP_USERNAME', 'admin')
PASSWORD = os.getenv('APP_PASSWORD', '')
SECRET = os.getenv('SESSION_SECRET', '')
if not PASSWORD or not SECRET or PASSWORD.startswith('change-this') or SECRET.startswith('replace-with'):
    raise RuntimeError('Set APP_PASSWORD and SESSION_SECRET in .env')
DB = Path(os.getenv('DATABASE_PATH', str(BASE / 'reports.db')))
DB.parent.mkdir(parents=True, exist_ok=True)
app = FastAPI(title='Social Media Reporting System')
app.add_middleware(SessionMiddleware, secret_key=SECRET, https_only=os.getenv('COOKIE_SECURE', 'false').lower() == 'true', same_site='lax')
templates = Jinja2Templates(directory=str(BASE / 'templates'))
PLATFORMS = {'instagram': 'instagram.com', 'facebook': 'facebook.com', 'tiktok': 'tiktok.com', 'x': 'x.com'}

@contextmanager
def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

with db() as conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT NOT NULL, url TEXT NOT NULL, post_name TEXT NOT NULL, post_date TEXT NOT NULL, views INTEGER NOT NULL DEFAULT 0, reach INTEGER NOT NULL DEFAULT 0, likes INTEGER NOT NULL DEFAULT 0, comments INTEGER NOT NULL DEFAULT 0, shares INTEGER NOT NULL DEFAULT 0, followers_gained INTEGER NOT NULL DEFAULT 0, ad_spend REAL NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT 'manual', created_at TEXT NOT NULL)''')

def logged_in(request):
    return request.session.get('user') == USERNAME

def require_login(request):
    if not logged_in(request):
        raise HTTPException(401, 'Please log in')

def platform_for_url(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname:
        raise ValueError('Tumia URL ya https://')
    host = parsed.hostname.lower()
    if host in ('twitter.com', 'www.twitter.com'):
        return 'x'
    for name, domain in PLATFORMS.items():
        if host == domain or host.endswith('.' + domain):
            return name
    if host in ('fb.watch', 'www.fb.watch'):
        return 'facebook'
    raise ValueError('Link lazima iwe ya Instagram, Facebook, TikTok au X.')

def summary(rows):
    result = {k: sum(row[k] for row in rows) for k in ('views','reach','likes','comments','shares','followers_gained','ad_spend')}
    result['posts'] = len(rows)
    result['engagements'] = result['likes'] + result['comments'] + result['shares']
    result['engagement_rate'] = round(result['engagements'] / result['reach'] * 100, 2) if result['reach'] else None
    result['cost_per_engagement'] = round(result['ad_spend'] / result['engagements'], 2) if result['engagements'] else None
    return result

@app.get('/login', response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, 'login.html', {'error': None})

@app.post('/login')
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if secrets.compare_digest(username, USERNAME) and secrets.compare_digest(password, PASSWORD):
        request.session.clear()
        request.session['user'] = USERNAME
        return RedirectResponse('/', status_code=303)
    return templates.TemplateResponse(request, 'login.html', {'error': 'Username au password si sahihi.'}, status_code=401)

@app.post('/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse('/login', status_code=303)

@app.get('/', response_class=HTMLResponse)
def home(request: Request, platform: str = '', start: str = '', end: str = '', q: str = ''):
    if not logged_in(request):
        return RedirectResponse('/login', status_code=303)
    with db() as conn:
        rows = conn.execute('SELECT * FROM posts ORDER BY post_date DESC, id DESC').fetchall()
    rows = [dict(r) for r in rows if (not platform or r['platform'] == platform) and (not start or r['post_date'] >= start) and (not end or r['post_date'] <= end) and (not q or q.lower() in (r['post_name'] + ' ' + r['url'] + ' ' + r['notes']).lower())]
    return templates.TemplateResponse(request, 'dashboard.html', {'rows': rows, 'stats': summary(rows), 'platform': platform, 'start': start, 'end': end, 'q': q, 'message': request.query_params.get('message', '')})

@app.post('/posts')
def add_post(request: Request, url: str = Form(...), post_name: str = Form(...), post_date: str = Form(...), views: int = Form(0), reach: int = Form(0), likes: int = Form(0), comments: int = Form(0), shares: int = Form(0), followers_gained: int = Form(0), ad_spend: float = Form(0), notes: str = Form('')):
    require_login(request)
    try:
        platform = platform_for_url(url.strip())
        datetime.strptime(post_date, '%Y-%m-%d')
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if any(v < 0 for v in (views, reach, likes, comments, shares, followers_gained, ad_spend)):
        raise HTTPException(400, 'Takwimu na gharama haziwezi kuwa hasi.')
    with db() as conn:
        conn.execute('INSERT INTO posts (platform,url,post_name,post_date,views,reach,likes,comments,shares,followers_gained,ad_spend,notes,source,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (platform,url.strip(),post_name.strip()[:160],post_date,views,reach,likes,comments,shares,followers_gained,ad_spend,notes[:1000],'manual',datetime.now(timezone.utc).isoformat()))
    return RedirectResponse('/?message=Post+saved', status_code=303)

@app.post('/posts/{post_id}/delete')
def delete_post(request: Request, post_id: int):
    require_login(request)
    with db() as conn:
        conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    return RedirectResponse('/?message=Post+deleted', status_code=303)

@app.get('/export.csv')
def export(request: Request, platform: str = '', start: str = '', end: str = ''):
    require_login(request)
    with db() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM posts ORDER BY post_date DESC').fetchall()]
    rows = [r for r in rows if (not platform or r['platform'] == platform) and (not start or r['post_date'] >= start) and (not end or r['post_date'] <= end)]
    stream = io.StringIO()
    fields = ['platform','post_name','post_date','url','views','reach','likes','comments','shares','followers_gained','ad_spend','notes','source']
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    content = '\ufeff' + stream.getvalue()
    return StreamingResponse(iter([content.encode('utf-8')]), media_type='text/csv; charset=utf-8', headers={'Content-Disposition':'attachment; filename="social-media-report.csv"'})

@app.post('/inspect-link')
def inspect_link(request: Request, url: str = Form(...)):
    require_login(request)
    try:
        platform = platform_for_url(url.strip())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {'platform': platform, 'url': url.strip(), 'status': 'manual_required', 'message': 'Link imetambuliwa. Kuvuta metrics kiotomatiki kunahitaji API integration na ruhusa za mtandao husika.'}
from fastapi.staticfiles import StaticFiles
app.mount('/static', StaticFiles(directory=str(BASE / 'static')), name='static')
