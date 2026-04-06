#!/usr/bin/env python3
"""
Pascalle Store — Servidor Web Principal
Ejecutar con: python3 server.py
"""
import http.server, socketserver, json, os, re, cgi, io, threading
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import database as db
import auth_utils as auth

PORT = int(os.environ.get('PORT', 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'uploads')

MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.pdf': 'application/pdf',
}

def read_template(name):
    path = os.path.join(TEMPLATES_DIR, name)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

class PascalleHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # Silenciar logs del servidor

    def send_html(self, html, status=200):
        body = html.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data, status=200):
        auth.send_json(self, status, data)

    def redirect(self, location):
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()

    def set_auth_cookie(self, token):
        self.send_header('Set-Cookie', f'auth_token={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400')

    def clear_auth_cookie(self):
        self.send_header('Set-Cookie', 'auth_token=; Path=/; HttpOnly; Max-Age=0')

    def get_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(length) if length else b''

    def get_json_body(self):
        try:
            return json.loads(self.get_body())
        except:
            return {}

    # ── GET ──────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        # Static files
        if path.startswith('/static/'):
            self.serve_static(path)
            return

        # API routes
        if path.startswith('/api/'):
            self.handle_api_get(path, parse_qs(parsed.query))
            return

        # Reset admin (ruta temporal de diagnóstico)
        if path == '/reset-admin':
            self._reset_admin()
            return

        # Page routes
        routes = {
            '': 'landing.html',
            '/': 'landing.html',
            '/login': 'login.html',
            '/registro': 'registro.html',
            '/dashboard': 'dashboard.html',
            '/dashboard/cargas': 'cargas.html',
            '/dashboard/pagos': 'pagos.html',
            '/dashboard/tracking': 'tracking.html',
            '/dashboard/perfil': 'perfil.html',
            '/admin': 'admin.html',
            '/admin/cargas': 'admin_cargas.html',
            '/admin/cobros': 'admin_cobros.html',
            '/admin/clientes': 'admin_clientes.html',
            '/admin/conciliacion': 'admin_conciliacion.html',
            '/logout': '__logout__',
        }

        if path == '/logout' or path == '':
            if path == '/logout':
                self.send_response(302)
                self.clear_auth_cookie()
                self.send_header('Location', '/')
                self.end_headers()
                return
            path = '/'

        template_name = routes.get(path)
        if template_name:
            html = read_template(template_name)
            if html:
                self.send_html(html)
            else:
                self.send_html(f"<h1>404 - Página no encontrada: {path}</h1>", 404)
        else:
            self.send_html("<h1>404</h1>", 404)

    def _reset_admin(self):
        """Ruta temporal para resetear el admin. Visitar una vez y luego quitar."""
        import sqlite3, bcrypt
        try:
            pw = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()
            conn = sqlite3.connect(db.DB_PATH)
            c = conn.cursor()
            existing = c.execute("SELECT id FROM users WHERE email='admin@importal.cl'").fetchone()
            if existing:
                c.execute("UPDATE users SET password_hash=?, is_active=1 WHERE email='admin@importal.cl'", (pw,))
                msg = "Contraseña del admin reseteada correctamente."
            else:
                c.execute("INSERT INTO users (email,password_hash,name,role,is_active) VALUES (?,?,?,'ADMIN',1)",
                          ('admin@importal.cl', pw, 'Administrador Importal'))
                msg = "Admin creado correctamente."
            conn.commit()
            conn.close()
            html = f"<h2 style='font-family:sans-serif;color:green'>✅ {msg}</h2><p style='font-family:sans-serif'>Ya puedes iniciar sesión en <a href='/login'>/login</a> con admin@importal.cl / admin123</p>"
        except Exception as e:
            html = f"<h2 style='font-family:sans-serif;color:red'>❌ Error: {e}</h2>"
        self.send_html(html)

    # ── POST ─────────────────────────────────────────────────────
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        if path.startswith('/api/'):
            self.handle_api_post(path)
        else:
            self.send_json({'error': 'Not found'}, 404)

    # ── STATIC FILES ─────────────────────────────────────────────
    def serve_static(self, path):
        filepath = os.path.join(BASE_DIR, path.lstrip('/'))
        if os.path.exists(filepath) and os.path.isfile(filepath):
            ext = os.path.splitext(filepath)[1].lower()
            mime = MIME_TYPES.get(ext, 'application/octet-stream')
            with open(filepath, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_json({'error': 'Not found'}, 404)

    # ── API GET ───────────────────────────────────────────────────
    def handle_api_get(self, path, params):
        # ── PUBLIC ──
        if path == '/api/health':
            self.send_json({'status': 'ok', 'version': '1.0'})
            return

        # ── AUTH REQUIRED ──
        payload = auth.get_token_from_request(self)
        if not payload:
            self.send_json({'error': 'No autenticado'}, 401)
            return
        uid = payload['sub']
        role = payload['role']

        # Client endpoints
        if path == '/api/me':
            user = db.get_user_by_id(uid)
            if user:
                user.pop('password_hash', None)
                self.send_json(user)
            else:
                self.send_json({'error': 'Usuario no encontrado'}, 404)

        elif path == '/api/dashboard/stats':
            cargas = db.get_cargas_for_client(uid)
            cobros = db.get_cobros_for_client(uid)
            deuda = sum(c['amount_clp'] + c['mora_amount'] for c in cobros
                        if c['status'] in ('PENDING','OVERDUE','MORA_1','MORA_2'))
            total_inv = sum(c['amount_clp'] for c in cobros if c['status'] == 'PAID')
            self.send_json({
                'cargas_activas': len([c for c in cargas if c['status'] not in ('CLOSED',)]),
                'deuda_total': deuda,
                'total_invertido': total_inv,
                'cobros_pendientes': len([c for c in cobros
                                          if c['status'] in ('PENDING','OVERDUE','MORA_1','MORA_2')]),
            })

        elif path == '/api/cargas':
            self.send_json(db.get_cargas_for_client(uid))

        elif path == '/api/cobros':
            self.send_json(db.get_cobros_for_client(uid))

        elif path == '/api/pagos':
            self.send_json(db.get_pagos_for_client(uid))

        elif path == '/api/tracking':
            carga_id = params.get('carga_id', [None])[0]
            if carga_id:
                self.send_json(db.get_tracking_for_carga(int(carga_id)))
            else:
                cargas = db.get_cargas_for_client(uid)
                result = {}
                for c in cargas:
                    result[c['id']] = db.get_tracking_for_carga(c['id'])
                self.send_json(result)

        elif path == '/api/perfil/envio':
            self.send_json(db.get_shipment_data(uid))

        # Admin endpoints
        elif path == '/api/admin/stats' and role == 'ADMIN':
            self.send_json(db.get_admin_stats())

        elif path == '/api/admin/cargas' and role == 'ADMIN':
            self.send_json(db.get_all_cargas())

        elif path == '/api/admin/cobros' and role == 'ADMIN':
            self.send_json(db.get_all_cobros())

        elif path == '/api/admin/clientes' and role == 'ADMIN':
            self.send_json(db.get_all_clients())

        elif path == '/api/admin/pagos' and role == 'ADMIN':
            self.send_json(db.get_all_pagos())

        elif path == '/api/admin/conciliacion/unmatched' and role == 'ADMIN':
            self.send_json(db.get_unmatched_movements())

        else:
            self.send_json({'error': 'Endpoint no encontrado'}, 404)

    # ── API POST ──────────────────────────────────────────────────
    def handle_api_post(self, path):
        # ── AUTH: LOGIN ──
        if path == '/api/auth/login':
            data = self.get_json_body()
            email = (data.get('email') or '').lower().strip()
            password = data.get('password') or ''
            user = db.get_user_by_email(email)
            if not user or not auth.verify_password(password, user['password_hash']):
                self.send_json({'error': 'Credenciales incorrectas'}, 401)
                return
            if not user['is_active']:
                self.send_json({'error': 'Cuenta desactivada'}, 403)
                return
            token = auth.create_token(user['id'], user['email'], user['role'])
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.set_auth_cookie(token)
            body = json.dumps({'token': token, 'user': {
                'id': user['id'], 'name': user['name'],
                'email': user['email'], 'role': user['role']
            }}).encode()
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
            return

        # ── AUTH: REGISTER ──
        if path == '/api/auth/register':
            data = self.get_json_body()
            email = (data.get('email') or '').lower().strip()
            password = data.get('password') or ''
            name = (data.get('name') or '').strip()
            if not email or not password or not name:
                self.send_json({'error': 'Datos incompletos'}, 400)
                return
            if len(password) < 6:
                self.send_json({'error': 'Contraseña muy corta (mín. 6 caracteres)'}, 400)
                return
            pw_hash = auth.hash_password(password)
            uid = db.create_user(email, pw_hash, name,
                                  data.get('rut',''), data.get('phone',''),
                                  data.get('company',''))
            if not uid:
                self.send_json({'error': 'El correo ya está registrado'}, 409)
                return
            token = auth.create_token(uid, email, 'CLIENT')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.set_auth_cookie(token)
            body = json.dumps({'token': token, 'message': '¡Registro exitoso!'}).encode()
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
            return

        # ── AUTH REQUIRED for below ──
        payload = auth.get_token_from_request(self)
        if not payload:
            self.send_json({'error': 'No autenticado'}, 401)
            return
        uid = payload['sub']
        role = payload['role']

        # ── CLIENT: SUBMIT PAGO ──
        if path == '/api/pagos':
            data = self.get_json_body()
            cobro_id = data.get('cobro_id')
            amount = data.get('amount_clp')
            method = data.get('method', 'TRANSFER')
            transfer_code = data.get('transfer_code')
            notes = data.get('notes', '')
            if not cobro_id or not amount:
                self.send_json({'error': 'Datos incompletos'}, 400)
                return
            pago_id = db.create_pago(cobro_id, uid, amount, method, transfer_code, notes)
            self.send_json({'success': True, 'pago_id': pago_id,
                            'message': 'Pago registrado. Revisaremos tu comprobante pronto.'})

        # ── CLIENT: SAVE PERFIL ENVIO ──
        elif path == '/api/perfil/envio':
            data = self.get_json_body()
            db.save_shipment_data(uid,
                data.get('address',''), data.get('city',''),
                data.get('region',''), data.get('agency','Starken'),
                data.get('notes',''))
            self.send_json({'success': True})

        # ── CLIENT: UPDATE PROFILE ──
        elif path == '/api/perfil':
            data = self.get_json_body()
            allowed = ['name', 'phone', 'rut', 'company']
            update = {k: data[k] for k in allowed if k in data}
            if update:
                db.update_user(uid, update)
            self.send_json({'success': True})

        # ── ADMIN: CREATE CARGA ──
        elif path == '/api/admin/cargas' and role == 'ADMIN':
            data = self.get_json_body()
            cid = db.create_carga(
                data.get('code'), data.get('type'),
                float(data.get('dollar_rate', 960)),
                data.get('open_date', datetime.now().date().isoformat()),
                data.get('notes', ''))
            self.send_json({'success': True, 'id': cid})

        # ── ADMIN: UPDATE CARGA ──
        elif path == '/api/admin/cargas/update' and role == 'ADMIN':
            data = self.get_json_body()
            cid = data.pop('id')
            db.update_carga(cid, data)
            self.send_json({'success': True})

        # ── ADMIN: CREATE COBRO ──
        elif path == '/api/admin/cobros' and role == 'ADMIN':
            data = self.get_json_body()
            cob_id, code = db.create_cobro(
                int(data['client_id']), int(data['carga_id']),
                data['type'], float(data['amount_clp']),
                data['due_date'], data.get('notes',''))
            self.send_json({'success': True, 'id': cob_id, 'unique_code': code})

        # ── ADMIN: CONFIRM PAGO ──
        elif path == '/api/admin/pagos/confirm' and role == 'ADMIN':
            data = self.get_json_body()
            db.confirm_pago(data['pago_id'], uid)
            self.send_json({'success': True})

        # ── ADMIN: ADD TRACKING ──
        elif path == '/api/admin/tracking' and role == 'ADMIN':
            data = self.get_json_body()
            db.add_tracking(data['carga_id'], data['stage'],
                            data.get('stage_date', datetime.now().isoformat()),
                            data.get('notes', ''))
            self.send_json({'success': True})

        # ── ADMIN: CONCILIACION CSV ──
        elif path == '/api/admin/conciliacion/upload' and role == 'ADMIN':
            data = self.get_json_body()
            movements = data.get('movements', [])
            matched = db.insert_bank_movements(movements)
            self.send_json({'success': True, 'matched': matched,
                            'total': len(movements),
                            'message': f'{matched} de {len(movements)} movimientos asociados automáticamente'})

        else:
            self.send_json({'error': 'Endpoint no encontrado'}, 404)


def mora_scheduler():
    """Ejecuta el cálculo de mora cada hora en background."""
    import time
    while True:
        try:
            db.update_mora_status()
        except Exception as e:
            pass
        time.sleep(3600)  # cada 1 hora

if __name__ == '__main__':
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    db.init_db()
    # Calcular mora al iniciar
    try:
        db.update_mora_status()
    except Exception:
        pass
    # Iniciar scheduler de mora en background
    t = threading.Thread(target=mora_scheduler, daemon=True)
    t.start()
    print(f"""
╔══════════════════════════════════════════════╗
║       GRUPO IMPORTAL — Servidor v1.0         ║
╠══════════════════════════════════════════════╣
║  URL:    http://0.0.0.0:{PORT:<20}     ║
║  Admin:  admin@importal.cl / admin123   ║
╚══════════════════════════════════════════════╝
    """)
    with socketserver.TCPServer(('0.0.0.0', PORT), PascalleHandler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Servidor detenido")
