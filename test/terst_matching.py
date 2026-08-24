"""Testes simples e diretos da matching engine.

Não usa nenhum framework de teste: cada teste é uma função que monta um
cenário, executa e checa o resultado com `assert`. Rodar com:

    python3 -m engine.test_matching

Se tudo passar, imprime "TODOS OS TESTES PASSARAM" no final. Qualquer
assert que falhar interrompe a execução com o traceback do teste que
quebrou.
"""

from __future__ import annotations

from engine.order import Order, OrderType, Side
from engine.order_book import OrderBook
from engine.matching import MatchingEngine, Trade


def prices_and_qtys(trades: list[Trade]) -> list[tuple[float, int]]:
    """Facilita comparar trades gerados com o esperado em cada teste."""
    return [(t.price, t.qty) for t in trades]


# ----------------------------------------------------------------------
# OrderBook: inserção, consulta e visualização
# ----------------------------------------------------------------------

def test_add_order_and_best_bid_ask() -> None:
    book = OrderBook()
    buy = Order(Side.BUY, OrderType.LIMIT, qty=10, price=9.5)
    sell = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.5)
    book.add_order(buy)
    book.add_order(sell)

    assert book.best_bid() == 9.5
    assert book.best_ask() == 10.5
    assert book.get_order(buy.id) is buy
    assert book.get_order("inexistente") is None


def test_add_order_rejects_market_and_pegged() -> None:
    book = OrderBook()
    market = Order(Side.BUY, OrderType.MARKET, qty=10)
    try:
        book.add_order(market)
        assert False, "deveria ter levantado NotImplementedError"
    except NotImplementedError:
        pass


def test_best_bid_ask_none_quando_vazio() -> None:
    book = OrderBook()
    assert book.best_bid() is None
    assert book.best_ask() is None


def test_price_time_priority_fifo_dentro_do_mesmo_preco() -> None:
    book = OrderBook()
    first = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    second = Order(Side.SELL, OrderType.LIMIT, qty=20, price=10.0)
    book.add_order(first)
    book.add_order(second)

    # a primeira a chegar deve ser a primeira no topo da fila
    assert book.peek_best(Side.SELL) is first
    assert book.ask_orders() == [first, second]


def test_bid_ask_levels_agregados() -> None:
    book = OrderBook()
    book.add_order(Order(Side.BUY, OrderType.LIMIT, qty=10, price=9.0))
    book.add_order(Order(Side.BUY, OrderType.LIMIT, qty=5, price=9.0))
    book.add_order(Order(Side.BUY, OrderType.LIMIT, qty=7, price=8.5))

    # melhor preço primeiro, quantidades somadas por nível
    assert book.bid_levels() == [(9.0, 15), (8.5, 7)]


def test_fill_remove_ordem_esgotada_do_book() -> None:
    book = OrderBook()
    order = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    book.add_order(order)

    book.fill(order, 10)
    assert order.qty == 0
    assert book.get_order(order.id) is None
    assert book.best_ask() is None


def test_fill_parcial_mantem_ordem_no_book() -> None:
    book = OrderBook()
    order = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    book.add_order(order)

    book.fill(order, 4)
    assert order.qty == 6
    assert book.get_order(order.id) is order
    assert book.best_ask() == 10.0


def test_print_book_nao_quebra_com_book_vazio_ou_cheio() -> None:
    book = OrderBook()
    book.print_book()  # book vazio

    book.add_order(Order(Side.BUY, OrderType.LIMIT, qty=10, price=9.0))
    book.add_order(Order(Side.SELL, OrderType.LIMIT, qty=5, price=10.0))
    book.print_book()  # book com ordens


# ----------------------------------------------------------------------
# MatchingEngine: limit orders (crossing)
# ----------------------------------------------------------------------

def test_limit_sem_cruzamento_apenas_entra_no_book() -> None:
    engine = MatchingEngine()
    sell = Order(Side.SELL, OrderType.LIMIT, qty=10, price=11.0)
    engine.submit(sell)

    buy = Order(Side.BUY, OrderType.LIMIT, qty=10, price=10.0)
    trades = engine.submit(buy)

    assert trades == []
    assert engine.book.get_order(buy.id) is buy
    assert buy.qty == 10


def test_limit_cruza_e_preenche_totalmente_contra_uma_ordem() -> None:
    engine = MatchingEngine()
    sell = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    engine.submit(sell)

    buy = Order(Side.BUY, OrderType.LIMIT, qty=10, price=10.0)
    trades = engine.submit(buy)

    assert prices_and_qtys(trades) == [(10.0, 10)]
    assert buy.qty == 0
    assert engine.book.get_order(buy.id) is None  # não sobrou, não entra no book
    assert engine.book.get_order(sell.id) is None  # ordem passiva foi consumida


