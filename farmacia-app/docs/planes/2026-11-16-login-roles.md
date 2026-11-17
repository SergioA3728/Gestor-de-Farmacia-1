# Plan: login con usuarios y roles en FarmaSys

Fecha: 2026-11-16 · Estado: **aprobado por Sergio (2026-11-16)**, con el cambio de costos visibles para el cajero

## Glosario
- **Autenticación:** comprobar *quién* eres (usuario y contraseña).
- **Autorización:** decidir *qué puedes hacer* según tu rol.
- **Rol:** tipo de usuario. Aquí hay dos: `admin` (el dueño) y `cajero`.
- **Hash de contraseña:** transformación de un solo sentido de la contraseña. Se guarda el hash y nunca la contraseña. Al iniciar sesión se calcula el hash de lo que la persona escribió y se compara con el guardado. Si alguien roba la base, no obtiene las contraseñas.
- **Sesión:** forma de recordar que alguien ya inició sesión entre una petición y otra. Flask la guarda en una **cookie firmada**, un dato que el navegador reenvía en cada petición. La firma se hace con `SECRET_KEY` para que nadie pueda modificar la cookie sin que se note.
- **`SECRET_KEY`:** clave secreta del servidor con la que se firman las cookies. Quien la conozca puede fabricar una sesión de admin.
- **`before_request`:** función de Flask que se ejecuta antes de *todas* las rutas. Sirve para poner un control en un solo lugar.
- **Decorador:** línea `@algo` encima de una función que le agrega comportamiento. Aquí `@solo_admin` rechaza a quien no sea admin.
- **Jinja:** el sistema de plantillas de Flask. Permite que el servidor decida qué HTML enviar, por ejemplo `{% if rol == 'admin' %}`.
- **Caché:** copia temporal de un dato en memoria para no volver a pedirlo a la base en cada petición.
- **401 / 403 / 503:** códigos HTTP. 401 significa "no has iniciado sesión". 403, "iniciaste sesión pero no tienes permiso". 503, "el servicio no está disponible en este momento".

## Problema
FarmaSys (`farmacia-app/`) es una app Flask publicada en Render que hoy no pide ningún tipo de autenticación. Cualquiera que tenga la URL puede:
- ver nombres y teléfonos de los clientes con deuda (`GET /api/creditos`);
- registrar ventas falsas, borrar productos (`DELETE /api/inventario/<id>`) o registrar abonos (`POST /api/creditos/<id>/abonar`);
- descargar reportes con la utilidad del negocio.

Además, no queda registrado *quién* hizo cada venta. Sergio confirmó que los datos actuales son de prueba (es un proyecto de portafolio).

## Objetivo
Al terminar:
1. Nadie puede usar la app ni la API sin iniciar sesión. Solo son públicas `/login` y los archivos de `/static/`.
2. Hay dos roles con permisos distintos (ver la sección **Permisos**). Los permisos los hace cumplir el servidor. Ocultar botones en la pantalla es solo comodidad, no seguridad. El cajero **sí** ve costos (decisión de Sergio, ver Permisos).
3. El admin puede crear cajeros, desactivarlos y reiniciarles la contraseña desde la app.
4. Cada venta nueva guarda qué usuario la hizo.
5. El primer admin se crea con variables de entorno, sin tocar la base a mano.

**Queda por fuera.** Esto se anota en `docs/PENDIENTES.md` durante la construcción (lo hace el líder, Claude):
- **Límite de intentos de login (protección contra fuerza bruta), con prioridad ALTA.** La app ya es pública en Render. Es aceptable postergarlo solo porque los datos son de prueba. Debe estar hecho antes de cualquier uso con datos reales.
- Recuperar la contraseña por correo y que cada usuario cambie la suya.
- Auditoría de abonos y de cambios de inventario por usuario.
- Tokens CSRF (ver Riesgos).

