import csv
import json
import os
import glob
from collections import defaultdict

EVENTOS_VALIDOS = {'333', '222', '444', '555', '666', '777', '333bf', '333oh', 'clock', 'minx', 'pyram', 'skewb', 'sq1', '444bf', '555bf'}

def encontrar_archivo(nombre_base):
    patrones = [
        f"WCA_export_{nombre_base}.tsv",
        f"WCA_export_{nombre_base.lower()}.tsv",
        f"{nombre_base}.tsv",
        f"{nombre_base.lower()}.tsv"
    ]
    for p in patrones:
        if os.path.exists(p): return p
    coincidencias = glob.glob(f"*{nombre_base}*.tsv", recursive=False)
    if coincidencias: return coincidencias[0]
    coincidencias_min = glob.glob(f"*{nombre_base.lower()}*.tsv", recursive=False)
    if coincidencias_min: return coincidencias_min[0]
    return f"WCA_export_{nombre_base.lower()}.tsv"

def procesar_datos():
    COMPETITIONS_FILE = encontrar_archivo("Competitions")
    COUNTRIES_FILE = encontrar_archivo("Countries")
    RESULTS_FILE = encontrar_archivo("Results")
    ATTEMPTS_FILE = encontrar_archivo("result_attempts") or encontrar_archivo("ResultAttempts")

    comps = {}
    print("Leyendo competiciones...")
    with open(COMPETITIONS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            date_str = f"{row['year']}-{row['month'].zfill(2)}-{row['day'].zfill(2)}"
            comps[row['id']] = date_str

    paises_continentes = {}
    print("Mapeando continentes...")
    with open(COUNTRIES_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            paises_continentes[row['id']] = row['continent_id']

    print("Procesando tabla principal de Results...")
    resultados_brutos = defaultdict(list)
    result_info = {}
    
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            ev = row['event_id']
            if ev not in EVENTOS_VALIDOS: continue
            
            res_id = row['id']
            wca_id = row['person_id']
            pais = row['person_country_id']
            continente = paises_continentes.get(pais, "Unknown")
            comp_id = row['competition_id']
            fecha = comps.get(comp_id, "9999-99-99")
            pname = row['person_name']
            
            # Memoria optimizada: Guardamos los datos estructurales del resultado
            result_info[res_id] = (ev, wca_id, pais, continente, comp_id, fecha, pname)
            
            # Rescatar el 'best' oficial por si acaso
            b = int(row.get('best', '0'))
            if b > 0:
                resultados_brutos[ev].append({
                    'time': b, 'wca_id': wca_id, 'pais': pais, 'continente': continente, 
                    'comp_id': comp_id, 'fecha': fecha, 'personName': pname
                })

    # --- LA CLAVE MAESTRA: LEER LA TABLA DE INTENTOS ---
    if ATTEMPTS_FILE and os.path.exists(ATTEMPTS_FILE):
        print(f"Procesando tabla secundaria de Intentos ({ATTEMPTS_FILE})...")
        with open(ATTEMPTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                res_id = row['result_id']
                # Cruzamos el intento con la información del competidor y torneo
                if res_id in result_info:
                    val = row.get('value', '0')
                    if val.lstrip('-').isdigit():
                        v = int(val)
                        if v > 0:
                            info = result_info[res_id]
                            resultados_brutos[info[0]].append({
                                'time': v, 'wca_id': info[1], 'pais': info[2], 'continente': info[3],
                                'comp_id': info[4], 'fecha': info[5], 'personName': info[6]
                            })
    else:
        print("AVISO: No se encontró la tabla result_attempts. Faltarán tiempos.")

    # Liberar la RAM 
    result_info.clear()

    for evento, solves in resultados_brutos.items():
        print(f"Calculando {evento}...")
        solves.sort(key=lambda x: x['fecha'])
        
        datos_colectivos = {
            'Metadata': {'paises_continentes': paises_continentes},
            'Mundial': {'tiempos': {}, 'hall_of_fame_individuals': defaultdict(int), 'hall_of_fame_countries': defaultdict(int), 'hall_of_fame_continents': defaultdict(int)},
            'Continental': defaultdict(lambda: {'tiempos': {}, 'hall_of_fame_individuals': defaultdict(int), 'hall_of_fame_countries': defaultdict(int)}),
            'Nacional': defaultdict(lambda: {'tiempos': {}, 'hall_of_fame_individuals': defaultdict(int)})
        }
        
        for s in solves:
            t = s['time']
            p = s['pais']
            c = s['continente']
            persona = f"{s['personName']} ({s['wca_id']})"
            
            # --- MUNDIAL ---
            if t not in datos_colectivos['Mundial']['tiempos']:
                datos_colectivos['Mundial']['tiempos'][t] = {'fecha': s['fecha'], 'descubridores': [persona], 'comps': [s['comp_id']]}
                datos_colectivos['Mundial']['hall_of_fame_individuals'][persona] += 1
                datos_colectivos['Mundial']['hall_of_fame_countries'][p] += 1
                datos_colectivos['Mundial']['hall_of_fame_continents'][c] += 1
            elif s['fecha'] == datos_colectivos['Mundial']['tiempos'][t]['fecha'] and persona not in datos_colectivos['Mundial']['tiempos'][t]['descubridores']:
                datos_colectivos['Mundial']['tiempos'][t]['descubridores'].append(persona)
                datos_colectivos['Mundial']['tiempos'][t]['comps'].append(s['comp_id'])
                datos_colectivos['Mundial']['hall_of_fame_individuals'][persona] += 1
                datos_colectivos['Mundial']['hall_of_fame_countries'][p] += 1
                datos_colectivos['Mundial']['hall_of_fame_continents'][c] += 1
                    
            # --- CONTINENTAL ---
            if t not in datos_colectivos['Continental'][c]['tiempos']:
                datos_colectivos['Continental'][c]['tiempos'][t] = {'fecha': s['fecha'], 'descubridores': [persona], 'comps': [s['comp_id']]}
                datos_colectivos['Continental'][c]['hall_of_fame_individuals'][persona] += 1
                datos_colectivos['Continental'][c]['hall_of_fame_countries'][p] += 1
            elif s['fecha'] == datos_colectivos['Continental'][c]['tiempos'][t]['fecha'] and persona not in datos_colectivos['Continental'][c]['tiempos'][t]['descubridores']:
                datos_colectivos['Continental'][c]['tiempos'][t]['descubridores'].append(persona)
                datos_colectivos['Continental'][c]['tiempos'][t]['comps'].append(s['comp_id'])
                datos_colectivos['Continental'][c]['hall_of_fame_individuals'][persona] += 1
                datos_colectivos['Continental'][c]['hall_of_fame_countries'][p] += 1
                    
            # --- NACIONAL ---
            if t not in datos_colectivos['Nacional'][p]['tiempos']:
                datos_colectivos['Nacional'][p]['tiempos'][t] = {'fecha': s['fecha'], 'descubridores': [persona], 'comps': [s['comp_id']]}
                datos_colectivos['Nacional'][p]['hall_of_fame_individuals'][persona] += 1
            elif s['fecha'] == datos_colectivos['Nacional'][p]['tiempos'][t]['fecha'] and persona not in datos_colectivos['Nacional'][p]['tiempos'][t]['descubridores']:
                datos_colectivos['Nacional'][p]['tiempos'][t]['descubridores'].append(persona)
                datos_colectivos['Nacional'][p]['tiempos'][t]['comps'].append(s['comp_id'])
                datos_colectivos['Nacional'][p]['hall_of_fame_individuals'][persona] += 1

        # Sin límites restrictivos para el Hall of Fame
        datos_colectivos['Mundial']['hall_of_fame_individuals'] = dict(sorted(datos_colectivos['Mundial']['hall_of_fame_individuals'].items(), key=lambda x: x[1], reverse=True))
        datos_colectivos['Mundial']['hall_of_fame_countries'] = dict(sorted(datos_colectivos['Mundial']['hall_of_fame_countries'].items(), key=lambda x: x[1], reverse=True))
        datos_colectivos['Mundial']['hall_of_fame_continents'] = dict(sorted(datos_colectivos['Mundial']['hall_of_fame_continents'].items(), key=lambda x: x[1], reverse=True))
        
        for c_key in datos_colectivos['Continental']:
            datos_colectivos['Continental'][c_key]['hall_of_fame_individuals'] = dict(sorted(datos_colectivos['Continental'][c_key]['hall_of_fame_individuals'].items(), key=lambda x: x[1], reverse=True))
            datos_colectivos['Continental'][c_key]['hall_of_fame_countries'] = dict(sorted(datos_colectivos['Continental'][c_key]['hall_of_fame_countries'].items(), key=lambda x: x[1], reverse=True))
            
        for p_key in datos_colectivos['Nacional']:
            datos_colectivos['Nacional'][p_key]['hall_of_fame_individuals'] = dict(sorted(datos_colectivos['Nacional'][p_key]['hall_of_fame_individuals'].items(), key=lambda x: x[1], reverse=True))

        with open(f'collective_{evento}.json', 'w', encoding='utf-8') as f:
            json.dump(datos_colectivos, f)
            
    print("¡Completado!")

if __name__ == "__main__":
    procesar_datos()