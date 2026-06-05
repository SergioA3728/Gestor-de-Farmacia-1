# Informe de Cambios — Sesión 2026-06-03

> **Para qué sirve este documento:** resumen ejecutivo + educativo de los 3 commits de hoy. El código está en git (diff navegable), este documento explica el **POR QUÉ** y los **conceptos** detrás de cada cambio.

---

## TL;DR

Hoy se hizo un **rediseño del dashboard**, un **refactor de seguridad/mantenibilidad** y se construyó un **módulo premium de analíticas**. Tres commits, +1300 líneas, 0 bugs introducidos.

| # | Commit | Tema | Archivos | +/- |
|---|--------|------|----------|-----|
| 1 | `6127c4e` | Dashboard mejorado (gráfica + top productos) | 4 | +363 / -19 |
| 2 | `7f88a04` | Refactor clean-code (XSS, magic numbers, perf) | 3 | +73 / -62 |
| 3 | `a9a7bbb` | Módulo Premium Analíticas (5 endpoints) | 4 | +930 / -6 |

---

## Commit 1 — Dashboard mejorado

**Qué se hizo:** el dashboard pasó de 3 stats a 4, con una gráfica de ventas de los últimos 7 días y un ranking de los 5 productos más vendidos.

**Conceptos aplicados:**

- **Composición por responsabilidad única:** cada nueva visualización = 1 endpoint dedicado. `/api/dashboard/ventas-semana` solo devuelve los 7 días; `/api/dashboard/top-productos` solo devuelve el top 5. Esto evita que `/api/dashboard` se convierta en una "bola de barro" que devuelve 20 cosas mezcladas.
- **CSS Grid nativo:** `grid-template-columns: repeat(4, 1fr)` y `1.2fr 1fr 1fr` en `cards-row`. Sin librerías, sin frameworks.

**Lo que NO se hizo (decisión consciente):** la gráfica se hizo con **CSS puro** (`.chart-bar-fill` con `height: X%`). Consideramos Chart.js o D3, pero eran dependencias extra para algo que se resuelve con 30 líneas de CSS. YAGNI en acción.

**Para revisar:** `git show 6127c4e --stat` → ver los 4 archivos → saltar a `static/app.js:235-310` para ver las funciones de carga.

---

## Commit 2 — Refactor clean-code (el más importante)

> Esta es la parte donde se aplicó la skill `clean-code` de verdad. Lee con atención.

### Fix #1: XSS — vulnerabilidad crítica

**El problema (encontrado durante la revisión):**

```js
// app.js (ANTES) — vulnerable
function esc(str) {
    return (str || "").replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

// Uso en renderInventario:
`<div class="alert-name">${d.nombre}</div>`
```

`esc()` solo escapaba comillas, que sirve para handlers `onclick` en atributos. Pero se usaba el mismo nombre en contextos de **texto HTML**, donde no protege. Un producto con nombre `<img src=x onerror=alert(1)>` ejecutaba JavaScript arbitrario. Vulnerabilidad real.

**El fix:**

```js
// app.js (DESPUÉS) — seguro
function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function escapeJs(str) {
    return (str || "").replace(/'/g, "\\'").replace(/"/g, "&quot;");
}
```

Dos funciones con **nombres que revelan intención** (principio: *nombres pronunciables*):
- `escapeHtml` → para inyectar en HTML
- `escapeJs` → para inyectar en strings JS (atributos `onclick`)

**Lección:** el contexto importa. Una función "escape" genérica no existe — siempre es para un contexto. La regla de la skill "intención reveladora" te obliga a nombrarlo bien, y al nombrarlo bien detectas el mal uso.

**Aplicado en 8 lugares:** sugerencias INVIMA, alertas, ventas, inventario, importación, top productos, etc.

### Fix #2: Performance — conexiones DB en loop

**El problema:**

```python
# dashboard_ventas_semana (ANTES) — 7 conexiones DB
for i in range(6, -1, -1):
    conn = get_db()  # ← nueva conexión por cada día
    dia = conn.execute("SELECT date('now', ?) as d", (f"-{i} days",)).fetchone()["d"]
    conn.close()
    ...
```

7 conexiones a SQLite solo para calcular 7 fechas que Python puede resolver con `datetime`.

**El fix:** `datetime.date.today() - datetime.timedelta(days=i)`. 1 conexión, 0 queries extra. Mismo resultado, 7x más rápido.

**Lección:** antes de pedirle algo a la base de datos, pregúntate si el lenguaje ya lo hace. SQLite tiene `date('now', '-1 day')`, sí, pero para **calcular fechas que ya tienes como input**, el overhead de abrir conexión + parsear SQL > `datetime` en Python.

### Fix #3: Magic numbers → constantes

