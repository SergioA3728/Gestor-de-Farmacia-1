from flask import Flask, request, jsonify, render_template
import sqlite3

app = Flask(__name__)
DB = "farmacia.db"
STOCK_MINIMO = 10

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS catalogo (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT NOT NULL,
            principio   TEXT,
            laboratorio TEXT,
            descripcion TEXT
        );

        CREATE TABLE IF NOT EXISTS inventario (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            invima_id        INTEGER,
            catalogo_id      INTEGER,
            nombre           TEXT NOT NULL,
            principio        TEXT,
            laboratorio      TEXT,
            registro         TEXT,
            cantidad         INTEGER NOT NULL DEFAULT 0,
            precio           REAL NOT NULL DEFAULT 0,
            fecha_vencimiento TEXT,
            lote             TEXT
        );

        CREATE TABLE IF NOT EXISTS ventas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            inventario_id   INTEGER NOT NULL,
            nombre          TEXT NOT NULL,
            laboratorio    TEXT,
            cantidad       INTEGER NOT NULL,
            precio_unitario REAL NOT NULL,
            total           REAL NOT NULL,
            fecha           TEXT DEFAULT (datetime('now', 'localtime'))
        );
    """)
    
    try:
        conn.execute("ALTER TABLE inventario ADD COLUMN fecha_vencimiento TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE inventario ADD COLUMN lote TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE inventario ADD COLUMN categoria TEXT")
    except:
        pass
    
    conn.commit()
    conn.close()

# ── INVIMA ────
@app.route("/api/invima/buscar")
def invima_buscar():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    conn = get_db()
    rows = conn.execute("""
        SELECT id, expediente, producto, principio_activo, registro, modalidad, titular
        FROM invima
        WHERE producto LIKE ? OR principio_activo LIKE ? OR titular LIKE ?
        LIMIT 30
    """, (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

CATEGORIAS_PREDEFINIDAS = [
    "Analgésicos / Antiinflamatorios", "Antibióticos", "Antialérgicos",
    "Antidiabéticos / Antihipertensivos", "Gastrointestinal", "Dermatológicos",
    "Suplementos / Vitaminas", "Otros"
]

CATEGORIAS_KEYWORDS = {
    "ibuprofeno": "Analgésicos / Antiinflamatorios", "diclofenaco": "Analgésicos / Antiinflamatorios",
    "naproxeno": "Analgésicos / Antiinflamatorios", "ketorolaco": "Analgésicos / Antiinflamatorios",
    "paracetamol": "Analgésicos / Antiinflamatorios", "acetaminofen": "Analgésicos / Antiinflamatorios",
    "tramadol": "Analgésicos / Antiinflamatorios", "morfina": "Analgésicos / Antiinflamatorios",
    "codeina": "Analgésicos / Antiinflamatorios",
    "amoxicilina": "Antibióticos", "azitromicina": "Antibióticos", "ciprofloxacino": "Antibióticos",
    "ceftriaxona": "Antibióticos", "amoxicilina clavulanato": "Antibióticos",
    "metronidazol": "Antibióticos", "doxiciclina": "Antibióticos", "penicilina": "Antibióticos",
    "cefuroxima": "Antibióticos", "levofloxacino": "Antibióticos",
    "loratadina": "Antialérgicos", "cetirizina": "Antialérgicos", "desloratadina": "Antialérgicos",
    "hidroxizina": "Antialérgicos", "clorfeniramina": "Antialérgicos", "difenhidramina": "Antialérgicos",
    "metformina": "Antidiabéticos / Antihipertensivos", "glibenclamida": "Antidiabéticos / Antihipertensivos",
    "insulina": "Antidiabéticos / Antihipertensivos", "lisinopril": "Antidiabéticos / Antihipertensivos",
    "enalapril": "Antidiabéticos / Antihipertensivos", "losartan": "Antidiabéticos / Antihipertensivos",
    "amlodipino": "Antidiabéticos / Antihipertensivos", "hidroclorotiazida": "Antidiabéticos / Antihipertensivos",
    "atorvastatin": "Antidiabéticos / Antihipertensivos", "simvastatin": "Antidiabéticos / Antihipertensivos",
    "omeprazol": "Gastrointestinal", "pantoprazol": "Gastrointestinal", "esomeprazol": "Gastrointestinal",
    "ranitidina": "Gastrointestinal", "famotidina": "Gastrointestinal", "metoclopramida": "Gastrointestinal",
    "domperidona": "Gastrointestinal", "loperamida": "Gastrointestinal", "buscapina": "Gastrointestinal",
    "hidrocortisona": "Dermatológicos", "betametasona": "Dermatológicos", "clotrimazol": "Dermatológicos",
    "miconazol": "Dermatológicos", "aceite mineral": "Dermatológicos", "urea": "Dermatológicos",
    "vitamina": "Suplementos / Vitaminas", "magnesio": "Suplementos / Vitaminas", "zinc": "Suplementos / Vitaminas",
    "hierro": "Suplementos / Vitaminas", "calcio": "Suplementos / Vitaminas", "vitamina d": "Suplementos / Vitaminas",
    "vitamina c": "Suplementos / Vitaminas", "complejo b": "Suplementos / Vitaminas"
}

def inferir_categoria(principio):
    if not principio:
        return ""
    principio_lower = principio.lower()
    for kw, cat in CATEGORIAS_KEYWORDS.items():
        if kw in principio_lower:
            return cat
    return ""

@app.route("/api/inferir-categoria", methods=["GET"])
def inferir_categoria_api():
    principio = request.args.get("principio", "")
    return jsonify({"categoria": inferir_categoria(principio)})

@app.route("/api/categorias", methods=["GET"])
def categorias_listar():
    return jsonify(CATEGORIAS_PREDEFINIDAS)

# ── CATÁLOGO PROPIO ─────────────────────────────────────
@app.route("/api/catalogo", methods=["GET"])
def catalogo_listar():
    conn = get_db()
    rows = conn.execute("SELECT * FROM catalogo ORDER BY nombre").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/catalogo", methods=["POST"])
def catalogo_crear():
    d = request.json
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO catalogo (nombre, principio, laboratorio, descripcion)
        VALUES (?, ?, ?, ?)
    """, (d["nombre"], d.get("principio",""), d.get("laboratorio",""), d.get("descripcion","")))
    conn.commit()
    nuevo_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "id": nuevo_id})

