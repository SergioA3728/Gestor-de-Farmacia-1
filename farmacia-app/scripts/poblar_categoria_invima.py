"""
Pobla 'categoria' en tabla invima usando execute_values (rápido).
Ejecutar: python scripts/poblar_categoria_invima.py
"""
import os
import sys
import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CATEGORIAS_KEYWORDS = {
    "ibuprofeno": "Analgésicos / Antiinflamatorios",
    "diclofenaco": "Analgésicos / Antiinflamatorios",
    "naproxeno": "Analgésicos / Antiinflamatorios",
    "ketorolaco": "Analgésicos / Antiinflamatorios",
    "paracetamol": "Analgésicos / Antiinflamatorios",
    "acetaminofen": "Analgésicos / Antiinflamatorios",
    "tramadol": "Analgésicos / Antiinflamatorios",
    "morfina": "Analgésicos / Antiinflamatorios",
    "codeina": "Analgésicos / Antiinflamatorios",
    "amoxicilina": "Antibióticos",
    "azitromicina": "Antibióticos",
    "ciprofloxacino": "Antibióticos",
    "ceftriaxona": "Antibióticos",
    "amoxicilina clavulanato": "Antibióticos",
    "metronidazol": "Antibióticos",
    "doxiciclina": "Antibióticos",
    "penicilina": "Antibióticos",
    "cefuroxima": "Antibióticos",
    "levofloxacino": "Antibióticos",
    "loratadina": "Antialérgicos",
    "cetirizina": "Antialérgicos",
    "desloratadina": "Antialérgicos",
    "hidroxizina": "Antialérgicos",
    "clorfeniramina": "Antialérgicos",
    "difenhidramina": "Antialérgicos",
    "metformina": "Antidiabéticos / Antihipertensivos",
    "glibenclamida": "Antidiabéticos / Antihipertensivos",
    "insulina": "Antidiabéticos / Antihipertensivos",
    "lisinopril": "Antidiabéticos / Antihipertensivos",
    "enalapril": "Antidiabéticos / Antihipertensivos",
    "losartan": "Antidiabéticos / Antihipertensivos",
    "amlodipino": "Antidiabéticos / Antihipertensivos",
    "hidroclorotiazida": "Antidiabéticos / Antihipertensivos",
    "atorvastatin": "Antidiabéticos / Antihipertensivos",
    "simvastatin": "Antidiabéticos / Antihipertensivos",
    "omeprazol": "Gastrointestinal",
    "pantoprazol": "Gastrointestinal",
    "esomeprazol": "Gastrointestinal",
    "ranitidina": "Gastrointestinal",
    "famotidina": "Gastrointestinal",
    "metoclopramida": "Gastrointestinal",
    "domperidona": "Gastrointestinal",
    "loperamida": "Gastrointestinal",
    "buscapina": "Gastrointestinal",
    "hidrocortisona": "Dermatológicos",
    "betametasona": "Dermatológicos",
    "clotrimazol": "Dermatológicos",
    "miconazol": "Dermatológicos",
    "aceite mineral": "Dermatológicos",
    "urea": "Dermatológicos",
    "shampoo": "Dermatológicos",
    "acondicionador": "Dermatológicos",
    "jabón": "Dermatológicos",
    "jabon": "Dermatológicos",
    "pasta dental": "Dermatológicos",
    "desodorante": "Dermatológicos",
    "antitranspirante": "Dermatológicos",
    "crema": "Dermatológicos",
    "protector solar": "Dermatológicos",
    "bálsamo labial": "Dermatológicos",
    "balsamo labial": "Dermatológicos",
    "loción": "Dermatológicos",
    "locion": "Dermatológicos",
    "aceite corporal": "Dermatológicos",
    "crema facial": "Dermatológicos",
    "crema corporal": "Dermatológicos",
    "crema hidratante": "Dermatológicos",
    "aloe": "Dermatológicos",
    "glicerina": "Dermatológicos",
    "manteca": "Dermatológicos",
    "shea": "Dermatológicos",
    "coco": "Dermatológicos",
    "caléndula": "Dermatológicos",
    "calendula": "Dermatológicos",
    "mentol": "Dermatológicos",
    "vitamina e": "Dermatológicos",
    "vitamina": "Suplementos / Vitaminas",
    "magnesio": "Suplementos / Vitaminas",
    "zinc": "Suplementos / Vitaminas",
    "hierro": "Suplementos / Vitaminas",
    "calcio": "Suplementos / Vitaminas",
    "vitamina d": "Suplementos / Vitaminas",
    "vitamina c": "Suplementos / Vitaminas",
    "complejo b": "Suplementos / Vitaminas",
    "omega": "Suplementos / Vitaminas",
    "colágeno": "Suplementos / Vitaminas",
    "colageno": "Suplementos / Vitaminas",
    "biotina": "Suplementos / Vitaminas",
    "sales": "Suplementos / Vitaminas",
    "condón": "Otros",
    "condon": "Otros",
    "preservativo": "Otros",
    "lubricante": "Otros",
    "pañal": "Otros",
    "panal": "Otros",
    "toallitas": "Otros",
    "gasa": "Otros",
    "venda": "Otros",
    "curita": "Otros",
    "algodón": "Otros",
    "algodon": "Otros",
    "jeringa": "Otros",
    "guante": "Otros",
    "alcohol": "Otros",
    "suero": "Otros",
    "yodo": "Otros",
    "peróxido": "Otros",
    "peroxido": "Otros",
    "termómetro": "Otros",
    "termometro": "Otros",
    "tiras reactivas": "Otros",
}

BATCH_SIZE = 1000


def inferir_categoria(principio):
    if not principio:
        return ""
    p = principio.lower()
    for kw, cat in CATEGORIAS_KEYWORDS.items():
        if kw in p:
            return cat
    return ""


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: Define DATABASE_URL")
        sys.exit(1)

    conn = psycopg2.connect(url, connect_timeout=30)
    cur = conn.cursor()

    cur.execute("SELECT id, principio_activo FROM invima")
    rows = cur.fetchall()
    total = len(rows)
    print(f"Total registros: {total}")

    pairs = [(inferir_categoria(principio), row_id) for row_id, principio in rows]
    con_cat = sum(1 for cat, _ in pairs if cat)

    updates = [(cat, rid) for cat, rid in pairs if cat]
    print(f"Con categoria: {len(updates)}")

    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i : i + BATCH_SIZE]
        execute_values(
            cur,
            "UPDATE invima SET categoria = v.cat FROM (VALUES %s) AS v(cat, id) WHERE invima.id = v.id",
            batch,
            page_size=BATCH_SIZE,
        )
        conn.commit()
        print(f"  Escritos: {min(i + BATCH_SIZE, len(updates))}/{len(updates)}")

    cur.execute("SELECT COUNT(*) FROM invima WHERE categoria IS NOT NULL AND categoria != ''")
    ok = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM invima WHERE categoria IS NULL OR categoria = ''")
    empty = cur.fetchone()[0]
    conn.close()
    print(f"Listo - Con categoria: {ok}, Sin categoria: {empty}")


if __name__ == "__main__":
    main()
