
from __future__ import annotations

from engine.order import Order, OrderType, Side
from engine.matching import MatchingEngine


def test_cancel_remove_ordem_do_meio_da_fila() -> None:
    engine = MatchingEngine()
    a = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    b = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    c = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    for o in (a, b, c):
        engine.submit(o)

    cancelled = engine.cancel(b.id)

    assert cancelled is b
    assert engine.book.get_order(b.id) is None
    assert engine.book.ask_orders() == [a, c]  # a e c mantêm ordem entre si


def test_cancel_ordem_inexistente_retorna_none() -> None:
    engine = MatchingEngine()
    assert engine.cancel("nao-existe") is None


def test_cancel_esvazia_nivel_de_preco() -> None:
    engine = MatchingEngine()
    a = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    engine.submit(a)

    engine.cancel(a.id)

    assert engine.book.best_ask() is None
    assert engine.book.ask_levels() == []


def test_modify_so_reduz_qty_mantem_prioridade() -> None:
    engine = MatchingEngine()
    a = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    b = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    engine.submit(a)
    engine.submit(b)

    trades = engine.modify(a.id, new_qty=4)

    assert trades == []
    assert a.qty == 4
    assert engine.book.ask_orders() == [a, b]  # continua na frente


def test_modify_muda_preco_perde_prioridade() -> None:
    engine = MatchingEngine()
    a = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    b = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    engine.submit(a)
    engine.submit(b)

    trades = engine.modify(a.id, new_price=10.5)

    assert trades == []
    moved = engine.book.get_order(a.id)
    assert moved is not None and moved.price == 10.5
    assert engine.book.ask_orders() == [b, moved]  # a foi pro fim


def test_modify_aumenta_qty_perde_prioridade() -> None:
    engine = MatchingEngine()
    a = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    b = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    engine.submit(a)
    engine.submit(b)

    engine.modify(a.id, new_qty=20)

    assert engine.book.ask_orders()[0] is b  # b passou na frente


def test_modify_preserva_id_original() -> None:
    engine = MatchingEngine()
    a = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    engine.submit(a)
    original_id = a.id

    engine.modify(a.id, new_price=11.0)

    assert engine.book.get_order(original_id) is not None
    assert engine.book.get_order(original_id).price == 11.0


def test_modify_com_novo_preco_que_cruza_executa_na_hora() -> None:
    engine = MatchingEngine()
    resting_buy = Order(Side.BUY, OrderType.LIMIT, qty=5, price=9.0)
    sell = Order(Side.SELL, OrderType.LIMIT, qty=5, price=10.0)
    engine.submit(resting_buy)
    engine.submit(sell)

    trades = engine.modify(sell.id, new_price=9.0)

    assert [(t.price, t.qty) for t in trades] == [(9.0, 5)]
    assert engine.book.get_order(sell.id) is None  # totalmente preenchida


def test_modify_ordem_inexistente_levanta_erro() -> None:
    engine = MatchingEngine()
    try:
        engine.modify("nao-existe", new_qty=1)
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass


def test_modify_sem_alterar_nada_nao_faz_nada() -> None:
    engine = MatchingEngine()
    a = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)
    engine.submit(a)

    trades = engine.modify(a.id)  # sem new_price nem new_qty

    assert trades == []
    assert a.qty == 10
    assert a.price == 10.0
    assert engine.book.get_order(a.id) is a  # mesmo objeto, nada mudou


def main() -> None:
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"OK  {test.__name__}")
    print(f"\nTODOS OS TESTES PASSARAM ({len(tests)} testes)")


if __name__ == "__main__":
    main()
