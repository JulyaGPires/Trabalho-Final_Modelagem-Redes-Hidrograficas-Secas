#include <chrono>
#include <cstdio>
#include <iostream>
#include <random>
#include "../src/includes/Floresta.hpp"
#include "../src/includes/Bfs.hpp"

using namespace std;

static int falhas = 0;
#define CHECA(cond, msg) do { if (!(cond)) { cout << "FALHOU: " << msg << "\n"; falhas++; } } while (0)

// Para cada raiz: a BFS da raiz cobre a arvore inteira. Somando todas as raizes,
// o total tem que ser igual a soma de todos os pesos e os nos visitados tem que somar n.
static void confereRaizes(const Floresta& f, const string& nome) {
    BFS bfs;
    double total = 0.0, esperado = 0.0;
    size_t visitados = 0;
    auto t0 = chrono::steady_clock::now();

    for (int32_t r : f.raizes) {
        total += bfs.deficitBFS(f, r);
        visitados += bfs.tamanhoBacia();
    }

    double seg = chrono::duration<double>(chrono::steady_clock::now() - t0).count();
    for (double p : f.peso) esperado += p;

    printf("[%s] BFS de todas as raizes: %.3f s | visitados: %zu de %d\n", nome.c_str(), seg, visitados, f.n);
    CHECA(visitados == (size_t)f.n, nome + ": nos visitados != n");
    CHECA(total == esperado, nome + ": soma das raizes != soma dos pesos");
}

static void arvorePequena() {
    // A=1 B=2 C=3 D=4 E=5 -> indices 0..4 ; pesos 5 3 2 1 4
    Floresta f;
    string erro;
    f.construir({1, 2, 3, 4, 5}, {3, 3, 4, 0, 4}, {5, 3, 2, 1, 4}, &erro);
    BFS bfs;
    CHECA(bfs.deficitBFS(f, f.indiceDe(3)) == 10, "C deve dar 10");
    CHECA(bfs.tamanhoBacia() == 3, "bacia de C tem 3 trechos");
    CHECA(bfs.deficitBFS(f, f.indiceDe(4)) == 15, "D deve dar 15");
    CHECA(bfs.tamanhoBacia() == 5, "bacia de D tem 5 trechos");
    CHECA(bfs.deficitBFS(f, f.indiceDe(1)) == 5, "A deve dar 5");
    CHECA(bfs.tamanhoBacia() == 1, "bacia de A tem 1 trecho");
    CHECA(bfs.deficitBFS(f, f.indiceDe(5)) == 4, "E deve dar 4");
}

static void florestaAleatoria() {
    // 200 mil nos; o no i aponta para um indice menor (ou e raiz) -> nunca ha ciclo
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
    confereRaizes(f, "aleatoria");
}

int main(int argc, char** argv) {
    if (argc > 1) {
        Floresta f;
        string erro;

        if (!f.carregarCSV(argv[1], "", &erro)) { 
            cout << "Erro: " << erro << "\n"; return 1; 
        }

        f.pesosSinteticos(42);
        confereRaizes(f, "real");
    } else {
        arvorePequena();
        florestaAleatoria();
    }

    if (falhas == 0) cout << "TESTE OK\n"; else cout << falhas << " falha(s)\n";
    return falhas == 0 ? 0 : 1;
}