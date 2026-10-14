import os, sys, time, json, hashlib, platform, uuid, subprocess
import secrets, random, socket, struct, zlib, threading, datetime, re
import hmac, shutil
from enum import Enum
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

# ═══ AUTO-INSTALL ═══
def _boot():
    need = {'zstandard':'zstandard','Crypto':'pycryptodome',
            'urllib3':'urllib3','requests':'requests'}
    missing = [p for m,p in need.items() if not _has(m)]
    if missing:
        print(f'  [*] installing: {", ".join(missing)}')
        try:
            subprocess.check_call([sys.executable,'-m','pip','install',
                '--quiet','--disable-pip-version-check',*missing])
        except Exception as e:
            print(f'  [!] {e}'); sys.exit(1)

def _has(n):
    try: __import__(n); return True
    except ImportError: return False

_boot()

import zstandard as zstd
import urllib3
import requests
from Crypto.Cipher import AES
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ═══ CONFIG — walang pass dito ═══
SERVER_URL = os.environ.get('GOJI_SERVER', 'https://goji-license-v3.onrender.com')
OWNER_HANDLE = '@Goji_Pogi'
BRAND        = 'GOJI'
VERSION      = 'V3'

# HMAC salt lang — para sign request (hindi password)
HMAC_SALT = os.environ.get('GOJI_HMAC', 'goji-warpshield-2026')

# ═══ THEME ═══
class T:
    RST='\033[0m'; B='\033[1m'; D='\033[2m'
    PRI='\033[38;5;117m'; SEC='\033[38;5;183m'; OK='\033[38;5;121m'
    WARN='\033[38;5;222m'; ERR='\033[38;5;210m'
    TXT='\033[38;5;255m'; MUTE='\033[38;5;245m'; DIM='\033[38;5;240m'
    TEAL='\033[38;5;116m'; PINK='\033[38;5;218m'; PEACH='\033[38;5;216m'

_ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]')
def vlen(s): return len(_ANSI.sub('', str(s)))
def clear(): os.system('cls' if os.name=='nt' else 'clear')
def tw():
    try: return shutil.get_terminal_size((100,30)).columns
    except Exception: return 100
def cw(n=80): return min(tw()-6, n)
def trunc(s, w, suf='…'):
    s = str(s)
    if vlen(s) <= w: return s
    if w <= vlen(suf): return suf[:w]
    keep = w - vlen(suf); out=''
    for ch in s:
        if vlen(out+ch) > keep: break
        out += ch
    return out + suf
def pad_r(s, w, f=' '):
    d = w - vlen(s); return str(s) + (f*d if d>0 else '')
def commas(n):
    try: return f'{int(n):,}'
    except Exception: return str(n)
def dur_human(s):
    s = float(max(0, s))
    if s < 1: return f'{int(s*1000)}ms'
    if s < 60: return f'{s:.1f}s'
    m, x = divmod(int(s), 60)
    if m < 60: return f'{m}m{x:02d}s'
    h, r = divmod(m, 60); return f'{h}h{r:02d}m'
def fv(v, fb='—'):
    if v is None: return fb
    if isinstance(v, str):
        return v if v.strip() and v.strip().upper()!='N/A' else fb
    return v
def as_int(v, d=0):
    try: return int(v)
    except (TypeError, ValueError): return d
def now(): return time.time()
def short(): return datetime.datetime.now().strftime('%H:%M:%S')

# ═══ DEVICE ID ═══
def get_device_id():
    parts = []
    for f in (lambda: platform.node(), lambda: str(uuid.getnode()),
              lambda: platform.system(), lambda: platform.machine(),
              lambda: platform.processor()):
        try: parts.append(f())
        except Exception: pass
    for p in ('/etc/machine-id','/var/lib/dbus/machine-id'):
        try:
            with open(p,'r') as fh: parts.append(fh.read().strip()); break
        except Exception: pass
    try: parts.append(os.environ.get('USERNAME') or os.environ.get('USER') or '')
    except Exception: pass
    return hashlib.sha256('|'.join(str(x) for x in parts if x).encode()).hexdigest()[:8].upper()

def module_fp():
    try:
        with open(os.path.abspath(__file__),'rb') as f: raw = f.read()
        m = b'#__SIG__='
        if m in raw: raw = raw.split(m)[0]
        return hashlib.sha256(raw + HMAC_SALT.encode()).hexdigest()[:12]
    except Exception: return 'unknown'

MODULE_FP = module_fp()

def sign_payload(payload, nonce):
    msg = json.dumps(payload, sort_keys=True)+'|'+nonce+'|'+MODULE_FP
    return hmac.new(HMAC_SALT.encode(), msg.encode(),
                    hashlib.sha256).hexdigest()[:16]

def new_nonce(): return secrets.token_hex(8)

# ═══ STORAGE ═══
def data_dir():
    d = os.path.join(os.path.expanduser('~'), f'.{BRAND.lower()}')
    os.makedirs(d, exist_ok=True); return d
def license_path(): return os.path.join(data_dir(),'license.json')

def load_stored_key(dev):
    try:
        p = license_path()
        if not os.path.exists(p): return None
        with open(p,'r') as f: d = json.load(f)
        return d.get(dev,{}).get('key')
    except Exception: return None

def save_stored_key(dev, key):
    try:
        p = license_path(); d = {}
        if os.path.exists(p):
            with open(p,'r') as f: d = json.load(f)
        d[dev] = {'key': key, 'last_ok': now()}
        with open(p,'w') as f: json.dump(d, f, indent=2)
    except Exception: pass

def clear_stored_key(dev):
    try:
        p = license_path()
        if not os.path.exists(p): return
        with open(p,'r') as f: d = json.load(f)
        d.pop(dev, None)
        with open(p,'w') as f: json.dump(d, f, indent=2)
    except Exception: pass

# ═══ SERVER API ═══
def server_ping():
    try:
        p = {'fp': MODULE_FP, 'n': new_nonce()}
        p['sig'] = sign_payload(p, p['n'])
        r = requests.post(f'{SERVER_URL}/api/ping', json=p,
                          timeout=6, verify=False)
        return r.json()
    except Exception as e:
        return {'on': False, 'mode': 'unknown', 'msg': str(e)[:40]}

