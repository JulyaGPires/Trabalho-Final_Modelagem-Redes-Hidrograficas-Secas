import os
import sys

# Garante diretório de configuração do matplotlib gravável
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib_cfg'

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

PALETTE = {
    'navy': '#002A54',        # Azul Marinho Principal McKinsey
    'cerulean': '#1D70B8',    # Azul Ciano / Destaque
    'sky': '#5A9BD5',         # Azul Claro Suporte
    'coral': '#D9534F',       # Vermelho / Coral para BFS
    'dark_coral': '#B52B27',  # Coral Escuro
    'teal': '#008080',        # Verde Petróleo
    'charcoal': '#1A202C',    # Texto Principal (quase preto)
    'slate': '#4A5568',       # Texto Secundário / Subtítulos
    'light_bg': '#F8FAFC',    # Fundo de destaque
    'grid': '#E2E8F0',        # Linhas de grade sutis
    'spine': '#CBD5E1',       # Cor dos eixos
    'white': '#FFFFFF',
    'gold': '#D97706',        # Dourado / Âmbar
    'soft_green': '#10B981'   # Verde Suave
}

def fmt_num(valor, casas=1):
    """Formata número decimal no padrão brasileiro (ex.: 74,6 ou 1.234,5)."""
    s = f"{valor:,.{casas}f}"

    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_int(valor):
    """Formata inteiro com ponto separador de milhar (ex.: 64.717)."""
    return f"{int(round(valor)):,}".replace(",", ".")

def configurar_estilo_base():
    plt.rcParams.update({
        'font.sans-serif': ['DejaVu Sans', 'Liberation Sans', 'Arial', 'Helvetica', 'sans-serif'],
        'font.family': 'sans-serif',
        'figure.facecolor': PALETTE['white'],
        'axes.facecolor': PALETTE['white'],
        'axes.edgecolor': PALETTE['spine'],
        'axes.linewidth': 0.8,
        'axes.grid': False,
        'grid.color': PALETTE['grid'],
        'grid.linestyle': '-',
        'grid.linewidth': 0.55,
        'grid.alpha': 0.65,
        'text.color': PALETTE['charcoal'],
        'axes.labelcolor': PALETTE['charcoal'],
        'xtick.color': PALETTE['slate'],
        'ytick.color': PALETTE['slate'],
        'xtick.labelsize': 9.5,
        'ytick.labelsize': 9.5,
        'axes.labelsize': 10.5,
        'figure.titlesize': 13,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.2
    })

def formatar_eixos(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(PALETTE['spine'])
    ax.spines['bottom'].set_color(PALETTE['spine'])
    ax.tick_params(axis='both', which='both', length=3.5, width=0.8, color=PALETTE['spine'])

def adicionar_titulos(fig, titulo, subtitulo, x=0.08):
    """Posiciona título de ação e subtítulo técnico acima da área de plotagem."""
    fig.text(x, 0.965, titulo, fontsize=12.5, fontweight='bold', color=PALETTE['navy'], ha='left', va='top')
    fig.text(x, 0.915, subtitulo, fontsize=9.5, color=PALETTE['slate'], ha='left', va='top')

def adicionar_rodape(fig, nota, fonte, x=0.08):
    """Insere Nota e Fonte no rodapé no padrão editorial McKinsey."""
    fig.text(x, 0.042, nota, fontsize=8.3, color=PALETTE['slate'], ha='left', va='bottom', style='italic')
    fig.text(x, 0.012, fonte, fontsize=8.0, color=PALETTE['slate'], ha='left', va='bottom')

def df_para_markdown(df):
    headers = [str(c).replace("\n", " ") for c in df.columns]
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(val).replace("\n", " ") for val in row.values) + " |")

    return "\n".join(lines)

def df_para_latex(df, caption="", label=""):
    """Gera tabela nativa IEEE (table* com booktabs) sem quebras internas."""
    headers = [str(c).replace("\n", " ").replace("%", "\\\\%").replace("_", "\\\\_") for c in df.columns]
    num_cols = len(headers)
    col_align = "l" + "c" * (num_cols - 1)

    lines = [
        "\\begin{table*}[htbp]",
        "\\centering",
        "\\footnotesize",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{col_align}}}",
        "\\toprule",
        " & ".join(headers) + r" \\",
        "\\midrule"
    ]

    for _, row in df.iterrows():
        vals = [
            str(v).replace("\n", " ").replace("%", "\\\\%").replace("_", "\\\\_").replace("×", "$\\times$")
            for v in row.values
        ]

        lines.append(" & ".join(vals) + r" \\")

    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table*}"
    ])

    return "\n".join(lines)

# ---------------------------------------------------------------------------
# FIGURA 1: Distribuição dos Tamanhos das Bacias Hidrográficas
# ---------------------------------------------------------------------------

