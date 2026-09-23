import urllib.request
import zipfile
import os
import csv
import json
from collections import defaultdict
from datetime import datetime

# Configuracion
URL_WCA = "https://www.worldcubeassociation.org/results/misc/WCA_export.tsv.zip"
ZIP_FILE = "WCA_export.tsv.zip"
EVENTOS_VALIDOS = {'333', '222', '444', '555', '666', '777', '333bf', '333oh', 'clock', 'minx', 'pyram', 'skewb', 'sq1', '444bf', '555bf'}

def descargar_y_extraer():
    print("Descargando base de datos WCA...")
    urllib.request.urlretrieve(URL_WCA, ZIP_FILE)
    print("Extrayendo archivos...")
    with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
        zip_ref.extract('WCA_export_Results.tsv')
        zip_ref.extract('WCA_export_Competitions.tsv')
        zip_ref.extract('WCA_export_Persons.tsv')
    os.remove(ZIP_FILE)

def procesar_datos():
    # 1. Leer competiciones para fechas
    comps = {}
    with open('WCA_export_Competitions.tsv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            # Formato YYYY-MM-DD aproximado (usamos el año/mes/dia de inicio)
            date_str = f"{row['year']}-{row['month'].zfill(2)}-{row['day'].zfill(2)}"
            comps[row['id']] = date_str

    # 2. Leer personas para continente
    personas = {}
    with open('WCA_export_Persons.tsv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row['subid'] == '1':
                personas[row['id']] = row['countryId']

    # Paises a continentes (Simplificado, la WCA usa prefijos o IDs, asumimos mapeo básico por prefijo de countryId si fuera necesario, 
    # pero Results ya tiene personCountryId. Necesitamos mapear pais a continente).
    # Para simplificar en este script, agruparemos Mundial y Nacional. 
    # (Continental requiere un mapeo exacto de los 195 países que puedes añadir luego).
    
    # 3. Leer y ordenar resultados
    print("Procesando resultados...")
    resultados_brutos = defaultdict(list)
    with open('WCA_export_Results.tsv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row['eventId'] not in EVENTOS_VALIDOS: continue
            if int(row['best']) <= 0: continue
            
            wca_id = row['personId']
            pais = row['personCountryId']
            comp_id = row['competitionId']
            fecha = comps.get(comp_id, "9999-99-99")
            best = int(row['best'])
            
            resultados_brutos[row['eventId']].append({
                'time': best, 'wca_id': wca_id, 'pais': pais, 
                'comp_id': comp_id, 'fecha': fecha, 'personName': row['personName']
            })

    # 4. Generar el JSON Colectivo por Evento
    for evento, solves in resultados_brutos.items():
        print(f"Calculando {evento}...")
        # Ordenar cronológicamente todo el evento
        solves.sort(key=lambda x: x['fecha'])
        
        datos_colectivos = {
            'Mundial': {'tiempos': {}, 'hall_of_fame': defaultdict(int)},
            'Nacional': defaultdict(lambda: {'tiempos': {}, 'hall_of_fame': defaultdict(int)})
        }
        
        # Procesar cronológicamente
        for s in solves:
            t = s['time']
            p = s['pais']
            persona = f"{s['personName']} ({s['wca_id']})"
            
            # Chequeo Mundial
            if t not in datos_colectivos['Mundial']['tiempos']:
                datos_colectivos['Mundial']['tiempos'][t] = {'fecha': s['fecha'], 'descubridores': [persona], 'comps': [s['comp_id']]}
                datos_colectivos['Mundial']['hall_of_fame'][persona] += 1
            elif s['fecha'] == datos_colectivos['Mundial']['tiempos'][t]['fecha']:
                if persona not in datos_colectivos['Mundial']['tiempos'][t]['descubridores']:
                    datos_colectivos['Mundial']['tiempos'][t]['descubridores'].append(persona)
                    datos_colectivos['Mundial']['tiempos'][t]['comps'].append(s['comp_id'])
                    datos_colectivos['Mundial']['hall_of_fame'][persona] += 1
                    
            # Chequeo Nacional
            if t not in datos_colectivos['Nacional'][p]['tiempos']:
                datos_colectivos['Nacional'][p]['tiempos'][t] = {'fecha': s['fecha'], 'descubridores': [persona], 'comps': [s['comp_id']]}
                datos_colectivos['Nacional'][p]['hall_of_fame'][persona] += 1
            elif s['fecha'] == datos_colectivos['Nacional'][p]['tiempos'][t]['fecha']:
                if persona not in datos_colectivos['Nacional'][p]['tiempos'][t]['descubridores']:
                    datos_colectivos['Nacional'][p]['tiempos'][t]['descubridores'].append(persona)
                    datos_colectivos['Nacional'][p]['tiempos'][t]['comps'].append(s['comp_id'])
                    datos_colectivos['Nacional'][p]['hall_of_fame'][persona] += 1

        # Limpiar diccionarios para JSON
        for region in ['Mundial']:
            datos_colectivos[region]['hall_of_fame'] = dict(sorted(datos_colectivos[region]['hall_of_fame'].items(), key=lambda x: x[1], reverse=True)[:100])
        for p in datos_colectivos['Nacional']:
            datos_colectivos['Nacional'][p]['hall_of_fame'] = dict(sorted(datos_colectivos['Nacional'][p]['hall_of_fame'].items(), key=lambda x: x[1], reverse=True)[:50])

        with open(f'collective_{evento}.json', 'w', encoding='utf-8') as f:
            json.dump(datos_colectivos, f)

    # Limpieza
    os.remove('WCA_export_Results.tsv')
    os.remove('WCA_export_Competitions.tsv')
    os.remove('WCA_export_Persons.tsv')

if __name__ == "__main__":
    descargar_y_extraer()
    procesar_datos()