def server_verify(dev, key=None):
    try:
        p = {'device_id': dev, 'key': key, 'fp': MODULE_FP,
             'n': new_nonce(), 'ts': int(now())}
        p['sig'] = sign_payload(p, p['n'])
        r = requests.post(f'{SERVER_URL}/api/verify', json=p,
                          timeout=8, verify=False)
        return r.json()
    except requests.exceptions.Timeout:
        return {'status': 'error', 'msg': 'timeout'}
    except requests.exceptions.ConnectionError:
        return {'status': 'error', 'msg': 'offline'}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)[:60]}

# ═══ UI ═══
def show_box(text, color=None):
    c = color or T.PRI
    lines = text.split('\n')
    w = max(vlen(x) for x in lines) + 4
    print()
    print(f'  {c}╔{"═"*w}╗{T.RST}')
    for line in lines:
        p = ' ' * (w - 2 - vlen(line))
        print(f'  {c}║{T.RST}  {line}{p}{c}║{T.RST}')
    print(f'  {c}╚{"═"*w}╝{T.RST}')
    print()

def fmt_exp(ts):
    if not ts: return 'never'
    try: return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
    except Exception: return '?'

# ═══ LICENSE GATE — walang pass ═══
def license_gate():
    dev = get_device_id()
    stored = load_stored_key(dev)
    while True:
        clear()
        print()
        print(f'  {T.PRI}{T.B}{BRAND}{T.RST} {T.SEC}{VERSION}{T.RST}  '
              f'{T.DIM}· fp {MODULE_FP}{T.RST}')
        print(f'  {T.DIM}{"━"*46}{T.RST}')
        print()
        print(f'  {T.MUTE}connecting to server...{T.RST}')
        time.sleep(0.3)
        ping = server_ping()
        mode = ping.get('mode','unknown')

        if mode == 'locked' or not ping.get('on', False):
            show_box(f'{T.ERR}✗ SERVER OFFLINE{T.RST}\n\n'
                     f'{T.MUTE}{ping.get("msg","server locked")}{T.RST}',
                     T.ERR)
            print(f'  {T.MUTE}1{T.RST} retry · {T.MUTE}0{T.RST} exit')
            try: c = input(f'  {T.PRI}›{T.RST} ').strip()
            except (EOFError, KeyboardInterrupt): sys.exit(0)
            if c=='0': sys.exit(0)
            continue

        res = server_verify(dev, stored)
        status = res.get('status')

        if status == 'ok':
            show_box(f'{T.OK}✓ ACCESS GRANTED{T.RST}\n\n'
                     f'{T.MUTE}tier:{T.RST} {T.WARN}{res.get("tier","standard")}{T.RST}\n'
                     f'{T.MUTE}expires:{T.RST} {T.TXT}{fmt_exp(res.get("expires"))}{T.RST}',
                     T.OK)
            time.sleep(1.0)
            return stored or 'ok'

        if status == 'no_key':
            show_box(f'{T.WARN}❌ ACCESS DENIED{T.RST}\n\n'
                     f'{T.MUTE}Your Device ID:{T.RST}  {T.B}{T.TXT}{dev}{T.RST}\n\n'
                     f'{T.PRI}▸ Contact {OWNER_HANDLE} to purchase a key!{T.RST}',
                     T.WARN)
            print(f'  {T.MUTE}Paste token (ENTER=retry):{T.RST}')
            try: k = input(f'  {T.PRI}›{T.RST} ').strip().lower()
            except (EOFError, KeyboardInterrupt): sys.exit(0)
            if not k: continue
            if not re.match(r'^[a-z]{3}-[a-z]{3}-[a-z]{3}$', k):
                print(f'  {T.ERR}✗ format: xxx-xxx-xxx (a-z only){T.RST}')
                time.sleep(1.5); continue
            stored = k
            save_stored_key(dev, stored)
            continue

        if status == 'expired':
            show_box(f'{T.ERR}❌ ACCESS DENIED{T.RST}\n\n'
                     f'{T.ERR}Key expired on {fmt_exp(res.get("expires"))}{T.RST}\n\n'
                     f'{T.MUTE}Your Device ID:{T.RST}  {T.B}{T.TXT}{dev}{T.RST}\n\n'
                     f'{T.PRI}▸ Contact {OWNER_HANDLE}{T.RST}', T.ERR)
            print(f'  {T.MUTE}1 retry · 0 exit{T.RST}')
            try: c = input(f'  {T.PRI}›{T.RST} ').strip()
            except (EOFError, KeyboardInterrupt): sys.exit(0)
            if c=='0': sys.exit(0)
            clear_stored_key(dev); stored = None
            continue

        if status == 'revoked':
            show_box(f'{T.ERR}❌ ACCESS DENIED{T.RST}\n\n'
                     f'{T.ERR}Your key has been revoked.{T.RST}\n\n'
                     f'{T.MUTE}Your Device ID:{T.RST}  {T.B}{T.TXT}{dev}{T.RST}\n\n'
                     f'{T.PRI}▸ Contact {OWNER_HANDLE}{T.RST}', T.ERR)
            print(f'  {T.MUTE}1 retry · 0 exit{T.RST}')
            try: c = input(f'  {T.PRI}›{T.RST} ').strip()
            except (EOFError, KeyboardInterrupt): sys.exit(0)
            if c=='0': sys.exit(0)
            clear_stored_key(dev); stored = None
            continue

        if status == 'mismatch':
            show_box(f'{T.ERR}❌ ACCESS DENIED{T.RST}\n\n'
                     f'{T.ERR}This key is bound to another device.{T.RST}\n\n'
                     f'{T.MUTE}Your Device ID:{T.RST}  {T.B}{T.TXT}{dev}{T.RST}\n\n'
                     f'{T.PRI}▸ Contact {OWNER_HANDLE}{T.RST}', T.ERR)
            print(f'  {T.MUTE}1 retry · 0 exit{T.RST}')
            try: c = input(f'  {T.PRI}›{T.RST} ').strip()
            except (EOFError, KeyboardInterrupt): sys.exit(0)
            if c=='0': sys.exit(0)
            clear_stored_key(dev); stored = None
            continue

        print(f'  {T.ERR}✗ {res.get("msg","unknown error")}{T.RST}')
        print(f'  {T.MUTE}1 retry · 0 exit{T.RST}')
        try: c = input(f'  {T.PRI}›{T.RST} ').strip()
        except (EOFError, KeyboardInterrupt): sys.exit(0)
        if c=='0': sys.exit(0)

