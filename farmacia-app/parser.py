import pdfplumber
import sqlite3
import os

PDF_PATH = "Listado de Registros Sanitarios Vigentes de Medicamentos con Principio Activo - INVIMA.pdf"
DB_PATH = "farmacia.db"

def limpiar(texto):
    if texto is None:
        return ""
    return " ".join(texto.split())

def crear_base_de_datos(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invima (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            expediente       TEXT,
            producto         TEXT,
            principio_activo TEXT,
            registro         TEXT,
            estado           TEXT,
            modalidad        TEXT,
            titular          TEXT
        )
    """)
    conn.commit()

def parsear_pdf(pdf_path, conn):
    registros = []
    columnas = ["EXPEDIENTE", "PRODUCTO", "PRINCIPIO_ACTIVO",
                "REGISTRO_SANITARIO", "ESTADO_REGISTRO", "MODALIDAD", "TITULAR"]

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            print(f"Procesando página {i+1}/{total}...", end="\r")
            tabla = page.extract_table()
            if not tabla:
                continue
            for fila in tabla:
                if fila is None or len(fila) < 7:
                    continue
                # Saltar filas de encabezado
                if fila[0] and "EXPEDIENTE" in str(fila[0]):
                    continue
                expediente       = limpiar(fila[0])
                producto         = limpiar(fila[1])
                principio_activo = limpiar(fila[2])
                registro         = limpiar(fila[3])
                estado           = limpiar(fila[4])
                modalidad        = limpiar(fila[5])
                titular          = limpiar(fila[6])

                # Solo guardar filas que tengan registro INVIMA
                if "INVIMA" not in registro:
                    continue

                registros.append((
                    expediente, producto, principio_activo,
                    registro, estado, modalidad, titular
                ))

    conn.executemany("""
        INSERT INTO invima
            (expediente, producto, principio_activo, registro, estado, modalidad, titular)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, registros)
    conn.commit()
    return len(registros)

if __name__ == "__main__":
    if not os.path.exists(PDF_PATH):
        print(f"Error: no encuentro el archivo '{PDF_PATH}'")
        print("Verifica que el PDF esté en la misma carpeta que este script.")
        exit(1)

    conn = sqlite3.connect(DB_PATH)
    crear_base_de_datos(conn)
    total = parsear_pdf(PDF_PATH, conn)
    conn.close()

    print(f"\nListo. Se importaron {total} registros a '{DB_PATH}'")