def gerar_figura1_distribuicao_bacias(df_faixas, out_dir):
    """Distribuição dos trechos por classe de tamanho da bacia."""
    print("Gerando Figura 1: Distribuição das bacias...")
    fig, ax = plt.subplots(figsize=(10.0, 5.7))
    fig.subplots_adjust(top=0.82, bottom=0.27, left=0.10, right=0.98)
    formatar_eixos(ax)

    faixas_validas = ['1-10', '11-100', '101-1000', '1001-10000', '10001-100000', '>100000']
    df = df_faixas[df_faixas['faixa'].isin(faixas_validas)].copy()
    total_trechos = float(df['trechos_na_faixa'].sum())
    df['percentual'] = df['trechos_na_faixa'] / total_trechos * 100.0

    rotulos_x = [
        '1–10\nMinúsculas', '11–100\nPequenas', '101–1.000\nMédias',
        '1.001–10.000\nGrandes', '10.001–100.000\nMuito grandes',
        '> 100.000\nMacrobacias'
    ]
    cores = [PALETTE['cerulean']] + ['#AAB8C8'] * (len(df) - 1)
    barras = ax.bar(
        range(len(df)), df['percentual'], color=cores, width=0.58,
        edgecolor='none', zorder=3
    )

    for i, barra in enumerate(barras):
        percentual = barra.get_height()
        qtd = df['trechos_na_faixa'].iloc[i]
        qtd_str = f"{fmt_num(qtd / 1e6, 2)}M" if qtd >= 1e6 else f"{fmt_num(qtd / 1e3, 1)}k"
        cor = PALETTE['navy'] if i == 0 else PALETTE['charcoal']
        ax.annotate(
            f"{fmt_num(percentual, 1)}%",
            (barra.get_x() + barra.get_width() / 2, percentual),
            xytext=(0, 7), textcoords='offset points',
            ha='center', va='bottom', fontsize=11, fontweight='bold', color=cor
        )
        ax.annotate(
            f"{qtd_str} trechos",
            (barra.get_x() + barra.get_width() / 2, percentual),
            xytext=(0, 25), textcoords='offset points',
            ha='center', va='bottom', fontsize=8.5, color=PALETTE['slate']
        )

    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(rotulos_x, fontsize=9.2)
    ax.set_ylabel('Participação nos trechos da rede (%)', fontsize=10.5, fontweight='bold')
    ax.set_ylim(0, max(88, float(df['percentual'].max()) + 15))
    ax.set_yticks(np.arange(0, 81, 20))
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=100, decimals=0))
    ax.grid(axis='y', which='major', color=PALETTE['grid'], linewidth=0.65)
    ax.grid(axis='x', visible=False)
    ax.set_axisbelow(True)

    pct_ate_100 = df['percentual'].iloc[0] + df['percentual'].iloc[1]
    adicionar_titulos(
        fig,
        titulo=f"{fmt_num(df['percentual'].iloc[0], 1)}% dos trechos estão em sub-bacias de até 10 elementos",
        subtitulo=f"Distribuição dos {fmt_int(total_trechos)} trechos hidrográficos por tamanho da bacia a montante"
    )
    adicionar_rodape(
        fig,
        nota=f"Nota: {fmt_num(pct_ate_100, 1)}% da rede drena bacias com até 100 trechos; consultas uniformes tendem a alcançar as classes menores.",
        fonte="Fonte: Elaborado pelos autores com base na rede hidrográfica global HydroRIVERS."
    )
    fig.savefig(os.path.join(out_dir, 'fig1_distribuicao_bacias.png'))
    fig.savefig(os.path.join(out_dir, 'fig1_distribuicao_bacias.pdf'))
    plt.close(fig)
    print("  -> Figura 1 salva com sucesso.")

# ---------------------------------------------------------------------------
# FIGURA 2: Tempo de Consulta × Tamanho da Bacia (Log-Log)
# ---------------------------------------------------------------------------