# ═══ SDP PROTOCOL ═══
class SdpType(Enum):
    INT_POS=0; INT_NEG=1; FLOAT=2; DOUBLE=3
    STRING=4; LIST=5; DICT=6; STRUCT_BEGIN=7; STRUCT_END=8

class SdpError(Exception): pass

def _sort(kv):
    k = kv[0]
    return (0, k) if isinstance(k, int) else (1, str(k))

class SdpStruct(dict):
    def __init__(self, data=None):
        super().__init__()
        self.data = b''; self.offset = 0
        if isinstance(data, bytes): self.data = data; self._unpack()
        elif data is not None: super().update(data); self._pack()
    def _pack(self):
        self.data = bytes([SdpType.STRUCT_BEGIN.value << 4])
        for t, v in sorted(self.items(), key=_sort): self._pv(t, v)
        self.data += bytes([SdpType.STRUCT_END.value << 4])
    def _unpack(self):
        if not self.data: return
        if self.data[0] >> 4 == SdpType.STRUCT_BEGIN.value: self.offset = 1
        while self.offset < len(self.data):
            t, v = self._uv()
            if isinstance(v, SdpType) and v == SdpType.STRUCT_END: break
            self[t] = v
    def _wn(self, v):
        r = bytearray()
        while v >= 0x80: r.append((v & 0x7F) | 0x80); v >>= 7
        r.append(v & 0x7F); return bytes(r)
    def _rn(self):
        if self.offset >= len(self.data): raise SdpError('eof')
        n = 1; val = self.data[self.offset] & 0x7F
        while self.data[self.offset+n-1] >= 0x80:
            if self.offset+n >= len(self.data): raise SdpError('trunc')
            val |= (self.data[self.offset+n] & 0x7F) << (7*n); n += 1
        self.offset += n; return val
    def _hdr(self, tag, dt):
        if tag < 15: self.data += bytes([(dt.value << 4) | tag])
        else:
            self.data += bytes([(dt.value << 4) | 15]); self.data += self._wn(tag)
    def _pv(self, tag, val):
        if isinstance(val, bool):
            self._hdr(tag, SdpType.INT_POS); self.data += self._wn(1 if val else 0)
        elif isinstance(val, int):
            if val < 0: self._hdr(tag, SdpType.INT_NEG); self.data += self._wn(-val)
            else: self._hdr(tag, SdpType.INT_POS); self.data += self._wn(val)
        elif isinstance(val, float):
            self._hdr(tag, SdpType.DOUBLE)
            pk = struct.pack('<d', val); self.data += self._wn(len(pk)) + pk
        elif isinstance(val, (str, bytes)):
            self._hdr(tag, SdpType.STRING)
            e = val.encode('utf-8') if isinstance(val, str) else val
            self.data += self._wn(len(e)) + e
        elif isinstance(val, list):
            self._hdr(tag, SdpType.LIST); self.data += self._wn(len(val))
            for it in val: self._pv(0, it)
        elif isinstance(val, dict):
            if isinstance(val, SdpStruct):
                self._hdr(tag, SdpType.STRUCT_BEGIN)
                for k, v in sorted(val.items(), key=_sort): self._pv(k, v)
                self.data += bytes([SdpType.STRUCT_END.value << 4])
            else:
                self._hdr(tag, SdpType.DICT); self.data += self._wn(len(val))
                for k, v in sorted(val.items(), key=_sort):
                    self._pv(0, k); self._pv(0, v)
        else: raise SdpError('bad')
    def _uv(self):
        try:
            if self.offset >= len(self.data): return 0, None
            h = self.data[self.offset]
            tag = h & 0xF; dt = SdpType(h >> 4); self.offset += 1
            if tag == 15: tag = self._rn()
            if dt == SdpType.INT_POS: return tag, self._rn()
            if dt == SdpType.INT_NEG: return tag, -self._rn()
            if dt == SdpType.FLOAT:
                return tag, struct.unpack('<f', self._rn().to_bytes(4,'little'))[0]
            if dt == SdpType.DOUBLE:
                return tag, struct.unpack('<d', self._rn().to_bytes(8,'little'))[0]
            if dt == SdpType.STRING:
                n = self._rn(); ch = self.data[self.offset:self.offset+n]
                try: v = ch.decode('utf-8')
                except UnicodeDecodeError: v = ch
                self.offset += n; return tag, v
            if dt == SdpType.LIST:
                n = self._rn(); v = []
                for _ in range(n):
                    _, it = self._uv(); v.append(it)
                return tag, v
            if dt == SdpType.DICT:
                n = self._rn(); v = {}
                for _ in range(n):
                    _, k = self._uv(); _, x = self._uv(); v[k] = x
                return tag, v
            if dt == SdpType.STRUCT_BEGIN:
                sub = {}
                while True:
                    st, sv = self._uv()
                    if isinstance(sv, SdpType) and sv == SdpType.STRUCT_END: break
                    sub[st] = sv
                return tag, SdpStruct(sub)
            if dt == SdpType.STRUCT_END: return tag, SdpType.STRUCT_END
            raise SdpError('bad')
        except SdpError: raise
        except Exception: raise SdpError('unpack')

_AES_KEY = bytes.fromhex('f5a193d50ade553e9835595f5cd75ddd')
_AES_IV = b'\x00' * 16
def _aes(data):
    if not data or len(data)%16: raise SdpError('cipher')
    return AES.new(_AES_KEY, AES.MODE_CBC, iv=_AES_IV).decrypt(data).rstrip(b'\x00')

