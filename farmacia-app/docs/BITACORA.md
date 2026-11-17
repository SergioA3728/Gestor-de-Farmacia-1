# Bitácora de FarmaSys

## 2026-11-16 · Mapeo inicial del proyecto

**Qué se hizo:** Se leyó el proyecto completo sin cambiar código, para entender cómo está armado y qué problemas tiene antes de mejorarlo. Es el punto de partida para las mejoras del portafolio.
**Por qué:** No se puede mejorar bien algo que no se entiende, y el proyecto hay que poder explicarlo y defenderlo.

**Decisiones (las que ya tiene el proyecto):**
- **SQL a mano con `psycopg2`, sin ORM.** Se gana control total y nada de "magia": cada consulta se lee tal cual. Se paga con más código repetido (abrir y cerrar conexión en cada ruta) y con más facilidad para errores como olvidar cerrar la conexión. Un ORM como SQLAlchemy daría modelos, relaciones y migraciones, a cambio de una capa más que aprender.
- **Una sola página HTML + JavaScript sin framework.** Es simple, no necesita compilar nada y carga rápido. El costo es que `app.js` (~1100 líneas) mezcla interfaz, estado y llamadas a la API. React o Vue ordenarían eso en componentes, pero para este tamaño serían más de lo necesario.
- **Todo el backend en `app.py` (1255 líneas).** Es cómodo al principio y ya es el límite. Si el proyecto creciera diez veces, habría que separarlo en módulos (Blueprints de Flask) por área: inventario, ventas, reportes.
- **Crear tablas al arrancar (`init_db()` en app.py:1251) en vez de migraciones.** Funciona para tablas nuevas, pero no lleva registro de cambios en el esquema. Por eso la columna `invima.categoria` existe en la base y no en el código (problema 3).
- **Sin foreign keys.** Se pueden borrar y recargar tablas sin que la base de datos se queje. A cambio, los datos pueden quedar inconsistentes sin ningún aviso (problema 5).
- **Copiar nombre y precio en cada venta.** Es una buena decisión: la venta guarda el precio de ese momento, así que el histórico no cambia si después se actualiza el inventario.

**Cómo funciona (resumen):**
- Navegador: `templates/index.html` + `static/app.js` (`navigate()`, l.129) llaman a la API con `fetch`.
- Servidor: Flask en `app.py`. `get_db()` (l.66) abre la conexión con `DATABASE_URL`.
- Base de datos: PostgreSQL, con las tablas `catalogo`, `inventario`, `ventas`, `invima` y `creditos`.
- Producción: Render ejecuta `gunicorn app:app` (`Procfile`).
- Agregar producto: `buscarInvimaModal()` (app.js:38) → `GET /api/invima/buscar` → `GET /api/inferir-categoria` → `POST /api/inventario` (app.py:409), que suma la cantidad si el producto ya existe o inserta uno nuevo.
- Registrar venta: `venta-guardar` (app.js:654) → `POST /api/ventas` (`registrar_venta`, app.py:986): valida stock → `UPDATE inventario` → `INSERT ventas` (+ `creditos` si es fiado) → `commit`.

**Conceptos nuevos:** endpoint (URL de la API que hace una tarea), driver (librería que habla con la base de datos), ORM (capa que traduce objetos a SQL), foreign key (regla que obliga a que un id apunte a una fila real), transacción (grupo de cambios que se guardan todos o ninguno), worker (proceso de gunicorn que atiende peticiones), race condition (error que depende del orden en que se cruzan dos operaciones simultáneas), migración (script versionado que cambia el esquema de la base).

### Los 5 problemas más importantes

1. **Sin autenticación con la app pública en Render.** *Comprobado.* Ninguna ruta pide usuario. Cualquiera con la URL puede ver los nombres de los clientes con deuda, las ventas y los márgenes, y también puede borrar productos o marcar créditos como pagados.
2. **La venta no valida la cantidad ni la concurrencia** (app.py:1002-1014). *Comprobado.*
   - No revisa `cantidad > 0`. Con -5, el `UPDATE` hace `cantidad - (-5)`: el stock sube y la venta queda con total negativo.
   - Lee, valida y actualiza en pasos separados, sin bloquear la fila. Dos ventas simultáneas de la última unidad dejan el stock en -1.
