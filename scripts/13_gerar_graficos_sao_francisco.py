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
    fig.text(x, 0.965, titulo, fontsize=12.2, fontweight='bold', color=PALETTE['navy'], ha='left', va='top')
    fig.text(x, 0.915, subtitulo, fontsize=9.3, color=PALETTE['slate'], ha='left', va='top')


def adicionar_rodape(fig, nota, fonte, x=0.08):
    """Insere Nota e Fonte no rodapé no padrão editorial McKinsey."""
    fig.text(x, 0.042, nota, fontsize=8.1, color=PALETTE['slate'], ha='left', va='bottom', style='italic')
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
    headers = [str(c).replace("\n", " ").replace("%", r"\%").replace("_", r"\_") for c in df.columns]
    num_cols = len(headers)
    col_align = "l" + "c" * (num_cols - 1)

    lines = [
        r"\begin{table*}[htbp]",
        r"\centering",
        r"\footnotesize",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{col_align}}}",
        r"\toprule",
        " & ".join(headers) + r" \\",
        r"\midrule"
    ]

    for _, row in df.iterrows():
        vals = [
            str(v).replace("\n", " ").replace("%", r"\%").replace("_", r"\_").replace("×", r"$\times$")
            for v in row.values
        ]
        lines.append(" & ".join(vals) + r" \\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}"
    ])
    return "\n".join(lines)


def renderizar_tabela_png_pdf(df_tab, col_widths, titulo, nota, fonte, out_base):
    """Renderiza tabela com altura proporcional ao número de linhas para evitar sobreposição."""
    n_linhas = len(df_tab) + 1
    margem_topo_in = 0.78
    margem_rodape_in = 0.72
    altura_linha_in = 0.38
    fig_h = max(3.4, margem_topo_in + margem_rodape_in + n_linhas * altura_linha_in)

    fig, ax = plt.subplots(figsize=(10.4, fig_h))
    top_frac = 1.0 - (margem_topo_in / fig_h)
    bot_frac = margem_rodape_in / fig_h
    fig.subplots_adjust(left=0.03, right=0.97, top=top_frac, bottom=bot_frac)
    ax.axis('off')

    tab = ax.table(
        cellText=df_tab.values,
        colLabels=df_tab.columns,
        colWidths=col_widths,
        bbox=[0.0, 0.0, 1.0, 1.0],
        cellLoc='center'
    )

    tab.auto_set_font_size(False)
    tab.set_fontsize(8.6)

    for (row, col), cell in tab.get_celld().items():
        cell.set_edgecolor(PALETTE['spine'])
        cell.set_linewidth(0.7)
        if row == 0:
            cell.set_facecolor(PALETTE['navy'])
            cell.set_text_props(color=PALETTE['white'], fontweight='bold', fontsize=8.6)
        else:
            cell.set_facecolor(PALETTE['light_bg'] if row % 2 == 1 else PALETTE['white'])
            cell.set_text_props(color=PALETTE['charcoal'], fontsize=8.5)
            if col == 0:
                cell.get_text().set_ha('left')
                cell.PAD = 0.035

    y_titulo = 1.0 - (0.22 / fig_h)
    y_nota = 0.36 / fig_h
    y_fonte = 0.12 / fig_h

    fig.text(0.5, y_titulo, titulo, fontsize=11.0, fontweight='bold', color=PALETTE['navy'], ha='center', va='top')
    fig.text(0.5, y_nota, nota, fontsize=8.1, color=PALETTE['slate'], ha='center', va='bottom', style='italic')
    fig.text(0.5, y_fonte, fonte, fontsize=8.0, color=PALETTE['slate'], ha='center', va='bottom')

    fig.savefig(f"{out_base}.png")
    fig.savefig(f"{out_base}.pdf")
    plt.close(fig)


# ---------------------------------------------------------------------------
# FIGURA 6: Latência por Consulta — Rede Global vs. Bacia do São Francisco
# ---------------------------------------------------------------------------

