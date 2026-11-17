"""Prueba de login y permisos de FarmaSys, sin PostgreSQL.

Reemplaza la base de datos por una conexión falsa y recorre TODAS las rutas que
Flask conoce (app.url_map). Si alguien agrega una ruta nueva y olvida protegerla
con @solo_admin, esta prueba falla.

Uso (desde farmacia-app/):   python tests/test_permisos.py
Requiere flask y psycopg2-binary instalados (no requiere PostgreSQL).
"""
import os
import sys

import psycopg2

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)
os.environ.update({
    "DATABASE_URL": "postgresql://falsa",
    "SECRET_KEY": "clave-solo-para-pruebas",
    "COOKIE_SEGURA": "0",
})
os.environ.pop("ADMIN_USUARIO", None)
os.environ.pop("ADMIN_PASSWORD", None)

from werkzeug.security import generate_password_hash  # noqa: E402

# ── Base de datos falsa ──────────────────────────────────
USUARIOS = {
    1: {"id": 1, "usuario": "dueno", "nombre": "Dueño", "rol": "admin", "activo": True,
        "password_hash": generate_password_hash("clave-admin-123")},
    2: {"id": 2, "usuario": "caja1", "nombre": "Cajera Uno", "rol": "cajero", "activo": True,
        "password_hash": generate_password_hash("clave-caja-123")},
    3: {"id": 3, "usuario": "exempleado", "nombre": "Ex", "rol": "cajero", "activo": False,
        "password_hash": generate_password_hash("clave-ex-1234")},
}
ESTADO = {"db_caida": False, "hay_usuarios": True, "sqls": []}
ITEM = {"id": 5, "nombre": "Acetaminofen", "laboratorio": "MK", "precio": 3000.0, "precio_costo": 1800.0}


class CursorFalso:
    def __init__(self):
        self.resultado = None

    def execute(self, sql, params=None):
        s = " ".join(sql.split())
        ESTADO["sqls"].append((s, params))
        self.resultado = None
        if "information_schema" in s:
            self.resultado = [{"x": 1}]                       # las columnas "ya existen"
        elif s.startswith("SELECT 1 FROM usuarios LIMIT 1"):
            self.resultado = [{"x": 1}] if ESTADO["hay_usuarios"] else []
        elif "FROM usuarios WHERE id = %s" in s:
            u = USUARIOS.get(params[0])
            self.resultado = [u] if u else []
        elif "FROM usuarios WHERE usuario = %s" in s:
            self.resultado = [u for u in USUARIOS.values() if u["usuario"] == params[0]]
        elif s.startswith("INSERT INTO usuarios") and "RETURNING" in s:
            self.resultado = [{"id": 99}]
        elif s.startswith("UPDATE usuarios"):
            uid = params[-1]
            self.resultado = [{"id": uid}] if uid in USUARIOS else []
        elif s.startswith("UPDATE inventario SET cantidad = cantidad -"):
            self.resultado = [ITEM]

    def fetchone(self):
        return self.resultado[0] if self.resultado else None

    def fetchall(self):
        return self.resultado or []


class ConexionFalsa:
    def cursor(self, *a, **k):
        return CursorFalso()

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def connect_falso(*a, **k):
    if ESTADO["db_caida"]:
        raise psycopg2.OperationalError("base caída (simulada)")
    return ConexionFalsa()


psycopg2.connect = connect_falso
import app as farm  # noqa: E402  (init_db corre contra la conexión falsa)

farm.app.logger.disabled = True  # las rutas permitidas pueden fallar contra la BD falsa: no es lo que se prueba
client = farm.app.test_client()
MSG_SOLO_ADMIN = "Solo el administrador puede hacer esto"

# Lo único que un cajero puede usar. Todo lo demás debe darle 403.
PERMITIDAS_CAJERO = {
    ("GET", "/"), ("GET", "/login"), ("POST", "/login"), ("POST", "/logout"),
    ("GET", "/api/invima/buscar"), ("GET", "/api/inferir-categoria"),
    ("GET", "/api/categorias"), ("GET", "/api/catalogo"),
    ("GET", "/api/inventario"),
    ("GET", "/api/dashboard"), ("GET", "/api/dashboard/alertas"),
    ("GET", "/api/dashboard/ventas-hoy"), ("GET", "/api/dashboard/ventas-semana"),
    ("GET", "/api/dashboard/top-productos"),
    ("GET", "/api/ventas"), ("POST", "/api/ventas"),
    ("GET", "/api/creditos"), ("POST", "/api/creditos/<int:credito_id>/abonar"),
}
PUBLICAS = {"/login"}

