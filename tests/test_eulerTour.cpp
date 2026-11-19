#include <chrono>
#include <cstdio>
#include <iostream>
#include <random>
#include "../src/includes/Floresta.hpp"
#include "../src/includes/Bfs.hpp"
#include "../src/includes/EulerTour.hpp"

using namespace std;

static int falhas = 0;
#define CHECA(cond, msg) do { if (!(cond)) { cout << "FALHOU: " << msg << "\n"; falhas++; } } while (0)

// arvore pequena, floresta aleatoria (todos os nos) e uma cadeia longa.
static void arvorePequena() {
    Floresta f;
    string erro;
    f.construir({1, 2, 3, 4, 5}, {3, 3, 4, 0, 4}, {5, 3, 2, 1, 4}, &erro);
    EulerTour et;
    CHECA(et.preprocessar(f), "preprocessar falhou");
    CHECA(et.deficitEuler(f.indiceDe(3)) == 10, "C deve dar 10");
    CHECA(et.deficitEuler(f.indiceDe(4)) == 15, "D deve dar 15");
    CHECA(et.deficitEuler(f.indiceDe(1)) == 5, "A deve dar 5");
    CHECA(et.deficitEuler(f.indiceDe(5)) == 4, "E deve dar 4");
    CHECA(et.tamanhoBacia(f.indiceDe(3)) == 3, "bacia de C tem 3 trechos");
    CHECA(et.tamanhoBacia(f.indiceDe(4)) == 5, "bacia de D tem 5 trechos");
}

// compara com a BFS nos trechos indicados
static void comparaComBFS(const Floresta& f, const EulerTour& et, const vector<int32_t>& trechos, const string& nome) {
    BFS bfs;
    size_t divergencias = 0;
    for (int32_t u : trechos) {
        double b = bfs.deficitBFS(f, u);
        if (et.deficitEuler(u) != b || et.tamanhoBacia(u) != bfs.tamanhoBacia()) divergencias++;
    }

    printf("[%s] consultas: %zu | divergencias: %zu\n", nome.c_str(), trechos.size(), divergencias);
    CHECA(divergencias == 0, nome + ": Euler Tour diferente da BFS");
}

static void florestaAleatoria() {
    const int N = 200000;
    mt19937 rng(1);
    vector<int64_t> ids(N), next(N);
    vector<double> pesos(N, 1.0);

    for (int i = 0; i < N; i++) {
        ids[i] = i + 1;
        if (i == 0 || rng() % 50 == 0) next[i] = 0;
        else next[i] = (int64_t)(rng() % i) + 1;
    }

    Floresta f;
    string erro;
    CHECA(f.construir(ids, next, pesos, &erro), "construir aleatoria: " + erro);
    f.pesosSinteticos(7);
    EulerTour et;
    CHECA(et.preprocessar(f), "preprocessar falhou");

    vector<int32_t> todos(N);
    for (int i = 0; i < N; i++) todos[i] = i;
    comparaComBFS(f, et, todos, "aleatoria, todos os nos");
}

static void cadeiaLonga() {
    // 1 milhao de trechos em fila (pior caso para recursao): i desagua em i-1
    const int N = 1000000;
    vector<int64_t> ids(N), next(N);
    vector<double> pesos(N, 1.0);
    for (int i = 0; i < N; i++) { 
        ids[i] = i + 1; next[i] = (i == 0) ? 0 : i; 
    }

    Floresta f;
    string erro;
    CHECA(f.construir(ids, next, pesos, &erro), "construir cadeia: " + erro);
    EulerTour et;
    CHECA(et.preprocessar(f), "preprocessar falhou");
    CHECA(et.deficitEuler(0) == N, "cadeia: raiz deve somar N");
    CHECA(et.deficitEuler(N - 1) == 1, "cadeia: ultimo trecho soma 1");
    CHECA(et.deficitEuler(N / 2) == N - N / 2, "cadeia: meio");
    cout << "[cadeia 1M] sem estouro de pilha\n";
}

int main(int argc, char** argv) {
    if (argc > 1) {
        Floresta f;
        string erro;
        if (!f.carregarCSV(argv[1], "", &erro)) { cout << "Erro: " << erro << "\n"; return 1; }
        f.pesosSinteticos(42);
        EulerTour et;
        auto t0 = chrono::steady_clock::now();

        if (!et.preprocessar(f)) { cout << "Erro: preprocessar falhou\n"; return 1; }
        double seg = chrono::duration<double>(chrono::steady_clock::now() - t0).count();
        printf("[real] pre-processamento do Euler Tour: %.3f s\n", seg);
        mt19937 rng(3);
        vector<int32_t> sorteados(10000);
        
        for (auto& u : sorteados) u = (int32_t)(rng() % f.n);
        comparaComBFS(f, et, sorteados, "real, 10 mil trechos");
    } else {
        arvorePequena();
        florestaAleatoria();
        cadeiaLonga();
    }
    if (falhas == 0) cout << "TESTE OK\n"; else cout << falhas << " falha(s)\n";
    return falhas == 0 ? 0 : 1;
}