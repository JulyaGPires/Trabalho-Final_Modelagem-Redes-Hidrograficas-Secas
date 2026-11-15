import pandas as pd
import numpy as np
from pathlib import Path

arquivo = Path("data/processed/dataset_hidrologico_global.csv")
pasta_resultados = Path("results")
pasta_resultados.mkdir(exist_ok=True)

tamanho_bloco = 100_000

estatisticas = {}
frequencias = {"endorheic": {}, "ord_stra": {}, "ord_clas": {}, "ord_flow": {}}

total_linhas = 0
colunas_arquivo = None

print("[INFO] Iniciando auditoria do HydroRIVERS global...")

for bloco in pd.read_csv(arquivo, chunksize=tamanho_bloco):
    total_linhas += len(bloco)

    if colunas_arquivo is None:
        colunas_arquivo = list(bloco.columns)

        print("\n[COLUNAS]")
        print(colunas_arquivo)

        for coluna in colunas_arquivo:
            estatisticas[coluna] = {"nulos": 0,"zeros": 0, "negativos": 0,"nao_finitos": 0,"minimo": float("inf"),"maximo": float("-inf")}

    for coluna in colunas_arquivo:
        valores = pd.to_numeric(bloco[coluna], errors="coerce")

        stats = estatisticas[coluna]

        stats["nulos"] += int(valores.isna().sum())

        validos = valores.dropna()
        finitos = validos[np.isfinite(validos)]

        stats["nao_finitos"] += len(validos) - len(finitos)
        stats["zeros"] += int((finitos == 0).sum())
        stats["negativos"] += int((finitos < 0).sum())

        if len(finitos):
            stats["minimo"] = min(stats["minimo"], finitos.min())
            stats["maximo"] = max(stats["maximo"], finitos.max())

    for coluna in frequencias:
        contagem = bloco[coluna].value_counts(dropna=False)

        for valor, quantidade in contagem.items():
            valor = str(valor)
            frequencias[coluna][valor] = (frequencias[coluna].get(valor, 0) + int(quantidade))

    if total_linhas % 500_000 < tamanho_bloco:
        print(f"[INFO] Linhas analisadas: {total_linhas:,}")

print("\n[RESULTADO]")
print(f"Total de registros: {total_linhas:,}")

linhas_relatorio = []

for coluna, stats in estatisticas.items():
    minimo = stats["minimo"]
    maximo = stats["maximo"]

    if minimo == float("inf"):
        minimo = None
        maximo = None

    linhas_relatorio.append({"atributo": coluna,"nulos": stats["nulos"],"zeros": stats["zeros"],"negativos": stats["negativos"],"nao_finitos": stats["nao_finitos"], "minimo": minimo,"maximo": maximo})

relatorio = pd.DataFrame(linhas_relatorio)

saida_csv = pasta_resultados / "auditoria_atributos_hydrorivers.csv"
relatorio.to_csv(saida_csv, index=False)

saida_txt = pasta_resultados / "frequencias_hydrorivers.txt"

with open(saida_txt, "w", encoding="utf-8") as arquivo_txt:
    for coluna, contagem in frequencias.items():
        arquivo_txt.write(f"\n{coluna.upper()}\n")

        for valor, quantidade in sorted( contagem.items(), key=lambda item: item[1],reverse=True)[:20]:
            arquivo_txt.write(f"{valor}: {quantidade:,}\n")

print(f"\nRelatório numérico: {saida_csv}")
print(f"Frequências: {saida_txt}")
print("\n[INFO] Auditoria concluída.")