3. **La columna `invima.categoria` no está en `init_db()`** (app.py:116-127), pero app.py:360 la lee. *Comprobado en el código.* *Por confirmar* si la base de producción la tiene. En una base nueva, elegir un producto INVIMA daría error 500.
4. **Conexiones sin `try/finally`.** *Comprobado.* Si una ruta lanza una excepción, `conn.close()` no se ejecuta. El plan gratis tiene pocas conexiones, así que con suficientes errores la app deja de responder.
5. **`parser.py:74` borra `invima` y la vuelve a cargar sin foreign keys.** *Comprobado.* Los `invima_id` de `inventario` quedan apuntando a otro medicamento o a nada, sin aviso.

El resto de problemas está en `docs/PENDIENTES.md`.

**Cómo comprobarlo:** abrir app.py:1002 y ver que no hay validación de `cantidad > 0`. Buscar `categoria` dentro del `CREATE TABLE invima` de `init_db()` y ver que no aparece.

### Ampliación del mapeo: riesgos de datos y de dinero

Los cinco problemas de arriba son los más graves. Estos otros afectan **números que el dueño de la farmacia lee y en los que confía**, y no estaban explicados.

- **Reporte de utilidad con el costo equivocado** (app.py:841). *Comprobado.* Calcula `SUM(cantidad * precio)` del inventario, que es precio de venta. Pero el último commit agregó `precio_costo`. La utilidad sale mal sin dar ningún error, que es peor que un fallo visible.
- **Índice de alerta del reporte de inventario** (app.py:661). *Comprobado.* `row[7]` busca "CRÍTICO" en una columna que no es la de alerta, así que el color nunca se aplica. (Detalle en PENDIENTES.)
- **Abonos** (app.py:1044-1066). *Comprobado.*
  - `monto <= 0` con un texto como "500" lanza `TypeError` y devuelve error 500 en vez de 400.
  - Lee el saldo, calcula en Python y escribe. Dos abonos simultáneos al mismo crédito pisan el cálculo del otro y se pierde uno. Mismo patrón de condición de carrera que la venta. Arreglo: `UPDATE ... SET saldo = saldo - %s` hecho por la base de datos.
- **`es_credito` mal interpretado** (app.py:1008). *Comprobado.* Se toma del JSON del cliente tal cual. Si llega el texto `"false"`, Python lo evalúa como verdadero y se crea un crédito que no existe. Hay que validar que sea booleano.
- **Zona horaria mezclada** (app.py:1017 frente a 904 y 927). *Por confirmar.* La venta guarda `datetime.now()` con la hora del servidor (en Render suele ser UTC). El dashboard filtra con `CURRENT_DATE` de PostgreSQL. Una venta a las 8 p. m. en Barranquilla (UTC-5) puede contarse como del día siguiente. Además `fecha` es `TEXT`, lo que obliga a convertirla con `::date`.
- **`init_db()` en cada worker** (app.py:1251). *Comprobado.* Se ejecuta al importar el módulo, así que cada worker de gunicorn lo corre al arrancar. Como usa `CREATE TABLE IF NOT EXISTS` no rompe nada hoy, pero dos workers que arrancan a la vez pueden chocar al crear o alterar tablas. Con migraciones esto desaparece.

**Decisión para priorizar:** primero lo que pierde o falsea dinero (venta, abono, `es_credito`, utilidad), luego autenticación, luego conexiones y esquema. Se hace en ese orden porque autenticación protege de terceros, pero estos errores ocurren con usuarios legítimos todos los días.

**Patrón que se repite y vale llevarse a otros proyectos:** "leer, calcular en Python, escribir" sin bloqueo (venta y abono). La regla general es dejar que la base de datos haga la operación atómica: `UPDATE ... WHERE cantidad >= %s` y revisar cuántas filas cambió.

**Conceptos nuevos:** atómica (operación que ocurre completa o no ocurre, sin que otra se cuele en medio), `TypeError` (error de Python al comparar tipos incompatibles, como texto con número), UTC (hora universal; Colombia es UTC-5), idempotente (que ejecutarla varias veces deja el mismo resultado, como `IF NOT EXISTS`).

## 2026-11-16 · Venta segura: stock atómico, validaciones y costo guardado

