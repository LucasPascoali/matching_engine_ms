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

    def cancel(self, order_id: str) -> Optional[Order]:
        """Cancela a ordem `order_id`.
        """
        return self.book.cancel(order_id)

    def modify(self,order_id: str,new_price: Optional[float] = None,new_qty: Optional[int] = None,) -> List[Trade]:
        """Altera preço e/ou qty da ordem `order_id`.

        Regra de prioridade:
            - Só reduzir qty: mantém a posição na fila.
            
            - Mudar o preço, ou aumentar qty: perde prioridade (cancel/replace)
        """
        
        order = self.book.get_order(order_id)
        if order is None:
            raise ValueError(f"ordem {order_id} não encontrada no book")

        price_changed = new_price is not None and new_price != order.price
        qty_increased = new_qty is not None and new_qty > order.qty

        if not price_changed and not qty_increased:
            if new_qty is not None and new_qty != order.qty:
                self.book.reduce_qty(order, new_qty)
            return []

        cancelled = self.book.cancel(order_id)
        replacement = Order(
            side=cancelled.side,
            order_type=cancelled.order_type,
            qty=new_qty if new_qty is not None else cancelled.qty,
            price=new_price if new_price is not None else cancelled.price,
            peg_reference=cancelled.peg_reference,
            id=cancelled.id,
        )
        return self.submit(replacement)
    
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
