# Codexion — Explicação Completa do Projeto (Português)

> Guia técnico para entender, explicar e defender o projeto a 100%.

---

## Índice

1. [O que é o projeto?](#1-o-que-é-o-projeto)
2. [Analogia com o Problema dos Filósofos](#2-analogia-com-o-problema-dos-filósofos)
3. [Estrutura de Ficheiros](#3-estrutura-de-ficheiros)
4. [Tipos de Dados (structs e enums)](#4-tipos-de-dados-structs-e-enums)
5. [Fluxo de Execução — Passo a Passo](#5-fluxo-de-execução--passo-a-passo)
6. [Análise Ficheiro a Ficheiro](#6-análise-ficheiro-a-ficheiro)
7. [Fila de Prioridade (min-heap)](#7-fila-de-prioridade-min-heap)
8. [Problemas de Concorrência e Soluções](#8-problemas-de-concorrência-e-soluções)
9. [Os dois schedulers: FIFO vs EDF](#9-os-dois-schedulers-fifo-vs-edf)
10. [O dongle_cooldown](#10-o-dongle_cooldown)
11. [A thread monitor](#11-a-thread-monitor)
12. [Primitivas POSIX usadas](#12-primitivas-posix-usadas)
13. [Sequência de Memória e Limpeza](#13-sequência-de-memória-e-limpeza)
14. [Casos de Teste Importantes](#14-casos-de-teste-importantes)
15. [Perguntas Frequentes na Avaliação](#15-perguntas-frequentes-na-avaliação)

---

## 1. O que é o projeto?

O **Codexion** é uma simulação de programação concorrente em C. Modela um grupo de programadores (*coders*) a partilhar dongles USB num espaço de trabalho circular.

**Regras do mundo simulado:**
- Cada coder precisa de **dois dongles** em simultâneo para compilar o seu código quântico.
- Os dongles estão dispostos entre pares adjacentes de coders (tal como garfos nos Filósofos).
- Após largar os dongles, o coder faz debug e depois refactoriza, e repete.
- Se um coder não começar a compilar dentro de `time_to_burnout` milissegundos, ele faz **burnout** e a simulação para.
- A simulação termina com sucesso quando todos os coders atingem `number_of_compiles_required` compilações.

---

## 2. Analogia com o Problema dos Filósofos

| Problema dos Filósofos | Codexion |
|---|---|
| Filósofo | Coder (thread) |
| Garfo | Dongle (USB) |
| Comer | Compilar (requer 2 dongles) |
| Pensar | Debug + Refactorizar |
| Morrer de fome | Burnout |

A diferença principal é que o Codexion adiciona:
- **Cooldown por dongle**: após ser largar, um dongle fica indisponível durante `dongle_cooldown` ms.
- **Scheduler configurável**: FIFO (ordem de chegada) ou EDF (prazo mais curto primeiro).
- **Fila de prioridade por dongle**: em vez de mutex simples, há um heap mínimo de waiters.
- **Thread monitor dedicada**: detecta burnout com precisão de 10ms.

---

## 3. Estrutura de Ficheiros

```
codexion/
├── codexion.h          ← Header único: todos os tipos e protótipos
├── main.c              ← Ponto de entrada: parse → init → run → cleanup
├── args.c              ← Validação e parsing dos 8 argumentos
├── args_validate.c     ← Validação de limites (MIN/MAX por campo)
├── sim.c               ← sim_run(), sim_cleanup(), broadcast_all()
├── sim_init.c          ← Alocação de memória e inicialização de structs
├── sim_stats.c         ← Impressão de estatísticas no stderr após fim
├── coder.c             ← Thread de cada coder, lógica de aquisição de dongles
├── coder_actions.c     ← do_debug() e do_refactor()
├── dongle.c            ← dongle_init/destroy/acquire/release
├── dongle_utils.c      ← wait_one_ms(), is_my_turn(), try_acquire()
├── pqueue.c            ← Implementação do heap (init, push, pop, peek, remove)
├── pqueue_utils.c      ← comes_before(), sift_up(), sift_down()
├── monitor.c           ← Thread monitor: detecta burnout e conclusão
├── log.c               ← log_state(): impressão thread-safe no stdout
├── time_utils.c        ← get_time_ms() e sleep_ms()
└── Makefile
```

---

## 4. Tipos de Dados (structs e enums)

### `t_sim` — Estado global da simulação

```c
struct s_sim {
    int             n_coders;           // número de coders (e dongles)
    long long       time_to_burnout;    // ms antes de burnout
    long long       time_to_compile;    // ms a compilar (segurando 2 dongles)
    long long       time_to_debug;      // ms a debugar
    long long       time_to_refactor;   // ms a refactorizar
    int             n_compiles_required;// compiles necessários para terminar
    long long       dongle_cooldown;    // ms de cooldown após largar dongle
    t_scheduler     scheduler;          // FIFO ou EDF

    t_coder        *coders;             // array de coders (alocado em heap)
    t_dongle       *dongles;            // array de dongles (alocado em heap)
    pthread_t       monitor_thread;     // thread do monitor

    pthread_mutex_t stop_mutex;         // protege o campo 'stopped'
    int             stopped;            // flag de paragem (0=a correr, 1=parado)
    int             burnout_coder_id;   // ID do coder que fez burnout (0=nenhum)

    pthread_mutex_t log_mutex;          // serializa todas as impressões
    pthread_mutex_t dongle_order_mutex; // protege a ordem de aquisição
    long long       start_time_ms;      // timestamp de início (epoch ms)
    long long       end_time_ms;        // timestamp de fim
};
```

### `t_coder` — Estado de cada thread

```c
struct s_coder {
    int         id;                 // 1..n_coders
    int         left_dongle;        // índice do dongle à esquerda (= id-1)
    int         right_dongle;       // índice do dongle à direita (= id % n)
    int         compile_count;      // número de compilações feitas
    t_state     state;              // WAITING/COMPILING/DEBUGGING/REFACTORING
    long long   last_compile_start; // quando começou o último compile
    long long   deadline;           // last_compile_start + time_to_burnout
    pthread_t   thread;             // identificador da thread POSIX
    t_sim      *sim;                // ponteiro para o estado global
};
```

### `t_dongle` — Estado de cada dongle

```c
struct s_dongle {
    pthread_mutex_t mutex;          // protege todos os campos abaixo
    pthread_cond_t  cond;           // para acordar waiters
    int             in_use;         // 1 = alguém está a usá-lo
    int             in_cooldown;    // 1 = em cooldown (não disponível)
    long long       release_time;   // quando foi libertado
    t_pqueue        waiters;        // fila de prioridade dos coders à espera
    t_sim          *sim;            // acesso às configs globais
};
```

### `t_pqueue` e `t_pq_node` — Heap mínimo

```c
struct s_pq_node {
    long long   key;        // FIFO: timestamp de chegada | EDF: deadline
    int         coder_id;   // quem está à espera
};

struct s_pqueue {
    t_pq_node  *nodes;      // array do heap
    int         size;       // elementos activos
    int         capacity;   // capacidade alocada
};
```

### Enums

```c
typedef enum e_scheduler { SCHED_FIFO_MODE, SCHED_EDF_MODE } t_scheduler;
typedef enum e_state { STATE_WAITING, STATE_COMPILING, STATE_DEBUGGING,
                       STATE_REFACTORING, STATE_BURNED_OUT } t_state;
typedef enum e_limits { MAX_CODERS=200, MIN_TIME_MS=1, MAX_TIME_MS=100000,
                        MAX_COMPILES=10000, CODER_START_OFFSET=5 } t_limits;
```

`CODER_START_OFFSET = 5`: cada coder espera `(id-1)*5 ms` antes de começar, para evitar que todos tentem os dongles exactamente ao mesmo tempo na inicialização.

---

## 5. Fluxo de Execução — Passo a Passo

```
main()
│
├─ parse_args()          ← valida os 8 argumentos, preenche t_sim
│
├─ sim_init()
│   ├─ init_mutexes()    ← cria stop_mutex, log_mutex, dongle_order_mutex
│   ├─ alloc_sim()       ← malloc para array de coders e dongles
│   ├─ init_dongles()    ← por cada dongle: mutex + cond + pq_init
│   └─ init_coders()     ← atribui id, left/right dongle, deadline inicial
│
├─ sim_run()
│   ├─ pthread_create(monitor_thread)   ← thread monitor começa
│   ├─ pthread_create(coder_thread x N) ← N threads de coder começam
│   ├─ pthread_join(coder_thread x N)   ← espera que todos terminem
│   ├─ set stopped=1                    ← sinaliza o monitor para parar
│   ├─ broadcast_all()                  ← acorda qualquer thread ainda bloqueada
│   └─ pthread_join(monitor_thread)     ← espera que o monitor termine
│
├─ sim_print_stats()    ← imprime estatísticas no stderr
│
└─ sim_cleanup()        ← destroi mutexes, cond vars, liberta memória
```

### Ciclo de vida de um coder

```
coder_routine()
│
└─ loop enquanto !sim_is_stopped()
    ├─ STATE_WAITING
    ├─ do_compile()
    │   ├─ get_dongle_order() → determina qual adquirir primeiro (menor índice)
    │   ├─ dongle_acquire(first) → bloqueia até conseguir
    │   ├─ dongle_acquire(second) → bloqueia até conseguir
    │   ├─ loga "has taken a dongle" x2
    │   ├─ actualiza last_compile_start e deadline
    │   ├─ loga "is compiling"
    │   ├─ sleep_ms(time_to_compile)
    │   ├─ compile_count++
    │   ├─ dongle_release(second)
    │   └─ dongle_release(first)
    ├─ do_debug()
    │   ├─ loga "is debugging"
    │   └─ sleep_ms(time_to_debug)
    └─ do_refactor()
        ├─ loga "is refactoring"
        └─ sleep_ms(time_to_refactor)
```

---

## 6. Análise Ficheiro a Ficheiro

### `main.c`
Ponto de entrada. Declara `t_sim sim` na stack (memset a zero). Chama `parse_args`, depois `sim_init`, `sim_run`, `sim_print_stats` e `sim_cleanup`. Retorna 1 em caso de erro, 0 em sucesso.

---

### `args.c` + `args_validate.c`

**`is_positive_int()`**: verifica que cada caracter é '0'-'9'. Rejeita negativos (por terem '-'), strings vazias, e não-inteiros.

**`validate_nums()`**: aplica `is_positive_int` aos argumentos 1..7.

**`set_scheduler()`**: compara com `"fifo"` ou `"edf"` via `strcmp`.

**`fill_sim()`**: converte strings para números com `atoi` e preenche os campos de `t_sim`.

**`validate_limits()`** (em `args_validate.c`): verifica que:
- `n_coders` ∈ [1, 200]
- Todos os tempos ∈ [1, 100000] ms
- `time_to_compile < time_to_burnout` ← **crítico**: o compile tem de ser possível antes do burnout
- `n_compiles_required` ∈ [1, 10000]
- `dongle_cooldown` ∈ [0, 100000] ms (pode ser 0)

---

### `time_utils.c`

**`get_time_ms()`**: usa `gettimeofday()` para obter o tempo epoch em microssegundos, e converte para milissegundos:
```c
return (long long)tv.tv_sec * 1000LL + (long long)tv.tv_usec / 1000LL;
```

**`sleep_ms(ms)`**: chama `usleep(ms * 1000)` (converte ms para µs).

---

### `log.c`

```c
void log_state(t_sim *sim, int coder_id, const char *msg)
{
    pthread_mutex_lock(&sim->log_mutex);
    elapsed = get_time_ms() - sim->start_time_ms;
    printf("%lld %d %s\n", elapsed, coder_id, msg);
    pthread_mutex_unlock(&sim->log_mutex);
}
```

O `log_mutex` garante que dois `printf` de threads diferentes nunca se intercalam na mesma linha. Todo o output vai para **stdout**; as estatísticas finais vão para **stderr**.

---

### `pqueue.c` e `pqueue_utils.c`

Implementação manual de **min-heap** (nenhuma biblioteca STL permitida pelo subject).

**`comes_before(a, b)`**:
```c
if (a->key < b->key) return 1;
if (a->key == b->key && a->coder_id > b->coder_id) return 1;
return 0;
```
- Para FIFO: `key = timestamp` → quem chegou mais cedo tem menor key → sai primeiro.
- Para EDF: `key = deadline` → quem tem deadline mais próxima tem menor key → sai primeiro.
- **Tie-breaker**: `coder_id > b->coder_id` → em empate, o coder com **maior** id "vem antes" no heap (ou seja, o coder com menor id fica para depois). Isto garante determinismo nos edge cases.

**`pq_sift_up(pq, i)`**: após inserir no fim do array, move o elemento para cima enquanto for "melhor" que o pai. `pai = (i-1)/2`.

**`pq_sift_down(pq, i)`**: após remover o topo (substituído pelo último), move para baixo comparando com filhos `2*i+1` e `2*i+2`.

**`pq_push()`**: inserção com redimensionamento automático (dobra capacidade se cheia).

**`pq_remove(coder_id)`**: busca linear O(n) pelo `coder_id`, substitui pelo último, e faz sift_down + sift_up para reequilibrar.

**Complexidade**: push O(log n), pop O(log n), remove O(n) no pior caso (n ≤ 200).

---

### `dongle.c` e `dongle_utils.c`

#### `dongle_acquire(d, coder)`

```
1. Bloqueia d->mutex
2. Calcula a key (FIFO: get_time_ms(), EDF: coder->deadline)
3. Insere o coder na fila de prioridade d->waiters
4. Chama acquire_loop(d, coder)
```

#### `acquire_loop(d, coder)`

```
loop:
  1. Verifica sim->stopped → se parado, remove da fila e retorna 0
  2. Chama try_acquire(d, coder)
     → se sucesso, desbloqueia d->mutex e retorna 1
  3. Chama wait_one_ms(d)
     → pthread_cond_timedwait com timeout de 1ms
     → liberta d->mutex durante a espera e volta a adquirir quando acordado
```

**Porquê `timedwait` em vez de `wait` simples?**
Para que o coder re-cheque o flag `stopped` periodicamente, mesmo que nenhum `broadcast` aconteça. Sem isto, um coder poderia ficar bloqueado para sempre após a paragem da simulação.

#### `try_acquire(d, coder)`

```c
int try_acquire(t_dongle *d, t_coder *coder)
{
    if (!is_my_turn(d, coder->id) || d->in_use) return 0;
    if (d->in_cooldown) {
        now = get_time_ms();
        if ((d->release_time + d->sim->dongle_cooldown) - now <= 0)
            d->in_cooldown = 0;
    }
    if (d->in_cooldown) return 0;
    d->in_use = 1;
    pq_remove(&d->waiters, coder->id);
    return 1;
}
```

**`is_my_turn(d, coder_id)`**: verifica se o topo do heap é este coder (só ele pode avançar).

**Cooldown check**: a expressão `(release_time + cooldown) - now <= 0` evita overflow ao subtrair em vez de somar.

#### `dongle_release(d, coder)`

```c
d->in_use = 0;
d->in_cooldown = 1;
d->release_time = get_time_ms();
pthread_cond_broadcast(&d->cond);  // acorda todos os waiters deste dongle
```

O broadcast faz todos os waiters acordarem e cada um tentará `try_acquire`, mas apenas o que está no topo do heap vai conseguir (os outros voltam a adormecer).

---

### `coder.c`

#### `get_dongle_order(coder, *first, *second)`

```c
if (left < right) { *first = left; *second = right; }
else              { *first = right; *second = left; }
```

**Prevenção de deadlock**: ao adquirir sempre o dongle de menor índice primeiro, quebra-se a condição de **espera circular** de Coffman. Nunca haverá uma situação em que o coder A espera pelo dongle do coder B enquanto B espera pelo de A, porque ambos tentariam o mesmo dongle (o de menor índice) primeiro.

O `dongle_order_mutex` protege esta lógica de uma potencial race condition na leitura simultânea de `left_dongle` e `right_dongle` (embora estes campos sejam imutáveis após init, a norma 42 exige precaução).

#### `coder_routine()`

```c
sleep_ms((long long)(coder->id - 1) * CODER_START_OFFSET);
```

Cada coder espera `(id-1)*5 ms` antes de começar. O coder 1 começa imediatamente, o coder 2 espera 5ms, o 3 espera 10ms, etc. Isto evita contention total no início e ajuda o scheduler a distinguir prioridades desde o início.

---

### `monitor.c`

#### `monitor_routine()`

```c
while (1) {
    usleep(500);            // verifica a cada 0.5ms
    if (sim_is_stopped(sim)) break;
    if (check_all_done(sim)) { stop_sim(sim); break; }
    if (check_burnout(sim))  { stop_sim(sim); break; }
}
```

**Porquê 500µs?** A tolerância de burnout é 10ms. A dormir 0.5ms, no pior caso a detecção demora ~0.5ms após o deadline real — bem dentro dos 10ms exigidos.

#### `check_burnout()`

```c
deadline = sim->coders[i].last_compile_start + sim->time_to_burnout;
if (now >= deadline && sim->coders[i].state != STATE_COMPILING)
    // burnout!
```

**Nota crucial**: `state != STATE_COMPILING` → se o coder já começou a compilar, não faz burnout (mesmo que o deadline já tenha passado durante o compile). O burnout só ocorre se o coder **não conseguiu começar a compilar** a tempo.

#### `stop_sim()`

```c
pthread_mutex_lock(&sim->stop_mutex);
sim->stopped = 1;
sim->end_time_ms = get_time_ms();
pthread_mutex_unlock(&sim->stop_mutex);
broadcast_all(sim);  // acorda todos os coders bloqueados em acquire_loop
```

---

### `sim_init.c`

**`init_coders()`** — detalhe do dongle assignment:
```c
sim->coders[i].left_dongle = i;            // dongle i pertence ao coder i+1
if (sim->n_coders == 1)
    sim->coders[i].right_dongle = 0;       // 1 coder → só 1 dongle
else
    sim->coders[i].right_dongle = (i + 1) % sim->n_coders;  // circular
```

Para 4 coders:
- Coder 1: left=0, right=1
- Coder 2: left=1, right=2
- Coder 3: left=2, right=3
- Coder 4: left=3, right=0 (circular)

**`init_coders()`** — deadline inicial:
```c
sim->coders[i].last_compile_start = sim->start_time_ms;
sim->coders[i].deadline = sim->start_time_ms + sim->time_to_burnout;
```
Todos começam com o mesmo deadline inicial (o tempo de burnout a partir do início da simulação).

---

### `sim.c`

**`sim_run()`**: cria monitor primeiro, depois os coders, faz join dos coders, define `stopped=1`, faz broadcast e join do monitor.

**Porquê join dos coders antes do monitor?** Os coders podem estar bloqueados em `acquire_loop`. O `stopped=1` + `broadcast_all` acorda-os. Após o join dos coders, o `stopped` já está a 1 e o monitor vai sair no próximo ciclo.

---

## 7. Fila de Prioridade (min-heap)

Um **min-heap** é uma árvore binária completa onde o pai é sempre menor (ou igual) que os filhos. É implementado como array:

```
Índices:     0     1     2     3     4
             P   filho  filho  ...
             |  esq=2i+1  dir=2i+2
```

**Exemplo visual** (FIFO, 3 coders à espera do dongle com timestamps 100, 50, 200):
```
Inserção: 100 → [100]
Inserção: 50  → [100, 50] → sift_up → [50, 100]
Inserção: 200 → [50, 100, 200]

Array: [50, 100, 200]
         50
        /    \
      100    200
```

O `pq_peek` devolve sempre o coder com menor timestamp (o que chegou primeiro, em FIFO).

---

## 8. Problemas de Concorrência e Soluções

### 8.1 Deadlock (Impasse)

**Condições de Coffman (as 4 condições para deadlock):**
1. **Exclusão mútua**: um dongle só pode ser usado por um coder de cada vez. ✓ (necessário)
2. **Posse e espera**: um coder segura um dongle e espera por outro. ✓ (pode acontecer)
3. **Sem preempção**: não se pode forçar um coder a largar o dongle. ✓ (necessário)
4. **Espera circular**: A espera B espera C espera A. ✗ **ELIMINADO**

**Solução**: ordenação global dos recursos (Coffman Ordering). Ao adquirir sempre o dongle de menor índice primeiro, nunca há espera circular. Se coder 1 (left=0, right=1) e coder 2 (left=1, right=2) quiserem os seus dongles:
- Coder 1 tenta: first=0, second=1
- Coder 2 tenta: first=1, second=2
- Não há sobreposição na ordem de aquisição → sem deadlock.

**O caso especial do último coder**: O coder N tem left=N-1, right=0. Sem ordenação: pegaria N-1 e depois tentaria 0. Mas com a ordenação, pega 0 (menor) primeiro. Isto é exactamente o que `get_dongle_order` faz.

### 8.2 Starvation (Inanição)

**Problema**: um coder podia ser sempre preterido por outros, nunca conseguindo um dongle.

**Solução**: a fila de prioridade garante que cada coder que entrou na fila **vai eventualmente ser o topo** e conseguir o dongle. Em FIFO, a ordem de chegada é respeitada. Em EDF, o de deadline mais próximo tem prioridade, mas todos vão chegar ao topo.

### 8.3 Race condition no flag `stopped`

**Problema**: múltiplas threads lêem e escrevem `sim->stopped` em simultâneo.

**Solução**: `stop_mutex` protege todas as leituras e escritas de `stopped`.

```c
int sim_is_stopped(t_sim *sim) {
    pthread_mutex_lock(&sim->stop_mutex);
    int stopped = sim->stopped;
    pthread_mutex_unlock(&sim->stop_mutex);
    return stopped;
}
```

### 8.4 Interleaving de logs

**Problema**: dois `printf` de threads diferentes podem intercalar caracteres na mesma linha.

**Solução**: `log_mutex` serializa todo o output. O mutex é adquirido antes do `printf` e libertado depois. Nunca se chama `log_state` com outro mutex do sistema já adquirido (evita deadlock).

### 8.5 Double-acquire de dongle

**Problema**: dois coders poderiam obter o mesmo dongle em simultâneo.

**Solução**: o flag `in_use` é verificado e definido atomicamente dentro do `d->mutex`. A sequência `is_my_turn() && !in_use → in_use=1` é uma secção crítica protegida.

---

## 9. Os dois schedulers: FIFO vs EDF

### FIFO (First In, First Out)

```c
key = get_time_ms();  // timestamp no momento de pedir o dongle
```

- O coder que pediu o dongle primeiro (menor timestamp) é atendido primeiro.
- Simples, justo em termos de ordem de chegada.
- **Risco**: um coder com deadline urgente pode ficar atrás de um que chegou antes mas tem folga.

### EDF (Earliest Deadline First)

```c
key = coder->deadline;  // = last_compile_start + time_to_burnout
```

- O coder com deadline mais próxima é atendido primeiro.
- Óptimo para sistemas de tempo-real: minimiza burnouts sob carga.
- `deadline` é actualizado no início de cada compile: `coder->deadline = coder->last_compile_start + sim->time_to_burnout`.

### Tie-breaker (empate de deadlines)

Em EDF, dois coders podem ter o mesmo deadline (ex: mesmo `last_compile_start`). O tie-breaker em `comes_before` é `a->coder_id > b->coder_id`: o coder com **maior id** aparece primeiro no heap, ou seja, o com **menor id** fica para depois. Isto garante determinismo total.

---

## 10. O dongle_cooldown

Após um dongle ser libertado (`dongle_release`):
```c
d->in_cooldown = 1;
d->release_time = get_time_ms();
```

O próximo coder que tentar `try_acquire` vai verificar:
```c
if (d->in_cooldown) {
    now = get_time_ms();
    if ((d->release_time + d->sim->dongle_cooldown) - now <= 0)
        d->in_cooldown = 0;  // cooldown expirou
}
if (d->in_cooldown) return 0;  // ainda em cooldown, não adquire
```

**Porquê `(release_time + cooldown) - now` em vez de `now - release_time >= cooldown`?**
Matematicamente equivalente, mas a versão com subtração evita potencial overflow em sistemas com `long long` pequeno (embora improvável aqui). É uma boa prática defensiva.

O cooldown simula o tempo que um dongle físico precisaria de "reiniciar" antes de ser usado por outra pessoa.

---

## 11. A thread monitor

A monitor é uma thread separada (não é um coder). Corre `monitor_routine`.

**Responsabilidades:**
1. Detectar burnout com precisão ≤ 10ms.
2. Detectar que todos os coders completaram o número de compiles necessário.
3. Chamar `stop_sim()` quando uma condição de paragem é satisfeita.

**Periodicidade**: dorme 500µs (`usleep(500)`) entre verificações.

**Porquê 500µs e não 1ms ou 10ms?**
- A 500µs, no pior caso a latência de detecção é ~500µs, bem abaixo dos 10ms exigidos.
- A 10ms, a latência poderia ser até 10ms, o que violaria o requisito.

**Burnout detection logic**:
```c
if (now >= deadline && coder->state != STATE_COMPILING)
```
A condição `!= STATE_COMPILING` é importante: se o coder já adquiriu os dois dongles e está a compilar, ele não faz burnout mesmo que o tempo do deadline tenha passado. O burnout só ocorre se ele ainda está `STATE_WAITING` quando o deadline chega.

---

## 12. Primitivas POSIX usadas

### `pthread_create` / `pthread_join`

```c
pthread_create(&sim->monitor_thread, NULL, monitor_routine, sim);
// ...
pthread_join(sim->coders[i].thread, NULL);
```

`pthread_create` lança uma nova thread que começa a executar a função passada com o argumento dado.
`pthread_join` bloqueia até a thread terminar, garantindo que não há memory leaks nem use-after-free.

### `pthread_mutex_t`

Mutex = **MUT**ual **EX**clusion. Garante que só uma thread está numa secção crítica.

```c
pthread_mutex_lock(&mutex);   // bloqueia se alguém já tiver o mutex
// ... secção crítica ...
pthread_mutex_unlock(&mutex); // liberta
```

### `pthread_cond_t`

Variável de condição. Permite que uma thread **durma** enquanto espera por uma condição, sem busy-wait (sem gastar CPU).

```c
// Thread A (que espera):
pthread_mutex_lock(&mutex);
pthread_cond_wait(&cond, &mutex);  // liberta mutex atomicamente e dorme
// quando acorda, volta a ter o mutex
pthread_mutex_unlock(&mutex);

// Thread B (que notifica):
pthread_mutex_lock(&mutex);
// mudar estado
pthread_cond_broadcast(&cond);  // acorda todos os que esperam
pthread_mutex_unlock(&mutex);
```

**`pthread_cond_timedwait`**: igual ao `wait`, mas com timeout. Se o timeout expirar sem `broadcast`, a thread acorda de qualquer forma.

### `gettimeofday`

```c
struct timeval tv;
gettimeofday(&tv, NULL);
// tv.tv_sec = segundos desde epoch (1 Jan 1970)
// tv.tv_usec = microssegundos dentro do segundo actual
long long ms = tv.tv_sec * 1000LL + tv.tv_usec / 1000LL;
```

### `usleep`

```c
usleep(500);      // dorme 500 microssegundos = 0.5ms
usleep(1000);     // dorme 1 milissegundo
```

---

## 13. Sequência de Memória e Limpeza

### Alocação (sim_init)
```
malloc(sizeof(t_coder) * n_coders)   → sim->coders
malloc(sizeof(t_dongle) * n_coders)  → sim->dongles
malloc(sizeof(t_pq_node) * capacity) → dongle[i].waiters.nodes   (para cada dongle)
```

### Libertação (sim_cleanup)
```
Para cada dongle:
    pq_free(&dongles[i])           → free(dongles[i].waiters.nodes)
    pthread_cond_destroy(...)
    pthread_mutex_destroy(...)
free(sim->dongles)
free(sim->coders)
pthread_mutex_destroy(&stop_mutex)
pthread_mutex_destroy(&log_mutex)
pthread_mutex_destroy(&dongle_order_mutex)
```

**Ordem de limpeza**: destruir primeiro os recursos internos de cada dongle, depois o array de dongles, depois o array de coders. Os mutexes globais são os últimos a ser destruídos.

---

## 14. Casos de Teste Importantes

### Teste básico — sem burnout
```bash
./codexion 4 1400 200 100 100 3 100 fifo
```
4 coders, 1400ms para burnout, 200ms compile, 100ms debug, 100ms refactor, 3 compiles, 100ms cooldown, FIFO.

### Teste com 1 coder (edge case)
```bash
./codexion 1 800 200 100 100 2 50 fifo
```
1 coder → 1 dongle → o coder usa o mesmo dongle como left e right (índice 0 em ambos).

### Teste de burnout intencional
```bash
./codexion 3 200 100 500 500 5 100 fifo
```
O debug+refactor demoram muito mais do que o time_to_burnout → burnout garantido.

### Teste EDF
```bash
./codexion 4 1000 150 100 50 5 80 edf
```
Com EDF, o coder com deadline mais próxima tem prioridade nos dongles.

### Validação de argumentos inválidos
```bash
./codexion 5 abc 200 100 100 3 100 fifo  # erro: não é inteiro
./codexion 5 -100 200 100 100 3 100 fifo # erro: negativo
./codexion 5 200 300 100 100 3 100 fifo  # erro: compile >= burnout
./codexion 5 200 100 100 100 3 100 random # erro: scheduler inválido
```

---

## 15. Perguntas Frequentes na Avaliação

**P: Por que usas uma priority queue em vez de um mutex simples por dongle?**
R: Um mutex simples não garante ordem de atendimento. Dois coders a competir pelo mesmo dongle seriam atendidos de forma arbitrária pelo OS, sem respeitar FIFO nem EDF. A priority queue garante que o atendimento é determinístico e justo.

**P: Como é que o deadlock é prevenido?**
R: Através da ordenação dos recursos (Coffman Ordering). Todos os coders adquirem sempre o dongle de menor índice primeiro. Isto elimina a condição de espera circular. Sem esta ordenação, o coder 1 poderia segurar o dongle 0 e esperar pelo 1, enquanto o coder 2 segura o 1 e espera pelo 0 → deadlock.

**P: O que acontece quando `sim->stopped` é definido a 1?**
R: O `broadcast_all` acorda todas as threads bloqueadas em `pthread_cond_timedwait` (nos `acquire_loop`). Cada thread acorda, re-verifica `sim_is_stopped()`, encontra `stopped=1` e sai do loop. Os coders terminam as suas threads e o monitor termina a sua.

**P: Porquê `dongle_order_mutex`?**
R: Protege a leitura de `left_dongle` e `right_dongle` na função `get_dongle_order`. Embora estes campos não mudem após `init_coders`, a norma 42 e boas práticas de concorrência exigem protecção de dados partilhados.

**P: O que é o `CODER_START_OFFSET`?**
R: É 5ms. Cada coder espera `(id-1)*5ms` antes de começar. Isso escala os inícios para evitar que todos os coders compitam pelos mesmos dongles ao mesmo milissegundo, o que poderia criar contention intensa e complicar o scheduling.

**P: Qual é a diferença entre `pthread_cond_wait` e `pthread_cond_timedwait`?**
R: `wait` bloqueia indefinidamente até receber um sinal (`signal` ou `broadcast`). `timedwait` tem um timeout: se não receber sinal até ao tempo especificado, acorda sozinho. Usamos `timedwait` com 1ms para que os coders re-verifiquem o flag `stopped` periodicamente.

**P: Como é que o cooldown é implementado exactamente?**
R: Quando `dongle_release` é chamado, `in_cooldown=1` e `release_time=now`. Em cada chamada a `try_acquire`, se `in_cooldown==1`, verificamos se `(release_time + cooldown) - now <= 0`. Se sim, clearamos `in_cooldown`. Isto é verificado dentro do mutex do dongle, garantindo atomicidade.

**P: O monitor pode fazer burnout antes do coder?**
R: O monitor detecta burnout verificando `now >= deadline && state != COMPILING`. Existe uma janela de ~0.5ms entre o instante real de burnout e a detecção. O requisito é que a mensagem seja impressa no máximo 10ms após o burnout real, o que é satisfeito com uma periodicidade de 500µs.

**P: Podes ter variáveis globais?**
R: Não. O subject proíbe explicitamente. Todo o estado é passado através de ponteiros para `t_sim`, que é declarado na stack de `main()` e passado por referência a todas as funções e threads.

**P: O que imprime no stdout vs stderr?**
R: **Stdout**: todos os logs de estado durante a simulação (`timestamp X msg`). **Stderr**: as estatísticas finais (`sim_print_stats`). Isto permite redirecionar os logs sem perder as estatísticas.