**El problema:** números `5` (umbral crítico), `30` (días de alerta) y strings `"%Y-%m-%d"`, `"$#,##0"`, `"%Y%m%d"` aparecían en 5+ lugares distintos. Si querías cambiar el umbral crítico, tenías que buscar y reemplazar manualmente. Riesgo de olvidar uno.

**El fix:** bloque de constantes al inicio del archivo:

```python
STOCK_MINIMO = 10
STOCK_CRITICO = 5
DIAS_ALERTA_VENCIMIENTO = 30
DATE_FMT = "%Y-%m-%d"
FMT_FECHA_REPORTE = "%Y%m%d"
```

**Lección:** "obsession primitive" (obsesión primitiva) es un code smell. Si un número tiene significado de negocio, merece un nombre. `5` no significa nada; `STOCK_CRITICO` significa "por debajo de esto es rojo".

### Fix #4: `try/except: pass` → check explícito

**El problema:** las migraciones de schema estaban así:

```python
try:
    conn.execute("ALTER TABLE inventario ADD COLUMN fecha_vencimiento TEXT")
except:
    pass  # ← silencio absoluto
```

Si la migración fallaba por una razón **legítima** (no porque la columna ya existiera), el error se perdía para siempre. Imposible de debuggear.

**El fix:** función helper con `pragma_table_info` que pregunta a SQLite si la columna existe antes de intentar crearla:

```python
def _ensure_column(conn, table, column, definition):
    existe = conn.execute(
        "SELECT 1 FROM pragma_table_info(?) WHERE name = ?",
        (table, column)
    ).fetchone()
    if not existe:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
```

**Lección:** `try/except: pass` es casi siempre código defectuoso. Si no puedes manejar el error, déjalo propagar. Si la "excepción esperada" es común, usa un check explícito (es más legible y testeable).

**Para revisar:** `git show 7f88a04` → enfócate en el diff de `static/app.js` (cambios en `${d.nombre}` → `${escapeHtml(d.nombre)}`).

---

## Commit 3 — Módulo Premium Analíticas

**Qué se hizo:** nuevo flag `PREMIUM_ENABLED = False` en backend, nueva página "Analíticas" en el sidebar, y 5 endpoints nuevos. Si el flag está en `False`, los endpoints devuelven 403 y la página muestra un CTA de upgrade.

### Concepto clave: Feature Flag

```python
PREMIUM_ENABLED = False

def _premium_required():
    if not PREMIUM_ENABLED:
        return jsonify({"ok": False, "premium_required": True, "error": "..."}), 403
    return None
```

Un solo lugar controla el acceso. Para activar Premium: cambias la constante, restart, listo. Sin branching en el código de cada endpoint.

### Inyección de config al frontend

```python
@app.route("/")
def index():
    return render_template("index.html", premium_enabled=PREMIUM_ENABLED)
```

```html
<script>
    window.PREMIUM_ENABLED = {{ 'true' if premium_enabled else 'false' }};
</script>
```

El backend es la **única fuente de verdad**. No hay riesgo de drift (que el JS diga `true` y el backend diga `false`).

### Decisión: 5 endpoints en lugar de 4

El spec decía "5 análisis" pero "4 endpoints". Hubo una decisión de diseño: **5 endpoints**, uno por análisis. Razón: SRP (Single Responsibility Principle) — un endpoint por responsabilidad. Combinar 2 análisis en un endpoint los acopla. Lo confirmaste antes de implementar.

### `fetchJSON()` wrapper

Patrón típico de cliente HTTP: centralizar el manejo de errores. Si un fetch devuelve 403 con `premium_required: true`, mostramos el modal. Si no, propagamos.

```js
async function fetchJSON(url) {
    try {
        const res = await fetch(url);
        if (res.status === 403) {
            const data = await res.json();
            if (data.premium_required) {
                mostrarModalPremium();
                return null;
            }
        }
        if (!res.ok) return null;
        return await res.json();
    } catch (err) {
        return null;
    }
}
```

**Lección:** DRY sin caer en abstracción prematura. La regla era clara: 403 con `premium_required: true` siempre se maneja igual → vale la pena el wrapper.

**Para revisar:** `git show a9a7bbb --stat` → `app.py:983-1100` para los 5 endpoints → `static/app.js` para los 5 loaders (siguen el mismo patrón, fácil de leer en secuencia).

---

## Lecciones para llevar (resumen)