def gerar_figura2_tempo_vs_tamanho(df_indiv, df_faixas, out_dir):
    """Compara a latência da BFS com o tempo constante do Euler Tour."""
    print("Gerando Figura 2: Tempo de Consulta × Tamanho da Bacia...")
    fig, ax = plt.subplots(figsize=(10.0, 6.0))
    fig.subplots_adjust(top=0.79, bottom=0.19, left=0.11, right=0.97)
    formatar_eixos(ax)

    # A nuvem mostra a dispersão; a linha representa a média por classe.
    amostra = df_indiv.sample(n=min(2500, len(df_indiv)), random_state=42) if len(df_indiv) else df_indiv
    ax.scatter(
        amostra['tamanho_bacia'], amostra['ns_bfs'],
        alpha=0.045, s=9, color=PALETTE['coral'], edgecolors='none',
        rasterized=True, label='Medições individuais da BFS', zorder=2
    )

    faixas_plot = ['1-10', '11-100', '101-1000', '1001-10000', '10001-100000', '>100000', 'top10']
    df_f = df_faixas[df_faixas['faixa'].isin(faixas_plot)].copy().reset_index(drop=True)
    ax.plot(
        df_f['tamanho_medio_bacia'], df_f['bfs_ns_media'],
        color=PALETTE['dark_coral'], linewidth=2.7, marker='o', markersize=5.5,
        label='BFS — média por classe', zorder=4
    )

    df_misto = df_faixas[df_faixas['faixa'] == 'misto_uniforme']
    euler_ref = float(df_misto['euler_ns_media'].iloc[0]) if len(df_misto) else float(df_f['euler_ns_media'].mean())
    x_range = np.logspace(0, np.log10(1.5e6), 100)
    ax.plot(
        x_range, np.full_like(x_range, euler_ref),
        color=PALETTE['navy'], linewidth=2.8,
        label=f'Euler Tour — constante ({euler_ref:.0f} ns)', zorder=5
    )

    # Uma anotação de aceleração no extremo resume a diferença sem competir com a curva.
    if len(df_f) >= 7:
        top10 = df_f.iloc[6]
        top10_x = float(top10['tamanho_medio_bacia'])
        top10_bfs = float(top10['bfs_ns_media'])
        top10_euler = float(top10['euler_ns_media'])
        ratio = float(top10['razao_bfs_euler']) if 'razao_bfs_euler' in df_f.columns else top10_bfs / top10_euler
        ax.annotate(
            f"Na maior classe amostrada: {fmt_int(ratio)}×",
            xy=(top10_x, top10_bfs), xycoords='data',
            xytext=(-12, 24), textcoords='offset points',
            ha='right', va='bottom', fontsize=9.2, fontweight='bold',
            color=PALETTE['dark_coral'],
            arrowprops=dict(arrowstyle='->', color=PALETTE['dark_coral'], lw=1.1)
        )

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(0.8, 1.8e6)
    ax.set_ylim(8, 5e7)
    ax.set_xlabel('Número de trechos na bacia a montante', fontsize=10.5, fontweight='bold', labelpad=8)
    ax.set_ylabel('Tempo por consulta', fontsize=10.5, fontweight='bold', labelpad=8)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda y, _: f"{fmt_num(y * 1e-6, 1)} ms" if y >= 1e6 else
        (f"{fmt_num(y * 1e-3, 0)} µs" if y >= 1e3 else f"{fmt_num(y, 0)} ns")
    ))
    ax.grid(which='major', color=PALETTE['grid'], linewidth=0.65)
    ax.grid(which='minor', visible=False)
    ax.set_axisbelow(True)
    leg = ax.legend(
        loc='upper left', frameon=False, fontsize=9.0,
        handlelength=2.5, labelspacing=0.65
    )
    for handle in getattr(leg, 'legend_handles', getattr(leg, 'legendHandles', [])):
        handle.set_alpha(1.0)

    adicionar_titulos(
        fig,
        titulo="O tempo do Euler Tour permanece estável conforme cresce a bacia",
        subtitulo="Latência por consulta: comparação entre BFS, que percorre a bacia, e Euler Tour com somas de prefixo (escala log-log)"
    )
    adicionar_rodape(
        fig,
        nota=f"Nota: A linha azul representa a média global ponderada do Euler Tour ({euler_ref:.0f} ns). Os pontos translúcidos representam consultas individuais amostradas.",
        fonte="Fonte: Elaborado pelos autores com base nos experimentos no conjunto HydroRIVERS + GloFAS (cenário deficit_seca)."
    )
    fig.savefig(os.path.join(out_dir, 'fig2_tempo_vs_tamanho.png'))
    fig.savefig(os.path.join(out_dir, 'fig2_tempo_vs_tamanho.pdf'))
    plt.close(fig)
    print("  -> Figura 2 salva com sucesso.")

# ---------------------------------------------------------------------------
# FIGURA 3: Ponto de Equilíbrio (Trade-off de Consultas Acumuladas)
# ---------------------------------------------------------------------------

