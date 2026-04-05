"""
Pascalle Store — Base de datos SQLite
Todas las operaciones de base de datos están aquí.
"""
import sqlite3, json, os
from datetime import datetime, timedelta

_DATA_DIR = os.environ.get('DATA_DIR', os.path.join(os.path.dirname(__file__), 'data'))
os.makedirs(_DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(_DATA_DIR, 'pascalle.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Crea todas las tablas si no existen y crea el admin por defecto."""
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            rut TEXT,
            phone TEXT,
            company TEXT,
            role TEXT NOT NULL DEFAULT 'CLIENT',
            is_active INTEGER DEFAULT 1,
            has_mora INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS shipment_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER UNIQUE NOT NULL,
            address TEXT,
            city TEXT,
            region TEXT,
            agency TEXT DEFAULT 'Starken',
            notes TEXT,
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (client_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS cargas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            dollar_rate REAL DEFAULT 960,
            real_dollar_rate REAL DEFAULT 940,
            agency_rate REAL DEFAULT 5900,
            open_date TEXT,
            close_date TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carga_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            name TEXT,
            description TEXT,
            price_usd REAL NOT NULL,
            photo_url TEXT,
            sizes TEXT DEFAULT '[]',
            total_stock INTEGER DEFAULT 1,
            status TEXT DEFAULT 'AVAILABLE',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (carga_id) REFERENCES cargas(id),
            FOREIGN KEY (provider_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            carga_id INTEGER NOT NULL,
            size TEXT,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price_usd REAL NOT NULL,
            total_price_usd REAL NOT NULL,
            status TEXT DEFAULT 'REQUESTED',
            created_at TEXT DEFAULT (datetime('now')),
            confirmed_at TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (client_id) REFERENCES users(id),
            FOREIGN KEY (carga_id) REFERENCES cargas(id)
        );

        CREATE TABLE IF NOT EXISTS cobros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unique_code TEXT UNIQUE NOT NULL,
            client_id INTEGER NOT NULL,
            carga_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount_clp REAL NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            paid_at TEXT,
            mora_amount REAL DEFAULT 0,
            mora_started_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            notes TEXT,
            FOREIGN KEY (client_id) REFERENCES users(id),
            FOREIGN KEY (carga_id) REFERENCES cargas(id)
        );

        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cobro_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            amount_clp REAL NOT NULL,
            method TEXT NOT NULL DEFAULT 'TRANSFER',
            status TEXT DEFAULT 'PENDING',
            transfer_code TEXT,
            transfer_receipt TEXT,
            bank_reference TEXT,
            confirmed_at TEXT,
            confirmed_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            notes TEXT,
            FOREIGN KEY (cobro_id) REFERENCES cobros(id),
            FOREIGN KEY (client_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carga_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            stage_date TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (carga_id) REFERENCES cargas(id)
        );

        CREATE TABLE IF NOT EXISTS bank_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movement_date TEXT,
            description TEXT,
            amount REAL,
            reference TEXT,
            cobro_id INTEGER,
            status TEXT DEFAULT 'UNMATCHED',
            uploaded_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (cobro_id) REFERENCES cobros(id)
        );

        CREATE TABLE IF NOT EXISTS boletas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carga_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            boleta_url TEXT,
            bank_receipt_url TEXT,
            dollar_rate_receipt REAL,
            status TEXT DEFAULT 'PENDING',
            admin_notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            verified_at TEXT,
            FOREIGN KEY (carga_id) REFERENCES cargas(id),
            FOREIGN KEY (provider_id) REFERENCES users(id)
        );
    """)
    conn.commit()

    # Crear admin por defecto si no existe
    import bcrypt
    admin_exists = c.execute("SELECT id FROM users WHERE role='ADMIN' LIMIT 1").fetchone()
    if not admin_exists:
        pw = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()
        c.execute("""INSERT INTO users (email,password_hash,name,role)
                     VALUES (?,?,?,'ADMIN')""",
                  ('admin@importal.cl', pw, 'Administrador Importal'))
        conn.commit()
        print("✅ Admin creado: admin@importal.cl / admin123")

    conn.close()

# ─── USERS ─────────────────────────────────────────────────────
def get_user_by_email(email):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(u) if u else None

def get_user_by_id(uid):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return dict(u) if u else None

def create_user(email, password_hash, name, rut='', phone='', company=''):
    conn = get_db()
    try:
        c = conn.execute(
            "INSERT INTO users (email,password_hash,name,rut,phone,company) VALUES (?,?,?,?,?,?)",
            (email, password_hash, name, rut, phone, company))
        conn.commit()
        uid = c.lastrowid
        conn.close()
        return uid
    except sqlite3.IntegrityError:
        conn.close()
        return None

def get_all_clients():
    conn = get_db()
    rows = conn.execute("""
        SELECT u.*,
               COUNT(DISTINCT co.carga_id) as total_cargas,
               COALESCE(SUM(CASE WHEN co.status IN ('PENDING','OVERDUE','MORA_1','MORA_2') THEN co.amount_clp + co.mora_amount ELSE 0 END),0) as total_deuda,
               CASE
                 WHEN MAX(CASE WHEN co.status='MORA_2' THEN 2 WHEN co.status='MORA_1' THEN 1 ELSE 0 END)=2 THEN 'MORA_2'
                 WHEN MAX(CASE WHEN co.status='MORA_2' THEN 2 WHEN co.status='MORA_1' THEN 1 ELSE 0 END)=1 THEN 'MORA_1'
                 ELSE 'NONE'
               END as mora_status
        FROM users u
        LEFT JOIN cobros co ON co.client_id=u.id
        WHERE u.role='CLIENT'
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_user(uid, data):
    conn = get_db()
    fields = ', '.join(f"{k}=?" for k in data)
    vals = list(data.values()) + [uid]
    conn.execute(f"UPDATE users SET {fields} WHERE id=?", vals)
    conn.commit()
    conn.close()

