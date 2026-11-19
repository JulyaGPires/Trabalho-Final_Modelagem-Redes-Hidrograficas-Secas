#ifndef EULERTOUR_HPP
#define EULERTOUR_HPP

#include <vector>
#include <cstdint>
#include <cstddef>
#include "Floresta.hpp"

class EulerTour {
    public:
        EulerTour();
        bool preprocessar(const Floresta& floresta);          
        double deficitEuler(int32_t indice) const;                 
        size_t tamanhoBacia(int32_t indice) const;            

    private:
        std::vector<int32_t> tin; // tin[v]  = posição de v na ordem de visita
        std::vector<int32_t> tout; // tout[v] = posição do último descendente de v
        std::vector<int32_t> ordem; // ordem[p] = vértice que está na posição p
        std::vector<double>  soma; // tamanho n+
};

#endif