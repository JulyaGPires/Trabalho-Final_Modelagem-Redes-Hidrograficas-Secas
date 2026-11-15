from pathlib import Path
from zipfile import ZipFile
from netCDF4 import Dataset
from datetime import datetime, timedelta, date
from collections import Counter
import csv

downloads = Path("/mnt/c/Users/julya/Downloads")
temporario = Path("/mnt/c/Users/julya/Downloads/glofas_temp/data_0.nc")
saida = Path("data/processed/glofas")

temporario.parent.mkdir(parents=True, exist_ok=True)
saida.mkdir(parents=True, exist_ok=True)

arquivo_antigo = "459882f3429d7472e61f5627d754f6f0.zip"

zips = sorted(
    p for p in downloads.glob("*.zip")
    if p.name not in ("HydroRIVERS_v10_shp.zip", arquivo_antigo)
)

print("Arquivos encontrados:", len(zips))

if len(zips) != 24:
    raise SystemExit("ERRO: esperávamos exatamente 24 arquivos.")

datas_encontradas = Counter()
manifesto = []

for numero, zip_path in enumerate(zips, 1):
    print(f"\n[{numero}/24] {zip_path.name}", flush=True)

    try:
        with ZipFile(zip_path) as z:
            info = z.getinfo("data_0.nc")

            with z.open(info) as origem, open(temporario, "wb") as destino:
                while True:
                    bloco = origem.read(64 * 1024 * 1024)
                    if not bloco:
                        break
                    destino.write(bloco)

        with Dataset(temporario) as ds:
            tempo = ds.variables["valid_time"]
            valores = tempo[:]

            timestamps = [
                datetime(1970, 1, 1) +
                timedelta(seconds=int(valor))
                for valor in valores
            ]

        # O timestamp marca o fim da média das 24 horas anteriores.
        dias = [(t - timedelta(days=1)).date() for t in timestamps]

        datas_encontradas.update(dias)

        manifesto.append({
            "arquivo": zip_path.name,
            "registros": len(dias),
            "primeiro_dia": str(dias[0]),
            "ultimo_dia": str(dias[-1])
        })

        print(
            f"  {len(dias)} registros | "
            f"{dias[0]} até {dias[-1]}",
            flush=True
        )

    finally:
        if temporario.exists():
            temporario.unlink()

inicio = date(2000, 1, 1)
fim = date(2020, 12, 31)

esperadas = set()
dia = inicio

while dia <= fim:
    esperadas.add(dia)
    dia += timedelta(days=1)

encontradas = set(datas_encontradas)

faltantes = sorted(esperadas - encontradas)
extras = sorted(encontradas - esperadas)

duplicadas = sorted(
    d for d, quantidade in datas_encontradas.items()
    if quantidade > 1
)

with open(saida / "manifesto_glofas.csv", "w", newline="") as f:
    escritor = csv.DictWriter(
        f, fieldnames=["arquivo", "registros", "primeiro_dia", "ultimo_dia"]
    )
    escritor.writeheader()
    escritor.writerows(manifesto)

with open(saida / "cobertura_diaria_glofas.csv", "w", newline="") as f:
    escritor = csv.writer(f)
    escritor.writerow(["data", "quantidade_registros"])

    for dia in sorted(esperadas):
        escritor.writerow([dia, datas_encontradas[dia]])

with open(saida / "validacao_glofas.txt", "w") as f:
    f.write(f"Dias esperados: {len(esperadas)}\n")
    f.write(f"Dias encontrados: {len(encontradas & esperadas)}\n")
    f.write(f"Dias ausentes: {len(faltantes)}\n")
    f.write(f"Dias duplicados: {len(duplicadas)}\n")
    f.write(f"Datas fora do período: {len(extras)}\n")

    f.write("\nDIAS AUSENTES:\n")
    for d in faltantes:
        f.write(f"{d}\n")

    f.write("\nDIAS DUPLICADOS:\n")
    for d in duplicadas:
        f.write(f"{d}: {datas_encontradas[d]} registros\n")

    f.write("\nDATAS FORA DO PERÍODO:\n")
    for d in extras:
        f.write(f"{d}\n")

print("\n========== VALIDAÇÃO FINAL ==========")
print("Dias esperados:", len(esperadas))
print("Dias encontrados:", len(encontradas & esperadas))
print("Dias ausentes:", len(faltantes))
print("Dias duplicados:", len(duplicadas))
print("Datas fora do período:", len(extras))

if faltantes:
    print("\nPrimeiros dias ausentes:", faltantes[:20])

if duplicadas:
    print("\nPrimeiros dias duplicados:")
    for d in duplicadas[:20]:
        print(d, "->", datas_encontradas[d], "registros")

print("\nRelatórios salvos em:", saida)
