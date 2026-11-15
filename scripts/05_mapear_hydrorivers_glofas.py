import pandas as pd
import numpy as np

entrada = "data/processed/dataset_hidrologico_global.csv"
saida = "data/processed/mapeamento_hydrorivers_glofas.csv"

LAT_INICIAL = 89.975
LON_INICIAL = -179.975
RESOLUCAO = 0.05

tamanho = 200_000
primeiro = True
celulas = []

# Lê a rede hidrográfica em blocos para reduzir o uso de memória.
for bloco in pd.read_csv(entrada, chunksize=tamanho):

    lat = bloco["lat"].to_numpy()
    lon = bloco["lon"].to_numpy()


# Converte as coordenadas geográficas para índices da grade GloFAS.
    linha = np.rint((LAT_INICIAL - lat) / RESOLUCAO).astype(np.int32)
    coluna = np.rint((lon - LON_INICIAL) / RESOLUCAO).astype(np.int32)

    bloco_saida = pd.DataFrame({"hyriv_id": bloco["hyriv_id"], "row_glofas": linha,"col_glofas": coluna})
    bloco_saida.to_csv(saida, mode="w" if primeiro else "a",header=primeiro,index=False)

    primeiro = False


# Guarda as células associadas aos trechos para identificar as posições únicas.
    celulas.append(
        linha.astype(np.int64) * 7200 + coluna
    )

    print(f"Trechos processados: {sum(len(x) for x in celulas):,}")

celulas_unicas = np.unique(np.concatenate(celulas))

print("\nMAPEAMENTO CONCLUÍDO")
print(f"Trechos mapeados: {sum(len(x) for x in celulas):,}")
print(f"Células GloFAS distintas: {len(celulas_unicas):,}")
print(f"Arquivo: {saida}")
