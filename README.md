# Modelagem de Redes Hidrográficas sob Cenários de Seca

Sistema computacional desenvolvido em **C++17 e Python** para modelagem, processamento e análise de redes hidrográficas globais e regionais, integrando dados do **HydroRIVERS** e da reanálise hidrológica **GloFAS 5.0**.

O projeto implementa estruturas de dados e algoritmos para consultas eficientes de déficit hídrico acumulado a montante, além de ferramentas para processamento de dados, experimentação, geração de gráficos científicos e visualização de redes no Gephi.

As principais estruturas e técnicas implementadas são:

- **Floresta Direcionada em CSR (Compressed Sparse Row):** representação compacta da rede hidrográfica, na qual cada vértice representa um trecho de rio e as conexões seguem a direção do escoamento.
- **Ordenação Topológica de Kahn:** validação da estrutura direcionada e identificação de ciclos.
- **Euler Tour + Somas de Prefixo:** linearização das árvores para responder consultas de déficit acumulado a montante.
- **Busca em Largura (BFS):** implementação de referência para comparação de desempenho.
- **KD-Tree tridimensional:** indexação espacial e consultas por proximidade.
- **Benchmarks:** avaliação de tempo de execução, latência, consumo de memória e comparação entre algoritmos.

O estudo contempla tanto a rede hidrográfica global quanto um recorte regional da **Bacia do Rio São Francisco**.

---

## 1. Organização do repositório

```text
Trabalho-Final_Modelagem-Redes-Hidrograficas-Secas/
├── Makefile
├── README.md
├── requirements.txt
├── .gitignore
│
├── src/
│   ├── main.cpp
│   ├── code/
│   │   ├── Benchmark.cpp
│   │   ├── BenchmarkSaoFrancisco.cpp
│   │   ├── Bfs.cpp
│   │   ├── EulerTour.cpp
│   │   ├── Floresta.cpp
│   │   └── KdTree.cpp
│   └── includes/
│       ├── Bfs.hpp
│       ├── EulerTour.hpp
│       ├── Floresta.hpp
│       └── KdTree.hpp
│
├── tests/
│   ├── test_bfs.cpp
│   ├── test_eulerTour.cpp
│   ├── test_floresta.cpp
│   └── test_kdtree.cpp
│
├── scripts/
│   ├── 01_processar_hydrorivers.py
│   ├── 02_validar_hydrorivers.py
│   ├── 03_verificar_conectividade.py
│   ├── 04_extrair_glofas.py
│   ├── 05_mapear_hydrorivers_glofas.py
│   ├── 06_calcular_deficit_glofas.py
│   ├── 07_preparar_sao_francisco.py
│   ├── 08_analisar_deficit_sao_francisco.py
│   ├── 09_gerar_deficit_trechos.py
│   ├── 10_gerar_sample.py
│   ├── 11_gerar_graficos_artigo.py
│   ├── 12_gerar_dataset_sao_francisco.py
│   ├── 13_gerar_graficos_sao_francisco.py
│   ├── 14_gerar_gephi_bacia.py
│   └── piloto/
│
├── data/
│   ├── input/
│   ├── processed/
│   └── sample/
│       └── exemplo.csv
│
├── results/
│   ├── graficos/
│   ├── grafos/
│   ├── sao_francisco/
│   ├── validation/
│   └── arquivos de resultados experimentais
│
└── build/
    └── arquivos gerados pela compilação
```

Os diretórios `data/input/` e `data/processed/` são utilizados para armazenar os dados necessários ao processamento e à execução. Os datasets de grande porte não são versionados no GitHub.

O diretório `build/` é gerado durante a compilação.

---

## 2. Tecnologias e dependências

### Linguagens

- C++17
- Python 3

### Ferramentas

- GCC/G++ com suporte a C++17
- GNU Make
- Python e `pip`
- Git

### Bibliotecas Python

