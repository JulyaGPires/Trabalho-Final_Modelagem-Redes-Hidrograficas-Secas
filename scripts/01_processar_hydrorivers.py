from pathlib import Path
import geopandas as gpd
import pandas as pd
import pyogrio


def main():
    projeto_dir = Path(__file__).resolve().parent.parent

    shapefile = (projeto_dir / "data" / "input" /"HydroRIVERS_global" / "HydroRIVERS_v10.shp")

    output_dir = projeto_dir / "data" / "processed"
    output_path = output_dir / "dataset_hidrologico_global.csv"
    temp_path = output_dir / "dataset_hidrologico_global.csv.tmp"

    # Leitura em blocos para não carregar toda a rede na memória.
    tamanho_bloco = 50000

    if not shapefile.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {shapefile}")

    if output_path.exists():
        raise FileExistsError( f"O arquivo de saída já existe: {output_path}. " "Renomeie-o ou delete-o antes de iniciar novo processamento.")

    print("[INFO] Consultando metadados do HydroRIVERS...")
    info = pyogrio.read_info(shapefile)
    total = info["features"]
    colunas = list(info["fields"])

    print(f"[INFO] Total de trechos a processar: {total:,}")
    print(f"[INFO] Atributos preservados: {len(colunas)}")
    print(f"[INFO] Processando em blocos de {tamanho_bloco:,} trechos...")

    output_dir.mkdir(parents=True, exist_ok=True)

    if temp_path.exists():
        temp_path.unlink()

    try:
        for inicio in range(0, total, tamanho_bloco):
            fim = min(inicio + tamanho_bloco, total)
            progresso = (fim / total) * 100
            print(f"[INFO] Processando {inicio + 1:,} até {fim:,} ({progresso:.1f}%)...")

            gdf = pyogrio.read_dataframe(shapefile,columns=colunas, skip_features=inicio,max_features=tamanho_bloco,)

              # Calcula o ponto médio dos trechos em uma projeção adequada.
            gdf_proj = gdf.to_crs("EPSG:8857")
            pontos = gdf_proj.geometry.interpolate(0.5, normalized=True).to_crs("EPSG:4326")

            df = gdf.drop(columns="geometry")

            # 10 casas decimais para lon e lat
            df["lon"] = pontos.x.round(10)
            df["lat"] = pontos.y.round(10)

            df.columns = df.columns.str.lower()

            df.to_csv(temp_path, mode="w" if inicio == 0 else "a", header=(inicio == 0), index=False,)


        # O arquivo final só é criado depois que o processamento termina.
        temp_path.replace(output_path)

        print("[SUCESSO] Processamento global concluído com sucesso!")
        print(f"[INFO] Arquivo gerado: {output_path}")

    except Exception as e:
        print(f"[ERRO] Falha durante o processamento: {e}")
        if temp_path.exists():
            temp_path.unlink()
        raise


if __name__ == "__main__":
    main()
