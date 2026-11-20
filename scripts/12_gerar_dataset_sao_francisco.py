from pathlib import Path
import sys
import time
import pandas as pd


ARQUIVO_IDS_SF = Path("data/processed/hydrorivers_sao_francisco.csv")
CANDIDATOS_GLOBAL = [
    Path("data/processed/dataset_com_deficit.csv"),
    Path("data/processed/dataset_geral_deficit.csv"),
]
ARQUIVO_SAIDA = Path("data/processed/dataset_deficit_sao_francisco.csv")


def localizar_dataset_global() -> Path:
    for caminho in CANDIDATOS_GLOBAL:
        if caminho.exists():
            return caminho
    nomes = ", ".join(str(c) for c in CANDIDATOS_GLOBAL)
    raise FileNotFoundError(f"Dataset global não encontrado. Caminhos verificados: {nomes}")


def main() -> None:
    inicio = time.time()

    if not ARQUIVO_IDS_SF.exists():
        raise FileNotFoundError(f"Arquivo regional não encontrado: {ARQUIVO_IDS_SF}")

    arquivo_global = localizar_dataset_global()
    ARQUIVO_SAIDA.parent.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Lendo IDs da bacia do São Francisco em: {ARQUIVO_IDS_SF}")
    df_ids = pd.read_csv(ARQUIVO_IDS_SF, usecols=["hyriv_id"])

    if df_ids["hyriv_id"].duplicated().any():
        raise ValueError("Existem hyriv_id duplicados em hydrorivers_sao_francisco.csv.")

    ids_sf = set(df_ids["hyriv_id"].astype("int64"))
    print(f"[INFO] Total de trechos esperados na bacia: {len(ids_sf):,}")
    print(f"[INFO] Filtrando dataset global em: {arquivo_global}")

    if ARQUIVO_SAIDA.exists():
        ARQUIVO_SAIDA.unlink()

    primeiro = True
    total_exportado = 0
    ids_encontrados = set()
    raizes_borda = []
    colunas_exportadas = []
    somas_deficit = {"deficit_seca": 0.0, "deficit_total": 0.0, "deficit_mes": 0.0}

    for bloco in pd.read_csv(arquivo_global, chunksize=500_000):
        if not colunas_exportadas:
            colunas_exportadas = list(bloco.columns)

        filtrado = bloco[bloco["hyriv_id"].isin(ids_sf)].copy()
        if not filtrado.empty:
            filtrado["next_down"] = filtrado["next_down"].fillna(0).astype("int64")

            # Converte destinos fora da bacia em raízes locais (next_down = 0)
            externos = (filtrado["next_down"] != 0) & (~filtrado["next_down"].isin(ids_sf))
            if externos.any():
                raizes_borda.extend(filtrado.loc[externos, "hyriv_id"].astype("int64").tolist())
                filtrado.loc[externos, "next_down"] = 0

            filtrado.to_csv(
                ARQUIVO_SAIDA,
                mode="w" if primeiro else "a",
                index=False,
                header=primeiro,
            )
            primeiro = False
            total_exportado += len(filtrado)
            ids_encontrados.update(filtrado["hyriv_id"].astype("int64"))

            for col in somas_deficit:
                if col in filtrado.columns:
                    somas_deficit[col] += float(filtrado[col].sum())

    if total_exportado != len(ids_sf) or len(ids_encontrados) != len(ids_sf):
        faltantes = len(ids_sf - ids_encontrados)
        raise ValueError(
            f"Divergência na filtragem: esperados {len(ids_sf):,}, "
            f"exportados {total_exportado:,}, faltantes {faltantes:,}."
        )

    duracao = time.time() - inicio
    print("\n" + "=" * 56)
    print("DATASET DO SÃO FRANCISCO GERADO COM SUCESSO")
    print("=" * 56)
    print(f"Arquivo de saída      : {ARQUIVO_SAIDA}")
    print(f"Trechos exportados    : {total_exportado:,}")
    print(f"Raízes de borda (0)   : {len(raizes_borda)} trechos -> {raizes_borda}")
    print(f"Soma deficit_seca     : {somas_deficit['deficit_seca']:,.2f}")
    print(f"Soma deficit_total    : {somas_deficit['deficit_total']:,.2f}")
    print(f"Soma deficit_mes      : {somas_deficit['deficit_mes']:,.2f}")
    print(f"Tempo de execução     : {duracao:.2f} s")
    print("=" * 56)


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print(f"[ERRO] {erro}", file=sys.stderr)
        sys.exit(1)