LOGIN_HOST = 'login.ml.youngjoygame.com'
LOGIN_PORT = 30021
CLIENT_VERSION = '2.2.16.1232.1'
CHANNEL = 'and_usa'
DEVICE_ID_RE = re.compile(r'(?:and|ios)_[0-9A-Za-z]{16,128}(?:-[0-9a-fA-F]{4,16}){3,6}')

_DNS = {}; _DNS_LK = threading.Lock()
def _resolve(h):
    if not h or re.match(r'^\d+\.\d+\.\d+\.\d+$', h): return h
    n = now()
    with _DNS_LK:
        x = _DNS.get(h)
        if x and x[1] > n: return x[0]
    try: ip = socket.gethostbyname(h)
    except Exception: ip = h
    with _DNS_LK: _DNS[h] = (ip, n+600)
    return ip

class GameConn:
    def __init__(self, dev):
        self.device_id = dev; self.host = LOGIN_HOST; self.port = LOGIN_PORT
        self.seq = 1; self.sock = None; self.q = b''; self.lh = 0
        p = dev.split('_')
        if len(p) >= 2:
            i = p[1]
            if len(p) >= 3 and len(i) < 32: i += '_'+p[2]
            if len(i) >= 32:
                self.md5 = i[:32]
                self.aid = i[32:48] if len(i) >= 48 else ''
                self.adid = i[48:] if len(i) > 48 else ''
            else: self.md5 = i; self.aid = ''; self.adid = ''
        else: self.md5 = dev; self.aid = ''; self.adid = ''
        self.acct = 0; self.skey = ''; self.zone = 0
        self.gh = ''; self.gp = 0; self.cts = 0
    def open(self, h=None, p=None):
        if h: self.host = h
        if p: self.port = p
        ip = _resolve(self.host)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try: self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception: pass
        self.sock.settimeout(8); self.sock.connect((ip, self.port))
    def close(self):
        if self.sock:
            try: self.sock.close()
            except Exception: pass
        self.sock = None; self.seq = 1; self.q = b''
    def put(self, pid, pk):
        p = SdpStruct({0:pid, 1:self.seq, 5:pk.data}).data
        buf = zstd.compress(p); sz = len(buf)+4
        if sz > 0xFFFFFF: raise SdpError('large')
        self.sock.send((sz | (16 << 24)).to_bytes(4,'big') + buf)
        self.seq += 1
    def get(self):
        try:
            while len(self.q) < 4:
                d = self.sock.recv(4096)
                if not d: return None, None
                self.q += d
            fl = int.from_bytes(self.q[:4],'big')
            sz = fl & 0xFFFFFF; ct = fl >> 24
            self.lh = sz
            while len(self.q) < sz:
                d = self.sock.recv(4096)
                if not d: return None, None
                self.q += d
            data = self.q[4:sz]; self.q = self.q[sz:]
            if ct == 1: data = zlib.decompress(data)
            elif ct == 16: data = zstd.decompress(data)
            elif ct == 2: data = _aes(data)
            elif ct == 3: data = zlib.decompress(_aes(data))
            elif ct == 18: data = zstd.decompress(_aes(data))
            r = SdpStruct(data); pid = r[0]
            if pid is None: return None, None
            b = r.get(6)
            if not isinstance(b, bytes):
                b = r.get(5)
                if not isinstance(b, bytes): return pid, None
            return pid, SdpStruct(b)
        except socket.timeout: return -1, None
        except Exception: return None, None
    def login(self):
        self.open(LOGIN_HOST, LOGIN_PORT)
        self.put(1, SdpStruct({
            0: self.device_id,
            1: f'gps_adid={self.adid}&android_id={self.aid}&device_unique_id={self.md5}',
            2: CLIENT_VERSION, 3: CHANNEL, 4: 'en',
        }))
        pid, res = self.get()
        if pid == 2 and res:
            self.acct = res.get(0); self.skey = res.get(1)
            zd = res.get(2)
            if isinstance(zd, dict): self.zone = zd.get(0, 0)
            elif isinstance(zd, list) and zd:
                self.zone = zd[0] if not isinstance(zd[0], dict) else zd[0].get(0, 0)
            else: self.zone = zd or 0
            self.cts = res.get(19, 0)
            s = str(self.acct)
            if s.startswith('221') or s.startswith('222'): return False, res
            return True, res
        return False, res
    def srv(self):
        self.put(5, SdpStruct({0:self.acct, 1:self.skey, 2:CLIENT_VERSION,
                               5:self.zone, 6:CHANNEL}))
        pid, res = self.get()
        if pid == 6 and res:
            a = res[1]; self.gh, ps = a.split(':')
            self.gp = int(ps); return True, res
        return False, res
    def join(self):
        self.close(); self.open(self.gh, self.gp)
        self.put(10001, SdpStruct({0:self.acct, 1:self.skey, 2:self.zone,
                                   4:CLIENT_VERSION, 13:CHANNEL, 15:self.device_id}))
        self.put(10101, SdpStruct({0:0, 2:2}))
    def sync(self, tries=25):
        for _ in range(tries):
            pid, _ = self.get()
            if pid is None or pid == -1: return False
            if pid == 10002: return True
        return False
    def find(self, val, kind='id'):
        if kind == 'id':
            try: pk = SdpStruct({1:int(val)})
            except (TypeError, ValueError): return None
        else: pk = SdpStruct({0:str(val).strip()})
        self.put(11153, pk); miss = 0
        while True:
            pid, res = self.get()
            if pid is None or pid == -1: return None
            if pid == 11154: return res
            if pid == 20001:
                miss += 1
                if self.lh < 100 and miss >= 3: return None

