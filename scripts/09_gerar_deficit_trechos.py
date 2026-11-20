"""
PROBLEMA DAS CELULAS REPETIDAS
  Varios trechos caem na mesma celula do GloFAS (0,05 graus). Se cada trecho
  herdasse o valor inteiro da celula, a soma de uma bacia contaria a mesma
  celula varias vezes.

  Solucao adotada: o valor de cada celula e DISTRIBUIDO entre os trechos que
  caem nela, de modo que a soma dos pesos dos trechos de uma celula e igual
  ao valor da celula (cada celula entra uma vez no total).

    --regra comprimento (padrao): fracao de cada trecho = length_km do trecho
                                  / soma dos length_km dos trechos da celula
    --regra igual               : fracao = 1 / (numero de trechos da celula)

  Se todos os trechos de uma celula tiverem comprimento 0, a divisao é igual.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- parametros
N_CELULAS_PADRAO = 3_799_864
N_MESES = 252
MES_INI = 144          # jan/2012 (indice na matriz)
MES_FIM = 216          # dez/2017 e o 215; o fim e exclusivo
N_MESES_SECA = MES_FIM - MES_INI   # 72


def achar_coluna(colunas, candidatos):
    """Devolve o nome real da coluna que bate com algum candidato (sem diferenciar maiuscula)."""
    mapa = {c.lower(): c for c in colunas}
    for cand in candidatos:
        if cand.lower() in mapa:
            return mapa[cand.lower()]
    return None


def exigir_coluna(arquivo, colunas, candidatos, descricao):
    col = achar_coluna(colunas, candidatos)
    if col is None:
        sys.exit(f"[ERRO] {arquivo}: nao achei a coluna de {descricao}. "
                 f"Procurei {candidatos}. Colunas existentes: {list(colunas)}")
    return col


def calcular_fracoes(cel, valido, comp, n_celulas, regra):
    """
    Fracao do valor da celula que cada trecho recebe.
    A soma das fracoes dos trechos de uma mesma celula e 1.
    """
    n_trechos = len(cel)
    n_por_celula = np.bincount(cel[valido], minlength=n_celulas)
    frac = np.zeros(n_trechos, dtype=np.float64)

    if regra == "comprimento":
        soma_comp = np.bincount(cel[valido], weights=comp[valido], minlength=n_celulas)
        tem_comp = valido & (soma_comp[cel] > 0)
        frac[tem_comp] = comp[tem_comp] / soma_comp[cel[tem_comp]]
        sem_comp = valido & ~tem_comp                   # celula cujos trechos tem comprimento 0
        frac[sem_comp] = 1.0 / n_por_celula[cel[sem_comp]]
    else:
        frac[valido] = 1.0 / n_por_celula[cel[valido]]
    return frac, n_por_celula


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", default="data/processed/dataset_hidrologico_global.csv")
    p.add_argument("--mapeamento", default="data/processed/glofas/mapeamento_hydrorivers_indices.csv")
    p.add_argument("--deficits", default="data/processed/glofas/deficits_mensais_por_celula_float32.dat")
    p.add_argument("--meses", default="data/processed/glofas/indice_meses_glofas.csv")
    p.add_argument("--celulas-regiao", default="data/processed/glofas/celulas_sao_francisco_unicas.csv")
    p.add_argument("--saida", default="data/processed/dataset_com_deficit.csv")
    p.add_argument("--relatorio", default="results/cenarios_deficit_info.txt")
    p.add_argument("--regra", choices=["comprimento", "igual"], default="comprimento",
                   help="como dividir o valor da celula entre os trechos dela")
    p.add_argument("--n-celulas", type=int, default=N_CELULAS_PADRAO)
    p.add_argument("--mes-indice", type=int, default=None,
                   help="forca o indice (0..251) do mes unico, em vez de escolher pelo Sao Francisco")
    p.add_argument("--bloco", type=int, default=100_000, help="celulas lidas por vez")
    args = p.parse_args()

    if args.bloco <= 0:
        sys.exit("[ERRO] O tamanho do bloco deve ser positivo.")

    for arq in [args.dataset, args.mapeamento, args.deficits, args.meses]:
        if not Path(arq).exists():
            sys.exit(f"[ERRO] arquivo nao encontrado: {arq}")

    n_celulas = args.n_celulas
    tamanho_esperado = n_celulas * N_MESES * 4
    tamanho_real = Path(args.deficits).stat().st_size
    if tamanho_real != tamanho_esperado:
        sys.exit(f"[ERRO] {args.deficits} tem {tamanho_real} bytes; esperado {tamanho_esperado} "
                 f"({n_celulas} celulas x {N_MESES} meses x 4 bytes). Confira --n-celulas.")

    dados = np.memmap(args.deficits, dtype="float32", mode="r", shape=(n_celulas, N_MESES))

    # ------------------------------------------------------------ meses
    meses = pd.read_csv(args.meses)
    col_idx_mes = exigir_coluna(args.meses, meses.columns, ["indice_mes"], "indice do mes")
    col_ano_mes = exigir_coluna(args.meses, meses.columns, ["ano_mes"], "ano_mes")
    meses = meses.sort_values(col_idx_mes).reset_index(drop=True)
    if len(meses) != N_MESES:
        sys.exit(f"[ERRO] {args.meses} tem {len(meses)} meses; esperado {N_MESES}")
    nome_mes = dict(zip(meses[col_idx_mes].to_numpy(), meses[col_ano_mes].astype(str).to_numpy()))
    print(f"[INFO] Janela da seca: {nome_mes[MES_INI]} ate {nome_mes[MES_FIM - 1]} ({N_MESES_SECA} meses)")

    # ------------------------------------------------ 1. mes unico (Sao Francisco)
    if args.mes_indice is not None:
        mes_unico = args.mes_indice
        origem_mes = "informado manualmente (--mes-indice)"
    else:
        if not Path(args.celulas_regiao).exists():
            sys.exit(f"[ERRO] arquivo da regiao nao encontrado: {args.celulas_regiao} "
                     f"(ou informe --mes-indice)")
        reg = pd.read_csv(args.celulas_regiao)
        col_cell = exigir_coluna(args.celulas_regiao, reg.columns, ["cell_index"], "indice da celula")
        celulas_reg = reg[col_cell].drop_duplicates().to_numpy(dtype=np.int64)
        if len(celulas_reg) == 0 or celulas_reg.min() < 0 or celulas_reg.max() >= n_celulas:
            sys.exit("[ERRO] indices de celulas da regiao fora dos limites da matriz")
        print(f"[INFO] Escolhendo o mes unico entre {len(celulas_reg):,} celulas da regiao...")
        matriz_reg = np.asarray(dados[celulas_reg, MES_INI:MES_FIM], dtype=np.float64)
        agregado = np.nansum(matriz_reg, axis=0)
        mes_unico = MES_INI + int(np.argmax(agregado))
        origem_mes = (f"maior deficit agregado de {len(celulas_reg):,} celulas do Sao Francisco "
                      f"entre {nome_mes[MES_INI]} e {nome_mes[MES_FIM - 1]}")
        del matriz_reg
    if not (0 <= mes_unico < N_MESES):
        sys.exit(f"[ERRO] indice de mes invalido: {mes_unico}")
    print(f"[INFO] Mes unico: indice {mes_unico} = {nome_mes[mes_unico]}")

    # ------------------------------------------------ 2. valores por celula
    print("[INFO] Calculando os 3 valores por celula (leitura em blocos)...")
    seca = np.zeros(n_celulas, dtype=np.float64)
    total = np.zeros(n_celulas, dtype=np.float64)
    mes = np.zeros(n_celulas, dtype=np.float64)
    celulas_sem_dado = 0
    for ini in range(0, n_celulas, args.bloco):
        fim = min(ini + args.bloco, n_celulas)
        bloco = np.asarray(dados[ini:fim])                    # float32, (linhas, 252)
        seca[ini:fim] = np.nansum(bloco[:, MES_INI:MES_FIM], axis=1, dtype=np.float64)
        total[ini:fim] = np.nansum(bloco, axis=1, dtype=np.float64)
        mes[ini:fim] = np.nan_to_num(bloco[:, mes_unico], nan=0.0).astype(np.float64)
        celulas_sem_dado += int((~np.isfinite(bloco)).all(axis=1).sum())
        print(f"       {fim:>10,} / {n_celulas:,}", end="\r")
    print()

    # ------------------------------------------------ 3. rede e mapeamento
    print("[INFO] Lendo a rede e o mapeamento trecho -> celula...")
    cab = pd.read_csv(args.dataset, nrows=0).columns
    c_id = exigir_coluna(args.dataset, cab, ["hyriv_id"], "hyriv_id")
    c_next = exigir_coluna(args.dataset, cab, ["next_down"], "next_down")
    c_lat = exigir_coluna(args.dataset, cab, ["lat"], "latitude")
    c_lon = exigir_coluna(args.dataset, cab, ["lon"], "longitude")
    colunas_ler = [c_id, c_next, c_lat, c_lon]
    renomear = {c_id: "hyriv_id", c_next: "next_down", c_lat: "lat", c_lon: "lon"}
    if args.regra == "comprimento":
        c_comp = exigir_coluna(args.dataset, cab, ["length_km"], "comprimento do trecho")
        colunas_ler.append(c_comp)
        renomear[c_comp] = "length_km"
    trechos = pd.read_csv(args.dataset, usecols=colunas_ler).rename(columns=renomear)
    n_trechos = len(trechos)

    cab_m = pd.read_csv(args.mapeamento, nrows=0).columns
    m_id = exigir_coluna(args.mapeamento, cab_m, ["hyriv_id"], "hyriv_id")
    m_cel = exigir_coluna(args.mapeamento, cab_m,
                          ["cell_index", "indice_celula", "celula_indice", "indice"], "indice da celula")
    mapa = pd.read_csv(args.mapeamento, usecols=[m_id, m_cel])
    mapa = mapa.rename(columns={m_id: "hyriv_id", m_cel: "cell_index"})
    if mapa["hyriv_id"].duplicated().any():
        sys.exit("[ERRO] mapeamento com hyriv_id repetido")

    trechos = trechos.merge(mapa, on="hyriv_id", how="left")     # left: mantem a ordem do dataset
    if len(trechos) != n_trechos:
        sys.exit(f"[ERRO] o merge mudou o numero de linhas: {n_trechos} -> {len(trechos)}")

    sem_celula = np.array(trechos["cell_index"].isna())          # np.array copia (pandas novo devolve somente leitura)
    cel = np.array(trechos["cell_index"].fillna(-1), dtype=np.int64)
    sem_celula |= cel < 0
    valido = ~sem_celula
    if cel[valido].size and cel[valido].max() >= n_celulas:
        sys.exit("[ERRO] cell_index fora dos limites da matriz")
    cel[sem_celula] = 0                                          # evita indice negativo; sera mascarado

    comp = np.zeros(n_trechos, dtype=np.float64)
    if args.regra == "comprimento":
        comp = np.array(trechos["length_km"], dtype=np.float64)
        if not np.isfinite(comp).all():
            sys.exit("[ERRO] Existem comprimentos ausentes ou nao finitos.")
        if (comp < 0).any():
            sys.exit("[ERRO] Existem comprimentos negativos.")

    # ------------------------------------------------ 4. distribuicao entre os trechos
    frac, n_por_celula = calcular_fracoes(cel, valido, comp, n_celulas, args.regra)

    usadas = n_por_celula > 0
    n_usadas = int(usadas.sum())
    media_por_celula = float(n_por_celula[usadas].mean()) if n_usadas else 0.0
    max_por_celula = int(n_por_celula.max())
    celulas_com_varios = int((n_por_celula > 1).sum())
    print(f"[INFO] Celulas usadas por algum trecho: {n_usadas:,} de {n_celulas:,}")
    print(f"[INFO] Trechos por celula: media {media_por_celula:.2f}, maximo {max_por_celula}; "
          f"celulas com mais de um trecho: {celulas_com_varios:,}")

    for nome, vetor in [("deficit_seca", seca), ("deficit_total", total), ("deficit_mes", mes)]:
        valores = vetor[cel] * frac
        valores[sem_celula] = 0.0                                # trecho sem celula: deficit 0
        trechos[nome] = valores

    # ------------------------------------------------ verificacoes
    cols_def = ["deficit_seca", "deficit_total", "deficit_mes"]
    if trechos[cols_def].isna().any().any():
        sys.exit("[ERRO] sobrou NaN nos deficits")

    # conservacao: a soma dos pesos dos trechos e igual a soma dos valores das celulas usadas
    print("[INFO] Conservacao (soma dos pesos dos trechos x soma dos valores das celulas usadas):")
    for nome, vetor in [("deficit_seca", seca), ("deficit_total", total), ("deficit_mes", mes)]:
        soma_trechos = float(trechos[nome].sum())
        soma_celulas = float(vetor[usadas].sum())
        ok = np.isclose(soma_trechos, soma_celulas, rtol=1e-9, atol=1e-6)
        print(f"       {nome:<14} trechos {soma_trechos:.9g} | celulas {soma_celulas:.9g} | "
              f"{'OK' if ok else 'DIVERGENTE'}")
        if not ok:
            sys.exit("[ERRO] a distribuicao nao conservou o total")

    # conferencia manual de trechos sorteados
    rng = np.random.default_rng(1)
    candidatos = np.flatnonzero(valido)
    amostra = rng.choice(candidatos, size=min(5, len(candidatos)), replace=False)
    print("[INFO] Conferencia manual de trechos sorteados (matriz x CSV):")
    for i in amostra:
        c = int(cel[i])
        linha = np.asarray(dados[c], dtype=np.float64)
        esp_celula = np.nansum(linha[MES_INI:MES_FIM])           # valor da celula no cenario seca
        membros = np.flatnonzero(valido & (cel == c))            # trechos que dividem a celula
        if args.regra == "comprimento" and comp[membros].sum() > 0:
            fr = comp[i] / comp[membros].sum()
        else:
            fr = 1.0 / len(membros)
        esp_trecho = esp_celula * fr
        soma_membros = float(trechos.loc[membros, "deficit_seca"].sum())
        ok = (np.isclose(trechos.at[i, "deficit_seca"], esp_trecho, rtol=1e-6, atol=1e-9) and
              np.isclose(soma_membros, esp_celula, rtol=1e-6, atol=1e-9))
        print(f"       hyriv_id {int(trechos.at[i, 'hyriv_id'])} | celula {c} ({len(membros)} trechos) | "
              f"seca {trechos.at[i, 'deficit_seca']:.6g} | {'OK' if ok else 'DIVERGENTE'}")
        if not ok:
            sys.exit("[ERRO] a conferencia manual divergiu")

    # ------------------------------------------------ 5. saida
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.relatorio).parent.mkdir(parents=True, exist_ok=True)
    saida = trechos[["hyriv_id", "next_down", "lat", "lon"] + cols_def]
    print(f"[INFO] Gravando {args.saida} ...")
    saida.to_csv(args.saida, index=False, float_format="%.9g")

    n_sem = int(sem_celula.sum())
    if args.regra == "comprimento":
        txt_regra = "proporcional ao length_km do trecho dentro da celula"
    else:
        txt_regra = "dividida igualmente entre os trechos da celula"
    linhas = [
        "Cenarios de deficit por trecho",
        f"Trechos: {n_trechos:,}",
        f"deficit_seca : soma de {N_MESES_SECA} meses, {nome_mes[MES_INI]} a {nome_mes[MES_FIM - 1]}",
        f"deficit_total: soma de {N_MESES} meses, {nome_mes[0]} a {nome_mes[N_MESES - 1]}",
        f"deficit_mes  : {nome_mes[mes_unico]} (indice {mes_unico}); criterio: {origem_mes}",
        "Regra de NaN: mes sem dado conta como 0 (nansum), a mesma regra do C++",
        f"Celulas da matriz sem nenhum dado valido: {celulas_sem_dado:,}",
        f"Trechos sem celula no mapeamento (deficit 0): {n_sem:,}",
        "",
        "Celulas repetidas: o valor de cada celula e distribuido entre os trechos que caem nela,",
        f"  regra: {txt_regra}.",
        "  A soma dos pesos dos trechos de uma celula e o valor da celula (cada celula entra uma vez).",
        f"  Celulas usadas por algum trecho: {n_usadas:,} de {n_celulas:,}",
        f"  Trechos por celula: media {media_por_celula:.2f}, maximo {max_por_celula}; "
        f"celulas compartilhadas por mais de um trecho: {celulas_com_varios:,}",
        "  Limitacao: uma bacia que inclui so parte dos trechos de uma celula recebe so parte do valor dela.",
        "Unidade: soma de vazoes mensais em m3/s (indicador agregado, nao volume fisico).",
    ]
    Path(args.relatorio).write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print("\n" + "\n".join(linhas))
    print(f"\n[OK] CSV: {args.saida}\n[OK] Relatorio: {args.relatorio}")


if __name__ == "__main__":
    main()