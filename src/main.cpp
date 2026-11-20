#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

#include "Bfs.hpp"
#include "EulerTour.hpp"
#include "Floresta.hpp"
#include "KdTree.hpp"

using namespace std;
using Relogio = chrono::steady_clock;

// retorna o tempo decorrido em segundos desde o ponto inicial
static double segundosDesde(Relogio::time_point inicio) {
    return chrono::duration<double>(Relogio::now() - inicio).count();
}

// formata o tempo para uma unidade legivel (ns, us, ms ou s)
static string formatarTempo(double seg) {
    ostringstream os;
    os << fixed << setprecision(2);
    if (seg < 1e-6)      os << seg * 1e9 << " ns";
    else if (seg < 1e-3) os << seg * 1e6 << " us";
    else if (seg < 1.0)  os << seg * 1e3 << " ms";
    else                 os << seg << " s";
    return os.str();
}

static void mostrarUso(const char* programa) {
    cerr << "Uso: " << programa << " <arquivo.csv> [--cenario seca|total|mes|sintetico]\n";
}

// executa a consulta pelo mesmo trecho na BFS e no Euler Tour para comparar tempo e resultado
static void responder(const Floresta& floresta, BFS& bfs, const EulerTour& euler, int32_t indice, double somaTotal) {
    // 1) BFS tradicional: percorre a bacia a montante a partir do vertice
    auto t0 = Relogio::now();
    double deficitBfs = bfs.deficitBFS(floresta, indice);
    double tempoBfs = segundosDesde(t0);
    size_t bacia = bfs.tamanhoBacia();

    // 2) Euler Tour: consulta em O(1) usando somas de prefixo
    const int REPETICOES = 10000;
    double deficitEuler = euler.deficitEuler(indice);
    volatile double acumulador = 0.0;
    double soma = 0.0;
    t0 = Relogio::now();
    for (int r = 0; r < REPETICOES; ++r) {
        soma += euler.deficitEuler(indice);
    }
    double tempoEuler = segundosDesde(t0) / REPETICOES;
    acumulador = soma;  // evita que o compilador otimize e ignore o loop
    (void)acumulador;

    double diferenca = fabs(deficitBfs - deficitEuler);
    // tolerancia para compensar pequenas imprecisoes de ponto flutuante acumuladas nas somas
    double tolerancia = 1e-9 * max({1.0, fabs(deficitBfs), fabs(deficitEuler)}) + 1e-12 * somaTotal;
    bool valoresIguais = (diferenca <= tolerancia);
    size_t baciaEuler = euler.tamanhoBacia(indice);
    bool tamanhosIguais = (bacia == baciaEuler);

    cout << fixed << setprecision(4);
    cout << "  Trecho   : hyriv_id = " << floresta.ids[indice] << " (indice " << indice << ")\n";
    cout << "  Bacia    : " << bacia << " trechos (incluindo o proprio)\n";
    cout << "  BFS         deficit = " << setw(16) << deficitBfs
         << "   tempo = " << formatarTempo(tempoBfs) << "\n";
    cout << "  Euler Tour  deficit = " << setw(16) << deficitEuler
         << "   tempo = " << formatarTempo(tempoEuler) << " (media de " << REPETICOES << " repeticoes)\n";
    if (tempoEuler > 0.0) {
        cout << "  BFS / Euler = " << setprecision(1) << tempoBfs / tempoEuler << "x mais lenta\n";
    }
    cout << "  Resultados coincidem: " << (valoresIguais && tamanhosIguais ? "SIM" : "NAO  <-- verificar!") << "\n";
    if (!valoresIguais || !tamanhosIguais) {
        cout << scientific << setprecision(3)
             << "    diferenca = " << diferenca << " (tolerancia " << tolerancia << ")\n"
             << fixed << "    bacia BFS = " << bacia << " | bacia Euler = " << baciaEuler << "\n";
    }
}