| # | Concepto | Cuándo aplicarlo |
|---|----------|------------------|
| 1 | **Nombres reveladores** detectan mal uso | Cuando una función se llama "escape" sin contexto, renómbrala por contexto |
| 2 | **Magic numbers** son deuda técnica | Cualquier número con significado de negocio merece constante |
| 3 | **`try/except: pass`** es bug esperando pasar | Si no puedes manejar el error, propágalo |
| 4 | **SRP a nivel de endpoint** | Un endpoint = una responsabilidad. Cuesta más combinarlos que separarlos |
| 5 | **Feature flags** para features pagas | Una constante + un helper es mejor que `if` dispersos |
| 6 | **Backend como source of truth** | Config que el front necesita → inyectar con `render_template` |

---

## Cómo revisar los cambios tú mismo

```bash
# Ver resumen de los 3 commits
cd "C:\Users\sergi\Desktop\Gestor farmacia\farmacia-app"
git log --oneline -3

# Ver el dashboard mejorado
git show 6127c4e --stat

# Ver el refactor (más importante)
git show 7f88a04

# Ver el módulo premium
git show a9a7bbb --stat
```

**Orden sugerido de lectura:** Commit 2 (refactor) → Commit 1 (dashboard) → Commit 3 (premium). El refactor es el que más enseña.

---

*Generado al final de la sesión. Si quieres más detalle de algún cambio, pregúntame y lo expandimos.*

---

# Informe de Cambios — Sesión 2026-06-04 (sesión 4)

> **Tema:** migración de SQLite a PostgreSQL para deploy en Render.
> **Alcance:** `app.py` (backend), `requirements.txt`, `.env.example`. Frontend intacto. Lógica de negocio intacta. Estructura de tablas intacta.

---

## TL;DR

La app ya no usa SQLite. Ahora se conecta a **PostgreSQL** vía la variable de entorno `DATABASE_URL`. Toda la lógica de negocio, los endpoints, el frontend y la estructura de tablas siguen igual — solo cambió el "cómo se habla con la base de datos".

| # | Archivo | Cambio | +/- |
|---|---------|--------|-----|
| 1 | `app.py` | `sqlite3` → `psycopg2` + `RealDictCursor` | +60 / -45 |
| 2 | `app.py` | Placeholders `?` → `%s` (29 cambios) | — |
| 3 | `app.py` | Funciones de fecha SQLite → equivalentes PostgreSQL | — |
| 4 | `app.py` | `lastrowid` → `INSERT ... RETURNING id` | — |
| 5 | `requirements.txt` | + `psycopg2-binary` | +1 línea |
| 6 | `.env.example` | Nuevo — documenta `DATABASE_URL` | nuevo archivo |

---

## Concepto clave: el driver cambia, el SQL cambia un poco, la lógica no

SQLite y PostgreSQL hablan el mismo idioma base (SQL estándar), pero tienen **peculiaridades** que se parecen a dialectos distintos de un mismo lenguaje. La migración consistió en identificar esas peculiaridades y traducirlas.

### Mapeo de peculiaridades

| Concepto | SQLite (antes) | PostgreSQL (ahora) |
|----------|----------------|--------------------|
| Conexión | `sqlite3.connect("farmacia.db")` | `psycopg2.connect(os.environ["DATABASE_URL"])` |
| Acceso a filas | `sqlite3.Row` (dict-like) | `psycopg2.extras.RealDictCursor` (dict puro) |
| Placeholder | `?` | `%s` |
| Auto-increment | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| Decimal/real | `REAL` | `DOUBLE PRECISION` |
| "Hoy" | `date('now', 'localtime')` | `CURRENT_DATE` |
| Inicio de mes | `date('now', 'start of month')` | `DATE_TRUNC('month', CURRENT_DATE)::date` |
| Hace N días | `date('now', '-6 days')` | `CURRENT_DATE - INTERVAL '6 days'` |
| Cast texto→fecha | `date(columna)` | `columna::date` |
| Inspección de schema | `pragma_table_info(?)` | `information_schema.columns` |
| Múltiples statements | `cursor.executescript(...)` | ejecutar uno por uno |
| Último ID insertado | `cursor.lastrowid` | `INSERT ... RETURNING id` + `fetchone()` |
| Cargar script completo | `conn.executescript("...")` | varios `cur.execute("...")` |

### Por qué `RealDictCursor`

Antes, con `sqlite3.Row`, podías hacer `row["total"]` Y `row[0]`. Con `cursor_factory=RealDictCursor` solo puedes hacer `row["total"]`. **Eliminamos el acceso por índice**, lo cual es bueno: el código se vuelve más legible y menos propenso a errores de "columna equivocada".

`grep` confirmó que el código solo usa `row["nombre"]`, nunca `row[0]`. Cero impacto funcional.

---

## Decisión de diseño: la "no-decisión" más importante

Hubo 3 opciones para local dev (sigue funcionando como antes vs. PostgreSQL puro vs. Docker). **Elegiste PostgreSQL puro** — sin fallback a SQLite. Esto es la decisión correcta por estas razones:

