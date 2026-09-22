import os
import glob
from collections import defaultdict

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
CARPETA_SUPERIOR = os.path.dirname(CARPETA_ACTUAL)

eventos_validos = {
    '333', '222', '444', '555', '666', '777', '333bf', '333oh', 
    'clock', 'minx', 'pyram', 'skewb', 'sq1', '444bf', '555bf'
}

# 1. Buscar los archivos TSV de forma inteligente
ruta_paises = None
ruta_resultados = None

for base in [CARPETA_ACTUAL, CARPETA_SUPERIOR]:
    p = os.path.join(base, "WCA_export_Countries.tsv")
    r = os.path.join(base, "WCA_export_Results.tsv")
    if os.path.exists(p):
        ruta_paises = p
    if os.path.exists(r):
        ruta_resultados = r

if not ruta_paises or not ruta_resultados:
    print("❌ Error: No se encuentran los archivos TSV de la WCA en la carpeta actual ni en la superior.")
    exit()

# 2. Cargar continentes
paises_continentes = {}
with open(ruta_paises, 'r', encoding='utf-8') as f:
    headers = f.readline().strip('\n').split('\t')
    id_idx = headers.index('id') if 'id' in headers else 0
    cont_idx = None
    for col in ['continentId', 'continent', 'regionId']:
        if col in headers:
            cont_idx = headers.index(col)
            break
            
    for line in f:
        row = line.strip('\n').split('\t')
        if len(row) > id_idx:
            pid = row[id_idx]
            pcont = row[cont_idx] if cont_idx is not None and len(row) > cont_idx else "_Unknown"
            paises_continentes[pid] = pcont

# 3. Leer los resultados
data = defaultdict(lambda: defaultdict(lambda: {'name': '', 'country': '', 'times': set()}))
print("⏳ Leyendo base de datos WCA...")

with open(ruta_resultados, 'r', encoding='utf-8') as f:
    headers = f.readline().strip('\n').split('\t')
    ev_idx = headers.index('eventId') if 'eventId' in headers else headers.index('event_id')
    pid_idx = headers.index('personId') if 'personId' in headers else headers.index('person_id')
    pname_idx = headers.index('personName') if 'personName' in headers else headers.index('person_name')
    pcountry_idx = headers.index('personCountryId') if 'personCountryId' in headers else headers.index('person_country_id')
    
    cols_tiempos = ['value1', 'value2', 'value3', 'value4', 'value5', 'best']
    val_indices = [headers.index(col) for col in cols_tiempos if col in headers]

    for line in f:
        row = line.strip('\n').split('\t')
        if len(row) <= max(ev_idx, pid_idx, pname_idx, pcountry_idx):
            continue
            
        ev = row[ev_idx]
        if ev not in eventos_validos:
            continue
        
        pid = row[pid_idx]
        user_data = data[ev][pid]
        
        if not user_data['name']:
            user_data['name'] = row[pname_idx]
            user_data['country'] = row[pcountry_idx]
            
        for idx in val_indices:
            if idx < len(row):
                val_str = row[idx]
                if val_str and val_str not in (-1, -2, '0', '-1', '-2', '0'):
                    try:
                        val = int(val_str)
                        if val > 0:
                            user_data['times'].add(val)
                    except ValueError:
                        pass

def calcular_racha(tiempos_set):
    if not tiempos_set:
        return 0, 0, 0
    tiempos = sorted(list(tiempos_set))
    mejor_rango = 0
    mejor_min = 0
    mejor_max = 0
    r_min = r_max = tiempos[0]
    
    for i in range(1, len(tiempos)):
        if tiempos[i] == r_max + 1:
            r_max = tiempos[i]
        else:
            rango_actual = r_max - r_min
            if rango_actual > mejor_rango:
                mejor_rango = rango_actual
                mejor_min = r_min
                mejor_max = r_max
            r_min = r_max = tiempos[i]
            
    rango_actual = r_max - r_min
    if rango_actual > mejor_rango:
        mejor_rango = rango_actual
        mejor_min = r_min
        mejor_max = r_max
        
    return mejor_rango, mejor_min, mejor_max

print("📊 Calculando rankings...")

for ev in eventos_validos:
    if ev not in data:
        continue
        
    resultados = []
    for pid, udata in data[ev].items():
        rango_cs, min_cs, max_cs = calcular_racha(udata['times'])
        if rango_cs > 0:
            resultados.append((rango_cs, min_cs, max_cs, pid, udata['name'], udata['country']))
            
    resultados.sort(key=lambda x: (-x[0], x[1], x[3]))
    
    # Guardar directos en la raíz para que tu index.html los lea sin cambiar rutas
    ruta_archivo = os.path.join(CARPETA_ACTUAL, f"ranking_{ev}.txt")
    
    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        for i, (rango_cs, min_cs, max_cs, pid, name, country) in enumerate(resultados, 1):
            continent = paises_continentes.get(country, "_Unknown")
            rango_sec = f"{rango_cs / 100:.2f}"
            min_sec = f"{min_cs / 100:.2f}"
            max_sec = f"{max_cs / 100:.2f}"
            f.write(f"{i}. {name} ({pid}. {country}. {continent}) - {rango_sec}s ({min_sec} - {max_sec})\n")

print("✅ ¡Listo! Archivos de ranking generados correctamente.")
