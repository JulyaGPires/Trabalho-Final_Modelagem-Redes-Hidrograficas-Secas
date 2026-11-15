import json
import time
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path("data/processed/glofas")

ARQUIVO_DADOS = BASE / "serie_vazoes_glofas_float32.dat"
ARQUIVO_METADADOS = BASE / "metadados_glofas.json"
ARQUIVO_DATAS = BASE / "indice_datas_glofas.csv"
ARQUIVO_CELULAS = BASE / "celulas_glofas_unicas.csv"
ARQUIVO_MAPEAMENTO = BASE / "mapeamento_hydrorivers_glofas.csv"

SAIDA_DEFICITS = BASE / "deficits_mensais_por_celula_float32.dat"
SAIDA_INDICES = BASE / "mapeamento_hydrorivers_indices.csv"
SAIDA_METADADOS = BASE / "deficits_mensais_metadados.json"
SAIDA_MESES = BASE / "indice_meses_glofas.csv"

TEMP_MENSAIS = BASE / "tmp" / "medias_mensais_temp.dat"

# Quantidade de células processadas por vez.
BLOCO_CELULAS = 100_000


def calcular_deficits():
    inicio_total = time.time()
    print("[INFO] Lendo metadados e índice de datas...", flush=True)

    with open(ARQUIVO_METADADOS, "r") as f:
        metadados = json.load(f)

    n_dias = metadados["linhas_dias"]
    n_celulas = metadados["colunas_celulas"]

    datas = pd.read_csv(ARQUIVO_DATAS)
    datas["data"] = pd.to_datetime(datas["data"])

    periodos = datas["data"].dt.to_period("M")
    meses_unicos = periodos.drop_duplicates().tolist()
    n_meses = len(meses_unicos)

    if n_meses != 252:
        raise ValueError(f"Esperados 252 meses, encontrados {n_meses}.")

    tamanho_esperado = n_dias * n_celulas * 4
    if ARQUIVO_DADOS.stat().st_size != tamanho_esperado:
        raise ValueError("Tamanho do arquivo binário não confere com os metadados.")

    print(f"Dias: {n_dias:,} | Células: {n_celulas:,} | Meses: {n_meses}")

    # Identifica os dias pertencentes a cada mês para calcular as médias mensais.
    intervalos_meses = []
    for mes in meses_unicos:
        idx = np.flatnonzero(periodos == mes)
        intervalos_meses.append((idx[0], idx[-1] + 1, len(idx)))

    print("\n[ETAPA 1/5] Calculando médias mensais (leitura sequencial otimizada)...", flush=True)
    TEMP_MENSAIS.parent.mkdir(parents=True, exist_ok=True)

    dados = np.memmap( ARQUIVO_DADOS,dtype=np.float32,mode="r",shape=(n_dias, n_celulas),order="C", )

    # Guarda as médias mensais antes de calcular os déficits.
    temp_mensais = np.memmap( TEMP_MENSAIS,dtype=np.float32,mode="w+",shape=(n_meses, n_celulas),order="C",)

    t0 = time.time()
    try:
        for m_idx, (d_ini, d_fim, n_dias_mes) in enumerate(intervalos_meses):
            # Lê os dados do mês atual.
            bloco_dias = dados[d_ini:d_fim, :]

            validos = np.isfinite(bloco_dias)
            quantidades = validos.sum(axis=0)

            # Soma apenas os valores disponíveis.
            somas = np.sum(bloco_dias, axis=0, where=validos,dtype=np.float64,)

            medias = np.full(n_celulas, np.nan, dtype=np.float32)
            mascara = quantidades > 0
            medias[mascara] = (somas[mascara] / quantidades[mascara]).astype(np.float32)

            temp_mensais[m_idx, :] = medias

            if (m_idx + 1) % 12 == 0 or (m_idx + 1) == n_meses:
                ano = 2000 + (m_idx // 12)
                tempo_decorrido = (time.time() - t0) / 60
                progresso = (m_idx + 1) / n_meses * 100
                print(f"  Médias calculadas até {ano} ({m_idx + 1}/{n_meses} meses, {progresso:.1f}%) | {tempo_decorrido:.1f} min", flush=True)

        temp_mensais.flush()
        del dados

        print("\n[ETAPA 2/5] Calculando déficits históricos e transpondo matriz final...", flush=True)

        # Armazena os déficits em uma matriz organizada por célula e mês.
        saida_deficits = np.memmap(SAIDA_DEFICITS,dtype=np.float32,mode="w+",shape=(n_celulas, n_meses), order="C",)

        for inicio in range(0, n_celulas, BLOCO_CELULAS):
            fim = min(inicio + BLOCO_CELULAS, n_celulas)
            largura = fim - inicio

            # Carrega os meses das células deste bloco.
            bloco_meses = np.array(temp_mensais[:, inicio:fim], dtype=np.float32, copy=True).T


            for mes_cal in range(12):
                idx_meses = np.arange(mes_cal, n_meses, 12)
                valores = bloco_meses[:, idx_meses]

                validos = np.isfinite(valores)
                quantidades = validos.sum(axis=1)

                # Calcula a média usando apenas os valores disponíveis.
                somas = np.sum(valores,axis=1, where=validos,dtype=np.float64,)

                referencia = np.full(largura, np.nan, dtype=np.float64)
                mascara = quantidades > 0
                referencia[mascara] = somas[mascara] / quantidades[mascara]

                deficits = referencia[:, None] - valores
                np.maximum(deficits, 0, out=deficits)
                deficits[~validos] = np.nan

                bloco_meses[:, idx_meses] = deficits.astype(np.float32)

            saida_deficits[inicio:fim, :] = bloco_meses

            if (inicio // BLOCO_CELULAS) % 10 == 0 or fim == n_celulas:
                progresso = 100 * fim / n_celulas
                print(f"  Déficits calculados: {fim:,}/{n_celulas:,} células ({progresso:.1f}%)", flush=True)

        saida_deficits.flush()
        del saida_deficits
        del temp_mensais

    finally:
        # Remove o arquivo temporário após o cálculo.
        if TEMP_MENSAIS.exists():
            TEMP_MENSAIS.unlink()

    print("\n[ETAPA 3/5] Gerando índice de meses...", flush=True)
    pd.DataFrame({"indice_mes": range(n_meses),"ano_mes": [str(m) for m in meses_unicos],}).to_csv(SAIDA_MESES, index=False)

    print("\n[ETAPA 4/5] Mapeando trechos HydroRIVERS para índices das células GloFAS...", flush=True)
    celulas = np.loadtxt( ARQUIVO_CELULAS,delimiter=",",skiprows=1,dtype=np.int32,)

    # Confere se as colunas das células estão dentro da grade GloFAS.
    if np.any(celulas[:, 1] < 0) or np.any(celulas[:, 1] >= 7200):
        raise ValueError("Índice de coluna fora do intervalo esperado.")

    # Combina linha e coluna para identificar cada célula.
    chaves_celulas = celulas[:, 0].astype(np.int64) * 7200 + celulas[:, 1].astype(np.int64)

    if not np.all(chaves_celulas[:-1] <= chaves_celulas[1:]):
        raise ValueError("A lista de células não está ordenada por linha e coluna.")

    total_trechos = 0
    with open(SAIDA_INDICES, "w") as f_out:
        f_out.write("hyriv_id,cell_index\n")

        for parte in pd.read_csv(ARQUIVO_MAPEAMENTO, chunksize=500_000):
            # Confere as colunas antes de localizar as células.
            if ((parte["glofas_coluna"] < 0).any() or (parte["glofas_coluna"] >= 7200).any()):
                raise ValueError("Coluna GloFAS fora do intervalo esperado.")

            consultas = (parte["glofas_linha"].to_numpy(dtype=np.int64) * 7200 + parte["glofas_coluna"].to_numpy(dtype=np.int64))

            indices = np.searchsorted(chaves_celulas, consultas)
            dentro = indices < n_celulas

            correspondem = np.zeros(len(parte), dtype=bool)
            correspondem[dentro] = chaves_celulas[indices[dentro]] == consultas[dentro]

            if not np.all(correspondem):
                raise ValueError("Células do mapeamento não encontradas em celulas_glofas_unicas.csv.")

            resultado = pd.DataFrame({"hyriv_id": parte["hyriv_id"].to_numpy(),"cell_index": indices.astype(np.int32),})
            resultado.to_csv(f_out, index=False, header=False)

            total_trechos += len(parte)
            print(f"  Trechos associados: {total_trechos:,}", flush=True)

    print("\n[ETAPA 5/5] Salvando metadados finais...", flush=True)
    resultado_metadados = {
        "arquivo": SAIDA_DEFICITS.name,
        "dtype": "float32",
        "layout": "cell_major_C",
        "n_celulas": n_celulas,
        "n_meses": n_meses,
        "periodo": "2000-01 a 2020-12",
        "referencia": "Media historica das medias mensais dos 21 anos para cada mes do calendario.",
        "deficit": "max(0, Q_ref - Q_atual)",
        "valores_ausentes": "NaN preservado",
        "associacoes_hydrorivers": total_trechos,
    }

    with open(SAIDA_METADADOS, "w") as f:
        json.dump(resultado_metadados, f, indent=4, ensure_ascii=False)

    tempo_total = (time.time() - inicio_total) / 60
    print("\n" + "=" * 50)
    print("PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
    print(f"Células únicas: {n_celulas:,}")
    print(f"Meses processados: {n_meses}")
    print(f"Trechos associados: {total_trechos:,}")
    print(f"Matriz de déficits: {SAIDA_DEFICITS} (3.83 GiB)")
    print(f"Mapeamento de índices: {SAIDA_INDICES}")
    print(f"Tempo total estimado: {tempo_total:.1f} minutos")
    print("=" * 50)


if __name__ == "__main__":
    calcular_deficits()
