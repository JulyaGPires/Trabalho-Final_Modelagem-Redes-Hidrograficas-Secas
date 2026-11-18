#ifndef KDTREE_HPP
#define KDTREE_HPP

#include <cstddef>
#include <cstdint>
#include <utility>
#include <vector>

class KdTree {
    public:
        // Ponto 3D na esfera com o id do trecho
        struct Ponto {
            double coord[3];
            int32_t id;
        };

        struct Vizinho {
            int32_t id;
            double dist_km;
        };

        KdTree();

        void construir(const std::vector<int32_t>& ids, const std::vector<double>& lat, const std::vector<double>& lon);
        bool buscarMaisProximo(double lat, double lon, Vizinho& resultado);

        // Busca os k trechos mais proximos ordenados por distancia
        std::vector<Vizinho> buscarKVizinhos(double lat, double lon, int k);

        // Busca linear sequencial para validar nos testes
        bool buscarMaisProximoLinear(double lat, double lon, Vizinho& resultado) const;

        size_t tamanho() const { return pontos.size(); }
        int altura() const;
        long long getNumComparacoes() const { return num_comparacoes; }
        void zerarComparacoes() { num_comparacoes = 0; }
        long long getConsumoMemoriaBytes() const;
        double getTempoConstrucaoSeg() const { return tempo_construcao; }

        // Converte lat/lon para coordenadas 3D (X, Y, Z)
        static void paraXYZ(double lat, double lon, double ponto3D[3]);

    private:
        static constexpr double RAIO_TERRA_KM = 6371.0088;

        std::vector<Ponto> pontos;
        long long num_comparacoes;
        double tempo_construcao;

        void construirRec(int inicio, int fim, int profundidade);

        void maisProximoRec(int inicio, int fim, int profundidade, const double pontoAlvo[3], int& melhorIndice, double& menorDistanciaQuadrada);

        void kVizinhosRec(int inicio, int fim, int profundidade, const double pontoAlvo[3], int k, std::vector<std::pair<double, int>>& heapVizinhos);

        static double dist2(const double pontoA[3], const double pontoB[3]);
        static double corda2ParaKm(double distanciaQuadrada);
};

#endif 
