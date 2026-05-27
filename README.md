# Multiplicacao de Matrizes Distribuida

Projeto em Python para comparar quatro formas de multiplicar matrizes:

1. Serial.
2. Paralela local com `ProcessPoolExecutor`.
3. Distribuida com sockets TCP.
4. Distribuida hibrida, usando sockets e processos nos servidores.

## Arquivos

```text
main.py          # parametros principais do experimento
matrix_ops.py    # multiplicacao serial/paralela, divisao e juncao de blocos
distributed.py   # servidores, cliente distribuido e protocolo socket
benchmark.py     # medicao, validacao e execucao dos cenarios
plotting.py      # graficos com pyplot
```

## Instalar

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Rodar

Edite os parametros no topo de `main.py`:

```python
MATRIX_SIZES = [5, 60, 120, 500, 1000]
REPEATS = 2
SERVER_COUNT = 2
SERVER_COUNTS = [1, 2, 3, 4]
LOCAL_PARALLEL_WORKERS = 12
LOCAL_PARALLEL_WORKERS_VALUES = [1, 2, 4, 8, 12]
WORKERS_PER_SERVER = 6
WORKERS_PER_SERVER_VALUES = [1, 2, 4, 6]
DISTRIBUTED_TIMEOUT = 900.0
SHOW_PLOTS = True
```

O programa executa quatro cenarios:

1. `tamanho_matriz`: varia `MATRIX_SIZES` e mantem servidores/workers fixos.
2. `quantidade_servidores`: roda todos os `MATRIX_SIZES` para cada valor de `SERVER_COUNTS`.
3. `workers_locais`: roda todos os `MATRIX_SIZES` para cada valor de `LOCAL_PARALLEL_WORKERS_VALUES`.
4. `workers_por_servidor`: roda todos os `MATRIX_SIZES` para cada valor de `WORKERS_PER_SERVER_VALUES`.

Depois execute:

```bash
.venv/bin/python main.py
```

Os graficos abrem na tela e tambem sao salvos em:

```text
results/plots/
```

Os resultados em CSV sao salvos em:

```text
results/benchmark_results.csv
```
