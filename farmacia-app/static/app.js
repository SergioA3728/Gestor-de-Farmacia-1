const $ = id => document.getElementById(id);

function formatCOP(valor) {
    return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", minimumFractionDigits: 0 }).format(valor);
}

function esc(str) {
    return (str || "").replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

// ── INVIMA ─────────────────────────────────────────────
let invimaSel = null;
let editandoId = null;

async function cargarCategorias() {
    const res = await fetch("/api/categorias");
    const cats = await res.json();
    const sel = $("inv-categoria");
    sel.innerHTML = '<option value="">Seleccionar...</option>';
    cats.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c;
        opt.textContent = c;
        sel.appendChild(opt);
    });
}

async function buscarInvimaModal() {
    const q = $("inv-buscar-invima").value.trim();
    if (q.length < 2) {
        $("invima-sugerencias").innerHTML = "";
        return;
    }
    const res = await fetch(`/api/invima/buscar?q=${encodeURIComponent(q)}`);
    const datos = await res.json();
    renderInvimaModal(datos);
}

function renderInvimaModal(datos) {
    const cont = $("invima-sugerencias");
    if (!datos.length) {
        cont.innerHTML = "<div class='sugerencia-item'>Sin resultados</div>";
        cont.style.display = "block";
        return;
    }
    cont.style.display = "block";
    cont.innerHTML = datos.map(d => `
        <div class="sugerencia-item" onclick="seleccionarInvima(${d.id}, '${esc(d.producto)}', '${esc(d.principio_activo)}', '${esc(d.titular)}', '${esc(d.registro)}')">
            <div class="nombre">${d.producto}</div>
            <div class="detalle">${d.principio_activo} · ${d.titular}</div>
        </div>
    `).join("");
}

function seleccionarInvima(id, nombre, principio, laboratorio, registro) {
    invimaSel = { invima_id: id };
    $("inv-nombre").value = nombre;
    $("inv-principio").value = principio;
    $("inv-laboratorio").value = laboratorio;
    
    $("inv-principio").setAttribute("readonly", true);
    $("inv-laboratorio").setAttribute("readonly", true);
    $("inv-principio").classList.add("field-locked");
    $("inv-laboratorio").classList.add("field-locked");
    
    $("invima-sugerencias").style.display = "none";
    $("inv-buscar-invima").value = "";
    
    fetch(`/api/inferir-categoria?principio=${encodeURIComponent(principio)}`)
        .then(r => r.json())
        .then(data => {
            if (data.categoria) {
                $("inv-categoria").value = data.categoria;
            }
        });
}

$("inv-buscar-invima")?.addEventListener("input", () => {
    clearTimeout(window.invimaTimer);
    window.invimaTimer = setTimeout(buscarInvimaModal, 300);
});

document.addEventListener("mousedown", e => {
    if (!e.target.closest("#inv-buscar-invima") && !e.target.closest("#invima-sugerencias")) {
        $("invima-sugerencias").style.display = "none";
    }
});

// ── PRESENTACIÓN ─────────────────────────────────────────────
function actualizarTotalCalculado() {
    const cantidad = parseInt($("inv-cantidad").value) || 0;
    const porUnidad = parseInt($("inv-por-unidad").value) || 1;
    const total = cantidad * porUnidad;
    $("total-calculado").textContent = total > 0 ? `→ Total: ${total} unidades` : "";
}

$("inv-presentacion")?.addEventListener("change", () => {
    const defaults = { cajas: 30, sobres: 10, "media caja": 15, unidades: 1 };
    const pres = $("inv-presentacion")?.value;
    if (pres && pres !== "unidades") {
        $("inv-por-unidad").value = defaults[pres] || 10;
    } else {
        $("inv-por-unidad").value = 1;
    }
    actualizarTotalCalculado();
});

$("inv-cantidad")?.addEventListener("input", actualizarTotalCalculado);
$("inv-por-unidad")?.addEventListener("input", actualizarTotalCalculado);