## Cómo está hoy
- `farmacia-app/app.py`
  - L10 `app = Flask(__name__)`. No hay `SECRET_KEY` ni se usa `session`.
  - L66 `get_db()` abre una conexión nueva con `psycopg2.connect` cada vez que se llama, sin *pool* (reserva de conexiones reutilizables). L61 `query()` ejecuta SQL.
  - L77 `init_db()` crea las tablas con `CREATE TABLE IF NOT EXISTS` y L158 `_ensure_column()` agrega las columnas que falten. `init_db()` corre al importar el módulo (al final del archivo), una vez por cada *worker* (proceso) de gunicorn.
  - 30 rutas, todas abiertas (L174 a L1253). La lista completa está en Permisos.
  - L403 `GET /api/inventario` hace `SELECT *` y devuelve `precio_costo`.
  - L980 `GET /api/ventas` hace `SELECT *` y devuelve `costo_unitario`.
  - L989 `registrar_venta()` inserta en `ventas`.
  - L1253 `/` muestra `templates/index.html` con `render_template(..., premium_enabled=...)`, así que ya usa Jinja.
- `farmacia-app/templates/index.html`: la única página. El menú tiene botones `data-page` = `dashboard` (L64), `inventario` (L68), `ventas` (L72), `reportes` (L80) y `analiticas` (L88). `navigate()` en `static/app.js` L129-150 los conecta.
- `farmacia-app/static/app.js`
  - Hace 22 llamadas `fetch()` a `/api/...` y no maneja 401 ni errores de red.
  - L190: `cargarDashboard()` hace `POST /api/inventario/recategorizar` **cada vez** que carga.
  - L935-949: los reportes se descargan con `window.location.href = "/api/reportes/..."`. Esa descarga **no pasa por `fetch`**.
- `farmacia-app/.env.example`: solo trae `DATABASE_URL`. `farmacia-app/.gitignore` L1 excluye `.env` (verificado).
- `farmacia-app/parser.py` y `farmacia-app/scripts/*.py` **no importan `app.py`** (verificado), así que exigir `SECRET_KEY` no los afecta.
- `farmacia-app/requirements.txt` ya incluye `werkzeug`, que trae `generate_password_hash` y `check_password_hash`. **No hace falta ninguna dependencia nueva.**
- Despliegue: `farmacia-app/Procfile` (`gunicorn app:app`) en Render. Las variables de entorno se configuran en el panel de Render.

## Permisos
| Ruta (archivo `app.py`) | Cajero | Admin |
|---|---|---|
| `GET /api/invima/buscar`, `/api/inferir-categoria`, `/api/categorias`, `GET /api/catalogo` | ✅ | ✅ |
| `GET /api/inventario` | ✅ (con `precio_costo`) | ✅ |
| `GET /api/dashboard*` (5 rutas) | ✅ | ✅ |
| `GET /api/ventas` | ✅ | ✅ |
| `POST /api/ventas` | ✅ | ✅ |
| `GET /api/creditos`, `POST /api/creditos/<id>/abonar` | ✅ | ✅ |
| `POST /api/catalogo` (1) | ❌ | ✅ |
| `POST /api/inventario`, `PUT`/`DELETE /api/inventario/<id>`, `importar`, `confirmar-importacion`, `recategorizar` (6) | ❌ | ✅ |
| `/api/reportes/*` (3) | ❌ | ✅ |
| `/api/analytics/*` (5) | ❌ | ✅ |
| `/api/usuarios*` (nuevas) | ❌ | ✅ |

**15 rutas existentes** llevan `@solo_admin`, además de las nuevas de usuarios.

Decisiones explícitas (Sergio las puede cambiar antes de aprobar):
- **El cajero registra abonos y ve nombre y teléfono de todos los deudores.** Atiende el mostrador y cobra, así que lo necesita. El riesgo de que marque créditos como pagados sin cobrar se reduce, pero no desaparece: queda la auditoría de abonos en Pendientes.
- **El cajero SÍ ve el costo de cada producto (decisión de Sergio).** En tiendas de barrio el precio no es fijo: a clientes conocidos o recurrentes el cajero cobra más cerca del costo, así que necesita el costo como referencia. No ve reportes ni analíticas.
- **Un admin puede reiniciar la contraseña de otro admin.** Se acepta porque es un negocio con un solo dueño.