As dependências Python estão declaradas em `requirements.txt`, incluindo:

- NumPy
- Pandas
- GeoPandas
- Shapely
- PyProj
- PyOgrio
- Matplotlib
- Xarray
- netCDF4

As versões específicas devem ser instaladas diretamente pelo arquivo de dependências.

### Sistemas operacionais

O projeto foi desenvolvido em ambiente Linux/WSL2. Recomenda-se Ubuntu ou outra distribuição Linux com ferramentas equivalentes.

No Windows, é recomendado utilizar o **WSL2 com Ubuntu**, pois os comandos do Makefile foram preparados para um ambiente compatível com Linux.

---

## 3. Instalação do ambiente

As instruções a seguir consideram uma instalação Ubuntu ou WSL2 sem as ferramentas de desenvolvimento previamente configuradas.

### 3.1. Instalar as ferramentas necessárias

Atualize a lista de pacotes:

```bash
sudo apt update
```

Instale Git, compilador C++, Make e ferramentas Python:

```bash
sudo apt install -y git build-essential make python3 python3-pip python3-venv unzip
```

Verifique as instalações:

```bash
git --version
g++ --version
make --version
python3 --version
```

O compilador precisa oferecer suporte ao padrão C++17.

### 3.2. Clonar o repositório

```bash
git clone https://github.com/JulyaGPires/Trabalho-Final_Modelagem-Redes-Hidrograficas-Secas.git
```

Entre no diretório:

```bash
cd Trabalho-Final_Modelagem-Redes-Hidrograficas-Secas
```

### 3.3. Criar o ambiente virtual Python

```bash
python3 -m venv .venv
```

Ative o ambiente:

```bash
source .venv/bin/activate
```

### 3.4. Instalar as bibliotecas Python

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

A instalação deve ser executada com o ambiente virtual ativado.

---

## 4. Obtenção dos datasets

Os dados processados necessários à execução do sistema são disponibilizados separadamente no **Zenodo**, devido ao tamanho dos arquivos.

**Repositório de dados:** https://doi.org/10.5281/zenodo.24429365

A distribuição é organizada em dois conjuntos:

1. **Datasets finais:** arquivos CSV prontos para utilização pelo programa em C++.
2. **Arquivos intermediários:** dados necessários para reproduzir a geração dos datasets finais, sem repetir o processamento completo dos arquivos brutos originais.

### 4.1. Datasets finais

| Arquivo | Descrição |
|---|---|
| `dataset_com_deficit.csv` | Rede hidrográfica global com atributos de déficit hídrico |
| `dataset_deficit_sao_francisco.csv` | Recorte regional da Bacia do São Francisco, preparado para execução |

Após obter autorização e baixar os dois arquivos, coloque-os em:

```text
data/
└── processed/
    ├── dataset_com_deficit.csv
    └── dataset_deficit_sao_francisco.csv
```

**Esses dois arquivos são suficientes para executar os programas principais e os benchmarks**, desde que o ambiente C++ esteja instalado e os executáveis tenham sido compilados.

Não é necessário baixar os arquivos intermediários para utilizar os datasets finais.

### 4.2. Arquivos intermediários

Para reproduzir o processamento dos datasets finais, o depósito também disponibiliza, mediante acesso autorizado:

```text
intermediarios.zip
```

O arquivo compactado contém:

```text
data/
└── processed/
    ├── dataset_hidrologico_global.csv
    ├── hydrorivers_sao_francisco.csv
    └── glofas/
        ├── deficits_mensais_por_celula_float32.dat
        ├── mapeamento_hydrorivers_indices.csv
        ├── indice_meses_glofas.csv
        └── celulas_sao_francisco_unicas.csv
```

Extraia o ZIP **na raiz do repositório**, preservando a estrutura de diretórios.

Exemplo:

```bash
unzip intermediarios.zip
```