def gerar_figura6_latencia_escala(df_faixas_g, df_faixas_sf, df_geral_g, df_geral_sf, out_dir):
    """Compara a latência por consulta (com desvio padrão) entre escalas."""
    print("Gerando Figura 6: Latência por Consulta (Global vs. São Francisco)...")

    fig, ax = plt.subplots(figsize=(10.2, 6.2))
    fig.subplots_adjust(top=0.79, bottom=0.20, left=0.11, right=0.97)
    formatar_eixos(ax)

    faixas_disjuntas = ['1-10', '11-100', '101-1000', '1001-10000', '10001-100000', '>100000']
    fg = df_faixas_g[df_faixas_g['faixa'].isin(faixas_disjuntas)].copy()
    fsf = df_faixas_sf[df_faixas_sf['faixa'].isin(faixas_disjuntas)].copy()

    misto_g = df_faixas_g[df_faixas_g['faixa'] == 'misto_uniforme'].iloc[0]
    misto_sf = df_faixas_sf[df_faixas_sf['faixa'] == 'misto_uniforme'].iloc[0]

    mib = 1024.0 * 1024.0
    mem_euler_g = float(df_geral_g[df_geral_g['metrica'] == 'memoria_euler_residente_estimada']['valor'].iloc[0]) / mib
    mem_euler_sf = float(df_geral_sf[df_geral_sf['metrica'] == 'memoria_euler_residente_estimada']['valor'].iloc[0]) / mib

    lat_global_mista = float(misto_g['euler_ns_media'])
    lat_sf_mista = float(misto_sf['euler_ns_media'])
    ganho_cache = lat_global_mista / lat_sf_mista

    def erro_log_seguro(medias, desvios):
        y = np.asarray(medias, dtype=float)
        sd = np.nan_to_num(np.asarray(desvios, dtype=float), nan=0.0)
        inf = np.minimum(sd, y * 0.85)
        return np.vstack([inf, sd])

    # Curvas com barras de erro (±1 desvio padrão entre execuções)
    ax.errorbar(
        fg['tamanho_medio_bacia'], fg['bfs_ns_media'],
        yerr=erro_log_seguro(fg['bfs_ns_media'], fg['bfs_ns_desvio']),
        color=PALETTE['coral'], linewidth=2.0, linestyle='--', marker='s', markersize=5.0,
        capsize=3.0, elinewidth=1.0, capthick=0.9,
        label='BFS — rede global (8.477.883 trechos)', zorder=3
    )
    ax.errorbar(
        fsf['tamanho_medio_bacia'], fsf['bfs_ns_media'],
        yerr=erro_log_seguro(fsf['bfs_ns_media'], fsf['bfs_ns_desvio']),
        color=PALETTE['dark_coral'], linewidth=2.4, linestyle='-', marker='o', markersize=5.2,
        capsize=3.0, elinewidth=1.0, capthick=0.9,
        label='BFS — bacia do São Francisco (31.332 trechos)', zorder=4
    )
    ax.errorbar(
        fg['tamanho_medio_bacia'], fg['euler_ns_media'],
        yerr=erro_log_seguro(fg['euler_ns_media'], fg['euler_ns_desvio']),
        color=PALETTE['navy'], linewidth=2.1, linestyle='--', marker='s', markersize=5.0,
        capsize=3.0, elinewidth=1.0, capthick=0.9,
        label=f'Euler Tour — rede global ({fmt_num(mem_euler_g, 1)} MiB)', zorder=4
    )
    ax.errorbar(
        fsf['tamanho_medio_bacia'], fsf['euler_ns_media'],
        yerr=erro_log_seguro(fsf['euler_ns_media'], fsf['euler_ns_desvio']),
        color=PALETTE['cerulean'], linewidth=2.6, linestyle='-', marker='o', markersize=5.2,
        capsize=3.0, elinewidth=1.0, capthick=0.9,
        label=f'Euler Tour — bacia do São Francisco ({fmt_num(mem_euler_sf, 2)} MiB)', zorder=5
    )

    # Linhas horizontais nas cotas exatas das médias ponderadas (consultas uniformes)
    ax.axhline(lat_global_mista, color=PALETTE['navy'], linestyle=':', linewidth=1.25, alpha=0.85, zorder=2)
    ax.axhline(lat_sf_mista, color=PALETTE['cerulean'], linestyle=':', linewidth=1.25, alpha=0.85, zorder=2)

    # Rótulos posicionados na margem limpa à direita (x > 2,5e5), sem tocar em curvas ou barras de erro
    ax.text(
        1.0e7, lat_global_mista * 1.15,
        f"Média ponderada global: {fmt_num(lat_global_mista, 1)} ns",
        ha='right', va='bottom', fontsize=8.4, fontweight='bold', color=PALETTE['navy'], zorder=6
    )
    ax.text(
        1.0e7, lat_sf_mista * 1.18,
        f"Média ponderada São Francisco: {fmt_num(lat_sf_mista, 1)} ns",
        ha='right', va='bottom', fontsize=8.4, fontweight='bold', color=PALETTE['cerulean'], zorder=6
    )

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(1.0, 1.2e7)
    ax.set_ylim(4.0, 4.0e7)
    ax.set_xticks([1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7])
    ax.set_xlabel('Número de trechos na bacia a montante', fontsize=10.5, fontweight='bold', labelpad=8)
    ax.set_ylabel('Tempo por consulta', fontsize=10.5, fontweight='bold', labelpad=8)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda y, _: f"{fmt_num(y * 1e-6, 1)} ms" if y >= 1e6 else
        (f"{fmt_num(y * 1e-3, 0)} µs" if y >= 1e3 else f"{fmt_num(y, 0)} ns")
    ))
    ax.grid(which='major', color=PALETTE['grid'], linewidth=0.65)
    ax.grid(which='minor', visible=False)
    ax.set_axisbelow(True)

    ax.legend(
        loc='upper left', frameon=False, fontsize=8.8,
        handlelength=2.6, labelspacing=0.55
    )

    adicionar_titulos(
        fig,
        titulo=f"Recorte regional reduz a latência do Euler Tour em {fmt_num(ganho_cache, 1)}×, consistente com efeito de cache",
        subtitulo="Tempo aproximadamente constante do Euler Tour (O(1) operações) vs. crescimento linear da BFS (média ± desvio padrão)"
    )
    adicionar_rodape(
        fig,
        nota="Nota: Amostragem por execução: 1.000 consultas (faixas 1–1.000), 500 (1.001–10.000), 200 (10.001–100.000; 518 trechos no SF) e 100 (>100.000). A BFS também acelera na sub-rede.",
        fonte="Fonte: Elaborado pelos autores com base nos experimentos no conjunto HydroRIVERS + GloFAS 5.0 (cenário deficit_seca)."
    )

    fig.savefig(os.path.join(out_dir, 'fig6_comparacao_latencia_sf.png'))
    fig.savefig(os.path.join(out_dir, 'fig6_comparacao_latencia_sf.pdf'))
    plt.close(fig)
    print("  -> Figura 6 salva com sucesso.")


