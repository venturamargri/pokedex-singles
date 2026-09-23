import csv
import json
import os
import glob
from collections import defaultdict

EVENTOS_VALIDOS = {'333', '222', '444', '555', '666', '777', '333bf', '333oh', 'clock', 'minx', 'pyram', 'skewb', 'sq1', '444bf', '555bf'}

# ==========================================
# FUNCIÓN PARA ENCONTRAR LOS TSV DINÁMICAMENTE
# ==========================================
def encontrar_archivo(nombre_base):
    patrones = [
        f"WCA_export_{nombre_base}.tsv",
        f"WCA_export_{nombre_base.lower()}.tsv",
        f"{nombre_base}.tsv",
        f"{nombre_base.lower()}.tsv"
    ]
    for p in patrones:
        if os.path.exists(p):
            return p
            
    coincidencias = glob.glob(f"*{nombre_base}*.tsv", recursive=False)
    if coincidencias: return coincidencias[0]
    
    coincidencias_min = glob.glob(f"*{nombre_base.lower()}*.tsv", recursive=False)
    if coincidencias_min: return coincidencias_min[0]
    
    return f"WCA_export_{nombre_base.lower()}.tsv"

def procesar_datos():
    # Asignación dinámica de archivos a prueba de fallos
    COMPETITIONS_FILE = encontrar_archivo("Competitions")
    COUNTRIES_FILE = encontrar_archivo("Countries")
    RESULTS_FILE = encontrar_archivo("Results")

    # 1. Leer competiciones para obtener las fechas
    comps = {}
    print(f"Leyendo competiciones desde {COMPETITIONS_FILE}...")
    with open(COMPETITIONS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            date_str = f"{row['year']}-{row['month'].zfill(2)}-{row['day'].zfill(2)}"
            comps[row['id']] = date_str

    # 2. Leer la tabla de países para cruzar País -> Continente
    paises_continentes = {}
    print(f"Mapeando países a continentes desde {COUNTRIES_FILE}...")
    with open(COUNTRIES_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            paises_continentes[row['id']] = row['continent_id']  # <-- COLUMNA CORREGIDA

    # 3. Leer resultados masivos
    print(f"Procesando resultados masivos desde {RESULTS_FILE}...")
    resultados_brutos = defaultdict(list)
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row['event_id'] not in EVENTOS_VALIDOS: continue  # <-- COLUMNA CORREGIDA
            if int(row['best']) <= 0: continue
            
            wca_id = row['person_id']  # <-- COLUMNA CORREGIDA
            pais = row['person_country_id']  # <-- COLUMNA CORREGIDA
            continente = paises_continentes.get(pais, "Unknown")
            comp_id = row['competition_id']  # <-- COLUMNA CORREGIDA
            fecha = comps.get(comp_id, "9999-99-99")
            best = int(row['best'])
            
            resultados_brutos[row['event_id']].append({
                'time': best, 'wca_id': wca_id, 'pais': pais, 'continente': continente, 
                'comp_id': comp_id, 'fecha': fecha, 'personName': row['person_name']  # <-- COLUMNA CORREGIDA
            })

    # 4. Generar el JSON Colectivo por Evento
    for evento, solves in resultados_brutos.items():
        print(f"Calculando Pokédex y Hall of Fame para {evento}...")
        
        # El secreto: Ordenar cronológicamente todo el evento desde 2003 hasta hoy
        solves.sort(key=lambda x: x['fecha'])
        
        datos_colectivos = {
            'Mundial': {'tiempos': {}, 'hall_of_fame': defaultdict(int)},
            'Continental': defaultdict(lambda: {'tiempos': {}, 'hall_of_fame': defaultdict(int)}),
            'Nacional': defaultdict(lambda: {'tiempos': {}, 'hall_of_fame': defaultdict(int)})
        }
        
        # Detectar a los descubridores
        for s in solves:
            t = s['time']
            p = s['pais']
            c = s['continente']
            persona = f"{s['personName']} ({s['wca_id']})"
            
            # --- MUNDIAL ---
            if t not in datos_colectivos['Mundial']['tiempos']:
                datos_colectivos['Mundial']['tiempos'][t] = {'fecha': s['fecha'], 'descubridores': [persona], 'comps': [s['comp_id']]}
                datos_colectivos['Mundial']['hall_of_fame'][persona] += 1
            elif s['fecha'] == datos_colectivos['Mundial']['tiempos'][t]['fecha']:
                if persona not in datos_colectivos['Mundial']['tiempos'][t]['descubridores']:
                    datos_colectivos['Mundial']['tiempos'][t]['descubridores'].append(persona)
                    datos_colectivos['Mundial']['tiempos'][t]['comps'].append(s['comp_id'])
                    datos_colectivos['Mundial']['hall_of_fame'][persona] += 1
                    
            # --- CONTINENTAL ---
            if t not in datos_colectivos['Continental'][c]['tiempos']:
                datos_colectivos['Continental'][c]['tiempos'][t] = {'fecha': s['fecha'], 'descubridores': [persona], 'comps': [s['comp_id']]}
                datos_colectivos['Continental'][c]['hall_of_fame'][persona] += 1
            elif s['fecha'] == datos_colectivos['Continental'][c]['tiempos'][t]['fecha']:
                if persona not in datos_colectivos['Continental'][c]['tiempos'][t]['descubridores']:
                    datos_colectivos['Continental'][c]['tiempos'][t]['descubridores'].append(persona)
                    datos_colectivos['Continental'][c]['tiempos'][t]['comps'].append(s['comp_id'])
                    datos_colectivos['Continental'][c]['hall_of_fame'][persona] += 1
                    
            # --- NACIONAL ---
            if t not in datos_colectivos['Nacional'][p]['tiempos']:
                datos_colectivos['Nacional'][p]['tiempos'][t] = {'fecha': s['fecha'], 'descubridores': [persona], 'comps': [s['comp_id']]}
                datos_colectivos['Nacional'][p]['hall_of_fame'][persona] += 1
            elif s['fecha'] == datos_colectivos['Nacional'][p]['tiempos'][t]['fecha']:
                if persona not in datos_colectivos['Nacional'][p]['tiempos'][t]['descubridores']:
                    datos_colectivos['Nacional'][p]['tiempos'][t]['descubridores'].append(persona)
                    datos_colectivos['Nacional'][p]['tiempos'][t]['comps'].append(s['comp_id'])
                    datos_colectivos['Nacional'][p]['hall_of_fame'][persona] += 1

        # Limpiar y ordenar el Hall of Fame para que el JSON sea ligero
        datos_colectivos['Mundial']['hall_of_fame'] = dict(sorted(datos_colectivos['Mundial']['hall_of_fame'].items(), key=lambda x: x[1], reverse=True)[:100])
        
        for c_key in datos_colectivos['Continental']:
            datos_colectivos['Continental'][c_key]['hall_of_fame'] = dict(sorted(datos_colectivos['Continental'][c_key]['hall_of_fame'].items(), key=lambda x: x[1], reverse=True)[:50])
            
        for p_key in datos_colectivos['Nacional']:
            datos_colectivos['Nacional'][p_key]['hall_of_fame'] = dict(sorted(datos_colectivos['Nacional'][p_key]['hall_of_fame'].items(), key=lambda x: x[1], reverse=True)[:50])

        # Guardar en la raíz (donde Git lo espera)
        with open(f'collective_{evento}.json', 'w', encoding='utf-8') as f:
            json.dump(datos_colectivos, f)
            
    print("¡Generación completada con éxito!")

if __name__ == "__main__":
    procesar_datos()