// ── NAVEGACIÓN ───────────────────────────────────────────────
function navigate(page) {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => {
        n.classList.remove("active");
        n.setAttribute("aria-selected", "false");
    });
    
    $(`page-${page}`).classList.add("active");
    const navBtn = $(`nav-${page}`) || document.querySelector(`.nav-item[data-page="${page}"]`);
    if (navBtn) {
        navBtn.classList.add("active");
        navBtn.setAttribute("aria-selected", "true");
    }
    
    if (page === "dashboard") cargarDashboard();
    if (page === "inventario") cargarInventario();
    if (page === "ventas") { cargarInventarioVentas(); cargarVentas(); }
}

document.querySelectorAll(".nav-item").forEach(btn => {
    btn.addEventListener("click", () => navigate(btn.dataset.page));
});

document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        filtroActual = btn.dataset.filter;
        renderInventario(aplicarFiltro(inventarioCache));
    });
});

// ── MODO OSCURO ─────────────────────────────────────────────
function toggleModoOscuro() {
    const html = document.documentElement;
    const isDark = html.classList.toggle("dark");
    localStorage.setItem("darkMode", isDark);
    const toggle = $("dark-toggle");
    if (toggle) toggle.setAttribute("aria-checked", isDark);
}

function initModoOscuro() {
    const saved = localStorage.getItem("darkMode") === "true";
    if (saved) {
        document.documentElement.classList.add("dark");
        const toggle = $("dark-toggle");
        if (toggle) toggle.setAttribute("aria-checked", "true");
    }
}

$("dark-toggle")?.addEventListener("click", toggleModoOscuro);
$("dark-toggle")?.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleModoOscuro();
    }
});

// ── DASHBOARD ─────────────────────────────────────────────
async function cargarDashboard() {
    await fetch("/api/inventario/recategorizar", { method: "POST" });
    
    const res = await fetch("/api/dashboard");
    const data = await res.json();
    
    $("stat-total").textContent = data.total_productos || 0;
    $("stat-bajo-stock").textContent = data.bajo_stock || 0;
    $("stat-vencer").textContent = data.prox_vencer || 0;
    $("stat-ventas-mes").textContent = formatCOP(data.ventas_mes || 0);
    
    const hora = new Date().getHours();
    const saludo = hora < 12 ? "Buenos días" : hora < 18 ? "Buenas tardes" : "Buenas noches";
    $("dash-saludo").textContent = saludo + ", Administrador";
    
    const fecha = new Date();
    const opciones = { weekday: "long", year: "numeric", month: "long", day: "numeric" };
    $("current-date").textContent = fecha.toLocaleDateString("es-CO", opciones);
    
    cargarCentroAlertas();
    cargarVentasHoy();
    cargarGraficaSemana();
    cargarTopProductos();
}

async function cargarCentroAlertas() {
    const res = await fetch("/api/dashboard/alertas");
    const data = await res.json();
    const cont = $("alertas-container");
    
    const bajoStock = data.bajo_stock || [];
    const proxVencer = data.proximos_vencer || [];
    const todas = [
        ...bajoStock.map(d => ({...d, tipo: "stock"})),
        ...proxVencer.map(d => ({...d, tipo: "vencer"}))
    ];
    
    if (todas.length === 0) {
        cont.innerHTML = `<div class="empty-state"><p>No hay alertas pendientes</p></div>`;
        return;
    }
    
    cont.innerHTML = todas.slice(0, 8).map(d => {
        if (d.tipo === "stock") {
            const nivel = d.nivel === "critico" ? "danger" : "warning";
            const label = d.nivel === "critico" ? "Crítico" : "Bajo";
            return `<div class="alert-item"><span class="alert-badge ${nivel}">${label}</span><div class="alert-info"><div class="alert-name">${d.nombre}</div><div class="alert-detail">Stock: ${d.cantidad}</div></div></div>`;
        } else {
            return `<div class="alert-item"><span class="alert-badge danger">Vence</span><div class="alert-info"><div class="alert-name">${d.nombre}</div><div class="alert-detail">${d.fecha_vencimiento}</div></div></div>`;
        }
    }).join("");
}

