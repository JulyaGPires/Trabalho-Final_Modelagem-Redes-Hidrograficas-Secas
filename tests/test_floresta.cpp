#include <chrono>
#include <cstdio>
#include <iostream>
#include "../src/includes/Floresta.hpp"

using namespace std;
using Relogio = chrono::steady_clock;

static int falhas = 0;
#define CHECA(condicao, mensagem) do { \
    if (!(condicao)) { \
        cout << "FALHOU: " << mensagem << "\n"; \
        falhas++; \
    } \
} while (0)

// Testa a topologia de um exemplo pequeno:
//   A(5)   B(3)
//     \     /
//      C(2)   E(4)
//        \     /
//         D(1)  [foz]
// ids: A=1, B=2, C=3, D=4, E=5
static void testeArvorePequena() {
    vector<int64_t> ids   = {1, 2, 3, 4, 5};
    vector<int64_t> next  = {3, 3, 4, 0, 4};
    vector<double>  pesos = {5, 3, 2, 1, 4};

    Floresta floresta;
    string erro;
    CHECA(floresta.construir(ids, next, pesos, &erro), "construir arvore pequena: " + erro);

    CHECA(floresta.n == 5, "quantidade total de vertices n == 5");
    CHECA(floresta.raizes.size() == 1 && floresta.raizes[0] == 3, "unica raiz e D (indice 3)");
    CHECA(floresta.jusante[0] == 2 && floresta.jusante[1] == 2, "A e B desaguam em C");
    CHECA(floresta.jusante[3] == -1, "D e a foz");

    int32_t indiceC = floresta.indiceDe(3);
    CHECA(indiceC == 2, "indiceDe(3) == 2");
    CHECA(floresta.iniFilhos[indiceC + 1] - floresta.iniFilhos[indiceC] == 2, "C possui 2 afluentes");
    CHECA(floresta.indiceDe(99) == -1, "ID inexistente deve retornar -1");
    CHECA(floresta.semCiclos(), "arvore pequena nao deve conter ciclos");
}

// Testa construcao quando os IDs dos trechos vem fora de ordem no vetor
static void testeIdsDesordenados() {
    vector<int64_t> ids   = {4, 1, 5, 3, 2};
    vector<int64_t> next  = {0, 3, 4, 4, 3};
    vector<double>  pesos = {1, 5, 4, 2, 3};

    Floresta floresta;
    string erro;
    CHECA(floresta.construir(ids, next, pesos, &erro), "construir com ids desordenados: " + erro);

    int32_t indiceD = floresta.indiceDe(4);
    int32_t indiceC = floresta.indiceDe(3);
    CHECA(indiceD == 0 && indiceC == 3, "indices corretos com ids desordenados");
    CHECA(floresta.jusante[indiceC] == indiceD, "C desagua em D");
    CHECA(floresta.semCiclos(), "sem ciclos com ids desordenados");
}

// Testa se o algoritmo de Kahn detecta a presenca de um ciclo
static void testeCiclo() {
    // 1 -> 2 -> 3 -> 2 (ciclo entre 2 e 3)
    Floresta floresta;
    string erro;
    CHECA(floresta.construir({1, 2, 3}, {2, 3, 2}, {1, 1, 1}, &erro), "construir grafo com ciclo: " + erro);
    CHECA(!floresta.semCiclos(), "algoritmo de Kahn deve detectar o ciclo");
}

// Testa comportamento quando um trecho aponta para um ID inexistente
static void testeNextInexistente() {
    Floresta floresta;
    string erro;
    CHECA(!floresta.construir({1, 2}, {99, 0}, {1, 1}, &erro), "next_down inexistente deve falhar");
    CHECA(!erro.empty(), "mensagem de erro preenchida");
}

static int testeCSVReal(const string& caminhoCSV) {
    Floresta floresta;
    string erro;

    auto inicioLeitura = Relogio::now();
    if (!floresta.carregarCSV(caminhoCSV, "", &erro)) {
        cout << "Erro ao abrir CSV: " << erro << "\n";
        return 1;
    }
    double tempoLeitura = chrono::duration<double>(Relogio::now() - inicioLeitura).count();

    int32_t maxAfluentes = 0;
    for (int32_t i = 0; i < floresta.n; ++i) {
        int32_t qtdFilhos = floresta.iniFilhos[i + 1] - floresta.iniFilhos[i];
        maxAfluentes = max(maxAfluentes, qtdFilhos);
    }

    auto inicioKahn = Relogio::now();
    bool ok = floresta.semCiclos();
    double tempoKahn = chrono::duration<double>(Relogio::now() - inicioKahn).count();

    double memoriaMB = floresta.memoriaBytes() / (1024.0 * 1024.0);

    printf("Trechos: %d | raizes (fozes): %zu | arestas: %zu\n", floresta.n, floresta.raizes.size(), floresta.filhos.size());
    printf("Maximo de afluentes diretos em um trecho: %d\n", maxAfluentes);
    printf("Leitura + construcao: %.2f s | Kahn: %.2f s | memoria: %.1f MiB\n", tempoLeitura, tempoKahn, memoriaMB);
    printf("Sem ciclos (Kahn removeu todos os trechos): %s\n", ok ? "SIM" : "NAO");

    return ok ? 0 : 1;
}

int main(int argc, char** argv) {
    if (argc > 1) {
        return testeCSVReal(argv[1]);
    }

    testeArvorePequena();
    testeIdsDesordenados();
    testeCiclo();
    testeNextInexistente();

    if (falhas == 0) {
        cout << "TESTE OK\n";
    } else {
        cout << falhas << " falha(s) encontrada(s)\n";
    }

    return (falhas == 0) ? 0 : 1;
}
