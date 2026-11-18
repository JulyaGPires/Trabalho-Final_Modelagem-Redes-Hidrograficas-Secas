#include "Floresta.hpp"
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <numeric>
#include <random>
#include <string_view>

using namespace std;

static string paraMinusculo(string texto) {
    for (char& caractere : texto) {
        caractere = static_cast<char>(tolower(static_cast<unsigned char>(caractere)));
    }
    return texto;
}

static void separarPorVirgula(const string& linha, vector<string_view>& campos) {
    campos.clear();
    size_t inicio = 0;
    for (size_t i = 0; i <= linha.size(); ++i) {
        if (i == linha.size() || linha[i] == ',') {
            campos.emplace_back(linha.data() + inicio, i - inicio);
            inicio = i + 1;
        }
    }
}

// Retorna o indice interno a partir do hyriv_id (busca binaria)
int32_t Floresta::indiceDe(int64_t id) const {
    // Se os IDs ja estavam ordenados no arquivo, busca direto no vetor principal
    if (ordem.empty()) {
        auto iterador = lower_bound(ids.begin(), ids.end(), id);
        if (iterador == ids.end() || *iterador != id) {
            return -1;
        }
        return static_cast<int32_t>(iterador - ids.begin());
    }

    // Se precisou ordenar indiretamente, busca pelo vetor de indices
    auto iterador = lower_bound(ordem.begin(), ordem.end(), id, [&](int32_t indice, int64_t valorAlvo) {
                                return ids[indice] < valorAlvo;
                    });
    if (iterador == ordem.end() || ids[*iterador] != id) {
        return -1;
    }
    
    return *iterador;
}

bool Floresta::construir(vector<int64_t> idsEntrada, const vector<int64_t>& nextIds, vector<double> pesos, string* erro) {
    auto registrarErro = [&](const string& mensagem) {
        if (erro) {
            *erro = mensagem;
        }
        return false;
    };

    size_t total = idsEntrada.size();
    if (nextIds.size() != total || pesos.size() != total) {
        return registrarErro("ids, next_down e pesos possuem tamanhos diferentes");
    }

    if (total > static_cast<size_t>(INT32_MAX) - 1) {
        return registrarErro("quantidade de trechos ultrapassa o limite de int32");
    }

    n = static_cast<int32_t>(total);
    ids = move(idsEntrada);
    peso = move(pesos);
    ordem.clear();
    raizes.clear();

    // 1. Mapeamento dos IDs: se não vierem ordenados, cria um vetor de indices ordenados
    if (!is_sorted(ids.begin(), ids.end())) {
        ordem.resize(n);
        iota(ordem.begin(), ordem.end(), 0);
        sort(ordem.begin(), ordem.end(), [&](int32_t a, int32_t b) {
                return ids[a] < ids[b];
             });

        // Checa se existem IDs duplicados
        for (int32_t k = 1; k < n; ++k) {
            if (ids[ordem[k]] == ids[ordem[k - 1]]) {
                return registrarErro("hyriv_id repetido encontrado nos dados");
            }
        }
    } else {
        if (adjacent_find(ids.begin(), ids.end()) != ids.end()) {
            return registrarErro("hyriv_id repetido encontrado nos dados");
        }
    }

    // 2. Mapeia para qual trecho a jusante cada vertice desagua (-1 se for foz)
    jusante.assign(n, -1);
    int64_t trechosSemDestino = 0;

    for (int32_t i = 0; i < n; ++i) {
        if (nextIds[i] == 0) {
            continue; // 0 no HydroRIVERS representa a foz
        }

        int32_t proximo = indiceDe(nextIds[i]);
        if (proximo < 0) {
            trechosSemDestino++;
            continue;
        }
        jusante[i] = proximo;
    }

    if (trechosSemDestino > 0) {
        return registrarErro(to_string(trechosSemDestino) + " trechos possuem next_down inexistente em hyriv_id");
    }

    // 3. Monta a lista de afluentes em formato CSR e identifica as raizes (fozes)
    iniFilhos.assign(static_cast<size_t>(n) + 1, 0);

    // Conta quantos afluentes chegam em cada trecho
    for (int32_t i = 0; i < n; ++i) {
        if (jusante[i] >= 0) {
            iniFilhos[jusante[i] + 1]++;
        } else {
            raizes.push_back(i); // Foz do rio
        }
    }

    // Soma cumulativa para definir as posicoes de inicio no vetor de filhos
    for (int32_t i = 0; i < n; ++i) {
        iniFilhos[i + 1] += iniFilhos[i];
    }

    filhos.assign(iniFilhos[n], 0);
    vector<int32_t> posicoesAtuais(iniFilhos.begin(), iniFilhos.end() - 1);

    // Preenche os afluentes de cada no
    for (int32_t i = 0; i < n; ++i) {
        if (jusante[i] >= 0) {
            int32_t pai = jusante[i];
            filhos[posicoesAtuais[pai]++] = i;
        }
    }

    return true;
}