## Cambios

### 1. `farmacia-app/app.py`

**a) Configuración, después de L10:**
- `SECRET_KEY`: se lee con `os.environ.get("SECRET_KEY")`. Si falta, se lanza `RuntimeError("Falta SECRET_KEY: genera una con python -c \"import secrets; print(secrets.token_hex(32))\" y defínela en .env o en Render")`, el mismo estilo que ya usa `get_db()` con `DATABASE_URL`. La app no arranca, con un mensaje claro en los logs.
- `SESSION_COOKIE_HTTPONLY=True`: JavaScript no puede leer la cookie.
- `SESSION_COOKIE_SAMESITE="Lax"`: el navegador no envía la cookie en POST que vienen de otros sitios.
- `SESSION_COOKIE_SECURE`: la cookie solo viaja por HTTPS. Vale `True` salvo que `COOKIE_SEGURA=0`, que se usa en local porque ahí no hay HTTPS.
- `PERMANENT_SESSION_LIFETIME = 12 horas`, lo que dura un turno.

**b) En `init_db()`:**
```sql
CREATE TABLE IF NOT EXISTS usuarios (
    id            SERIAL PRIMARY KEY,
    usuario       TEXT NOT NULL UNIQUE,
    nombre        TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    rol           TEXT NOT NULL CHECK (rol IN ('admin','cajero')),
    activo        BOOLEAN NOT NULL DEFAULT TRUE,
    creado        TEXT NOT NULL
)
```
- `_ensure_column(conn, "ventas", "usuario_id", "INTEGER")` y `_ensure_column(conn, "ventas", "vendedor", "TEXT")`. `vendedor` copia el nombre del usuario, igual que hoy se copia el nombre del producto, para que el histórico no cambie si después se edita el usuario. Las ventas anteriores quedan en `NULL`.
- **Primer admin:** solo se crea si la tabla `usuarios` está vacía y existen `ADMIN_USUARIO` y `ADMIN_PASSWORD`.
  - `ADMIN_PASSWORD` tiene que tener **al menos 8 caracteres**. Si es más corta, no se crea el admin y se imprime un aviso.
  - Se usa `INSERT ... ON CONFLICT (usuario) DO NOTHING` para que dos workers que arrancan a la vez no creen dos admins.
  - La contraseña nunca se imprime. Si la tabla está vacía y faltan las variables, se imprime un aviso.

**c) Protección global con `before_request`:**
```python
RUTAS_PUBLICAS = {"login", "static"}   # nombres de endpoint de Flask

@app.before_request
def exigir_login():
    if request.endpoint in RUTAS_PUBLICAS:
        return
    try:
        usuario = usuario_actual()
    except psycopg2.Error:
        # La base no responde: no es "no autorizado", es "no disponible".
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "Base de datos no disponible, intenta de nuevo"}), 503
        return "Base de datos no disponible, recarga en unos segundos", 503
    if not usuario:
        # Las descargas de reportes son navegación normal (window.location), no fetch:
        # para ellas, y para las páginas, se redirige al login en vez de devolver JSON.
        if request.path.startswith("/api/") and not request.path.startswith("/api/reportes/"):
            return jsonify({"ok": False, "error": "Inicia sesión"}), 401
        return redirect(url_for("login"))
    g.usuario = usuario                # g = objeto de Flask que dura una sola petición
```
Se protege **todo por defecto**: si mañana alguien agrega una ruta y se olvida de protegerla, igual queda protegida.

