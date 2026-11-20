"""Gera arquivo com bacias inteiras (raiz + subarvore) de varios tamanhos para usar de exemplo no repositório."""
import sys
import numpy as np
import pandas as pd
import os

ENTRADA = sys.argv[1] if len(sys.argv) > 1 else "data/processed/dataset_com_deficit.csv"
SAIDA = sys.argv[2] if len(sys.argv) > 2 else "data/sample/exemplo.csv"

# (tamanho-alvo da bacia, quantas bacias desse tamanho)
ALVOS = [(3000, 1), (300, 3), (30, 5)]
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = -34.0, 6.0, -74.0, -34.0   # Brasil

df = pd.read_csv(ENTRADA)
n = len(df)
ids = df["hyriv_id"].to_numpy(np.int64)
nxt = df["next_down"].to_numpy(np.int64)

# indice do pai (trecho a jusante) de cada no; -1 para as fozes
ordem = np.argsort(ids)
ids_ord = ids[ordem]
pos = np.clip(np.searchsorted(ids_ord, nxt), 0, n - 1)
assert np.all((nxt == 0) | (ids_ord[pos] == nxt)), "next_down aponta para id inexistente"
pai = np.where(nxt == 0, -1, ordem[pos])

# raiz de cada no, por "pulos" (raiz = raiz[raiz] ate estabilizar)
raiz = np.where(pai < 0, np.arange(n), pai)
while True:
    nova = raiz[raiz]
    if np.array_equal(nova, raiz):
        break
    raiz = nova

tamanho = np.bincount(raiz, minlength=n)
raizes = np.flatnonzero(pai < 0)
lat, lon = df["lat"].to_numpy(), df["lon"].to_numpy()
na_caixa = (lat[raizes] >= LAT_MIN) & (lat[raizes] <= LAT_MAX) & \
           (lon[raizes] >= LON_MIN) & (lon[raizes] <= LON_MAX)
candidatas = raizes[na_caixa]
print(f"{len(raizes)} bacias no total, {len(candidatas)} com a raiz na caixa")

escolhidas = []
for alvo, qtd in ALVOS:
    livres = np.setdiff1d(candidatas, escolhidas)
    ordenadas = livres[np.argsort(np.abs(tamanho[livres] - alvo))]
    escolhidas += list(ordenadas[:qtd])

manter = np.isin(raiz, escolhidas)
amostra = df[manter]

# validacao: toda ligacao fica dentro da amostra
ids_amostra = set(amostra["hyriv_id"])
assert all(v == 0 or v in ids_amostra for v in amostra["next_down"]), "amostra incoerente"

os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
amostra.to_csv(SAIDA, index=False)
print(f"{len(amostra)} trechos, {len(escolhidas)} bacias, tamanhos: "
      f"{sorted(int(tamanho[r]) for r in escolhidas)}")
print(f"Escrito em {SAIDA}")