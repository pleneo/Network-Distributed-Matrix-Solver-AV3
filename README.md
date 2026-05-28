# Multiplicação de Matrizes Distribuída

Sistema em Python que implementa e compara quatro estratégias de multiplicação de matrizes — serial, paralela local, distribuída serial e distribuída híbrida — medindo tempo, *speedup* e eficiência em cenários de *benchmark* controlados.

Desenvolvido como atividade prática da disciplina de **Computação Paralela e Concorrente** (UNIFOR, 2026), seguindo a Metodologia de Foster (PCAM).

---

## O que o sistema faz

1. **Gera** pares de matrizes aleatórias com semente fixa (reprodutibilidade garantida).
2. **Multiplica** cada par pelos quatro modos e mede o tempo de cada um.
3. **Valida** que todos os resultados distribuídos são idênticos ao resultado serial.
4. **Salva** as medições em CSV e gera 12 gráficos PNG automaticamente.

### Os quatro modos de execução

| Modo | Descrição |
|------|-----------|
| **Serial** | Multiplicação clássica em um único processo. Linha de base. |
| **Paralelo local** | Divide as linhas de A entre N processos locais via `ProcessPoolExecutor`. Sem sockets. |
| **Distribuído serial** | Envia blocos de linhas para K servidores via TCP. Cada servidor calcula seu bloco de forma serial. |
| **Distribuído híbrido** | Igual ao distribuído serial, mas cada servidor usa internamente `ProcessPoolExecutor` com W processos. |

---

## Arquitetura

```
Cliente (main.py / benchmark.py)
│
├── Gera matrizes A e B
├── Divide A em K blocos de linhas (split_rows)
├── Envia cada bloco + B para um servidor via socket TCP (ThreadPoolExecutor)
│
└── Servidores (distributed.py — processos independentes)
    ├── Recebem bloco + B via protocolo JSON com prefixo de 8 bytes
    ├── Calculam C_parcial = bloco × B (serial ou ProcessPoolExecutor)
    └── Devolvem o resultado ao cliente

Cliente reassembla os blocos (combine_blocks) → matriz C completa
```

O protocolo TCP usa um **cabeçalho de 8 bytes** (*big-endian unsigned long long*) com o tamanho do *payload* JSON antes de cada mensagem, evitando problemas de fragmentação de pacotes.

---

## Estrutura do projeto

```
AV3/
├── main.py              # Parâmetros configuráveis; ponto de entrada
├── matrix_ops.py        # Operações matriciais puras (sem I/O ou rede)
├── distributed.py       # Protocolo TCP, servidores e cliente distribuído
├── benchmark.py         # Orquestração, medição, validação e CSV
├── plotting.py          # Geração dos 12 gráficos PNG
├── requirements.txt     # matplotlib, pytest
├── tests/
│   ├── test_matrix_ops.py    # Testes de corretude das operações matriciais
│   └── test_distributed.py   # Testes do sistema distribuído completo
└── results/
    ├── benchmark_results.csv # Medições (936 linhas com parâmetros padrão)
    └── plots/                # 12 gráficos PNG gerados automaticamente
```

---

## Pré-requisitos

- Python **3.10** ou superior
- Acesso à internet na primeira execução (para baixar o `matplotlib`)

---

## Instalação

```bash
# 1. Entre na pasta do projeto
cd AV3

# 2. Crie o ambiente virtual
python -m venv .venv

# 3. Ative o ambiente
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\Activate.ps1      # Windows (PowerShell)

# 4. Instale as dependências
pip install -r requirements.txt
```

---

## Executar os testes

Antes de rodar o benchmark, verifique que tudo está correto:

```bash
python -m pytest tests/ -v
```

Saída esperada: **6 passed**.

Os testes verificam:
- Multiplicação serial com resultado conhecido (3×3 manual)
- Paralelo produz o mesmo resultado que serial
- `split_rows` e `combine_blocks` são operações inversas
- Modo distribuído serial e híbrido produzem resultados corretos

---

## Executar o benchmark

```bash
python main.py
```

Antes dos benchmarks, o programa exibe uma **demonstração** com as matrizes 3×3 do enunciado:

```
A =
    1    0   -1
    4   -1    2
   -1    2    4

B =
   -1    2   -3
    5   -4    2
    4    1    0

C = A x B =
   -5    1   -3
   -1   14  -14
   27   -6    7
```

