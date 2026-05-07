# Gestor Farmacia - Contexto del Proyecto

## Información General
- **Nombre**: FarmaVida - Gestor de Farmacia
- **Tipo**: Aplicación web Flask
- **Ubicación**: C:\Users\sergi\Desktop\Gestor farmacia\farmacia-app

## Stack Tecnológico
- **Backend**: Python + Flask + SQLite + Pandas + OpenPyXL
- **Frontend**: HTML + CSS vanilla + JavaScript vanilla
- **Sin frameworks** (ni React, ni Vue)

## Estructura de Archivos
```
farmacia-app/
├── app.py              # Backend Flask - rutas API + página principal
├── farmacia.db        # Base de datos SQLite
├── templates/
│   └── index.html    # Frontend principal
└── static/
    ├── style.css    # Estilos CSS con dark mode (V2 redesign)
    └── app.js      # Lógica JavaScript
```

## Base de Datos (SQLite)

### Tablas:
1. **inventario**: id, nombre, principio, laboratorio, cantidad, precio, fecha_vencimiento, lote, categoria, invima_id
2. **ventas**: id, inventario_id, nombre, laboratorio, cantidad, precio_unitario, total, fecha
3. **invima**: datos de productos INVIMA para autocompletar

### Constantes:
- STOCK_MINIMO = 10

## Rutas API

| endpoint | método | descripción |
|----------|--------|-------------|
| `/api/dashboard` | GET | Stats: total productos, bajo stock, próximos a vencer |
| `/api/dashboard/alertas` | GET | Lista productos bajo stock + próximos a vencer (30 días) |
| `/api/dashboard/ventas-hoy` | GET | Total vendido hoy + número de transacciones |
| `/api/inventario` | GET/POST | Listar / agregar productos |
| `/api/inventario/<id>` | DELETE | Eliminar producto |
| `/api/inventario/<id>` | PUT | Actualizar producto |
| `/api/ventas` | GET/POST | Listar / registrar ventas |
| `/api/invima/buscar` | GET | Buscar productos en INVIMA |
| `/api/inferir-categoria` | GET | Infiere categoría según principio activo |
| `/api/categorias` | GET | Lista de categorías predefinidas |
| `/api/reportes/inventario` | GET | Exporta Excel de inventario |
| `/api/reportes/ventas` | GET | Exporta Excel de ventas |
| `/api/inventario/importar` | POST | Preview importación Excel |
| `/api/inventario/confirmar-importacion` | POST | Confirma importación |

## UI/UX (V2 - Nuevo Diseño)

### Paleta de Colores:
- **Primario**: Coral (#e11d48)
- **Acento**: Teal (#0d9488)
- **Background**: Cream (#fafaf9) con patrón de puntos sutil
- **Modo oscuro**: Rich dark (#0c0a09)

### Dashboard:
- Saludo dinámico según hora (Buenos días/tardes/noches)
- Fecha como badge
- Quick actions: Nueva venta, Agregar producto, Exportar reporte
- Stats cards con barras de color (green/yellow/red)
- Centro de alertas con items clickeables
- Ventas de hoy con diseño mejorado

### Categorías de Productos (8):
1. Analgésicos / Antiinflamatorios
2. Antibióticos
3. Antialérgicos
4. Antidiabéticos / Antihipertensivos
5. Gastrointestinal
6. Dermatológicos
7. Suplementos / Vitaminas
8. Otros

### Inferencia de Categoría:
- Keywords en `CATEGORIAS_KEYWORDS` mapean palabras clave del principio activo a categorías
- Se aplica automáticamente al agregar o importar productos

### Presentación de Productos:
- Campo cantidad directa al editar (inv-cantidad-directa)
- Grupo presentación (presentación + unidades por presentación) al crear nuevo
- Total calculado en tiempo real

### Reportes Excel:
- Encabezados con fondo azul (#4472C4), texto blanco, negrita
- Columnas renombradas a español
- Formato por tipo: moneda COP, fechas DD/MM/YYYY
- Filas alternas en gris claro
- Color condicional en alertas: CRÍTICO (rojo), BAJO (amarillo), OK (verde)
- Totales al final

### JavaScript:
- Navegación SPA: `navigate(page)`
- Dark mode: `toggleModoOscuro()`, `initModoOscuro()`
- Dashboard: `cargarDashboard()`, `cargarCentroAlertas()`, `cargarVentasHoy()`, saludo dinámico
- INVIMA: `buscarInvimaModal()`, `seleccionarInvima()`, fetch a `/api/inferir-categoria`
- Inventario: `cargarInventario()`, `renderInventario()`, `eliminarInventario()`, `editarInventario()`
- Presentación: `actualizarTotalCalculado()`
- Ventas: `cargarVentas()`, `seleccionarVenta()`

### Known Issues / Pendientes:
- Revisar consistencia de todos los estilos CSS
- Verificar que las stat cards de alerta navegan correctamente al inventario con filtro
- Revisar que el modal de importar funciona correctamente
- Testing general de todos los flujos

## Cómo Ejecutar

```bash
cd "C:\Users\sergi\Desktop\Gestor farmacia\farmacia-app"
pip install flask pandas openpyxl
python app.py
```

Luego abrir en el navegador: http://127.0.0.1:5000

## Errores Comunes y Soluciones

1. **ModuleNotFoundError: No module named 'flask'**
   - Solución: `pip install flask pandas openpyxl`

2. **sqlite3.OperationalError: no such table: inventario**
   - Solución: Eliminar `farmacia.db` y reiniciar para recrear tablas con `init_db()`

## Notas

- IMPORTANTE: Solo trabajar dentro de `C:\Users\sergi\Desktop\Gestor farmacia\farmacia-app`
- NUNCA crear carpetas externas como "Gestor biblioteca" u otras
- El proyecto usa JavaScript vanilla (sin frameworks)
- No hay sistema de autenticación
- Los datos de INVIMA deben existir en la base de datos
- Dark mode se guarda en localStorage del navegador
- Nuevo diseño V2 con estética premium cálida