**`usuario_actual()` y la carga de conexiones.** El dashboard dispara 5 `fetch` en paralelo. Si cada uno abriera una conexión extra para leer el usuario, se duplicarían las conexiones contra una base gratuita que tiene pocas. Para evitarlo:
- Se guarda una **caché en memoria por worker**, un diccionario `{uid: (datos_usuario, vence_en)}` con duración de **60 segundos**.
- Si el usuario está en la caché y no ha vencido, no se consulta la base.
- Si no está, se hace `SELECT id, nombre, rol, activo FROM usuarios WHERE id = %s` con su propia conexión y `try/finally`. Si `activo` es falso, se trata como si no hubiera sesión.
- Cuando el admin desactiva a un usuario o le cambia el rol, se borra su entrada de la caché **en ese worker**. En los demás workers el cambio tarda como máximo 60 segundos en aplicarse. Se acepta ese retraso.

**d) Decorador `@solo_admin`:** responde 403 si `g.usuario["rol"] != "admin"`. Se aplica a las 15 rutas marcadas con ❌ y a las nuevas de usuarios.

**e) ~~Filtrado de costos~~:** eliminado; el cajero ve costos.

**f) Rutas nuevas:**
- `GET /login`: muestra `templates/login.html`. **Si ya hay una sesión válida, redirige a `/`.**
- `POST /login`: valida con `check_password_hash` y comprueba que el usuario esté `activo`. Si está bien, hace `session.clear()` y luego `session["uid"] = id` (esto evita la *session fixation*, que alguien te imponga una sesión preparada por él). Si falla, muestra un mensaje genérico, "Usuario o contraseña incorrectos", que no revela qué usuarios existen. No acepta parámetro `next`, así que no hay riesgo de redirección abierta.
- `POST /logout`: `session.clear()` y redirige a `/login`.
- `GET /api/usuarios` (admin): lista los usuarios sin `password_hash`.
- `POST /api/usuarios` (admin): crea un usuario. Valida que `usuario` no esté vacío, que `rol` sea válido y que la contraseña tenga al menos 8 caracteres.
- `PUT /api/usuarios/<id>` (admin): activar o desactivar, cambiar el rol o reiniciar la contraseña. **El admin no puede desactivarse a sí mismo ni quitarse el rol de admin.** Así siempre queda al menos el admin que hace la petición.

> Ya no se crea `GET /api/yo`. El servidor pasa el usuario a la plantilla (ver punto 3), así que el frontend no necesita preguntarlo.

**g) `index()` (L1253):** `render_template("index.html", premium_enabled=..., usuario=g.usuario)`.

**h) `registrar_venta()` (L989):** agrega `usuario_id = g.usuario["id"]` y `vendedor = g.usuario["nombre"]` al `INSERT INTO ventas`.

### 2. `farmacia-app/templates/login.html` (nuevo)
Formulario HTML que hace `POST /login`, usa el mismo `style.css` y muestra el mensaje de error si lo hay. **No lleva JavaScript ni llama a la API**, así que no puede generar un bucle de redirecciones con el 401.

### 3. `farmacia-app/templates/index.html`
Lo decide el servidor con Jinja, usando `usuario.rol`. Así no hay un instante en que el cajero vea botones de admin antes de que se oculten.
- El nombre del usuario y un botón "Salir" (`<form method="post" action="/logout">`).
- Los botones de menú `reportes` y `analiticas`, y un botón nuevo `data-page="usuarios"`, se envuelven en `{% if usuario.rol == 'admin' %}`. El botón nuevo se integra solo con `navigate()`, porque `app.js` L150 ya conecta todo `.nav-item[data-page]`.
- Se agrega la sección de página `usuarios`, también solo para admin, con una tabla de usuarios y un formulario para crear cajeros.
- Para el cajero, la pestaña `inventario` se deja visible en **modo lectura**: se ocultan con Jinja "Agregar", "Importar", "Editar" y "Borrar". Al construir se verifica que la búsqueda de productos en Ventas siga funcionando.
- Se agrega `<body data-rol="{{ usuario.rol }}">` para que `app.js` sepa el rol sin hacer otra petición.

### 4. `farmacia-app/static/app.js`
- **Envoltorio de `fetch` al inicio del archivo** (un solo lugar, no hay que tocar las 22 llamadas):
  - si la respuesta es 401, envía al usuario a `/login`;
  - si es 403, muestra "No tienes permiso para esta acción";
  - si es 503 o hay un error de red, muestra "Sin conexión con el servidor, intenta de nuevo".
