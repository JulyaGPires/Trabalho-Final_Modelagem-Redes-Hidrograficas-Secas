import xarray as xr
import pandas as pd
from pathlib import Path

arquivo_nc = Path("data/input/data_0.nc")

arquivo_mapa = "data/processed/mapeamento_hydrorivers_glofas.csv"
arquivo_saida = "data/processed/hydrorivers_glofas_2016-11-02.csv"

indice_data = 0

print("Abrindo GloFAS...")

with xr.open_dataset(arquivo_nc) as ds:

    data = pd.Timestamp(ds.valid_time.values[indice_data])

    print("Data selecionada:", data)

    print("Carregando mapa de vazão...")

    raster = ds["avg_dis"].isel( valid_time=indice_data).values

    print("Dimensões do raster:", raster.shape)

    primeiro = True
    total = 0

    for bloco in pd.read_csv(arquivo_mapa, chunksize=200_000):

        linhas = bloco["row_glofas"].to_numpy()
        colunas = bloco["col_glofas"].to_numpy()

        vazoes = raster[linhas, colunas]

        resultado = pd.DataFrame({ "hyriv_id": bloco["hyriv_id"], "data": data,"avg_dis_m3_s": vazoes})

        resultado.to_csv(
            arquivo_saida,
            mode="w" if primeiro else "a",
            header=primeiro,
            index=False
        )

        primeiro = False
        total += len(bloco)

        print(f"Trechos integrados: {total:,}")

print("\nINTEGRAÇÃO CONCLUÍDA")
print("Total de trechos:", total)
print("Arquivo:", arquivo_saida)
