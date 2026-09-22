import os
import glob
import csv
import sys
from collections import defaultdict


# ============================================================
# CONFIGURACIÓN
# ============================================================

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

eventos_validos = {
    '333',
    '222',
    '444',
    '555',
    '666',
    '777',
    '333bf',
    '333oh',
    'clock',
    'minx',
    'pyram',
    'skewb',
    'sq1',
    '444bf',
    '555bf',
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def buscar_tsv(nombre_tabla):
    """
    Busca un TSV de la exportación WCA v2 sin depender
    del número/fecha exactos del archivo.

    Ejemplos:
        *_Persons.tsv
        *_Results.tsv
        *_ResultAttempts.tsv
        *_Countries.tsv
        *_Continents.tsv
    """

    patrones = [
        os.path.join(CARPETA_ACTUAL, f"*_{nombre_tabla}.tsv"),
        os.path.join(CARPETA_ACTUAL, f"*_{nombre_tabla.lower()}.tsv"),
    ]

    encontrados = []

    for patron in patrones:
        encontrados.extend(glob.glob(patron))

    # Eliminar duplicados
    encontrados = list(dict.fromkeys(encontrados))

    if not encontrados:
        return None

    # Si hubiera más de uno, usar el más reciente
    encontrados.sort(key=os.path.getmtime, reverse=True)

    return encontrados[0]


def leer_tsv(ruta):
    """
    Generador que lee un TSV utilizando csv.DictReader.
    """
    with open(ruta, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')

        if reader.fieldnames is None:
            raise RuntimeError(f"El archivo {ruta} no tiene cabecera TSV.")

        yield from reader


def calcular_racha(tiempos_set):
    """
    Busca la mayor secuencia de valores consecutivos
    en centésimas de segundo.

    Ejemplo:
        1234, 1235, 1236, 1240

    produce:
        rango = 2
        mínimo = 1234
        máximo = 1236

    porque 1236 - 1234 = 2.
    """

    if not tiempos_set:
        return 0, 0, 0

    tiempos = sorted(tiempos_set)

    mejor_rango = 0
    mejor_min = 0
    mejor_max = 0

    r_min = tiempos[0]
    r_max = tiempos[0]

    for tiempo in tiempos[1:]:

        if tiempo == r_max + 1:
            r_max = tiempo

        else:
            rango_actual = r_max - r_min

            if rango_actual > mejor_rango:
                mejor_rango = rango_actual
                mejor_min = r_min
                mejor_max = r_max

            r_min = tiempo
            r_max = tiempo

    # Comprobar la última racha
    rango_actual = r_max - r_min

    if rango_actual > mejor_rango:
        mejor_rango = rango_actual
        mejor_min = r_min
        mejor_max = r_max

    return mejor_rango, mejor_min, mejor_max


# ============================================================
# 1. LOCALIZAR LOS TSV
# ============================================================

print("🔎 Buscando archivos TSV de la WCA...")

ruta_personas = buscar_tsv("Persons")
ruta_resultados = buscar_tsv("Results")
ruta_intentos = buscar_tsv("result_attempts")
ruta_paises = buscar_tsv("Countries")
ruta_continentes = buscar_tsv("Continents")

print()

print(f"Persons:        {ruta_personas}")
print(f"Results:        {ruta_resultados}")
print(f"ResultAttempts: {ruta_intentos}")
print(f"Countries:      {ruta_paises}")
print(f"Continents:     {ruta_continentes}")

print()


archivos_obligatorios = {
    "Persons": ruta_personas,
    "Results": ruta_resultados,
    "ResultAttempts": ruta_intentos,
    "Countries": ruta_paises,
}

faltan = [
    nombre
    for nombre, ruta in archivos_obligatorios.items()
    if ruta is None
]

if faltan:
    print("❌ ERROR: faltan archivos TSV obligatorios:")
    for nombre in faltan:
        print(f"   - {nombre}")

    print()
    print("Archivos TSV encontrados realmente:")

    for archivo in glob.glob(os.path.join(CARPETA_ACTUAL, "*.tsv")):
        print(f"   {os.path.basename(archivo)}")

    sys.exit(1)


# ============================================================
# 2. CARGAR PERSONAS
# ============================================================

print("👤 Cargando personas...")

personas = {}

for row in leer_tsv(ruta_personas):

    person_id = row.get("id")

    if not person_id:
        continue

    personas[person_id] = {
        "wca_id": row.get("wca_id", ""),
        "name": row.get("name", ""),
        "country_id": row.get("country_id", ""),
    }

print(f"   Personas cargadas: {len(personas):,}")


# ============================================================
# 3. CARGAR PAÍSES Y CONTINENTES
# ============================================================

print("🌍 Cargando países y continentes...")

continentes = {}

if ruta_continentes:

    for row in leer_tsv(ruta_continentes):

        continent_id = row.get("id")

        if continent_id:
            continentes[continent_id] = row.get(
                "name",
                continent_id
            )

print(f"   Continentes: {len(continentes):,}")


paises = {}

for row in leer_tsv(ruta_paises):

    country_id = row.get("id")

    if not country_id:
        continue

    paises[country_id] = {
        "iso2": row.get("iso2", ""),
        "continent_id": row.get("continent_id", ""),
        "name": row.get("name", ""),
    }

print(f"   Países: {len(paises):,}")


# ============================================================
# 4. LEER RESULTS
# ============================================================
#
# En WCA Export v2:
#
# results.id
# results.event_id
# results.person_id
#
# Los intentos individuales YA NO están aquí.
# Están en result_attempts.
#
# Guardamos:
#
# result_id -> (event_id, person_id)
#
# ============================================================

print()
print("📊 Indexando resultados WCA...")

result_index = {}

contador = 0

for row in leer_tsv(ruta_resultados):

    contador += 1

    result_id = row.get("id")
    event_id = row.get("event_id")
    person_id = row.get("person_id")

    if not result_id or not event_id or not person_id:
        continue

    if event_id not in eventos_validos:
        continue

    result_index[result_id] = (
        event_id,
        person_id
    )

    if contador % 1_000_000 == 0:
        print(
            f"   Resultados procesados: "
            f"{contador:,}"
        )


print(
    f"   Resultados relevantes indexados: "
    f"{len(result_index):,}"
)


# ============================================================
# 5. LEER RESULT_ATTEMPTS
# ============================================================
#
# Cada intento contiene:
#
# result_id
# value
# attempt_number
#
# ============================================================

print()
print("⏱️ Leyendo intentos individuales...")
print("   Esto puede tardar varios minutos.")


# data[evento][persona] = set de tiempos
data = defaultdict(
    lambda: defaultdict(set)
)

contador_intentos = 0
contador_validos = 0

for row in leer_tsv(ruta_intentos):

    contador_intentos += 1

    result_id = row.get("result_id")

    if not result_id:
        continue

    info_resultado = result_index.get(result_id)

    if info_resultado is None:
        continue

    event_id, person_id = info_resultado

    value_str = row.get("value")

    if not value_str:
        continue

    try:
        value = int(value_str)
    except ValueError:
        continue

    # -1 = DNF
    # -2 = DNS
    #  0 = sin resultado
    if value <= 0:
        continue

    # Solo trabajamos con eventos de tiempo.
    if event_id not in eventos_validos:
        continue

    data[event_id][person_id].add(value)

    contador_validos += 1

    if contador_intentos % 1_000_000 == 0:
        print(
            f"   Intentos procesados: "
            f"{contador_intentos:,}"
        )


print()
print(
    f"   Intentos procesados: "
    f"{contador_intentos:,}"
)

print(
    f"   Intentos válidos utilizados: "
    f"{contador_validos:,}"
)


# ============================================================
# 6. CALCULAR Y GENERAR RANKINGS
# ============================================================

print()
print("🏆 Calculando rankings...")


total_archivos = 0

for event_id in sorted(eventos_validos):

    if event_id not in data:
        print(
            f"   ⚠️ {event_id}: "
            f"sin resultados"
        )
        continue

    resultados = []

    for person_id, tiempos in data[event_id].items():

        rango_cs, min_cs, max_cs = calcular_racha(
            tiempos
        )

        # Solo incluimos personas que tengan
        # al menos dos valores consecutivos.
        if rango_cs <= 0:
            continue

        persona = personas.get(
            person_id,
            {}
        )

        nombre = persona.get(
            "name",
            "Desconocido"
        )

        wca_id = persona.get(
            "wca_id",
            person_id
        )

        country_id = persona.get(
            "country_id",
            ""
        )

        pais = paises.get(
            country_id,
            {}
        )

        iso2 = pais.get(
            "iso2",
            country_id
        )

        continent_id = pais.get(
            "continent_id",
            ""
        )

        continente = continentes.get(
            continent_id,
            "_Unknown"
        )

        resultados.append(
            (
                rango_cs,
                min_cs,
                max_cs,
                wca_id,
                nombre,
                iso2,
                continente
            )
        )

    # Orden:
    # 1. Mayor rango
    # 2. Menor tiempo inicial
    # 3. WCA ID
    resultados.sort(
        key=lambda x: (
            -x[0],
            x[1],
            x[3]
        )
    )

    ruta_archivo = os.path.join(
        CARPETA_ACTUAL,
        f"ranking_{event_id}.txt"
    )

    with open(
        ruta_archivo,
        "w",
        encoding="utf-8"
    ) as f:

        for posicion, resultado in enumerate(
            resultados,
            1
        ):

            (
                rango_cs,
                min_cs,
                max_cs,
                wca_id,
                nombre,
                iso2,
                continente
            ) = resultado

            rango_sec = rango_cs / 100
            min_sec = min_cs / 100
            max_sec = max_cs / 100

            f.write(
                f"{posicion}. "
                f"{nombre} "
                f"({wca_id}. {iso2}. {continente}) "
                f"- {rango_sec:.2f}s "
                f"({min_sec:.2f} - {max_sec:.2f})\n"
            )

    total_archivos += 1

    print(
        f"   ✅ {event_id}: "
        f"{len(resultados):,} participantes "
        f"-> ranking_{event_id}.txt"
    )


# ============================================================
# 7. COMPROBACIÓN FINAL
# ============================================================

print()

if total_archivos == 0:
    print(
        "❌ ERROR: no se ha generado ningún "
        "archivo de ranking."
    )
    sys.exit(1)

print(
    f"🎉 ¡Listo! Se han generado "
    f"{total_archivos} archivos de ranking."
)

print()
print("Archivos generados:")

for archivo in sorted(
    glob.glob(
        os.path.join(
            CARPETA_ACTUAL,
            "ranking_*.txt"
        )
    )
):
    tamaño = os.path.getsize(archivo)

    print(
        f"   {os.path.basename(archivo)} "
        f"({tamaño:,} bytes)"
    )