fallos = []


def check(cond, descripcion):
    if not cond:
        fallos.append(descripcion)
        print("FALLA", descripcion)


def rutas():
    """(método, regla, url concreta) de todas las rutas de la app, menos /static."""
    for regla in farm.app.url_map.iter_rules():
        if regla.endpoint == "static":
            continue
        url = regla.rule
        for arg in regla.arguments:
            url = url.replace(f"<int:{arg}>", "1").replace(f"<{arg}>", "1")
        for metodo in sorted(regla.methods - {"HEAD", "OPTIONS"}):
            yield metodo, regla.rule, url


def pedir(metodo, url, **kw):
    return client.open(url, method=metodo, **kw)


def sesion(uid):
    farm._cache_usuarios.clear()
    with client.session_transaction() as s:
        s.clear()
        if uid:
            s["uid"] = uid


def es_bloqueo_admin(r):
    return r.status_code == 403 and (r.get_json(silent=True) or {}).get("error") == MSG_SOLO_ADMIN


# ── 1. Sin sesión: todo cerrado salvo /login ─────────────
sesion(None)
for metodo, regla, url in rutas():
    if regla in PUBLICAS:
        continue
    r = pedir(metodo, url)
    if regla.startswith("/api/") and not regla.startswith("/api/reportes/"):
        check(r.status_code == 401, f"sin sesión {metodo} {regla} debía dar 401 y dio {r.status_code}")
    else:
        check(r.status_code == 302 and "/login" in r.headers.get("Location", ""),
              f"sin sesión {metodo} {regla} debía redirigir a /login y dio {r.status_code}")
check(client.get("/static/style.css").status_code == 200, "/static/style.css debe ser público")

# ── 2. Cajero: solo lo permitido ─────────────────────────
total_bloqueadas = 0
for metodo, regla, url in rutas():
    if regla in PUBLICAS:  # el login se prueba aparte (sección 6)
        continue
    sesion(2)
    r = pedir(metodo, url, json={})
    if (metodo, regla) in PERMITIDAS_CAJERO:
        check(r.status_code not in (401, 403), f"cajero debía poder {metodo} {regla} y dio {r.status_code}")
    else:
        total_bloqueadas += 1
        check(es_bloqueo_admin(r), f"cajero NO debía poder {metodo} {regla} y dio {r.status_code}")
print(f"Rutas bloqueadas al cajero: {total_bloqueadas}")
check(total_bloqueadas == 18, f"se esperaban 18 rutas de admin (15 + 3 de usuarios), hay {total_bloqueadas}")

# ── 3. Admin: nada lo bloquea por rol ────────────────────
for metodo, regla, url in rutas():
    if regla in PUBLICAS:  # el login se prueba aparte (sección 6)
        continue
    sesion(1)
    r = pedir(metodo, url, json={})
    check(r.status_code != 401 and not es_bloqueo_admin(r), f"admin bloqueado en {metodo} {regla} ({r.status_code})")

# ── 4. Usuario desactivado o inexistente = sin sesión ────
for uid in (3, 404):
    sesion(uid)
    check(client.get("/api/ventas").status_code == 401, f"uid {uid} (inactivo/inexistente) debía dar 401")

# ── 5. Base caída: 503, no 500 ───────────────────────────
sesion(2)
ESTADO["db_caida"] = True
check(client.get("/api/ventas").status_code == 503, "BD caída en /api debía dar 503")
check(client.get("/").status_code == 503, "BD caída en / debía dar 503")
check(client.post("/login", data={"usuario": "caja1", "password": "x"}).status_code == 503, "BD caída en login debía dar 503")
ESTADO["db_caida"] = False