- **L190:** la llamada automática a `recategorizar` se hace solo si `document.body.dataset.rol === "admin"`. Sin esta condición, cada vez que un cajero abre el dashboard recibiría un 403.
- Se agregan funciones para la sección Usuarios: listar, crear, activar/desactivar y reiniciar la contraseña.
- Se acepta esta limitación: si a un cajero se le cambia el rol con la pestaña abierta, la pantalla sigue igual hasta que recargue. El servidor sí aplica el cambio en su siguiente petición, como máximo 60 segundos después.

### 5. `farmacia-app/tests/test_permisos.py` (nuevo, en el repo)
Esta es la **defensa principal contra el riesgo más probable: olvidar `@solo_admin` en una ruta.** El script:
- reemplaza la base por una conexión falsa (la misma técnica que la prueba de ventas de la sesión anterior, que estaba en una carpeta temporal y **no** en el repo);
- recorre `app.url_map` (la lista de todas las rutas que Flask conoce);
- falla si una ruta no aparece en la lista `PERMITIDAS_CAJERO` ni devuelve 403 para un cajero;
- comprueba que sin sesión toda `/api/*` devuelve 401 (o redirige, en `/api/reportes/*`) y `/` redirige a `/login`;
- comprueba que el admin no se puede desactivar a sí mismo y que `ADMIN_PASSWORD` corto no crea admin;
- comprueba que si la base falla se responde 503.

Se corre con `python tests/test_permisos.py`. Necesita Flask y psycopg2 instalados, pero no PostgreSQL.

### 6. `farmacia-app/.env.example`
Agregar `SECRET_KEY=`, `ADMIN_USUARIO=`, `ADMIN_PASSWORD=` y `COOKIE_SEGURA=0`, todas vacías o con un valor de ejemplo. Añadir un comentario con el comando para generar la clave.

### 7. `farmacia-app/docs/PENDIENTES.md`
El líder (Claude) agrega los cuatro puntos de "Queda por fuera", con el límite de intentos de login marcado como prioridad ALTA.

### 8. Render (panel, lo hace Sergio)
Definir `SECRET_KEY` (aleatoria y larga), `ADMIN_USUARIO` y `ADMIN_PASSWORD` (8 caracteres o más) **antes** de desplegar. Después del primer arranque se puede borrar `ADMIN_PASSWORD` del panel, porque solo se usa cuando la tabla está vacía.

## Alternativas consideradas
1. **Flask-Login (librería).** Es lo estándar y trae `@login_required` y `current_user`. No se usa en esta versión: son unas 60 líneas propias que Sergio puede leer y entender, y así no se suma una dependencia. Si más adelante hace falta "recordarme" u otras funciones avanzadas, se migra.
2. **Poner `@login_required` en cada ruta en vez de `before_request`.** Se descarta. Con 30 rutas, olvidar una deja un hueco; negar todo por defecto es más seguro.
3. **JWT (un token firmado que el frontend guarda y envía) en vez de cookie de sesión.** Se descarta. El frontend y la API están en el mismo dominio, y una cookie `HttpOnly` es más simple y más difícil de robar con JavaScript que un token guardado en `localStorage`.
4. **Consultar la base en cada petición sin caché.** Desactivar a un usuario se aplicaría al instante, pero se duplicarían las conexiones en el dashboard, que hace 5 peticiones en paralelo. Se elige la caché de 60 segundos.
5. **Guardar el rol solo en la cookie, sin consultar la base.** No usa conexiones extra, pero un cajero desactivado seguiría entrando hasta 12 horas. Se descarta.
6. **Pedirle el rol al servidor con `GET /api/yo` desde JavaScript.** Se descarta. Con Jinja el servidor ya sabe el rol al armar la página, así que se ahorra una petición y no se ven botones de admin ni por un instante.
7. **Una sola contraseña compartida.** Sergio la descartó: no se sabe quién vendió y no se le puede quitar el acceso a una sola persona.