async function cargarVentasHoy() {
    const res = await fetch("/api/dashboard/ventas-hoy");
    const data = await res.json();
    const cont = $("ventas-hoy-container");
    
    if (!data.transacciones || data.transacciones === 0) {
        cont.innerHTML = `<div class="empty-state"><p>No hay ventas hoy</p></div>`;
        return;
    }
    
    cont.innerHTML = `<div style="text-align:center;padding:16px 0"><div style="font-size:2rem;font-weight:700;color:var(--success)">${formatCOP(data.total)}</div><div style="font-size:13px;color:var(--text-secondary)">${data.transacciones} transacciones</div></div>`;
}

async function cargarGraficaSemana() {
    const cont = $("dashboard-chart");
    if (!cont) return;
    
    try {
        const res = await fetch("/api/dashboard/ventas-semana");
        const datos = await res.json();
        
        if (!datos || datos.length === 0) {
            cont.innerHTML = `<div class="empty-state"><p>Sin datos de ventas</p></div>`;
            return;
        }
        
        const maxValor = Math.max(...datos.map(d => d.total), 1);
        const diasCortos = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
        
        const formatearCorto = (n) => {
            if (n >= 1_000_000) return "$" + (n / 1_000_000).toFixed(1) + "M";
            if (n >= 1_000) return "$" + (n / 1_000).toFixed(0) + "K";
            return "$" + n.toFixed(0);
        };
        
        const formatearLabel = (fechaStr) => {
            const f = new Date(fechaStr + "T00:00:00");
            return diasCortos[f.getDay()];
        };
        
        cont.innerHTML = datos.map(d => {
            const alturaPct = maxValor > 0 ? (d.total / maxValor) * 100 : 0;
            const esCero = d.total === 0;
            return `
                <div class="chart-bar-wrapper">
                    <div class="chart-bar">
                        <div class="chart-bar-fill ${esCero ? "zero" : ""}" 
                             data-value="${formatearCorto(d.total)}"
                             style="height: ${Math.max(alturaPct, 2)}%"></div>
                    </div>
                    <div class="chart-label">${formatearLabel(d.fecha)}</div>
                </div>
            `;
        }).join("");
    } catch (err) {
        cont.innerHTML = `<div class="empty-state"><p>Error al cargar gráfica</p></div>`;
    }
}

