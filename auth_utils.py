"""
Pascalle Store — Autenticación JWT + bcrypt
"""
import jwt, bcrypt, json
from datetime import datetime, timedelta

import os
SECRET_KEY = os.environ.get("SECRET_KEY", "pascalle-store-secret-key-2026-change-in-production")
ALGORITHM  = "HS256"
TOKEN_EXP_HOURS = 24

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except:
        return False

def create_token(user_id: int, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXP_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception as e:
        print(f"[AUTH ERROR] decode_token failed: {e}", flush=True)
        return None

def get_token_from_request(handler) -> dict | None:
    """Extrae y valida el token JWT del cookie o header Authorization."""
    # Buscar en cookie
    cookie_header = handler.headers.get('Cookie', '')
    token = None
    for part in cookie_header.split(';'):
        part = part.strip()
        if part.startswith('auth_token='):
            token = part[len('auth_token='):]
            break
    # Buscar en header Authorization: Bearer <token>
    has_auth_header = False
    if not token:
        auth_header = handler.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            has_auth_header = True
    print(f"[AUTH] cookie={'YES' if cookie_header else 'NO'} bearer={'YES' if has_auth_header else 'NO'} token={'FOUND' if token else 'MISSING'}", flush=True)
    if not token:
        return None
    return decode_token(token)

def require_role(handler, *roles):
    """Retorna el payload del token si tiene alguno de los roles. Si no, envía 401."""
    payload = get_token_from_request(handler)
    if not payload:
        send_json(handler, 401, {"error": "No autenticado"})
        return None
    if payload.get('role') not in roles:
        send_json(handler, 403, {"error": "Sin permiso"})
        return None
    return payload

def send_json(handler, status: int, data: dict):
    body = json.dumps(data, ensure_ascii=False).encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', len(body))
    handler.end_headers()
    handler.wfile.write(body)
