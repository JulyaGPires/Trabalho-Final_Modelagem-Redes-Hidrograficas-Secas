from collections import defaultdict, deque
import csv
from pathlib import Path
import sys


CANDIDATOS_ENTRADA = [
    Path("data/processed/dataset_deficit_sao_francisco.csv"),
    Path("data/processed/dataset_com_deficit.csv"),
]

ARQUIVO_NODES = Path("data/processed/gephi_bacia_minuscula_nodes.csv")
ARQUIVO_EDGES = Path("data/processed/gephi_bacia_minuscula_edges.csv")

MIN_NOS = 10
MAX_NOS = 16


def localizar_entrada() -> Path:
    for caminho in CANDIDATOS_ENTRADA:
        if caminho.exists():
            return caminho
    nomes = ", ".join(str(c) for c in CANDIDATOS_ENTRADA)
    raise FileNotFoundError(f"Nenhum dataset encontrado. Caminhos verificados: {nomes}")


def indice_para_nome(idx: int) -> str:
    """Converte 0 -> A, 1 -> B, ..., 25 -> Z, 26 -> AA."""
    letras = []
    n = idx
    while True:
        letras.append(chr(ord("A") + (n % 26)))
        n = (n // 26) - 1
        if n < 0:
            break
    return "".join(reversed(letras))


def main() -> None:
    arquivo_entrada = localizar_entrada()
    ARQUIVO_NODES.parent.mkdir(parents=True, exist_ok=True)

    trechos: dict[str, dict] = {}
    afluentes: dict[str, list[str]] = defaultdict(list)

    with open(arquivo_entrada, "r", encoding="utf-8", newline="") as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            hid = linha["hyriv_id"].strip()
            ndown = linha["next_down"].strip()
            trechos[hid] = {
                "hyriv_id": hid,
                "next_down": ndown,
                "lat": float(linha["lat"]),
                "lon": float(linha["lon"]),
                "deficit_seca": float(linha["deficit_seca"]),
                "deficit_total": float(linha["deficit_total"]),
                "deficit_mes": float(linha["deficit_mes"]),
            }
            if ndown != "0":
                afluentes[ndown].append(hid)

    # Ordenação topológica bottom-up (Kahn) para calcular tamanho a montante e ramificações
    grau_entrada = {hid: len(afluentes[hid]) for hid in trechos}
    fila = deque([hid for hid, g in grau_entrada.items() if g == 0])

    tam_montante = {hid: 1 for hid in trechos}
    confluencias = {hid: (1 if grau_entrada[hid] >= 2 else 0) for hid in trechos}
    acum_seca = {hid: dados["deficit_seca"] for hid, dados in trechos.items()}

    while fila:
        u = fila.popleft()
        pai = trechos[u]["next_down"]
        if pai in trechos:
            tam_montante[pai] += tam_montante[u]
            confluencias[pai] += confluencias[u]
            acum_seca[pai] += acum_seca[u]
            grau_entrada[pai] -= 1
            if grau_entrada[pai] == 0:
                fila.append(pai)

    # Filtra sub-bacias entre MIN_NOS e MAX_NOS com déficit > 0 e múltiplas nascentes
    candidatos = [
        hid for hid, tam in tam_montante.items()
        if MIN_NOS <= tam <= MAX_NOS and acum_seca[hid] > 0.0 and confluencias[hid] >= 2
    ]
    if not candidatos:
        candidatos = [
            hid for hid, tam in tam_montante.items()
            if MIN_NOS <= tam <= MAX_NOS
        ]

    if not candidatos:
        raise RuntimeError(f"Nenhuma sub-bacia encontrada entre {MIN_NOS} e {MAX_NOS} trechos.")

    foz_id = max(
        candidatos,
        key=lambda hid: (confluencias[hid], -abs(tam_montante[hid] - 12), acum_seca[hid]),
    )

    # Coleta os vértices em ordem BFS a partir da Foz (A = Foz, B, C = afluentes diretos...)
    sub_nos: list[str] = []
    busca = deque([foz_id])
    while busca:
        atual = busca.popleft()
        sub_nos.append(atual)
        filhos_ordenados = sorted(
            [c for c in afluentes[atual] if c in trechos],
            key=lambda c: (-tam_montante[c], c),
        )
        for filho in filhos_ordenados:
            busca.append(filho)

    conjunto_sub = set(sub_nos)
    nomes_vertices = {hid: indice_para_nome(i) for i, hid in enumerate(sub_nos)}

    campos_nodes = [
        "Id",
        "Label",
        "hyriv_id",
        "papel",
        "deficit_seca",
        "deficit_total",
        "deficit_mes",
        "deficit_seca_montante",
        "trechos_montante",
        "grau_entrada",
        "grau_saida",
        "lat",
        "lon",
    ]

    total_edges = 0
    resumo_vertices = []

    with (
        open(ARQUIVO_NODES, "w", encoding="utf-8", newline="") as f_nodes,
        open(ARQUIVO_EDGES, "w", encoding="utf-8", newline="") as f_edges,
    ):
        escritor_nodes = csv.DictWriter(f_nodes, fieldnames=campos_nodes)
        escritor_edges = csv.writer(f_edges)

        escritor_nodes.writeheader()
        escritor_edges.writerow(["Source", "Target", "Type", "Weight"])

        for hid in sub_nos:
            d = trechos[hid]
            filhos_no_recorte = [c for c in afluentes[hid] if c in conjunto_sub]
            g_in = len(filhos_no_recorte)
            g_out = 0 if hid == foz_id else 1

            if hid == foz_id:
                papel = "Foz"
            elif g_in == 0:
                papel = "Nascente"
            else:
                papel = "Afluente"

            nome = nomes_vertices[hid]
            escritor_nodes.writerow({
                "Id": hid,
                "Label": nome,
                "hyriv_id": hid,
                "papel": papel,
                "deficit_seca": f"{d['deficit_seca']:.4f}",
                "deficit_total": f"{d['deficit_total']:.4f}",
                "deficit_mes": f"{d['deficit_mes']:.4f}",
                "deficit_seca_montante": f"{acum_seca[hid]:.4f}",
                "trechos_montante": tam_montante[hid],
                "grau_entrada": g_in,
                "grau_saida": g_out,
                "lat": f"{d['lat']:.6f}",
                "lon": f"{d['lon']:.6f}",
            })

            resumo_vertices.append((nome, hid, papel, g_in, g_out, d["deficit_seca"], acum_seca[hid]))

            destino = d["next_down"]
            if hid != foz_id and destino in conjunto_sub:
                escritor_edges.writerow([hid, destino, "Directed", 1])
                total_edges += 1

    print("=" * 74)
    print("SUB-BACIA EXPORTADA PARA O GEPHI (PESOS E PAPÉIS NOS VÉRTICES)")
    print("=" * 74)
    print(f"Dataset de origem   : {arquivo_entrada}")
    print(f"Foz (raiz)          : Vértice {nomes_vertices[foz_id]} (hyriv_id = {foz_id})")
    print(f"Vértices exportados : {len(sub_nos)} | Arestas direcionadas: {total_edges} (Weight = 1)")
    print(f"Arquivo de nós      : {ARQUIVO_NODES}")
    print(f"Arquivo de arestas  : {ARQUIVO_EDGES}")
    print("-" * 74)
    print(f"{'Nome':<5} {'hyriv_id':<12} {'Papel':<10} {'In':>3} {'Out':>4} {'Déficit Nó':>14} {'Acum. Montante':>16}")
    print("-" * 74)
    for nome, hid, papel, g_in, g_out, def_no, def_acum in resumo_vertices:
        print(f"{nome:<5} {hid:<12} {papel:<10} {g_in:>3} {g_out:>4} {def_no:>14,.2f} {def_acum:>16,.2f}")
    print("=" * 74)


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print(f"[ERRO] {erro}", file=sys.stderr)
        sys.exit(1)