# ── INVENTARIO ───────────────────────────────────────────
@app.route("/api/inventario", methods=["GET"])
def inventario_listar():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM inventario ORDER BY nombre
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/inventario", methods=["POST"])
def inventario_agregar():
    d = request.json
    conn = get_db()
    existing = conn.execute("""
        SELECT id, cantidad FROM inventario
        WHERE (invima_id = ? AND invima_id IS NOT NULL)
           OR (catalogo_id = ? AND catalogo_id IS NOT NULL)
    """, (d.get("invima_id"), d.get("catalogo_id"))).fetchone()

    if existing:
        conn.execute("""
            UPDATE inventario SET cantidad = cantidad + ?, precio = ?
            WHERE id = ?
        """, (d["cantidad"], d["precio"], existing["id"]))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "accion": "actualizado"})
    else:
        categoria = d.get("categoria", "") or inferir_categoria(d.get("principio", ""))
        conn.execute("""
            INSERT INTO inventario
                (invima_id, catalogo_id, nombre, principio, laboratorio, registro, cantidad, precio, fecha_vencimiento, lote, categoria)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d.get("invima_id"), d.get("catalogo_id"),
            d["nombre"], d.get("principio",""), d.get("laboratorio",""),
            d.get("registro",""), d["cantidad"], d["precio"],
            d.get("fecha_vencimiento",""), d.get("lote",""), categoria
        ))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "accion": "creado"})

@app.route("/api/inventario/<int:item_id>", methods=["DELETE"])
def inventario_eliminar(item_id):
    conn = get_db()
    conn.execute("DELETE FROM inventario WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/inventario/<int:item_id>", methods=["PUT"])
def inventario_actualizar(item_id):
    d = request.json
    conn = get_db()
    conn.execute("""
        UPDATE inventario SET 
            precio = ?, cantidad = ?, fecha_vencimiento = ?, lote = ?, categoria = ?
        WHERE id = ?
    """, (d.get("precio"), d.get("cantidad"), d.get("fecha_vencimiento"), d.get("lote"), d.get("categoria", ""), item_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/inventario/importar", methods=["POST"])
def inventario_importar():
    import pandas as pd
    from werkzeug.utils import secure_filename
    
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No se recibió archivo"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "error": "Archivo vacío"}), 400
    
    try:
        df = pd.read_excel(file)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Error al leer Excel: {str(e)}"}), 400
    
    COLUMNAS_VALIDAS = ["nombre", "principio", "laboratorio", "cantidad", "precio", "fecha_vencimiento", "lote", "categoria"]
    COLUMNAS_ALIAS = {
        "producto": "nombre", "medicamento": "nombre", "articulo": "nombre",
        "componente": "principio", "genérico": "principio",
        "marca": "laboratorio", "fabricante": "laboratorio",
        "stock": "cantidad", "existencias": "cantidad",
        "valor": "precio", "costo": "precio",
        "vencimiento": "fecha_vencimiento", "caduca": "fecha_vencimiento",
        "lote": "lote", "categoría": "categoria",
        "precio unitario (cop)": "precio",
        "precio unitario": "precio",
        "número de unidades": "cantidad",
        "numero de unidades": "cantidad",
        "unidades": "cantidad"
    }
    
    df.columns = [c.strip().lower() for c in df.columns]
    df.rename(columns=COLUMNAS_ALIAS, inplace=True)
    
    cols_disponibles = [c for c in df.columns if c in COLUMNAS_VALIDAS]
    df = df[cols_disponibles]
    
    for col in ["cantidad", "precio"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    conn = get_db()
    preview = []
    
    for idx, row in df.iterrows():
        nombre_raw = row.get("nombre")
        if pd.isna(nombre_raw) or (isinstance(nombre_raw, float) and str(nombre_raw) == "nan"):
            continue
        nombre = str(nombre_raw).strip()
        if not nombre:
            continue
        
        invima_match = None
        if nombre:
            invima_match = conn.execute("""
                SELECT id, principio_activo, titular, registro
                FROM invima
                WHERE producto LIKE ? OR principio_activo LIKE ?
                LIMIT 1
            """, (f"%{nombre}%", f"%{nombre}%")).fetchone()
        
        item = {
            "nombre": nombre,
            "principio": row.get("principio", "") or (invima_match["principio_activo"] if invima_match else ""),
            "laboratorio": row.get("laboratorio", "") or (invima_match["titular"] if invima_match else ""),
            "registro": invima_match["registro"] if invima_match else "",
            "cantidad": int(row.get("cantidad", 0)),
            "precio": float(row.get("precio", 0)),
            "fecha_vencimiento": str(row.get("fecha_vencimiento", ""))[:10] if pd.notna(row.get("fecha_vencimiento")) else "",
            "lote": str(row["lote"]) if pd.notna(row.get("lote")) else "",
            "categoria": str(row["categoria"]) if pd.notna(row.get("categoria")) else "" or inferir_categoria(row.get("principio", "")),
            "invima_id": invima_match["id"] if invima_match else None,
            "match": invima_match is not None
        }
        preview.append(item)
    
    conn.close()
    return jsonify({"ok": True, "preview": preview, "columnas": cols_disponibles})

@app.route("/api/inventario/confirmar-importacion", methods=["POST"])
def inventario_confirmar_importacion():
    d = request.json
    items = d.get("items", [])
    
    if not items:
        return jsonify({"ok": False, "error": "No hay items"}), 400
    
    conn = get_db()
    insertados = 0
    actualizados = 0
    
    for item in items:
        nombre = item.get("nombre", "").strip()
        if not nombre:
            continue
        
        existing = conn.execute("""
            SELECT id, cantidad FROM inventario
            WHERE (invima_id = ? AND invima_id IS NOT NULL)
               OR (nombre = ?)
        """, (item.get("invima_id"), nombre)).fetchone()
        
        if existing:
            conn.execute("""
                UPDATE inventario SET cantidad = cantidad + ?, precio = ?
                WHERE id = ?
            """, (item.get("cantidad", 0), item.get("precio", 0), existing["id"]))
            actualizados += 1
        else:
            conn.execute("""
                INSERT INTO inventario (invima_id, nombre, principio, laboratorio, registro, cantidad, precio, fecha_vencimiento, lote, categoria)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get("invima_id"), nombre, item.get("principio", ""), item.get("laboratorio", ""),
                item.get("registro", ""), item.get("cantidad", 0), item.get("precio", 0),
                item.get("fecha_vencimiento", ""), item.get("lote", ""), item.get("categoria", "")
            ))
            insertados += 1
    
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "insertados": insertados, "actualizados": actualizados})

