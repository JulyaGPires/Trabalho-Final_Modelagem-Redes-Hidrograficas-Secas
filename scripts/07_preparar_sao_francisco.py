from pathlib import Path
import geopandas as gpd
import pandas as pd
import shapely
import numpy as np
import time

# Arquivos de entrada
entrada_rios = Path("data/processed/dataset_hidrologico_global.csv")
geopackage = Path("data/input/Regioes_Hidrograficas/regiao_sao_francisco.gpkg")
mapeamento_global = Path("data/processed/glofas/mapeamento_hydrorivers_indices.csv")

# Arquivos de saída
saida_trechos = Path("data/processed/hydrorivers_sao_francisco.csv")
saida_celulas = Path("data/processed/glofas/celulas_sao_francisco_unicas.csv")

for arq in [entrada_rios, geopackage, mapeamento_global]:
    if not arq.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {arq}")

# Carrega o limite da região hidrográfica
print("[INFO] Carregando limite da região do São Francisco...")
regiao = gpd.read_file(geopackage).to_crs("EPSG:4326")
poligono = regiao.geometry.union_all()
shapely.prepare(poligono)
minx, miny, maxx, maxy = poligono.bounds

# Seleciona os trechos do HydroRIVERS localizados na região
print("[INFO] Filtrando trechos do HydroRIVERS na região...")
if saida_trechos.exists():
    saida_trechos.unlink()

total_trechos = 0
inicio = time.time()
primeiro = True
ids_regiao = set()

for bloco in pd.read_csv(entrada_rios, chunksize=500_000):
    lon = bloco["lon"].to_numpy()
    lat = bloco["lat"].to_numpy()

    # Usa os limites do polígono para reduzir os pontos que precisam ser testados
    na_caixa = (lon >= minx) & (lon <= maxx) & (lat >= miny) & (lat <= maxy)
    if not np.any(na_caixa):
        continue

    candidatos = bloco.loc[na_caixa]
    dentro = shapely.contains_xy(
        poligono,
        candidatos["lon"].to_numpy(),
        candidatos["lat"].to_numpy()
    )

    selecionados = candidatos.loc[dentro]
    if not selecionados.empty:
        selecionados.to_csv(
            saida_trechos,
            mode="a",
            index=False,
            header=primeiro
        )
        primeiro = False
        ids_regiao.update(selecionados["hyriv_id"])
        total_trechos += len(selecionados)

print(f"Trechos encontrados na região: {total_trechos:,}")

# Identifica as células GloFAS associadas aos trechos selecionados
print("[INFO] Mapeando células GloFAS correspondentes...")
celulas = set()
ids_com_celula = set()

for bloco in pd.read_csv(mapeamento_global, usecols=["hyriv_id", "cell_index"], chunksize=500_000):
    encontrados = bloco[bloco["hyriv_id"].isin(ids_regiao)].copy()
    if encontrados.empty:
        continue

    encontrados["cell_index"] = pd.to_numeric(encontrados["cell_index"], errors="coerce")
    encontrados = encontrados.dropna(subset=["cell_index"])
    encontrados["cell_index"] = encontrados["cell_index"].astype("int64")

    ids_com_celula.update(encontrados["hyriv_id"])
    celulas.update(encontrados["cell_index"])

# Salva os índices das células GloFAS sem duplicações
pd.DataFrame({"cell_index": sorted(celulas)}).to_csv(saida_celulas, index=False)

tempo = time.time() - inicio
print("\n" + "=" * 50)
print(f"Região preparada com sucesso em {tempo:.1f}s!")
print(f"Trechos HydroRIVERS: {total_trechos:,}")
print(f"Trechos com célula GloFAS: {len(ids_com_celula):,}")
print(f"Trechos sem mapeamento: {len(ids_regiao - ids_com_celula):,}")
print(f"Células GloFAS únicas: {len(celulas):,}")
print(f"Arquivos gerados:")
print(f"  - {saida_trechos}")
print(f"  - {saida_celulas}")
print("=" * 50)