bool Floresta::carregarCSV(const string& caminhoArquivo, const string& colunaPeso, string* erro) {
    auto registrarErro = [&](const string& mensagem) {
        if (erro) {
            *erro = mensagem;
        }
        return false;
    };

    ifstream arquivo(caminhoArquivo);
    if (!arquivo.is_open()) {
        return registrarErro("nao foi possivel abrir o arquivo: " + caminhoArquivo);
    }

    string primeiraLinha;
    if (!getline(arquivo, primeiraLinha)) {
        return registrarErro("arquivo CSV informado esta vazio");
    }
    if (!primeiraLinha.empty() && primeiraLinha.back() == '\r') {
        primeiraLinha.pop_back();
    }

    vector<string_view> camposCabecalho;
    separarPorVirgula(primeiraLinha, camposCabecalho);

    int colId = -1;
    int colNext = -1;
    int colPeso = -1;
    string alvoPeso = paraMinusculo(colunaPeso);

    for (size_t i = 0; i < camposCabecalho.size(); ++i) {
        string nomeColuna = paraMinusculo(string(camposCabecalho[i]));
        if (nomeColuna == "hyriv_id") {
            colId = static_cast<int>(i);
        } else if (nomeColuna == "next_down") {
            colNext = static_cast<int>(i);
        } else if (!alvoPeso.empty() && nomeColuna == alvoPeso) {
            colPeso = static_cast<int>(i);
        }
    }

    if (colId < 0 || colNext < 0) {
        return registrarErro("colunas hyriv_id e/ou next_down nao foram encontradas no CSV");
    }

    if (!alvoPeso.empty() && colPeso < 0) {
        return registrarErro("coluna de peso '" + colunaPeso + "' nao foi encontrada");
    }

    int maiorColuna = max({colId, colNext, colPeso});

    vector<int64_t> idsLidos;
    vector<int64_t> nextLidos;
    vector<double> pesosLidos;

    string linha;
    vector<string_view> camposLinha;
    size_t numeroLinha = 1;

    while (getline(arquivo, linha)) {
        numeroLinha++;
        if (!linha.empty() && linha.back() == '\r') {
            linha.pop_back();
        }

        if (linha.empty()) {
            continue;
        }

        separarPorVirgula(linha, camposLinha);
        if (static_cast<int>(camposLinha.size()) <= maiorColuna) {
            return registrarErro("linha " + to_string(numeroLinha) + " com colunas faltando");
        }

        idsLidos.push_back(strtoll(camposLinha[colId].data(), nullptr, 10));
        nextLidos.push_back(strtoll(camposLinha[colNext].data(), nullptr, 10));

        double pesoTrecho = 0.0;
        if (colPeso >= 0 && !camposLinha[colPeso].empty()) {
            pesoTrecho = strtod(camposLinha[colPeso].data(), nullptr);
            if (std::isnan(pesoTrecho)) {
                pesoTrecho = 0.0; // Valor invalido ou NaN conta como 0
            }
        }
        pesosLidos.push_back(pesoTrecho);
    }

    return construir(move(idsLidos), nextLidos, move(pesosLidos), erro);
}

// Gera pesos aleatorios inteiros entre 1 e 10 para testes
void Floresta::pesosSinteticos(unsigned semente) {
    mt19937 gerador(semente);
    uniform_int_distribution<int> distPesos(1, 10);

    peso.assign(n, 0.0);
    for (int32_t i = 0; i < n; ++i) {
        peso[i] = static_cast<double>(distPesos(gerador));
    }
}

// Algoritmo de Kahn: processa nascentes ate as fozes. Se visitar todos os nós, não há ciclos.
bool Floresta::semCiclos() const {
    // Grau de entrada = quantidade de afluentes que chegam no trecho
    vector<int32_t> grauEntrada(n);
    for (int32_t i = 0; i < n; ++i) {
        grauEntrada[i] = iniFilhos[i + 1] - iniFilhos[i];
    }

    // Fila começa com as nascentes (grau de entrada zero)
    vector<int32_t> fila;
    fila.reserve(n);
    for (int32_t i = 0; i < n; ++i) {
        if (grauEntrada[i] == 0) {
            fila.push_back(i);
        }
    }

    size_t inicioFila = 0;
    while (inicioFila < fila.size()) {
        int32_t atual = fila[inicioFila++];
        int32_t proximo = jusante[atual];

        if (proximo >= 0) {
            grauEntrada[proximo]--;
            if (grauEntrada[proximo] == 0) {
                fila.push_back(proximo);
            }
        }
    }

    // Se processou todos os vertices, não há ciclos
    return fila.size() == static_cast<size_t>(n);
}

size_t Floresta::memoriaBytes() const {
    return (ids.capacity() * sizeof(int64_t)) +
           (jusante.capacity() * sizeof(int32_t)) +
           (peso.capacity() * sizeof(double)) +
           (iniFilhos.capacity() * sizeof(int32_t)) +
           (filhos.capacity() * sizeof(int32_t)) +
           (raizes.capacity() * sizeof(int32_t)) +
           (ordem.capacity() * sizeof(int32_t));
}