O comando pressupõe que o arquivo ZIP esteja na raiz do projeto e que o utilitário `unzip` esteja instalado.

Caso necessário:

```bash
sudo apt install -y unzip
```

Os arquivos intermediários permitem reproduzir as etapas finais de atribuição dos déficits aos trechos hidrográficos e de construção do dataset regional.

Eles não substituem os arquivos brutos completos do HydroRIVERS e do GloFAS necessários para reproduzir todo o pré-processamento desde a origem.

---

## 5. Estrutura dos datasets finais

Os datasets finais possuem as seguintes colunas:

| Coluna | Descrição |
|---|---|
| `hyriv_id` | Identificador do trecho hidrográfico no HydroRIVERS |
| `next_down` | Identificador do trecho imediatamente a jusante; valor `0` indica ausência de conexão dentro da rede representada |
| `lat` | Latitude associada ao trecho |
| `lon` | Longitude associada ao trecho |
| `deficit_seca` | Indicador de déficit acumulado no período de seca analisado |
| `deficit_total` | Indicador de déficit acumulado ao longo da série temporal disponível |
| `deficit_mes` | Indicador de déficit referente ao mês crítico selecionado |

### Cenários hidrológicos

O projeto utiliza três cenários:

**Déficit de seca (`deficit_seca`)**

Soma dos déficits mensais entre janeiro de 2012 e dezembro de 2017, totalizando 72 meses.

**Déficit total (`deficit_total`)**

Soma dos déficits mensais de toda a série temporal processada, composta por 252 meses.

**Déficit mensal (`deficit_mes`)**

Déficit correspondente ao mês selecionado a partir do maior déficit agregado nas células GloFAS associadas à Bacia do São Francisco, dentro do período de janeiro de 2012 a dezembro de 2017.

Os déficits são tratados como **indicadores agregados de vazão**, expressos conforme a unidade adotada no processamento, em m³/s. As somas temporais não devem ser interpretadas diretamente como volumes físicos de água em m³.

### Distribuição dos déficits aos trechos

No processamento final, os valores associados às células GloFAS são distribuídos entre os trechos HydroRIVERS correspondentes.

O procedimento utiliza, por padrão, uma distribuição proporcional ao comprimento dos trechos dentro de cada célula, evitando atribuir integralmente o mesmo déficit a múltiplos segmentos.

---

## 6. Compilação do projeto

> [!NOTE]
> Para consultar todos os demais comandos e opções disponíveis no `Makefile`, execute `make help` na raiz do repositório.

Na raiz do repositório, execute:

```bash
make all
```

Esse comando compila os executáveis principais:

```text
build/secas
build/benchmark
build/benchmark_sf
```

Também é possível consultar os comandos disponíveis:

```bash
make help
```

A compilação não exige que os datasets já estejam baixados. Os arquivos de dados são necessários nas etapas de execução.

---

## 7. Execução dos testes

O projeto contém testes unitários para as estruturas de dados e os algoritmos implementados.

Para compilar os testes:

```bash
make tests
```

Para compilar e executar os testes:

```bash
make test
```

As estruturas testadas incluem:

- Floresta direcionada;
- Euler Tour;
- BFS;
- KD-Tree.

### Verificação com dataset de exemplo

O repositório inclui um pequeno dataset em:

```text
data/sample/exemplo.csv
```

Esse arquivo permite realizar uma verificação inicial sem baixar os datasets completos.

Execute:

```bash
make check
```

O comando executa os testes unitários e uma verificação de funcionamento com o dataset de exemplo.

Para executar somente o exemplo:

```bash
make run-sample
```

**Exemplo — Rede regional (`make run-sample`):**

```text
> id 61500238
> coord -34 -62
> sair
```

**Recomendação:** após instalar o ambiente, utilize `make check` para validar a compilação e o funcionamento básico antes de executar os experimentos completos.

---

## 8. Execução com os datasets finais