# ---------------------------------------------------------------------------
# FIGURA 7: Ponto de Equilíbrio sob Consultas Uniformes — Global vs. São Francisco
# ---------------------------------------------------------------------------

def gerar_figura7_equilibrio_escala(df_faixas_g, df_faixas_sf, out_dir):
    """Compara o custo acumulado e o ponto de equilíbrio sob consultas uniformes."""
    print("Gerando Figura 7: Ponto de Equilíbrio sob Consultas Uniformes (Global vs. SF)...")

    fig, ax = plt.subplots(figsize=(10.2, 6.4))
    fig.subplots_adjust(top=0.79, bottom=0.20, left=0.105, right=0.97)
    formatar_eixos(ax)

    N = np.logspace(0, 6.3, 400)

    misto_g = df_faixas_g[df_faixas_g['faixa'] == 'misto_uniforme'].iloc[0]
    misto_sf = df_faixas_sf[df_faixas_sf['faixa'] == 'misto_uniforme'].iloc[0]

    pre_g = float(misto_g['preproc_euler_s_mediana'])
    bfs_g_s = float(misto_g['bfs_ns_media']) * 1e-9
    euler_g_s = float(misto_g['euler_ns_media']) * 1e-9
    eq_g = float(misto_g['consultas_equilibrio'])
    t_eq_g = pre_g + eq_g * euler_g_s

    pre_sf = float(misto_sf['preproc_euler_s_mediana'])
    bfs_sf_s = float(misto_sf['bfs_ns_media']) * 1e-9
    euler_sf_s = float(misto_sf['euler_ns_media']) * 1e-9
    eq_sf = float(misto_sf['consultas_equilibrio'])
    t_eq_sf = pre_sf + eq_sf * euler_sf_s

    ax.plot(N, pre_g + N * euler_g_s, color=PALETTE['navy'], linewidth=2.4, linestyle='--',
            label='Euler Tour — rede global (custo total)', zorder=4)
    ax.plot(N, N * bfs_g_s, color=PALETTE['coral'], linewidth=2.1, linestyle='--',
            label='BFS — rede global (consultas uniformes)', zorder=3)
    ax.plot(N, pre_sf + N * euler_sf_s, color=PALETTE['cerulean'], linewidth=3.0, linestyle='-',
            label='Euler Tour — São Francisco (custo total)', zorder=5)
    ax.plot(N, N * bfs_sf_s, color=PALETTE['gold'], linewidth=2.4, linestyle='-',
            label='BFS — São Francisco (consultas uniformes)', zorder=4)

    ax.axvline(eq_g, ymin=0, ymax=1, color=PALETTE['navy'], linestyle=(0, (4, 3)), linewidth=1.1, alpha=0.55, zorder=1)
    ax.axvline(eq_sf, ymin=0, ymax=1, color=PALETTE['cerulean'], linestyle=(0, (4, 3)), linewidth=1.2, alpha=0.7, zorder=1)

    ax.scatter([eq_g], [t_eq_g], s=95, color=PALETTE['navy'], edgecolor='white', linewidth=1.7, zorder=8)
    ax.scatter([eq_sf], [t_eq_sf], s=105, color=PALETTE['cerulean'], edgecolor='white', linewidth=1.8, zorder=8)

    ax.annotate(
        f"Equilíbrio global (consultas uniformes)\n{fmt_int(eq_g)} consultas ({fmt_num(eq_g / 1e3, 1)} mil)\nTempo total: {fmt_num(t_eq_g, 2)} s",
        xy=(eq_g, t_eq_g), xycoords='data',
        xytext=(0.45, 0.80), textcoords='axes fraction',
        ha='left', va='top', fontsize=8.8, color=PALETTE['navy'],
        bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='#D8E1EA', lw=0.9),
        arrowprops=dict(arrowstyle='-', color=PALETTE['navy'], lw=1.2,
                        connectionstyle='angle3,angleA=0,angleB=90'),
        zorder=9
    )

    ax.annotate(
        f"Equilíbrio São Francisco (consultas uniformes)\n{fmt_int(eq_sf)} consultas\nTempo total: {fmt_num(t_eq_sf * 1e3, 2)} ms",
        xy=(eq_sf, t_eq_sf), xycoords='data',
        xytext=(0.035, 0.56), textcoords='axes fraction',
        ha='left', va='top', fontsize=8.8, fontweight='bold', color=PALETTE['cerulean'],
        bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='#D8E1EA', lw=0.9),
        arrowprops=dict(arrowstyle='-', color=PALETTE['cerulean'], lw=1.25,
                        connectionstyle='angle3,angleA=0,angleB=90'),
        zorder=9
    )

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(1, 2e6)
    ax.set_ylim(4e-6, 40.0)
    ax.set_yticks([1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1, 10])
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda y, _: f"{fmt_num(y * 1e6, 0)} µs" if y < 1e-3 else
        (f"{fmt_num(y * 1e3, 0)} ms" if y < 1.0 else f"{fmt_num(y, 0)} s")
    ))
    ax.xaxis.set_major_locator(ticker.LogLocator(base=10))
    ax.xaxis.set_major_formatter(ticker.LogFormatterMathtext(base=10))
    ax.grid(axis='y', which='major', color=PALETTE['grid'], linewidth=0.7)
    ax.grid(axis='x', which='major', color=PALETTE['grid'], linewidth=0.45, alpha=0.35)
    ax.set_axisbelow(True)

    ax.set_xlabel('Número acumulado de consultas (N)', fontsize=11, fontweight='bold', labelpad=9)
    ax.set_ylabel('Tempo acumulado', fontsize=11, fontweight='bold', labelpad=9)

    ax.legend(
        loc='lower right', frameon=False, fontsize=8.8,
        handlelength=2.8, labelspacing=0.55
    )

    adicionar_titulos(
        fig,
        titulo=f"Sob consultas uniformes nos trechos, Euler Tour compensa após {fmt_int(eq_sf)} consultas no São Francisco",
        subtitulo="Tempo acumulado = pré-processamento + N × tempo médio sob distribuição uniforme sobre os trechos da rede"
    )
    adicionar_rodape(
        fig,
        nota="Nota: A hipótese de consultas uniformes favorece a BFS e define um limite superior; consultas reais focadas em rios maiores atingem o equilíbrio antes.",
        fonte="Fonte: Elaborado pelos autores com base nos experimentos no conjunto HydroRIVERS + GloFAS 5.0 (cenário deficit_seca)."
    )

    fig.savefig(os.path.join(out_dir, 'fig7_comparacao_equilibrio_sf.png'))
    fig.savefig(os.path.join(out_dir, 'fig7_comparacao_equilibrio_sf.pdf'))
    plt.close(fig)
    print("  -> Figura 7 salva com sucesso.")


