import pdfplumber
import psycopg2
import psycopg2.extras
import os

PDF_PATH = "Listado de Registros Sanitarios Vigentes de Medicamentos con Principio Activo - INVIMA.pdf"


def limpiar(texto):
    if texto is None:
        return ""
    return " ".join(texto.split())


def get_db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        url = input("DATABASE_URL no está configurada. Pégala ahora: ").strip()
    if not url:
        raise RuntimeError("No se proporcionó DATABASE_URL.")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


def parsear_pdf(pdf_path):
    registros = []

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
                if fila[0] and "EXPEDIENTE" in str(fila[0]):
                    continue
                expediente       = limpiar(fila[0])
                producto         = limpiar(fila[1])
                principio_activo = limpiar(fila[2])
                registro         = limpiar(fila[3])
                estado           = limpiar(fila[4])
                modalidad        = limpiar(fila[5])
                titular          = limpiar(fila[6])

                if "INVIMA" not in registro:
                    continue

                registros.append((
                    expediente, producto, principio_activo,
                    registro, estado, modalidad, titular
                ))

    return registros


def importar_a_postgresql(registros):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS total FROM invima")
    existentes = cur.fetchone()["total"]

    if existentes > 0:
        print(f"\nLa tabla 'invima' ya tiene {existentes} registros.")
        resp = input("¿Deseas ELIMINAR los existentes e importar de nuevo? (s/n): ").strip().lower()
        if resp != "s":
            print("Cancelado. No se importaron datos.")
            conn.close()
            return
        cur.execute("DELETE FROM invima")
        print("Registros existentes eliminados.")

    insertados = 0
    batch_size = 500
    for i in range(0, len(registros), batch_size):
        batch = registros[i:i + batch_size]
        cur.executemany("""
            INSERT INTO invima
                (expediente, producto, principio_activo, registro, estado, modalidad, titular)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, batch)
        insertados += len(batch)
        print(f"Insertados {insertados}/{len(registros)}...", end="\r")

    conn.commit()
    conn.close()
    return insertados


if __name__ == "__main__":
    import sys

    if not os.path.exists(PDF_PATH):
        print(f"Error: no encuentro el archivo '{PDF_PATH}'")
        print("Verifica que el PDF esté en la misma carpeta que este script.")
        sys.exit(1)

    print("Parseando PDF de INVIMA...")
    registros = parsear_pdf(PDF_PATH)
    print(f"\nSe encontraron {len(registros)} registros con INVIMA válido.")

    if not registros:
        print("No se encontraron registros. Verifica el PDF.")
        sys.exit(1)

    if "--count" in sys.argv:
        print(f"\nTotal de registros disponibles: {len(registros)}")
        sys.exit(0)

    resp = input("¿Importar a PostgreSQL? (s/n): ").strip().lower()
    if resp != "s":
        print("Cancelado.")
        sys.exit(0)

    importados = importar_a_postgresql(registros)
    if importados:
        print(f"\nListo. Se importaron {importados} registros a PostgreSQL.")
    sys.exit(0)