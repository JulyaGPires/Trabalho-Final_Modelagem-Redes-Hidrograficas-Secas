#ifndef BFS_HPP
#define BFS_HPP

#include <vector>
#include <cstdint>
#include <cstddef>
#include "Floresta.hpp"

class BFS {
    public:
        BFS();
        double deficitBFS(const Floresta& floresta, int32_t indice);
        size_t tamanhoBacia() const; // retorna o tamanho da bacia

    private:
        std::vector<int32_t> fila;
};

#endif