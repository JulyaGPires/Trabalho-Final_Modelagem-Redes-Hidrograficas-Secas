# ==============================================================================
# Makefile - Modelagem de Redes Hidrográficas sob Cenários de Seca
# ==============================================================================
# Uso rápido:
#   make help          - Exibe este menu de ajuda interativo
#   make all           - Compila todos os programas principais (secas, benchmark, benchmark_sf)
#   make test          - Compila e executa todos os testes unitários
#   make run-sample    - Executa o programa interativo com dataset de exemplo (rápido)
#   make run           - Executa o programa interativo com dataset global
#   make benchmark     - Roda o benchmark global completo
#   make benchmark-sf  - Roda o benchmark da bacia do São Francisco
#   make graficos      - Gera todos os gráficos e tabelas do artigo
#   make gephi         - Gera os arquivos CSV para visualização no Gephi
# ==============================================================================

# Compilador e Flags C++
CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O3 -Wall -Wextra
CPPFLAGS ?= -Isrc/includes -MMD -MP

# Interpretador Python (prioriza o ambiente virtual local .venv se existir)
PYTHON   ?= $(shell if [ -f .venv/bin/python3 ]; then echo .venv/bin/python3; else echo python3; fi)

# Diretórios
BUILD_DIR := build
OBJ_DIR   := $(BUILD_DIR)/obj
INC_DIR   := src/includes
SRC_DIR   := src/code
TEST_DIR  := tests
DATA_DIR  := data/processed
SAMPLE_DIR:= data/sample
RES_DIR   := results
RES_SF_DIR:= results/sao_francisco
RES_GFX   := results/graficos

# Datasets padrão
DATASET_GLOBAL := $(DATA_DIR)/dataset_com_deficit.csv
DATASET_SF     := $(DATA_DIR)/dataset_deficit_sao_francisco.csv
DATASET_SAMPLE := $(SAMPLE_DIR)/exemplo.csv

# Parâmetros de Execução e Benchmarks (Customizáveis via linha de comando)
# Exemplo: make benchmark EXECUCOES=5 CENARIO=deficit_mes
EXECUCOES    ?= 10
SEMENTE      ?= 42
ESCALA       ?= 1.0
BFS_TODOS    ?= 3
BFS_TODOS_SF ?= 5
PASTA        ?= $(RES_DIR)
PASTA_SF     ?= $(RES_SF_DIR)
CENARIO      ?= deficit_seca
CENARIO_CLI  ?= seca
CENARIO_SF   ?= deficit_seca

# Executáveis Principais
BIN_SECAS        := $(BUILD_DIR)/secas
BIN_BENCHMARK    := $(BUILD_DIR)/benchmark
BIN_BENCHMARK_SF := $(BUILD_DIR)/benchmark_sf

# Executáveis de Teste
BIN_TEST_FLORESTA := $(BUILD_DIR)/test_floresta
BIN_TEST_BFS      := $(BUILD_DIR)/test_bfs
BIN_TEST_EULER    := $(BUILD_DIR)/test_euler
BIN_TEST_KDTREE   := $(BUILD_DIR)/test_kdtree

# Objetos Principais
OBJS_CORE := $(OBJ_DIR)/Floresta.o \
             $(OBJ_DIR)/Bfs.o \
             $(OBJ_DIR)/EulerTour.o \
             $(OBJ_DIR)/KdTree.o

OBJS_MAIN      := $(OBJ_DIR)/main.o
OBJS_BENCH     := $(OBJ_DIR)/Benchmark.o
OBJS_BENCH_SF  := $(OBJ_DIR)/BenchmarkSaoFrancisco.o

# Objetos de Teste
OBJ_T_FLORESTA := $(OBJ_DIR)/test_floresta.o
OBJ_T_BFS      := $(OBJ_DIR)/test_bfs.o
OBJ_T_EULER    := $(OBJ_DIR)/test_eulerTour.o
OBJ_T_KDTREE   := $(OBJ_DIR)/test_kdtree.o

