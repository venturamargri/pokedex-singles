import os
from collections import defaultdict

# 1. Forzamos que los archivos se lean y guarden exactamente donde está este script
CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

eventos_validos = {
    '333', '222', '444', '555', '666', '777', '333bf', '333oh', 
    'clock', 'minx', 'pyram', 'skewb', 'sq1', '444bf', '555bf'
}

# 2. Cargar continentes (País -> Continente)
paises_continentes = {}
ruta_paises = os.path.join(CARPETA_ACTUAL, "WCA_export_Countries.tsv")

try:
    with open(ruta_paises, 'r', encoding='utf-8') as f:
        headers = f.readline().strip('\n').split('\t')
        id_idx = headers.index('id')
        cont_idx = headers.index('continentId')
        for line in f:
            row = line.strip('\n').split('\t')
            if len(row) > max(id_idx, cont_idx):
                paises_continentes[row[id_idx]] = row[cont_idx]
except FileNotFoundError:
    print(f"❌ Error: No se encuentra {ruta_paises}")
    print("Asegúrate de que el archivo .tsv de países está en la misma carpeta.")
    exit()

# 3. Leer los resultados de todos los competidores
# Estructura: data[evento][wca_id] = {'name': nombre, 'country': pais, 'times': set()}
data = defaultdict(lambda: defaultdict(lambda: {'name': '', 'country': '', 'times': set()}))
ruta_resultados = os.path.join(CARPETA_ACTUAL, "WCA_export_Results.tsv")

print("⏳ Leyendo base de datos WCA (Millones de filas, dale unos segundos)...")

try:
    with open(ruta_resultados, 'r', encoding='utf-8') as f:
        headers = f.readline().strip('\n').split('\t')
        ev_idx = headers.index('eventId')
        pid_idx = headers.index('personId')
        pname_idx = headers.index('personName')
        pcountry_idx = headers.index('personCountryId')
        
        # Índices de las columnas que contienen los tiempos
        cols_tiempos = ['value1', 'value2', 'value3', 'value4', 'value5', 'best']
        val_indices = [headers.index(col) for col in cols_tiempos if col in headers]

        for line in f:
            row = line.strip('\n').split('\t')
            # Saltamos líneas corruptas
            if len(row) < len(headers):
                continue
                
            ev = row[ev_idx]
            if ev not in eventos_validos:
                continue
            
            pid = row[pid_idx]
            user_data = data[ev][pid]
            
            if not user_data['name']:
                user_data['name'] = row[pname_idx]
                user_data['country'] = row[pcountry_idx]
                
            # Extraer tiempos que sean mayores de 0 (ignoramos DNF, DNS...)
            for idx in val_indices:
                val_str = row[idx]
                if val_str and val_str not in ('-1', '-2', '0'):
                    try:
                        val = int(val_str)
                        if val > 0:
                            user_data['times'].add(val)
                    except ValueError:
                        pass
except FileNotFoundError:
    print(f"❌ Error: No se encuentra {ruta_resultados}")
    exit()

# 4. Función para calcular el mejor rango (racha)
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
            
    # Comprobar la racha con la que terminamos el bucle
    rango_actual = r_max - r_min
    if rango_actual > mejor_rango:
        mejor_rango = rango_actual
        mejor_min = r_min
        mejor_max = r_max
        
    return mejor_rango, mejor_min, mejor_max

print("📊 Calculando rankings y generando archivos .txt...")

# 5. Generar un archivo .txt por cada evento
for ev in eventos_validos:
    if ev not in data:
        continue
        
    resultados = []
    for pid, udata in data[ev].items():
        rango_cs, min_cs, max_cs = calcular_racha(udata['times'])
        if rango_cs > 0: # Ignoramos a los que tienen rango 0 (solo 1 marca)
            resultados.append((rango_cs, min_cs, max_cs, pid, udata['name'], udata['country']))
            
    # Ordenar: Mayor rango primero. Desempate: Menor tiempo de inicio.
    resultados.sort(key=lambda x: (-x[0], x[1], x[3]))
    
    # Aseguramos que la ruta apunte a la misma carpeta del script
    ruta_archivo = os.path.join(CARPETA_ACTUAL, f"ranking_{ev}.txt")
    
    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        for i, (rango_cs, min_cs, max_cs, pid, name, country) in enumerate(resultados, 1):
            continent = paises_continentes.get(country, "_Unknown")
            
            # Pasamos de centésimas a segundos formateados
            rango_sec = f"{rango_cs / 100:.2f}"
            min_sec = f"{min_cs / 100:.2f}"
            max_sec = f"{max_cs / 100:.2f}"
            
            # Formato exacto que lee tu Javascript:
            f.write(f"{i}. {name} ({pid}. {country}. {continent}) - {rango_sec}s ({min_sec} - {max_sec})\n")

print("✅ ¡Todos los rankings se han guardado con éxito en esta misma carpeta!")