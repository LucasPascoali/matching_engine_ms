"""Matching: cruzamento de ordens contra o order book.

Cada execução gera uma linha no formato exigido pelo enunciado:
    Trade, price: <price>, qty: <qty>
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from order import Order, OrderType, Side
from order_book import OrderBook


@dataclass(frozen=True)
class Trade:
    """Uma execução entre uma ordem agressora e uma passiva."""

    price: float
    qty: int

    def __str__(self) -> str:
        return f"Trade, price: {self.price:g}, qty: {self.qty}"


class MatchingEngine:
    """Processa ordens contra um único OrderBook (um único ativo)."""

    def __init__(self, book: Optional[OrderBook] = None) -> None:
        self.book = book if book is not None else OrderBook()

    def submit(self, order: Order) -> List[Trade]:
        """Processa `order` e retorna a lista de trades gerados
        """
        if order.order_type == OrderType.LIMIT:
            trades = self._match(order)
            if order.qty > 0:
                self.book.add_order(order)
            return trades

        if order.order_type == OrderType.MARKET:
            return self._match(order)

        raise NotImplementedError(
            f"MatchingEngine.submit ainda não trata ordens do tipo "
            f"{order.order_type.name}; será implementado em pegged.py."
        )

    # ------------------------------------------------------------------
    # Auxiliares internos
    # ------------------------------------------------------------------

    def _match(self, order: Order) -> List[Trade]:
        opposite_side = Side.SELL if order.side == Side.BUY else Side.BUY
        trades: List[Trade] = []

        while order.qty > 0:
            resting = self.book.peek_best(opposite_side)
            if resting is None or not self._crosses(order, resting.price):
                break

            fill_qty = min(order.qty, resting.qty)
            trade_price = resting.price  # a ordem passiva define o preço

            order.qty -= fill_qty
            self.book.fill(resting, fill_qty)

            trade = Trade(trade_price, fill_qty)
            trades.append(trade)
            print(trade)

        return trades

    @staticmethod
    def _crosses(order: Order, best_opposite_price: float) -> bool:
        """Decide se `order` cruza com o melhor preço do lado oposto.
        """
        if order.order_type == OrderType.MARKET:
            return True
        if order.side == Side.BUY:
            return order.price >= best_opposite_price
        return order.price <= best_opposite_price