# ---------------------------------------------------------------------------
# FIGURA 8: Série Mensal do Déficit Agregado no São Francisco (2012–2017)
# ---------------------------------------------------------------------------

def gerar_figura8_serie_deficit_sf(arq_serie, out_dir):
    """Apresenta a série mensal do déficit agregado na bacia (jan/2012 a dez/2017)."""
    print("Gerando Figura 8: Série Mensal do Déficit Agregado (2012–2017)...")
    df = pd.read_csv(arq_serie)

    valores_mil = df['deficit_agregado'].to_numpy(dtype=float) / 1e3
    meses = df['ano_mes'].astype(str).tolist()
    x = np.arange(len(df))

    idx_pico = int(np.argmax(valores_mil))
    val_pico_bruto = float(df['deficit_agregado'].iloc[idx_pico])
    mes_pico = meses[idx_pico]
    media_bruta = float(np.nanmean(df['deficit_agregado'].to_numpy(dtype=float)))
    media_mil = media_bruta / 1e3

    fig, ax = plt.subplots(figsize=(10.0, 5.7))
    fig.subplots_adjust(top=0.80, bottom=0.20, left=0.10, right=0.97)
    formatar_eixos(ax)

    cores = [PALETTE['coral'] if i == idx_pico else PALETTE['sky'] for i in range(len(df))]
    ax.bar(x, valores_mil, width=0.76, color=cores, edgecolor='none', zorder=3)

    ax.axhline(media_mil, color=PALETTE['navy'], linestyle='--', linewidth=1.3, zorder=4)
    ax.text(
        0.6, media_mil + (valores_mil.max() * 0.025),
        f"Média 2012–2017: {fmt_int(media_bruta)} m³/s",
        fontsize=8.8, fontweight='bold', color=PALETTE['navy'], zorder=5
    )

    ax.annotate(
        f"Máximo do período: {mes_pico} ({fmt_int(val_pico_bruto)} m³/s)",
        xy=(idx_pico, valores_mil[idx_pico]), xycoords='data',
        xytext=(-14, 14), textcoords='offset points',
        ha='right', va='bottom', fontsize=9.0, fontweight='bold',
        color=PALETTE['dark_coral'],
        arrowprops=dict(arrowstyle='->', color=PALETTE['dark_coral'], lw=1.15),
        zorder=6
    )

    posicoes_ano = [i for i, m in enumerate(meses) if m.endswith('-01')]
    rotulos_ano = [meses[i][:4] for i in posicoes_ano]
    for pos in posicoes_ano[1:]:
        ax.axvline(pos - 0.5, color=PALETTE['grid'], linestyle=':', linewidth=0.9, zorder=1)

    ax.set_xticks([p + 5.5 for p in posicoes_ano])
    ax.set_xticklabels(rotulos_ano, fontsize=9.5, fontweight='bold')
    ax.set_xlim(-1, len(df))
    ax.set_ylim(0, valores_mil.max() * 1.18)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: fmt_int(v)))
    ax.grid(axis='y', which='major', color=PALETTE['grid'], linewidth=0.65)
    ax.grid(axis='x', visible=False)
    ax.set_axisbelow(True)

    ax.set_xlabel('Mês (jan/2012 a dez/2017)', fontsize=10.5, fontweight='bold', labelpad=8)
    ax.set_ylabel('Déficit de vazão agregado (× 10³ m³/s)', fontsize=10.5, fontweight='bold', labelpad=8)

    adicionar_titulos(
        fig,
        titulo="Maior déficit agregado do período 2012–2017 ocorreu em março de 2017",
        subtitulo="Déficit de vazão agregado mensal nas células GloFAS da bacia do Rio São Francisco (72 meses)"
    )
    adicionar_rodape(
        fig,
        nota="Nota: O mês 2017-03 registra o maior déficit absoluto entre todos os 252 meses da série na bacia e define o cenário deficit_mes.",
        fonte="Fonte: Elaborado pelos autores com base na reanálise GloFAS 5.0 (recorte da bacia do Rio São Francisco)."
    )

    fig.savefig(os.path.join(out_dir, 'fig8_serie_deficit_sao_francisco.png'))
    fig.savefig(os.path.join(out_dir, 'fig8_serie_deficit_sao_francisco.pdf'))
    plt.close(fig)
    print("  -> Figura 8 salva com sucesso.")


