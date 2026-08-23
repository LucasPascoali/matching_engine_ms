"""Modelos de domínio da matching engine.

Este módulo define apenas as estruturas de dados que representam uma
ordem e seus atributos (tipo, lado, preço, quantidade). Nenhuma lógica de
matching, book ou execução vive aqui — o objetivo é manter os modelos
simples e testáveis isoladamente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import count
from typing import Optional

_id_counter = count(1)


def _next_order_id() -> str:
    """Gera um identificador único e sequencial para uma ordem.
    """
    return f"ID_{next(_id_counter)}"


class Side(Enum):
    """Lado da ordem: compra ou venda."""

    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Tipo da ordem.

    - LIMIT: ordem passiva com preço fixo definido pelo participante.
    - MARKET: ordem que deve ser preenchida imediatamente ao melhor
      preço disponível (tratada como IOC — ver README, seção de
      decisões de design).
    - PEGGED: ordem cujo preço acompanha uma referência do book (melhor
      bid ou melhor offer), sendo reprecificada automaticamente pela
      engine sempre que essa referência mudar.
    """

    LIMIT = "limit"
    MARKET = "market"
    PEGGED = "pegged"

class PegReference(Enum):
    """Referência de preço que uma ordem pegged deve seguir."""

    BID = "bid"
    OFFER = "offer"


@dataclass
class Order:
    """Representa uma ordem dentro da matching engine.

    Atributos:
        side: compra/venda
        order_type: limit/market/pegged
        qty: quantidade restante a ser executada
        price: preço da ordem
        peg_reference: referência de preço para ordens do tipo pegged
        id: identificador
        original_qty: quantidade original da ordem no momento da criação
    """

    side: Side
    order_type: OrderType
    qty: int
    price: Optional[float] = None
    peg_reference: Optional[PegReference] = None
    id: str = field(default_factory=_next_order_id)
    original_qty: int = field(init=False)

    def __post_init__(self) -> None:
        if self.qty <= 0:
            raise ValueError("qty deve ser maior que zero")

        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("ordens limit exigem price")

        if self.order_type == OrderType.MARKET and self.price is not None:
            raise ValueError("ordens market não devem ter price definido")

        if self.order_type == OrderType.PEGGED and self.peg_reference is None:
            raise ValueError("ordens pegged exigem peg_reference (bid/offer)")

        if self.order_type != OrderType.PEGGED and self.peg_reference is not None:
            raise ValueError("peg_reference só é válido para ordens pegged")

        self.original_qty = self.qty

    def __repr__(self) -> str:  # pragma: no cover - apenas legibilidade
        price_repr = self.price if self.price is not None else "N/A"
        return (
            f"Order({self.id}, {self.side}, "
            f"{self.order_type.lower()}, qty={self.qty}, "
            f"price={price_repr})"
        )