int main(int argc, char** argv) {
    if (argc < 2) {
        mostrarUso(argv[0]);
        return 1;
    }

    // leitura dos argumentos de linha de comando
    string caminho = argv[1];
    string cenario = "seca";
    for (int i = 2; i < argc; ++i) {
        string arg = argv[i];
        if (arg == "--cenario" && i + 1 < argc) {
            cenario = argv[++i];
        } else {
            mostrarUso(argv[0]);
            return 1;
        }
    }

    // mapeia o cenario escolhido para a coluna correspondente no CSV
    string colunaPeso;
    if (cenario == "seca")        colunaPeso = "deficit_seca";
    else if (cenario == "total")  colunaPeso = "deficit_total";
    else if (cenario == "mes")    colunaPeso = "deficit_mes";
    else if (cenario == "sintetico") colunaPeso = "";
    else {
        cerr << "Cenario invalido: " << cenario << "\n";
        mostrarUso(argv[0]);
        return 1;
    }

    // carrega os dados do CSV e constroi a floresta hidrografica
    Floresta floresta;
    string erro;
    auto t0 = Relogio::now();
    if (!floresta.carregarCSV(caminho, colunaPeso, &erro)) {
        cerr << "Erro ao carregar o CSV: " << erro << "\n";
        return 1;
    }
    if (cenario == "sintetico") {
        floresta.pesosSinteticos();
    }
    cout << "Cenario: " << cenario << (colunaPeso.empty() ? " (pesos aleatorios de 1 a 10)" : " (coluna " + colunaPeso + ")") << "\n";
    cout << "Floresta: " << floresta.n << " trechos, " << floresta.raizes.size() << " fozes/raizes ("
         << formatarTempo(segundosDesde(t0)) << ", "
         << floresta.memoriaBytes() / (1024.0 * 1024.0) << " MiB)\n";

    // valida se a rede e aciclica usando ordenacao topologica (algoritmo de Kahn)
    t0 = Relogio::now();
    if (!floresta.semCiclos()) {
        cerr << "Erro: a rede tem ciclos; nao e uma floresta.\n";
        return 1;
    }
    cout << "Sem ciclos (Kahn): OK (" << formatarTempo(segundosDesde(t0)) << ")\n";

    // monta a KD-Tree espacial se o CSV contiver latitude e longitude
    KdTree kd;
    bool temKd = (floresta.lat.size() == static_cast<size_t>(floresta.n) &&
                  floresta.lon.size() == static_cast<size_t>(floresta.n));
    if (temKd) {
        vector<int32_t> indices(floresta.n);
        iota(indices.begin(), indices.end(), 0);
        kd.construir(indices, floresta.lat, floresta.lon);
        // libera a memoria de lat/lon da floresta, ja que a KD-Tree tem sua propria estrutura 3D
        floresta.lat.clear(); floresta.lat.shrink_to_fit();
        floresta.lon.clear(); floresta.lon.shrink_to_fit();
        cout << "KD-Tree: " << kd.tamanho() << " pontos, altura " << kd.altura() << " ("
             << formatarTempo(kd.getTempoConstrucaoSeg()) << ", "
             << kd.getConsumoMemoriaBytes() / (1024.0 * 1024.0) << " MiB)\n";
    } else {
        cout << "KD-Tree: indisponivel (o CSV nao tem as colunas lat e lon). Use apenas 'id'.\n";
    }

    EulerTour euler;
    t0 = Relogio::now();
    if (!euler.preprocessar(floresta)) {
        cerr << "Erro: o Euler Tour nao visitou todos os trechos.\n";
        return 1;
    }
    cout << "Euler Tour: pre-processamento em " << formatarTempo(segundosDesde(t0)) << "\n";

    BFS bfs;

    // soma de todos os pesos da rede para calcular a margem de erro numerico
    double somaTotal = accumulate(floresta.peso.begin(), floresta.peso.end(), 0.0);

    // loop interativo no terminal
    cout << "\nComandos: 'id <hyriv_id>', 'coord <lat> <lon>', 'sair'\n";
    string linha;
    while (true) {
        cout << "\n> " << flush;
        if (!getline(cin, linha)) break;

        replace(linha.begin(), linha.end(), ',', '.');
        istringstream entrada(linha);
        string comando;
        if (!(entrada >> comando)) continue;  // linha em branco

        if (comando == "sair" || comando == "exit" || comando == "q") {
            break;
        } else if (comando == "id") {
            long long id;
            if (!(entrada >> id)) {
                cout << "  Uso: id <hyriv_id>\n";
                continue;
            }
            int32_t indice = floresta.indiceDe(id);
            if (indice < 0) {
                cout << "  hyriv_id " << id << " nao existe na rede.\n";
                continue;
            }
            responder(floresta, bfs, euler, indice, somaTotal);
        } else if (comando == "coord") {
            double lat, lon;
            if (!(entrada >> lat >> lon)) {
                cout << "  Uso: coord <lat> <lon>  (graus; ex.: coord -20.07 -44.57)\n";
                continue;
            }

            // checa se as coordenadas estao em intervalos validos
            if (!isfinite(lat) || !isfinite(lon) || lat < -90.0 || lat > 90.0 || lon < -180.0 || lon > 180.0) {
                cout << "  Coordenada fora do intervalo (lat -90..90, lon -180..180).\n";
                continue;
            }
            if (!temKd) {
                cout << "  Consulta por coordenada indisponivel: o CSV nao tem lat/lon.\n";
                continue;
            }

            // busca o trecho mais proximo na KD-Tree e responde a consulta
            KdTree::Vizinho vizinho;
            auto tk = Relogio::now();
            if (!kd.buscarMaisProximo(lat, lon, vizinho)) {
                cout << "  Nenhum trecho encontrado (rede vazia).\n";
                continue;
            }
            double tempoKd = segundosDesde(tk);
            cout << "  KD-Tree  : trecho mais proximo a " << fixed << setprecision(2) << vizinho.dist_km
                 << " km da coordenada (busca em " << formatarTempo(tempoKd) << ")\n";
            responder(floresta, bfs, euler, vizinho.id, somaTotal);
        } else {
            cout << "  Comando desconhecido. Use: id <hyriv_id> | coord <lat> <lon> | sair\n";
        }
    }

    return 0;
}