# ---------------------------------------------------------------------------
# TABELA 3: Comparativo de Escalabilidade (Rede Global vs. São Francisco)
# ---------------------------------------------------------------------------

def gerar_tabela3_comparacao_escala(df_geral_g, df_geral_sf, out_dir):
    """Gera tabela comparativa Global vs. São Francisco em CSV, MD, LaTeX, PNG e PDF."""
    print("Gerando Tabela 3: Comparativo Rede Global vs. Bacia do São Francisco...")

    def pegar(df, m):
        v = df[df['metrica'] == m]['valor']
        return float(v.iloc[0]) if len(v) > 0 else 0.0

    mib = 1024.0 * 1024.0

    n_g = pegar(df_geral_g, 'trechos')
    n_sf = pegar(df_geral_sf, 'trechos')

    mem_fl_g = pegar(df_geral_g, 'memoria_floresta_vetores') / mib
    mem_fl_sf = pegar(df_geral_sf, 'memoria_floresta_vetores') / mib

    mem_et_g = pegar(df_geral_g, 'memoria_euler_residente_estimada') / mib
    mem_et_sf = pegar(df_geral_sf, 'memoria_euler_residente_estimada') / mib

    pre_g = pegar(df_geral_g, 'preproc_euler_s_mediana') * 1e3
    pre_sf = pegar(df_geral_sf, 'preproc_euler_s_mediana') * 1e3

    bfs_g = pegar(df_geral_g, 'tempo_medio_bfs_misto_uniforme')
    bfs_sf = pegar(df_geral_sf, 'tempo_medio_bfs_misto_uniforme')

    et_g = pegar(df_geral_g, 'tempo_medio_euler_misto_uniforme')
    et_sf = pegar(df_geral_sf, 'tempo_medio_euler_misto_uniforme')

    eq_g = pegar(df_geral_g, 'consultas_equilibrio_misto_uniforme')
    eq_sf = pegar(df_geral_sf, 'consultas_equilibrio_misto_uniforme')

    kahn_g = df_geral_g[df_geral_g['metrica'] == 'tempo_todos_trechos_kahn']['valor'].mean() * 1e3
    kahn_sf = df_geral_sf[df_geral_sf['metrica'] == 'tempo_todos_trechos_kahn']['valor'].mean() * 1e3

    linhas = [
        {'Métrica Estrutural / Desempenho': 'Trechos hidrográficos (n)', 'Rede Global': fmt_int(n_g), 'Bacia São Francisco': fmt_int(n_sf), 'Relação (Global / SF)': f"{fmt_num(n_g / n_sf, 1)}×"},
        {'Métrica Estrutural / Desempenho': 'Memória base (floresta + CSR)', 'Rede Global': f"{fmt_num(mem_fl_g, 1)} MiB", 'Bacia São Francisco': f"{fmt_num(mem_fl_sf, 2)} MiB", 'Relação (Global / SF)': f"{fmt_num(mem_fl_g / mem_fl_sf, 1)}×"},
        {'Métrica Estrutural / Desempenho': 'Memória adicional Euler Tour', 'Rede Global': f"{fmt_num(mem_et_g, 1)} MiB", 'Bacia São Francisco': f"{fmt_num(mem_et_sf, 2)} MiB", 'Relação (Global / SF)': f"{fmt_num(mem_et_g / mem_et_sf, 1)}×"},
        {'Métrica Estrutural / Desempenho': 'Pré-processamento Euler (mediana)', 'Rede Global': f"{fmt_num(pre_g, 1)} ms", 'Bacia São Francisco': f"{fmt_num(pre_sf, 2)} ms", 'Relação (Global / SF)': f"{fmt_num(pre_g / pre_sf, 1)}×"},
        {'Métrica Estrutural / Desempenho': 'Latência média BFS (consultas uniformes)', 'Rede Global': f"{fmt_num(bfs_g, 1)} ns", 'Bacia São Francisco': f"{fmt_num(bfs_sf, 1)} ns", 'Relação (Global / SF)': f"{fmt_num(bfs_g / bfs_sf, 2)}×"},
        {'Métrica Estrutural / Desempenho': 'Latência média Euler Tour (uniforme)', 'Rede Global': f"{fmt_num(et_g, 1)} ns", 'Bacia São Francisco': f"{fmt_num(et_sf, 1)} ns", 'Relação (Global / SF)': f"{fmt_num(et_g / et_sf, 1)}×"},
        {'Métrica Estrutural / Desempenho': 'Ponto de equilíbrio (consultas uniformes)', 'Rede Global': fmt_int(eq_g), 'Bacia São Francisco': fmt_int(eq_sf), 'Relação (Global / SF)': f"{fmt_num(eq_g / eq_sf, 1)}×"},
        {'Métrica Estrutural / Desempenho': 'Varredura completa (Kahn)', 'Rede Global': f"{fmt_num(kahn_g, 1)} ms", 'Bacia São Francisco': f"{fmt_num(kahn_sf, 2)} ms", 'Relação (Global / SF)': f"{fmt_num(kahn_g / kahn_sf, 1)}×"},
    ]

    df_tab = pd.DataFrame(linhas)
    df_tab.to_csv(os.path.join(out_dir, 'tabela3_comparacao_global_sf.csv'), index=False)

    with open(os.path.join(out_dir, 'tabela3_comparacao_global_sf.md'), 'w', encoding='utf-8') as f:
        f.write(df_para_markdown(df_tab))

    with open(os.path.join(out_dir, 'tabela3_comparacao_global_sf.tex'), 'w', encoding='utf-8') as f:
        f.write(df_para_latex(
            df_tab,
            caption=r"Comparativo de Escalabilidade e Localidade Espacial: Rede Global vs. Bacia do Rio São Francisco (Cenário deficit\_seca)",
            label="tab:comparacao_global_sf"
        ))

    renderizar_tabela_png_pdf(
        df_tab=df_tab,
        col_widths=[0.44, 0.18, 0.20, 0.18],
        titulo="Tabela 3 — Comparativo de Desempenho: Rede Global vs. Bacia do Rio São Francisco",
        nota="Nota: O recorte regional cabe na cache L2/L3 (0,60 MiB), reduzindo a latência do Euler Tour em 8,0× e o equilíbrio uniforme para 126 consultas.",
        fonte="Fonte: Elaborado pelos autores com base nos benchmarks sobre HydroRIVERS + GloFAS 5.0 (cenário deficit_seca).",
        out_base=os.path.join(out_dir, 'tabela3_comparacao_global_sf')
    )
    print("  -> Tabela 3 salva com sucesso.")

