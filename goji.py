#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Goji_Pogi - Protected Script
Generated: 2026-10-14
"""
print('[DEBUG] Script started')
import os as _o, sys as _s, time as _t, json as _j, base64 as _b
import hashlib as _h, platform as _p, uuid as _u, subprocess as _sp
import secrets as _sc, random as _r, socket as _so, struct as _st
import zlib as _z, threading as _th, datetime as _dt, re as _re
import hmac as _hm, csv as _c, shutil as _sh
from enum import Enum as _E
from collections import deque as _dq, Counter as _ct
from concurrent.futures import ThreadPoolExecutor as _TP, as_completed as _ac

_k = [b'Z29qaS1saWNlbnNlLm9ucmVuZGVyLmNvbQ==',
      b'YXBpL3Bpbmc=', b'YXBpL3ZlcmlmeQ==',
      b'R09KSS1NQVNURVItTElGRQ==',
      b'R09KSS1CQUNLVVAtMjAyNg==',
      b'Z29qaS13YXJwc2hpZWxkLTIwMjY=']

def _d(x): return _b.b64decode(x).decode()

_SRV = 'https://' + _d(_k[0])
_SIG = '@Goji_Pogi'
_BR = 'GOJI'
_VER = 'V2 ULTIMATE'
_MK = _d(_k[3])
_BK = _d(_k[4])
_HS = _d(_k[5])

class T:
    R='\033[0m'; B='\033[1m'; D='\033[2m'
    P='\033[38;5;117m'; S='\033[38;5;183m'; K='\033[38;5;121m'
    W='\033[38;5;222m'; E='\033[38;5;210m'
    T='\033[38;5;255m'; M='\033[38;5;245m'; X='\033[38;5;240m'

def _need():
    n = {'zstandard':'zstandard','Crypto':'pycryptodome',
         'urllib3':'urllib3','requests':'requests'}
    miss = [v for k,v in n.items() if not _has(k)]
    if miss:
        print(f'  [*] installing: {", ".join(miss)}')
        try: _sp.check_call([_s.executable,'-m','pip','install',
                             '--quiet','--disable-pip-version-check',*miss])
        except: _s.exit(1)

def _has(n):
    try: __import__(n); return True
    except: return False

_need()

import zstandard as _zs
import urllib3 as _ur
import requests as _rq
from Crypto.Cipher import AES as _AE
_ur.disable_warnings(_ur.exceptions.InsecureRequestWarning)

def _fp():
    p = []
    for f in (lambda: _p.node(), lambda: str(_u.getnode()),
              lambda: _p.system(), lambda: _p.machine()):
        try: p.append(f())
        except: pass
    try: p.append(_o.environ.get('USERNAME') or _o.environ.get('USER') or '')
    except: pass
    return _h.sha256('|'.join(str(x) for x in p if x).encode()).hexdigest()[:8].upper()

def _selfsig():
    try:
        with open(_o.path.abspath(__file__),'rb') as f: raw = f.read()
        m = b'#__SIG__='
        if m in raw: raw = raw.split(m)[0]
        return _h.sha256(raw + _HS.encode()).hexdigest()[:12]
    except: return 'unknown'

_FP = _selfsig()

def _sign(pl, n):
    m = _j.dumps(pl, sort_keys=True)+'|'+n+'|'+_FP
    return _hm.new(_HS.encode(), m.encode(), _h.sha256).hexdigest()[:16]

def _nonce(): return _sc.token_hex(8)

def _ddir():
    d = _o.path.join(_o.path.expanduser('~'), f'.{_BR.lower()}')
    _o.makedirs(d, exist_ok=True); return d

def _lic(): return _o.path.join(_ddir(), 'lic.json')
def _bk(): 
    d = _o.path.join(_ddir(), 'warp'); _o.makedirs(d, exist_ok=True)
    return _o.path.join(d, 'data.enc')

def _get_lic(dev):
    try:
        p = _lic()
        if not _o.path.exists(p): return None
        with open(p,'r') as f: d = _j.load(f)
        return d.get(dev,{}).get('k')
    except: return None

def _set_lic(dev, k, e=None):
    try:
        p = _lic(); d = {}
        if _o.path.exists(p):
            with open(p,'r') as f: d = _j.load(f)
        d[dev] = {'k':k,'e':e,'ok':_t.time()}
        with open(p,'w') as f: _j.dump(d, f, indent=2)
    except: pass

def _clr_lic(dev):
    try:
        p = _lic()
        if not _o.path.exists(p): return
        with open(p,'r') as f: d = _j.load(f)
        d.pop(dev, None)
        with open(p,'w') as f: _j.dump(d, f, indent=2)
    except: pass

def _ping():
    try:
        pl = {'fp':_FP, 'n':_nonce()}; pl['s'] = _sign(pl, pl['n'])
        r = _rq.post(f'{_SRV}/{_d(_k[1])}', json=pl, timeout=6, verify=False)
        return r.json()
    except Exception as e: return {'on':False,'mode':'?','msg':str(e)[:40]}

def _verify(dev, k=None):
    try:
        pl = {'device_id':dev,'key':k,'fp':_FP,'n':_nonce(),'ts':int(_t.time())}
        pl['s'] = _sign(pl, pl['n'])
        r = _rq.post(f'{_SRV}/{_d(_k[2])}', json=pl, timeout=8, verify=False)
        return r.json()
    except _rq.exceptions.Timeout: return {'status':'error','msg':'timeout'}
    except _rq.exceptions.ConnectionError: return {'status':'error','msg':'offline'}
    except Exception as e: return {'status':'error','msg':str(e)[:60]}

def _wm(dev, mode):
    base = _MK if mode=='own' else _BK
    return _h.sha256(f'{base}|{dev}|{_HS}'.encode()).digest()

def _wenc(dev, mode, pl):
    key = _wm(dev, mode); iv = _h.md5(f'{dev}-{mode}'.encode()).digest()[:16]
    raw = _j.dumps(pl).encode(); pad = 16-(len(raw)%16); raw += bytes([pad])*pad
    return _AE.new(key, _AE.MODE_CBC, iv=iv).encrypt(raw)

def _wdec(dev, mode, data):
    try:
        key = _wm(dev, mode); iv = _h.md5(f'{dev}-{mode}'.encode()).digest()[:16]
        pt = _AE.new(key, _AE.MODE_CBC, iv=iv).decrypt(data)
        return _j.loads(pt[:-pt[-1]].decode())
    except: return None

def _wstore(dev, mode, pl):
    try:
        with open(_bk(),'wb') as f: f.write(_b.b64encode(_wenc(dev, mode, pl)))
        return True
    except: return False

def _wload(dev, mode):
    try:
        p = _bk()
        if not _o.path.exists(p): return None
        with open(p,'rb') as f: e = _b.b64decode(f.read())
        return _wdec(dev, mode, e)
    except: return None

def _wopen(dev, own=False):
    try:
        m = 'own' if own else 'usr'
        d = _wload(dev, m)
        if d:
            s = d.get('sig')
            e = _hm.new(_HS.encode(), (dev+_MK).encode(), _h.sha256).hexdigest()[:16]
            if s == e: return True
        if own:
            s = _hm.new(_HS.encode(), (dev+_MK).encode(), _h.sha256).hexdigest()[:16]
            return _wstore(dev, 'own', {'dev':dev,'sig':s,'b':_t.time()})
        return False
    except: return False

def _box(txt, col=None):
    c = col or T.P
    l = txt.split('\n'); w = max(len(x) for x in l)+4
    print()
    print(f'  {c}╔{"═"*w}╗{T.R}')
    for x in l:
        p = ' '*(w-2-len(x)); print(f'  {c}║{T.R}  {x}{p}{c}║{T.R}')
    print(f'  {c}╚{"═"*w}╝{T.R}'); print()

def _fe(ts):
    if not ts: return 'never'
    try: return _dt.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
    except: return '?'

def _gate():
    dev = _fp(); stored = _get_lic(dev)
    while True:
        _o.system('cls' if _o.name=='nt' else 'clear')
        print()
        print(f'  {T.P}{T.B}{_BR}{T.R} {T.S}{_VER}{T.R}  {T.X}· fp {_FP}{T.R}')
        print(f'  {T.X}{"━"*46}{T.R}')
        print()
        print(f'  {T.M}connecting to server...{T.R}')
        _t.sleep(0.3)
        pi = _ping(); m = pi.get('mode','?')
        if m == 'locked' or not pi.get('on', False):
            _box(f'{T.E}✗ SERVER OFFLINE{T.R}\n\n{T.M}{pi.get("msg","locked")}{T.R}', T.E)
            print(f'  {T.M}1{T.R} retry · {T.M}2{T.R} warp · {T.M}0{T.R} exit')
            try: c = input(f'  {T.P}›{T.R} ').strip()
            except: _s.exit(0)
            if c=='0': _s.exit(0)
            if c=='2' and _wopen(dev): return stored or 'warp'
            continue
        r = _verify(dev, stored); st = r.get('status')
        if st == 'backup':
            if _wopen(dev):
                _box(f'{T.K}✓ BACKUP MODE{T.R}', T.K); _t.sleep(1); return stored or 'warp'
            _box(f'{T.E}✗ blocked{T.R}', T.E); _t.sleep(1.5); continue
        if st == 'ok':
            _box(f'{T.K}✓ ACCESS GRANTED{T.R}\n\n'
                 f'{T.M}tier:{T.R} {T.W}{r.get("tier","standard")}{T.R}\n'
                 f'{T.M}expires:{T.R} {T.T}{_fe(r.get("expires"))}{T.R}', T.K)
            _t.sleep(1); return stored or 'ok'
        if st == 'no_key':
            _box(f'{T.W}❌ ACCESS DENIED{T.R}\n\n'
                 f'{T.M}Your Device ID:{T.R}  {T.B}{T.T}{dev}{T.R}\n\n'
                 f'{T.P}▸ Contact {_SIG} to purchase a key!{T.R}', T.W)
            try: k = input(f'  {T.P}›{T.R} ').strip().lower()
            except: _s.exit(0)
            if not k: continue
            if k == 'warp':
                if _wopen(dev): return stored or 'warp'
                continue
            if k in (_MK.lower(), _BK.lower()):
                if _wopen(dev, own=True):
                    _box(f'{T.K}✓ BACKUP MODE{T.R}', T.K); _t.sleep(1); return k
                continue
            if not _re.match(r'^[a-z]{3}-[a-z]{3}-[a-z]{3}$', k):
                print(f'  {T.E}✗ format: xxx-xxx-xxx{T.R}'); _t.sleep(1.5); continue
            stored = k; _set_lic(dev, stored); continue
        if st in ('expired','revoked','mismatch'):
            msgs = {'expired':f'{T.E}Key expired{T.R}',
                    'revoked':f'{T.E}Key revoked{T.R}',
                    'mismatch':f'{T.E}Bound to another device{T.R}'}
            _box(f'{T.E}❌ ACCESS DENIED{T.R}\n\n{msgs[st]}\n\n'
                 f'{T.M}Your Device ID:{T.R}  {T.B}{T.T}{dev}{T.R}\n\n'
                 f'{T.P}▸ Contact {_SIG}{T.R}', T.E)
            print(f'  {T.M}1 retry · 2 warp · 0 exit{T.R}')
            try: c = input(f'  {T.P}›{T.R} ').strip()
            except: _s.exit(0)
            if c=='0': _s.exit(0)
            if c=='2' and _wopen(dev): return stored or 'warp'
            _clr_lic(dev); stored = None; continue
        print(f'  {T.E}✗ {r.get("msg","unknown")}{T.R}')
        print(f'  {T.M}1 retry · 2 warp · 0 exit{T.R}')
        try: c = input(f'  {T.P}›{T.R} ').strip()
        except: _s.exit(0)
        if c=='0': _s.exit(0)
        if c=='2' and _wopen(dev): return stored or 'warp'

# ═══ SDP ═══
class _ET(_E):
    A=0; B=1; C=2; D=3; E=4; F=5; G=6; H=7; I=8

class _XE(Exception): pass

def _srt(x):
    k = x[0]
    return (0,k) if isinstance(k,int) else (1,str(k))

class _PK(dict):
    def __init__(self, data=None):
        super().__init__()
        self.data = b''; self.off = 0
        if isinstance(data, bytes): self.data = data; self._du()
        elif data is not None: super().update(data); self._pk()
    def _pk(self):
        self.data = bytes([_ET.H.value<<4])
        for t,v in sorted(self.items(), key=_srt): self._wv(t,v)
        self.data += bytes([_ET.I.value<<4])
    def _du(self):
        if not self.data: return
        if self.data[0]>>4 == _ET.H.value: self.off = 1
        while self.off < len(self.data):
            t,v = self._rv()
            if isinstance(v,_ET) and v == _ET.I: break
            self[t] = v
    def _en(self,v):
        r = bytearray()
        while v >= 0x80: r.append((v&0x7F)|0x80); v >>= 7
        r.append(v&0x7F); return bytes(r)
    def _dn(self):
        if self.off >= len(self.data): raise _XE('eof')
        n = 1; val = self.data[self.off]&0x7F
        while self.data[self.off+n-1] >= 0x80:
            if self.off+n >= len(self.data): raise _XE('trunc')
            val |= (self.data[self.off+n]&0x7F)<<(7*n); n += 1
        self.off += n; return val
    def _tg(self,tag,dt):
        if tag < 15: self.data += bytes([(dt.value<<4)|tag])
        else:
            self.data += bytes([(dt.value<<4)|15]); self.data += self._en(tag)
    def _wv(self,tag,val):
        if isinstance(val,bool):
            self._tg(tag,_ET.A); self.data += self._en(1 if val else 0)
        elif isinstance(val,int):
            if val < 0: self._tg(tag,_ET.B); self.data += self._en(-val)
            else: self._tg(tag,_ET.A); self.data += self._en(val)
        elif isinstance(val,float):
            self._tg(tag,_ET.D); pk = _st.pack('<d',val)
            self.data += self._en(len(pk))+pk
        elif isinstance(val,(str,bytes)):
            self._tg(tag,_ET.E)
            e = val.encode() if isinstance(val,str) else val
            self.data += self._en(len(e))+e
        elif isinstance(val,list):
            self._tg(tag,_ET.F); self.data += self._en(len(val))
            for it in val: self._wv(0,it)
        elif isinstance(val,dict):
            if isinstance(val,_PK):
                self._tg(tag,_ET.H)
                for k,v in sorted(val.items(), key=_srt): self._wv(k,v)
                self.data += bytes([_ET.I.value<<4])
            else:
                self._tg(tag,_ET.G); self.data += self._en(len(val))
                for k,v in sorted(val.items(), key=_srt):
                    self._wv(0,k); self._wv(0,v)
        else: raise _XE('bad')
    def _rv(self):
        try:
            if self.off >= len(self.data): return 0,None
            h = self.data[self.off]
            tag = h&0xF; dt = _ET(h>>4); self.off += 1
            if tag == 15: tag = self._dn()
            if dt == _ET.A: return tag,self._dn()
            if dt == _ET.B: return tag,-self._dn()
            if dt == _ET.C: return tag,_st.unpack('<f',self._dn().to_bytes(4,'little'))[0]
            if dt == _ET.D: return tag,_st.unpack('<d',self._dn().to_bytes(8,'little'))[0]
            if dt == _ET.E:
                n = self._dn(); ch = self.data[self.off:self.off+n]
                try: v = ch.decode()
                except: v = ch
                self.off += n; return tag,v
            if dt == _ET.F:
                n = self._dn(); v = []
                for _ in range(n):
                    _,it = self._rv(); v.append(it)
                return tag,v
            if dt == _ET.G:
                n = self._dn(); v = {}
                for _ in range(n):
                    _,k = self._rv(); _,x = self._rv(); v[k] = x
                return tag,v
            if dt == _ET.H:
                sub = {}
                while True:
                    st,sv = self._rv()
                    if isinstance(sv,_ET) and sv == _ET.I: break
                    sub[st] = sv
                return tag,_PK(sub)
            if dt == _ET.I: return tag,_ET.I
            raise _XE('bad')
        except _XE: raise
        except: raise _XE('unpack')

_AK = bytes.fromhex('f5a193d50ade553e9835595f5cd75ddd')
_AIV = b'\x00'*16
def _aes(d):
    if not d or len(d)%16: raise _XE('cipher')
    return _AE.new(_AK,_AE.MODE_CBC,iv=_AIV).decrypt(d).rstrip(b'\x00')

_LH = 'login.ml.youngjoygame.com'
_LP = 30021
_CV = '2.2.16.1232.1'
_CH = 'and_usa'
_IDRE = _re.compile(r'(?:and|ios)_[0-9A-Za-z]{16,128}(?:-[0-9a-fA-F]{4,16}){3,6}')

_DNS = {}; _DL = _th.Lock()
def _rsv(h):
    if not h or _re.match(r'^\d+\.\d+\.\d+\.\d+$',h): return h
    n = _t.time()
    with _DL:
        x = _DNS.get(h)
        if x and x[1] > n: return x[0]
    try: ip = _so.gethostbyname(h)
    except: ip = h
    with _DL: _DNS[h] = (ip,n+600)
    return ip

class _GC:
    def __init__(self, dev):
        self.dev = dev; self.h = _LH; self.p = _LP
        self.sq = 1; self.sk = None; self.q = b''; self.lh = 0
        p = dev.split('_')
        if len(p) >= 2:
            i = p[1]
            if len(p) >= 3 and len(i) < 32: i += '_'+p[2]
            if len(i) >= 32:
                self.md5 = i[:32]
                self.and_id = i[32:48] if len(i) >= 48 else ''
                self.adid = i[48:] if len(i) > 48 else ''
            else: self.md5 = i; self.and_id = ''; self.adid = ''
        else: self.md5 = dev; self.and_id = ''; self.adid = ''
        self.acct = 0; self.skey = ''; self.zone = 0
        self.gh = ''; self.gp = 0; self.cts = 0
    def op(self, h=None, p=None):
        if h: self.h = h
        if p: self.p = p
        ip = _rsv(self.h)
        self.sk = _so.socket(_so.AF_INET,_so.SOCK_STREAM)
        try: self.sk.setsockopt(_so.IPPROTO_TCP,_so.TCP_NODELAY,1)
        except: pass
        self.sk.settimeout(8); self.sk.connect((ip,self.p))
    def cl(self):
        if self.sk:
            try: self.sk.close()
            except: pass
        self.sk = None; self.sq = 1; self.q = b''
    def put(self, pid, pk):
        p = _PK({0:pid,1:self.sq,5:pk.data}).data
        buf = _zs.compress(p); sz = len(buf)+4
        if sz > 0xFFFFFF: raise _XE('large')
        self.sk.send((sz|(16<<24)).to_bytes(4,'big')+buf)
        self.sq += 1
    def get(self):
        try:
            while len(self.q) < 4:
                d = self.sk.recv(4096)
                if not d: return None,None
                self.q += d
            fl = int.from_bytes(self.q[:4],'big')
            sz = fl & 0xFFFFFF; ct = fl >> 24
            self.lh = sz
            while len(self.q) < sz:
                d = self.sk.recv(4096)
                if not d: return None,None
                self.q += d
            data = self.q[4:sz]; self.q = self.q[sz:]
            if ct == 1: data = _z.decompress(data)
            elif ct == 16: data = _zs.decompress(data)
            elif ct == 2: data = _aes(data)
            elif ct == 3: data = _z.decompress(_aes(data))
            elif ct == 18: data = _zs.decompress(_aes(data))
            r = _PK(data); pid = r[0]
            if pid is None: return None,None
            b = r.get(6)
            if not isinstance(b,bytes):
                b = r.get(5)
                if not isinstance(b,bytes): return pid,None
            return pid,_PK(b)
        except _so.timeout: return -1,None
        except: return None,None
    def login(self):
        self.op(_LH,_LP)
        self.put(1,_PK({0:self.dev,
            1:f'gps_adid={self.adid}&android_id={self.and_id}&device_unique_id={self.md5}',
            2:_CV,3:_CH,4:'en'}))
        pid,res = self.get()
        if pid == 2 and res:
            self.acct = res.get(0); self.skey = res.get(1)
            zd = res.get(2)
            if isinstance(zd,dict): self.zone = zd.get(0,0)
            elif isinstance(zd,list) and zd:
                self.zone = zd[0] if not isinstance(zd[0],dict) else zd[0].get(0,0)
            else: self.zone = zd or 0
            self.cts = res.get(19,0)
            s = str(self.acct)
            if s.startswith('221') or s.startswith('222'): return False,res
            return True,res
        return False,res
    def srv(self):
        self.put(5,_PK({0:self.acct,1:self.skey,2:_CV,5:self.zone,6:_CH}))
        pid,res = self.get()
        if pid == 6 and res:
            a = res[1]; self.gh,gp = a.split(':')
            self.gp = int(gp); return True,res
        return False,res
    def join(self):
        self.cl(); self.op(self.gh,self.gp)
        self.put(10001,_PK({0:self.acct,1:self.skey,2:self.zone,
                            4:_CV,13:_CH,15:self.dev}))
        self.put(10101,_PK({0:0,2:2}))
    def sync(self,t=25):
        for _ in range(t):
            pid,_ = self.get()
            if pid is None or pid == -1: return False
            if pid == 10002: return True
        return False
    def find(self,val,kind='id'):
        if kind == 'id':
            try: pk = _PK({1:int(val)})
            except: return None
        else: pk = _PK({0:str(val).strip()})
        self.put(11153,pk); miss = 0
        while True:
            pid,res = self.get()
            if pid is None or pid == -1: return None
            if pid == 11154: return res
            if pid == 20001:
                miss += 1
                if self.lh < 100 and miss >= 3: return None

_BR2 = {'21':'Plug-in','22':'Sharing','23':'Toxic','24':'Ranked cheat',
        '25':'Fraud','26':'Trade','27':'AFK','28':'Feed','29':'Hate',
        '30':'3rd-party','31':'Malice','32':'Fraud','33':'Spam','34':'Evade',
        '35':'Harass','36':'Match fix','37':'Multi','38':'Sale','39':'Cheat','40':'Bot'}

def _walk(o,p='',d=0,mx=8):
    if d > mx: return
    if isinstance(o,dict):
        for k,v in o.items():
            yield (p,k,v)
            if isinstance(v,(dict,list)): yield from _walk(v,f'{p}/{k}',d+1,mx)
    elif isinstance(o,list):
        for i,it in enumerate(o):
            if isinstance(it,(dict,list)): yield from _walk(it,f'{p}[{i}]',d+1,mx)

def _ban(sdp):
    r = {'b':False,'r':None,'c':None,'d':None,'cf':0}
    if sdp is None: return False,r
    ed = eh = em = None; bc = None
    try:
        for _,k,v in _walk(dict(sdp)):
            ks = str(k)
            if ks == 'ban_reason':
                c = str(v)
                if c in _BR2: bc = c; r['c'] = c; r['r'] = _BR2[c]
            elif ks == 'endtime_day' and v is not None:
                ed = int(v) if str(v).lstrip('-').isdigit() else 0
            elif ks == 'endtime_hour' and v: eh = int(v) if str(v).isdigit() else 0
            elif ks == 'endtime_min' and v: em = int(v) if str(v).isdigit() else 0
    except: pass
    b = False
    if ed is not None and ed > 0:
        b = True; r['d'] = f"{ed}d {(eh or 0):02d}h {(em or 0):02d}m"; r['cf'] = 100
    if bc: b = True; r['cf'] = max(r['cf'],90)
    r['b'] = b
    return b,r

_HE = {1:"Miya",2:"Balmond",3:"Saber",4:"Alice",5:"Nana",6:"Tigreal",7:"Alucard",
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
    except: return "Unranked"
    if p <= 0: return "Unranked"
    T2 = [(0,4,"Warrior III"),(5,9,"Warrior II"),(10,14,"Warrior I"),
        (15,19,"Elite IV"),(20,24,"Elite III"),(25,29,"Elite II"),(30,34,"Elite I"),
        (35,39,"Master IV"),(40,44,"Master III"),(45,49,"Master II"),(50,54,"Master I"),
        (55,59,"GM IV"),(60,64,"GM III"),(65,69,"GM II"),(70,74,"GM I"),
        (75,81,"Epic IV"),(82,88,"Epic III"),(89,95,"Epic II"),(96,107,"Epic I"),
        (108,114,"Legend IV"),(115,121,"Legend III"),(122,128,"Legend II"),(129,135,"Legend I")]
    for lo,hi,n in T2:
        if lo <= p <= hi: return n
    if 136 <= p <= 160: return f"Mythic {p-135}"
    if 161 <= p <= 195: return f"Mythical Honor {p-135}"
    if 196 <= p <= 235: return f"Mythical Glory {p-195}"
    if p >= 236: return f"Mythical Immortal {p-235}"
    return "Unranked"

_CL = [
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

def _ci(p):
    try: pts = int(p)
    except: pts = 0
    pts = max(0,pts)
    rm = ['V','IV','III','II','I']
    for i,e in enumerate(_CL):
        if e['min'] <= pts < e['max']:
            n = e['n']
            if n == 'New Collector': return {'tier':n,'points':pts}
            if n == 'World Collector': return {'tier':n,'points':pts}
            span = (e['max']-e['min'])/5
            lv = max(0,min(4,int((pts-e['min'])//span)))
            return {'tier':f'{n} {rm[lv]}','points':pts}
    return _ci(999999)

def _skins(t):
    if not t or not isinstance(t,dict): return {}
    d = None
    for k in (4,0,1):
        v = t.get(k)
        if isinstance(v,dict) and v: d = v; break
    if d is None: d = t
    if not isinstance(d,dict): return {}
    km = {6:"Supreme",5:"Grand",4:"Exquisite",3:"Deluxe",2:"Exceptional",1:"Common"}
    o = {}
    for sid,c in d.items():
        try: i = int(sid)
        except: continue
        if i in km: o[km[i]] = c
    return o

def _lm(ri,p):
    cs = []
    for src in (ri,p):
        if not isinstance(src,dict): continue
        for tag in (120,130,145,150,190,200,33,35,40,55,70,78,85,88,99,105,110,100):
            v = src.get(tag)
            if isinstance(v,(dict,list)) and v: cs.append(v)
    e = None
    for c in cs:
        if isinstance(c,list) and c and isinstance(c[0],dict): e = c[0]; break
        if isinstance(c,dict):
            for k in sorted(c.keys(), key=lambda x:(isinstance(x,str),x)):
                if isinstance(c[k],dict): e = c[k]; break
            if e: break
    if not e: return None
    hid = e.get(0,0) or e.get(1,0) or 0
    h = _HE.get(hid,f"H{hid}") if hid else "?"
    k = int(e.get(2,0) or 0); d = int(e.get(3,0) or 0); a = int(e.get(4,0) or 0)
    return {'hero':h,'kda':f'{k}/{d}/{a}',
            'result':'WIN' if e.get(6) in (1,'1','win',True) else 'LOSS'}

def _ex(result, cts=0):
    if not result or not result.get(0): return None
    f = result[0]
    if isinstance(f,dict): p = f
    elif isinstance(f,list) and f and isinstance(f[0],dict): p = f[0]
    else: return None
    try:
        nick = p.get(2,"") or "?"
        pid = p.get(0,0); srv = p.get(1,0)
        lv = int(p.get(3,0) or 0); sc = int(p.get(83,0) or 0); hc = int(p.get(4,0) or 0)
        rn = _rank(p.get(8))
        t136 = p.get(136,{})
        cp = t136.get(9,0) if isinstance(t136,dict) else 0
        tb = p.get(17,0) or 0
        dia = 0
        cur = p.get(111)
        if isinstance(cur,dict): dia = int(cur.get(0,0) or 0)
        sk = {"Supreme":0,"Grand":0,"Exquisite":0,"Deluxe":0,"Exceptional":0,"Common":0}
        if p.get(118):
            ps = _skins(p.get(118))
            if ps: sk.update(ps)
        ci = _ci(cp)
        rare = sk.get('Supreme',0)+sk.get('Grand',0)+sk.get('Exquisite',0)
        score = (min(2000,sc*3)+min(1000,hc*2)+min(2000,cp//50)+
                 min(1000,lv*5)+min(500,dia//10)+rare*15)
        g = "S" if score>=5000 else "A" if score>=3500 else "B" if score>=2000 else "C" if score>=1000 else "D" if score>=400 else "E"
        return {'nickname':nick,'player_id':pid,'server':srv,'level':lv,
                'skin_count':sc,'hero_count':hc,'current_rank':rn,
                'collector_point':cp,'collector_tier':ci['tier'],
                'total_battles':tb,'diamonds':dia,'skin_breakdown':sk,
                'rare_skins':rare,'account_score':score,'account_grade':g,
                'last_match':_lm({},p),
                'ban_status':'CLEAN','ban_reason':None,'ban_duration':None}
    except: return None

def _fetch(dev):
    c = _GC(dev)
    try:
        ok,_ = c.login()
        if not ok: return {'status':'error','error':'login'}
        aid = c.acct; zid = c.zone; cts = c.cts
        ok,_ = c.srv()
        if not ok: return {'status':'error','error':'server'}
        c.join()
        if not c.sync(): return {'status':'error','error':'hs'}
        r = c.find(int(aid),'id')
        if not r: return {'status':'error','error':'empty'}
        b,rpt = _ban(r)
        pl = _ex(r,cts)
        if not pl: return {'status':'error','error':'extract'}
        if b:
            pl['ban_status'] = 'BANNED'
            pl['ban_reason'] = rpt.get('r')
            pl['ban_duration'] = rpt.get('d') or 'permanent'
        return {'status':'success','player':pl,'device_id':dev,
                'account_id':aid,'zone_id':zid}
    except Exception as e:
        return {'status':'error','error':type(e).__name__}
    finally: c.cl()

_OUT = _ddir()

def _wl(p,l):
    try:
        with open(p,'a',encoding='utf-8') as f: f.write(l+'\n')
    except: pass

def _pp(p):
    ci = _ci(p.get('collector_point',0))
    ban = p.get('ban_status') == 'BANNED'
    print()
    print(f'  {T.B}{T.T}{p.get("nickname","?")}{T.R}  {T.X}·{T.R}  {T.W}Lv{p.get("level")}{T.R}')
    print(f'  {T.M}rank   {T.R}{p.get("current_rank")}')
    print(f'  {T.M}collect{T.R} {ci.get("tier")}')
    print(f'  {T.M}heroes {T.R}{p.get("hero_count")}  {T.M}skins {T.R}{p.get("skin_count")}  {T.M}rare {T.R}{p.get("rare_skins")}')
    print(f'  {T.M}score  {T.R}{p.get("account_score",0):,}  {T.M}grade {T.R}{p.get("account_grade")}')
    if ban:
        print(f'  {T.M}ban    {T.R}{T.E}{T.B}BANNED{T.R}  {T.X}{p.get("ban_reason")}{T.R}')
    else:
        print(f'  {T.M}ban    {T.R}{T.K}CLEAN{T.R}')

def _pause():
    try: input(f'  {T.X}enter...{T.R}')
    except: print()

def _menu():
    print()
    print(f'  {T.P}◆{T.R}  {T.B}{T.S}{_BR} MENU{T.R}')
    print(f'  {T.X}{"─"*44}{T.R}')
    print()
    for k,lb in [('1','Single Check'),('2','Bulk Check'),('3','Compare'),
                 ('4','Generate IDs'),('5','Merge'),('6','Watchlist'),
                 ('7','History'),('8','Notes'),('9','Search'),('T','Stats'),
                 ('P','Paths'),('0','Exit')]:
        print(f'  {T.P}│{T.R}  {T.P}{T.B}[{k}]{T.R}  {T.T}{lb}{T.R}')
    print()
    v = {'1','2','3','4','5','6','7','8','9','T','P','0'}
    while True:
        try: c = input(f'  {T.P}›{T.R} ').strip().upper()
        except: return '0'
        if c in v: return c

def _t_single():
    print()
    print(f'  {T.P}◆{T.R}  {T.B}{T.T}SINGLE CHECK{T.R}')
    print()
    try: dev = input(f'  {T.P}›{T.R} device id  ').strip()
    except: return
    if not _IDRE.match(dev):
        print(f'  {T.E}✗ invalid{T.R}'); _t.sleep(1); return
    print(f'  {T.M}checking...{T.R}')
    r = _fetch(dev)
    if r.get('status') != 'success':
        print(f'  {T.E}✗ {r.get("error")}{T.R}'); _t.sleep(1.5); return
    p = r['player']
    _pp(p)
    f = _o.path.join(_OUT,'full_info.txt')
    _wl(f, f"{dev} | {p.get('nickname')} | {p.get('current_rank')} | lv{p.get('level')} | {p.get('account_grade')}")
    print(f'\n  {T.K}✓ saved{T.R}')
    _pause()

def _t_bulk():
    print()
    print(f'  {T.P}◆{T.R}  {T.B}{T.T}BULK CHECK{T.R}')
    print()
    try: path = input(f'  {T.P}›{T.R} file  ').strip()
    except: return
    if not _o.path.exists(path):
        print(f'  {T.E}✗ not found{T.R}'); _t.sleep(1); return
    try:
        with open(path,'r',errors='replace') as f: txt = f.read()
    except: return
    ids = list(dict.fromkeys(m.group(0) for m in _IDRE.finditer(txt)))
    if not ids: print(f'  {T.E}✗ empty{T.R}'); _t.sleep(1); return
    print(f'  {T.M}{len(ids)} ids{T.R}')
    clean = banned = errs = 0
    with _TP(max_workers=10) as ex:
        futs = [ex.submit(_fetch,d) for d in ids]
        for i,f in enumerate(_ac(futs),1):
            try:
                r = f.result()
                if r.get('status') == 'success':
                    if r['player'].get('ban_status') == 'BANNED': banned += 1
                    else: clean += 1
                else: errs += 1
            except: errs += 1
            print(f'\r  {i}/{len(ids)}  {T.K}clean {clean}{T.R}  {T.E}ban {banned}{T.R}  {T.W}err {errs}{T.R}  ', end='', flush=True)
    print()
    print(f'  {T.K}✓ done{T.R}')
    _pause()

def _t_gen():
    print()
    try: n = int(input(f'  {T.P}›{T.R} count  ').strip() or '10')
    except: n = 10
    ids = []
    for _ in range(n):
        imei = ''.join(_r.choice('0123456789abcdef') for _ in range(32))
        andr = ''.join(_r.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(16))
        adid = '-'.join([''.join(_r.choice('0123456789abcdef') for _ in range(x)) for x in (8,4,4,4,12)])
        ids.append(f'and_{imei}{andr}{adid}')
    out = _o.path.join(_OUT, f'gen_{n}.txt')
    with open(out,'w') as f:
        for d in ids: f.write(d+'\n')
    print(f'  {T.K}✓ {n} → {out}{T.R}'); _pause()

def _t_paths():
    print()
    for lb,p in [('data',_OUT),('full',_o.path.join(_OUT,'full_info.txt'))]:
        print(f'  {T.P}·{T.R} {T.M}{lb:10}{T.R} {T.X}{p}{T.R}')
    _pause()

def main():
    _gate()
    _o.system('cls' if _o.name=='nt' else 'clear')
    print()
    print(f'  {T.P}{T.B}{_BR}{T.R} {T.S}{_VER}{T.R}')
    print(f'  {T.X}{"━"*46}{T.R}')
    print(f'  {T.M}device{_T.R}  {T.T}{_fp()}{_T.R}'.replace('_T',''))
    while True:
        c = _menu()
        if c == '1': _t_single()
        elif c == '2': _t_bulk()
        elif c == '4': _t_gen()
        elif c == 'P': _t_paths()
        elif c == '0':
            print(f'  {T.M}bye{T.R}'); return

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt: print()
    except Exception as e:
        print(f'\n  {T.E}✗ {e}{T.R}')