BAN_REASONS = {
    '21':'Plug-in Apps','22':'Account Sharing','23':'Toxic Behavior',
    '24':'Cheating in Ranked','25':'Payment Fraud','26':'Account Trading',
    '27':'AFK','28':'Intentional Feeding','29':'Hate Speech','30':'Third-party Tool',
    '31':'Malicious Behavior','32':'Fraud','33':'Spam','34':'Ban Evasion',
    '35':'Harassment','36':'Match Manipulation','37':'Multiple Accounts',
    '38':'Account Sale','39':'Cheating','40':'Bot Activity',
}

def _walk(o, p='', d=0, mx=8):
    if d > mx: return
    if isinstance(o, dict):
        for k, v in o.items():
            yield (p, k, v)
            if isinstance(v, (dict, list)): yield from _walk(v, f'{p}/{k}', d+1, mx)
    elif isinstance(o, list):
        for i, it in enumerate(o):
            if isinstance(it, (dict, list)): yield from _walk(it, f'{p}[{i}]', d+1, mx)

def _scan_ban(sdp):
    rpt = {'banned':False,'reason':None,'code':None,'dur':None,'conf':0}
    if sdp is None: return False, rpt
    ed = eh = em = None; bc = None
    try:
        for _, k, v in _walk(dict(sdp)):
            ks = str(k)
            if ks == 'ban_reason':
                c = str(v)
                if c in BAN_REASONS: bc = c; rpt['code']=c; rpt['reason']=BAN_REASONS[c]
            elif ks == 'endtime_day' and v is not None:
                ed = int(v) if str(v).lstrip('-').isdigit() else 0
            elif ks == 'endtime_hour' and v: eh = int(v) if str(v).isdigit() else 0
            elif ks == 'endtime_min' and v: em = int(v) if str(v).isdigit() else 0
    except Exception: pass
    b = False
    if ed is not None and ed > 0:
        b = True; rpt['dur'] = f"{ed}d {(eh or 0):02d}h {(em or 0):02d}m"; rpt['conf'] = 100
    if bc: b = True; rpt['conf'] = max(rpt['conf'], 90)
    rpt['banned'] = b
    return b, rpt

HEROES = {1:"Miya",2:"Balmond",3:"Saber",4:"Alice",5:"Nana",6:"Tigreal",7:"Alucard",
8:"Karina",9:"Akai",10:"Franco",11:"Bane",12:"Bruno",13:"Clint",14:"Rafaela",
15:"Eudora",16:"Zilong",17:"Fanny",18:"Layla",19:"Minotaur",20:"Lolita",
21:"Hayabusa",22:"Freya",23:"Gord",24:"Natalia",25:"Kagura",26:"Chou",27:"Sun",
28:"Alpha",29:"Ruby",30:"Yi Sun-shin",31:"Moskov",32:"Johnson",33:"Cyclops",
34:"Estes",35:"Hilda",36:"Aurora",37:"Lapu-Lapu",38:"Vexana",39:"Roger",
40:"Karrie",41:"Gatotkaca",42:"Harley",43:"Irithel",44:"Grock",45:"Argus",
46:"Odette",47:"Lancelot",48:"Diggie",49:"Hylos",50:"Zhask",51:"Helcurt",
52:"Pharsa",53:"Lesley",54:"Jawhead",55:"Angela",56:"Gusion",57:"Valir",
58:"Martis",59:"Uranus",60:"Hanabi",61:"Chang'e",62:"Kaja",63:"Selena",
64:"Aldous",65:"Claude",66:"Vale",67:"Leomord",68:"Lunox",69:"Hanzo",
70:"Belerick",71:"Kimmy",72:"Thamuz",73:"Harith",74:"Minsitthar",75:"Kadita",
76:"Faramis",77:"Badang",78:"Khufra",79:"Granger",80:"Guinevere",81:"Esmeralda",
82:"Terizla",83:"X.Borg",84:"Ling",85:"Dyrroth",86:"Lylia",87:"Baxia",
88:"Masha",89:"Wanwan",90:"Silvanna",91:"Cecilion",92:"Carmilla",93:"Atlas",
94:"Popol and Kupa",95:"Yu Zhong",96:"Luo Yi",97:"Benedetta",98:"Khaleed",
99:"Barats",100:"Brody",101:"Yve",102:"Mathilda",103:"Paquito",104:"Gloo",
105:"Beatrix",106:"Phoveus",107:"Natan",108:"Aulus",109:"Aamon",110:"Valentina",
111:"Edith",112:"Floryn",113:"Yin",114:"Melissa",115:"Xavier",116:"Julian",
117:"Fredrinn",118:"Joy",119:"Novaria",120:"Arlott",121:"Ixia",122:"Nolan",
123:"Cici",124:"Chip",125:"Zhuxin",126:"Suyou",127:"Lukas",128:"Kalea",
129:"Zetian",130:"Obsidia"}

def _rank(p):
    try: p = int(p)
    except (TypeError, ValueError): return "Unranked"
    if p <= 0: return "Unranked"
    T2 = [(0,4,"Warrior III"),(5,9,"Warrior II"),(10,14,"Warrior I"),
        (15,19,"Elite IV"),(20,24,"Elite III"),(25,29,"Elite II"),(30,34,"Elite I"),
        (35,39,"Master IV"),(40,44,"Master III"),(45,49,"Master II"),(50,54,"Master I"),
        (55,59,"GM IV"),(60,64,"GM III"),(65,69,"GM II"),(70,74,"GM I"),
        (75,81,"Epic IV"),(82,88,"Epic III"),(89,95,"Epic II"),(96,107,"Epic I"),
        (108,114,"Legend IV"),(115,121,"Legend III"),(122,128,"Legend II"),(129,135,"Legend I")]
    for lo, hi, n in T2:
        if lo <= p <= hi: return n
    if 136 <= p <= 160: return f"Mythic {p-135}"
    if 161 <= p <= 195: return f"Mythical Honor {p-135}"
    if 196 <= p <= 235: return f"Mythical Glory {p-195}"
    if p >= 236: return f"Mythical Immortal {p-235}"
    return "Unranked"

