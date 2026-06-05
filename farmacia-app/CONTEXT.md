# Gestor Farmacia - Contexto del Proyecto

> **Última actualización:** 2026-06-05 (sesión 5)
> **Estado:** deployado en Render. PostgreSQL. Premium = OFF.
> **Producción:** https://gestor-de-farmacia-1.onrender.com (plan free, cold start 30-60s)
> Para revisar cambios de la última sesión: `docs/INFORME_SESION.md`.

## Información General
- **Nombre**: FarmaSys - Gestor de Farmacia
- **Tipo**: Aplicación web Flask
- **Ubicación**: C:\Users\sergi\Desktop\Gestor farmacia\farmacia-app
- **Sesiones de cambios**: ver `docs/INFORME_SESION.md` después de cada sesión

## Stack Tecnológico
- **Backend**: Python + Flask + **PostgreSQL** + psycopg2 + Pandas + OpenPyXL
- **Frontend**: HTML + CSS vanilla + JavaScript vanilla
- **Sin frameworks** (ni React, ni Vue)
- **AI Assistants**: skills `clean-code` y `session-report` activas en `.agents/skills/`
  - `clean-code/SKILL.md` — guía por defecto para code review y arquitectura
  - `session-report/SKILL.md` — comportamiento pedagógico + formato del informe de sesión
  - `session-report/SKILL-generic.md` — versión genérica reutilizable en otros proyectos

## Estructura de Archivos
```
farmacia-app/
├── app.py                 # Backend Flask - rutas API + página principal
├── .env.example           # Plantilla de variables de entorno (DATABASE_URL)
├── requirements.txt       # Dependencias: flask, pandas, openpyxl, werkzeug, psycopg2-binary
├── CONTEXT.md             # Este archivo
├── docs/
│   └── INFORME_SESION.md  # Informe educativo de cada sesión
├── templates/
│   └── index.html         # Frontend principal
├── static/
│   ├── style.css          # Estilos CSS con dark mode (V2 redesign)
│   └── app.js             # Lógica JavaScript
└── .agents/
    └── skills/
        ├── clean-code/         # Software Crafter Experto
        ├── session-report/     # Comportamiento pedagógico + informe educativo
        │   ├── SKILL.md            # Específica de FarmaSys
        │   └── SKILL-generic.md    # Reutilizable en otros proyectos
        ├── accessibility/      # WCAG 2.2
        ├── flask-api-development/
        ├── frontend-design/
        ├── pandas-pro/
        ├── python-executor/
        ├── python-testing-patterns/
        ├── seo/
        └── ...
```

## Base de Datos (PostgreSQL)

### Tablas:
1. **inventario**: id, nombre, principio, laboratorio, cantidad, precio, fecha_vencimiento, lote, categoria, invima_id
2. **ventas**: id, inventario_id, nombre, laboratorio, cantidad, precio_unitario, total, fecha
3. **invima**: datos de productos INVIMA para autocompletar
4. **catalogo**: id, nombre, principio, laboratorio, descripcion

### Constantes (app.py):
- `STOCK_MINIMO = 10`
- `STOCK_CRITICO = 5`
- `DIAS_ALERTA_VENCIMIENTO = 30`
- `DATE_FMT = "%Y-%m-%d"`
- `FMT_FECHA_REPORTE = "%Y%m%d"`
- `PREMIUM_ENABLED = False` ← controla acceso al módulo analíticas
- `MARGEN_POR_CATEGORIA` ← diccionario de márgenes para analítica

## Rutas API

### Dashboard
| endpoint | método | descripción |
|----------|--------|-------------|
| `/api/dashboard` | GET | Stats (incluye `ventas_mes`) |
| `/api/dashboard/alertas` | GET | Bajo stock + próximos a vencer |
| `/api/dashboard/ventas-hoy` | GET | Total + transacciones de hoy |
| `/api/dashboard/ventas-semana` | GET | **Nuevo** — ventas por día, últimos 7 |
| `/api/dashboard/top-productos` | GET | **Nuevo** — top 5 más vendidos |

### Inventario
| endpoint | método | descripción |
|----------|--------|-------------|
| `/api/inventario` | GET/POST | Listar / agregar |
| `/api/inventario/<id>` | DELETE/PUT | Eliminar / actualizar |
| `/api/inventario/importar` | POST | Preview importación Excel |
| `/api/inventario/confirmar-importacion` | POST | Confirmar |
| `/api/inventario/recategorizar` | POST | Recategorizar sin categoría |

### Analíticas (PREMIUM — devuelve 403 si `PREMIUM_ENABLED = False`)
| endpoint | método | descripción |
|----------|--------|-------------|
| `/api/analytics/comparativa` | GET | Mes actual vs anterior + variación % |
| `/api/analytics/rotacion` | GET | Top 10 productos por ratio ventas/stock |
| `/api/analytics/rentabilidad` | GET | Categorías ordenadas por utilidad |
| `/api/analytics/margen` | GET | Margen bruto global estimado |
| `/api/analytics/proyeccion` | GET | Cierre de mes según promedio diario |

