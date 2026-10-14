# GOJI V2 ULTIMATE

## files
- `goji_client.py`   — client (distribute to customers)
- `goji_server.py`   — flask server (deploy to Render)
- `build_pyarmor.sh` — protection script

## deploy server (Render)
1. push to GitHub
2. Render → New Web Service → connect repo
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn goji_server:app --bind 0.0.0.0:$PORT`
5. Env vars:
   - `OWNER_PASS` = your_password
   - `OWNER_HANDLE` = @Goji_Pogi
   - `BRAND` = GOJI
   - `HMAC_SALT` = goji-warpshield-2026

## protect client (PyArmor)
```bash
pip install pyarmor
bash build_pyarmor.sh