A execução completa com os parâmetros padrão leva **20–40 minutos** dependendo do hardware.

---

## Configuração dos parâmetros

Edite o topo de `main.py` para ajustar os experimentos:

```python
MATRIX_SIZES = [1, 5, 60, 120, 250, 500, 750]  # tamanhos para o cenário 1
CONTROL_MATRIX_SIZES = [250, 500]               # tamanhos para o cenário 2
WORKER_MATRIX_SIZES = [1, 5, 60, 120, 250, 500, 750]  # cenários 3 e 4

REPEATS = 3          # repetições por combinação (a média é usada nos gráficos)
SEED = 42            # semente base para geração das matrizes

SERVER_COUNT = 2                      # servidores padrão
SERVER_COUNTS = [1, 2, 3, 4]         # valores do cenário 2

LOCAL_PARALLEL_WORKERS = 12           # workers locais padrão
LOCAL_PARALLEL_WORKERS_VALUES = [1, 2, 4, 8, 12]  # valores do cenário 3

TOTAL_SERVER_WORKERS = 12             # total de workers no híbrido (cenário 2)
WORKERS_PER_SERVER = 6                # workers por servidor padrão
WORKERS_PER_SERVER_VALUES = [1, 2, 4, 6]  # valores do cenário 4

DISTRIBUTED_TIMEOUT = 1000.0          # timeout em segundos para operações TCP
```

> **Isonomia:** a semente efetiva de cada execução é `SEED + repeat + size`, garantindo que todos os quatro modos operem sobre exatamente as mesmas matrizes em cada combinação de tamanho e repetição.

---

## Cenários de benchmark

| # | Cenário | Parâmetro variado | Tamanhos usados |
|---|---------|-------------------|-----------------|
| 1 | `tamanho_matriz` | N ∈ {1, 5, 60, 120, 250, 500, 750} | todos |
| 2 | `quantidade_servidores` | servidores ∈ {1, 2, 3, 4} | {250, 500} |
| 3 | `workers_locais` | workers locais ∈ {1, 2, 4, 8, 12} | todos |
| 4 | `workers_por_servidor` | workers/servidor ∈ {1, 2, 4, 6} | todos |

No cenário 2, `workers_por_servidor = TOTAL_SERVER_WORKERS // servidores` — o total de processos no modo híbrido permanece fixo em 12, isolando o efeito da distribuição.

---

## Resultados gerados

### CSV

`results/benchmark_results.csv` — uma linha por medição, com colunas:

| Coluna | Descrição |
|--------|-----------|
| `scenario` | Nome do cenário |
| `repeat` | Número da repetição |
| `varied_parameter` / `varied_value` | Parâmetro e valor variados |
| `mode` | `serial`, `parallel`, `distributed`, `hybrid` |
| `size` | Ordem N da matriz |
| `time` | Tempo de execução (s) |
| `speedup` | `tempo_serial / tempo_modo` |
| `efficiency` | `speedup / unidades_paralelas` |
| `servers`, `local_workers`, `workers_per_server` | Configuração usada |
| `valid` | `True` se o resultado bate com o serial |

### Gráficos (12 PNG em `results/plots/`)

| Cenário | Gráficos gerados |
|---------|-----------------|
| `tamanho_matriz` | tempo, *speedup* e eficiência × tamanho N |
| `quantidade_servidores` | tempo, *speedup* e eficiência × nº de servidores |
| `workers_locais` | tempo, *speedup* e eficiência × workers locais |
| `workers_por_servidor` | tempo, *speedup* e eficiência × workers/servidor |

Os cenários 3 e 4 compartilham escala vertical nos gráficos para permitir comparação direta.

---

## Principais resultados (parâmetros padrão)

- Para N ≤ 60, o *overhead* de processos e TCP **supera** o ganho de paralelismo.
- Para N ≥ 250, o paralelo local e o híbrido atingem **speedup entre 4,6× e 6,2×**.
- O distribuído serial mantém **eficiência ~0,96** (2 servidores) porque cada servidor aproveita bem sua capacidade.
- Aumentar workers além de 4–8 apresenta **rendimentos decrescentes**, conforme previsto pela Lei de Amdahl.

---
