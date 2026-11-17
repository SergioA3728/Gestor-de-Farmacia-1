# Pendientes de FarmaSys

Problemas menores detectados en el mapeo del 2026-11-16. Los 5 principales están en `BITACORA.md`.
**Comprobado:** se vio en el código. **Por confirmar:** se dedujo, no se reprodujo.

## Errores
- [ ] Reporte de inventario con índices de columna equivocados: el color de alerta nunca se aplica, y hay formatos de fecha y moneda en columnas que no corresponden. `app.py:656-700`. *Comprobado.*
- [ ] Importar Excel: `row.get(...) or ...` no sirve con `NaN` (que es "verdadero"), y `jsonify` puede emitir `NaN` inválido. `app.py:529-530`. *Por confirmar* con un Excel real.
- [ ] Confirmar la importación cruza los productos por `nombre`, mientras que el alta manual los cruza por ID: puede duplicar o actualizar el producto equivocado. `app.py:562-566`. *Comprobado.*
- [ ] Zona horaria: `datetime.now()` (UTC en Render) frente a `CURRENT_DATE`. Las ventas después de las 7 p. m. pueden contar al día siguiente. `app.py:1017`, `904`, `927`. *Por confirmar.*
- [ ] `request.json` puede ser `None`, y un `monto` en texto rompe la comparación. `app.py:385`, `410`, `1046`. *Comprobado.* (Resuelto en la venta el 2026-11-16; siguen pendientes las demás rutas.)
- [x] `es_credito` llega del cliente sin validar. Resuelto en la venta (`registrar_venta`) el 2026-11-16; sigue pendiente en las otras rutas si lo reciben. *Comprobado.*
- [ ] Abonos con la misma condición de carrera que tenía la venta. `app.py:~1060`. *Comprobado.*
- [ ] El reporte de utilidad no usa `costo_unitario`; al usarlo, tratar NULL con `COALESCE`. `app.py:~855`. *Comprobado.*

## Seguridad
- [ ] `escapeJs` solo escapa comillas y se usa dentro de `onclick`. `app.js:17-19`, `58`. *Comprobado.*

## Diseño y mantenimiento
- [ ] Umbrales 5 y 10 escritos a mano en vez de usar `STOCK_CRITICO` y `STOCK_MINIMO`. `app.py:628`, `709-710`. *Comprobado.*
- [ ] Diccionario de categorías duplicado y distinto en dos archivos. `app.py:196-333` y `scripts/poblar_categoria_invima.py:13-105`. *Comprobado.*
- [ ] El dashboard llama a `POST /api/inventario/recategorizar` en cada carga. `app.js:190`. *Comprobado.*
- [ ] Una consulta `ILIKE` por cada fila del Excel. `app.py:510-525`. *Comprobado.*
- [ ] Las fechas se guardan como `TEXT`. `app.py:100`, `113`. *Comprobado.*
- [ ] `init_db()` corre al importar el módulo: la app no arranca sin `DATABASE_URL`. `app.py:1251`. *Comprobado.*
- [ ] Comentario falso sobre la siembra de 158 productos. `app.py:1237-1250`. *Comprobado.*
- [ ] `requirements.txt` sin versiones fijas. *Comprobado.*
- [ ] No hay tests. *Comprobado.*
- [ ] `canonical` de ejemplo (`tu-dominio.com`). `templates/index.html:8`. *Comprobado.*
- [ ] `.gitignore`: `#farmacia.db` es un comentario y no excluye nada; faltan `.env.*` y `*.log`. *Comprobado.*
- [ ] `CONTEXT.md` desactualizado: dice "local-only" y la app está publicada. *Comprobado.*

## Login y roles (de docs/planes/2026-11-16-login-roles.md)
- [ ] **PRIORIDAD ALTA — Límite de intentos de login.** Sin él se pueden probar contraseñas sin parar contra `/login`. La app ya es pública en Render; hacerlo antes de cualquier uso con datos reales.
- [ ] Recuperar contraseña y que cada usuario cambie la suya (hoy solo el admin la reinicia).
- [ ] Reiniciar la contraseña o desactivar a alguien no cierra una sesión ya abierta en otro worker hasta 60 s después (caché) — y reiniciar la contraseña no invalida la cookie vigente hasta 12 h. Solución: guardar una "versión de sesión" en `usuarios` y compararla.
- [ ] Auditoría de abonos y de cambios de inventario por usuario (hoy solo la venta guarda `vendedor`).
- [ ] Tokens CSRF (hoy protege `SameSite=Lax`).
- [ ] **Precio negociado en la venta:** el cajero ve el costo como referencia, pero `registrar_venta()` siempre cobra `inventario.precio`. Siguiente cambio a planear.
