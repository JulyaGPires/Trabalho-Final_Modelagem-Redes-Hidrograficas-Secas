#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <random>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "Floresta.hpp"
#include "Bfs.hpp"
#include "EulerTour.hpp"

using namespace std;
using Relogio = chrono::steady_clock;

// guarda o resultado das somas para o compilador não jogar o cálculo fora
static volatile double sorvedouro = 0.0;

// ---------------------------------------------------------------- faixas de tamanho de bacia

const int NUM_FAIXAS = 6;
const int NUM_GRUPOS = 7;   // as 6 faixas mais as 10 maiores bacias (grupo "top10")

static const size_t LIMITE[NUM_FAIXAS] = {10, 100, 1000, 10000, 100000, (size_t)-1};
static const char* NOME[NUM_GRUPOS] = {"1-10", "11-100", "101-1000", "1001-10000", "10001-100000", ">100000", "top10"};
static const size_t BASE_CONSULTAS[NUM_FAIXAS] = {1000, 1000, 1000, 500, 200, 100};   // por execução

// ---------------------------------------------------------------- estruturas

struct Config {
    string csv;
    string coluna;            
    string pasta = "results";
    int execucoes = 10;
    unsigned semente = 42;
    double escala = 1.0;
    int bfsTodos = 0;         
};

// o que foi medido para um grupo de consultas em uma execução
struct MedidaGrupo {
    size_t consultas = 0;
    size_t tamanhoMax = 0;
    size_t divergencias = 0;
    double tamanhoMedio = 0.0;
    double nsBFS = 0.0;        // ns por consulta
    double nsEuler = 0.0;      // ns por consulta
    double nsPorVisita = 0.0;  // ns da BFS por trecho visitado
};

struct Grupo {
    vector<int32_t> candidatos;    // todos os trechos do grupo
    size_t somaTamanhos = 0;       // soma dos tamanhos de bacia de todos os trechos do grupo
    vector<MedidaGrupo> medidas;   // uma por execução
};

// uma consulta de BFS cronometrada sozinha (para o gráfico de dispersão)
struct Individual {
    int grupo;
    int execucao;
    size_t tamanho;
    double ns;
};

struct Estat {
    double media = 0.0;
    double desvio = 0.0;
};

// medidas que valem para a execução inteira (não são por faixa)
struct MedidaGeral {
    double tempoPreproc = 0.0;
    double tempoPosOrdem = 0.0;
    double tempoEulerTodos = 0.0;
    double maxDifTodos = 0.0;
    size_t divergenciasTodos = 0;
};

// ---------------------------------------------------------------- utilidades

static double segundos(Relogio::time_point a, Relogio::time_point b) {
    return chrono::duration<double>(b - a).count();
}

static double nanos(Relogio::time_point a, Relogio::time_point b) {
    return chrono::duration<double, nano>(b - a).count();
}

static Estat estatistica(const vector<double>& v) {
    Estat e;
    if (v.empty()) return e;
    for (double x : v) e.media += x;
    e.media /= (double)v.size();
    if (v.size() > 1) {
        double s = 0.0;
        for (double x : v) s += (x - e.media) * (x - e.media);
        e.desvio = sqrt(s / (double)(v.size() - 1));   // desvio amostral
    }
    return e;
}

static double mediana(vector<double> v) {
    if (v.empty()) return 0.0;
    sort(v.begin(), v.end());
    size_t n = v.size();
    if (n % 2 == 1) return v[n / 2];
    return (v[n / 2 - 1] + v[n / 2]) / 2.0;
}

// lê uma linha do /proc/self/status (VmRSS, VmHWM...), valor em kB
static long lerKb(const string& chave) {
    ifstream arq("/proc/self/status");
    string linha;
    while (getline(arq, linha)) {
        if (linha.rfind(chave + ":", 0) == 0) {
            return atol(linha.c_str() + chave.size() + 1);
        }
    }
    return -1;
}

// zera o pico de memória do processo (VmHWM) para medir só o que vem depois
static bool resetarPicoRSS() {
    ofstream arq("/proc/self/clear_refs");
    if (!arq) return false;
    arq << "5";
    arq.flush();
    return arq.good();
}

static string modeloCPU() {
    ifstream arq("/proc/cpuinfo");
    string linha;
    while (getline(arq, linha)) {
        if (linha.rfind("model name", 0) == 0) {
            size_t p = linha.find(':');
            if (p != string::npos && p + 2 <= linha.size()) return linha.substr(p + 2);
        }
    }
    return "desconhecido";
}