# ─── CARGAS ────────────────────────────────────────────────────
def get_cargas_for_client(client_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT DISTINCT ca.*,
               COALESCE(SUM(CASE WHEN co.status IN ('PENDING','OVERDUE','MORA_1','MORA_2') THEN co.amount_clp + co.mora_amount ELSE 0 END),0) as deuda,
               COALESCE(SUM(CASE WHEN co.status='PAID' THEN co.amount_clp ELSE 0 END),0) as total_invertido
        FROM cargas ca
        JOIN cobros co ON co.carga_id=ca.id AND co.client_id=?
        GROUP BY ca.id
        ORDER BY ca.created_at DESC
    """, (client_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_cargas():
    conn = get_db()
    rows = conn.execute("SELECT * FROM cargas ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_carga(code, ctype, dollar_rate, open_date, notes=''):
    conn = get_db()
    c = conn.execute(
        "INSERT INTO cargas (code,type,dollar_rate,open_date,notes) VALUES (?,?,?,?,?)",
        (code, ctype, dollar_rate, open_date, notes))
    conn.commit()
    cid = c.lastrowid
    conn.close()
    return cid

def update_carga(cid, data):
    conn = get_db()
    fields = ', '.join(f"{k}=?" for k in data)
    vals = list(data.values()) + [cid]
    conn.execute(f"UPDATE cargas SET {fields} WHERE id=?", vals)
    conn.commit()
    conn.close()

def get_carga_by_id(cid):
    conn = get_db()
    r = conn.execute("SELECT * FROM cargas WHERE id=?", (cid,)).fetchone()
    conn.close()
    return dict(r) if r else None

# ─── COBROS ────────────────────────────────────────────────────
def get_cobros_for_client(client_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT co.*, ca.code as carga_code, ca.type as carga_type
        FROM cobros co
        JOIN cargas ca ON ca.id=co.carga_id
        WHERE co.client_id=?
        ORDER BY co.created_at DESC
    """, (client_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_cobros():
    conn = get_db()
    rows = conn.execute("""
        SELECT co.*, u.name as client_name, u.email as client_email,
               ca.code as carga_code, ca.type as carga_type
        FROM cobros co
        JOIN users u ON u.id=co.client_id
        JOIN cargas ca ON ca.id=co.carga_id
        ORDER BY co.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_cobro(client_id, carga_id, cobro_type, amount_clp, due_date, notes=''):
    import random, string
    conn = get_db()
    carga = conn.execute("SELECT code FROM cargas WHERE id=?", (carga_id,)).fetchone()
    user = conn.execute("SELECT name FROM users WHERE id=?", (client_id,)).fetchone()
    carga_code = carga['code'].replace('-','') if carga else 'C000'
    initials = ''.join(w[0].upper() for w in user['name'].split()[:2]) if user else 'XX'
    rand = ''.join(random.choices(string.digits, k=3))
    unique_code = f"PS-{carga_code}-{initials}-{rand}"
    try:
        c = conn.execute(
            "INSERT INTO cobros (unique_code,client_id,carga_id,type,amount_clp,due_date,notes) VALUES (?,?,?,?,?,?,?)",
            (unique_code, client_id, carga_id, cobro_type, amount_clp, due_date, notes))
        conn.commit()
        cid = c.lastrowid
        conn.close()
        return cid, unique_code
    except:
        conn.close()
        return None, None

def update_cobro(cobro_id, data):
    conn = get_db()
    fields = ', '.join(f"{k}=?" for k in data)
    vals = list(data.values()) + [cobro_id]
    conn.execute(f"UPDATE cobros SET {fields} WHERE id=?", vals)
    conn.commit()
    conn.close()

def get_client_pending_debt(client_id):
    conn = get_db()
    r = conn.execute(
        "SELECT COALESCE(SUM(amount_clp + mora_amount),0) as total FROM cobros WHERE client_id=? AND status IN ('PENDING','OVERDUE','MORA_1','MORA_2')",
        (client_id,)).fetchone()
    conn.close()
    return r['total'] if r else 0

# ─── PAGOS ─────────────────────────────────────────────────────
def create_pago(cobro_id, client_id, amount, method, transfer_code=None, notes=''):
    conn = get_db()
    c = conn.execute(
        "INSERT INTO pagos (cobro_id,client_id,amount_clp,method,transfer_code,notes) VALUES (?,?,?,?,?,?)",
        (cobro_id, client_id, amount, method, transfer_code, notes))
    conn.commit()
    pid = c.lastrowid
    conn.close()
    return pid

def get_pagos_for_client(client_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*, co.unique_code, co.type as cobro_type,
               ca.code as carga_code
        FROM pagos p
        JOIN cobros co ON co.id=p.cobro_id
        JOIN cargas ca ON ca.id=co.carga_id
        WHERE p.client_id=?
        ORDER BY p.created_at DESC
    """, (client_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def confirm_pago(pago_id, admin_id):
    conn = get_db()
    now = datetime.now().isoformat()
    pago = conn.execute("SELECT * FROM pagos WHERE id=?", (pago_id,)).fetchone()
    if pago:
        conn.execute("UPDATE pagos SET status='CONFIRMED', confirmed_at=?, confirmed_by=? WHERE id=?",
                     (now, admin_id, pago_id))
        conn.execute("UPDATE cobros SET status='PAID', paid_at=? WHERE id=?",
                     (now, pago['cobro_id']))
        conn.commit()
    conn.close()

def get_all_pagos():
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*, u.name as client_name, co.unique_code,
               co.type as cobro_type, ca.code as carga_code
        FROM pagos p
        JOIN users u ON u.id=p.client_id
        JOIN cobros co ON co.id=p.cobro_id
        JOIN cargas ca ON ca.id=co.carga_id
        ORDER BY p.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── TRACKING ──────────────────────────────────────────────────
def get_tracking_for_carga(carga_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tracking WHERE carga_id=? ORDER BY created_at ASC",
        (carga_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_tracking(carga_id, stage, stage_date, notes=''):
    conn = get_db()
    conn.execute("INSERT INTO tracking (carga_id,stage,stage_date,notes) VALUES (?,?,?,?)",
                 (carga_id, stage, stage_date, notes))
    conn.commit()
    conn.close()

# ─── STATS ADMIN ───────────────────────────────────────────────
def get_admin_stats():
    conn = get_db()
    from datetime import datetime
    stats = {}
    stats['total_clients'] = conn.execute("SELECT COUNT(*) FROM users WHERE role='CLIENT'").fetchone()[0]
    stats['cargas_activas'] = conn.execute("SELECT COUNT(*) FROM cargas WHERE status NOT IN ('CLOSED')").fetchone()[0]
    stats['cobros_pendientes'] = conn.execute("SELECT COUNT(*) FROM cobros WHERE status IN ('PENDING','OVERDUE','MORA_1','MORA_2')").fetchone()[0]
    stats['deuda_total'] = conn.execute("SELECT COALESCE(SUM(amount_clp+mora_amount),0) FROM cobros WHERE status IN ('PENDING','OVERDUE','MORA_1','MORA_2')").fetchone()[0]
    stats['pagos_sin_confirmar'] = conn.execute("SELECT COUNT(*) FROM pagos WHERE confirmed_at IS NULL").fetchone()[0]
    stats['clientes_mora'] = conn.execute("SELECT COUNT(DISTINCT client_id) FROM cobros WHERE status IN ('MORA_1','MORA_2')").fetchone()[0]
    mes_inicio = datetime.now().replace(day=1).strftime('%Y-%m-01')
    stats['recaudado_mes'] = conn.execute(
        "SELECT COALESCE(SUM(amount_clp),0) FROM pagos WHERE confirmed_at IS NOT NULL AND confirmed_at >= ?",
        (mes_inicio,)).fetchone()[0]
    conn.close()
    return stats

def get_shipment_data(client_id):
    conn = get_db()
    r = conn.execute("SELECT * FROM shipment_data WHERE client_id=?", (client_id,)).fetchone()
    conn.close()
    return dict(r) if r else {}

def save_shipment_data(client_id, address, city, region, agency, notes=''):
    conn = get_db()
    existing = conn.execute("SELECT id FROM shipment_data WHERE client_id=?", (client_id,)).fetchone()
    if existing:
        conn.execute("UPDATE shipment_data SET address=?,city=?,region=?,agency=?,notes=?,updated_at=datetime('now') WHERE client_id=?",
                     (address, city, region, agency, notes, client_id))
    else:
        conn.execute("INSERT INTO shipment_data (client_id,address,city,region,agency,notes) VALUES (?,?,?,?,?,?)",
                     (client_id, address, city, region, agency, notes))
    conn.commit()
    conn.close()

# ─── BANK CONCILIATION ─────────────────────────────────────────
def update_mora_status():
    """
    Ejecutar periódicamente (cada hora).
    Reglas:
      - Cobro vencido sin pago → OVERDUE
      - +24h vencido → MORA_1 (5% mora)
      - +48h vencido → MORA_2 (10% mora acumulado = +5% más)
      - +10 días vencido → suspender cliente (is_active=0 temporalmente)
    """
    conn = get_db()
    now = datetime.now()
    cobros = conn.execute(
        "SELECT * FROM cobros WHERE status IN ('PENDING','OVERDUE','MORA_1','MORA_2')"
    ).fetchall()
    for c in cobros:
        due = c['due_date']
        if not due:
            continue
        try:
            due_dt = datetime.fromisoformat(due)
        except:
            due_dt = datetime.strptime(due[:10], '%Y-%m-%d')
        diff = now - due_dt
        hours = diff.total_seconds() / 3600
        if hours < 0:
            continue  # No vencido aún
        base = c['amount_clp']
        if hours >= 240:  # 10 días → suspender
            new_mora = base * 0.10
            conn.execute(
                "UPDATE cobros SET status='MORA_2', mora_amount=?, mora_started_at=COALESCE(mora_started_at,?) WHERE id=?",
                (new_mora, now.isoformat(), c['id']))
            conn.execute("UPDATE users SET is_active=0 WHERE id=? AND role='CLIENT'", (c['client_id'],))
        elif hours >= 48:  # 48h → mora total 10%
            new_mora = base * 0.10
            conn.execute(
                "UPDATE cobros SET status='MORA_2', mora_amount=?, mora_started_at=COALESCE(mora_started_at,?) WHERE id=?",
                (new_mora, now.isoformat(), c['id']))
        elif hours >= 24:  # 24h → mora 5%
            new_mora = base * 0.05
            conn.execute(
                "UPDATE cobros SET status='MORA_1', mora_amount=?, mora_started_at=COALESCE(mora_started_at,?) WHERE id=?",
                (new_mora, now.isoformat(), c['id']))
        else:  # Vencido pero menos de 24h
            conn.execute(
                "UPDATE cobros SET status='OVERDUE' WHERE id=? AND status='PENDING'",
                (c['id'],))
    conn.commit()
    conn.close()

def get_unmatched_movements():
    conn = get_db()
    rows = conn.execute("SELECT *, movement_date as bank_date FROM bank_movements WHERE status='UNMATCHED' ORDER BY movement_date DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def match_movement(movement_id, cobro_id):
    conn = get_db()
    conn.execute("UPDATE bank_movements SET cobro_id=?,status='MATCHED' WHERE id=?",
                 (cobro_id, movement_id))
    conn.commit()
    conn.close()

def insert_bank_movements(movements):
    """movements: list of dicts with keys: date, description, amount, type"""
    import re
    conn = get_db()
    matched = 0
    # Get all pending cobros with unique codes
    pending_cobros = conn.execute(
        "SELECT id, unique_code FROM cobros WHERE status IN ('PENDING','OVERDUE','MORA_1','MORA_2')"
    ).fetchall()
    code_map = {row['unique_code'].upper(): row['id'] for row in pending_cobros}

    for m in movements:
        desc = (m.get('description') or '').upper()
        cobro_id = None
        status = 'UNMATCHED'
        # Search for any known unique code pattern within description
        for code_upper, cid in code_map.items():
            if code_upper in desc:
                cobro_id = cid
                status = 'MATCHED'
                matched += 1
                # Mark the cobro as paid
                now = datetime.now().isoformat()
                conn.execute("UPDATE cobros SET status='PAID', paid_at=? WHERE id=?", (now, cid))
                break
        bank_date = m.get('date') or m.get('movement_date')
        conn.execute(
            "INSERT INTO bank_movements (movement_date,description,amount,cobro_id,status) VALUES (?,?,?,?,?)",
            (bank_date, m.get('description'), m.get('amount'), cobro_id, status))
    conn.commit()
    conn.close()
    return matched
