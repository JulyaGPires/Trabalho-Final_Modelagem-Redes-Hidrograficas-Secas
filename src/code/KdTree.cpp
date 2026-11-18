#include "KdTree.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <utility>

KdTree::KdTree() : num_comparacoes(0), tempo_construcao(0.0) {}

// Converte latitude e longitude para coordenadas 3D na esfera unitaria
void KdTree::paraXYZ(double lat, double lon, double ponto3D[3]) {
    const double grausParaRadianos = M_PI / 180.0;
    double latRad = lat * grausParaRadianos;
    double lonRad = lon * grausParaRadianos;

    ponto3D[0] = std::cos(latRad) * std::cos(lonRad);
    ponto3D[1] = std::cos(latRad) * std::sin(lonRad);
    ponto3D[2] = std::sin(latRad);
}

// Distancia euclidiana 3D ao quadrado
double KdTree::dist2(const double pontoA[3], const double pontoB[3]) {
    double diferencaX = pontoA[0] - pontoB[0];
    double diferencaY = pontoA[1] - pontoB[1];
    double diferencaZ = pontoA[2] - pontoB[2];

    return (diferencaX * diferencaX) + (diferencaY * diferencaY) + (diferencaZ * diferencaZ);
}

// Converte a corda na esfera unitaria para distancia real na Terra (em km)
double KdTree::corda2ParaKm(double distanciaQuadrada) {
    double corda = std::sqrt(distanciaQuadrada);

    // Evita erro de ponto flutuante passar do diametro maximo
    if (corda > 2.0) {
        corda = 2.0;
    }

    return 2.0 * RAIO_TERRA_KM * std::asin(corda / 2.0);
}

// Carrega os dados e inicia a construcao recursiva
void KdTree::construir(const std::vector<int32_t>& ids, const std::vector<double>& lat, const std::vector<double>& lon) {
    auto tempoInicio = std::chrono::steady_clock::now();

    size_t totalPontos = ids.size();
    pontos.clear();
    pontos.resize(totalPontos);

    for (size_t i = 0; i < totalPontos; ++i) {
        paraXYZ(lat[i], lon[i], pontos[i].coord);
        pontos[i].id = ids[i];
    }

    num_comparacoes = 0;

    if (totalPontos > 0) {
        construirRec(0, static_cast<int>(totalPontos), 0);
    }

    auto tempoFim = std::chrono::steady_clock::now();
    tempo_construcao = std::chrono::duration<double>(tempoFim - tempoInicio).count();
}

// Divide o intervalo no elemento mediano do eixo atual
void KdTree::construirRec(int inicio, int fim, int profundidade) {
    if (fim - inicio <= 1) {
        return;
    }

    int meio = inicio + (fim - inicio) / 2;
    int eixo = profundidade % 3; // 0=X, 1=Y, 2=Z

    // Pega a mediana no eixo atual em tempo linear O(n)
    std::nth_element(pontos.begin() + inicio, pontos.begin() + meio, pontos.begin() + fim, [eixo](const Ponto& pontoA, const Ponto& pontoB) {
            return pontoA.coord[eixo] < pontoB.coord[eixo];
        }
    );

    construirRec(inicio, meio, profundidade + 1);
    construirRec(meio + 1, fim, profundidade + 1);
}

void KdTree::maisProximoRec(int inicio, int fim, int profundidade, const double pontoAlvo[3], int& melhorIndice, double& menorDistanciaQuadrada) {
    if (inicio >= fim) {
        return;
    }

    int meio = inicio + (fim - inicio) / 2;
    int eixo = profundidade % 3;
    const Ponto& pontoAtual = pontos[meio];

    num_comparacoes++;

    double distAtual = dist2(pontoAtual.coord, pontoAlvo);
    if (distAtual < menorDistanciaQuadrada) {
        menorDistanciaQuadrada = distAtual;
        melhorIndice = meio;
    }

    double diferencaEixo = pontoAlvo[eixo] - pontoAtual.coord[eixo];

    // Desce primeiro no lado em que o ponto alvo se encontra
    if (diferencaEixo < 0.0) {
        maisProximoRec(inicio, meio, profundidade + 1, pontoAlvo, melhorIndice, menorDistanciaQuadrada);

        if ((diferencaEixo * diferencaEixo) < menorDistanciaQuadrada) {
            maisProximoRec(meio + 1, fim, profundidade + 1, pontoAlvo, melhorIndice, menorDistanciaQuadrada);
        }
    } else {
        maisProximoRec(meio + 1, fim, profundidade + 1, pontoAlvo, melhorIndice, menorDistanciaQuadrada);

        if ((diferencaEixo * diferencaEixo) < menorDistanciaQuadrada) {
            maisProximoRec(inicio, meio, profundidade + 1, pontoAlvo, melhorIndice, menorDistanciaQuadrada);
        }
    }
}

