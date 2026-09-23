import csv
import json
from collections import defaultdict

EVENTOS_VALIDOS = {'333', '222', '444', '555', '666', '777', '333bf', '333oh', 'clock', 'minx', 'pyram', 'skewb', 'sq1', '444bf', '555bf'}

def procesar_datos():
    # 1. Leer competiciones para obtener las fechas
    comps = {}
    print("Leyendo competiciones...")
    with open('WCA_export_Competitions.tsv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            # Creamos una fecha YYYY-MM-DD ordenable
            date_str = f"{row['year']}-{row['month'].zfill(2)}-{row['day'].zfill(2)}"
            comps[row['id']] = date_str

    # 2. Leer la tabla de países para cruzar País -> Continente
    paises_continentes = {}
    print("Mapeando países a continentes...")
    with open('WCA_export_Countries.tsv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            paises_continentes[row['id']] = row['continentId']

    # 3. Leer resultados masivos
    print("Procesando resultados masivos...")
    resultados_brutos = defaultdict(list)
    with open('WCA_export_Results.tsv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row['eventId'] not in EVENTOS_VALIDOS: continue
            if int(row['best']) <= 0: continue
            
            wca_id = row['personId']
            pais = row['personCountryId']
            continente = paises_continentes.get(pais, "Unknown") # <-- El cruce ocurre aquí
            comp_id = row['competitionId']
            fecha = comps.get(comp_id, "9999-99-99")
            best = int(row['best'])
            
            resultados_brutos[row['eventId']].append({
                'time': best, 'wca_id': wca_id, 'pais': pais, 'continente': continente, 
                'comp_id': comp_id, 'fecha': fecha, 'personName': row['personName']
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

        # Limpiar y ordenar el Hall of Fame para que no pese demasiado el JSON
        datos_colectivos['Mundial']['hall_of_fame'] = dict(sorted(datos_colectivos['Mundial']['hall_of_fame'].items(), key=lambda x: x[1], reverse=True)[:100])
        
        for c_key in datos_colectivos['Continental']:
            datos_colectivos['Continental'][c_key]['hall_of_fame'] = dict(sorted(datos_colectivos['Continental'][c_key]['hall_of_fame'].items(), key=lambda x: x[1], reverse=True)[:50])
            
        for p_key in datos_colectivos['Nacional']:
            datos_colectivos['Nacional'][p_key]['hall_of_fame'] = dict(sorted(datos_colectivos['Nacional'][p_key]['hall_of_fame'].items(), key=lambda x: x[1], reverse=True)[:50])

        # Guardar archivo maestro
        with open(f'collective_{evento}.json', 'w', encoding='utf-8') as f:
            json.dump(datos_colectivos, f)
            
    print("¡Generación completada con éxito!")

if __name__ == "__main__":
    procesar_datos()