static long memTotalMb() {
    ifstream arq("/proc/meminfo");
    string linha;
    while (getline(arq, linha)) {
        if (linha.rfind("MemTotal:", 0) == 0) return atol(linha.c_str() + 9) / 1024;
    }
    return -1;
}

static string versaoSistema() {
    ifstream arq("/proc/version");
    string linha;
    getline(arq, linha);
    return linha;
}

static bool lerArgumentos(int argc, char** argv, Config& cfg) {
    vector<string> posicionais;
    for (int i = 1; i < argc; i++) {
        string a = argv[i];
        if (a == "--execucoes" && i + 1 < argc) cfg.execucoes = atoi(argv[++i]);
        else if (a == "--semente" && i + 1 < argc) cfg.semente = (unsigned)atol(argv[++i]);
        else if (a == "--pasta" && i + 1 < argc) cfg.pasta = argv[++i];
        else if (a == "--escala" && i + 1 < argc) cfg.escala = atof(argv[++i]);
        else if (a == "--bfs-todos" && i + 1 < argc) cfg.bfsTodos = atoi(argv[++i]);
        else if (a.rfind("--", 0) == 0) {
            cout << "opção desconhecida: " << a << "\n";
            return false;
        } else posicionais.push_back(a);
    }
    if (posicionais.empty()) {
        cout << "uso: ./build/benchmark <csv> [coluna_de_peso] [--execucoes N] [--semente S] [--pasta DIR] [--escala X] [--bfs-todos N]\n";
        cout << "ex.: ./build/benchmark data/processed/dataset_com_deficit.csv deficit_seca\n";
        return false;
    }
    cfg.csv = posicionais[0];
    if (posicionais.size() > 1) cfg.coluna = posicionais[1];
    if (cfg.execucoes < 1 || cfg.escala <= 0.0 || cfg.bfsTodos < 0) {
        cout << "--execucoes precisa ser >= 1, --escala > 0 e --bfs-todos >= 0\n";
        return false;
    }
    return true;
}

// ---------------------------------------------------------------- calcular o déficit de todos os trechos sem Euler Tour
// passada única: processa cada trecho só depois de todos os afluentes dele (ordem de Kahn)
// e já soma o acumulado dele no trecho a jusante. serve de baseline e de conferência independente.
// devolve false se a rede contiver ciclos (número de trechos processados != n).
static bool somarPorKahn(const Floresta& f, vector<double>& acumulado) {
    acumulado = f.peso;
    vector<int32_t> grau(f.n);
    for (int32_t i = 0; i < f.n; i++) {
        grau[i] = f.iniFilhos[i + 1] - f.iniFilhos[i];
    }

    vector<int32_t> fila;
    fila.reserve(f.n);
    for (int32_t i = 0; i < f.n; i++) {
        if (grau[i] == 0) fila.push_back(i);   // nascentes
    }

    size_t proximo = 0;
    while (proximo < fila.size()) {
        int32_t v = fila[proximo];
        proximo++;
        int32_t pai = f.jusante[v];
        if (pai >= 0) {
            acumulado[pai] += acumulado[v];
            grau[pai]--;
            if (grau[pai] == 0) fila.push_back(pai);
        }
    }
    return fila.size() == static_cast<size_t>(f.n);
}

// ---------------------------------------------------------------- mede um conjunto de consultas
static MedidaGrupo medirGrupo(const Floresta& f, BFS& bfs, const EulerTour& et,
                              const vector<int32_t>& consultas, double tol,
                              vector<pair<size_t, double>>& individuais) {
    MedidaGrupo m;
    size_t n = consultas.size();
    m.consultas = n;

    vector<double> resBFS(n);
    vector<double> resEuler(n);

    // tamanho das bacias (fora da parte cronometrada)
    size_t somaTamanhos = 0;
    for (int32_t u : consultas) {
        size_t t = et.tamanhoBacia(u);
        somaTamanhos += t;
        m.tamanhoMax = max(m.tamanhoMax, t);
    }
    m.tamanhoMedio = (double)somaTamanhos / (double)n;

    // BFS: todas as consultas do grupo de uma vez, divide pelo número de consultas
    auto a = Relogio::now();
    for (size_t i = 0; i < n; i++) {
        resBFS[i] = bfs.deficitBFS(f, consultas[i]);
    }
    double totalBFS = nanos(a, Relogio::now());
    m.nsBFS = totalBFS / (double)n;
    m.nsPorVisita = totalBFS / (double)somaTamanhos;

    // Euler Tour: mesmas consultas, mesmo jeito
    a = Relogio::now();
    for (size_t i = 0; i < n; i++) {
        resEuler[i] = et.deficitEuler(consultas[i]);
    }
    double totalEuler = nanos(a, Relogio::now());
    m.nsEuler = totalEuler / (double)n;

    // confere se os dois deram o mesmo resultado (fora da medição)
    for (size_t i = 0; i < n; i++) {
        if (fabs(resBFS[i] - resEuler[i]) > tol) m.divergencias++;
    }

    // BFS uma consulta por vez, para o gráfico de tempo x tamanho da bacia
    individuais.clear();
    for (int32_t u : consultas) {
        auto b = Relogio::now();
        double valor = bfs.deficitBFS(f, u);
        double ns = nanos(b, Relogio::now());
        sorvedouro = sorvedouro + valor;
        individuais.push_back({et.tamanhoBacia(u), ns});
    }

    return m;
}

