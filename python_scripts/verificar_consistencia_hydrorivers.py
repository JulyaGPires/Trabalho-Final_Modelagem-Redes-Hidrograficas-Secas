import pandas as pd

arquivo = "data/processed/dataset_hidrologico_global.csv"

contagens = {}

colunas = [
    "next_down",
    "dist_dn_km",
    "dis_av_cms",
    "ord_flow",
    "endorheic"
]

for bloco in pd.read_csv(arquivo, usecols=colunas, chunksize=100_000):

    bloco["vazao_zero"] = bloco["dis_av_cms"] == 0
    bloco["classe_10"] = bloco["ord_flow"] == 10
    bloco["terminal"] = bloco["next_down"] == 0
    bloco["distancia_zero"] = bloco["dist_dn_km"] == 0

    verificacoes = {
        "vazao_zero_e_classe_10": bloco["vazao_zero"] & bloco["classe_10"],
        "vazao_zero_sem_classe_10": bloco["vazao_zero"] & ~bloco["classe_10"],
        "classe_10_com_vazao": ~bloco["vazao_zero"] & bloco["classe_10"],
        "terminal_endorreico": bloco["terminal"] & (bloco["endorheic"] == 1),
        "terminal_nao_endorreico": bloco["terminal"] & (bloco["endorheic"] == 0),
        "terminal_distancia_zero": bloco["terminal"] & bloco["distancia_zero"],
        "terminal_distancia_nao_zero": bloco["terminal"] & ~bloco["distancia_zero"]
    }

    for nome, mascara in verificacoes.items():
        contagens[nome] = contagens.get(nome, 0) + int(mascara.sum())

print("\n=== CONSISTÊNCIA DO HYDRORIVERS ===")

for nome, quantidade in contagens.items():
    print(f"{nome}: {quantidade:,}")
