import os, json, time, secrets, string, threading
import hashlib, hmac
from datetime import datetime
from functools import wraps
from flask import (Flask, request, jsonify, render_template, session,
                   redirect, url_for)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ═══════════════════════════════════════════════════════════
#  §1  CONFIG
# ═══════════════════════════════════════════════════════════

OWNER_HANDLE   = os.environ.get('OWNER_HANDLE', '@Goji_Pogi')
BRAND          = os.environ.get('BRAND', 'GOJI')
HMAC_SALT      = os.environ.get('HMAC_SALT', 'goji-warpshield-2026')
PW_SALT        = os.environ.get('PW_SALT', secrets.token_hex(32))
MAX_OWNER_HITS = int(os.environ.get('MAX_OWNER_HITS', '5'))

# raw passwords from env (never stored, never logged)
_OWNER_PW_RAW  = os.environ.get('OWNER_PASS', '')
_MASTER_PW_RAW = os.environ.get('MASTER_PASS', '')

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')
_lk = threading.Lock()
_seen_nonces = {}
_nonce_lock = threading.Lock()

# ═══════════════════════════════════════════════════════════
#  §2  HASHING
# ═══════════════════════════════════════════════════════════

def _hash_password(pw: str, salt: str) -> str:
    """Double SHA-256 + salt. walang plaintext sa memory."""
    if not pw:
        return ''
    h1 = hashlib.sha256(pw.encode()).hexdigest()
    h2 = hashlib.sha256((h1 + salt).encode()).hexdigest()
    return h2

# precompute hash at boot
OWNER_PASS_HASH  = _hash_password(_OWNER_PW_RAW, PW_SALT)
MASTER_PASS_HASH = _hash_password(_MASTER_PW_RAW, PW_SALT)

def _verify_password(input_pw: str, expected_hash: str) -> bool:
    if not expected_hash or not input_pw:
        return False
    computed = _hash_password(input_pw, PW_SALT)
    return hmac.compare_digest(computed, expected_hash)

# ═══════════════════════════════════════════════════════════
#  §3  STORAGE
# ═══════════════════════════════════════════════════════════

_DEFAULT_META = {
    'created': time.time(),
    'mode': 'primary',
    'owner_logins': [],
    'owner_lock': False,
    'owner_lock_at': None,
    'owner_lock_reason': None,
}

def _load():
    if not os.path.exists(DATA_FILE):
        return {'devices': {}, 'keys': {}, 'meta': dict(_DEFAULT_META)}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        d.setdefault('devices', {})
        d.setdefault('keys', {})
        d.setdefault('meta', {})
        for k, v in _DEFAULT_META.items():
            d['meta'].setdefault(k, v)
        return d
    except Exception:
        return {'devices': {}, 'keys': {}, 'meta': dict(_DEFAULT_META)}

def _save(d):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(d, f, indent=2, default=str)
    except Exception:
        pass

def _now(): return time.time()

def _fmt(ts):
    if not ts: return 'never'
    try: return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
    except Exception: return '?'

ALPHA = string.ascii_lowercase

# ═══════════════════════════════════════════════════════════
#  §4  DECORATORS
# ═══════════════════════════════════════════════════════════

def _owner_req(f):
    @wraps(f)
    def w(*a, **kw):
        if not session.get('owner'):
            return redirect(url_for('login'))
        with _lk:
            d = _load()
            if d['meta'].get('owner_lock'):
                session.clear()
                return redirect(url_for('login'))
        return f(*a, **kw)
    return w

def _master_req(f):
    @wraps(f)
    def w(*a, **kw):
        if not session.get('master'):
            return redirect(url_for('master_login_page'))
        return f(*a, **kw)
    return w

# ═══════════════════════════════════════════════════════════
#  §5  HMAC VERIFY
# ═══════════════════════════════════════════════════════════

def _verify_sig(payload):
    try:
        sig = payload.pop('sig', None)
        n = payload.get('n', '')
        fp = payload.get('fp', '')
        if not sig or not n:
            return False
        with _nonce_lock:
            nt = time.time()
            if n in _seen_nonces:
                return False
            _seen_nonces[n] = nt
            for k in list(_seen_nonces):
                if nt - _seen_nonces[k] > 300:
                    del _seen_nonces[k]
        msg = json.dumps(payload, sort_keys=True) + '|' + n + '|' + fp
        expect = hmac.new(HMAC_SALT.encode(), msg.encode(),
                          hashlib.sha256).hexdigest()[:16]
        return hmac.compare_digest(sig, expect)
    except Exception:
        return False

# ═══════════════════════════════════════════════════════════
#  §6  PUBLIC API
# ═══════════════════════════════════════════════════════════

