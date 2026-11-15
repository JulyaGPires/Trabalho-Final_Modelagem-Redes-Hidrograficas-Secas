
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
arquivo = BASE_DIR / "data" / "processed" / "dataset_hidrologico_global.csv"


def main():
    print("=== VERIFICACAO DE CONECTIVIDADE GEOGRAFICA ===")

    df = pd.read_csv(
       arquivo,
       usecols=["hyriv_id", "next_down", "lon", "lat"]
    )

    # Mesmo recorte geografico usado na validacao anterior
    fora = (
        (df["lat"] > 13.5) |
        (df["lon"] < -82) |
        (df["lon"] > -34) |
        (df["lat"] < -56)
    )

    continental = df[~fora]
    externo = df[fora]

    # Conjuntos de IDs de cada regiao
    ids_continentais = set(continental["hyriv_id"])
    ids_externos = set(externo["hyriv_id"])

    # Referencias dos trechos continentais
    conexoes_continentais = continental[
        continental["next_down"].isin(ids_externos)
    ]

    # Referencias dos trechos externos
    conexoes_externas = externo[
        externo["next_down"].isin(ids_continentais)
    ]

    print(f"\nTrechos continentais: {len(continental)}")
    print(f"Trechos externos: {len(externo)}")

    print("\n--- Conexoes entre regioes ---")

    print(
        "Trechos continentais apontando para externos:",
        len(conexoes_continentais)
    )

    print(
        "Trechos externos apontando para continentais:",
        len(conexoes_externas)
    )

    if len(conexoes_continentais) > 0:
        print("\nExemplos de conexoes continentais para externas:")
        print(
            conexoes_continentais[
                ["hyriv_id", "next_down", "lon", "lat"]
            ].head(10).to_string(index=False)
        )

    if len(conexoes_externas) > 0:
        print("\nExemplos de conexoes externas para continentais:")
        print(
            conexoes_externas[
                ["hyriv_id", "next_down", "lon", "lat"]
            ].head(10).to_string(index=False)
        )

    print("\n=== FIM DA VERIFICACAO ===")


if __name__ == "__main__":
    main()
