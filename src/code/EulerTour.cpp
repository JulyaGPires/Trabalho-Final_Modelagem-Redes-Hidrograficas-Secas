#include "EulerTour.hpp"

using namespace std;

EulerTour::EulerTour(){}

bool EulerTour::preprocessar(const Floresta& floresta){
    this->tin.assign(floresta.n, 0);
    this->tout.assign(floresta.n, 0);
    this->ordem.assign(floresta.n, 0);
    this->soma.assign(floresta.n + 1, 0.0);
    vector<int32_t> tamanho;
    tamanho.assign(floresta.n, 1);

    int32_t contarPosicoes = 0;
    vector<int32_t> pilha;

    for(auto raiz: floresta.raizes){
        pilha.push_back(raiz);

        while(!pilha.empty()){
            int32_t v = pilha.back(); 
            pilha.pop_back();
            this->tin[v] = contarPosicoes;
            this->ordem[contarPosicoes] = v;
            contarPosicoes++;

            // adiciona os filhos na pilha
            int32_t inicio = floresta.iniFilhos[v];
            int32_t fim = floresta.iniFilhos[v + 1];
            for(int32_t k = inicio; k < fim; k++){
                pilha.push_back(floresta.filhos[k]);
            }
        }
    }

    // confere se todos os nós foram visitados
    if(contarPosicoes != floresta.n){
        return false;
    }

    for(int32_t p=floresta.n - 1;p>0;p--){
        int32_t v = this->ordem[p];
        if(floresta.jusante[v] >= 0){
            tamanho[floresta.jusante[v]] += tamanho[v];
        }
    }

    for(int32_t t=0;t<floresta.n;t++){
        this->tout[t] = this->tin[t] + tamanho[t] - 1;
    }

    for(int32_t s=0;s<floresta.n;s++){
        this->soma[s+1] = this->soma[s] + floresta.peso[this->ordem[s]];
    }

    return true;
}    

// déficit acumulado da bacia de um trecho
double EulerTour::deficitEuler(int32_t indice) const{
    return this->soma[this->tout[indice] + 1] - this->soma[tin[indice]];
} 

size_t EulerTour::tamanhoBacia(int32_t indice) const{
    return this->tout[indice] - this->tin[indice] + 1;
}