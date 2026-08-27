# Matching Engine

Matching engine simples, em memória, para um único ativo. Python puro,
sem dependências externas.

## Como rodar

```bash
python main.py                 # REPL interativo
python main.py < cenario.txt   # via script/pipe
```

Comandos do REPL:

```
add buy|sell limit <qty> <price>
add buy|sell market <qty>
add buy|sell pegged <qty> bid|offer
cancel <id>
modify <id> [price=<p>] [qty=<q>]
book
quit
```

## Estrutura

```
engine
|_ order.py            # modelos de domínio (Order, Side, OrderType, PegReference)
|_ order_book.py         # estrutura de dados: bids/asks, heap de preços, deque por nível
|_ matching.py             # regras de negócio: crossing, cancel, modify, pegged
|_ main.py                  # CLI/REPL
tests
|_ test_*.py                 # testes
```

Três camadas separadas por responsabilidade: `order.py` só valida uma
ordem isolada; `order_book.py` só guarda e organiza ordens (não sabe o
que é "cruzar" ou "pegged"); `matching.py` concentra toda a lógica de
negócio. Isso mantém o book reutilizável e cada peça testável sozinha.

## Requisitos do enunciado

| Requisitos | Onde |
|---|---|
| Complexidade O(N) | ver [Complexidade](#complexidade) |
| Visualização do book | `OrderBook.print_book()` |
| Prioridade preço-tempo (FIFO) | `deque` por nível de preço |
| Cancelamento | `MatchingEngine.cancel` |
| Modify (preço/qty) | `MatchingEngine.modify` |
| Pegged (bid/offer) | `MatchingEngine._submit_pegged` / `_reprice_pegged_orders` |
| Limit que cruza o book | ver [Decisões de design](#decisões-de-design) |
| `Trade, price: <p>, qty: <q>` | `Trade.__str__` |

## Complexidade

- `add_order`, `best_bid`/`best_ask`: O(1) amortizado (heap com lazy
  deletion — cada preço só é descartado do heap uma vez).
- `fill`, `reduce_qty`: O(1).
- `cancel`: O(k), k = ordens no mesmo nível de preço (busca no `deque`).
  No pior caso O(N). Trade-off aceito: O(1) real exigiria uma lista
  duplamente encadeada com ponteiros por ordem, complexidade extra que
  não pareceu justificada para o escopo do exercício.

## Decisões de design

- **Limit que cruza o book:** primeiro tenta executar contra o book; a
  sobra (se houver) fica resting no seu preço-limite. Preço do trade é
  sempre o da ordem passiva — comportamento padrão em exchanges reais.
- **Market = IOC:** cruza o máximo possível imediatamente e descarta o
  restante; nunca fica resting (não haveria preço válido para isso).
- **Modify:** só reduzir qty mantém prioridade (ajuste in-place). Mudar
  preço ou aumentar qty é tratado como cancel/replace (mesmo `id`, vai
  para o fim da fila) — evita que alguém "segure" a fila aumentando
  volume que nunca teve.
- **Pegged:** preço nunca é escolhido manualmente, sempre calculado
  pela engine a partir de `best_bid`/`best_ask`. O `OrderBook` não sabe
  o que é pegged — a `MatchingEngine` mantém seu próprio registro e
  manipula o book de fora.

### O bug de pegged (e por que existem duas leituras de "melhor preço")

Pegged orders resting no book contaminavam seu próprio cálculo de
referência: se uma pegged ocupava o topo do book, um fill parcial que
não esvaziava o nível não movia `best_bid`/`best_ask`, então ela nunca
reprecificava contra si mesma. O mesmo acontecia entre múltiplas
pegged no mesmo nível sem nenhuma ordem real por trás.

Solução: `_reprice_pegged_orders` remove **todas** as pegged resting do
book antes de calcular o alvo de qualquer uma, e só então
recalcula/reinsere. Isso porque matching precisa enxergar toda a
liquidez (inclusive pegged), mas reprice precisa enxergar só liquidez
real — não dá para satisfazer as duas com uma única leitura de "melhor
preço", então a mais simples é remover fisicamente antes de perguntar.

Efeito colateral aceito: a cada reprice, todas as pegged saem e voltam
ao book (mesmo as que não mudam de preço).

## Limitações conhecidas

- Um único ativo por engine; sem persistência; sem concorrência.
- `cancel` é O(k), não O(1) — ver acima.
- Reprice de pegged reinsere todas as pegged a cada passada, mesmo as
  que não mudam.