**Qué se hizo:** `registrar_venta()` (`app.py`, `POST /api/ventas`) ahora resta el stock con una sola orden SQL que revisa y actualiza a la vez. También valida los datos de entrada, guarda el costo del producto en cada venta y cierra la conexión siempre.
**Por qué:** viene de las respuestas de Sergio a las preguntas 1 y 3 del mapeo. Él vio que dos ventas simultáneas dejaban el stock en -1, pero no sabía cómo arreglarlo. También creía que el costo ya estaba guardado en `ventas`, y no lo estaba.

**Decisiones:**
- **`UPDATE ... WHERE id = %s AND cantidad >= %s RETURNING ...` en vez de leer, comparar en Python y escribir.**
  - Alternativa 1: `SELECT ... FOR UPDATE`, que bloquea la fila a mano. Funciona, pero son dos pasos y hay que recordar el bloqueo.
  - Alternativa 2: subir el aislamiento a SERIALIZABLE, que obliga a reintentar transacciones.
  - Se eligió el `UPDATE` condicional porque es una sola orden y es lo más simple. En READ COMMITTED (el nivel por defecto de PostgreSQL), el segundo cajero espera a que el primero termine y vuelve a evaluar la condición con el stock ya restado. Si no queda stock, no actualiza ninguna fila. `RETURNING` devuelve nombre, precio y costo sin otra consulta.
  - Se paga con un caso más: si el `UPDATE` no devuelve fila, hay que hacer un `SELECT 1` para distinguir "no existe" (404) de "sin stock" (400).
- **Validar antes de abrir la conexión.** Los datos malos no gastan conexiones del plan gratis.
- **Validación estricta de tipos.**
  - `cantidad` e `inventario_id` deben ser enteros positivos, y se excluye `bool` porque en Python `True == 1`.
  - `es_credito` debe ser booleano real: el texto `"false"` es verdadero en Python.
  - Los campos de texto deben ser texto.
  - Un crédito exige `cliente_nombre`, porque sin nombre no se puede cobrar.
  - Se pagan respuestas 400 más estrictas: un cliente que antes "funcionaba" mandando `"2"` en vez de `2` ahora falla.
- **`ventas.costo_unitario` copia `precio_costo` en el momento de la venta**, igual que ya se hacía con `precio_unitario`. Así la utilidad histórica no cambia si luego se cambia el costo en inventario. Las ventas viejas quedan en NULL ("sin costo registrado") y no se inventa un valor retroactivo, porque sería un dato falso.
- **`try/finally` para `conn.close()`.** `finally` se ejecuta con `return` o con excepción. Si no hubo `commit`, cerrar la conexión descarta los cambios a medias, incluida la resta de stock. Esto resuelve el problema 4 del mapeo solo para esta ruta.

**Cómo funciona:**
1. `registrar_venta()` lee el JSON con `get_json(silent=True)` y valida.
2. Abre la conexión y ejecuta el `UPDATE` condicional.
3. Si no devolvió fila, responde 404 o 400.
4. Si la devolvió, inserta en `ventas` (con `costo_unitario`) y, si es fiado, en `creditos`.
5. Hace `commit` y el `finally` cierra la conexión.
- `init_db()` agrega la columna con `_ensure_column(conn, "ventas", "costo_unitario", "DOUBLE PRECISION")`.

**Conceptos nuevos:** READ COMMITTED (nivel de aislamiento por defecto de PostgreSQL: cada orden ve lo ya confirmado por otras), `RETURNING` (cláusula que devuelve las filas que modificó un `UPDATE` o `INSERT`), `silent=True` (Flask devuelve `None` en vez de lanzar error si el JSON es inválido), `finally` (bloque que se ejecuta siempre), conexión falsa o mock (objeto que imita la base para probar sin PostgreSQL real).

**Cómo comprobarlo:**
- Hecho: 19 casos con una conexión falsa. El revisor aprobó el cambio, y sus ajustes de validación ya están aplicados.
- **No probado:** el SQL contra PostgreSQL real. Con una base de prueba:
  1. Vender más que el stock debe dar 400 y dejar el stock igual.
  2. Vender con `"cantidad": -5` o `"es_credito": "false"` debe dar 400.
  3. Mirar `SELECT costo_unitario FROM ventas ORDER BY id DESC LIMIT 1`.
  4. Para la carrera real, lanzar dos ventas de la última unidad a la vez: solo una debe salir bien.

