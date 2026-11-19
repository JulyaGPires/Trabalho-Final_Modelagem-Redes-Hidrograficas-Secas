#include "Bfs.hpp"

using namespace std;

BFS::BFS(){
    this->fila.clear();
}

double BFS::deficitBFS(const Floresta& floresta, int32_t indice){
    this->fila.clear();          
    size_t proximoFila = 0;  // posicao do proximo trecho a sair da fila
    double soma = 0.0;

    this->fila.push_back(indice);

    while(proximoFila < this->fila.size()){
        int32_t vertice = this->fila[proximoFila];
        proximoFila++;

        soma += floresta.peso[vertice];

        // filhos (afluentes) de 'vertice': floresta.filhos[inicio] ... floresta.filhos[fim-1]
        int32_t inicio = floresta.iniFilhos[vertice];
        int32_t fim = floresta.iniFilhos[vertice + 1];
        for(int32_t k = inicio; k < fim; k++){
            this->fila.push_back(floresta.filhos[k]);
        }
    }

    return soma;
}

// tamanho da bacia
size_t BFS::tamanhoBacia() const {
    return this->fila.size();
}