Antes de executar esta seção, baixe os datasets finais do Zenodo e coloque-os em `data/processed/`, conforme a Seção 4.

### Comandos interativos
Após executar `make run` ou `make run-sf`, o programa permite realizar consultas pelos seguintes comandos:

- `id <hyriv_id>` — consulta um trecho pelo identificador HydroRIVERS.
- `coord <lat> <lon>` — consulta por coordenadas geográficas.
- `sair` — encerra o programa.

### 8.1. Rede hidrográfica global

```bash
make run
```

**Exemplo — Rede global (`make run`):**

```text
> id 61500238
> coord -34 -78
> sair
```

O programa utiliza:

```text
data/processed/dataset_com_deficit.csv
```

### 8.2. Bacia do Rio São Francisco

```bash
make run-sf
```

**Exemplo — Rede regional (`make run-sf`):**

```text
> id 61017073
> coord -34 -78
> sair
```

O programa utiliza:

```text
data/processed/dataset_deficit_sao_francisco.csv
```

Caso o dataset regional não esteja presente, o Makefile poderá tentar gerá-lo a partir do dataset global e dos arquivos intermediários necessários.

Por isso, para a execução direta, recomenda-se baixar previamente os dois datasets finais.

---

## 9. Reprodução dos datasets processados

Esta seção é opcional e destina-se a usuários que desejam reproduzir as etapas finais de processamento dos dados.

É necessário baixar e extrair `intermediarios.zip`, conforme a Seção 4.2.

### 9.1. Analisar o déficit da Bacia do São Francisco

```bash
make analise-sf
```

Executa a análise regional dos dados hidrológicos utilizados nos cenários de déficit.

### 9.2. Gerar o dataset global com déficit

```bash
make deficit-trechos
```

Executa:

```text
scripts/09_gerar_deficit_trechos.py
```

A etapa utiliza os arquivos intermediários HydroRIVERS/GloFAS e produz:

```text
data/processed/dataset_com_deficit.csv
```

### 9.3. Gerar o dataset regional

```bash
make dataset-sf
```

Executa:

```text
scripts/12_gerar_dataset_sao_francisco.py
```

Essa etapa utiliza:

```text
data/processed/dataset_com_deficit.csv
data/processed/hydrorivers_sao_francisco.csv
```

E produz:

```text
data/processed/dataset_deficit_sao_francisco.csv
```

O processamento regional seleciona os trechos pertencentes ao recorte do São Francisco e ajusta conexões a jusante que ultrapassam os limites da rede regional.

### Ordem recomendada

Para reconstruir os datasets finais a partir dos intermediários:

```bash
make deficit-trechos
make dataset-sf
```

A análise regional pode ser executada separadamente:

```bash
make analise-sf
```

**Atenção:** essas operações podem sobrescrever os datasets finais existentes. Recomenda-se preservar uma cópia dos arquivos originais disponibilizados no Zenodo para comparação.

---

## 10. Benchmarks de desempenho

O projeto implementa experimentos para comparar o desempenho das estruturas e algoritmos utilizados nas consultas hidrográficas.

As avaliações contemplam:

- Tempo de pré-processamento;
- Latência das consultas;
- Comparação entre Euler Tour e BFS;
- Comportamento em diferentes tamanhos de consulta;
- Consumo de memória;
- Análises globais e regionais;
- Comparação entre cenários de déficit.

### 10.1. Benchmark global

```bash
make benchmark
```

Utiliza o dataset global.

### 10.2. Benchmark regional

```bash
make benchmark-sf
```

Utiliza o dataset da Bacia do São Francisco.

### 10.3. Executar todos os cenários

```bash
make benchmark-all
```

Executa os experimentos para os três cenários de déficit, tanto na rede global quanto na regional.

Os resultados são registrados em arquivos CSV e TXT dentro de `results/`, incluindo o subdiretório:

```text
results/sao_francisco/
```