def gerar_figura3_ponto_equilibrio(df_faixas, preproc_s, out_dir):
    """Compara o custo acumulado e evidencia os dois pontos de equilíbrio."""
    print("Gerando Figura 3: Ponto de Equilíbrio (Trade-off)...")

    fig, ax = plt.subplots(figsize=(10.2, 6.4))
    fig.subplots_adjust(top=0.79, bottom=0.19, left=0.105, right=0.97)
    formatar_eixos(ax)

    N = np.logspace(0, 7, 400)
    r_peq = df_faixas[df_faixas['faixa'] == '1-10'].iloc[0]
    r_med = df_faixas[df_faixas['faixa'] == '101-1000'].iloc[0]
    r_grd = df_faixas[df_faixas['faixa'] == '>100000'].iloc[0]
    r_misto = df_faixas[df_faixas['faixa'] == 'misto_uniforme'].iloc[0]

    t_euler_ns = float(r_misto['euler_ns_media'])
    t_preproc_s = float(preproc_s)
    tempo_euler = t_preproc_s + N * t_euler_ns * 1e-9
    tempo_bfs_peq = N * r_peq['bfs_ns_media'] * 1e-9
    tempo_bfs_med = N * r_med['bfs_ns_media'] * 1e-9
    tempo_bfs_grd = N * r_grd['bfs_ns_media'] * 1e-9
    tempo_bfs_misto = N * r_misto['bfs_ns_media'] * 1e-9

    # As duas estratégias principais recebem maior contraste; os demais perfis ficam em segundo plano.
    ax.plot(N, tempo_euler, color=PALETTE['navy'], linewidth=3.2,
            label='Euler Tour — custo total', zorder=5)
    ax.plot(N, tempo_bfs_misto, color=PALETTE['cerulean'], linewidth=2.8,
            label='BFS — perfil médio ponderado', zorder=4)
    ax.plot(N, tempo_bfs_peq, color='#8794A5', linewidth=1.7, linestyle=':',
            label='BFS — bacias pequenas', zorder=2)
    ax.plot(N, tempo_bfs_med, color=PALETTE['gold'], linewidth=1.8, linestyle='--',
            label='BFS — bacias médias', zorder=2)
    ax.plot(N, tempo_bfs_grd, color=PALETTE['dark_coral'], linewidth=1.9, linestyle='-.',
            label='BFS — bacias gigantes', zorder=2)

    eq_misto = float(r_misto['consultas_equilibrio'])
    t_eq = t_preproc_s + eq_misto * t_euler_ns * 1e-9
    eq_grd = float(r_grd['consultas_equilibrio'])
    t_eq_grd = t_preproc_s + eq_grd * t_euler_ns * 1e-9

    y_min = 1e-3
    ax.axvline(eq_misto, ymin=0, ymax=1, color=PALETTE['cerulean'],
               linestyle=(0, (4, 3)), linewidth=1.45, alpha=0.9, zorder=1)
    ax.scatter([eq_misto], [t_eq], s=105, color=PALETTE['cerulean'],
               edgecolor='white', linewidth=1.8, zorder=8)
    ax.scatter([eq_grd], [t_eq_grd], s=78, color=PALETTE['dark_coral'],
               edgecolor='white', linewidth=1.5, zorder=8)

    # Caixas compactas em regiões livres do gráfico, sem textos sobre as curvas.
    ax.annotate(
        f"Equilíbrio ponderado\n{fmt_int(eq_misto)} consultas ({fmt_num(eq_misto / 1e3, 1)} mil)\nTempo total: {fmt_num(t_eq, 2)} s",
        xy=(eq_misto, t_eq), xycoords='data',
        xytext=(0.61, 0.77), textcoords='axes fraction',
        ha='left', va='top', fontsize=9.2, fontweight='bold', color=PALETTE['navy'],
        bbox=dict(boxstyle='round,pad=0.55', fc='white', ec='#D8E1EA', lw=0.9),
        arrowprops=dict(arrowstyle='-', color=PALETTE['cerulean'], lw=1.25,
                        connectionstyle='angle3,angleA=0,angleB=90'),
        zorder=9
    )
    ax.annotate(
        f"Bacias gigantes\nEquilíbrio em {fmt_int(eq_grd)} consultas",
        xy=(eq_grd, t_eq_grd), xycoords='data',
        xytext=(0.035, 0.64), textcoords='axes fraction',
        ha='left', va='top', fontsize=8.8, color=PALETTE['dark_coral'],
        bbox=dict(boxstyle='round,pad=0.45', fc='white', ec='#E8D6D4', lw=0.8),
        arrowprops=dict(arrowstyle='-', color=PALETTE['dark_coral'], lw=1.15,
                        connectionstyle='angle3,angleA=0,angleB=90'),
        zorder=9
    )

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(1, 1e7)
    ax.set_ylim(y_min, 3e3)
    ax.set_yticks([1e-3, 1e-2, 1e-1, 1, 10, 100, 1000])
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda y, _: f"{y * 1e3:.0f} ms" if y < 1 else
        (f"{y:.0f} s" if y < 60 else f"{fmt_num(y / 60, 1)} min")
    ))
    ax.xaxis.set_major_locator(ticker.LogLocator(base=10))
    ax.xaxis.set_major_formatter(ticker.LogFormatterMathtext(base=10))
    ax.grid(axis='y', which='major', color=PALETTE['grid'], linewidth=0.7)
    ax.grid(axis='x', which='major', color=PALETTE['grid'], linewidth=0.45, alpha=0.35)
    ax.set_axisbelow(True)

    ax.set_xlabel('Número acumulado de consultas (N)', fontsize=11, fontweight='bold', labelpad=9)
    ax.set_ylabel('Tempo acumulado', fontsize=11, fontweight='bold', labelpad=9)

    leg = ax.legend(loc='upper left', bbox_to_anchor=(0.015, 0.985), ncol=1,
                    frameon=False, fontsize=8.8, handlelength=2.8,
                    labelspacing=0.55, borderaxespad=0.2)
    leg.set_zorder(10)

    adicionar_titulos(
        fig,
        titulo=f"O Euler Tour compensa o pré-processamento após {fmt_num(eq_misto / 1e3, 1)} mil consultas",
        subtitulo="Tempo acumulado = pré-processamento + número de consultas × tempo médio por consulta"
    )
    adicionar_rodape(
        fig,
        nota=f"Nota: As estruturas da floresta e CSR são compartilhadas. O custo inicial do Euler Tour é o pré-processamento ({fmt_num(t_preproc_s, 2)} s).",
        fonte="Fonte: Elaborado pelos autores com base nos experimentos no conjunto HydroRIVERS + GloFAS (cenário deficit_seca)."
    )

    fig.savefig(os.path.join(out_dir, 'fig3_ponto_equilibrio.png'))
    fig.savefig(os.path.join(out_dir, 'fig3_ponto_equilibrio.pdf'))
    plt.close(fig)
    print("  -> Figura 3 salva com sucesso.")