# Cores para saída no terminal
BLUE   := \033[1;34m
GREEN  := \033[1;32m
YELLOW := \033[1;33m
CYAN   := \033[1;36m
BOLD   := \033[1m
RESET  := \033[0m

# ==============================================================================
# Alvos Principais
# ==============================================================================

.DEFAULT_GOAL := help

.PHONY: help all tests test clean clean-all check \
        run run-sf run-sample \
        benchmark benchmark-sf benchmark-all \
        graficos graficos-artigo graficos-sf \
        gephi sample dataset-sf prep-sf analise-sf deficit-trechos \
        test-floresta test-bfs test-euler test-kdtree

## help: Exibe este menu de ajuda intuitivo e detalhado
help:
	@echo ""
	@echo "$(BOLD)========================================================================$(RESET)"
	@echo "$(CYAN)$(BOLD)      MODELAGEM DE REDES HIDROGRÁFICAS SOB CENÁRIOS DE SECA$(RESET)"
	@echo "$(BOLD)========================================================================$(RESET)"
	@echo "Estrutura do projeto com Euler Tour + BFS + KD-Tree em redes HydroRIVERS/GloFAS."
	@echo ""
	@echo "$(YELLOW)$(BOLD)COMPILAÇÃO:$(RESET)"
	@echo "  $(GREEN)make all$(RESET)            Compila todos os binários principais (secas, benchmark, benchmark_sf)"
	@echo "  $(GREEN)make tests$(RESET)          Compila todos os 4 binários de testes unitários"
	@echo "  $(GREEN)make clean$(RESET)          Remove objetos (.o) e binários gerados na pasta build/"
	@echo "  $(GREEN)make clean-all$(RESET)      Limpa pasta build/ e caches Python (__pycache__)"
	@echo ""
	@echo "$(YELLOW)$(BOLD)EXECUÇÃO INTERATIVA (secas - CLI):$(RESET)"
	@echo "  $(GREEN)make run-sample$(RESET)     Roda interativamente no dataset de exemplo (rápido, ~4k trechos)"
	@echo "  $(GREEN)make run$(RESET)            Roda interativamente no dataset global (8M+ trechos)"
	@echo "                      Opções: $(CYAN)CENARIO_CLI=seca|total|mes|sintetico$(RESET) (padrão: seca)"
	@echo "  $(GREEN)make run-sf$(RESET)         Roda interativamente na bacia do São Francisco (~33k trechos)"
	@echo ""
	@echo "$(YELLOW)$(BOLD)TESTES UNITÁRIOS E VALIDAÇÃO:$(RESET)"
	@echo "  $(GREEN)make test$(RESET)           Compila e roda todos os testes unitários"
	@echo "  $(GREEN)make test-floresta$(RESET)  Testa construção de topologia e detecção de ciclos (Kahn)"
	@echo "  $(GREEN)make test-bfs$(RESET)       Testa integridade e cobertura da busca em largura"
	@echo "  $(GREEN)make test-euler$(RESET)     Valida prefix sums do Euler Tour vs BFS em cadeia de 1M nós"
	@echo "  $(GREEN)make test-kdtree$(RESET)    Valida busca 1-NN e k-NN da KD-Tree vs busca linear"
	@echo ""
	@echo "$(YELLOW)$(BOLD)BENCHMARKS:$(RESET)"
	@echo "  $(GREEN)make benchmark$(RESET)      Roda o benchmark global (Euler Tour vs BFS por faixa de bacia)"
	@echo "                      Opções: $(CYAN)CENARIO=deficit_seca|deficit_total|deficit_mes$(RESET)"
	@echo "                              $(CYAN)EXECUCOES=10 SEMENTE=42 ESCALA=1.0 BFS_TODOS=3$(RESET)"
	@echo "  $(GREEN)make benchmark-sf$(RESET)   Roda o benchmark focado na sub-rede do São Francisco"
	@echo "                      Opções: $(CYAN)CENARIO_SF=deficit_mes|deficit_seca|deficit_total$(RESET)"
	@echo "  $(GREEN)make benchmark-all$(RESET)  Executa a bateria completa de benchmarks para todos os cenários"
	@echo ""
	@echo "$(YELLOW)$(BOLD)GRÁFICOS E PUBLICAÇÃO:$(RESET)"
	@echo "  $(GREEN)make graficos$(RESET)       Gera todas as figuras (1 a 8) e tabelas (1 a 3) em results/graficos/"
	@echo "  $(GREEN)make graficos-artigo$(RESET)Gera figuras 1-5 e tabelas 1-2 (análise da rede global)"
	@echo "  $(GREEN)make graficos-sf$(RESET)    Gera figuras 6-8 e tabela 3 (comparativo São Francisco)"
	@echo ""
	@echo "$(YELLOW)$(BOLD)PROCESSAMENTO DE DADOS E SCRIPTS:$(RESET)"
	@echo "  $(GREEN)make gephi$(RESET)          Gera processed/gephi_bacia_minuscula_nodes.csv e processed/gephi_bacia_minuscula_edges.csv para importação no Gephi"
	@echo "  $(GREEN)make sample$(RESET)         Gera amostra representativa data/sample/exemplo.csv"
	@echo "  $(GREEN)make prep-sf$(RESET)        Prepara recortes de trechos e células do São Francisco"
	@echo "  $(GREEN)make analise-sf$(RESET)     Calcula série temporal histórica (2012-2017) do São Francisco"
	@echo "  $(GREEN)make dataset-sf$(RESET)     Filtra dataset do São Francisco a partir do global"
	@echo "  $(GREEN)make deficit-trechos$(RESET)Mapeia déficits do GloFAS nos trechos hidrográficos"
	@echo "$(BOLD)========================================================================$(RESET)"
	@echo ""

# Compilação dos binários principais
build: all

all: $(BIN_SECAS) $(BIN_BENCHMARK) $(BIN_BENCHMARK_SF)
	@echo "$(GREEN)$(BOLD)[OK] Todos os executáveis principais foram compilados com sucesso!$(RESET)"

tests: $(BIN_TEST_FLORESTA) $(BIN_TEST_BFS) $(BIN_TEST_EULER) $(BIN_TEST_KDTREE)
	@echo "$(GREEN)$(BOLD)[OK] Todos os testes unitários foram compilados com sucesso!$(RESET)"

# Diretório de objetos
$(OBJ_DIR):
	@mkdir -p $(OBJ_DIR)

# Regras de compilação de código-fonte
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp | $(OBJ_DIR)
	@echo "$(BLUE)Compilando $(notdir $<)...$(RESET)"
	@$(CXX) $(CXXFLAGS) $(CPPFLAGS) -c $< -o $@

$(OBJ_DIR)/main.o: src/main.cpp | $(OBJ_DIR)
	@echo "$(BLUE)Compilando $(notdir $<)...$(RESET)"
	@$(CXX) $(CXXFLAGS) $(CPPFLAGS) -c $< -o $@

$(OBJ_DIR)/%.o: $(TEST_DIR)/%.cpp | $(OBJ_DIR)
	@echo "$(BLUE)Compilando teste $(notdir $<)...$(RESET)"
	@$(CXX) $(CXXFLAGS) $(CPPFLAGS) -c $< -o $@

# Ligação dos binários principais
$(BIN_SECAS): $(OBJS_MAIN) $(OBJS_CORE)
	@mkdir -p $(BUILD_DIR)
	@echo "$(GREEN)Ligando $@...$(RESET)"
	@$(CXX) $(CXXFLAGS) $^ -o $@

$(BIN_BENCHMARK): $(OBJS_BENCH) $(OBJ_DIR)/Floresta.o $(OBJ_DIR)/Bfs.o $(OBJ_DIR)/EulerTour.o
	@mkdir -p $(BUILD_DIR)
	@echo "$(GREEN)Ligando $@...$(RESET)"
	@$(CXX) $(CXXFLAGS) $^ -o $@

$(BIN_BENCHMARK_SF): $(OBJS_BENCH_SF) $(OBJ_DIR)/Floresta.o $(OBJ_DIR)/Bfs.o $(OBJ_DIR)/EulerTour.o
	@mkdir -p $(BUILD_DIR)
	@echo "$(GREEN)Ligando $@...$(RESET)"
	@$(CXX) $(CXXFLAGS) $^ -o $@

# Ligação dos testes unitários
$(BIN_TEST_FLORESTA): $(OBJ_T_FLORESTA) $(OBJ_DIR)/Floresta.o
	@mkdir -p $(BUILD_DIR)
	@$(CXX) $(CXXFLAGS) $^ -o $@

$(BIN_TEST_BFS): $(OBJ_T_BFS) $(OBJ_DIR)/Bfs.o $(OBJ_DIR)/Floresta.o
	@mkdir -p $(BUILD_DIR)
	@$(CXX) $(CXXFLAGS) $^ -o $@

$(BIN_TEST_EULER): $(OBJ_T_EULER) $(OBJ_DIR)/EulerTour.o $(OBJ_DIR)/Bfs.o $(OBJ_DIR)/Floresta.o
	@mkdir -p $(BUILD_DIR)
	@$(CXX) $(CXXFLAGS) $^ -o $@

$(BIN_TEST_KDTREE): $(OBJ_T_KDTREE) $(OBJ_DIR)/KdTree.o
	@mkdir -p $(BUILD_DIR)
	@$(CXX) $(CXXFLAGS) $^ -o $@

# ==============================================================================
# Execução de Testes
# ==============================================================================

test: tests
	@echo ""
	@echo "$(CYAN)$(BOLD)>>> Executando bateria de testes unitários...$(RESET)"
	@echo "$(YELLOW)[1/4] Testando Floresta Hidrográfica...$(RESET)"
	@$(BIN_TEST_FLORESTA)
	@echo "$(YELLOW)[2/4] Testando BFS...$(RESET)"
	@$(BIN_TEST_BFS)
	@echo "$(YELLOW)[3/4] Testando Euler Tour (Prefix Sums)...$(RESET)"
	@$(BIN_TEST_EULER)
	@echo "$(YELLOW)[4/4] Testando KD-Tree Espacial...$(RESET)"
	@$(BIN_TEST_KDTREE)
	@echo "$(GREEN)$(BOLD)>>> TODOS OS TESTES PASSARAM COM SUCESSO!$(RESET)"
	@echo ""

test-floresta: $(BIN_TEST_FLORESTA)
	@$(BIN_TEST_FLORESTA)

test-bfs: $(BIN_TEST_BFS)
	@$(BIN_TEST_BFS)

test-euler: $(BIN_TEST_EULER)
	@$(BIN_TEST_EULER)

test-kdtree: $(BIN_TEST_KDTREE)
	@$(BIN_TEST_KDTREE)

# Smoke check rápido
check: test run-sample-smoke
	@echo "$(GREEN)$(BOLD)[OK] Smoke test e validação concluídos!$(RESET)"

run-sample-smoke: $(BIN_SECAS)
	@echo "sair" | $(BIN_SECAS) $(DATASET_SAMPLE) --cenario $(CENARIO_CLI) > /dev/null
	@echo "$(GREEN)[OK] Executável interativo testado no sample com sucesso.$(RESET)"

# ==============================================================================
# Execução Interativa (secas)
# ==============================================================================

run-sample: $(BIN_SECAS)
		@echo "$(CYAN)Executando no dataset de amostra (exemplo.csv), cenário $(CENARIO_CLI)...$(RESET)"
		@$(BIN_SECAS) $(DATASET_SAMPLE) --cenario $(CENARIO_CLI)

run: $(BIN_SECAS)
	@if [ ! -f $(DATASET_GLOBAL) ]; then \
		echo "$(YELLOW)Aviso: $(DATASET_GLOBAL) não encontrado. Roda com 'make run-sample' ou gere o dataset.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(CYAN)Executando no dataset global ($(DATASET_GLOBAL)) com cenário $(CENARIO_CLI)...$(RESET)"
	@$(BIN_SECAS) $(DATASET_GLOBAL) --cenario $(CENARIO_CLI)

run-sf: $(BIN_SECAS)
	@if [ ! -f $(DATASET_SF) ]; then \
		echo "$(YELLOW)Aviso: $(DATASET_SF) não encontrado. Gerando via 'make dataset-sf'...$(RESET)"; \
		$(MAKE) dataset-sf; \
	fi
	@echo "$(CYAN)Executando no dataset São Francisco ($(DATASET_SF)) com cenário $(CENARIO_CLI)...$(RESET)"
	@$(BIN_SECAS) $(DATASET_SF) --cenario $(CENARIO_CLI)

# ==============================================================================
# Benchmarks
# ==============================================================================

benchmark: $(BIN_BENCHMARK)
	@mkdir -p $(PASTA)
	@if [ ! -f $(DATASET_GLOBAL) ]; then \
		echo "$(YELLOW)Erro: Dataset global $(DATASET_GLOBAL) não encontrado.$(RESET)"; \
		exit 1; \
	fi
	@echo "$(CYAN)Iniciando Benchmark Global [Cenário: $(CENARIO)]...$(RESET)"
	@$(BIN_BENCHMARK) $(DATASET_GLOBAL) $(CENARIO) \
		--execucoes $(EXECUCOES) \
		--semente $(SEMENTE) \
		--escala $(ESCALA) \
		--bfs-todos $(BFS_TODOS) \
		--pasta $(PASTA)

benchmark-sf: $(BIN_BENCHMARK_SF)
	@mkdir -p $(PASTA_SF)
	@if [ ! -f $(DATASET_SF) ]; then \
		echo "$(YELLOW)Dataset $(DATASET_SF) não encontrado. Gerando...$(RESET)"; \
		$(MAKE) dataset-sf; \
	fi
	@echo "$(CYAN)Iniciando Benchmark São Francisco [Cenário: $(CENARIO_SF)]...$(RESET)"
	@$(BIN_BENCHMARK_SF) $(DATASET_SF) $(CENARIO_SF) \
		--execucoes $(EXECUCOES) \
		--semente $(SEMENTE) \
		--escala $(ESCALA) \
		--bfs-todos $(BFS_TODOS_SF) \
		--pasta $(PASTA_SF)

benchmark-all: $(BIN_BENCHMARK) $(BIN_BENCHMARK_SF)
	@echo "$(CYAN)$(BOLD)>>> Executando todos os cenários de benchmark (Global e São Francisco)...$(RESET)"
	@$(MAKE) benchmark CENARIO=deficit_seca
	@$(MAKE) benchmark CENARIO=deficit_total
	@$(MAKE) benchmark CENARIO=deficit_mes
	@$(MAKE) benchmark-sf CENARIO_SF=deficit_seca
	@$(MAKE) benchmark-sf CENARIO_SF=deficit_total
	@$(MAKE) benchmark-sf CENARIO_SF=deficit_mes
	@echo "$(GREEN)$(BOLD)>>> Todos os benchmarks foram concluídos!$(RESET)"

# ==============================================================================
# Gráficos e Publicação (Python)
# ==============================================================================

graficos: graficos-artigo graficos-sf
	@echo "$(GREEN)$(BOLD)[OK] Todas as figuras e tabelas foram geradas em $(RES_GFX)/$(RESET)"

graficos-artigo:
	@mkdir -p $(RES_GFX)
	@echo "$(CYAN)Gerando figuras 1 a 5 e tabelas 1 e 2 do artigo...$(RESET)"
	@$(PYTHON) scripts/11_gerar_graficos_artigo.py

graficos-sf:
	@mkdir -p $(RES_GFX)
	@echo "$(CYAN)Gerando figuras 6 a 8 e tabela 3 do artigo (São Francisco)...$(RESET)"
	@$(PYTHON) scripts/13_gerar_graficos_sao_francisco.py

# ==============================================================================
# Processamento de Dados e Visualização
# ==============================================================================

gephi:
	@echo "$(CYAN)Gerando gephi_bacia_minuscula_nodes.csv e gephi_bacia_minuscula_edges.csv para o Gephi...$(RESET)"
	@$(PYTHON) scripts/14_gerar_gephi_bacia.py

sample:
	@echo "$(CYAN)Gerando dataset de amostra (data/sample/exemplo.csv)...$(RESET)"
	@mkdir -p $(SAMPLE_DIR)
	@$(PYTHON) scripts/10_gerar_sample.py $(DATASET_GLOBAL) $(DATASET_SAMPLE)

prep-sf:
	@echo "$(CYAN)Preparando dados do São Francisco (script 07)...$(RESET)"
	@$(PYTHON) scripts/07_preparar_sao_francisco.py

analise-sf:
	@echo "$(CYAN)Analisando série temporal do São Francisco (script 08)...$(RESET)"
	@$(PYTHON) scripts/08_analisar_deficit_sao_francisco.py

dataset-sf:
	@echo "$(CYAN)Gerando dataset de déficit do São Francisco (script 12)...$(RESET)"
	@$(PYTHON) scripts/12_gerar_dataset_sao_francisco.py

deficit-trechos:
	@echo "$(CYAN)Distribuindo déficit do GloFAS nos trechos, gerando dataset_com_deficit (script 09)...$(RESET)"
	@$(PYTHON) scripts/09_gerar_deficit_trechos.py

# ==============================================================================
# Limpeza
# ==============================================================================

clean:
	@echo "$(YELLOW)Limpando objetos e binários compilados...$(RESET)"
	@rm -rf $(OBJ_DIR)
	@rm -f $(BIN_SECAS) $(BIN_BENCHMARK) $(BIN_BENCHMARK_SF) \
	       $(BIN_TEST_FLORESTA) $(BIN_TEST_BFS) $(BIN_TEST_EULER) $(BIN_TEST_KDTREE)
	@echo "$(GREEN)[OK] Pasta build limpa.$(RESET)"

clean-all: clean
	@echo "$(YELLOW)Limpando caches do Python...$(RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)[OK] Limpeza completa realizada.$(RESET)"

-include $(wildcard $(OBJ_DIR)/*.d)