// ---------------------------------------------------------------- arquivos de saída

static void escreverAmbiente(const string& caminho, const Config& cfg, const Floresta& f, bool picoOk) {
    ofstream out(caminho);
    string so = versaoSistema();
    string soMin = so;
    for (char& c : soMin) c = (char)tolower((unsigned char)c);
    bool wsl = soMin.find("microsoft") != string::npos;

    out << "arquivo de pesos: " << cfg.csv << "\n";
    out << "cenário (coluna de peso): " << (cfg.coluna.empty() ? "pesos inteiros sintéticos" : cfg.coluna) << "\n";
    out << "trechos: " << f.n << " | raízes: " << f.raizes.size() << "\n";
    out << "execuções gravadas: " << cfg.execucoes << " (mais 1 de aquecimento) | semente: " << cfg.semente
        << " | escala das consultas: " << cfg.escala << " | passadas BFS (--bfs-todos): " << cfg.bfsTodos << "\n";
    out << "CPU: " << modeloCPU() << "\n";
    out << "threads de hardware: " << thread::hardware_concurrency() << "\n";
    out << "RAM total: " << memTotalMb() << " MB\n";
    out << "sistema: " << so << "\n";
    out << "WSL: " << (wsl ? "sim" : "não") << "\n";
#ifdef __VERSION__
    out << "compilador: " << __VERSION__ << "\n";
#endif
#ifdef __OPTIMIZE__
    out << "compilado com otimização (-O2/-O3): sim\n";
#else
    out << "compilado com otimização (-O2/-O3): NÃO (os tempos não valem para o artigo)\n";
#endif
    out << "pico de memória do Euler Tour medido: " << (picoOk ? "sim" : "não (clear_refs indisponível)") << "\n";
}