**Pendiente de este cambio:**
- Los abonos tienen el mismo patrón de carrera (`app.py:~1060`).
- El reporte de utilidad (`app.py:~855`) todavía no usa `costo_unitario`. Cuando lo use tendrá que tratar el NULL con `COALESCE`.
- Zona horaria.
- Autenticación.

**Lección que se lleva a otros proyectos:** "leer, calcular en Python, escribir" deja un hueco entre la lectura y la escritura por donde se cuela otra petición. Cuando la regla es de datos ("no vender más de lo que hay"), hay que ponerla en la operación de la base de datos, que es atómica, y revisar el resultado (filas devueltas), en vez de revisarla antes en el código.

**Preguntas para Sergio:**
1. Dos cajeros venden 3 unidades cada uno de un producto con 4 en stock, exactamente a la vez. ¿Qué responde cada petición y cuánto stock queda? ¿Qué hace PostgreSQL con el segundo `UPDATE` mientras espera?
2. El reporte de utilidad va a usar `costo_unitario`. Para las ventas viejas con NULL, ¿las tratarías como costo 0, las excluirías del reporte o usarías el `precio_costo` actual? ¿Qué le pasa al número que ve el dueño en cada opción?
3. Un compañero propone quitar el `UPDATE` condicional y dejar el `SELECT` de antes, pero con un `time.sleep` o un candado de Python (`threading.Lock`). ¿Qué le respondes? Piensa en cuántos workers de gunicorn corren en Render.

---

## 2026-11-16 · Login con usuarios y roles (admin y cajero)

**Qué se hizo:** la app ahora exige iniciar sesión. Hay dos roles: `admin` (todo) y `cajero` (vender, ver inventario, clientes y fiados). Las rutas de administración responden 403 al cajero. Plan completo, revisión del pez dorado, decisiones de Sergio y "Cambios respecto al plan": [docs/planes/2026-11-16-login-roles.md](planes/2026-11-16-login-roles.md).
**Por qué:** hasta ahora cualquiera con la URL veía costos, utilidades y deudas de clientes. Era el pendiente "Autenticación" de la entrada anterior.

**Decisiones:**
- **Negar por defecto.** Un solo `@app.before_request` (`exigir_login`, `app.py:~283`) protege todas las rutas, salvo las de `RUTAS_PUBLICAS` (`login` y `static`). Alternativa: decorar ruta por ruta con `@login_requerido`. Con decoradores, olvidar uno deja la ruta abierta sin que nada avise. Con la lista pública, olvidar algo lo deja cerrado, y el error se nota enseguida. Lo que se paga: hay que acordarse de agregar a la lista las rutas que de verdad deben ser públicas. Para lo que es solo de admin sí se usa `@solo_admin`, porque ahí hay que decidir ruta por ruta.
- **Contraseñas con hash y hash de relleno.** Se guarda `generate_password_hash(...)`, nunca la contraseña. Si el usuario no existe, el login igual compara contra `_HASH_RELLENO`. Así tarda lo mismo con usuario válido y con inválido, y nadie puede descubrir qué usuarios existen midiendo el tiempo de respuesta.
- **Cookie firmada.** La sesión de Flask va en una cookie firmada con `SECRET_KEY` (`app.py:~19`). Firmada no significa cifrada: el navegador puede leerla, pero no modificarla sin la clave. Por eso la app no arranca sin `SECRET_KEY`, en vez de usar una clave por defecto que todos conocerían.
- **Caché de 60 s por worker** (`_cache_usuarios`, `CACHE_USUARIO_SEG`). Evita una consulta a la BD en cada petición. Alternativas: consultar siempre (más simple y exacto, pero más lento y más carga), o guardar el rol en la cookie (sin consulta, pero un usuario desactivado seguiría entrando hasta que expire la cookie). Lo que se paga: desactivar a alguien puede tardar hasta 60 s en aplicarse en los otros workers. El worker donde se hace el cambio sí actualiza al instante, con `_cache_usuarios.pop`.
- **Prueba que recorre `url_map`** (`tests/test_permisos.py`). No prueba rutas a mano: recorre todas las que Flask conoce y comprueba que cada una exige sesión o está en la lista pública, y que las de admin devuelven 403 al cajero. Una ruta nueva queda cubierta sin tocar la prueba. Se comprobó con una **mutación**: se quitó un `@solo_admin` a propósito y la prueba falló. Una prueba que nunca ha fallado no demuestra que detecte algo.
- **401, 403 y 503.** 401 es "no sé quién eres" (sin sesión). 403 es "sé quién eres y no puedes". 503 es "la BD no responde", que no es culpa de las credenciales. Si se confundieran, un fallo de la BD sacaría a todos al login como si hubieran escrito mal la clave. Las descargas de `/api/reportes/` son navegación normal, no `fetch`, así que sin sesión se redirigen al login en vez de recibir JSON.
- **Decisión de negocio de Sergio:** el cajero ve el costo. En las tiendas de barrio el precio se negocia con los clientes conocidos y el cajero necesita saber el margen. Esa decisión generó un pendiente nuevo, "precio negociado en la venta" (ver `docs/PENDIENTES.md`).

