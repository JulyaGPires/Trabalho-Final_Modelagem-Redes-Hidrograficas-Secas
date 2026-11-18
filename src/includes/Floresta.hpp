#ifndef FLORESTA_HPP
#define FLORESTA_HPP

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

class Floresta {
    public:
        int32_t n = 0; // trechos de rios (vertices)
        std::vector<int64_t> ids;  // hyriv_id original de cada trecho
        std::vector<int32_t> jusante; // Indice do trecho a jusante (rio abaixo), ou -1 se for foz
        std::vector<double> peso; // Deficit hidrico ou peso do trecho

        // Lista de adjacencia compacta (CSR) para guardar os afluentes (filhos) de cada trecho:
        // os afluentes do vertice v estão no intervalo [iniFilhos[v], iniFilhos[v + 1])
        std::vector<int32_t> iniFilhos; // Vetor de deslocamentos (tamanho n + 1)
        std::vector<int32_t> filhos; // Indices dos afluentes
        std::vector<int32_t> raizes; // Vertices que são fozes (onde jusante == -1)

        bool construir(std::vector<int64_t> idsEntrada, const std::vector<int64_t>& nextIds, std::vector<double> pesos, std::string* erro = nullptr);
        bool carregarCSV(const std::string& caminhoArquivo, const std::string& colunaPeso = "", std::string* erro = nullptr);

        void pesosSinteticos(unsigned semente = 42);
        bool semCiclos() const; // Verifica se não há ciclos usando ordenação topológica (algoritmo de Kahn)
        int32_t indiceDe(int64_t id) const; // Retorna o indice interno a partir do hyriv_id, ou -1 se não existir
        size_t memoriaBytes() const;

    private:
        std::vector<int32_t> ordem; // Usado para busca binária caso os IDs não venham ordenados
};

#endif