## Riesgos
| Riesgo | Cómo se evita o se deshace |
|---|---|
| Desplegar sin `SECRET_KEY` o sin admin y quedar fuera | Sin `SECRET_KEY` la app no arranca y muestra un mensaje claro. Si no hay admin, se avisa en los logs. Las variables se configuran en Render antes del deploy. |
| Olvidar `@solo_admin` en una ruta | `tests/test_permisos.py` recorre **todas** las rutas automáticamente. |
| La base no responde y todo da 500 | `before_request` responde 503 con un mensaje, y `app.js` lo muestra. |
| Se agotan las conexiones de la base gratuita | Caché de 60 segundos para el usuario. Las conexiones se abren y se cierran con `try/finally`. |
| Algo del frontend falla para el cajero (403 inesperados, la venta sin inventario) | Probar con un cajero el flujo completo: dashboard, venta, crédito y abono. Revisar la consola del navegador. |
| CSRF (otro sitio hace que tu navegador envíe una petición con tu cookie) | `SameSite=Lax` bloquea los POST que vienen de otros sitios, incluido `importar`, que usa `multipart/form-data` y no pasa por la consulta previa de CORS. Para PUT y DELETE el navegador exige esa consulta previa (*preflight*), y la app no habilita CORS. Es aceptable para esta versión. Los tokens CSRF quedan en Pendientes. |
| Fuerza bruta sobre `/login` | **Fuera de alcance, prioridad ALTA en Pendientes.** El hash lento de werkzeug lo frena en parte. Se acepta solo porque los datos son de prueba. |
| `init_db()` corre en varios workers a la vez | Se usan `CREATE TABLE IF NOT EXISTS` y `INSERT ... ON CONFLICT DO NOTHING`. |
| Scripts que dejan de funcionar al exigir `SECRET_KEY` | Verificado: ningún script importa `app.py`. |
| Volver atrás | Todo el cambio queda en un commit y `git revert` deja la app como antes. La tabla `usuarios` y las columnas nuevas de `ventas` pueden quedarse, porque el código viejo no las lee. **Si algún día hay datos reales, se hace un respaldo de la base antes de desplegar.** |

## Cómo se comprueba
1. **Automático:** `python tests/test_permisos.py` muestra "TODO OK" (permisos, 401, 403, 503, costos ocultos y reglas de admin).
2. Con PostgreSQL local de prueba y un `.env` con `SECRET_KEY`, `ADMIN_USUARIO`, `ADMIN_PASSWORD` y `COOKIE_SEGURA=0`:
   1. Arrancar la app. En `usuarios`, el `password_hash` debe empezar por `scrypt:` o `pbkdf2:`, nunca ser la contraseña en texto.
   2. Sin sesión: `/` redirige a `/login`, `curl http://localhost:5000/api/creditos` devuelve **401** y `/static/style.css` carga.
   3. Con sesión iniciada, entrar a `/login` redirige a `/`.
   4. Con una contraseña incorrecta sale el mensaje genérico. Con la correcta se entra al dashboard.
   5. Como admin, crear `caja1`. Una contraseña de 5 caracteres debe ser rechazada.
   6. Como `caja1`: el menú no muestra reportes, analíticas ni usuarios, y el inventario no tiene botones para modificar. El dashboard carga sin errores en la consola. La búsqueda de productos en Ventas funciona. Se puede vender de contado y a crédito, y abonar. En la base, `ventas.vendedor` dice el nombre de `caja1`.
   7. Como admin, desactivar `caja1`. Como máximo 60 segundos después, la siguiente acción de `caja1` lo manda a `/login`.
   8. Si el admin intenta desactivarse a sí mismo, se rechaza.
   9. "Salir" cierra la sesión. Al volver atrás en el navegador y recargar, se llega a `/login`.
   10. Detener PostgreSQL con la app abierta: aparece "Sin conexión con el servidor", no una página en blanco.