### Ventas / Reportes / INVIMA
| endpoint | método | descripción |
|----------|--------|-------------|
| `/api/ventas` | GET/POST | Listar / registrar |
| `/api/reportes/inventario` | GET | Excel de inventario |
| `/api/reportes/ventas` | GET | Excel de ventas (con filtros desde/hasta) |
| `/api/reportes/utilidad` | GET | Excel de utilidad |
| `/api/invima/buscar` | GET | Buscar en INVIMA |
| `/api/inferir-categoria` | GET | Infiere categoría según principio |
| `/api/categorias` | GET | Lista de categorías predefinidas |
| `/api/catalogo` | GET/POST | Catálogo propio |

## UI/UX (V2)

### Paleta:
- **Primario**: Coral `#e11d48`
- **Acento**: Teal `#0d9488`
- **Background**: Cream `#fafaf9`
- **Modo oscuro**: Rich dark `#0c0a09`

### Páginas:
- **Dashboard** — 4 stat cards + gráfica semanal + cards de alertas/ventas-hoy/top-productos
- **Inventario** — tabla con filtros + importar Excel + INVIMA autocomplete
- **Ventas** — formulario + historial
- **Reportes** — 3 tipos de exportación Excel
- **Analíticas (Premium)** — 5 cards de análisis. Si `PREMIUM_ENABLED = False` muestra CTA de upgrade

### Sidebar:
- Principal: Dashboard / Inventario / Ventas
- Reportes: Exportar reportes
- Premium: Analíticas (con badge PRO)

### Categorías de Productos (8):
Analgésicos / Antibióticos / Antialérgicos / Antidiabéticos / Gastrointestinal / Dermatológicos / Suplementos / Otros

### Inferencia de Categoría:
- `CATEGORIAS_KEYWORDS` mapea palabras clave del principio activo a categorías
- Se aplica al agregar o importar productos

### JavaScript — funciones principales:
- **Navegación**: `navigate(page)` (SPA)
- **Dashboard**: `cargarDashboard()`, `cargarCentroAlertas()`, `cargarVentasHoy()`, `cargarGraficaSemana()`, `cargarTopProductos()`
- **Inventario**: `cargarInventario()`, `renderInventario()`, `eliminarInventario()`, `editarInventario()`
- **Ventas**: `cargarVentas()`, `seleccionarVenta()`
- **Analíticas**: `cargarAnaliticas()` (dispatch) + 5 loaders individuales
- **Modal premium**: `mostrarModalPremium()` / `cerrarModalPremium()`
- **Seguridad**: `escapeHtml()` + `escapeJs()` (XSS-safe)
- **HTTP**: `fetchJSON()` wrapper centralizado

## Decisiones de Diseño Actuales

1. **`PREMIUM_ENABLED = False`** — el módulo analíticas existe pero está bloqueado. Para activarlo: cambiar el flag en `app.py` y reiniciar.
2. **5 endpoints de analítica** (no 4) — uno por análisis, SRP.
3. **Gráfica con CSS puro** — sin librerías JS externas.
4. **Catálogo hardcoded de INVIMA** — 158 productos comunes sembrados en `init_db()`.
5. **No hay tests automatizados** — verificado manualmente con Flask test client.
6. **No hay sistema de autenticación** — single user, local-only.
7. **PostgreSQL como única BD** (sesión 4) — sin fallback a SQLite. Conexión vía `DATABASE_URL`. `psycopg2` con `RealDictCursor`.

## Cómo Ejecutar

```bash
cd "C:\Users\sergi\Desktop\Gestor farmacia\farmacia-app"
pip install -r requirements.txt
set DATABASE_URL=postgresql://usuario:clave@localhost:5432/farmacia
python app.py
```

Luego abrir: http://127.0.0.1:5000

## Errores Comunes

1. **`ModuleNotFoundError: No module named 'flask'`** → `pip install -r requirements.txt`
2. **`RuntimeError: DATABASE_URL no está configurada`** → definir la variable de entorno (ver `.env.example`).
3. **`psycopg2.OperationalError: connection to server failed`** → PostgreSQL no está corriendo, o la URL es incorrecta.
4. **`UndefinedColumn: column ... does not exist`** → la BD tiene un schema viejo; borrar la BD y dejar que `init_db()` la recree.

## Próximos Pasos / Ideas (no implementadas)

- [ ] Integrar pasarela de pago real (Wompi / Mercado Pago) para activar Premium
- [ ] Agregar exportación de analíticas a PDF
- [ ] Tests automatizados (pytest + Flask test client)
- [ ] Gráficas más elaboradas (Chart.js) si el volumen de datos crece
- [ ] Sistema de autenticación multi-usuario
- [ ] Caché de consultas de analítica (Redis o en memoria)
- [x] Deploy a Render (web service + PostgreSQL free tier) — hecho en sesión 5

## Notas

- Solo trabajar dentro de `C:\Users\sergi\Desktop\Gestor farmacia\farmacia-app`
- Skill `clean-code` es la guía por defecto para code review
- Cada sesión debe terminar con un informe en `docs/INFORME_SESION.md`
- El usuario es **principiante en programación** — preferir explicaciones educativas sobre tecnicismos
- Dark mode se guarda en `localStorage`