# ── 6. Login ─────────────────────────────────────────────
sesion(None)
r = client.post("/login", data={"usuario": "caja1", "password": "mala-clave"})
check(r.status_code == 401 and "incorrectos" in r.get_data(as_text=True), "clave mala debía dar 401 con mensaje genérico")
r = client.post("/login", data={"usuario": "noexiste", "password": "lo-que-sea"})
check(r.status_code == 401 and "incorrectos" in r.get_data(as_text=True), "usuario inexistente: mismo mensaje genérico")
r = client.post("/login", data={"usuario": "caja\x001", "password": "x"})
check(r.status_code == 401, "usuario con byte nulo debía dar 401, no 500")
r = client.post("/login", data={"usuario": "exempleado", "password": "clave-ex-1234"})
check(r.status_code == 401, "usuario desactivado no debía poder entrar")
r = client.post("/login", data={"usuario": "caja1", "password": "clave-caja-123"})
check(r.status_code == 302, "login correcto debía redirigir")
with client.session_transaction() as s:
    check(s.get("uid") == 2, "login correcto debía guardar uid en la sesión")
check(client.get("/login").status_code == 302, "con sesión, GET /login debía redirigir a /")
client.post("/logout")
with client.session_transaction() as s:
    check("uid" not in s, "logout debía borrar la sesión")

# ── 7. Reglas de administración de usuarios ──────────────
sesion(1)
r = client.put("/api/usuarios/1", json={"activo": False})
check(r.status_code == 400, "el admin no debía poder desactivarse a sí mismo")
r = client.put("/api/usuarios/1", json={"rol": "cajero"})
check(r.status_code == 400, "el admin no debía poder quitarse el rol de admin")
r = client.put("/api/usuarios/2", json={"activo": False})
check(r.status_code == 200, "el admin debía poder desactivar a un cajero")
r = client.put("/api/usuarios/2", json={"activo": "false"})
check(r.status_code == 400, "activo como texto debía rechazarse")
r = client.post("/api/usuarios", json={"usuario": "caja2", "nombre": "Caja Dos", "password": "corta", "rol": "cajero"})
check(r.status_code == 400, "contraseña de menos de 8 debía rechazarse")
r = client.post("/api/usuarios", json={"usuario": "caja2", "nombre": "Caja Dos", "password": "larga-12345", "rol": "jefe"})
check(r.status_code == 400, "rol inválido debía rechazarse")
r = client.post("/api/usuarios", json={"usuario": "caja2", "nombre": "Caja Dos", "password": "larga-12345", "rol": "cajero"})
check(r.status_code == 200, "crear cajero válido debía funcionar")
insert = [p for s, p in ESTADO["sqls"] if s.startswith("INSERT INTO usuarios")][-1]
check(insert[2] != "larga-12345" and insert[2].startswith(("scrypt:", "pbkdf2:")), "la contraseña debe guardarse hasheada")
r = client.get("/api/usuarios")
check(all("password_hash" not in u for u in (r.get_json() or [{}])), "GET /api/usuarios nunca debe enviar password_hash")

# ── 8. Primer admin desde variables de entorno ───────────
def insertos_admin():
    return [s for s, _ in ESTADO["sqls"] if s.startswith("INSERT INTO usuarios") and "'admin'" in s]

ESTADO["hay_usuarios"] = False
os.environ.update({"ADMIN_USUARIO": "dueno", "ADMIN_PASSWORD": "corta"})
antes = len(insertos_admin())
farm.crear_admin_inicial(ConexionFalsa())
check(len(insertos_admin()) == antes, "ADMIN_PASSWORD corta no debía crear admin")
os.environ["ADMIN_PASSWORD"] = "suficientemente-larga"
farm.crear_admin_inicial(ConexionFalsa())
check(len(insertos_admin()) == antes + 1, "ADMIN_PASSWORD válida debía crear el admin")
ESTADO["hay_usuarios"] = True

# ── 9. La venta guarda quién la hizo ─────────────────────
sesion(2)
r = client.post("/api/ventas", json={"inventario_id": 5, "cantidad": 1})
check(r.status_code == 200, f"cajero debía poder vender (dio {r.status_code})")
venta = [p for s, p in ESTADO["sqls"] if s.startswith("INSERT INTO ventas")][-1]
check(venta[-2:] == (2, "Cajera Uno"), f"la venta debía guardar usuario_id y vendedor, guardó {venta[-2:]}")

print("\nRESULTADO:", "TODO OK" if not fallos else f"{len(fallos)} FALLAS")
sys.exit(1 if fallos else 0)
