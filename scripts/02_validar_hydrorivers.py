
from pathlib import Path
import csv
import sqlite3


def main():
    projeto_dir = Path(__file__).resolve().parent.parent

    csv_path = (
        projeto_dir / "data" / "processed" /
        "dataset_hidrologico_global.csv"
    )

    resultados_dir = projeto_dir / "results"
    banco_path = resultados_dir / "hydrorivers_validacao.sqlite"
    relatorio_path = resultados_dir / "relatorio_hydrorivers.txt"

    tamanho_bloco = 50000

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV não encontrado: {csv_path}")

    resultados_dir.mkdir(parents=True, exist_ok=True)

    if banco_path.exists():
        raise FileExistsError(
            f"O banco já existe: {banco_path}\n"
            "Renomeie-o ou remova-o antes de executar novamente."
        )

    print("[INFO] Iniciando validação do HydroRIVERS...")
    print("[INFO] Criando banco SQLite para processamento em disco...")

    conn = sqlite3.connect(banco_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE nos (
            id INTEGER PRIMARY KEY,
            next_down INTEGER NOT NULL,
            indegree INTEGER DEFAULT 0
        )
    """)

    total_linhas = 0
    ids_invalidos = 0
    destinos_invalidos = 0
    duplicados = 0

    try:
        # -------------------------------------------------
        # ETAPA 1: IMPORTAÇÃO DOS IDENTIFICADORES
        # -------------------------------------------------

        print("\n[ETAPA 1] Importando identificadores...")

        with open(csv_path, "r", newline="", encoding="utf-8") as arquivo:
            leitor = csv.DictReader(arquivo)
            lote = []

            for linha in leitor:
                total_linhas += 1

                try:
                    hyriv_id = int(linha["hyriv_id"])
                    next_down = int(linha["next_down"])

                    if hyriv_id <= 0 or next_down < 0:
                        raise ValueError

                    lote.append((hyriv_id, next_down))

                except (ValueError, TypeError, KeyError):
                    ids_invalidos += 1
                    continue

                if len(lote) >= tamanho_bloco:
                    antes = conn.total_changes

                    cursor.executemany(
                        """
                        INSERT OR IGNORE INTO nos (id, next_down)
                        VALUES (?, ?)
                        """,
                        lote
                    )

                    duplicados += len(lote) - (
                        conn.total_changes - antes
                    )

                    conn.commit()
                    lote.clear()

                    if total_linhas % 500000 < tamanho_bloco:
                        print(
                            f"[INFO] {total_linhas:,} registros importados..."
                        )

            if lote:
                antes = conn.total_changes

                cursor.executemany(
                    """
                    INSERT OR IGNORE INTO nos (id, next_down)
                    VALUES (?, ?)
                    """,
                    lote
                )

                duplicados += len(lote) - (
                    conn.total_changes - antes
                )

                conn.commit()

        cursor.execute("SELECT COUNT(*) FROM nos")
        total_nos = cursor.fetchone()[0]

        print(f"[INFO] Linhas lidas: {total_linhas:,}")
        print(f"[INFO] IDs únicos: {total_nos:,}")
        print(f"[INFO] IDs duplicados: {duplicados:,}")

        # -------------------------------------------------
        # ETAPA 2: INDEXAÇÃO E REFERÊNCIAS
        # -------------------------------------------------

        print("\n[ETAPA 2] Verificando conexões...")

        cursor.execute("""
            CREATE INDEX idx_nos_next_down
            ON nos(next_down)
        """)

        conn.commit()

        cursor.execute("""
            SELECT COUNT(*)
            FROM nos
            WHERE next_down = 0
        """)
        terminais = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM nos AS origem
            WHERE origem.next_down <> 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM nos AS destino
                  WHERE destino.id = origem.next_down
              )
        """)
        referencias_inexistentes = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT origem.next_down)
            FROM nos AS origem
            WHERE origem.next_down <> 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM nos AS destino
                  WHERE destino.id = origem.next_down
              )
        """)
        destinos_inexistentes_distintos = cursor.fetchone()[0]

        cursor.execute("""
            SELECT origem.id, origem.next_down
            FROM nos AS origem
            WHERE origem.next_down <> 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM nos AS destino
                  WHERE destino.id = origem.next_down
              )
            LIMIT 20
        """)
        amostra_referencias = cursor.fetchall()

        print(f"[INFO] Trechos terminais: {terminais:,}")
        print(
            f"[INFO] Referências inexistentes: "
            f"{referencias_inexistentes:,}"
        )

        # -------------------------------------------------
        # ETAPA 3: PREPARAÇÃO PARA DETECÇÃO DE CICLOS
        # -------------------------------------------------

        print("\n[ETAPA 3] Calculando graus de entrada...")

        cursor.execute("""
            UPDATE nos
            SET indegree = (
                SELECT COUNT(*)
                FROM nos AS origem
                WHERE origem.next_down = nos.id
            )
        """)

        conn.commit()

        # Fila de nós que podem ser removidos.
        cursor.execute("""
            CREATE TABLE fila (
                sequencia INTEGER PRIMARY KEY AUTOINCREMENT,
                id INTEGER UNIQUE
            )
        """)

        cursor.execute("""
            INSERT INTO fila (id)
            SELECT id
            FROM nos
            WHERE indegree = 0
        """)

        conn.commit()

        cursor.execute("""
            CREATE TEMP TABLE lote_nos (
                id INTEGER PRIMARY KEY
            )
        """)

        cursor.execute("""
            CREATE TEMP TABLE lote_destinos (
                destino INTEGER PRIMARY KEY,
                quantidade INTEGER
            )
        """)

        # -------------------------------------------------
        # ETAPA 4: REMOÇÃO TOPOLÓGICA
        # -------------------------------------------------

        print("\n[ETAPA 4] Detectando ciclos na rede...")
        print("[INFO] Processando a fila em blocos...")

        removidos = 0

        while True:
            cursor.execute("""
                SELECT sequencia, id
                FROM fila
                ORDER BY sequencia
                LIMIT ?
            """, (tamanho_bloco,))

            lote_fila = cursor.fetchall()

            if not lote_fila:
                break

            ids = [registro[1] for registro in lote_fila]
            ultima_sequencia = lote_fila[-1][0]

            cursor.execute("DELETE FROM lote_nos")
            cursor.execute("DELETE FROM lote_destinos")

            cursor.executemany(
                "INSERT INTO lote_nos (id) VALUES (?)",
                [(identificador,) for identificador in ids]
            )

            cursor.execute("""
                INSERT INTO lote_destinos (destino, quantidade)
                SELECT nos.next_down, COUNT(*)
                FROM nos
                JOIN lote_nos ON lote_nos.id = nos.id
                JOIN nos AS destino
                    ON destino.id = nos.next_down
                GROUP BY nos.next_down
            """)

            # Retira da fila os nós já processados.
            cursor.execute("""
                DELETE FROM fila
                WHERE sequencia <= ?
            """, (ultima_sequencia,))

            # Cada nó removido deixa de contribuir para o
            # grau de entrada do seu destino a jusante.
            cursor.execute("""
                UPDATE nos
                SET indegree = indegree - (
                    SELECT quantidade
                    FROM lote_destinos
                    WHERE lote_destinos.destino = nos.id
                )
                WHERE id IN (
                    SELECT destino FROM lote_destinos
                )
            """)

            # Os destinos que ficaram com grau zero
            # podem ser removidos na próxima iteração.
            cursor.execute("""
                INSERT OR IGNORE INTO fila (id)
                SELECT nos.id
                FROM nos
                JOIN lote_destinos
                    ON lote_destinos.destino = nos.id
                WHERE nos.indegree = 0
            """)

            removidos += len(ids)

            conn.commit()

            if removidos % 500000 < tamanho_bloco:
                print(f"[INFO] Nós processados: {removidos:,}")

        # -------------------------------------------------
        # ETAPA 5: IDENTIFICAÇÃO DOS CICLOS
        # -------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*)
            FROM nos
            WHERE indegree > 0
        """)
        nos_em_ciclos = cursor.fetchone()[0]

        cursor.execute("""
            SELECT id, next_down
            FROM nos
            WHERE indegree > 0
            LIMIT 20
        """)
        amostra_ciclos = cursor.fetchall()

        # -------------------------------------------------
        # ETAPA 6: RESULTADOS
        # -------------------------------------------------

        relatorio = [
            "VALIDAÇÃO DO HYDRORIVERS GLOBAL",
            "=" * 45,
            "",
            f"Linhas lidas: {total_linhas:,}",
            f"IDs únicos: {total_nos:,}",
            f"IDs duplicados: {duplicados:,}",
            f"Registros inválidos: {ids_invalidos:,}",
            "",
            f"Trechos terminais (next_down = 0): {terminais:,}",
            f"Referências inexistentes: {referencias_inexistentes:,}",
            (
                "Destinos inexistentes distintos: "
                f"{destinos_inexistentes_distintos:,}"
            ),
            "",
            f"Nós removidos na análise topológica: {removidos:,}",
            f"Nós restantes em ciclos: {nos_em_ciclos:,}",
            "",
            "AMOSTRA DE REFERÊNCIAS INEXISTENTES:",
            str(amostra_referencias),
            "",
            "AMOSTRA DE NÓS RESTANTES EM CICLOS:",
            str(amostra_ciclos),
            "",
            "OBSERVAÇÃO:",
            "A remoção topológica identifica os nós que pertencem",
            "a ciclos em um grafo no qual cada nó possui no máximo",
            "uma conexão de saída. Referências inexistentes são",
            "ignoradas nessa análise de ciclos.",
        ]

        relatorio_path.write_text(
            "\n".join(relatorio),
            encoding="utf-8"
        )

        print("\n" + "=" * 45)
        print("[SUCESSO] Validação concluída!")
        print("=" * 45)

        for linha in relatorio:
            print(linha)

        print(f"\n[INFO] Relatório: {relatorio_path}")
        print(f"[INFO] Banco SQLite: {banco_path}")

    except Exception as erro:
        conn.rollback()
        print(f"\n[ERRO] Falha na validação: {erro}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