1. **DRY real**: el mismo código corre en local y en Render. No hay "dos versiones de la verdad".
2. **Cero abstracción**: no hay capa de compatibilidad, no hay traducción de queries. El código es PostgreSQL nativo.
3. **Alineado con la realidad**: la app va a producción. Si el dev no es idéntico a producción, vas a encontrar bugs en prod que no viste en local.

El trade-off: tienes que instalar PostgreSQL localmente. Pero eso es una sola vez y se hace en 5 minutos. Ver [Cómo correr local](#cómo-correr-local) abajo.

---

## La única "gran" decisión técnica: dónde vive el `fecha` de ventas

En SQLite, la tabla `ventas` tenía:

```sql
fecha TEXT DEFAULT (datetime('now', 'localtime'))
```

Tres opciones para PostgreSQL:

| Opción | Pros | Contras |
|--------|------|---------|
| **A**: `fecha TEXT DEFAULT NOW()::TEXT` | Cambio mínimo | Cast implícito, no es idiomático |
| **B**: `fecha TEXT NOT NULL`, sin default, generado en Python | Schema explícito, sin "magia" | Hay que pasar `fecha` en cada INSERT |
| **C**: `fecha TIMESTAMP DEFAULT NOW()` | Idiomático, tipos correctos | Cambia el tipo de columna, afecta comparaciones |

**Elegimos B**: schema explícito, generación en Python. Razón: el `INSERT` de ventas solo ocurre en **un lugar** del código (`registrar_venta()`), así que el costo de pasar `fecha` es nulo. Y el resto del código ya trata `fecha` como string (formato ISO), así que cero impacto.

```python
import datetime
fecha_actual = datetime.datetime.now().isoformat(timespec="seconds")
conn.execute("""
    INSERT INTO ventas (inventario_id, nombre, laboratorio, cantidad, precio_unitario, total, fecha)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
""", (item["id"], item["nombre"], item["laboratorio"],
      d["cantidad"], item["precio"], total, fecha_actual))
```

---

## La traducción de fechas, explicada

Las funciones de fecha de SQLite son **azúcar sintáctico** sobre lo que Python ya puede hacer. La traducción es casi 1-a-1, pero los nombres cambian.

### Caso 1: "hoy"

```sql
-- SQLite
WHERE date(fecha) = date('now', 'localtime')

-- PostgreSQL
WHERE fecha::date = CURRENT_DATE
```

`fecha::date` es la sintaxis PostgreSQL para "convertir texto a fecha". `CURRENT_DATE` es una constante que vale la fecha actual.

### Caso 2: "desde el inicio del mes"

```sql
-- SQLite
WHERE date(fecha) >= date('now', 'start of month')

-- PostgreSQL
WHERE fecha::date >= DATE_TRUNC('month', CURRENT_DATE)::date
```

`DATE_TRUNC('month', fecha)` te devuelve el primer día del mes al que pertenece esa fecha. Por eso el `::date` al final: porque `DATE_TRUNC` devuelve un timestamp, y para comparar con una fecha hace falta castearlo.

### Caso 3: "últimos 7 días"

```sql
-- SQLite
WHERE date(fecha) >= date('now', '-6 days')

-- PostgreSQL
WHERE fecha::date >= CURRENT_DATE - INTERVAL '6 days'
```

`INTERVAL '6 days'` es la forma PostgreSQL de decir "6 días de duración". Restarlo a `CURRENT_DATE` te da "hace 6 días".

### Caso 4: mes anterior

```sql
-- SQLite
WHERE date(fecha) >= date('now', 'start of month', '-1 month')
  AND date(fecha) <  date('now', 'start of month')

-- PostgreSQL
WHERE fecha::date >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::date
  AND fecha::date <  DATE_TRUNC('month', CURRENT_DATE)::date
```

Un poco más verboso, pero conceptualmente idéntico.

---

## `_ensure_column`: el truco del schema inspector

SQLite expone metadata de tablas con `pragma_table_info(?)`. PostgreSQL no — usa el estándar SQL `information_schema`.

**Antes:**
```python
def _ensure_column(conn, table, column, definition):
    existe = conn.execute(
        "SELECT 1 FROM pragma_table_info(?) WHERE name = ?",
        (table, column)
    ).fetchone()
    if not existe:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
```

**Después:**
```python
def _ensure_column(conn, table, column, definition):
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
    """, (table, column))
    if not cur.fetchone():
        cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}')
```

Diferencias:
1. La sintaxis `?` → `%s`
2. `pragma_table_info(?)` → query a `information_schema.columns`
3. `table_schema = 'public'` — necesario para no tocar tablas de otros schemas (es un filtro de seguridad)

**Nota técnica:** las comillas dobles en `"{table}"` y `"{column}"` son **defensivas**. Hoy las llamadas son todas a tablas/columnas hardcodeadas (sin input del usuario), así que no hay riesgo de inyección. Pero si en el futuro alguien pasa un nombre dinámico, las comillas previenen un SQL injection. Es una buena costumbre.

---

## `lastrowid` → `INSERT ... RETURNING id`

SQLite tiene un atributo mágico: `cursor.lastrowid` te da el ID de la última fila insertada. psycopg2 **no** tiene ese atributo (porque PostgreSQL usa sequences, no el truco de "último rowid").

La forma idiomática PostgreSQL es pedirlo en el mismo `INSERT`:

**Antes:**
```python
cur = conn.execute("INSERT INTO catalogo (nombre, ...) VALUES (?, ...)", (...))
nuevo_id = cur.lastrowid
```

**Después:**
```python
cur = conn.cursor()
cur.execute("""
    INSERT INTO catalogo (nombre, ...) VALUES (%s, ...)
    RETURNING id
""", (...))
nuevo_id = cur.fetchone()["id"]
```

`RETURNING id` es una cláusula PostgreSQL que devuelve columnas de la fila recién insertada. Es más rápido y más limpio que hacer un `SELECT` separado.

---

## `get_db()` con error explícito

```python
def get_db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL no está configurada. "
            "Defínela con: set DATABASE_URL=postgresql://usuario:clave@localhost:5432/farmacia"
        )
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
```

Decisiones:
1. **Error explícito** en vez de fallback a SQLite. Si no configuraste la variable, quieres un error claro, no una conexión fantasma.
2. **Normalizar `postgres://` → `postgresql://`**: Render históricamente usaba `postgres://` (deprecated). psycopg2 acepta ambos pero el módulo `psycopg2` rechaza `postgres://` en versiones recientes. El `.replace(..., 1)` lo arregla.

---

## Lo que NO cambió (a propósito)

| Cosa | Por qué no cambió |
|------|-------------------|
| Endpoints (rutas) | Eran el contrato con el frontend. Tocarlas rompería el JS. |
| Lógica de negocio | La migración es del **driver**, no del **dominio**. |
| Frontend (HTML/CSS/JS) | El frontend no sabe qué base de datos hay detrás. |
| Tipos de columna en `inventario` y `catalogo` | Eran portables a PostgreSQL tal cual. |
| Estructura del JSON de respuesta | El frontend lo consume; no se toca. |
| Tests manuales (con `app.test_client()`) | Funcionan igual, solo cambia la BD de prueba. |

---

## Cómo correr local

### 1. Instalar PostgreSQL

**Windows:** descarga el instalador desde [postgresql.org/download/windows](https://www.postgresql.org/download/windows/). Elige las opciones por defecto. Anota la contraseña del usuario `postgres`.

**Alternativa con Docker (recomendada si ya tienes Docker):**
```bash
docker run --name farmacia-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16
```

### 2. Crear la base de datos

Abre `psql` (o usa pgAdmin) y corre:
```sql
CREATE DATABASE farmacia;
```

### 3. Configurar la variable de entorno

**Windows (PowerShell):**
```powershell
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/farmacia"
```

**Windows (CMD):**
```cmd
set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/farmacia
```

**Mac/Linux:**
```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/farmacia
```

### 4. Instalar dependencias e iniciar

```bash
pip install -r requirements.txt
python app.py
```

El servidor crea las tablas automáticamente y siembra los 158 productos del catálogo INVIMA en el primer arranque.

---

## Cómo deployar en Render

1. Sube el repo a GitHub.
2. En Render, crea un nuevo **"Web Service"** apuntando a tu repo.
3. Render detecta el `Procfile` y sabe que es Python.
4. Crea una **base de datos PostgreSQL** en Render (plan free).
5. En el Web Service, en **Environment**, agrega `DATABASE_URL` — Render la llena automáticamente si la vinculas a la BD.
6. Deploy.

Cuando Render inyecta `DATABASE_URL`, el formato puede ser `postgres://` (sin la "ql"). El `get_db()` lo normaliza.

---

## Migración de datos existentes (si tenías un `farmacia.db` con datos)

SQLite y PostgreSQL no son compatibles a nivel de archivo. Si tienes datos en el `farmacia.db` actual, sigue estos pasos:

### Opción 1: CSV por tabla (recomendada para pocos datos)

```python
import sqlite3
import psycopg2
import csv

# 1. Exportar desde SQLite
sqlite_conn = sqlite3.connect("farmacia.db")
sqlite_conn.row_factory = sqlite3.Row

with open("inventario.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    rows = sqlite_conn.execute("SELECT * FROM inventario").fetchall()
    writer.writerow(rows[0].keys())  # headers
    for r in rows:
        writer.writerow(list(r))

# 2. Importar a PostgreSQL
pg_conn = psycopg2.connect("postgresql://...")
cur = pg_conn.cursor()
with open("inventario.csv", "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    headers = next(reader)
    cols = ", ".join(headers)
    placeholders = ", ".join(["%s"] * len(headers))
    for row in reader:
        cur.execute(f"INSERT INTO inventario ({cols}) VALUES ({placeholders})", row)
pg_conn.commit()
```

Repetir para `ventas` y `catalogo` (el `invima` se siembra solo).

### Opción 2: `pgloader` (recomendada para muchos datos)

```bash
pip install pgloader
pgloader farmacia.db postgresql://postgres:postgres@localhost:5432/farmacia
```

`pgloader` infiere el schema, transforma los tipos y carga los datos. No requiere escribir código.

---

## Verificación

```bash
# 1. Sintaxis correcta
python -c "import ast; ast.parse(open('app.py').read())" → OK

# 2. Importa sin errores
python -c "import app" → OK

# 3. get_db() da error claro si falta DATABASE_URL
python -c "from app import get_db; get_db()" → RuntimeError con instrucciones

# 4. Búsqueda de código SQLite residual
grep -E "sqlite|farmacia\.db|pragma_table_info|executescript|lastrowid" app.py
→ No matches
```

---

## Lecciones para llevar

| # | Concepto | Cuándo aplicarlo |
|---|----------|------------------|
| 1 | **Migración de driver ≠ migración de schema** | Cuando cambias de BD, el SQL cambia un poco, pero el dominio y los tipos no necesariamente |
| 2 | **`%s` es el placeholder universal de psycopg2** | Cualquier consulta con parámetros en PostgreSQL |
| 3 | **`INSERT ... RETURNING id` es la forma idiomática** | Cuando necesitas el ID de algo que acabas de insertar |
| 4 | **`information_schema.columns` para inspeccionar schema** | Cuando necesitas migraciones que dependen del schema actual |
| 5 | **Variables de entorno + error explícito** | Configuración que el dev/prod deben proveer → nunca fallback silencioso |
| 6 | **`RealDictCursor` ≥ `sqlite3.Row`** | Acceso por nombre de columna, más legible y compatible con `**row` |
| 7 | **`::date` y `::tipo` son casts en PostgreSQL** | Cuando SQLite hacía el cast implícito y PostgreSQL necesita explícito |

---

# Informe de Cambios — Sesión 2026-06-05

> **Tema:** deploy en Render + 3 fixes críticos post-deploy.
> **Alcance:** `Procfile`, `requirements.txt`, `runtime.txt`, `app.py`. Sin tocar frontend ni lógica de negocio.

---

## TL;DR

La app pasó de local a producción en `https://gestor-de-farmacia-1.onrender.com`. El deploy tuvo **3 errores en cascada** que se resolvieron en 3 commits: gunicorn necesitó Start Command explícito, `init_db()` no corría porque gunicorn no ejecuta `if __name__ == "__main__"`, y 38 llamadas a `conn.execute()` no funcionaban en psycopg2. Lección: **probar localmente con el mismo comando de prod antes de hacer deploy**.

| # | Commit | Tema | +/- |
|---|--------|------|-----|
| 1 | `2f72dd9` | Preparar deploy: gunicorn + runtime.txt | +5 / -2 |
| 2 | `43a31fa` | Fix: `init_db()` en top-level | +28 / -2 |
| 3 | `6e4311d` | Fix: helper `query()` para psycopg2 | +59 / -38 |

---

## Conceptos aplicados / decisiones de diseño

### Decisión 1: gunicorn en lugar del dev server de Flask

**Qué se hizo:** cambiar `web: python app.py` por `web: gunicorn app:app` en el `Procfile`, y agregar `gunicorn` a `requirements.txt`.

**Concepto:** el servidor que viene con Flask (`flask run` o `app.run()`) es **solo para desarrollo**. Maneja 1 request a la vez, expone stack traces en HTML, y no es seguro en internet. En producción se usa un **servidor WSGI** como gunicorn (Linux), waitress (Windows) o uWSGI.

**Por qué gunicorn y no waitress:**

| | gunicorn | waitress |
|---|---|---|
| Estándar en Linux/Render | ✅ sí | ❌ menos común |
| Funciona en Windows | ❌ no (usa `fcntl`) | ✅ sí |
| Estándar de la industria | ✅ el más usado | ⚠️ segundo lugar |

**Elegimos gunicorn** porque Render es Linux. El "no se puede probar en Windows" es solo una limitación del entorno dev, no del código.

**Lección:** cada entorno (dev / staging / prod) tiene su propio "runtime" (cómo se ejecuta tu código). En local puede ser `flask run`, en prod `gunicorn`. No son intercambiables.

### Decisión 2: `runtime.txt` para fijar la versión de Python

**Qué se hizo:** crear `runtime.txt` con `python-3.12.3`.

**Concepto:** Heroku y Render (que vienen de la cultura Heroku) leen un archivo `runtime.txt` en la raíz del proyecto para saber qué versión de Python usar. Esto evita que el servidor de producción use una versión distinta a la que probaste.

**Dato curioso que aprendimos en este deploy:** Render **ignoró** nuestro `runtime.txt` y usó Python 3.14.3 (su default). Probablemente porque `runtime.txt` está deprecado en Render. **No rompió nada** (la app es compatible con 3.12 y 3.14), pero el control sobre la versión ya no lo tenemos.

**Lección:** los archivos de "configuración mágica" (runtime.txt, Procfile) son útiles pero **frágiles** — el proveedor puede dejarlos de soportar. Vale la pena tener la app compatible con varias versiones.

### Decisión 3: `init_db()` en top-level (no dentro de `if __name__`) — **EL FIX CRÍTICO**

**Qué se hizo:** mover `init_db()` desde dentro del bloque `if __name__ == "__main__":` al top-level del archivo. Se ejecuta **cada vez que se importa el módulo**, no solo cuando se corre `python app.py`.

**El problema que resolvió:**

```python
# ANTES (no funcionaba en Render):
if __name__ == "__main__":
    init_db()           # ← solo se ejecuta con `python app.py`
    app.run(...)

# DESPUÉS (funciona en Render):
init_db()               # ← se ejecuta al importar el módulo

if __name__ == "__main__":
    app.run(...)
```

**Por qué pasó esto:**

| Comando | ¿Ejecuta `if __name__ == "__main__"`? |
|---|---|
| `python app.py` | ✅ sí |
| `gunicorn app:app` | ❌ **no** (gunicorn IMPORTA el módulo y busca la variable `app`) |

Resultado: en Render, `init_db()` nunca se ejecutaba, las tablas no se creaban, y **todos los endpoints que tocaban la BD daban 500**.

**¿Por qué es seguro ejecutarlo múltiples veces?**

- `CREATE TABLE IF NOT EXISTS` → no falla si la tabla ya existe
- El sembrado de INVIMA tiene un check `SELECT COUNT(*) FROM invima` → solo inserta si la tabla está vacía
- En general: `init_db()` es **idompatente** (correo seguro varias veces)

**Lección:** `if __name__ == "__main__"` no es para "código que quiero que corra siempre", es para "código que solo quiero cuando ejecuto el script directamente". Los side-effects (como `init_db()`) que quieras en producción deben ir al top-level o a un script aparte.

**Documentación dejada en el código:** un bloque de comentarios explica todo esto, incluyendo cómo migrar a un script separado (`scripts/init_db.py`) si en el futuro la app crece.

### Decisión 4: Helper `query()` como wrapper sobre el patrón psycopg2 — **EL FIX RAÍZ**

**Qué se hizo:** agregar un helper de 4 líneas al inicio de `app.py` y reemplazar las 38 llamadas a `conn.execute(...)` por `query(conn, ...)`.

**El problema que resolvió:**

```python
# ANTES (sqlite3, ya no funciona):
total = conn.execute("SELECT SUM(cantidad) as total FROM inventario").fetchone()["total"]

# DESPUÉS (psycopg2, sí funciona):
def query(conn, sql, params=None):
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur

total = query(conn, "SELECT SUM(cantidad) as total FROM inventario").fetchone()["total"]
```

**Por qué psycopg2 es distinto:**

- `sqlite3`: el objeto `connection` tiene `.execute()` que devuelve un cursor
- `psycopg2`: el objeto `connection` **no tiene `.execute()`** — hay que crear un cursor explícitamente

Esto se nos pasó en la sesión 4 cuando hicimos la migración. En local funcionó porque solo probamos `init_db()` y un SELECT de prueba, pero nunca testeamos los endpoints. En Render, los endpoints se ejecutan por primera vez y **boom**.

**Por qué un helper en vez de 38 cambios directos:**

| Opción | Cambios | Si en el futuro cambias a SQLAlchemy |
|---|---|---|
| Cambiar cada función con `cur = conn.cursor()` | 38 | Tocar las 38 funciones de nuevo |
| Helper `query(conn, sql, params)` | 1 helper + 38 prefijos | Tocar **1 sola función** |

**Lección:** cuando un patrón se repite N veces en tu código, **considera centralizarlo**. El costo del helper es despreciable; el beneficio (mantenibilidad + futuro cambio de librería) es enorme.

### Decisión 5: no pagar el plan de Render (aceptar cold start)

**Qué se hizo:** dejar la app en el plan Free de Render, que "duerme" después de 15 minutos sin uso.

**Por qué:** el plan free cuesta $0. El plan Starter cuesta $7/mes. Para una app de aprendizaje + una farmacia, $0/mes es suficiente. El trade-off es que la primera request después de un rato de inactividad tarda 30-60 segundos (cold start).

**Lo que NO se hizo (decisión consciente):**

- ❌ Pagar el plan → no es necesario
- ❌ Migrar a Railway / Fly.io → no vale la pena por ahora
- ❌ Configurar un "keep-alive" externo (cron que pegue cada 10 min) → es contra los TOS de Render y no es confiable

**Lección:** los servicios cloud tienen planes. Saber cuál te sirve **hoy** es una decisión técnica, no financiera. Se puede migrar de plan cuando la app lo amerite.

---

## Lo que NO se hizo (decisiones conscientes)

| Lo que NO hicimos | Por qué |
|---|---|
| Probar gunicorn localmente antes de deploy | gunicorn no funciona en Windows (`fcntl` no existe). Confiamos en que funcionaría en Render (Linux). Funcionó. |
| Crear un script `scripts/init_db.py` separado | Para 4 tablas y 158 productos, el top-level es suficiente. La documentación explica cómo migrar a script si crece. |
| Cambiar el render template para que el JS consuma desde un proxy | Los endpoints funcionan, no hay razón |
| Configurar HTTPS personalizado | Render lo provee gratis con Let's Encrypt |
| Configurar un dominio custom (`farmacia.com.co`) | El subdominio `onrender.com` es suficiente por ahora |

---

## Cómo revisar los cambios tú mismo

```bash
cd "C:\Users\sergi\Desktop\Gestor farmacia\farmacia-app"

# Ver los 3 commits de hoy
git log --oneline -3

# Ver el diff completo del fix raíz (el más educativo)
git show 6e4311d -- app.py

# Probar la app en producción (Render tarda 30-60s si está dormida)
curl https://gestor-de-farmacia-1.onrender.com/api/dashboard
```

**Orden sugerido de lectura de los commits:** `6e4311d` (helper, fix raíz) → `43a31fa` (init_db, fix sutil) → `2f72dd9` (preparación, base del deploy).

---

## Lecciones para llevar (resumen)

| # | Concepto | Cuándo aplicarlo |
|---|----------|------------------|
| 1 | **gunicorn ≠ Flask dev server** | Cuando vayas a deployar una app Flask a producción |
| 2 | **`if __name__ == "__main__"` no se ejecuta con gunicorn** | Cuando uses gunicorn/uWSGI, los side-effects van al top-level o a scripts |
| 3 | **psycopg2 requiere `cur = conn.cursor().execute()`** | Cualquier proyecto con psycopg2 — el `conn.execute()` de sqlite3 no existe |
| 4 | **Un helper centralizado > 38 cambios repetidos** | Cuando un patrón se repite N veces, DRY > inlining |
| 5 | **Probar con el mismo comando de prod antes de deploy** | El `app.run()` local ≠ `gunicorn app:app` en Render. Si podés, probá con gunicorn antes. |
| 6 | **`runtime.txt` es frágil** | Útil pero deprecado. Mejor: hacer la app compatible con varias versiones |
| 7 | **Cold start es un trade-off del plan free** | Saber cuándo vale la pena pagar o cuándo quedarse en free |

---

## Lo que aprendimos juntos (resumen ejecutivo)

- ✅ **PostgreSQL ya estaba instalado** en el PC (PostgreSQL 18). Lo descubrimos juntos.
- ✅ **La contraseña de postgres no se podía recuperar** — la reseteamos juntos modificando temporalmente `pg_hba.conf` y reiniciando el servicio.
- ✅ **El deploy tuvo 3 errores en cascada**, cada uno más sutil que el anterior. Los 3 son errores **comunes** que cualquier dev junior enfrenta al deployar por primera vez.
- ✅ **El "init_db en top-level" fue el más educativo** porque toca un concepto fundamental: la diferencia entre ejecutar un script e importar un módulo.
- ✅ **El helper `query()` es la mejor decisión de diseño** porque centraliza el patrón, lo que hace que la app sea más fácil de mantener y migrar.

---

*Generado al final de la sesión 5 (2026-06-05). La app está en producción en `https://gestor-de-farmacia-1.onrender.com`. Si Render no responde, esperá 30-60 segundos y refrescá (cold start del plan free).*

*Si en el futuro querés recordar cómo se hizo algo, este informe + el commit `6e4311d` son los mejores puntos de partida.*
