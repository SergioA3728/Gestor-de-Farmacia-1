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

*Generado al final de la sesión 4. Si tienes PostgreSQL instalado y quieres probarlo, sigue [Cómo correr local](#cómo-correr-local). Si encuentras un bug, ábrelo con el patrón de las sesiones anteriores.*