async function cargarTopProductos() {
    const cont = $("top-productos-container");
    if (!cont) return;
    
    try {
        const res = await fetch("/api/dashboard/top-productos");
        const datos = await res.json();
        
        if (!datos || datos.length === 0) {
            cont.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                    <p>Sin ventas registradas</p>
                </div>`;
            return;
        }
        
        const rankClass = ["gold", "silver", "bronze", "", ""];
        
        cont.innerHTML = datos.map((d, i) => `
            <div class="top-producto-item">
                <div class="top-producto-rank ${rankClass[i]}">${i + 1}</div>
                <div class="top-producto-info">
                    <div class="top-producto-nombre" title="${esc(d.nombre)}">${d.nombre}</div>
                    <div class="top-producto-cantidad">${d.vendidos} unidades vendidas</div>
                </div>
            </div>
        `).join("");
    } catch (err) {
        cont.innerHTML = `
            <div class="empty-state">
                <p>Error al cargar</p>
            </div>`;
    }
}

// ── INVENTARIO ───────────────────────────────────────────────
let inventarioCache = [];
let filtroActual = "todos";

function aplicarFiltro(datos) {
    let filtrados = datos;
    
    if (filtroActual === "bajo-stock") {
        filtrados = datos.filter(d => d.cantidad <= 10);
    } else if (filtroActual === "prox-vencer") {
        const thirtyDays = new Date();
        thirtyDays.setDate(thirtyDays.getDate() + 30);
        filtrados = datos.filter(d => d.fecha_vencimiento && d.fecha_vencimiento <= thirtyDays.toISOString().split("T")[0]);
    }
    
    const q = $("inv-buscar")?.value.toLowerCase() || "";
    if (q) {
        filtrados = filtrados.filter(d =>
            (d.nombre || "").toLowerCase().includes(q) ||
            (d.laboratorio || "").toLowerCase().includes(q) ||
            (d.categoria || "").toLowerCase().includes(q)
        );
    }
    return filtrados;
}

async function cargarInventario() {
    const res = await fetch("/api/inventario");
    inventarioCache = await res.json();
    renderInventario(aplicarFiltro(inventarioCache));
}

function renderInventario(datos) {
    const cont = $("inventario-tabla");
    
    if (!datos || datos.length === 0) {
        cont.innerHTML = `
            <tr>
                <td colspan="8" style="text-align:center;padding:32px;color:var(--text-secondary)">
                    No hay productos en inventario
                </td>
            </tr>`;
        return;
    }
    
    const getStockClass = (cant) => {
        if (cant <= 5) return "critical";
        if (cant <= 10) return "low";
        return "ok";
    };
    
    const getStockText = (cant) => {
        if (cant <= 5) return "Crítico";
        if (cant <= 10) return "Bajo";
        return "OK";
    };
    
    const formatDate = (date) => {
        if (!date) return "-";
        try {
            return new Date(date).toLocaleDateString("es-CO");
        } catch { return date; }
    };
    
    cont.innerHTML = datos.map(d => `
        <tr>
            <td>
                <div style="font-weight:600">${d.nombre}</div>
                <div style="font-size:12px;color:var(--text-secondary)">${d.principio || ""}</div>
            </td>
            <td>${d.laboratorio || "-"}</td>
            <td>${d.categoria || "-"}</td>
            <td style="font-weight:600; color:${d.cantidad <= 5 ? 'var(--danger)' : d.cantidad <= 10 ? 'var(--warning)' : 'var(--text)'}">${d.cantidad}</td>
            <td class="precio">${formatCOP(d.precio)}</td>
            <td>${formatDate(d.fecha_vencimiento)}</td>
            <td>${d.lote || "-"}</td>
            <td>
                <button class="btn btn-icon" onclick="editarInventario(${d.id})" aria-label="Editar ${esc(d.nombre)}" title="Editar">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button class="btn btn-icon" onclick="eliminarInventario(${d.id})" aria-label="Eliminar ${esc(d.nombre)}" title="Eliminar">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                </button>
            </td>
        </tr>
    `).join("");
}

$("inv-buscar")?.addEventListener("input", () => {
    renderInventario(aplicarFiltro(inventarioCache));
});

async function eliminarInventario(id) {
    if (!confirm("Eliminar este producto del inventario?")) return;
    await fetch(`/api/inventario/${id}`, { method: "DELETE" });
    cargarInventario();
    cargarDashboard();
}

async function editarInventario(id) {
    const producto = inventarioCache.find(p => p.id === id);
    if (!producto) return;
    
    editandoId = id;
    $("modal-title").textContent = "Editar producto";
    await cargarCategorias();
    
    $("inv-nombre").value = producto.nombre || "";
    $("inv-principio").value = producto.principio || "";
    $("inv-laboratorio").value = producto.laboratorio || "";
    $("inv-cantidad").value = producto.cantidad || 1;
    $("inv-precio").value = producto.precio || 0;
    $("inv-fecha-vencimiento").value = producto.fecha_vencimiento || "";
    $("inv-lote").value = producto.lote || "";
    $("inv-categoria").value = producto.categoria || "";
    
    $("inv-presentacion").value = "unidades";
    $("inv-por-unidad").value = 1;
    $("inv-cantidad-directa").value = producto.cantidad || 1;
    
    $("grupo-presentacion").style.display = "none";
    $("grupo-cantidad-directa").style.display = "block";
    
    if (producto.invima_id) {
        $("inv-principio").setAttribute("readonly", true);
        $("inv-laboratorio").setAttribute("readonly", true);
        $("inv-principio").classList.add("field-locked");
        $("inv-laboratorio").classList.add("field-locked");
    } else {
        $("inv-principio").removeAttribute("readonly");
        $("inv-laboratorio").removeAttribute("readonly");
        $("inv-principio").classList.remove("field-locked");
        $("inv-laboratorio").classList.remove("field-locked");
    }
    
    $("modal-agregar").style.display = "flex";
}

// ── MODAL AGREGAR ─────────────────────────────────────────
$("btn-agregar-producto")?.addEventListener("click", () => {
    editandoId = null;
    $("modal-title").textContent = "Agregar producto";
    cargarCategorias();
    $("modal-agregar").style.display = "flex";
    $("inv-nombre").focus();
    actualizarTotalCalculado();
});

$("modal-agregar")?.querySelector(".modal-close")?.addEventListener("click", () => {
    $("modal-agregar").style.display = "none";
    limpiarFormulario();
});

$("modal-agregar")?.querySelector(".modal-overlay")?.addEventListener("click", () => {
    $("modal-agregar").style.display = "none";
    limpiarFormulario();
});

function limpiarFormulario() {
    invimaSel = null;
    $("inv-buscar-invima").value = "";
    $("invima-sugerencias").style.display = "none";
    $("inv-nombre").value = "";
    $("inv-principio").value = "";
    $("inv-laboratorio").value = "";
    $("inv-cantidad").value = 1;
    $("inv-precio").value = 0;
    $("inv-fecha-vencimiento").value = "";
    $("inv-lote").value = "";
    $("inv-categoria").value = "";
    
    $("inv-principio").removeAttribute("readonly");
    $("inv-laboratorio").removeAttribute("readonly");
    $("inv-principio").classList.remove("field-locked");
    $("inv-laboratorio").classList.remove("field-locked");
    
    $("grupo-presentacion").style.display = "block";
    $("grupo-cantidad-directa").style.display = "none";
    $("inv-cantidad-directa").value = 1;
    $("total-calculado").textContent = "";
}

$("inv-limpiar")?.addEventListener("click", limpiarFormulario);

let invPrincipioTimeout;
$("inv-principio")?.addEventListener("input", () => {
    clearTimeout(invPrincipioTimeout);
    invPrincipioTimeout = setTimeout(async () => {
        const principio = $("inv-principio").value.trim();
        if (!principio) return;
        
        const res = await fetch(`/api/inferir-categoria?principio=${encodeURIComponent(principio)}`);
        const data = await res.json();
        
        if (data.categoria) {
            $("inv-categoria").value = data.categoria;
        }
    }, 400);
});

$("inv-guardar")?.addEventListener("click", async () => {
    const nombre = $("inv-nombre").value.trim();
    const cantidad = parseInt($("inv-cantidad").value);
    const precio = parseFloat($("inv-precio").value);
    const presentacion = $("inv-presentacion").value;
    const porUnidad = parseInt($("inv-por-unidad").value) || 1;
    
    const cantidadReal = editandoId 
        ? parseInt($("inv-cantidad-directa").value) || 1
        : (presentacion === "unidades" ? cantidad : cantidad * porUnidad);
    
    if (!nombre) { alert("El nombre es obligatorio."); return; }
    if (!cantidadReal || cantidadReal < 1) { alert("La cantidad debe ser mayor a 0."); return; }
    if (isNaN(precio) || precio < 0) { alert("El precio no es válido."); return; }
    
    const body = {
        ...(invimaSel || {}),
        nombre,
        principio: $("inv-principio").value.trim(),
        laboratorio: $("inv-laboratorio").value.trim(),
        cantidad: cantidadReal,
        precio,
        fecha_vencimiento: $("inv-fecha-vencimiento").value,
        lote: $("inv-lote").value.trim(),
        categoria: $("inv-categoria").value
    };
    
    let res, data;
    if (editandoId) {
        res = await fetch(`/api/inventario/${editandoId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        data = await res.json();
    } else {
        res = await fetch("/api/inventario", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        data = await res.json();
    }
    
    if (data.ok) {
        $("modal-agregar").style.display = "none";
        editandoId = null;
        $("modal-title").textContent = "Agregar producto";
        limpiarFormulario();
        cargarInventario();
        cargarDashboard();
    } else {
        alert("Error al guardar.");
    }
});

// ── VENTAS ─────────────────────────────────────────────
let ventaSel = null;

async function cargarInventarioVentas() {
    const res = await fetch("/api/inventario");
    inventarioCache = await res.json();
}

$("venta-buscar")?.addEventListener("input", async () => {
    const q = $("venta-buscar").value.trim().toLowerCase();
    const cont = $("venta-sugerencias");
    if (q.length < 1) { cont.style.display = "none"; return; }
    
    if (inventarioCache.length === 0) { await cargarInventarioVentas(); }
    
    const filtrados = inventarioCache.filter(d => d.cantidad > 0 && (
        d.nombre.toLowerCase().includes(q) ||
        (d.laboratorio || "").toLowerCase().includes(q) ||
        (d.principio || "").toLowerCase().includes(q)
    ));
    
    if (!filtrados.length) { cont.style.display = "none"; return; }
    
    cont.style.display = "block";
    cont.innerHTML = filtrados.slice(0, 10).map(d => `
        <div class="suggestion-item" onclick="seleccionarVenta(${d.id})" role="option">
            <div style="font-weight:600">${d.nombre}</div>
            <div style="font-size:12px;color:var(--text-secondary)">${d.laboratorio || ""} · Stock: ${d.cantidad}</div>
        </div>
    `).join("");
});

function seleccionarVenta(id) {
    ventaSel = inventarioCache.find(d => d.id === id);
    if (!ventaSel) return;
    
    $("venta-nombre").value = ventaSel.nombre;
    $("venta-laboratorio").value = ventaSel.laboratorio || "-";
    $("venta-stock").value = ventaSel.cantidad;
    $("venta-precio").value = formatCOP(ventaSel.precio);
    $("venta-cantidad").value = 1;
    $("venta-cantidad").max = ventaSel.cantidad;
    $("venta-detalle").style.display = "grid";
    $("venta-detalle").setAttribute("aria-hidden", "false");
    $("venta-sugerencias").style.display = "none";
    $("venta-buscar").value = "";
}

$("venta-guardar")?.addEventListener("click", async () => {
    if (!ventaSel) return;
    const cantidad = parseInt($("venta-cantidad").value);
    
    const res = await fetch("/api/ventas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ inventario_id: ventaSel.id, cantidad })
    });
    const data = await res.json();
    
    if (data.ok) {
        msg("venta-msg", `Venta registrada. Total: ${formatCOP(data.total)}`, "ok");
        setTimeout(() => {
            ventaSel = null;
            $("venta-detalle").style.display = "none";
            $("venta-detalle").setAttribute("aria-hidden", "true");
            $("venta-buscar").value = "";
            cargarInventarioVentas();
            cargarVentas();
            cargarInventario();
            cargarDashboard();
        }, 1500);
    } else {
        msg("venta-msg", data.error || "Error al registrar.", "error");
    }
});

function msg(id, texto, tipo) {
    const el = $(id);
    if (el) {
        el.textContent = texto;
        el.className = "mensaje " + tipo;
    }
}

async function cargarVentas() {
    const res = await fetch("/api/ventas");
    const datos = await res.json();
    const cont = $("ventas-historial");
    
    if (!datos || datos.length === 0) {
        cont.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/></svg>
                <p>No hay ventas registradas</p>
            </div>`;
        return;
    }
    
    cont.innerHTML = datos.slice(0, 10).map(d => `
        <div class="venta-item">
            <div class="venta-item-info">
                <h4>${d.nombre}</h4>
                <p>${d.laboratorio || ""} · ${d.cantidad} unidad(es)</p>
            </div>
            <div class="venta-item-total">${formatCOP(d.total)}</div>
        </div>
    `).join("");
}

// Cerrar sugerencias al hacer click fuera
document.addEventListener("mousedown", e => {
    if (!e.target.closest(".search-wrapper")) {
        $("venta-sugerencias").style.display = "none";
    }
});

// ── IMPORTACIÓN ─────────────────────────────────────────
let importPreview = [];

$("btn-importar-excel")?.addEventListener("click", () => {
    $("modal-importar").style.display = "flex";
    $("importar-paso1").style.display = "block";
    $("importar-paso2").style.display = "none";
    $("importar-confirmar").style.display = "none";
    const estado = $("importar-estado");
    if (estado) { estado.style.display = "none"; estado.textContent = ""; }
});

const modalImportar = $("modal-importar");
if (modalImportar) {
    modalImportar.querySelector(".modal-close").addEventListener("click", () => {
        modalImportar.style.display = "none";
    });
    modalImportar.querySelector(".modal-overlay").addEventListener("click", () => {
        modalImportar.style.display = "none";
    });
}

$("importar-cancelar")?.addEventListener("click", () => {
    $("modal-importar").style.display = "none";
});

// Clic en cualquier parte del dropzone abre el picker
$("importar-dropzone")?.addEventListener("click", () => {
    $("importar-file").click();
});

// El span "busca" detiene la propagación para evitar doble disparo
$("importar-browse-btn")?.addEventListener("click", (e) => {
    e.stopPropagation();
    $("importar-file").click();
});

// Drag & drop
$("importar-dropzone")?.addEventListener("dragover", (e) => {
    e.preventDefault();
    $("importar-dropzone").style.borderColor = "var(--accent)";
    $("importar-dropzone").style.background = "var(--accent-light)";
});

$("importar-dropzone")?.addEventListener("dragleave", () => {
    $("importar-dropzone").style.borderColor = "";
    $("importar-dropzone").style.background = "";
});

$("importar-dropzone")?.addEventListener("drop", (e) => {
    e.preventDefault();
    $("importar-dropzone").style.borderColor = "";
    $("importar-dropzone").style.background = "";
    const file = e.dataTransfer?.files?.[0];
    if (file) procesarArchivoExcel(file);
});

async function procesarArchivoExcel(file) {
    const estado = $("importar-estado");
    if (estado) {
        estado.style.display = "block";
        estado.style.color = "var(--text-secondary)";
        estado.textContent = "Procesando...";
    }

    try {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch("/api/inventario/importar", { method: "POST", body: formData });
        if (!res.ok) throw new Error("Error del servidor (" + res.status + ")");
        const data = await res.json();

        if (estado) { estado.style.display = "none"; estado.textContent = ""; }

        if (!data.ok) {
            alert(data.error || "Error al importar");
            return;
        }

        if (!data.preview || data.preview.length === 0) {
            alert("No se encontraron productos. Verifica que el archivo tenga una columna 'nombre' o 'producto'.");
            return;
        }

        importPreview = data.preview;
        const matchCount = importPreview.filter(i => i.match).length;
        const noMatchCount = importPreview.length - matchCount;

        $("importar-resumen").innerHTML = `
            <span class="importar-match">✓ ${matchCount} encontrados en INVIMA</span> · 
            <span class="importar-no-match">⚠ ${noMatchCount} sin match</span>
        `;

        $("importar-tabla-body").innerHTML = importPreview.map(item => `
            <tr>
                <td>${item.match ? '<span class="importar-match">✓</span>' : '<span class="importar-no-match">-</span>'}</td>
                <td>${esc(item.nombre)}</td>
                <td>${esc(item.principio || "-")}</td>
                <td>${esc(item.laboratorio || "-")}</td>
                <td>${item.cantidad}</td>
                <td>${formatCOP(item.precio)}</td>
            </tr>
        `).join("");

        $("importar-file").value = "";
        $("importar-paso1").style.display = "none";
        $("importar-paso2").style.display = "block";
        $("importar-confirmar").style.display = "inline-block";
    } catch (err) {
        if (estado) {
            estado.style.display = "block";
            estado.style.color = "var(--danger)";
            estado.textContent = "Error: " + err.message + ". Intenta de nuevo.";
        }
    }
}

$("importar-file")?.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) procesarArchivoExcel(file);
});

$("importar-confirmar")?.addEventListener("click", async () => {
    const res = await fetch("/api/inventario/confirmar-importacion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: importPreview })
    });
    const data = await res.json();

    if (data.ok) {
        alert(`Importación completada: ${data.insertados} nuevos, ${data.actualizados} actualizados`);
        $("modal-importar").style.display = "none";
        cargarInventario();
        cargarDashboard();
    } else {
        alert(data.error || "Error al confirmar");
    }
});

// Reportes
async function descargarReporte(tipo) {
    let url = `/api/reportes/${tipo}`;
    
    if (tipo === "ventas") {
        const desde = $("ventas-desde")?.value;
        const hasta = $("ventas-hasta")?.value;
        if (desde) url += `?desde=${desde}`;
        if (hasta) url += (desde ? "&" : "?") + `hasta=${hasta}`;
    } else if (tipo === "utilidad") {
        const desde = $("utilidad-desde")?.value;
        const hasta = $("utilidad-hasta")?.value;
        if (desde) url += `?desde=${desde}`;
        if (hasta) url += (desde ? "&" : "?") + `hasta=${hasta}`;
    }
    
    window.location.href = url;
}

// ── INIT ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    initModoOscuro();
    cargarDashboard();
});