@app.route("/api/inventario/recategorizar", methods=["POST"])
def inventario_recategorizar():
    conn = get_db()
    productos = conn.execute("SELECT id, principio FROM inventario WHERE categoria IS NULL OR categoria = ''").fetchall()
    
    actualizados = 0
    for p in productos:
        nueva_cat = inferir_categoria(p["principio"])
        if nueva_cat:
            conn.execute("UPDATE inventario SET categoria = ? WHERE id = ?", (nueva_cat, p["id"]))
            actualizados += 1
    
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "actualizados": actualizados})

# ── REPORTES ───────────────────────────────────────────────
@app.route("/api/reportes/inventario")
def reporte_inventario():
    import pandas as pd
    from openpyxl.styles import Font, PatternFill, Alignment, numbers
    from openpyxl.utils import get_column_letter
    from io import BytesIO
    from datetime import datetime
    
    conn = get_db()
    rows = conn.execute("""
        SELECT nombre, laboratorio, cantidad, precio, fecha_vencimiento, categoria
        FROM inventario WHERE cantidad > 0 ORDER BY cantidad ASC
    """).fetchall()
    conn.close()
    
    data = [dict(r) for r in rows]
    df = pd.DataFrame(data)
    
    if not df.empty:
        df["valor_total"] = df["cantidad"] * df["precio"]
        df["alerta_stock"] = df["cantidad"].apply(lambda x: "CRÍTICO" if x <= 5 else ("BAJO" if x <= 10 else "OK"))
        df = df[["nombre", "laboratorio", "cantidad", "precio", "fecha_vencimiento", "categoria", "valor_total", "alerta_stock"]]
        df.columns = ["Nombre", "Laboratorio", "Cantidad", "Precio", "Fecha Vencimiento", "Categoría", "Valor Total", "Alerta Stock"]
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Inventario", index=False)
        
        ws = writer.sheets["Inventario"]
        
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        for col_idx, col in enumerate(ws[1], start=1):
            col.fill = header_fill
            col.font = header_font
            col.alignment = header_alignment
        
        grey_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        
        critico_fill = PatternFill(start_color="F4CCCC", end_color="F4CCCC", fill_type="solid")
        critico_font = Font(color="990000")
        bajo_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        bajo_font = Font(color="7D6608")
        ok_fill = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")
        ok_font = Font(color="274E13")
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
            if row_idx % 2 == 0:
                for cell in row:
                    cell.fill = grey_fill
            
            alerta_cell = row[7]
            alerta_val = alerta_cell.value
            if alerta_val == "CRÍTICO":
                alerta_cell.fill = critico_fill
                alerta_cell.font = critico_font
            elif alerta_val == "BAJO":
                alerta_cell.fill = bajo_fill
                alerta_cell.font = bajo_font
            elif alerta_val == "OK":
                alerta_cell.fill = ok_fill
                alerta_cell.font = ok_font
        
        last_data_row = ws.max_row + 1
        ws.cell(row=last_data_row, column=1, value="Total productos").font = Font(bold=True)
        ws.cell(row=last_data_row, column=3, value=len(df)).font = Font(bold=True)
        ws.cell(row=last_data_row, column=3).number_format = "#,##0"
        
        ws.cell(row=last_data_row + 1, column=1, value="Total unidades").font = Font(bold=True)
        ws.cell(row=last_data_row + 1, column=3, value=int(df["Cantidad"].sum())).font = Font(bold=True)
        ws.cell(row=last_data_row + 1, column=3).number_format = "#,##0"
        
        price_col = ws["D"]
        for cell in price_col[1:]:
            cell.number_format = "$#,##0"
        
        total_col = ws["G"]
        for cell in total_col[1:]:
            cell.number_format = "$#,##0"
        
        qty_col = ws["C"]
        for cell in qty_col[1:]:
            cell.number_format = "#,##0"
        
        date_col = ws["E"]
        for cell in date_col[1:]:
            cell.number_format = "DD/MM/YYYY"
        
        for column in ws.columns:
            max_length = max(len(str(cell.value or "")) for cell in column)
            ws.column_dimensions[get_column_letter(column[0].column)].width = max_length + 4
        
        if not df.empty:
            resumen = pd.DataFrame({
                "Métrica": ["Total productos", "Total unidades", "Valor total stock", "Bajo stock", "Crítico"],
                "Valor": [
                    len(df),
                    df["Cantidad"].sum() if "Cantidad" in df else 0,
                    df["Valor Total"].sum() if "Valor Total" in df else 0,
                    len(df[df["Cantidad"] <= 10]) if "Cantidad" in df else 0,
                    len(df[df["Cantidad"] <= 5]) if "Cantidad" in df else 0
                ]
            })
            resumen.to_excel(writer, sheet_name="Resumen", index=False)
    
    output.seek(0)
    from flask import send_file
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"inventario_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )

