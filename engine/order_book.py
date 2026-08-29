"""Order book: estrutura de dados que mantém ordens organizadas por
nível de preço e prioridade de chegada

Estrutura de dados escolhida:
    - Um dict `price -> deque[Order]` append/popleft em O(1)
    
    - Um heap (min-heap) por lado guarda os preços para permitir obter o melhor preço em O(1), e inserir um novo nível de preço em O(log N)
    
    - Um dict `order_id -> Order` dá acesso O(1) a qualquer ordem pelo id
"""

from __future__ import annotations

import heapq
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple
from engine.order import Order, OrderType, Side

class OrderBook:
    """Mantém o livro de ofertas de um único ativo."""

    def __init__(self) -> None:
        # price -> deque de ordens naquele nível, em ordem de chegada
        self._bids: Dict[float, Deque[Order]] = {}
        self._asks: Dict[float, Deque[Order]] = {}

        # heaps de preços.
        self._bid_price_heap: List[float] = []
        self._ask_price_heap: List[float] = []
      
        self._orders_by_id: Dict[str, Order] = {}

    def add_order(self, order: Order) -> None:
        if order.order_type not in (OrderType.LIMIT, OrderType.PEGGED):
            raise NotImplementedError(
                f"OrderBook.add_order não trata ordens do tipo "
                f"{order.order_type.name}; market orders são IOC e "
                f"nunca ficam no book."
            )
        if order.price is None:
            raise ValueError(
                "não é possível inserir no book uma ordem sem price "
                "definido (pegged deve ser precificada antes de add_order)"
            )
        self._add_limit_order(order)

    def _add_limit_order(self, order: Order) -> None:
        book, heap = self._book_and_heap_for(order.side)
        heap_key = self._heap_key(order.side, order.price)

        is_new_price_level = order.price not in book or not book[order.price]
        if order.price not in book:
            book[order.price] = deque()
        if is_new_price_level:
            heapq.heappush(heap, heap_key)

        book[order.price].append(order)
        self._orders_by_id[order.id] = order
      
    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders_by_id.get(order_id)

    def best_bid(self) -> Optional[float]:
        self._pop_stale_prices(self._bid_price_heap, self._bids, side=Side.BUY)
        if not self._bid_price_heap:
            return None
        return -self._bid_price_heap[0]

    def best_ask(self) -> Optional[float]:
        self._pop_stale_prices(self._ask_price_heap, self._asks, side=Side.SELL)
        if not self._ask_price_heap:
            return None
        return self._ask_price_heap[0]

    def bid_levels(self) -> List[Tuple[float, int]]:
        """Retorna [(preço, qty_total), ...] dos bids, do melhor para o pior."""
        return self._levels(self._bids, reverse=True)

    def ask_levels(self) -> List[Tuple[float, int]]:
        """Retorna [(preço, qty_total), ...] dos asks, do melhor para o pior."""
        return self._levels(self._asks, reverse=False)

    def bid_orders(self) -> List[Order]:
        """Retorna as ordens de compra, uma por linha (sem agregar por
        nível de preço), ordenadas do melhor preço para o pior e, dentro
        do mesmo preço, da mais antiga para a mais recente (FIFO).
        """
        return self._orders_sorted(self._bids, reverse=True)

    def ask_orders(self) -> List[Order]:
        """Retorna as ordens de venda, uma por linha (sem agregar por
        nível de preço), ordenadas do melhor preço para o pior e, dentro
        do mesmo preço, da mais antiga para a mais recente (FIFO).
        """
        return self._orders_sorted(self._asks, reverse=False)

    def peek_best(self, side: Side) -> Optional[Order]:
        """Retorna a ordem no topo da fila do melhor nível
        de preço para o lado indicado.
        """
        price = self.best_bid() if side == Side.BUY else self.best_ask()
        if price is None:
            return None
        book = self._bids if side == Side.BUY else self._asks
        return book[price][0]
 
    def fill(self, order: Order, qty: int) -> None:
        """Executa `qty` unidades da ordem `order`, que deve ser a ordem
        no topo da fila do seu nível de preço. Reduz order.qty e, se ela se esgotar, remove a
        ordem do book.
        """
        if qty <= 0 or qty > order.qty:
            raise ValueError("qty de fill inválida")
 
        book = self._bids if order.side == Side.BUY else self._asks
        order.qty -= qty
 
        if order.qty == 0:
            book[order.price].popleft()
            del self._orders_by_id[order.id]
            if not book[order.price]:
                del book[order.price]
    
    def cancel(self, order_id: str) -> Optional[Order]:
        """Remove do book a ordem `order_id`. Retorna a ordem removida, ou None se o id não existir.
        Complexidade: O(k) k é o número de ordems no mesmo nível de preco,
        """
        
        order = self._orders_by_id.get(order_id)
        if order is None:
            return None

        book = self._bids if order.side == Side.BUY else self._asks
        book[order.price].remove(order)
        del self._orders_by_id[order_id]
        if not book[order.price]:
            del book[order.price]
        return order

    def reduce_qty(self, order: Order, new_qty: int) -> None:
        """Reduz a qty de `order` para `new_qty`, mantendo prioridade
        
        — aumentar qty é tratado como perda de prioridade em matching.py..
        """
        if new_qty <= 0 or new_qty > order.qty:
            raise ValueError(
                "reduce_qty só aceita 0 < new_qty <= qty atual da ordem"
            )
        order.qty = new_qty

    # ------------------------------------------------------------------
    # Visualização
    # ------------------------------------------------------------------

    def print_book(self) -> None:
        """Imprime o livro com uma linha por ordem (sem agregar ordens
        do mesmo nível de preço), da mais antiga para a mais recente
        dentro de cada preço:

        Ordens de Compra    | Ordens de Venda
        --------------------|-----------------
        150 @ 10             | 100 @ 10.5
        50 @ 10               |
        100 @ 9.99           |
        """
        bids = self.bid_orders()
        asks = self.ask_orders()

        col_bid = "Ordens de Compra"
        col_ask = "Ordens de Venda"
        print(f"{col_bid:<20}| {col_ask}")
        print(f"{'-' * 20}|{'-' * 20}")

        rows = max(len(bids), len(asks))
        for i in range(rows):
            bid_str = self._format_order(bids[i]) if i < len(bids) else ""
            ask_str = self._format_order(asks[i]) if i < len(asks) else ""
            print(f"{bid_str:<20}| {ask_str}")

        if rows == 0:
            print("(book vazio)")

    @staticmethod
    def _format_order(order: Order) -> str:
        price_str = f"{order.price:g}"  # remove zeros à direita (10.0 -> "10")
        return f"{order.qty} @ {price_str}, {order.id}"

    # ------------------------------------------------------------------
    # Auxiliares internos
    # ------------------------------------------------------------------

    def _orders_sorted(
        self, book: Dict[float, Deque[Order]], reverse: bool
    ) -> List[Order]:
        """Achata o book em uma lista única de ordens: ordenada por
        preço (melhor primeiro) e, dentro de cada preço, na ordem de
        chegada (o deque já mantém isso — iterar do início para o fim
        percorre da mais antiga para a mais recente).
        """
        prices = sorted((p for p, dq in book.items() if dq), reverse=reverse)
        orders: List[Order] = []
        for p in prices:
            orders.extend(book[p])
        return orders

    # ------------------------------------------------------------------
    # Auxiliares internos
    # ------------------------------------------------------------------

    def _book_and_heap_for(self, side: Side) -> Tuple[Dict[float, Deque[Order]], List[float]]:
        if side == Side.BUY:
            return self._bids, self._bid_price_heap
        return self._asks, self._ask_price_heap

    @staticmethod
    def _heap_key(side: Side, price: float) -> float:
        # bids usam max-heap emulado (preço negado); asks usam min-heap normal
        return -price if side == Side.BUY else price

    def _pop_stale_prices(
        self, heap: List[float], book: Dict[float, Deque[Order]], side: Side
    ) -> None:
        """Remove do topo do heap níveis de preço que já ficaram vazios.

        Lazy deletion: em vez de remover do heap quando um nível esvazia
        (o que exigiria O(N) para achar a posição), só limpamos o topo
        quando alguém pergunta pelo melhor preço. Amortizado, cada preço
        só é "descartado" uma vez ao longo da vida do book.
        """
        while heap:
            price = -heap[0] if side == Side.BUY else heap[0]
            if price in book and book[price]:
                return
            heapq.heappop(heap)

    def _levels(
        self, book: Dict[float, Deque[Order]], reverse: bool
    ) -> List[Tuple[float, int]]:
        prices = sorted((p for p, dq in book.items() if dq), reverse=reverse)
        return [(p, sum(o.qty for o in book[p])) for p in prices]
        