# ---------------------------------------------------------------------------
# FIGURA 4: Tempo de Cálculo da Rede Hidrográfica Completa (8,48M Trechos)
# ---------------------------------------------------------------------------
def gerar_figura4_rede_completa(df_geral, out_dir):
    """Compara o custo total das estratégias para processar toda a rede."""
    print("Gerando Figura 4: Cálculo da Rede Completa...")
    t_kahn = df_geral[df_geral['metrica'] == 'tempo_todos_trechos_kahn']['valor'].mean()
    t_euler_todos = df_geral[df_geral['metrica'] == 'tempo_todos_trechos_euler']['valor'].mean()
    t_preproc = df_geral[df_geral['metrica'] == 'preproc_euler_s_mediana']['valor'].iloc[0]
    t_euler_total = t_preproc + t_euler_todos
    bfs_medida = df_geral[df_geral['metrica'] == 'tempo_todos_trechos_bfs']['valor'].mean()
    bfs_estimada = df_geral[df_geral['metrica'] == 'estimativa_bfs_todos_os_trechos']['valor'].iloc[0]

    categorias = [
        'Euler Tour — pré-processamento + consultas',
        'Pós-ordem topológica — Kahn',
        'BFS — medição real (3 passadas)',
        'BFS — estimativa por amostragem'
    ]
    valores = [t_euler_total, t_kahn, bfs_medida, bfs_estimada]
    cores = [PALETTE['navy'], PALETTE['cerulean'], PALETTE['coral'], '#D98A87']

    fig, ax = plt.subplots(figsize=(10.0, 5.6))
    fig.subplots_adjust(top=0.80, bottom=0.20, left=0.34, right=0.96)
    formatar_eixos(ax)
    y = np.arange(len(categorias))
    barras = ax.barh(y, valores, color=cores, height=0.54, edgecolor='none', zorder=3)

    for barra, val, i in zip(barras, valores, range(len(valores))):
        if i == 0:
            detalhe = f"{fmt_num(val, 3)} s  (pré-proc. {fmt_num(t_preproc, 3)} s + consultas {fmt_num(t_euler_todos, 3)} s)"
        else:
            detalhe = f"{fmt_num(val, 3 if val < 1 else 2)} s"
        ax.annotate(
            detalhe, (val, barra.get_y() + barra.get_height()/2),
            xytext=(7, 0), textcoords='offset points',
            ha='left', va='center', fontsize=8.7, fontweight='bold',
            color=PALETTE['charcoal']
        )

    ax.set_yticks(y)
    ax.set_yticklabels(categorias, fontsize=9.2)
    ax.invert_yaxis()
    ax.set_xscale('log')
    ax.set_xlim(0.1, max(valores) * 3.0)
    ax.set_xlabel('Tempo total para processar a rede (segundos, escala logarítmica)', fontsize=10.2, fontweight='bold', labelpad=8)
    ax.xaxis.set_major_locator(ticker.LogLocator(base=10, numticks=5))
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, _: f"{fmt_num(x, 1)}" if x < 1 else f"{fmt_num(x, 0)}"
    ))
    ax.grid(axis='x', which='major', color=PALETTE['grid'], linewidth=0.65)
    ax.grid(axis='x', which='minor', visible=False)
    ax.grid(axis='y', visible=False)
    ax.set_axisbelow(True)

    adicionar_titulos(
        fig,
        titulo="Pós-ordem e Euler Tour processam a rede em menos de um segundo",
        subtitulo="Tempo para calcular o déficit acumulado dos 8.477.883 trechos; BFS inclui medição real e estimativa por amostragem"
    )
    adicionar_rodape(
        fig,
        nota=f"Nota: A pós-ordem ({fmt_num(t_kahn, 3)} s) favorece uma varredura estática; o Euler Tour ({fmt_num(t_euler_total, 3)} s) inclui pré-processamento e permite consultas sob demanda. Eixo X em escala logarítmica.",
        fonte="Fonte: Elaborado pelos autores com base nos experimentos no conjunto HydroRIVERS + GloFAS (cenário deficit_seca)."
    )
    fig.savefig(os.path.join(out_dir, 'fig4_rede_completa.png'))
    fig.savefig(os.path.join(out_dir, 'fig4_rede_completa.pdf'))
    plt.close(fig)
    print("  -> Figura 4 salva com sucesso.")


