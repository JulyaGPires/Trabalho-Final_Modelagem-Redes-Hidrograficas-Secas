#include "../src/includes/KdTree.hpp"
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

using namespace std;

static bool carregarCSV(const string& caminhoArquivo, vector<int32_t>& ids, vector<double>& latitudes, vector<double>& longitudes) {
    ifstream arquivo(caminhoArquivo);
    if (!arquivo.is_open()) {
        cerr << "Erro ao abrir CSV: " << caminhoArquivo << "\n";
        return false;
    }

    string primeiraLinha;
    if (!getline(arquivo, primeiraLinha)) {
        return false;
    }

    // Identifica os indices das colunas pelo cabecalho
    vector<string> cabecalho;
    stringstream streamCabecalho(primeiraLinha);
    string nomeColuna;

    while (getline(streamCabecalho, nomeColuna, ',')) {
        for (char& ch : nomeColuna) {
            ch = static_cast<char>(tolower(ch));
        }
        if (!nomeColuna.empty() && nomeColuna.back() == '\r') {
            nomeColuna.pop_back();
        }
        cabecalho.push_back(nomeColuna);
    }

    int colId = -1;
    int colLat = -1;
    int colLon = -1;

    for (size_t i = 0; i < cabecalho.size(); ++i) {
        if (cabecalho[i] == "hyriv_id") colId = static_cast<int>(i);
        else if (cabecalho[i] == "lat") colLat = static_cast<int>(i);
        else if (cabecalho[i] == "lon") colLon = static_cast<int>(i);
    }

    if (colId < 0 || colLat < 0 || colLon < 0) {
        cerr << "Colunas obrigatorias (hyriv_id, lat, lon) nao encontradas\n";
        return false;
    }

    int maiorIndiceNecessario = max(colId, max(colLat, colLon));
    string linha;

    while (getline(arquivo, linha)) {
        if (linha.empty()) {
            continue;
        }

        vector<string> camposLinha;
        camposLinha.reserve(maiorIndiceNecessario + 1);

        size_t inicioPos = 0;
        for (int c = 0; c <= maiorIndiceNecessario; ++c) {
            size_t virgulaPos = linha.find(',', inicioPos);

            if (virgulaPos == string::npos) {
                camposLinha.push_back(linha.substr(inicioPos));
                break;
            }

            camposLinha.push_back(linha.substr(inicioPos, virgulaPos - inicioPos));
            inicioPos = virgulaPos + 1;
        }

        if (static_cast<int>(camposLinha.size()) <= maiorIndiceNecessario) {
            continue;
        }

        ids.push_back(stoi(camposLinha[colId]));
        latitudes.push_back(stod(camposLinha[colLat]));
        longitudes.push_back(stod(camposLinha[colLon]));
    }

    return true;
}

using PontoConsulta = pair<double, double>;

// Executa um lote de consultas comparando KD-Tree com busca linear
static int rodarCenario(KdTree& arvore, const string& nomeCenario, const vector<PontoConsulta>& consultas) {
    int totalDivergencias = 0;
    double tempoTotalKdTree = 0.0;
    double tempoTotalLinear = 0.0;

    arvore.zerarComparacoes();

    for (const auto& ponto : consultas) {
        double latConsulta = ponto.first;
        double lonConsulta = ponto.second;

        KdTree::Vizinho vizinhoKd{};
        KdTree::Vizinho vizinhoLinear{};

        auto inicioKd = chrono::steady_clock::now();
        arvore.buscarMaisProximo(latConsulta, lonConsulta, vizinhoKd);
        auto fimKd = chrono::steady_clock::now();

        auto inicioLinear = chrono::steady_clock::now();
        arvore.buscarMaisProximoLinear(latConsulta, lonConsulta, vizinhoLinear);
        auto fimLinear = chrono::steady_clock::now();

        tempoTotalKdTree += chrono::duration<double>(fimKd - inicioKd).count();
        tempoTotalLinear += chrono::duration<double>(fimLinear - inicioLinear).count();

        // O resultado precisa bater no id ou na distancia em caso de empate
        bool mesmoId = (vizinhoKd.id == vizinhoLinear.id);
        bool mesmaDistancia = (fabs(vizinhoKd.dist_km - vizinhoLinear.dist_km) <= 1e-9);

        if (!mesmoId && !mesmaDistancia) {
            totalDivergencias++;
            if (totalDivergencias <= 5) {
                cerr << "Divergencia em (" << latConsulta << ", " << lonConsulta << ")\n";
            }
        }
    }

    double totalConsultas = static_cast<double>(consultas.size());
    double tempoMedioKd_us = (tempoTotalKdTree / totalConsultas) * 1e6;
    double tempoMedioLin_us = (tempoTotalLinear / totalConsultas) * 1e6;
    double mediaNosVisitados = static_cast<double>(arvore.getNumComparacoes()) / totalConsultas;
    double ganhoDesempenho = (tempoTotalKdTree > 0.0) ? (tempoTotalLinear / tempoTotalKdTree) : 0.0;

    cout << "\n[1-NN | " << nomeCenario << "] consultas: " << consultas.size()
         << " | divergencias: " << totalDivergencias << "\n";
    cout << "  KD-Tree: " << tempoMedioKd_us << " us/consulta (media "
         << mediaNosVisitados << " nos visitados)\n";
    cout << "  Linear : " << tempoMedioLin_us << " us/consulta"
         << " | ganho: " << ganhoDesempenho << "x\n";

    return totalDivergencias;
}