**Importante:** os resultados já disponibilizados no GitHub correspondem aos experimentos registrados no repositório. A execução de novos benchmarks poderá sobrescrever arquivos locais e produzir resultados diferentes conforme o hardware, o sistema operacional e as condições de execução.

---

## 11. Gráficos e tabelas científicos

Os scripts Python permitem gerar visualizações e tabelas a partir dos resultados experimentais.

Para executar a geração de gráficos:

```bash
make graficos
```

Os arquivos são armazenados principalmente em:

```text
results/graficos/
```

Entre as análises disponíveis estão:

- Distribuição das bacias hidrográficas;
- Tempo de execução em função do tamanho da rede;
- Ponto de equilíbrio entre algoritmos;
- Comparação de desempenho na rede completa;
- Consumo de memória RAM;
- Comparação de latência na Bacia do São Francisco;
- Análise do ponto de equilíbrio regional;
- Série temporal de déficit hídrico na Bacia do São Francisco.

As figuras são disponibilizadas em formatos adequados à visualização e à utilização em documentos científicos, incluindo PNG e PDF.

As tabelas também podem ser geradas em formatos como CSV, Markdown, LaTeX, PNG e PDF.

**Observação:** a geração dos gráficos utiliza os resultados experimentais existentes. Para produzir figuras a partir de novos experimentos, execute primeiro os benchmarks correspondentes.

---

## 12. Visualização da rede no Gephi

O projeto possui um script para gerar arquivos de nós e arestas destinados à visualização no Gephi.

Execute:

```bash
make gephi
```

O comando utiliza:

```text
scripts/14_gerar_gephi_bacia.py
```

Os arquivos gerados são:

```text
data/processed/gephi_bacia_minuscula_nodes.csv
data/processed/gephi_bacia_minuscula_edges.csv
```

Essa exportação corresponde a uma **sub-rede reduzida**, preparada para visualização e inspeção estrutural no Gephi, e não à exportação integral da rede hidrográfica global.

As visualizações e figuras já produzidas para o estudo estão disponíveis em:

```text
results/grafos/
```

---

## 13. Limpeza dos arquivos de compilação

Para remover os executáveis e objetos compilados:

```bash
make clean
```

Para realizar uma limpeza adicional, incluindo arquivos temporários de Python:

```bash
make clean-all
```

Esses comandos não são destinados à exclusão dos datasets processados ou dos resultados científicos armazenados em `data/` e `results/`.

---

## 14. Fluxos de utilização recomendados

### Fluxo A — Testar o projeto sem baixar os datasets

Após clonar o repositório e instalar as dependências:

```bash
make check
```

Esse fluxo utiliza os testes unitários e o dataset de exemplo incluído no GitHub.

### Fluxo B — Executar o sistema com os datasets prontos

1. Baixe os dois datasets finais no Zenodo.
2. Coloque-os em `data/processed/`.
3. Execute:

```bash
make all
make run
make run-sf
```

### Fluxo C — Reproduzir os datasets finais

1. Após obter acesso ao depósito Zenodo, baixe `intermediarios.zip`.
2. Extraia o arquivo na raiz do repositório.
3. Ative o ambiente virtual Python e instale as dependências.
4. Execute:

```bash
make deficit-trechos
make dataset-sf
```

### Fluxo D — Reproduzir os experimentos e gráficos

Com os datasets finais disponíveis:

```bash
make all
make benchmark-all
make graficos
```

A execução dos experimentos completos pode exigir tempo considerável e recursos computacionais proporcionais ao tamanho da rede hidrográfica global.

---

## 15. Disponibilidade e reprodutibilidade

O projeto disponibiliza os seguintes materiais:

| Material | Local |
|---|---|
| Código-fonte C++ e Python | GitHub |
| Makefile e testes unitários | GitHub |
| Dataset de exemplo | GitHub |
| Resultados experimentais registrados | GitHub |
| Gráficos e tabelas científicos | GitHub |
| Dataset global processado | Zenodo — acesso restrito |
| Dataset regional processado | Zenodo — acesso restrito |
| Arquivos intermediários de processamento | Zenodo — acesso restrito |