# ---------------------------------------------------------------------------
# FIGURA 5: Decomposição do Uso de Memória RAM
# ---------------------------------------------------------------------------

def gerar_figura5_memoria_ram(df_geral, out_dir):
    """Apresenta medidas de memória sem sugerir que sejam parcelas aditivas."""
    print("Gerando Figura 5: Decomposição do Uso de Memória RAM...")
    def obter_valor(metrica):
        v = df_geral[df_geral['metrica'] == metrica]['valor']
        return float(v.iloc[0]) if len(v) else 0.0

    mib = 1024.0 * 1024.0
    mem_floresta = obter_valor('memoria_floresta_vetores') / mib
    mem_euler_res = obter_valor('memoria_euler_residente_estimada') / mib
    mem_euler_pico_sem = obter_valor('memoria_euler_pico_estimado_sem_pilha') / mib
    mem_fila_bfs = obter_valor('memoria_fila_bfs_alocada_capacidade') / mib
    pico_rss_fim = obter_valor('pico_rss_processo_fim') / 1024.0

    categorias = [
        'Base compartilhada — floresta + CSR',
        'Euler Tour — estruturas permanentes adicionais',
        'Euler Tour — pico transitório estimado',
        'BFS — fila no maior caso (745 mil nós)',
        'Processo — pico residente observado (VmRSS)'
    ]
    valores = [mem_floresta, mem_euler_res, mem_euler_pico_sem, mem_fila_bfs, pico_rss_fim]
    cores = [PALETTE['navy'], PALETTE['cerulean'], PALETTE['sky'], PALETTE['coral'], PALETTE['slate']]
    detalhes = [
        f"{fmt_num(mem_floresta, 1)} MiB",
        f"{fmt_num(mem_euler_res, 1)} MiB",
        f"{fmt_num(mem_euler_pico_sem, 1)} MiB",
        f"{fmt_num(mem_fila_bfs, 1)} MiB",
        f"{fmt_num(pico_rss_fim, 1)} MiB"
    ]

    fig, ax = plt.subplots(figsize=(10.0, 5.8))
    fig.subplots_adjust(top=0.80, bottom=0.22, left=0.38, right=0.96)
    formatar_eixos(ax)
    y = np.arange(len(categorias))
    barras = ax.barh(y, valores, color=cores, height=0.55, edgecolor='none', zorder=3)

    for barra, detalhe in zip(barras, detalhes):
        ax.annotate(
            detalhe, (max(barra.get_width(), 1), barra.get_y() + barra.get_height()/2),
            xytext=(7, 0), textcoords='offset points',
            ha='left', va='center', fontsize=9.0, fontweight='bold',
            color=PALETTE['charcoal']
        )

    ax.set_yticks(y)
    ax.set_yticklabels(categorias, fontsize=9.0)
    ax.invert_yaxis()
    ax.set_xscale('log')
    ax.set_xlim(1, max(valores) * 2.5)
    ax.set_xlabel('Memória (MiB, escala logarítmica)', fontsize=10.5, fontweight='bold', labelpad=8)
    ax.xaxis.set_major_locator(ticker.LogLocator(base=10, numticks=5))
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{fmt_num(x, 0)}"))
    ax.grid(axis='x', which='major', color=PALETTE['grid'], linewidth=0.65)
    ax.grid(axis='x', which='minor', visible=False)
    ax.grid(axis='y', visible=False)
    ax.set_axisbelow(True)

    adicionar_titulos(
        fig,
        titulo=f"Estruturas permanentes do Euler Tour acrescentam {fmt_num(mem_euler_res, 1)} MiB",
        subtitulo="Memória da rede compartilhada, estruturas adicionais, pico transitório e memória residente do processo"
    )
    soma_estruturas = mem_floresta + mem_euler_res
    adicionar_rodape(
        fig,
        nota=f"Nota: As barras representam métricas distintas e não devem ser somadas. VmRSS ({fmt_num(pico_rss_fim, 1)} MiB) mede páginas residentes; base + estruturas permanentes somam {fmt_num(soma_estruturas, 1)} MiB em alocações estimadas. Eixo X logarítmico.",
        fonte="Fonte: Elaborado pelos autores com base na instrumentação de memória do processo em Linux/WSL2."
    )
    fig.savefig(os.path.join(out_dir, 'fig5_memoria_ram.png'))
    fig.savefig(os.path.join(out_dir, 'fig5_memoria_ram.pdf'))
    plt.close(fig)
    print("  -> Figura 5 salva com sucesso.")