bool KdTree::buscarMaisProximo(double lat, double lon, Vizinho& resultado) {
    if (pontos.empty()) {
        return false;
    }

    double pontoAlvo[3];
    paraXYZ(lat, lon, pontoAlvo);

    int melhorIndice = -1;
    double menorDistanciaQuadrada = std::numeric_limits<double>::max();

    maisProximoRec(0, static_cast<int>(pontos.size()), 0, pontoAlvo, melhorIndice, menorDistanciaQuadrada);

    resultado.id = pontos[melhorIndice].id;
    resultado.dist_km = corda2ParaKm(menorDistanciaQuadrada);

    return true;
}

// Busca os k vizinhos mantendo um max-heap com os melhores
void KdTree::kVizinhosRec(int inicio, int fim, int profundidade, const double pontoAlvo[3], int k, std::vector<std::pair<double, int>>& heapVizinhos) {
    if (inicio >= fim) {
        return;
    }

    int meio = inicio + (fim - inicio) / 2;
    int eixo = profundidade % 3;
    const Ponto& pontoAtual = pontos[meio];

    num_comparacoes++;

    double distAtual = dist2(pontoAtual.coord, pontoAlvo);

    // Insere se nao completou k, ou substitui o pior se for melhor
    if (static_cast<int>(heapVizinhos.size()) < k) {
        heapVizinhos.push_back({distAtual, meio});
        std::push_heap(heapVizinhos.begin(), heapVizinhos.end());
    } else if (distAtual < heapVizinhos.front().first) {
        std::pop_heap(heapVizinhos.begin(), heapVizinhos.end());
        heapVizinhos.back() = {distAtual, meio};
        std::push_heap(heapVizinhos.begin(), heapVizinhos.end());
    }

    double diferencaEixo = pontoAlvo[eixo] - pontoAtual.coord[eixo];

    int primInicio = inicio, primFim = meio;
    int segInicio = meio + 1, segFim = fim;

    if (diferencaEixo >= 0.0) {
        primInicio = meio + 1;
        primFim = fim;
        segInicio = inicio;
        segFim = meio;
    }

    // Visita primeiro o lado prioritario
    kVizinhosRec(primInicio, primFim, profundidade + 1, pontoAlvo, k, heapVizinhos);

    // Visita o outro lado se ainda faltam vizinhos ou se o corte cruza o raio atual
    if (static_cast<int>(heapVizinhos.size()) < k || (diferencaEixo * diferencaEixo) < heapVizinhos.front().first) {
        kVizinhosRec(segInicio, segFim, profundidade + 1, pontoAlvo, k, heapVizinhos);
    }
}

std::vector<KdTree::Vizinho> KdTree::buscarKVizinhos(double lat, double lon, int k) {
    std::vector<Vizinho> vizinhosMaisProximos;

    if (pontos.empty() || k < 1) {
        return vizinhosMaisProximos;
    }

    double pontoAlvo[3];
    paraXYZ(lat, lon, pontoAlvo);

    std::vector<std::pair<double, int>> heapVizinhos;
    heapVizinhos.reserve(k);

    kVizinhosRec(0, static_cast<int>(pontos.size()), 0, pontoAlvo, k, heapVizinhos);

    // Ordena do mais proximo pro mais longe
    std::sort_heap(heapVizinhos.begin(), heapVizinhos.end());

    vizinhosMaisProximos.reserve(heapVizinhos.size());
    for (const auto& item : heapVizinhos) {
        vizinhosMaisProximos.push_back({pontos[item.second].id, corda2ParaKm(item.first)});
    }

    return vizinhosMaisProximos;
}

bool KdTree::buscarMaisProximoLinear(double lat, double lon, Vizinho& resultado) const {
    if (pontos.empty()) {
        return false;
    }

    double pontoAlvo[3];
    paraXYZ(lat, lon, pontoAlvo);

    int melhorIndice = 0;
    double menorDistanciaQuadrada = dist2(pontos[0].coord, pontoAlvo);

    for (size_t i = 1; i < pontos.size(); ++i) {
        double distAtual = dist2(pontos[i].coord, pontoAlvo);
        if (distAtual < menorDistanciaQuadrada) {
            menorDistanciaQuadrada = distAtual;
            melhorIndice = static_cast<int>(i);
        }
    }

    resultado.id = pontos[melhorIndice].id;
    resultado.dist_km = corda2ParaKm(menorDistanciaQuadrada);

    return true;
}

int KdTree::altura() const {
    if (pontos.empty()) {
        return -1;
    }

    int alturaCalculada = 0;
    size_t tamanhoAtual = pontos.size();

    while (tamanhoAtual > 1) {
        tamanhoAtual /= 2;
        alturaCalculada++;
    }

    return alturaCalculada;
}

long long KdTree::getConsumoMemoriaBytes() const {
    return static_cast<long long>(pontos.capacity()) * sizeof(Ponto);
}