@app.route("/api/reportes/ventas")
def reporte_ventas():
    import pandas as pd
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    from io import BytesIO
    from datetime import datetime
    
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")
    
    conn = get_db()
    query = "SELECT nombre, laboratorio, cantidad, precio_unitario, total, fecha FROM ventas WHERE 1=1"
    params = []
    if desde:
        query += " AND date(fecha) >= date(?)"
        params.append(desde)
    if hasta:
        query += " AND date(fecha) <= date(?)"
        params.append(hasta)
    query += " ORDER BY fecha DESC"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    data = [dict(r) for r in rows]
    df = pd.DataFrame(data)
    
    if not df.empty:
        df.columns = ["Nombre", "Laboratorio", "Cantidad", "Precio Unitario", "Total", "Fecha"]
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Ventas", index=False)
        
        ws = writer.sheets["Ventas"]
        
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        for col in ws[1]:
            col.fill = header_fill
            col.font = header_font
            col.alignment = header_alignment
        
        grey_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
            if row_idx % 2 == 0:
                for cell in row:
                    cell.fill = grey_fill
        
        price_col = ws["D"]
        for cell in price_col[1:]:
            cell.number_format = "$#,##0"
        
        total_col = ws["E"]
        for cell in total_col[1:]:
            cell.number_format = "$#,##0"
        
        qty_col = ws["C"]
        for cell in qty_col[1:]:
            cell.number_format = "#,##0"
        
        date_col = ws["F"]
        for cell in date_col[1:]:
            cell.number_format = "DD/MM/YYYY"
        
        name_col = ws["A"]
        lab_col = ws["B"]
        for cell in name_col[1:]:
            cell.alignment = Alignment(horizontal="left")
        for cell in lab_col[1:]:
            cell.alignment = Alignment(horizontal="left")
        
        for column in ws.columns:
            max_length = max(len(str(cell.value or "")) for cell in column)
            ws.column_dimensions[get_column_letter(column[0].column)].width = max_length + 4
        
        if not df.empty:
            last_row = ws.max_row + 1
            ws.cell(row=last_row, column=1, value="Total ventas").font = Font(bold=True)
            ws.cell(row=last_row, column=5, value=int(df["Total"].sum())).font = Font(bold=True)
            ws.cell(row=last_row, column=5).number_format = "$#,##0"
    
    output.seek(0)
    from flask import send_file
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"ventas_{desde or 'all'}_{hasta or 'all'}.xlsx"
    )