3. En Render, con las variables configuradas: el deploy arranca, se puede iniciar sesión y la cookie lleva `Secure` y `HttpOnly`. Se ve en las herramientas de desarrollador del navegador, en Application > Cookies.

## Revisión del pez dorado (2026-11-16) y qué se hizo
Veredicto: **Corregir antes de construir.**
| Hallazgo | Qué se hizo |
|---|---|
| El cajero recibe costos por `SELECT *` | Se filtraron, pero Sergio decidió que el cajero **sí** debe verlos (precio negociado en tiendas de barrio). Se quitó el filtro. |
| Prueba de permisos manual y fácil de saltar | Nuevo `tests/test_permisos.py`, que recorre `url_map`. |
| Conteo 17 vs 15 | Corregido a 15. |
| Las descargas de reportes no pasan por el envoltorio de `fetch` | `/api/reportes/*` sin sesión redirige a `/login` en vez de devolver JSON. |
| Fallo de la base en `usuario_actual()` | Responde 503 y `app.js` lo muestra. |
| Conexiones extra en las peticiones paralelas | Caché de 60 segundos por worker. |
| `KeyError` en vez de un mensaje claro | `RuntimeError` con instrucciones. |
| Cuándo se llama `/api/yo` y el parpadeo de botones | Se quita `/api/yo`: Jinja decide el HTML y `data-rol` en `<body>`. |
| `/login` con sesión iniciada | Redirige a `/`. |
| `ADMIN_PASSWORD` sin mínimo | Mínimo de 8 caracteres. |
| ¿Dónde está el "script como el de ventas"? | Aclarado: estaba en una carpeta temporal. El nuevo va al repo. |
| Cómo se integra la sección Usuarios | `data-page="usuarios"`, que `navigate()` ya maneja. |
| Quién escribe en PENDIENTES y qué | Punto 7 de Cambios. |
| Abonos y deudores visibles para el cajero | Se deja como decisión explícita en Permisos. |
| El admin reinicia la contraseña de otro admin | Se acepta y queda escrito. |
| El rol cambia con la pestaña abierta | Se acepta y queda escrito (punto 4). |
| Scripts que importan `app.py` | Verificado: ninguno lo hace. |
| ¿`.env` en `.gitignore`? | Verificado: `.gitignore` L1. |
| Fuerza bruta con la app ya pública | Sigue fuera de alcance, pero ahora está marcado con prioridad ALTA y con la condición explícita de hacerlo antes de usar datos reales. |
| CSRF: el argumento del *preflight* es débil para `multipart` | Corregido en Riesgos: `SameSite=Lax` es lo que protege `importar`. |

## Decisión posterior de Sergio y pendiente derivado
- El cajero ve costos como referencia de precio (ver Permisos).
- **Precio negociado en la venta:** hoy `registrar_venta()` siempre cobra `inventario.precio`. Para que el cajero cobre un precio distinto hace falta un cambio aparte (campo de precio en la venta, validación y efecto en reportes). Se hará después del login.

## Cambios respecto al plan
- **Ocultar con CSS en vez de `{% if %}`:** `app.js` busca varios botones por `id` al cargar (p. ej. `btn-agregar-producto`); quitarlos del HTML podía romperlo. Se usa `<body data-rol>` (puesto por el servidor) + la regla `body[data-rol="cajero"] .solo-admin { display:none }`. Mismo efecto sin parpadeo; la seguridad sigue en `@solo_admin`.
- **Campo "Costo (referencia)" en la pantalla de Ventas:** no estaba en el plan. Sin él el cajero no veía el costo aunque la API lo enviara, y fue lo que Sergio pidió.
- **Hash de relleno en el login:** si el usuario no existe se calcula igual un hash, para que el tiempo de respuesta no delate qué usuarios existen.
- **Avisos 403/503/sin red:** se muestran en una franja flotante creada por `app.js` (`avisoGlobal`).
- **`tests/test_permisos.py`** exige además que haya exactamente 18 rutas de admin, así una ruta nueva obliga a decidir su permiso. Se comprobó que detecta un `@solo_admin` quitado a propósito.
