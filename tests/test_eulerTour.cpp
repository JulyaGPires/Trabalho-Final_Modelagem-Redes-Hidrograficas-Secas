#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <iostream>
#include <random>
#include "../src/includes/Floresta.hpp"
#include "../src/includes/Bfs.hpp"
#include "../src/includes/EulerTour.hpp"

using namespace std;

static int falhas = 0;
#define CHECA(cond, msg) do { if (!(cond)) { cout << "FALHOU: " << msg << "\n"; falhas++; } } while (0)

struct Resultado {
    size_t consultas = 0, divergencias = 0;
    double maxAbs = 0.0, maxRel = 0.0;
};

// Compara Euler Tour e BFS nos trechos indicados.
static Resultado comparaComBFS(const Floresta& f, const EulerTour& et, const vector<int32_t>& trechos, double tol) {
    BFS bfs;
    Resultado r;
    for (int32_t u : trechos) {
        double b = bfs.deficitBFS(f, u);
        double e = et.deficitEuler(u);
        double d = fabs(e - b);
        r.consultas++;
        r.maxAbs = max(r.maxAbs, d);
        if (b != 0.0) r.maxRel = max(r.maxRel, d / fabs(b));
        if (d > tol || et.tamanhoBacia(u) != bfs.tamanhoBacia()) r.divergencias++;
    }
    return r;
}

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
    Resultado r = comparaComBFS(f, et, todos, 0.0);
    printf("[aleatoria, todos os nos] consultas: %zu | divergencias: %zu\n", r.consultas, r.divergencias);
    CHECA(r.divergencias == 0, "aleatoria: Euler Tour diferente da BFS");
}

static void cadeiaLonga() {
    const int N = 1000000;
    vector<int64_t> ids(N), next(N);
    vector<double> pesos(N, 1.0);
    for (int i = 0; i < N; i++) { ids[i] = i + 1; next[i] = (i == 0) ? 0 : i; }
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

// Teste na rede real, com trechos sorteados por faixa de tamanho de bacia.
static int redeReal(const string& caminho, const string& coluna) {
    Floresta f;
    string erro;
    if (!f.carregarCSV(caminho, coluna, &erro)) { cout << "Erro: " << erro << "\n"; return 1; }
    if (coluna.empty()) f.pesosSinteticos(42);

    EulerTour et;
    auto t0 = chrono::steady_clock::now();
    if (!et.preprocessar(f)) { cout << "Erro: preprocessar falhou\n"; return 1; }
    double seg = chrono::duration<double>(chrono::steady_clock::now() - t0).count();
    printf("[real] pre-processamento do Euler Tour: %.3f s\n", seg);

    double total = 0.0;
    for (double p : f.peso) total += p;
    double tol = coluna.empty() ? 0.0 : 1e-13 * total;
    printf("[real] pesos: %s | soma total: %.6g | tolerancia absoluta: %.3g\n",
           coluna.empty() ? "inteiros sinteticos" : coluna.c_str(), total, tol);

    // faixas pelo tamanho da bacia (o Euler Tour informa o tamanho em O(1))
    const array<size_t, 6> limite = {10, 100, 1000, 10000, 100000, (size_t)-1};
    const array<const char*, 6> nome = {"1-10", "11-100", "101-1000", "1001-10000", "10001-100000", ">100000"};
    const array<size_t, 6> maximo = {200, 200, 200, 100, 50, 10};
    array<vector<int32_t>, 6> escolhidos;
    array<size_t, 6> vistos = {0, 0, 0, 0, 0, 0};
    mt19937 rng(3);
    for (int32_t v = 0; v < f.n; v++) {
        size_t s = et.tamanhoBacia(v);
        int b = 0;
        while (s > limite[b]) b++;
        vistos[b]++;
        if (escolhidos[b].size() < maximo[b]) escolhidos[b].push_back(v);
        else { size_t j = rng() % vistos[b]; if (j < maximo[b]) escolhidos[b][j] = v; }   // reservoir sampling
    }

    size_t divTotal = 0;
    for (int b = 0; b < 6; b++) {
        Resultado r = comparaComBFS(f, et, escolhidos[b], tol);
        divTotal += r.divergencias;
        printf("[faixa %-12s] trechos na faixa: %8zu | consultas: %4zu | divergencias: %zu | max |dif|: %.3g | max dif relativa: %.3g\n",
               nome[b], vistos[b], r.consultas, r.divergencias, r.maxAbs, r.maxRel);
    }
    CHECA(divTotal == 0, "Euler Tour diferente da BFS");
    if (falhas == 0) cout << "TESTE OK\n"; else cout << falhas << " falha(s)\n";
    return falhas == 0 ? 0 : 1;
}

int main(int argc, char** argv) {
    if (argc > 1) return redeReal(argv[1], argc > 2 ? argv[2] : "");

    arvorePequena();
    florestaAleatoria();
    cadeiaLonga();
    if (falhas == 0) cout << "TESTE OK\n"; else cout << falhas << " falha(s)\n";
    return falhas == 0 ? 0 : 1;
}