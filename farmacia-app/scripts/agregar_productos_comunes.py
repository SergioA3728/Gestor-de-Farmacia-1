"""
Agrega productos comunes de farmacia NO cubiertos por INVIMA.
Higiene, cosméticos, salud sexual, primeros auxilios, etc.
Ejecutar: python scripts/agregar_productos_comunes.py
"""
import os
import sys
import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PRODUCTOS_COMUNES = [
    # Higiene bucal
    ("PASTA DENTAL COLGATE TOTAL 12", "FLUORURO DE SODIO 0.24%", "COLGATE-PALMOLIVE", "Higiene Bucal"),
    ("PASTA DENTAL SENSODYNE REPARACION", "NITRATO DE POTASIO", "GSK CONSUMER", "Higiene Bucal"),
    ("CEPILLO DENTES ORAL-B PRO-SALUD", "N/A", "PROCTER & GAMBLE", "Higiene Bucal"),
    ("ENJUAGUE BUCAL LISTERINE COOL MINT", "MENTOL + TIMOL", "KENVIL", "Higiene Bucal"),
    ("HILO DENTAL ORAL-B SUAVE", "N/A", "PROCTER & GAMBLE", "Higiene Bucal"),
    # Desodorantes
    ("DESODORANTE REXONA SPRAY", "CLORETO DE ALUMINIO", "RECKITT", "Higiene Personal"),
    ("DESODORANTE DOVE ROLL ON", "CLORETO DE ALUMINIO", "UNILEVER", "Higiene Personal"),
    ("DESODORANTE NIVEA INVISIBLE FOR BLACK", "CLORETO DE ALUMINIO", "BEIERSDORF", "Higiene Personal"),
    # Jabones
    ("JABON DOVE BEAUTY BAR", "SODIUM LAURETH SULFATE", "UNILEVER", "Higiene Personal"),
    ("JABON LQUIDO DOVE SENSITIVE", "SODIUM LAURETH SULFATE", "UNILEVER", "Higiene Personal"),
    # Cabello
    ("SHAMPOO HEAD SHOULDERS ANTICASPA", "PIRITIONATO DE ZINC", "PROCTER & GAMBLE", "Cuidado Capilar"),
    ("SHAMPOO CLEAR HOMBRE", "SELENIO SULFIDE", "UNILEVER", "Cuidado Capilar"),
    ("SHAMPOO PANTENE HIDROBOMB", "PANTENOL", "PROCTER & GAMBLE", "Cuidado Capilar"),
    ("ACONDICIONADOR PANTENE HIDROBOMB", "DIMETHICONE", "PROCTER & GAMBLE", "Cuidado Capilar"),
    # Cuidado de piel
    ("CREMA MANOS NIVEA", "GLICERINA", "BEIERSDORF", "Cuidado de la Piel"),
    ("CREMA MANOS DOVE", "SHEA BUTTER", "UNILEVER", "Cuidado de la Piel"),
    ("LOCION CORPORAL NIVEA HIDRATANTE", "ALOE VERA", "BEIERSDORF", "Cuidado de la Piel"),
    ("CREMA CORPORAL DOVE NUTRICION", "GLICERINA", "UNILEVER", "Cuidado de la Piel"),
    ("PROTECTOR SOLAR ISDIN FUSION WATER", "TITANIUM DIOXIDE", "ISDIN", "Cuidado de la Piel"),
    ("PROTECTOR SOLAR LA ROCHE-POSAY ANTHELIOS", "AVOBENZONE", "L'OREAL", "Cuidado de la Piel"),
    ("BALSO LABIAL NIVEA HYDRO CARE", "CERA DE ABEJA", "BEIERSDORF", "Cuidado de la Piel"),
    ("CREMA FACIAL CETAPHIL HIDRATANTE", "GLICERINA", "GALDERMA", "Cuidado de la Piel"),
    # Salud sexual
    ("CONDONES DUREX FEVER 3U", "LATEX NATURAL", "RECKITT", "Salud Sexual"),
    ("CONDONES DUREX REAL 3U", "LATEX NATURAL", "RECKITT", "Salud Sexual"),
    ("CONDONES DUREX SENSE 3U", "LATEX NATURAL", "RECKITT", "Salud Sexual"),
    ("CONDONES OKAMOTO 003 3U", "POLIURETANO", "OKAMOTO INDUSTRIES", "Salud Sexual"),
    ("LUBRIFICANTE DUREX REAL", "AGUA", "RECKITT", "Salud Sexual"),
    # Bebe
    ("PANALES HUGGIES SUPREME", "N/A", "KIMBERLY-CLARK", "Cuidado del Bebe"),
    ("PANALES PAMPERS ACTIVE SEC", "N/A", "PROCTER & GAMBLE", "Cuidado del Bebe"),
    ("TOALLITAS HUGGIES NATURALS", "PROPILÉN GLICOL", "KIMBERLY-CLARK", "Cuidado del Bebe"),
    ("CREMA ANTIPANAL DESITIN", "OXIDO DE ZINC", "PFIZER", "Cuidado del Bebe"),
    # Primeros auxilios
    ("CURITAS BAND-AID CLASSIC", "N/A", "JOHNSON & JOHNSON", "Primeros Auxilios"),
    ("ALCOHOL ETILICO QUIMIPHAR 70%", "ETANOL 70%", "QUIMIPHAR", "Primeros Auxilios"),
    ("AGUA OXIGENADA QUIMIPHAR", "PEROXIDO DE HIDROGENO", "QUIMIPHAR", "Primeros Auxilios"),
    ("YODOPOVIDONA BETADINE", "YODO 10%", "RECKITT", "Primeros Auxilios"),
    ("GAZA ESTERIL 3M TELA", "ALGODON", "3M", "Primeros Auxilios"),
    ("VENDA ELASTICA 3M", "ALGODON / LATEX", "3M", "Primeros Auxilios"),
    # Dispositivos medicos
    ("TERMOMETRO DIGITAL OMRON", "N/A", "OMRON HEALTHCARE", "Dispositivos Medicos"),
    ("TENSIOMETRO DIGITAL OMRON M2", "N/A", "OMRON HEALTHCARE", "Dispositivos Medicos"),
    ("GLUCOMETRO ONETOUCH SELECT", "N/A", "LIFESCAN", "Dispositivos Medicos"),
    # Vitaminas
    ("VITAMINA C REDOXON 1000MG", "ACIDO ASCORBICO", "BAYER", "Suplementos / Vitaminas"),
    ("VITAMINAS CENTRUM ADULTOS", "MULTIVITAMINAS", "PFIZER", "Suplementos / Vitaminas"),
    ("OMEGA 3 NATURAL LIFE", "ACIDOS GRASOS OMEGA 3", "NATURAL LIFE", "Suplementos / Vitaminas"),
    # Higiene femenina
    ("TOALLAS HIGIENICAS ALWAYS COMPACT", "CELULOSA / POLIPROPILENO", "PROCTER & GAMBLE", "Higiene Personal"),
    ("TAMPONES TAMPAX POCKET REGULAR", "ALGODON / VISCOSEA", "PROCTER & GAMBLE", "Higiene Personal"),
    # Otros comunes
    ("PAÑUELOS KLINEX ULTRA SUAVES", "CELULOSA", "KIMBERLY-CLARK", "Higiene Personal"),
    ("GEL ANTIBACTERIANO PURELL", "ETANOL 70%", "GOJO INDUSTRIES", "Higiene Personal"),
    ("CREMA PEINAR DOVE OIL CARE", "DIMETHICONE", "UNILEVER", "Cuidado Capilar"),
    ("MASCARILLA CAPILAR PANTENE 3 MINUTOS", "PANTENOL", "PROCTER & GAMBLE", "Cuidado Capilar"),
    ("SPRAY NASAL FLONASE ALLERGY", "PROPIONATO DE FLUTICASONA", "GLAXOSMITHKLINE", "Descongestionantes"),
]


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: Define DATABASE_URL")
        sys.exit(1)

    conn = psycopg2.connect(url, connect_timeout=30)
    cur = conn.cursor()

    insertados = 0
    duplicados = 0

    for producto, principio, titular, categoria in PRODUCTOS_COMUNES:
        cur.execute(
            "SELECT id FROM invima WHERE producto = %s AND titular = %s AND registro = 'N/A' LIMIT 1",
            (producto, titular),
        )
        if cur.fetchone():
            duplicados += 1
            continue

        cur.execute(
            """INSERT INTO invima (expediente, producto, principio_activo, registro, estado, modalidad, titular, categoria)
               VALUES ('N/A', %s, %s, 'N/A', 'N/A', 'N/A', %s, %s)""",
            (producto, principio, titular, categoria),
        )
        insertados += 1

    conn.commit()
    conn.close()
    print(f"Insertados: {insertados}")
    print(f"Duplicados omitidos: {duplicados}")


if __name__ == "__main__":
    main()