int main(int argc, char** argv) {
    Config cfg;
    if (!lerArgumentos(argc, argv, cfg)) return 1;

    string tag = cfg.coluna.empty() ? "sintetico" : cfg.coluna;
    filesystem::create_directories(cfg.pasta);
    string prefixo = cfg.pasta + "/benchmark_" + tag;

#ifndef __OPTIMIZE__
    cout << "AVISO: compilado sem otimização. Use -O3 para valer.\n";
#endif

    // ---------------------------------------------------------------- carrega a floresta
    Floresta f;
    string erro;
    cout << "lendo " << cfg.csv << " ...\n";
    auto inicio = Relogio::now();
    if (!f.carregarCSV(cfg.csv, cfg.coluna, &erro)) {
        cout << "Erro: " << erro << "\n";
        return 1;
    }
    double tempoCarregamento = segundos(inicio, Relogio::now());
    if (cfg.coluna.empty()) f.pesosSinteticos(cfg.semente);   

    long picoCarregamentoKb = lerKb("VmHWM");   

    double somaPesos = 0.0;
    for (double p : f.peso) somaPesos += p;
    // pesos reais: soma de double em ordens diferentes muda os últimos dígitos, então precisa de tolerância
    double tol = cfg.coluna.empty() ? 0.0 : 1e-13 * somaPesos;
    double tolTodos = cfg.coluna.empty() ? 0.0 : 1e-12 * somaPesos;   // mais folgada: são 8 milhões de valores

    printf("trechos: %d | raízes: %zu | soma dos pesos: %.6g | cenário: %s\n",
           f.n, f.raizes.size(), somaPesos, tag.c_str());

    // ---------------------------------------------------------------- memória do Euler Tour
    bool picoOk = resetarPicoRSS();
    long rssAntes = lerKb("VmRSS");

    unique_ptr<EulerTour> etBase(new EulerTour());
    if (!etBase->preprocessar(f)) {
        cout << "Erro: o pré-processamento do Euler Tour falhou (algum trecho não foi visitado)\n";
        return 1;
    }
    long rssDepois = lerKb("VmRSS");
    long picoDepois = lerKb("VmHWM");
    long eulerResidenteKb = rssDepois - rssAntes;
    long eulerPicoKb = picoOk ? (picoDepois - rssAntes) : -1;

    // ---------------------------------------------------------------- separa os trechos por faixa de tamanho de bacia
    vector<Grupo> grupos(NUM_GRUPOS);
    for (int32_t v = 0; v < f.n; v++) {
        size_t s = etBase->tamanhoBacia(v);
        int g = 0;
        while (s > LIMITE[g]) g++;
        grupos[g].candidatos.push_back(v);
        grupos[g].somaTamanhos += s;
    }

    // as 10 maiores bacias da rede (se houver na última faixa, pega de lá; senão pega de todos os trechos)
    {
        vector<int32_t> ordenados;
        if (!grupos[NUM_FAIXAS - 1].candidatos.empty()) {
            ordenados = grupos[NUM_FAIXAS - 1].candidatos;
        } else {
            ordenados.resize(f.n);
            iota(ordenados.begin(), ordenados.end(), 0);
        }
        sort(ordenados.begin(), ordenados.end(), [&](int32_t x, int32_t y) {
            return etBase->tamanhoBacia(x) > etBase->tamanhoBacia(y);
        });
        size_t quantas = min<size_t>(10, ordenados.size());
        for (size_t i = 0; i < quantas; i++) {
            grupos[NUM_GRUPOS - 1].candidatos.push_back(ordenados[i]);
            grupos[NUM_GRUPOS - 1].somaTamanhos += etBase->tamanhoBacia(ordenados[i]);
        }
    }

    size_t maiorBacia = 0;
    int32_t trechoMaiorBacia = 0;
    for (int32_t u : grupos[NUM_GRUPOS - 1].candidatos) {
        if (etBase->tamanhoBacia(u) > maiorBacia) {
            maiorBacia = etBase->tamanhoBacia(u);
            trechoMaiorBacia = u;
        }
    }

    // ---------------------------------------------------------------- memória da fila da BFS (na maior bacia da rede)
    long bfsFilaKb = -1;
    size_t bfsCapacidadeFila = 0;
    if (maiorBacia > 0) {
        long antes = lerKb("VmRSS");
        BFS bfsMemoria;
        sorvedouro = sorvedouro + bfsMemoria.deficitBFS(f, trechoMaiorBacia);
        bfsCapacidadeFila = bfsMemoria.capacidadeFila();
        long depois = lerKb("VmRSS");
        bfsFilaKb = depois - antes;
    }
    etBase.reset();   // libera o Euler Tour usado só para classificar

    // ---------------------------------------------------------------- rodadas de medição
    BFS bfs;
    vector<MedidaGeral> gerais;
    vector<Individual> individuaisTodos;

    cout << "medindo (1 rodada de aquecimento + " << cfg.execucoes << " gravadas)...\n";
    for (int rodada = -1; rodada < cfg.execucoes; rodada++) {
        bool registrar = rodada >= 0;
        MedidaGeral geral;

        // pré-processamento do Euler Tour (objeto novo a cada rodada)
        EulerTour et;
        auto a = Relogio::now();
        if (!et.preprocessar(f)) {
            cout << "Erro: o pré-processamento do Euler Tour falhou\n";
            return 1;
        }
        geral.tempoPreproc = segundos(a, Relogio::now());

        // consultas por faixa
        for (int g = 0; g < NUM_GRUPOS; g++) {
            const vector<int32_t>& candidatos = grupos[g].candidatos;
            if (candidatos.empty()) continue;

            vector<int32_t> consultas;
            if (g < NUM_FAIXAS) {
                size_t quantas = max<size_t>(1, (size_t)(BASE_CONSULTAS[g] * cfg.escala));
                mt19937 rng(cfg.semente + 7919u * (unsigned)(rodada + 2) + (unsigned)g);
                uniform_int_distribution<size_t> sorteio(0, candidatos.size() - 1);
                for (size_t i = 0; i < quantas; i++) consultas.push_back(candidatos[sorteio(rng)]);
            } else {
                consultas = candidatos;   // as 10 maiores, sempre as mesmas
            }

            vector<pair<size_t, double>> individuais;
            MedidaGrupo m = medirGrupo(f, bfs, et, consultas, tol, individuais);
            if (registrar) {
                grupos[g].medidas.push_back(m);
                for (auto& par : individuais) {
                    individuaisTodos.push_back({g, rodada + 1, par.first, par.second});
                }
            }
        }

        // déficit de todos os trechos: passada única (Kahn)
        vector<double> porKahn;
        a = Relogio::now();
        if (!somarPorKahn(f, porKahn)) {
            cout << "Erro: a rede possui ciclos (o algoritmo de Kahn não processou todos os trechos)\n";
            return 1;
        }
        geral.tempoPosOrdem = segundos(a, Relogio::now());

        // déficit de todos os trechos: uma consulta do Euler Tour para cada trecho
        vector<double> todosEuler(f.n);
        a = Relogio::now();
        for (int32_t v = 0; v < f.n; v++) {
            todosEuler[v] = et.deficitEuler(v);
        }
        geral.tempoEulerTodos = segundos(a, Relogio::now());

        // compara os dois (os 8 milhões de valores)
        for (int32_t v = 0; v < f.n; v++) {
            double d = fabs(porKahn[v] - todosEuler[v]);
            geral.maxDifTodos = max(geral.maxDifTodos, d);
            if (d > tolTodos) geral.divergenciasTodos++;
        }
        sorvedouro = sorvedouro + porKahn[0] + todosEuler[0];

        if (registrar) {
            gerais.push_back(geral);
            printf("  execução %d/%d ok (pré-processamento %.3f s)\n", rodada + 1, cfg.execucoes, geral.tempoPreproc);
        } else {
            cout << "  aquecimento ok\n";
        }
    }

    long picoFinalKb = lerKb("VmHWM");

    // ---------------------------------------------------------------- BFS em todos os trechos (opcional via --bfs-todos N)
    vector<double> temposBfsTodos;
    if (cfg.bfsTodos > 0) {
        cout << "\nexecutando BFS em todos os trechos (" << cfg.bfsTodos << " passadas)...\n";
        vector<double> todosBFS(f.n);
        for (int p = 0; p < cfg.bfsTodos; p++) {
            auto a = Relogio::now();
            for (int32_t v = 0; v < f.n; v++) {
                todosBFS[v] = bfs.deficitBFS(f, v);
            }
            double t = segundos(a, Relogio::now());
            temposBfsTodos.push_back(t);
            sorvedouro = sorvedouro + todosBFS[0];
            printf("  passada BFS %d/%d: %.3f s\n", p + 1, cfg.bfsTodos, t);
        }
    }

    // ---------------------------------------------------------------- resumo estatístico
    vector<double> vPre, vPos, vEulerTodos;
    size_t divergenciasTotais = 0;
    double maxDifGlobal = 0.0;
    for (auto& g : gerais) {
        vPre.push_back(g.tempoPreproc);
        vPos.push_back(g.tempoPosOrdem);
        vEulerTodos.push_back(g.tempoEulerTodos);
        divergenciasTotais += g.divergenciasTodos;
        maxDifGlobal = max(maxDifGlobal, g.maxDifTodos);
    }
    Estat ePre = estatistica(vPre);
    Estat ePos = estatistica(vPos);
    Estat eEulerTodos = estatistica(vEulerTodos);
    double preprocMediana = mediana(vPre);

    size_t divergenciasConsultas = 0;
    size_t tamanhoMaxGlobal = 0;
    for (auto& g : grupos) {
        for (auto& m : g.medidas) {
            divergenciasConsultas += m.divergencias;
            tamanhoMaxGlobal = max(tamanhoMaxGlobal, m.tamanhoMax);
        }
    }

    // por faixa: médias, razão, ponto de equilíbrio
    struct ResumoFaixa {
        Estat bfs, euler, razao, porVisita, tamMedio;
        double equilibrio = -1.0;   // -1 = o Euler Tour nunca compensa nessa faixa
        bool temDados = false;
    };
    vector<ResumoFaixa> resumo(NUM_GRUPOS);
    double estimativaBFSTodos = 0.0;   // segundos
    for (int g = 0; g < NUM_GRUPOS; g++) {
        if (grupos[g].medidas.empty()) continue;
        vector<double> vb, ve, vr, vv, vt;
        for (auto& m : grupos[g].medidas) {
            vb.push_back(m.nsBFS);
            ve.push_back(m.nsEuler);
            vr.push_back(m.nsEuler > 0 ? m.nsBFS / m.nsEuler : 0.0);
            vv.push_back(m.nsPorVisita);
            vt.push_back(m.tamanhoMedio);
        }
        ResumoFaixa& r = resumo[g];
        r.temDados = true;
        r.bfs = estatistica(vb);
        r.euler = estatistica(ve);
        r.razao = estatistica(vr);
        r.porVisita = estatistica(vv);
        r.tamMedio = estatistica(vt);

        // ponto de equilíbrio: preparo do Euler Tour (mediana) / quanto cada consulta economiza
        double economia = r.bfs.media - r.euler.media;
        if (economia > 0.0) r.equilibrio = (preprocMediana * 1e9) / economia;

        // estimativa de calcular todos os trechos da faixa com BFS (não inclui o top10, que se repete)
        if (g < NUM_FAIXAS) {
            estimativaBFSTodos += (double)grupos[g].somaTamanhos * r.porVisita.media * 1e-9;
        }
    }

    // soma dos tamanhos de bacia de todos os trechos (quantas visitas a BFS faria para calcular todos)
    size_t somaTodosTamanhos = 0;
    for (int g = 0; g < NUM_FAIXAS; g++) somaTodosTamanhos += grupos[g].somaTamanhos;

    // ponto de equilíbrio para uso misto (consultas distribuídas uniformemente pelos trechos da rede)
    double tempoBfsMisto = 0.0;
    double tempoEulerMisto = 0.0;
    for (int g = 0; g < NUM_FAIXAS; g++) {
        double pesoFaixa = (double)grupos[g].candidatos.size() / (double)f.n;
        tempoBfsMisto += pesoFaixa * resumo[g].bfs.media;
        tempoEulerMisto += pesoFaixa * resumo[g].euler.media;
    }
    double economiaMista = tempoBfsMisto - tempoEulerMisto;
    double equilibrioMisto = economiaMista > 0.0 ? (preprocMediana * 1e9) / economiaMista : -1.0;
    double razaoMista = tempoEulerMisto > 0.0 ? tempoBfsMisto / tempoEulerMisto : 0.0;
    double tamMedioMisto = (double)somaTodosTamanhos / (double)f.n;

    // memória estimada pelos tamanhos dos vetores
    double memFlorestaBytes = (double)f.memoriaBytes();
    double memEulerEstimada = (double)f.n * 3.0 * sizeof(int32_t) + ((double)f.n + 1.0) * sizeof(double);
    double memEulerPicoSemPilha = memEulerEstimada + (double)f.n * sizeof(int32_t);
    // limite superior com o pior caso teórico da pilha da DFS (árvore degenerada em linha: n * int32_t)
    double memEulerPicoComPilhaPiorCaso = memEulerPicoSemPilha + (double)f.n * sizeof(int32_t);
    double memFilaBFSMinimaEstimada = (double)tamanhoMaxGlobal * sizeof(int32_t);
    double memFilaBFSAlocadaReal = (double)bfsCapacidadeFila * sizeof(int32_t);

    // ---------------------------------------------------------------- escreve os CSVs
    escreverAmbiente(prefixo + "_ambiente.txt", cfg, f, picoOk);

    {   // 1) uma linha por faixa e execução
        ofstream out(prefixo + "_consultas.csv");
        out << setprecision(10);
        out << "cenario,faixa,execucao,consultas,tamanho_medio_bacia,tamanho_max_bacia,"
               "ns_por_consulta_bfs,ns_por_consulta_euler,razao_bfs_euler,ns_por_trecho_visitado_bfs,divergencias\n";
        for (int g = 0; g < NUM_GRUPOS; g++) {
            for (size_t e = 0; e < grupos[g].medidas.size(); e++) {
                const MedidaGrupo& m = grupos[g].medidas[e];
                out << tag << ',' << NOME[g] << ',' << (e + 1) << ',' << m.consultas << ',' << m.tamanhoMedio << ','
                    << m.tamanhoMax << ',' << m.nsBFS << ',' << m.nsEuler << ','
                    << (m.nsEuler > 0 ? m.nsBFS / m.nsEuler : 0.0) << ',' << m.nsPorVisita << ',' << m.divergencias << '\n';
            }
        }
    }

    {   // 2) média e desvio por faixa, com o ponto de equilíbrio
        ofstream out(prefixo + "_resumo_faixas.csv");
        out << setprecision(10);
        out << "cenario,faixa,trechos_na_faixa,soma_tamanhos_bacia,tamanho_medio_bacia,"
               "bfs_ns_media,bfs_ns_desvio,euler_ns_media,euler_ns_desvio,razao_media,razao_desvio,"
               "ns_por_trecho_visitado_bfs,preproc_euler_s_media,preproc_euler_s_mediana,consultas_equilibrio\n";
        for (int g = 0; g < NUM_GRUPOS; g++) {
            const ResumoFaixa& r = resumo[g];
            if (!r.temDados) continue;
            out << tag << ',' << NOME[g] << ',' << grupos[g].candidatos.size() << ',' << grupos[g].somaTamanhos << ','
                << r.tamMedio.media << ',' << r.bfs.media << ',' << r.bfs.desvio << ',' << r.euler.media << ','
                << r.euler.desvio << ',' << r.razao.media << ',' << r.razao.desvio << ',' << r.porVisita.media << ','
                << ePre.media << ',' << preprocMediana << ',' << r.equilibrio << '\n';
        }
        if (equilibrioMisto > 0.0) {
            out << tag << ",misto_uniforme," << f.n << ',' << somaTodosTamanhos << ','
                << tamMedioMisto << ',' << tempoBfsMisto << ",," << tempoEulerMisto << ",,"
                << razaoMista << ",,," << ePre.media << ',' << preprocMediana << ',' << equilibrioMisto << '\n';
        }
    }

    {   // 3) tempos de cada BFS sozinha (dispersão tempo x tamanho)
        ofstream out(prefixo + "_bfs_individual.csv");
        out << setprecision(10);
        out << "cenario,faixa,execucao,tamanho_bacia,ns_bfs\n";
        for (const Individual& i : individuaisTodos) {
            out << tag << ',' << NOME[i.grupo] << ',' << i.execucao << ',' << i.tamanho << ',' << i.ns << '\n';
        }
    }

    {   // 4) medidas gerais, formato longo (metrica,execucao,valor,unidade)
        ofstream out(prefixo + "_geral.csv");
        out << setprecision(10);
        out << "cenario,metrica,execucao,valor,unidade\n";
        auto linha = [&](const string& metrica, const string& exec, double valor, const string& unidade) {
            out << tag << ',' << metrica << ',' << exec << ',' << valor << ',' << unidade << '\n';
        };
        linha("trechos", "unico", f.n, "trechos");
        linha("raizes", "unico", (double)f.raizes.size(), "trechos");
        linha("soma_pesos", "unico", somaPesos, "peso");
        linha("tempo_leitura_csv_e_floresta", "unico", tempoCarregamento, "s");
        linha("pico_rss_leitura_csv", "unico", (double)picoCarregamentoKb, "kB");
        linha("memoria_floresta_vetores", "unico", memFlorestaBytes, "bytes");
        linha("memoria_euler_residente_estimada", "unico", memEulerEstimada, "bytes");
        linha("memoria_euler_pico_estimado_sem_pilha", "unico", memEulerPicoSemPilha, "bytes");
        linha("memoria_euler_pico_estimado_pior_caso_com_pilha", "unico", memEulerPicoComPilhaPiorCaso, "bytes");
        linha("memoria_euler_rss_residente", "unico", (double)eulerResidenteKb, "kB");
        linha("memoria_euler_rss_pico_preprocessamento", "unico", (double)eulerPicoKb, "kB");
        linha("memoria_fila_bfs_alocada_capacidade", "unico", memFilaBFSAlocadaReal, "bytes");
        linha("memoria_fila_bfs_minima_estimada", "unico", memFilaBFSMinimaEstimada, "bytes");
        linha("memoria_fila_bfs_rss_observacao", "unico", (double)bfsFilaKb, "kB");
        linha("tamanho_maior_bacia", "unico", (double)maiorBacia, "trechos");
        linha("soma_tamanhos_de_todas_as_bacias", "unico", (double)somaTodosTamanhos, "visitas");
        linha("estimativa_bfs_todos_os_trechos", "unico", estimativaBFSTodos, "s");
        linha("preproc_euler_s_mediana", "unico", preprocMediana, "s");
        linha("consultas_equilibrio_misto_uniforme", "unico", equilibrioMisto, "consultas");
        linha("tempo_medio_bfs_misto_uniforme", "unico", tempoBfsMisto, "ns");
        linha("tempo_medio_euler_misto_uniforme", "unico", tempoEulerMisto, "ns");
        linha("pico_rss_processo_fim", "unico", (double)picoFinalKb, "kB");
        for (size_t e = 0; e < gerais.size(); e++) {
            string ex = to_string(e + 1);
            linha("tempo_preprocessamento_euler", ex, gerais[e].tempoPreproc, "s");
            linha("tempo_todos_trechos_kahn", ex, gerais[e].tempoPosOrdem, "s");
            linha("tempo_todos_trechos_euler", ex, gerais[e].tempoEulerTodos, "s");
            linha("max_dif_kahn_euler_todos", ex, gerais[e].maxDifTodos, "peso");
            linha("divergencias_kahn_euler_todos", ex, (double)gerais[e].divergenciasTodos, "trechos");
        }
        for (size_t p = 0; p < temposBfsTodos.size(); p++) {
            string ex = to_string(p + 1);
            linha("tempo_todos_trechos_bfs", ex, temposBfsTodos[p], "s");
        }
    }

    // ---------------------------------------------------------------- resumo no terminal
    printf("\n================ resultados (%s) ================\n", tag.c_str());
    printf("leitura do CSV + floresta: %.2f s (informativo)\n", tempoCarregamento);
    printf("pré-processamento do Euler Tour: %.3f s ± %.3f s (mediana: %.3f s)\n", ePre.media, ePre.desvio, preprocMediana);
    printf("\n%-13s %10s %12s %14s %14s %10s %16s\n", "faixa", "trechos", "tam. médio", "BFS (ns)", "Euler (ns)", "razão", "equilíbrio");
    for (int g = 0; g < NUM_GRUPOS; g++) {
        const ResumoFaixa& r = resumo[g];
        if (!r.temDados) continue;
        char eq[32];
        if (r.equilibrio < 0) snprintf(eq, sizeof(eq), "nunca compensa");
        else snprintf(eq, sizeof(eq), "%.3g consultas", r.equilibrio);
        printf("%-13s %10zu %12.1f %14.1f %14.1f %9.1fx %16s\n", NOME[g], grupos[g].candidatos.size(),
               r.tamMedio.media, r.bfs.media, r.euler.media, r.razao.media, eq);
    }
    if (equilibrioMisto > 0.0) {
        printf("%-13s %10d %12.1f %14.1f %14.1f %9.1fx %.3g consultas\n",
               "misto_unif.*", f.n, tamMedioMisto, tempoBfsMisto, tempoEulerMisto, razaoMista, equilibrioMisto);
        printf("  (* misto_unif: ponderado pela distribuição uniforme dos trechos na rede; mediana pré-proc: %.3f s)\n", preprocMediana);
    }
    printf("\ncalcular o déficit de TODOS os trechos:\n");
    printf("  Euler Tour (1 consulta por trecho): %.3f s ± %.3f s\n", eEulerTodos.media, eEulerTodos.desvio);
    printf("  passada única (Kahn):               %.3f s ± %.3f s\n", ePos.media, ePos.desvio);
    printf("  BFS em cada trecho (estimativa):    %.1f s  (%zu visitas no total)\n", estimativaBFSTodos, somaTodosTamanhos);
    if (!temposBfsTodos.empty()) {
        Estat eBfs = estatistica(temposBfsTodos);
        printf("  BFS em cada trecho (medido):        %.3f s ± %.3f s (%d passadas)\n",
               eBfs.media, eBfs.desvio, (int)temposBfsTodos.size());
    }
    printf("\nmemória:\n");
    printf("  vetores da floresta:  %.1f MiB\n", memFlorestaBytes / (1024.0 * 1024.0));
    printf("  Euler Tour estimada:  %.1f MiB residente | pico pré-processamento: %.1f MiB (sem pilha) a %.1f MiB (pior caso com pilha)\n",
           memEulerEstimada / (1024.0 * 1024.0),
           memEulerPicoSemPilha / (1024.0 * 1024.0),
           memEulerPicoComPilhaPiorCaso / (1024.0 * 1024.0));
    
    printf("  Euler Tour medida pelo RSS: residente %.1f MiB | pico %s\n", eulerResidenteKb / 1024.0,
           eulerPicoKb < 0 ? "indisponível" : (to_string(eulerPicoKb / 1024) + " MiB").c_str());
    printf("  fila da BFS na maior bacia (%zu trechos): alocada %.1f MiB (capacidade %zu) | mín. teórico %.1f MiB | RSS obs. %.1f MiB\n",
           maiorBacia, memFilaBFSAlocadaReal / (1024.0 * 1024.0), bfsCapacidadeFila,
           memFilaBFSMinimaEstimada / (1024.0 * 1024.0), bfsFilaKb / 1024.0);
    printf("  pico do processo na leitura do CSV: %.1f MiB\n", picoCarregamentoKb / 1024.0);

    printf("\nconferências:\n");
    printf("  BFS x Euler nas consultas sorteadas: %zu divergências\n", divergenciasConsultas);
    printf("  Kahn x Euler em todos os trechos: %zu divergências | maior diferença %.3g (tolerância %.3g)\n",
           divergenciasTotais, maxDifGlobal, tolTodos);
    bool ok = (divergenciasConsultas == 0 && divergenciasTotais == 0);
    printf("%s\n", ok ? "CONFERÊNCIAS OK" : "ATENÇÃO: houve divergências, revisar antes de usar os tempos");
    printf("arquivos gravados em %s/ (prefixo benchmark_%s)\n", cfg.pasta.c_str(), tag.c_str());
    printf("(controle: %.6g)\n", (double)sorvedouro);
    return ok ? 0 : 1;
}