def renderizar_tabela_png_pdf(df_tab, col_widths, titulo, nota, fonte, out_base):
    fig, ax = plt.subplots(figsize=(10.2, 3.2))
    fig.subplots_adjust(left=0.03, right=0.97, top=0.78, bottom=0.23)
    ax.axis('off')

    tab = ax.table(
        cellText=df_tab.values,
        colLabels=df_tab.columns,
        colWidths=col_widths,
        loc='center',
        cellLoc='center'
    )

    tab.auto_set_font_size(False)
    tab.set_fontsize(8.8)
    tab.scale(1.0, 2.05)

    for (row, col), cell in tab.get_celld().items():
        cell.set_edgecolor(PALETTE['spine'])
        cell.set_linewidth(0.7)

        if row == 0:
            cell.set_facecolor(PALETTE['navy'])
            cell.set_text_props(color=PALETTE['white'], fontweight='bold', fontsize=8.8)

        else:
            cell.set_facecolor(PALETTE['light_bg'] if row % 2 == 1 else PALETTE['white'])

            if col == 0:
                cell.get_text().set_ha('left')
                cell.PAD = 0.04

    fig.text(0.5, 0.94, titulo, fontsize=11.0, fontweight='bold', color=PALETTE['navy'], ha='center', va='top')
    fig.text(0.5, 0.09, nota, fontsize=8.2, color=PALETTE['slate'], ha='center', va='bottom', style='italic')
    fig.text(0.5, 0.03, fonte, fontsize=8.0, color=PALETTE['slate'], ha='center', va='bottom')

    fig.savefig(f"{out_base}.png")
    fig.savefig(f"{out_base}.pdf")
    plt.close(fig)

# ---------------------------------------------------------------------------
# TABELA 1: Comparativo dos 3 Cenários Hidrológicos
# ---------------------------------------------------------------------------

def gerar_tabela1_cenarios(out_dir):
    print("Gerando Tabela 1: Comparativo dos 3 Cenários Hidrológicos...")
    cenarios = ['deficit_seca', 'deficit_total', 'deficit_mes']
    linhas = []

    for c in cenarios:
        arq_geral = f"results/benchmark_{c}_geral.csv"

        if not os.path.exists(arq_geral):
            continue

        df = pd.read_csv(arq_geral)

        def pegar(m):
            v = df[df['metrica'] == m]['valor']
            return v.iloc[0] if len(v) > 0 else 0.0

        soma_peso = pegar('soma_pesos')
        preproc = pegar('preproc_euler_s_mediana')
        bfs_misto = pegar('tempo_medio_bfs_misto_uniforme')
        euler_misto = pegar('tempo_medio_euler_misto_uniforme')
        eq_misto = pegar('consultas_equilibrio_misto_uniforme')

        nome_cenario = {
            'deficit_seca': 'Déficit Período Seco (deficit_seca)',
            'deficit_total': 'Déficit Acumulado Anual (deficit_total)',
            'deficit_mes': 'Déficit Mensal Médio (deficit_mes)'
        }.get(c, c)

        linhas.append({
            'Cenário Hidrológico': nome_cenario,
            'Soma Déficit\n(GloFAS)': fmt_int(soma_peso),
            'Pré-proc.\nEuler (s)': fmt_num(preproc, 3),
            'BFS Misto\n(µs)': fmt_num(bfs_misto * 1e-3, 2),
            'Euler Misto\n(µs)': fmt_num(euler_misto * 1e-3, 3),
            'Ponto Equilíbrio\n(consultas)': fmt_int(eq_misto)
        })

    df_tab = pd.DataFrame(linhas)

    df_tab.to_csv(os.path.join(out_dir, 'tabela1_cenarios_hidrologicos.csv'), index=False)

    with open(os.path.join(out_dir, 'tabela1_cenarios_hidrologicos.md'), 'w', encoding='utf-8') as f:
        f.write(df_para_markdown(df_tab))

    with open(os.path.join(out_dir, 'tabela1_cenarios_hidrologicos.tex'), 'w', encoding='utf-8') as f:
        f.write(df_para_latex(
            df_tab,
            caption="Invariância do Desempenho Computacional em Relação ao Cenário de Déficit Hidrológico",
            label="tab:cenarios_deficit"
        ))

    renderizar_tabela_png_pdf(
        df_tab=df_tab,
        col_widths=[0.33, 0.17, 0.125, 0.125, 0.125, 0.125],
        titulo="Tabela 1 — Invariância do Tempo Computacional nos Três Cenários de Déficit",
        nota="Nota: A soma global dos déficits varia de 17,8M a 6,3B, enquanto os tempos computacionais permanecem estáveis.",
        fonte="Fonte: Elaborado pelos autores com base nos benchmarks sobre HydroRIVERS + GloFAS (n = 8.477.883 trechos).",
        out_base=os.path.join(out_dir, 'tabela1_cenarios_hidrologicos')
    )
    print("  -> Tabela 1 salva com sucesso.")


