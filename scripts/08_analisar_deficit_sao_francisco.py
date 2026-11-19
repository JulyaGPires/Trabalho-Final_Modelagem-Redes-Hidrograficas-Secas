from pathlib import Path
import numpy as np
import pandas as pd

# Arquivos de entrada
arquivo_celulas = Path("data/processed/glofas/celulas_sao_francisco_unicas.csv")
arquivo_deficits = Path("data/processed/glofas/deficits_mensais_por_celula_float32.dat")
arquivo_meses = Path("data/processed/glofas/indice_meses_glofas.csv")

# Arquivo com o resultado da análise
saida = Path("results/deficit_mensal_sao_francisco_2012_2017.csv")
saida.parent.mkdir(parents=True, exist_ok=True)

for arq in [arquivo_celulas, arquivo_deficits, arquivo_meses]:
    if not arq.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {arq}")

# Seleciona as células da região e os meses de janeiro de 2012 a dezembro de 2017
celulas = pd.read_csv(arquivo_celulas)["cell_index"].drop_duplicates().to_numpy(dtype=np.int64)
meses = pd.read_csv(arquivo_meses)
meses = meses[(meses["indice_mes"] >= 144) & (meses["indice_mes"] <= 215)].copy()

if len(meses) != 72:
    raise ValueError(f"Esperados 72 meses na janela 2012-2017, encontrados: {len(meses)}")

if len(celulas) == 0 or celulas.min() < 0 or celulas.max() >= 3_799_864:
    raise ValueError("Índices de células fora dos limites da matriz global.")

print(f"Células da região: {len(celulas):,}")
print("[INFO] Lendo déficits da região via memmap...")

# Acessa a matriz de déficits sem carregar o arquivo inteiro na memória
dados = np.memmap(
    arquivo_deficits,
    dtype="float32",
    mode="r",
    shape=(3_799_864, 252)
)

# Extrai os déficits das células selecionadas para os 72 meses analisados
matriz = np.asarray(dados[celulas, 144:216])

validos = np.isfinite(matriz)
quantidade_validos = validos.sum(axis=0)
somas = np.nansum(matriz, axis=0)

# Evita considerar como zero os meses em que não há dados válidos
somas[quantidade_validos == 0] = np.nan

resultado = pd.DataFrame({
    "ano_mes": meses["ano_mes"].to_numpy(),
    "deficit_agregado": somas,
    "celulas_validas": quantidade_validos,
    "total_celulas": len(celulas),
    "cobertura_percentual": quantidade_validos / len(celulas) * 100
})

resultado.to_csv(saida, index=False)

if resultado["deficit_agregado"].notna().sum() == 0:
    raise ValueError("Não existem dados válidos na série.")

pior = resultado.loc[resultado["deficit_agregado"].idxmax()]

print("\n" + "=" * 50)
print("SECA HISTÓRICA DO SÃO FRANCISCO (2012 - 2017)")
print("=" * 50)
print(f"Janela temporal: {resultado['ano_mes'].iloc[0]} até {resultado['ano_mes'].iloc[-1]}")
print(f"Células analisadas: {len(celulas):,}")
print(f"Pior mês da crise: {pior['ano_mes']}")
print(f"Déficit agregado máximo: {pior['deficit_agregado']:.2f}")
print(f"Cobertura espacial no pico: {pior['cobertura_percentual']:.1f}%")
print(f"\nSérie histórica salva em: {saida}")
print("=" * 50)