@app.route('/api/ping', methods=['POST'])
def api_ping():
    data = request.get_json(silent=True) or {}
    _verify_sig(data)
    with _lk:
        d = _load()
        mode = d['meta'].get('mode', 'primary')
    return jsonify({
        'on': mode != 'locked',
        'mode': mode,
        'msg': {'primary': 'operational',
                'backup': 'backup mode',
                'locked': 'server locked'}.get(mode, '?'),
    })

@app.route('/api/verify', methods=['POST'])
def api_verify():
    data = request.get_json(silent=True) or {}
    if not _verify_sig(data):
        return jsonify({'status': 'error', 'msg': 'bad signature'}), 403
    dev = (data.get('device_id') or '').strip().upper()
    key = (data.get('key') or '').strip().lower()
    if not dev or len(dev) != 8:
        return jsonify({'status': 'error', 'msg': 'invalid device id'})

    with _lk:
        d = _load()
        n = _now()
        mode = d['meta'].get('mode', 'primary')

        if mode == 'locked':
            return jsonify({'status': 'error', 'msg': 'server locked'})
        if mode == 'backup':
            return jsonify({'status': 'backup', 'device_id': dev})

        dv = d['devices'].get(dev, {
            'device_id': dev, 'first_seen': n, 'last_seen': n,
            'key': None, 'status': 'unknown',
            'ip': request.remote_addr or '?',
            'user_agent': request.headers.get('User-Agent', '')[:120],
        })
        dv['last_seen'] = n
        dv['ip'] = request.remote_addr or dv.get('ip', '?')
        d['devices'][dev] = dv

        if dv.get('status') == 'kicked':
            _save(d)
            return jsonify({'status': 'revoked', 'device_id': dev})

        if not key:
            if dv.get('key') and dv['key'] in d['keys']:
                key = dv['key']
            else:
                _save(d)
                return jsonify({'status': 'no_key', 'device_id': dev})

        k = d['keys'].get(key)
        if not k:
            _save(d)
            return jsonify({'status': 'error', 'device_id': dev,
                            'msg': 'invalid key'})
        if k.get('revoked'):
            _save(d)
            return jsonify({'status': 'revoked', 'device_id': dev})

        bound = k.get('device_id')
        if bound and bound != dev:
            _save(d)
            return jsonify({'status': 'mismatch', 'device_id': dev})

        exp = k.get('expires')
        if exp and n > exp:
            _save(d)
            return jsonify({'status': 'expired', 'device_id': dev,
                            'expires': exp})

        if not bound:
            k['device_id'] = dev
            k['bound_at'] = n
        k['last_check'] = n
        dv['key'] = key
        dv['status'] = 'authorized'
        _save(d)

        return jsonify({'status': 'ok', 'device_id': dev,
                        'tier': k.get('tier', 'standard'),
                        'expires': exp})

@app.route('/healthz')
def healthz():
    return 'ok', 200

# ═══════════════════════════════════════════════════════════
#  §7  OWNER LOGIN + AUTO-LOCK
# ═══════════════════════════════════════════════════════════

def _record_owner_login(ip, ua):
    """track + auto-lock pag sobra na"""
    with _lk:
        d = _load()
        logins = d['meta'].setdefault('owner_logins', [])
        fp = hashlib.md5((ip + ua).encode()).hexdigest()[:8].upper()
        logins.append({'ip': ip, 'ua': ua, 'ts': _now(), 'fp': fp})
        d['meta']['owner_logins'] = logins[-50:]

        # unique fingerprints sa last 30 days
        cutoff = _now() - (30 * 86400)
        recent = [x for x in logins if x['ts'] >= cutoff]
        uniq = set(x['fp'] for x in recent)

        if len(uniq) > MAX_OWNER_HITS:
            d['meta']['owner_lock'] = True
            d['meta']['owner_lock_at'] = _now()
            d['meta']['owner_lock_reason'] = (
                f'{len(uniq)} unique devices (limit {MAX_OWNER_HITS})')
            # revoke lahat
            for k in d['keys'].values():
                k['revoked'] = True
                k['revoked_at'] = _now()
                k['revoked_reason'] = 'auto-revoke: owner pass leaked'
            for dv in d['devices'].values():
                dv['status'] = 'kicked'
                dv['key'] = None
        _save(d)
        return d['meta'].get('owner_lock', False)

