"""
Pobla 'categoria' en tabla invima usando execute_values (rápido).
Ejecutar: python scripts/poblar_categoria_invima.py
"""
import os
import sys
import unicodedata
import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CATEGORIAS_KEYWORDS = {
    "ibuprofeno": "Analgésicos / Antiinflamatorios", "diclofenaco": "Analgésicos / Antiinflamatorios",
    "naproxeno": "Analgésicos / Antiinflamatorios", "ketorolaco": "Analgésicos / Antiinflamatorios",
    "paracetamol": "Analgésicos / Antiinflamatorios", "acetaminofen": "Analgésicos / Antiinflamatorios",
    "tramadol": "Analgésicos / Antiinflamatorios", "morfina": "Analgésicos / Antiinflamatorios",
    "codeina": "Analgésicos / Antiinflamatorios", "aspirina": "Analgésicos / Antiinflamatorios",
    "metamizol": "Analgésicos / Antiinflamatorios", "piroxicam": "Analgésicos / Antiinflamatorios",
    "celecoxib": "Analgésicos / Antiinflamatorios", "meloxicam": "Analgésicos / Antiinflamatorios",
    "flurbiprofeno": "Analgésicos / Antiinflamatorios", "nimesulida": "Analgésicos / Antiinflamatorios",
    "indometacina": "Analgésicos / Antiinflamatorios",
    "amoxicilina": "Antibióticos", "azitromicina": "Antibióticos", "ciprofloxacino": "Antibióticos",
    "ceftriaxona": "Antibióticos", "amoxicilina clavulanato": "Antibióticos",
    "metronidazol": "Antibióticos", "doxiciclina": "Antibióticos", "penicilina": "Antibióticos",
    "cefuroxima": "Antibióticos", "levofloxacino": "Antibióticos", "cefalexina": "Antibióticos",
    "sulfametoxazol": "Antibióticos", "trimetoprim": "Antibióticos", "clindamicina": "Antibióticos",
    "eritromicina": "Antibióticos", "vancomicina": "Antibióticos", "gentamicina": "Antibióticos",
    "cefepima": "Antibióticos", "meropenem": "Antibióticos",
    "rifampicina": "Antibióticos", "isoniazida": "Antibióticos",
    "fluconazol": "Antibióticos", "voriconazol": "Antibióticos",
    "itraconazol": "Antibióticos", "anfotericina": "Antibióticos", "acyclovir": "Antibióticos",
    "loratadina": "Antialérgicos", "cetirizina": "Antialérgicos", "desloratadina": "Antialérgicos",
    "hidroxizina": "Antialérgicos", "clorfeniramina": "Antialérgicos", "difenhidramina": "Antialérgicos",
    "fexofenadina": "Antialérgicos", "levocetirizina": "Antialérgicos",
    "metformina": "Antidiabéticos / Antihipertensivos", "glibenclamida": "Antidiabéticos / Antihipertensivos",
    "insulina": "Antidiabéticos / Antihipertensivos", "lisinopril": "Antidiabéticos / Antihipertensivos",
    "enalapril": "Antidiabéticos / Antihipertensivos", "losartan": "Antidiabéticos / Antihipertensivos",
    "amlodipino": "Antidiabéticos / Antihipertensivos", "hidroclorotiazida": "Antidiabéticos / Antihipertensivos",
    "atorvastatin": "Antidiabéticos / Antihipertensivos", "simvastatin": "Antidiabéticos / Antihipertensivos",
    "valsartan": "Antidiabéticos / Antihipertensivos", "ramipril": "Antidiabéticos / Antihipertensivos",
    "bisoprolol": "Antidiabéticos / Antihipertensivos", "metoprolol": "Antidiabéticos / Antihipertensivos",
    "propranolol": "Antidiabéticos / Antihipertensivos", "atenolol": "Antidiabéticos / Antihipertensivos",
    "carvedilol": "Antidiabéticos / Antihipertensivos", "espironolactona": "Antidiabéticos / Antihipertensivos",
    "furosemida": "Antidiabéticos / Antihipertensivos", "clopidogrel": "Antidiabéticos / Antihipertensivos",
    "warfarina": "Antidiabéticos / Antihipertensivos", "heparina": "Antidiabéticos / Antihipertensivos",
    "omeprazol": "Gastrointestinal", "pantoprazol": "Gastrointestinal", "esomeprazol": "Gastrointestinal",
    "ranitidina": "Gastrointestinal", "famotidina": "Gastrointestinal", "metoclopramida": "Gastrointestinal",
    "domperidona": "Gastrointestinal", "loperamida": "Gastrointestinal", "buscapina": "Gastrointestinal",
    "lansoprazol": "Gastrointestinal", "sucralfato": "Gastrointestinal",
    "simeticona": "Gastrointestinal", "lactulosa": "Gastrointestinal", "bisacodilo": "Gastrointestinal",
    "hidrocortisona": "Dermatológicos", "betametasona": "Dermatológicos", "clotrimazol": "Dermatológicos",
    "miconazol": "Dermatológicos", "urea": "Dermatológicos",
    "acido retinoico": "Dermatológicos", "retinol": "Dermatológicos", "tretinoina": "Dermatológicos",
    "adapaleno": "Dermatológicos", "mupirocina": "Dermatológicos",
    "pimecrolimus": "Dermatológicos", "tacrolimus": "Dermatológicos",
    "vitamina": "Suplementos / Vitaminas", "magnesio": "Suplementos / Vitaminas", "zinc": "Suplementos / Vitaminas",
    "hierro": "Suplementos / Vitaminas", "calcio": "Suplementos / Vitaminas", "vitamina d": "Suplementos / Vitaminas",
    "vitamina c": "Suplementos / Vitaminas", "complejo b": "Suplementos / Vitaminas",
    "acido folico": "Suplementos / Vitaminas", "vitamina b12": "Suplementos / Vitaminas",
    "selenio": "Suplementos / Vitaminas", "potasio": "Suplementos / Vitaminas",
    "omega": "Suplementos / Vitaminas", "colageno": "Suplementos / Vitaminas", "biotina": "Suplementos / Vitaminas",
    "sales": "Suplementos / Vitaminas",
    "pasta dental": "Higiene Bucal", "cepillo dental": "Higiene Bucal",
    "enjuague bucal": "Higiene Bucal", "hilo dental": "Higiene Bucal",
    "desodorante": "Higiene Personal", "antitranspirante": "Higiene Personal",
    "jabon": "Higiene Personal",
    "condon": "Salud Sexual", "preservativo": "Salud Sexual", "lubricante": "Salud Sexual",
    "spray nasal": "Descongestionantes", "descongestionante": "Descongestionantes",
    "guaifenesina": "Descongestionantes", "pseudoefedrina": "Descongestionantes",
    "salbutamol": "Descongestionantes", "budesonida": "Descongestionantes",
    "montelukast": "Descongestionantes",
    "benznidazol": "Antiparasitarios", "albendazol": "Antiparasitarios",
    "ivermectina": "Antiparasitarios", "mebendazol": "Antiparasitarios",
    "levotiroxina": "Hormonales", "progesterona": "Hormonales", "testosterona": "Hormonales",
    "tamoxifeno": "Oncología", "metotrexato": "Oncología",
    "paclitaxel": "Oncología", "doxorubicina": "Oncología", "cisplatino": "Oncología",
    "bevacizumab": "Oncología", "trastuzumab": "Oncología", "rituximab": "Oncología",
    "pembrolizumab": "Oncología", "nivolumab": "Oncología",
    "imatinib": "Oncología", "letrozol": "Oncología", "anastrozol": "Oncología",
    "abiraterona": "Oncología", "enzalutamida": "Oncología",
    "dexametasona": "Oncología", "prednisona": "Oncología",
    "levodopa": "Neurológicos", "carbamazepina": "Neurológicos", "valproico": "Neurológicos",
    "lamotrigina": "Neurológicos", "levetiracetam": "Neurológicos", "fenitoina": "Neurológicos",
    "gabapentina": "Neurológicos", "pregabalina": "Neurológicos",
    "duloxetina": "Neurológicos", "venlafaxina": "Neurológicos", "amitriptilina": "Neurológicos",
    "fluoxetina": "Neurológicos", "sertralina": "Neurológicos", "escitalopram": "Neurológicos",
    "alprazolam": "Neurológicos", "lorazepam": "Neurológicos", "diazepam": "Neurológicos",
    "clonazepam": "Neurológicos", "zolpidem": "Neurológicos",
    "quetiapina": "Neurológicos", "olanzapina": "Neurológicos", "risperidona": "Neurológicos",
    "aripiprazol": "Neurológicos", "haloperidol": "Neurológicos",
    "tadalafil": "Urológicos", "sildenafilo": "Urológicos", "finasterida": "Urológicos",
    "tamsulosina": "Urológicos", "solifenacina": "Urológicos",
    "alendronato": "Osteoporosis", "risedronato": "Osteoporosis",
    "pilocarpina": "Oftalmológicos", "latanoprost": "Oftalmológicos", "timolol": "Oftalmológicos",
    "shampoo": "Cuidado Capilar", "acondicionador": "Cuidado Capilar",
    "crema facial": "Cuidado de la Piel", "protector solar": "Cuidado de la Piel",
    "balsamo labial": "Cuidado de la Piel", "locion": "Cuidado de la Piel",
    "crema de manos": "Cuidado de la Piel", "crema corporal": "Cuidado de la Piel",
    "panal": "Cuidado del Bebe", "toallitas": "Cuidado del Bebe",
    "gasa": "Primeros Auxilios", "venda": "Primeros Auxilios", "curita": "Primeros Auxilios",
    "algodon": "Primeros Auxilios", "jeringa": "Dispositivos Medicos", "guante": "Primeros Auxilios",
    "alcohol": "Primeros Auxilios", "yodo": "Primeros Auxilios",
    "termometro": "Dispositivos Medicos", "tensio metro": "Dispositivos Medicos", "glucometro": "Dispositivos Medicos",
}

BATCH_SIZE = 1000


def _normalizar(texto):
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def inferir_categoria(principio):
    campos = _normalizar(principio or "").lower().strip()
    if not campos:
        return ""
    for kw, cat in CATEGORIAS_KEYWORDS.items():
        if kw in campos:
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
