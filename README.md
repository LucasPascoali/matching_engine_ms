# Matching Engine

Implementação de uma matching engine simples para um único ativo, suportando
ordens *limit* e *market*, cancelamento, alteração (modify) e ordens *pegged*
(peg to bid / peg to offer).

Este projeto foi desenvolvido como parte de um processo seletivo.

## Status

Em desenvolvimento. O README será atualizado a cada etapa da
implementação.

## Premissas e decisões de design

O enunciado deixa alguns comportamentos em aberto. As
decisões abaixo são tomadas para refletir o comportamento mais próximo do
que se observa em exchanges reais:

1. **Limit order que cruza o book é preenchida (não ignorada).**
   Uma limit buy a um preço igual ou superior ao melhor ask disponível será
   executada imediatamente contra o book. Apenas a quantidade que não encontrar contraparte permanece como
   ordem passiva no book, na sua respectiva faixa de preço. Ignorar esse
   cruzamento geraria um comportamento contraintuitivo para quem está
   operando.

2. **Market order é tratada como IOC (*Immediate or Cancel*).**
   Uma market order tenta ser preenchida imediatamente contra as melhores
   ofertas disponíveis. Caso não haja liquidez suficiente no book para
   preencher toda a quantidade solicitada, a parcela remanescente é
   descartada. Isso porque uma market order não
   possui preço de referência associado — mantê-la pendente exigiria
   inventar um preço, o que descaracterizaria o tipo de ordem.

3. **Prioridade preço-tempo (price-time priority).**
   Dentro do mesmo nível de preço, ordens são preenchidas respeitando a
   ordem de chegada (FIFO), conforme exigido no enunciado.

4. **Alteração (modify) de ordem e perda de prioridade.**
   - Alteração de **preço**: a ordem é reinserida no final da fila do novo nível de preço, perdendo prioridade.
   - Alteração **apenas de quantidade para menos**: a ordem mantém sua posição na fila.
   - Alteração de quantidade **para mais**: a ordem vai para o final da fila do mesmo nível de preço, pois um aumento de quantidade poderia ser usado para "furar fila" se mantivesse a posição original.

5. **Sem persistência.** Todas as estruturas (book, ordens, trades) vivem em
   memória, conforme a premissa 3 do enunciado.

6. **Estruturas de dados e complexidade.** será preenchido conforme o desenvolvimento

## Sobre o uso de ferramentas de IA

Este projeto foi desenvolvido com o auxílio de ferramentas de Inteligência
Artificial, conforme permitido pelo enunciado do processo seletivo. Todo o
código, decisões técnicas e comportamento do sistema são de responsabilidade
e autoria do candidato, que conhece integralmente a base de código e é capaz
de explicá-la.

- **Ferramenta utilizada:** Claude (Anthropic) — modelo Claude Sonnet 5,
  via interface de chat Claude.ai.
- **Como foi usada:** apoio na estruturação do projeto, revisão de código e
  sugestões de design. Todas as decisões de arquitetura e regras de negócio
  foram avaliadas e validadas pelo candidato.
