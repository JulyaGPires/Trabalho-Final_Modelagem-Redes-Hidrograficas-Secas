import json
import time
from pathlib import Path
from datetime import date, datetime, timedelta
from zipfile import ZipFile
from shutil import copyfileobj, disk_usage

import numpy as np
import pandas as pd
from netCDF4 import Dataset

BASE = Path("data/processed/glofas")
DOWNLOADS = Path.home() / "Downloads"

MANIFESTO = BASE / "manifesto_glofas.csv"
COBERTURA = BASE / "cobertura_diaria_glofas.csv"
CELULAS = BASE / "celulas_glofas_unicas.csv"

SAIDA = BASE / "serie_vazoes_glofas_float32.dat"
DATAS_SAIDA = BASE / "indice_datas_glofas.csv"
METADADOS = BASE / "metadados_glofas.json"
RELATORIO = BASE / "extracao_glofas.txt"
CHECKPOINT = BASE / "checkpoint_extracao.json"

TEMP = BASE / "tmp" / "data_0.nc"

DATA_INICIAL = date(2000, 1, 1)
DATA_FINAL = date(2020, 12, 31)
N_DIAS = (DATA_FINAL - DATA_INICIAL).days + 1
BLOCO_TEMPO = 15

inicio = time.time()
BASE.mkdir(parents=True, exist_ok=True)
TEMP.parent.mkdir(parents=True, exist_ok=True)

print("[INFO] Lendo manifesto e cobertura...", flush=True)

manifesto = pd.read_csv(MANIFESTO)
manifesto = manifesto.sort_values(["primeiro_dia", "arquivo"]).reset_index(drop=True)

if len(manifesto) != 24:
    raise RuntimeError("O manifesto não contém exatamente 24 arquivos.")

cobertura = pd.read_csv(COBERTURA)
cobertura["data"] = pd.to_datetime(cobertura["data"]).dt.date

datas_esperadas = [DATA_INICIAL + timedelta(days=i)for i in range(N_DIAS)]

if len(cobertura) != N_DIAS:
    raise RuntimeError("A cobertura diária não tem 7.671 registros.")

if cobertura["quantidade_registros"].ne(1).any():
    raise RuntimeError("A cobertura diária apresenta datas ausentes ou duplicadas.")

if cobertura["data"].tolist() != datas_esperadas:
    raise RuntimeError("As datas da cobertura não estão completas e ordenadas.")

indice_data = {d: i for i, d in enumerate(datas_esperadas)}

print("[INFO] Carregando células únicas e pré-computando blocos espaciais...", flush=True)

celulas = np.loadtxt(CELULAS,delimiter=",",skiprows=1,dtype=np.int32)

linhas = celulas[:, 0]
colunas = celulas[:, 1]
n_celulas = len(celulas)