### Código-fonte

[GitHub — Modelagem de Redes Hidrográficas sob Cenários de Seca](https://github.com/JulyaGPires/Trabalho-Final_Modelagem-Redes-Hidrograficas-Secas)

### Dados processados

**Zenodo:** [Datasets - dados para executar o programa](https://doi.org/10.5281/zenodo.24429365)

A separação entre código-fonte e dados processados facilita a organização e a reprodução autorizada dos resultados, evitando o armazenamento de arquivos de grande porte no histórico do Git. **O DOI identifica o registro público; os arquivos permanecem restritos e exigem autorização para download.**

Os arquivos intermediários permitem reproduzir a geração dos datasets finais a partir dos produtos previamente processados, enquanto os datasets finais possibilitam executar diretamente as consultas e os benchmarks.

---

## 16. Referências dos dados

**HydroRIVERS**

Base de dados hidrográfica utilizada para representar os trechos de rios, suas coordenadas e conexões a jusante.

Fonte: [HydroRIVERS — HydroSHEDS](https://www.hydrosheds.org/products/hydrorivers)

**GloFAS 5.0**

Dados hidrológicos utilizados para construir os indicadores de déficit associados aos trechos da rede.

Fonte: [Global Flood Awareness System — Copernicus](https://global-flood.emergency.copernicus.eu/)

O uso e a redistribuição dos dados devem observar as condições de licença e atribuição das respectivas fontes.

---

## 17. Disponibilidade dos dados e condições de acesso

Os datasets processados deste projeto encontram-se depositados no **Zenodo**, com identificador DOI e metadados publicamente acessíveis. Entretanto, os arquivos foram disponibilizados sob **acesso restrito**, em razão das condições de licenciamento das bases utilizadas em sua construção.

O projeto integra informações hidrológicas do **GloFAS 5.0**, disponibilizadas pelo Copernicus Emergency Management Service, e dados de estrutura e conectividade hidrográfica do **HydroRIVERS**, produto do HydroSHEDS.

Embora os datasets finais sejam resultados de processamento computacional desenvolvido pelas autoras, eles preservam informações derivadas da topologia hidrográfica original. A licença do HydroRIVERS estabelece condições específicas para a redistribuição de seus dados e produtos derivados, e não foi possível confirmar integralmente o enquadramento dos arquivos produzidos nessas condições.

Diante dessa incerteza, optou-se por restringir o acesso aos arquivos, preservando a rastreabilidade científica, a identificação das fontes e a possibilidade de reprodução dos experimentos mediante acesso autorizado.

**O código-fonte, a documentação e os procedimentos de execução permanecem disponíveis publicamente neste repositório.** Os datasets necessários aos experimentos podem ser solicitados às responsáveis pelo depósito, observadas as condições de uso das fontes originais. Um link de acesso privado, quando concedido, não deve ser divulgado publicamente.

Essa medida busca conciliar a reprodutibilidade científica com o respeito às condições de licenciamento dos dados utilizados, sem reivindicar direitos sobre informações pertencentes a terceiros.

O artigo científico associado ao projeto apresenta a metodologia, os experimentos e a discussão dos resultados obtidos.

## Autoras
Autora: Julya Gonçalves Pires

- Email: julyapires500@gmail.com
- GitHub: [JulyaGPires](https://github.com/JulyaGPires)

Autora: Rita Mariê Amaral Siqueira

- Email: ritamariecajuru@gmail.com
- GitHub: [Ritaa-Marie](https://github.com/Ritaa-Marie)
- Linkedin: [Rita Mariê](https://www.linkedin.com/in/rita-mari%C3%AA-amaral-siqueira-567b74357/)