@app.route("/api/reportes/utilidad")
def reporte_utilidad():
    import pandas as pd
    from io import BytesIO
    from datetime import datetime
    
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")
    
    conn = get_db()
    query = "SELECT * FROM ventas WHERE 1=1"
    params = []
    if desde:
        query += " AND date(fecha) >= date(?)"
        params.append(desde)
    if hasta:
        query += " AND date(fecha) <= date(?)"
        params.append(hasta)
    query += " ORDER BY fecha DESC"
    
    ventas = conn.execute(query, params).fetchall()
    
    inventario_actual = conn.execute("SELECT SUM(cantidad * precio) as costo FROM inventario").fetchone()
    conn.close()
    
    ventas_data = [dict(r) for r in ventas]
    df_ventas = pd.DataFrame(ventas_data)
    
    ingresos = df_ventas["total"].sum() if not df_ventas.empty else 0
    costo_inventario = inventario_actual["costo"] or 0
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if not df_ventas.empty:
            df_ventas.to_excel(writer, sheet_name="Ventas", index=False)
        
        resumen = pd.DataFrame({
            "Concepto": ["Ingresos por ventas", "Costo estimado inventario", "Margen bruto estimado"],
            "Valor": [ingresos, costo_inventario, ingresos - costo_inventario]
        })
        resumen.to_excel(writer, sheet_name="Resumen", index=False)
    
    output.seek(0)
    from flask import send_file
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"utilidad_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )

@app.route("/api/dashboard/alertas", methods=["GET"])
def dashboard_alertas():
    import datetime
    conn = get_db()
    
    thirty_days = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    
    bajo_stock = conn.execute("""
        SELECT nombre, cantidad, 
               CASE WHEN cantidad <= 5 THEN 'critico' ELSE 'bajo' END as nivel
        FROM inventario
        WHERE cantidad <= ?
        ORDER BY cantidad ASC
    """, (STOCK_MINIMO,)).fetchall()
    
    vencer = conn.execute("""
        SELECT nombre, fecha_vencimiento, cantidad
        FROM inventario
        WHERE fecha_vencimiento IS NOT NULL AND fecha_vencimiento != '' AND fecha_vencimiento <= ?
        ORDER BY fecha_vencimiento ASC
    """, (thirty_days,)).fetchall()
    
    conn.close()
    return jsonify({
        "bajo_stock": [dict(r) for r in bajo_stock],
        "proximos_vencer": [dict(r) for r in vencer]
    })

@app.route("/api/dashboard/ventas-hoy", methods=["GET"])
def dashboard_ventas_hoy():
    conn = get_db()
    row = conn.execute("""
        SELECT COALESCE(SUM(total), 0) as total, COUNT(*) as transacciones
        FROM ventas
        WHERE date(fecha) = date('now', 'localtime')
    """).fetchone()
    conn.close()
    return jsonify({"total": row["total"], "transacciones": row["transacciones"]})

@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    import datetime
    conn = get_db()
    
    total = conn.execute("SELECT SUM(cantidad) as total FROM inventario").fetchone()["total"] or 0
    total_productos = conn.execute("SELECT COUNT(*) as count FROM inventario WHERE cantidad > 0").fetchone()["count"]
    bajo_stock = conn.execute("SELECT COUNT(*) as count FROM inventario WHERE cantidad <= ?", (STOCK_MINIMO,)).fetchone()["count"]
    
    thirty_days = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    vencer = conn.execute("""
        SELECT COUNT(*) as count FROM inventario 
        WHERE fecha_vencimiento IS NOT NULL AND fecha_vencimiento != '' AND fecha_vencimiento <= ?
    """, (thirty_days,)).fetchone()["count"]
    
    conn.close()
    return jsonify({
        "total_productos": total_productos,
        "total_unidades": total,
        "bajo_stock": bajo_stock,
        "prox_vencer": vencer
    })

# ── VENTAS ───────────────────────────────────────────────
@app.route("/api/ventas", methods=["GET"])
def ventas_listar():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM ventas ORDER BY fecha DESC LIMIT 100
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/ventas", methods=["POST"])
def registrar_venta():
    d = request.json
    conn = get_db()
    item = conn.execute("""
        SELECT id, nombre, laboratorio, cantidad, precio FROM inventario WHERE id = ?
    """, (d["inventario_id"],)).fetchone()

    if not item:
        conn.close()
        return jsonify({"ok": False, "error": "Producto no encontrado"}), 404

    if item["cantidad"] < d["cantidad"]:
        conn.close()
        return jsonify({"ok": False, "error": "Stock insuficiente"}), 400

    total = item["precio"] * d["cantidad"]

    conn.execute("""
        UPDATE inventario SET cantidad = cantidad - ? WHERE id = ?
    """, (d["cantidad"], item["id"]))

    conn.execute("""
        INSERT INTO ventas (inventario_id, nombre, laboratorio, cantidad, precio_unitario, total)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (item["id"], item["nombre"], item["laboratorio"], d["cantidad"], item["precio"], total))

    conn.commit()
    conn.close()
    return jsonify({"ok": True, "total": total})

# ── PÁGINA PRINCIPAL ─────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    import os
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