**Cómo funciona:**
1. Una petición entra y `exigir_login` revisa el endpoint. Si es público, pasa.
2. Si no, `usuario_actual()` lee `session["uid"]`, mira la caché o consulta `usuarios`, y exige que `activo` sea verdadero.
3. Sin usuario: 401 en `/api/*` o redirección a `login`. Con la BD caída: 503.
4. Con usuario, queda en `g.usuario` y la ruta corre. Si lleva `@solo_admin` y el rol no es admin, 403.
5. `login` (`app.py:~330`) verifica el hash, guarda `uid` en la sesión y vacía la caché de ese usuario.
6. `init_db()` crea la tabla `usuarios` y el admin inicial desde variables de entorno (`.env.example`). El front (`static/app.js`, `templates/index.html`, `templates/login.html`) oculta lo de admin, pero la seguridad real está en el servidor.

**Revisor:** aprobado con cambios menores, ya corregidos:
- El aviso de 403 salía a la vez que el modal premium.
- Carrera de `init_db` entre workers, resuelta con `pg_advisory_xact_lock`.
- El byte NUL en el usuario daba 500.
- El log del admin inicial.

**Aceptado sin cambio:**
- Un cajero que entra a mano a la URL de un reporte ve un JSON 403.
- Dos admins que se desactivan entre sí al mismo tiempo.
- Un cambio de contraseña no cierra las sesiones abiertas (está en PENDIENTES).

**Conceptos nuevos:** `before_request` (función de Flask que corre antes de cada ruta), hash (huella de un solo sentido de la contraseña), sesión (datos del usuario que el servidor recuerda entre peticiones), cookie firmada (cookie con una firma que detecta alteraciones), worker (proceso de gunicorn; cada uno tiene su propia memoria), `g` (espacio de Flask que dura una sola petición), mutación (romper el código a propósito para ver si la prueba lo detecta), advisory lock (candado de PostgreSQL elegido por la aplicación, aquí para que un solo worker cree las tablas).

**Cómo comprobarlo:**
- Hecho: `python tests/test_permisos.py` da TODO OK con una BD falsa.
- **No probado:** con PostgreSQL real ni en navegador. Falta entrar como admin y como cajero, desactivar un usuario y ver cuánto tarda en perder el acceso, y arrancar con dos workers.

**Lección que se lleva a otros proyectos:** la seguridad debe fallar cerrada. Se define una regla global que niega todo y se abren excepciones explícitas. Se añade una prueba que recorre todas las rutas, para que el siguiente que agregue una no dependa de acordarse.

**Preguntas para Sergio:**
1. ¿Por qué negar por defecto es más seguro que decorar cada ruta? Responde con un caso concreto: un compañero agrega mañana `/api/exportar_clientes`.
2. Se despliega en Render sin definir `SECRET_KEY`. ¿Qué pasa al arrancar? ¿Y qué pasaría si la app, en vez de fallar, generara una clave aleatoria en cada arranque con varios workers?
3. El dueño desactiva a un cajero que está en medio de una venta. ¿Qué ve el cajero y cuándo? ¿Qué cambiarías si el negocio exigiera corte inmediato?