# ---------------------------------------------------------------------------
# Execução Principal
# ---------------------------------------------------------------------------

def main():
    configurar_estilo_base()

    out_dir = os.path.join('results', 'graficos')
    os.makedirs(out_dir, exist_ok=True)
    print(f"Diretório de saída: {out_dir}")

    arq_faixas_g = 'results/benchmark_deficit_seca_resumo_faixas.csv'
    arq_geral_g = 'results/benchmark_deficit_seca_geral.csv'
    arq_faixas_sf = 'results/sao_francisco/benchmark_sf_deficit_seca_resumo_faixas.csv'
    arq_geral_sf = 'results/sao_francisco/benchmark_sf_deficit_seca_geral.csv'
    arq_serie_sf = 'results/deficit_mensal_sao_francisco_2012_2017.csv'

    for caminho in [arq_faixas_g, arq_geral_g, arq_faixas_sf, arq_geral_sf, arq_serie_sf]:
        if not os.path.exists(caminho):
            print(f"Erro: arquivo necessário não encontrado: {caminho}")
            sys.exit(1)

    df_faixas_g = pd.read_csv(arq_faixas_g)
    df_geral_g = pd.read_csv(arq_geral_g)
    df_faixas_sf = pd.read_csv(arq_faixas_sf)
    df_geral_sf = pd.read_csv(arq_geral_sf)

    gerar_figura6_latencia_escala(df_faixas_g, df_faixas_sf, df_geral_g, df_geral_sf, out_dir)
    gerar_figura7_equilibrio_escala(df_faixas_g, df_faixas_sf, out_dir)
    gerar_figura8_serie_deficit_sf(arq_serie_sf, out_dir)
    gerar_tabela3_comparacao_escala(df_geral_g, df_geral_sf, out_dir)

    print("\n=======================================================")
    print(f"FIGURAS 6–8 E TABELA 3 GERADA EM {out_dir}/")
    print("=======================================================\n")


if __name__ == '__main__':
    main()