def test_limit_cruza_parcialmente_e_o_resto_entra_no_book() -> None:
    engine = MatchingEngine()
    sell = Order(Side.SELL, OrderType.LIMIT, qty=5, price=10.0)
    engine.submit(sell)

    buy = Order(Side.BUY, OrderType.LIMIT, qty=12, price=10.0)
    trades = engine.submit(buy)

    assert prices_and_qtys(trades) == [(10.0, 5)]
    assert buy.qty == 7
    assert engine.book.get_order(buy.id) is buy  # o restante virou ordem passiva
    assert engine.book.best_bid() == 10.0


def test_limit_cruza_multiplos_niveis_de_preco() -> None:
    engine = MatchingEngine()
    engine.submit(Order(Side.SELL, OrderType.LIMIT, qty=5, price=10.0))
    engine.submit(Order(Side.SELL, OrderType.LIMIT, qty=5, price=10.5))
    engine.submit(Order(Side.SELL, OrderType.LIMIT, qty=5, price=11.0))

    buy = Order(Side.BUY, OrderType.LIMIT, qty=12, price=11.0)
    trades = engine.submit(buy)

    assert prices_and_qtys(trades) == [(10.0, 5), (10.5, 5), (11.0, 2)]
    assert buy.qty == 0
    assert engine.book.best_ask() == 11.0  # sobrou 3 no nível 11.0


def test_limit_respeita_fifo_dentro_do_mesmo_nivel() -> None:
    engine = MatchingEngine()
    first = Order(Side.SELL, OrderType.LIMIT, qty=5, price=10.0)
    second = Order(Side.SELL, OrderType.LIMIT, qty=5, price=10.0)
    engine.submit(first)
    engine.submit(second)

    buy = Order(Side.BUY, OrderType.LIMIT, qty=5, price=10.0)
    engine.submit(buy)

    # a primeira ordem a chegar deve ser consumida primeiro
    assert first.qty == 0
    assert second.qty == 5
    assert engine.book.get_order(first.id) is None
    assert engine.book.get_order(second.id) is second


def test_trade_usa_preco_da_ordem_passiva() -> None:
    engine = MatchingEngine()
    sell = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    engine.submit(sell)

    # comprador aceitaria pagar até 10.5, mas a passiva já estava a 10.0
    buy = Order(Side.BUY, OrderType.LIMIT, qty=10, price=10.5)
    trades = engine.submit(buy)

    assert prices_and_qtys(trades) == [(10.0, 10)]


def test_sell_limit_cruza_contra_bids() -> None:
    engine = MatchingEngine()
    buy = Order(Side.BUY, OrderType.LIMIT, qty=10, price=10.0)
    engine.submit(buy)

    sell = Order(Side.SELL, OrderType.LIMIT, qty=6, price=9.0)
    trades = engine.submit(sell)

    assert prices_and_qtys(trades) == [(10.0, 6)]
    assert sell.qty == 0


# ----------------------------------------------------------------------
# MatchingEngine: market orders (IOC)
# ----------------------------------------------------------------------

def test_market_preenche_totalmente_e_nao_entra_no_book() -> None:
    engine = MatchingEngine()
    engine.submit(Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0))

    market = Order(Side.BUY, OrderType.MARKET, qty=10)
    trades = engine.submit(market)

    assert prices_and_qtys(trades) == [(10.0, 10)]
    assert market.qty == 0
    assert engine.book.get_order(market.id) is None


def test_market_com_liquidez_insuficiente_descarta_o_resto() -> None:
    engine = MatchingEngine()
    engine.submit(Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0))

    market = Order(Side.BUY, OrderType.MARKET, qty=30)
    trades = engine.submit(market)

    assert prices_and_qtys(trades) == [(10.0, 10)]
    assert market.qty == 20  # não preenchido, mas descartado (não entra no book)
    assert engine.book.get_order(market.id) is None
    assert engine.book.best_ask() is None


def test_market_sem_liquidez_nenhuma_nao_gera_trade() -> None:
    engine = MatchingEngine()  # book vazio

    market = Order(Side.SELL, OrderType.MARKET, qty=10)
    trades = engine.submit(market)

    assert trades == []
    assert market.qty == 10
    assert engine.book.get_order(market.id) is None


def test_market_percorre_varios_niveis_de_preco() -> None:
    engine = MatchingEngine()
    engine.submit(Order(Side.SELL, OrderType.LIMIT, qty=5, price=10.0))
    engine.submit(Order(Side.SELL, OrderType.LIMIT, qty=5, price=10.5))

    market = Order(Side.BUY, OrderType.MARKET, qty=8)
    trades = engine.submit(market)

    assert prices_and_qtys(trades) == [(10.0, 5), (10.5, 3)]
    assert market.qty == 0


# ----------------------------------------------------------------------
# runner
# ----------------------------------------------------------------------

def _all_tests() -> list:
    return [obj for name, obj in list(globals().items()) if name.startswith("test_")]


def main() -> None:
    tests = _all_tests()
    for test in tests:
        test()
        print(f"OK  {test.__name__}")

    print(f"\nTODOS OS TESTES PASSARAM ({len(tests)} testes)")


if __name__ == "__main__":
    main()