COLLECTOR_TIERS = [
    {'n':'New Collector','min':0,'max':1000},
    {'n':'Amateur Collector','min':1000,'max':4000},
    {'n':'Junior Collector','min':4000,'max':10000},
    {'n':'Seasoned Collector','min':10000,'max':22000},
    {'n':'Expert Collector','min':22000,'max':44000},
    {'n':'Renowned Collector','min':44000,'max':84000},
    {'n':'Exalted Collector','min':84000,'max':160000},
    {'n':'Mega Collector','min':160000,'max':280000},
    {'n':'World Collector','min':280000,'max':float('inf')},
]
_RM = ['V','IV','III','II','I']
def _ci(p):
    try: pts = int(p)
    except (TypeError, ValueError): pts = 0
    pts = max(0, pts)
    for e in COLLECTOR_TIERS:
        if e['min'] <= pts < e['max']:
            n = e['n']
            if n in ('New Collector','World Collector'): return n
            span = (e['max']-e['min'])/5
            lv = max(0, min(4, int((pts-e['min'])//span)))
            return f'{n} {_RM[lv]}'
    return 'New Collector'

def _skins(t):
    if not t or not isinstance(t, dict): return {}
    d = None
    for k in (4,0,1):
        v = t.get(k)
        if isinstance(v, dict) and v: d = v; break
    if d is None: d = t
    if not isinstance(d, dict): return {}
    km = {6:"Supreme",5:"Grand",4:"Exquisite",3:"Deluxe",2:"Exceptional",1:"Common"}
    o = {}
    for sid, cnt in d.items():
        try: i = int(sid)
        except (ValueError, TypeError): continue
        if i in km: o[km[i]] = cnt
    return o

def _last_match(ri, p):
    cs = []
    for src in (ri, p):
        if not isinstance(src, dict): continue
        for tag in (120,130,145,150,190,200,33,35,40,55,70,78,85,88,99,105,110,100):
            v = src.get(tag)
            if isinstance(v, (dict, list)) and v: cs.append(v)
    e = None
    for c in cs:
        if isinstance(c, list) and c and isinstance(c[0], dict): e = c[0]; break
        if isinstance(c, dict):
            for k in sorted(c.keys(), key=lambda x:(isinstance(x,str),x)):
                if isinstance(c[k], dict): e = c[k]; break
            if e: break
    if not e: return None
    hid = e.get(0,0) or e.get(1,0) or 0
    h = HEROES.get(hid, f"H{hid}") if hid else "?"
    k = int(e.get(2,0) or 0); d = int(e.get(3,0) or 0); a = int(e.get(4,0) or 0)
    rr = e.get(6, e.get(7,0))
    res = 'WIN' if rr in (1,'1','win','WIN',True) else ('LOSS' if rr in (0,'0','loss','LOSS',False) else '?')
    return {'hero':h,'kda':f'{k}/{d}/{a}','result':res}

def _extract(result, cts=0):
    if not result or not result.get(0): return None
    f = result[0]
    if isinstance(f, dict): p = f
    elif isinstance(f, list) and f and isinstance(f[0], dict): p = f[0]
    else: return None
    try:
        nick = p.get(2,"") or "Unknown"
        pid = p.get(0,0); srv = p.get(1,0)
        lv = int(p.get(3,0) or 0); sc = int(p.get(83,0) or 0); hc = int(p.get(4,0) or 0)
        rn = _rank(p.get(8))
        t136 = p.get(136,{})
        cp = t136.get(9,0) if isinstance(t136,dict) else 0
        tw = p.get(18,0) or 0; tb = p.get(17,0) or 0
        wr = None
        if tb > 0 and tw > 0:
            w = (tw/tb)*100; wr = f"~{min(w,100):.1f}%" if w > 100 else f"{w:.1f}%"
        dia = 0
        cur = p.get(111)
        if isinstance(cur, dict): dia = int(cur.get(0,0) or 0)
        elif isinstance(cur, int): dia = cur
        sk = {"Supreme":0,"Grand":0,"Exquisite":0,"Deluxe":0,"Exceptional":0,"Common":0}
        if p.get(118):
            ps = _skins(p.get(118))
            if ps: sk.update(ps)
        ci = _ci(cp)
        rare = sk.get('Supreme',0)+sk.get('Grand',0)+sk.get('Exquisite',0)
        score = (min(2000, sc*3) + min(1000, hc*2) + min(2000, cp//50) +
                 min(1000, lv*5) + min(500, dia//10) + rare*15)
        g = "S" if score>=5000 else "A" if score>=3500 else "B" if score>=2000 else "C" if score>=1000 else "D" if score>=400 else "E"
        return {'nickname':nick,'player_id':pid,'server':srv,'level':lv,
                'skin_count':sc,'hero_count':hc,'current_rank':rn,
                'collector_point':cp,'collector_tier':ci,
                'total_battles':tb,'win_rate':wr,'diamonds':dia,
                'skin_breakdown':sk,'rare_skins':rare,
                'account_score':score,'account_grade':g,
                'last_match':_last_match({},p),
                'ban_status':'CLEAN','ban_reason':None,'ban_duration':None}
    except Exception: return None

def _fetch(dev):
    c = GameConn(dev)
    try:
        ok, _ = c.login()
        if not ok: return {'status':'error','error':'login'}
        aid = c.acct; zid = c.zone; cts = c.cts
        ok, _ = c.srv()
        if not ok: return {'status':'error','error':'server'}
        c.join()
        if not c.sync(): return {'status':'error','error':'hs'}
        r = c.find(int(aid), 'id')
        if not r: return {'status':'error','error':'empty'}
        b, rpt = _scan_ban(r)
        pl = _extract(r, cts)
        if not pl: return {'status':'error','error':'extract'}
        if b:
            pl['ban_status'] = 'BANNED'
            pl['ban_reason'] = rpt.get('reason')
            pl['ban_duration'] = rpt.get('dur') or 'permanent'
        return {'status':'success','player':pl,'device_id':dev,
                'account_id':aid,'zone_id':zid}
    except Exception as e:
        return {'status':'error','error':type(e).__name__}
    finally: c.close()

# ═══ MENU ═══
def _menu():
    print()
    print(f'  {T.PRI}◆{T.RST}  {T.B}{T.SEC}{BRAND} MENU{T.RST}')
    print(f'  {T.DIM}{"─"*44}{T.RST}')
    print()
    opts = [
        ('1','Single Check'),('2','Bulk Check'),('3','Compare Accounts'),
        ('4','Generate Device IDs'),('5','Merge IDs from Folder'),
        ('6','Watchlist'),('7','History'),('8','Notes'),('9','Search'),
        ('T','Stats'),('P','Show Output Paths'),('?','Help'),('@','About'),
        ('0','Exit'),
    ]
    pal = [T.PRI,T.SEC,T.OK,T.WARN,T.TEAL,T.PINK,T.PEACH]
    for i, (k, lb) in enumerate(opts):
        c = pal[i % len(pal)]
        print(f'  {c}│{T.RST}  {c}{T.B}[{k}]{T.RST}  {T.TXT}{lb}{T.RST}')
    print()
    valid = {k for k, _ in opts}
    while True:
        try: c = input(f'  {T.PRI}›{T.RST} ').strip().upper()
        except (EOFError, KeyboardInterrupt): print(); return '0'
        if c in valid: return c

# ═══ ACTIONS ═══
def _head(t, c=None):
    c = c or T.PRI
    print()
    print(f'  {c}◆{T.RST}  {T.B}{T.TXT}{t}{T.RST}')
    print(f'  {T.DIM}{"─"*cw()}{T.RST}')

def _pause(m='enter'):
    try: input(f'  {T.DIM}{m}...{T.RST}')
    except (EOFError, KeyboardInterrupt): print()

def _ask(p, d=''):
    suf = f'  {T.DIM}[{d}]{T.RST}' if d else ''
    try: a = input(f'  {T.PRI}›{T.RST} {T.MUTE}{p}{T.RST}{suf}  ').strip()
    except (EOFError, KeyboardInterrupt): print(); return d
    return a or d

def _t_single():
    _head('SINGLE CHECK')
    print()
    try: dev = input(f'  {T.PRI}›{T.RST} device id  ').strip()
    except (EOFError, KeyboardInterrupt): return
    if not DEVICE_ID_RE.match(dev):
        print(f'  {T.ERR}✗ invalid{T.RST}'); time.sleep(1); return
    print(f'  {T.MUTE}checking...{T.RST}')
    r = _fetch(dev)
    if r.get('status') != 'success':
        print(f'  {T.ERR}✗ {r.get("error")}{T.RST}'); time.sleep(1.5); return
    p = r['player']
    print()
    print(f'  {T.B}{T.TXT}{p.get("nickname","?")}{T.RST}  {T.DIM}·{T.RST}  '
          f'{T.WARN}Lv{p.get("level")}{T.RST}  {T.DIM}·{T.RST}  gr {p.get("account_grade")}')
    print(f'  {T.MUTE}rank   {T.RST}{p.get("current_rank")}')
    print(f'  {T.MUTE}collect{T.RST} {p.get("collector_tier")}')
    print(f'  {T.MUTE}heroes {T.RST}{p.get("hero_count")}  {T.MUTE}skins {T.RST}{p.get("skin_count")}')
    print(f'  {T.MUTE}score  {T.RST}{commas(p.get("account_score",0))}')
    if p.get('ban_status') == 'BANNED':
        print(f'  {T.MUTE}ban    {T.RST}{T.ERR}{T.B}BANNED{T.RST}  {T.DIM}{p.get("ban_reason")}{T.RST}')
    else:
        print(f'  {T.MUTE}ban    {T.RST}{T.OK}CLEAN{T.RST}')
    _pause()

def _t_bulk():
    _head('BULK CHECK')
    print()
    try: path = input(f'  {T.PRI}›{T.RST} file  ').strip().strip('"')
    except (EOFError, KeyboardInterrupt): return
    if not os.path.exists(path):
        print(f'  {T.ERR}✗ not found{T.RST}'); time.sleep(1); return
    try:
        with open(path,'r',errors='replace') as f: txt = f.read()
    except OSError as e:
        print(f'  {T.ERR}✗ {e}{T.RST}'); time.sleep(1); return
    ids = list(dict.fromkeys(m.group(0) for m in DEVICE_ID_RE.finditer(txt)))
    if not ids:
        print(f'  {T.ERR}✗ no ids{T.RST}'); time.sleep(1); return
    try: th = max(1, min(32, int(_ask('threads', default='10'))))
    except ValueError: th = 10
    print(f'  {T.MUTE}{len(ids)} ids · {th} threads{T.RST}')
    clean = banned = errs = 0
    with ThreadPoolExecutor(max_workers=th) as ex:
        futs = [ex.submit(_fetch, d) for d in ids]
        for i, f in enumerate(as_completed(futs), 1):
            try:
                r = f.result()
                if r.get('status')=='success':
                    if r['player'].get('ban_status')=='BANNED': banned += 1
                    else: clean += 1
                else: errs += 1
            except Exception: errs += 1
            print(f'\r  {i}/{len(ids)}  {T.OK}clean {clean}{T.RST}  '
                  f'{T.ERR}ban {banned}{T.RST}  {T.WARN}err {errs}{T.RST}  ',
                  end='', flush=True)
    print()
    print(f'  {T.OK}✓ done{T.RST}')
    _pause()

def _t_compare():
    _head('COMPARE')
    print()
    try:
        a = input(f'  {T.PRI}›{T.RST} #1  ').strip()
        b = input(f'  {T.PRI}›{T.RST} #2  ').strip()
    except (EOFError, KeyboardInterrupt): return
    if not a or not b: return
    ra = _fetch(a); rb = _fetch(b)
    if ra.get('status')!='success' or rb.get('status')!='success':
        print(f'  {T.ERR}✗ failed{T.RST}'); time.sleep(1.5); return
    pa, pb = ra['player'], rb['player']
    for f, x, y in [('nickname',pa.get('nickname'),pb.get('nickname')),
                    ('level',pa.get('level'),pb.get('level')),
                    ('rank',pa.get('current_rank'),pb.get('current_rank')),
                    ('collector',pa.get('collector_tier'),pb.get('collector_tier')),
                    ('grade',pa.get('account_grade'),pb.get('account_grade')),
                    ('score',commas(pa.get('account_score',0)),commas(pb.get('account_score',0)))]:
        print(f'  {T.MUTE}{f:<12}{T.RST}{T.TXT}{trunc(str(x),22):<24}{T.SEC}{trunc(str(y),22)}{T.RST}')
    _pause()

def _t_gen():
    _head('GENERATE DEVICE IDS')
    print()
    try: n = max(1, min(100000, int(_ask('count', default='100'))))
    except (ValueError, EOFError): n = 100
    ids = []
    for _ in range(n):
        imei = ''.join(random.choice('0123456789abcdef') for _ in range(32))
        andr = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(16))
        adid = '-'.join([''.join(random.choice('0123456789abcdef') for _ in range(x)) for x in (8,4,4,4,12)])
        ids.append(f'and_{imei}{andr}{adid}')
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'gen_{n}.txt')
    with open(out,'w') as f:
        for d in ids: f.write(d+'\n')
    print(f'  {T.OK}✓ {n} → {out}{T.RST}')
    _pause()

def _t_merge():
    _head('MERGE IDS')
    print()
    try: raw = input(f'  {T.PRI}›{T.RST} folder  ').strip().strip('"')
    except (EOFError, KeyboardInterrupt): return
    if not raw: return
    tgt = os.path.expanduser(raw)
    if not os.path.isdir(tgt):
        print(f'  {T.ERR}✗ not a folder{T.RST}'); time.sleep(1); return
    files = []
    for r,_,names in os.walk(tgt):
        for nn in names:
            if nn.lower().endswith(('.txt','.csv','.log','.tsv')):
                files.append(os.path.join(r,nn))
    all_ids = []; seen = set()
    for pp in files:
        try:
            with open(pp,'r',errors='replace') as f: txt = f.read()
        except OSError: continue
        for m in DEVICE_ID_RE.finditer(txt):
            d = m.group(0)
            if d not in seen: seen.add(d); all_ids.append(d)
    if not all_ids:
        print(f'  {T.ERR}✗ none{T.RST}'); time.sleep(1); return
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'merged.txt')
    with open(out,'w') as f:
        for d in all_ids: f.write(d+'\n')
    print(f'  {T.OK}✓ {len(all_ids)} → {out}{T.RST}')
    _pause()

def _t_watch():
    _head('WATCHLIST')
    print(f'  {T.MUTE}notebook module — coming soon{T.RST}')
    _pause()

def _t_hist():
    _head('HISTORY')
    print(f'  {T.MUTE}history module — coming soon{T.RST}')
    _pause()

def _t_notes():
    _head('NOTES')
    print(f'  {T.MUTE}notes module — coming soon{T.RST}')
    _pause()

def _t_search():
    _head('SEARCH')
    print(f'  {T.MUTE}search module — coming soon{T.RST}')
    _pause()

def _t_stats():
    _head('STATS')
    print(f'  {T.MUTE}stats module — coming soon{T.RST}')
    _pause()

def _t_paths():
    _head('OUTPUT PATHS')
    for lb, pp in [('data', data_dir()), ('license', license_path())]:
        print(f'  {T.PRI}·{T.RST} {T.MUTE}{pad_r(lb,10)}{T.RST} {T.DIM}{pp}{T.RST}')
    _pause()

def _t_help():
    _head('HELP')
    for n, d in [('Single Check','one device id'),('Bulk Check','file with ids'),
                 ('Compare','2 accounts'),('Generate IDs','random and_ ids'),
                 ('Merge','folder → dedupe'),('Paths','file locations')]:
        print(f'  {T.PRI}·{T.RST} {T.B}{T.TXT}{pad_r(n,16)}{T.RST} {T.MUTE}{d}{T.RST}')
    print(f'\n  {T.SEC}◆{T.RST} {T.MUTE}contact{_T.RST} {T.B}{OWNER_HANDLE}{T.RST}'.replace('_T','T'))
    _pause()

def _t_about():
    clear()
    print()
    print(f'  {T.PRI}{T.B}{BRAND}{T.RST} {T.SEC}{VERSION}{T.RST}')
    print(f'  {T.DIM}{"━"*46}{T.RST}')
    print()
    print(f'  {T.MUTE}version    {T.RST}{VERSION}')
    print(f'  {T.MUTE}contact    {T.RST}{OWNER_HANDLE}')
    print(f'  {T.MUTE}device id  {T.RST}{T.WARN}{get_device_id()}{T.RST}')
    print(f'  {T.MUTE}fingerprint{T.RST}{T.TEAL}{MODULE_FP}{T.RST}')
    print(f'  {T.MUTE}python     {T.RST}{sys.version.split()[0]}')
    print(f'  {T.MUTE}data dir   {T.RST}{data_dir()}')
    _pause()

# ═══ MAIN ═══
def main():
    license_gate()
    clear()
    print()
    print(f'  {T.PRI}{T.B}{BRAND}{T.RST} {T.SEC}{VERSION}{T.RST}')
    print(f'  {T.DIM}{"━"*46}{T.RST}')
    print(f'  {T.MUTE}device{T.RST}  {T.TXT}{get_device_id()}{T.RST}')
    while True:
        c = _menu()
        if c == '1': _t_single()
        elif c == '2': _t_bulk()
        elif c == '3': _t_compare()
        elif c == '4': _t_gen()
        elif c == '5': _t_merge()
        elif c == '6': _t_watch()
        elif c == '7': _t_hist()
        elif c == '8': _t_notes()
        elif c == '9': _t_search()
        elif c == 'T': _t_stats()
        elif c == 'P': _t_paths()
        elif c == '?': _t_help()
        elif c == '@': _t_about()
        elif c == '0':
            print(f'  {T.MUTE}bye{T.RST}'); return

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt: print()
    except Exception as e:
        print(f'\n  {T.ERR}✗ {e}{T.RST}')