@app.route('/')
def index():
    if session.get('owner'):
        return redirect(url_for('panel'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    err = None
    if request.method == 'POST':
        pw = request.form.get('pw', '')
        ip = request.remote_addr or '?'
        ua = request.headers.get('User-Agent', '')[:150]

        # check naka-lock
        with _lk:
            d = _load()
            if d['meta'].get('owner_lock'):
                return render_template('login.html', brand=BRAND,
                    err='access denied')

        if _verify_password(pw, OWNER_PASS_HASH):
            locked = _record_owner_login(ip, ua)
            if locked:
                return render_template('login.html', brand=BRAND,
                    err='access denied')
            session['owner'] = True
            return redirect(url_for('panel'))
        err = 'access denied'
    return render_template('login.html', brand=BRAND, err=err)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/panel')
@_owner_req
def panel():
    with _lk:
        d = _load()
    devices = list(d['devices'].values())
    keys = list(d['keys'].values())
    n = _now()
    mode = d['meta'].get('mode', 'primary')
    devices.sort(key=lambda x: x.get('last_seen', 0), reverse=True)
    keys.sort(key=lambda x: x.get('created', 0), reverse=True)
    stats = {
        'total_dev': len(devices),
        'active_dev': sum(1 for x in devices if x.get('status') == 'authorized'),
        'kicked_dev': sum(1 for x in devices if x.get('status') == 'kicked'),
        'total_keys': len(keys),
        'active_keys': sum(1 for x in keys if not x.get('revoked') and
                          (not x.get('expires') or x['expires'] > n)),
        'revoked_keys': sum(1 for x in keys if x.get('revoked')),
    }
    return render_template('panel.html',
        brand=BRAND, handle=OWNER_HANDLE, mode=mode,
        devices=devices, keys=keys, stats=stats, now=n, fmt=_fmt)

# ═══════════════════════════════════════════════════════════
#  §8  MASTER PANEL
# ═══════════════════════════════════════════════════════════

@app.route('/master')
def master_login_page():
    if session.get('master'):
        return redirect(url_for('master_panel'))
    return render_template('master_login.html', brand=BRAND, err=None)

@app.route('/master/login', methods=['POST'])
def master_login():
    pw = request.form.get('pw', '')
    if _verify_password(pw, MASTER_PASS_HASH):
        session['master'] = True
        return redirect(url_for('master_panel'))
    return render_template('master_login.html', brand=BRAND,
        err='access denied')

@app.route('/master/logout')
def master_logout():
    session.pop('master', None)
    return redirect(url_for('master_login_page'))

@app.route('/master/panel')
@_master_req
def master_panel():
    with _lk:
        d = _load()
    n = _now()
    logins = d['meta'].get('owner_logins', [])
    cutoff = n - (30 * 86400)
    uniq = set(x['fp'] for x in logins if x['ts'] >= cutoff)
    danger = len(uniq) >= (MAX_OWNER_HITS - 1)
    return render_template('master_panel.html',
        brand=BRAND,
        owner_lock=d['meta'].get('owner_lock', False),
        owner_lock_at=d['meta'].get('owner_lock_at'),
        owner_lock_reason=d['meta'].get('owner_lock_reason'),
        logins=list(reversed(logins[-20:])),
        unique_count=len(uniq),
        max_hits=MAX_OWNER_HITS,
        danger=danger,
        mode=d['meta'].get('mode', 'primary'),
        fmt=_fmt, now=n)

@app.route('/master/api/unlock', methods=['POST'])
@_master_req
def master_unlock():
    with _lk:
        d = _load()
        d['meta']['owner_lock'] = False
        d['meta']['owner_lock_at'] = None
        d['meta']['owner_lock_reason'] = None
        d['meta']['owner_logins'] = []
        _save(d)
    return jsonify({'ok': True})

@app.route('/master/api/lock', methods=['POST'])
@_master_req
def master_lock():
    with _lk:
        d = _load()
        d['meta']['owner_lock'] = True
        d['meta']['owner_lock_at'] = _now()
        d['meta']['owner_lock_reason'] = 'manual lock (master)'
        _save(d)
    return jsonify({'ok': True})

@app.route('/master/api/reset-tracker', methods=['POST'])
@_master_req
def master_reset():
    with _lk:
        d = _load()
        d['meta']['owner_logins'] = []
        d['meta']['owner_lock'] = False
        _save(d)
    return jsonify({'ok': True})

@app.route('/master/api/revoke-all', methods=['POST'])
@_master_req
def master_revoke_all():
    with _lk:
        d = _load()
        n = _now()
        for k in d['keys'].values():
            k['revoked'] = True
            k['revoked_at'] = n
            k['revoked_reason'] = 'master revoke-all'
        for dv in d['devices'].values():
            dv['status'] = 'kicked'
            dv['key'] = None
        _save(d)
    return jsonify({'ok': True})

@app.route('/master/api/kick-all', methods=['POST'])
@_master_req
def master_kick_all():
    with _lk:
        d = _load()
        for dv in d['devices'].values():
            dv['status'] = 'kicked'
            dv['key'] = None
        _save(d)
    return jsonify({'ok': True})

@app.route('/master/api/mode', methods=['POST'])
@_master_req
def master_mode():
    data = request.get_json() or {}
    mode = data.get('mode', 'primary')
    if mode not in ('primary', 'backup', 'locked'):
        mode = 'primary'
    with _lk:
        d = _load()
        d['meta']['mode'] = mode
        d['meta']['updated'] = _now()
        _save(d)
    return jsonify({'ok': True, 'mode': mode})

# ═══════════════════════════════════════════════════════════
#  §9  PANEL API
# ═══════════════════════════════════════════════════════════

@app.route('/api/panel/mode', methods=['POST'])
@_owner_req
def api_mode():
    data = request.get_json() or {}
    mode = data.get('mode', 'primary')
    if mode not in ('primary', 'backup', 'locked'):
        mode = 'primary'
    with _lk:
        d = _load()
        d['meta']['mode'] = mode
        _save(d)
    return jsonify({'ok': True, 'mode': mode})

@app.route('/api/panel/gen', methods=['POST'])
@_owner_req
def api_gen():
    data = request.get_json() or {}
    tier = data.get('tier', 'standard')
    try:
        count = max(1, min(50, int(data.get('count', 1))))
    except (TypeError, ValueError):
        count = 1
    days = data.get('days')
    note = (data.get('note') or '')[:80]
    created = []
    with _lk:
        d = _load()
        n = _now()
        for _ in range(count):
            for _t in range(100):
                k = '-'.join(''.join(secrets.choice(ALPHA) for _ in range(3))
                             for _ in range(3))
                if k not in d['keys']:
                    break
            d['keys'][k] = {
                'key': k, 'tier': tier, 'created': n,
                'expires': (n + int(days) * 86400) if days else None,
                'note': note, 'device_id': None, 'revoked': False,
            }
            created.append(k)
        _save(d)
    return jsonify({'ok': True, 'keys': created})

@app.route('/api/panel/revoke', methods=['POST'])
@_owner_req
def api_revoke():
    key = (request.get_json() or {}).get('key', '').strip().lower()
    with _lk:
        d = _load()
        if key not in d['keys']:
            return jsonify({'ok': False}), 404
        d['keys'][key]['revoked'] = True
        d['keys'][key]['revoked_at'] = _now()
        bd = d['keys'][key].get('device_id')
        if bd and bd in d['devices']:
            d['devices'][bd]['status'] = 'revoked'
            d['devices'][bd]['key'] = None
        _save(d)
    return jsonify({'ok': True})

@app.route('/api/panel/unrevoke', methods=['POST'])
@_owner_req
def api_unrevoke():
    key = (request.get_json() or {}).get('key', '').strip().lower()
    with _lk:
        d = _load()
        if key not in d['keys']:
            return jsonify({'ok': False}), 404
        d['keys'][key]['revoked'] = False
        d['keys'][key].pop('revoked_at', None)
        _save(d)
    return jsonify({'ok': True})

@app.route('/api/panel/kick', methods=['POST'])
@_owner_req
def api_kick():
    dev = (request.get_json() or {}).get('device_id', '').strip().upper()
    with _lk:
        d = _load()
        if dev not in d['devices']:
            return jsonify({'ok': False}), 404
        d['devices'][dev]['status'] = 'kicked'
        k = d['devices'][dev].get('key')
        if k and k in d['keys']:
            d['keys'][k]['revoked'] = True
            d['keys'][k]['revoked_at'] = _now()
        d['devices'][dev]['key'] = None
        _save(d)
    return jsonify({'ok': True})

@app.route('/api/panel/unkick', methods=['POST'])
@_owner_req
def api_unkick():
    dev = (request.get_json() or {}).get('device_id', '').strip().upper()
    with _lk:
        d = _load()
        if dev in d['devices']:
            d['devices'][dev]['status'] = 'unknown'
            _save(d)
    return jsonify({'ok': True})

@app.route('/api/panel/delete-device', methods=['POST'])
@_owner_req
def api_del_dev():
    dev = (request.get_json() or {}).get('device_id', '').strip().upper()
    with _lk:
        d = _load()
        d['devices'].pop(dev, None)
        _save(d)
    return jsonify({'ok': True})

@app.route('/api/panel/delete-key', methods=['POST'])
@_owner_req
def api_del_key():
    key = (request.get_json() or {}).get('key', '').strip().lower()
    with _lk:
        d = _load()
        d['keys'].pop(key, None)
        _save(d)
    return jsonify({'ok': True})

# ═══════════════════════════════════════════════════════════
#  §10  BOOT
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f'[GOJI] owner pass set: {bool(OWNER_PASS_HASH)}')
    print(f'[GOJI] master pass set: {bool(MASTER_PASS_HASH)}')
    print(f'[GOJI] max owner hits: {MAX_OWNER_HITS}')
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)