ids = (linhas // 300) * 10 + (colunas // 720)
grupos = np.unique(ids)

# Separa as células por blocos espaciais para otimizar a leitura dos dados
grupos_info = []
for identificador in grupos:
    indices = np.flatnonzero(ids == identificador)
    r = int(identificador // 10)
    c = int(identificador % 10)
    ll = linhas[indices] - r * 300
    cl = colunas[indices] - c * 720
    grupos_info.append((r, c, indices, ll, cl))

# Confere se há espaço suficiente para armazenar toda a matriz de vazões.
tamanho_bytes = N_DIAS * n_celulas * 4
livre = disk_usage(BASE).free

print(f"Dias: {N_DIAS}")
print(f"Células únicas: {n_celulas:,}")
print(f"Blocos espaciais ativos: {len(grupos)}")
print(f"Tamanho da matriz final: {tamanho_bytes / 1024**3:.2f} GiB")


if livre < tamanho_bytes + 50 * 1024**3:
    raise RuntimeError("Espaço livre em disco insuficiente para extração segura.")

if CHECKPOINT.exists() and SAIDA.exists():
    with open(CHECKPOINT) as f:
        estado = json.load(f)
    if estado.get("concluido", False):
        print("[SUCESSO] A extração já foi totalmente concluída anteriormente!")
        print(f"[INFO] Arquivo existente: {SAIDA}")
        raise SystemExit(0)
    modo = "r+"
    print(f"[INFO] Retomando extração do arquivo {estado['arquivo_index'] + 1}/24 a partir do dia {estado['proximo_tempo']}...")
elif not CHECKPOINT.exists() and not SAIDA.exists():
    estado = {
        "arquivo_index": 0,
        "proximo_tempo": 0,
        "valores_ausentes": 0,
        "concluido": False
    }
    modo = "w+"
else:
    raise RuntimeError(
        "Existe arquivo de saída ou checkpoint isolado. "
        "Delete-os manualmente caso queira recomeçar do zero."
    )

# Cria a matriz em disco para evitar carregar toda a série na memória RAM.
resultado = np.memmap(
    SAIDA,
    dtype=np.float32,
    mode=modo,
    shape=(N_DIAS, n_celulas)
)

try:

    # Processa os arquivos ZIP, permitindo retomar a extração por checkpoint.
    for arquivo_index in range(estado["arquivo_index"], len(manifesto)):
        tempo_arquivo_inicio = time.time()
        registro = manifesto.iloc[arquivo_index]
        nome = str(registro["arquivo"])
        zip_path = DOWNLOADS / nome

        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP não encontrado: {zip_path}")

        print(f"\n[{arquivo_index + 1}/24] Extraindo NetCDF temporário de {nome}...", flush=True)

        with ZipFile(zip_path) as z:
            nc_candidatos = [f for f in z.namelist() if f.endswith(".nc")]
            if not nc_candidatos:
                raise RuntimeError(f"Nenhum arquivo .nc encontrado dentro de {nome}")
            nome_nc = nc_candidatos[0]

            with z.open(nome_nc) as origem:
                with open(TEMP, "wb") as destino:
                    copyfileobj(origem, destino, length=8 * 1024 * 1024)

        with Dataset(TEMP) as ds:
            var = ds.variables["avg_dis"]
            tempo = ds.variables["valid_time"]
            n_registros = len(tempo)

            if n_registros != int(registro["registros"]):
                raise RuntimeError(f"Quantidade de datas inesperada em {nome}.")

            origem_tempo = datetime(1970, 1, 1)
            datas = [
                (origem_tempo + timedelta(seconds=int(ts)) - timedelta(days=1)).date()
                for ts in tempo[:]
            ]

            if datas[0].isoformat() != registro["primeiro_dia"]:
                raise RuntimeError(f"Primeira data incorreta em {nome}.")

            if datas[-1].isoformat() != registro["ultimo_dia"]:
                raise RuntimeError(f"Última data incorreta em {nome}.")

            if any(datas[i] >= datas[i + 1] for i in range(len(datas) - 1)):
                raise RuntimeError(f"Datas fora de ordem em {nome}.")

            indices_datas = np.array([indice_data[d] for d in datas], dtype=np.int64)

            inicio_tempo = estado["proximo_tempo"] if arquivo_index == estado["arquivo_index"] else 0
            total_blocos_tempo = (n_registros + BLOCO_TEMPO - 1) // BLOCO_TEMPO

            for t in range(inicio_tempo, n_registros, BLOCO_TEMPO):
                fim = min(t + BLOCO_TEMPO, n_registros)
                ausentes_bloco = 0

                for r, c, indices, linhas_local, colunas_local in grupos_info:
                    dados = var[t:fim,r * 300:(r + 1) * 300,c * 720:(c + 1) * 720]

                    valores = dados[:, linhas_local, colunas_local]
                    valores_np = np.ma.filled(valores, np.nan).astype(np.float32, copy=False)
                    ausentes_bloco += int(np.isnan(valores_np).sum())

                    for j, destino_t in enumerate(indices_datas[t:fim]):
                        resultado[destino_t, indices] = valores_np[j]

                resultado.flush()

                estado["valores_ausentes"] += ausentes_bloco
                estado["arquivo_index"] = arquivo_index
                estado["proximo_tempo"] = fim

                checkpoint_tmp = CHECKPOINT.with_suffix(".tmp")
                with open(checkpoint_tmp, "w") as f:
                    json.dump(estado, f)
                checkpoint_tmp.replace(CHECKPOINT)

                bloco_atual = t // BLOCO_TEMPO + 1
                print(f"  Bloco {bloco_atual}/{total_blocos_tempo} "f"| dias {t + 1}-{fim}/{n_registros}",flush=True)

        TEMP.unlink(missing_ok=True)

        estado["arquivo_index"] = arquivo_index + 1
        estado["proximo_tempo"] = 0

        checkpoint_tmp = CHECKPOINT.with_suffix(".tmp")
        with open(checkpoint_tmp, "w") as f:
            json.dump(estado, f)
        checkpoint_tmp.replace(CHECKPOINT)

        tempo_arquivo = (time.time() - tempo_arquivo_inicio) / 60
        print(f"[OK] Arquivo concluído em {tempo_arquivo:.1f} min | "f"ausentes acumulados: {estado['valores_ausentes']:,}",flush=True)

    resultado.flush()

finally:
    if "resultado" in locals():
        del resultado
    TEMP.unlink(missing_ok=True)

if estado["arquivo_index"] == len(manifesto):
    total = N_DIAS * n_celulas
    ausentes = estado["valores_ausentes"]


    # Índice de datas em CSV
    pd.DataFrame({"indice": range(N_DIAS), "data": [d.isoformat() for d in datas_esperadas]}).to_csv(DATAS_SAIDA, index=False)

    with open(METADADOS, "w") as f:
        json.dump({
            "linhas_dias": N_DIAS,
            "colunas_celulas": n_celulas,
            "bytes_por_elemento": 4,
            "dtype": "float32",
            "layout": "row_major_C",
            "data_inicial": DATA_INICIAL.isoformat(),
            "data_final": DATA_FINAL.isoformat(),
            "arquivo_dados": str(SAIDA.name),
            "arquivo_datas": str(DATAS_SAIDA.name),
            "arquivo_celulas": str(CELULAS.name)
        }, f, indent=2)


     # Metadados para carregamento no C++ (cpp_core)
    with open(RELATORIO, "w") as f:
        f.write("EXTRAÇÃO GLOFAS CONCLUÍDA\n")
        f.write(f"Período: {DATA_INICIAL} a {DATA_FINAL}\n")
        f.write(f"Dias: {N_DIAS}\n")
        f.write(f"Células: {n_celulas}\n")
        f.write(f"Valores esperados: {total}\n")
        f.write(f"Valores válidos: {total - ausentes}\n")
        f.write(f"Valores ausentes: {ausentes}\n")
        f.write("Tipo: float32\n")
        f.write("Unidade: m³/s\n")
        f.write(f"Arquivo binário: {SAIDA}\n")
        f.write(f"Metadados C++: {METADADOS}\n")
        f.write(f"Índice de datas: {DATAS_SAIDA}\n")

    estado["concluido"] = True
    with open(CHECKPOINT, "w") as f:
        json.dump(estado, f)

    print("\n========== EXTRAÇÃO GLOFAS CONCLUÍDA COM SUCESSO ==========")
    print(f"Dias: {N_DIAS}")
    print(f"Células únicas: {n_celulas:,}")
    print(f"Arquivo binário: {SAIDA} ({tamanho_bytes / 1024**3:.2f} GiB)")
    print(f"Metadados C++: {METADADOS}")
    print(f"Índice de datas: {DATAS_SAIDA}")
    print(f"Tempo total: {(time.time() - inicio) / 60:.1f} minutos")