int main(int argc, char** argv) {
    vector<int32_t> ids;
    vector<double> latitudes;
    vector<double> longitudes;

    mt19937_64 geradorAleatorio(42);

    int numConsultas = (argc > 2) ? atoi(argv[2]) : 10000;
    if (numConsultas < 1000) {
        numConsultas = 1000;
    }

    if (argc > 1) {
        if (!carregarCSV(argv[1], ids, latitudes, longitudes)) {
            return 1;
        }
    } else {
        uniform_real_distribution<double> distEixoZ(-1.0, 1.0);
        uniform_real_distribution<double> distLongitude(-180.0, 180.0);

        const int totalPontosSinteticos = 200000;
        ids.reserve(totalPontosSinteticos);
        latitudes.reserve(totalPontosSinteticos);
        longitudes.reserve(totalPontosSinteticos);

        for (int i = 0; i < totalPontosSinteticos; ++i) {
            ids.push_back(i + 1);
            latitudes.push_back(asin(distEixoZ(geradorAleatorio)) * 180.0 / M_PI);
            longitudes.push_back(distLongitude(geradorAleatorio));
        }
    }

    cout << "Pontos: " << ids.size() << "\n";

    KdTree arvore;
    arvore.construir(ids, latitudes, longitudes);

    double memoriaMB = arvore.getConsumoMemoriaBytes() / (1024.0 * 1024.0);
    cout << "Construcao: " << arvore.getTempoConstrucaoSeg() << " s | altura: " << arvore.altura()
         << " | memoria: " << memoriaMB << " MB\n";

    // Cenario A: consultas perto de rios existentes com pequeno ruido
    vector<PontoConsulta> consultasPertoDeRios;
    consultasPertoDeRios.reserve(numConsultas);

    uniform_int_distribution<size_t> indiceAleatorio(0, ids.size() - 1);
    normal_distribution<double> ruidoGaussiano(0.0, 0.1);

    for (int i = 0; i < numConsultas; ++i) {
        size_t indiceSorteado = indiceAleatorio(geradorAleatorio);

        double latSorteada = latitudes[indiceSorteado] + ruidoGaussiano(geradorAleatorio);
        double lonSorteada = longitudes[indiceSorteado] + ruidoGaussiano(geradorAleatorio);

        latSorteada = max(-90.0, min(90.0, latSorteada));

        if (lonSorteada > 180.0)  lonSorteada -= 360.0;
        if (lonSorteada < -180.0) lonSorteada += 360.0;

        consultasPertoDeRios.push_back({latSorteada, lonSorteada});
    }

    // Cenario B: consultas espalhadas pelo globo e casos de borda
    vector<PontoConsulta> consultasGlobo;
    consultasGlobo.reserve(numConsultas + 6);

    uniform_real_distribution<double> distEixoZGlobo(-1.0, 1.0);
    uniform_real_distribution<double> distLonGlobo(-180.0, 180.0);

    for (int i = 0; i < numConsultas; ++i) {
        double latUniforme = asin(distEixoZGlobo(geradorAleatorio)) * 180.0 / M_PI;
        double lonUniforme = distLonGlobo(geradorAleatorio);
        consultasGlobo.push_back({latUniforme, lonUniforme});
    }

    consultasGlobo.push_back({0.0, 180.0});  // Linha de mudanca de data (leste)
    consultasGlobo.push_back({0.0, -180.0}); // Linha de mudanca de data (oeste)
    consultasGlobo.push_back({90.0, 0.0}); // Polo Norte
    consultasGlobo.push_back({-90.0, 0.0}); // Polo Sul
    consultasGlobo.push_back({-19.9167, -43.9345}); // Belo Horizonte
    consultasGlobo.push_back({-20.0753, -44.5769}); // Itauna

    int totalErros = rodarCenario(arvore, "perto de rios", consultasPertoDeRios);
    totalErros += rodarCenario(arvore, "globo uniforme", consultasGlobo);

    // Cenario C: busca por 5 vizinhos mais proximos
    int divergenciasK = 0;
    const int numTestesK = 1000;

    for (int i = 0; i < numTestesK; ++i) {
        double latTeste = consultasPertoDeRios[i].first;
        double lonTeste = consultasPertoDeRios[i].second;

        auto cincoVizinhos = arvore.buscarKVizinhos(latTeste, lonTeste, 5);

        KdTree::Vizinho vizinhoUnico{};
        arvore.buscarMaisProximo(latTeste, lonTeste, vizinhoUnico);

        bool primeiroConfere = !cincoVizinhos.empty() && (fabs(cincoVizinhos[0].dist_km - vizinhoUnico.dist_km) <= 1e-9);

        bool ordenacaoValida = true;
        for (size_t j = 1; j < cincoVizinhos.size(); ++j) {
            if (cincoVizinhos[j].dist_km < cincoVizinhos[j - 1].dist_km) {
                ordenacaoValida = false;
                break;
            }
        }

        if (!primeiroConfere || !ordenacaoValida) {
            divergenciasK++;
        }
    }

    cout << "\n[k=5] divergencias em 1000 consultas: " << divergenciasK << "\n";

    bool todosTestesPassaram = (totalErros == 0 && divergenciasK == 0);
    cout << (todosTestesPassaram ? "TESTE OK\n" : "TESTE FALHOU\n");

    return todosTestesPassaram ? 0 : 1;
}
