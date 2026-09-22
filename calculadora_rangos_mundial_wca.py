import polars as pl
import time
import os
import glob

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
    # Fallback con glob por si hay variaciones
    coincidencias = glob.glob(f"*{nombre_base}*.tsv", recursive=False)
    if coincidencias: return coincidencias[0]
    coincidencias_min = glob.glob(f"*{nombre_base.lower()}*.tsv", recursive=False)
    if coincidencias_min: return coincidencias_min[0]
    return f"WCA_export_{nombre_base.lower()}.tsv"

RESULTS_FILE = encontrar_archivo("Results")
ATTEMPTS_FILE = encontrar_archivo("result_attempts") or encontrar_archivo("ResultAttempts")
COUNTRIES_FILE = encontrar_archivo("Countries")

# 🚨 CAMBIO PARA GITHUB ACTIONS: Guardamos en la raíz ('.') para que Git los vea
CARPETA_SALIDA = '.'
EVENTOS = ['333', '222', '444', '555', '666', '777', '333bf', '333oh', 'clock', 'minx', 'pyram', 'skewb', 'sq1', '444bf', '555bf']

def main():
    start_time = time.time()
    
    print(f"Archivos detectados:\n- {RESULTS_FILE}\n- {ATTEMPTS_FILE}\n- {COUNTRIES_FILE}")
    print("Cargando intentos y países...")
    
    attempts_df = (
        pl.scan_csv(ATTEMPTS_FILE, separator='\t', ignore_errors=True)
        .filter(pl.col('value') > 0)
        .select(['result_id', 'value'])
    ).collect()

    # Cargamos el archivo de países usando continent_id
    countries_df = pl.scan_csv(COUNTRIES_FILE, separator='\t', ignore_errors=True).select(['id', 'continent_id']).collect()

    for evento in EVENTOS:
        print(f"Procesando {evento.upper()}...")
        archivo_salida = os.path.join(CARPETA_SALIDA, f'ranking_{evento}.txt')
        
        results_lazy = (
            pl.scan_csv(RESULTS_FILE, separator='\t', ignore_errors=True)
            .filter(pl.col('event_id') == evento)
            .select(['id', 'person_name', 'person_id', 'person_country_id'])
        )
        
        df_joined = results_lazy.join(attempts_df.lazy(), left_on='id', right_on='result_id').collect()
        if df_joined.height == 0: continue

        df_unique = df_joined.unique(subset=['person_id', 'value']).sort(['person_id', 'value'])
        
        # Antirrango absoluto
        df_abs = df_unique.group_by('person_id').agg(
            min_abs = pl.col('value').min(),
            max_abs = pl.col('value').max()
        ).with_columns(antirrango = pl.col('max_abs') - pl.col('min_abs'))

        df_grouped = df_unique.with_columns(grupo = pl.col('value') - pl.int_range(0, pl.len()).over('person_id'))
        
        # Unimos con países para obtener el continent_id
        df_grouped = df_grouped.join(countries_df, left_on='person_country_id', right_on='id', how='left')
        
        df_streaks = df_grouped.group_by(['person_id', 'person_name', 'person_country_id', 'continent_id', 'grupo']).agg(
            min_val = pl.col('value').min(),
            max_val = pl.col('value').max()
        )
        
        df_streaks = df_streaks.with_columns(rango = pl.col('max_val') - pl.col('min_val'))
        df_streaks = df_streaks.filter(pl.col('rango') > 0)
        
        ranking = df_streaks.sort('rango', descending=True).group_by('person_id', maintain_order=True).first()
        
        ranking = ranking.join(df_abs, on='person_id', how='left')
        ranking = ranking.sort('rango', descending=True)
        
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            # Cabecera
            f.write(f"--- RANKING COMPLETO: MAYOR RANGO CONSECUTIVO EN {evento.upper()} ---\n\n")
            
            current_rank = 1
            last_rango = -1
            
            for i, row in enumerate(ranking.iter_rows(named=True), 1):
                if row['rango'] != last_rango:
                    current_rank = i
                    last_rango = row['rango']
                    
                # Inyectamos el continente: (2014LOPE04. Spain. _Europe)
                f.write(f"{current_rank}. {row['person_name']} ({row['person_id']}. {row['person_country_id']}. {row['continent_id']}) - {row['rango']/100:.2f}s ({row['min_val']/100:.2f}-{row['max_val']/100:.2f}) | AR: {row['antirrango']/100:.2f}s\n")

    print(f"\nProceso completado en {time.time() - start_time:.2f} segundos.")

if __name__ == '__main__':
    main()