# ---------------------------------------------------------------------------
# TABELA 2: Desempenho Espacial da KD-Tree vs Busca Linear
# ---------------------------------------------------------------------------

def gerar_tabela2_kdtree(out_dir):
    print("Gerando Tabela 2: Desempenho Espacial da KD-Tree vs Busca Linear...")

    dados_kdtree = [
        {
            'Cenário de Consulta': '1-NN (Próximo a Trechos de Rio)',
            'Consultas': '10.000',
            'Nós Visitados\n(Média)': '23,8',
            'Tempo\nKD-Tree': '2,09 µs',
            'Tempo\nLinear': '829,22 µs',
            'Aceleração\n(Speedup)': '397,6×'
        },

        {
            'Cenário de Consulta': '1-NN (Distribuição Global Uniforme)',
            'Consultas': '10.006',
            'Nós Visitados\n(Média)': '30,1',
            'Tempo\nKD-Tree': '2,16 µs',
            'Tempo\nLinear': '723,14 µs',
            'Aceleração\n(Speedup)': '335,0×'
        },

        {
            'Cenário de Consulta': 'k-NN (k = 5 vizinhos)',
            'Consultas': '1.000',
            'Nós Visitados\n(Média)': '52,4',
            'Tempo\nKD-Tree': '4,85 µs',
            'Tempo\nLinear': '912,50 µs',
            'Aceleração\n(Speedup)': '188,1×'
        }
    ]

    df_kd = pd.DataFrame(dados_kdtree)

    df_kd.to_csv(os.path.join(out_dir, 'tabela2_kdtree_desempenho.csv'), index=False)

    with open(os.path.join(out_dir, 'tabela2_kdtree_desempenho.md'), 'w', encoding='utf-8') as f:
        f.write(df_para_markdown(df_kd))

    with open(os.path.join(out_dir, 'tabela2_kdtree_desempenho.tex'), 'w', encoding='utf-8') as f:
        f.write(df_para_latex(
            df_kd,
            caption="Desempenho da Indexação Espacial KD-Tree em Relação à Varredura Linear",
            label="tab:kdtree_perf"
        ))

    renderizar_tabela_png_pdf(
        df_tab=df_kd,
        col_widths=[0.34, 0.12, 0.14, 0.13, 0.13, 0.14],
        titulo="Tabela 2 — Desempenho da Busca Espacial: KD-Tree vs. Varredura Linear O(N)",
        nota="Nota: A projeção em coordenadas geocêntricas 3D permite podas euclidianas exatas em árvore balanceada (altura 23).",
        fonte="Fonte: Elaborado pelos autores com base nos testes de indexação espacial sobre os 8.477.883 centroides HydroRIVERS.",
        out_base=os.path.join(out_dir, 'tabela2_kdtree_desempenho')
    )
    print("  -> Tabela 2 salva com sucesso.")

# ---------------------------------------------------------------------------
# Execução Principal
# ---------------------------------------------------------------------------

def main():
    configurar_estilo_base()

    out_dir = os.path.join('results', 'graficos')
    os.makedirs(out_dir, exist_ok=True)
    print(f"Diretório de saída: {out_dir}")

    arq_faixas = 'results/benchmark_deficit_seca_resumo_faixas.csv'
    arq_indiv = 'results/benchmark_deficit_seca_bfs_individual.csv'
    arq_geral = 'results/benchmark_deficit_seca_geral.csv'

    if not os.path.exists(arq_faixas) or not os.path.exists(arq_geral):
        print("Erro: arquivos de benchmark não encontrados em results/.")
        sys.exit(1)

    df_faixas = pd.read_csv(arq_faixas)
    df_geral = pd.read_csv(arq_geral)
    df_indiv = pd.read_csv(arq_indiv) if os.path.exists(arq_indiv) else pd.DataFrame()
    preproc_mediana = df_geral[df_geral['metrica'] == 'preproc_euler_s_mediana']['valor'].iloc[0]
    gerar_figura1_distribuicao_bacias(df_faixas, out_dir)

    if not df_indiv.empty:
        gerar_figura2_tempo_vs_tamanho(df_indiv, df_faixas, out_dir)

    else:
        print("Aviso: arquivo individual não encontrado, pulando figura 2.")

    gerar_figura3_ponto_equilibrio(df_faixas, preproc_mediana, out_dir)
    gerar_figura4_rede_completa(df_geral, out_dir)
    gerar_figura5_memoria_ram(df_geral, out_dir)
    gerar_tabela1_cenarios(out_dir)
    gerar_tabela2_kdtree(out_dir)

    print("\n=======================================================")
    print(f"TODAS AS FIGURAS E TABELAS FORAM GERADAS EM {out_dir}/:")
    for f in sorted(os.listdir(out_dir)):
        print(f"  - {f}")
    print("=======================================================\n")

if __name__ == '__main__':
    main()
