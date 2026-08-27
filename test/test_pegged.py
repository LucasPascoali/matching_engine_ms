from __future__ import annotations

from engine.order import Order, OrderType, PegReference, Side
from engine.matching import MatchingEngine


def test_pegged_sem_referencia_fica_pendente() -> None:
    engine = MatchingEngine()
    p = Order(Side.BUY, OrderType.PEGGED, qty=10, peg_reference=PegReference.BID)

    trades = engine.submit(p)

    assert trades == []
    assert p.price is None
    assert engine.book.get_order(p.id) is None  # não entrou no book


def test_pegged_precifica_quando_referencia_aparece() -> None:
    engine = MatchingEngine()
    p = Order(Side.BUY, OrderType.PEGGED, qty=10, peg_reference=PegReference.BID)
    engine.submit(p)  # ainda pendente

    ref_buy = Order(Side.BUY, OrderType.LIMIT, qty=5, price=9.0)
    engine.submit(ref_buy)  # cria o primeiro best_bid

    assert p.price == 9.0
    assert engine.book.get_order(p.id) is p


def test_pegged_reprecifica_quando_topo_muda() -> None:
    engine = MatchingEngine()
    engine.submit(Order(Side.BUY, OrderType.LIMIT, qty=5, price=9.0))
    p = Order(Side.BUY, OrderType.PEGGED, qty=10, peg_reference=PegReference.BID)
    engine.submit(p)
    assert p.price == 9.0

    engine.submit(Order(Side.BUY, OrderType.LIMIT, qty=3, price=9.5))

    assert p.price == 9.5
    assert engine.book.get_order(p.id) is p


def test_pegged_reprice_que_cruza_gera_trade() -> None:
    engine = MatchingEngine()
    engine.submit(Order(Side.SELL, OrderType.LIMIT, qty=10, price=9.5))
    p = Order(Side.BUY, OrderType.PEGGED, qty=10, peg_reference=PegReference.BID)
    engine.submit(p)  # sem bids ainda, fica pendente

    resting_buy = Order(Side.BUY, OrderType.LIMIT, qty=5, price=9.5)
    trades = engine.submit(resting_buy)  # cruza contra o sell 9.5

    assert [(t.price, t.qty) for t in trades] == [(9.5, 5)]
    # agora best_bid não existe mais (resting_buy foi consumida), p
    # deveria ficar pendente de novo
    assert p.price is None
    assert engine.book.get_order(p.id) is None


def test_fill_parcial_no_mesmo_nivel_com_ordem_real_nao_reprecifica() -> None:
    # há uma LIMIT real no mesmo nível: o preço de referência não é
    # sustentado só pela pegged, então ele não deveria mudar num fill
    # que não esvazia o nível.
    engine = MatchingEngine()
    a = Order(Side.SELL, OrderType.LIMIT, qty=10, price=15.0)
    engine.submit(a)
    p = Order(Side.SELL, OrderType.PEGGED, qty=10, peg_reference=PegReference.OFFER)
    engine.submit(p)
    assert p.price == 15.0

    buy = Order(Side.BUY, OrderType.LIMIT, qty=5, price=15.0)
    engine.submit(buy)  # consome metade de `a` (FIFO), `p` não é tocada

    assert a.qty == 5
    assert p.qty == 10
    assert p.price == 15.0  # nível 15.0 continua tendo `a`, preço não muda


def test_fill_que_esgota_ordem_real_faz_pegged_reprecificar() -> None:
    # caso que estava com bug: quando a única ordem "real" do nível é
    # consumida e só sobra a pegged, ela deve parar de sustentar o
    # próprio preço e voltar a buscar a referência real do book.
    engine = MatchingEngine()
    a = Order(Side.SELL, OrderType.LIMIT, qty=10, price=15.0)   # referência real mais alta
    b = Order(Side.SELL, OrderType.PEGGED, qty=10, peg_reference=PegReference.OFFER)
    c = Order(Side.SELL, OrderType.LIMIT, qty=10, price=10.0)   # melhor nível
    for o in (a, b, c):
        engine.submit(o)

    assert b.price == 10.0  # reprecificou quando `c` chegou (novo best_ask)

    # consome `c` inteira; sobra só `b` (pegged) no nível 10.0
    engine.submit(Order(Side.BUY, OrderType.LIMIT, qty=10, price=10.0))

    assert engine.book.get_order(c.id) is None
    # com `c` fora, o único preço "real" restante é o de `a` (15.0);
    # `b` não deve mais sustentar o próprio preço de 10.0
    assert b.price == 15.0
    assert engine.book.get_order(b.id) is b


def test_multiplas_pegged_no_mesmo_nivel_sem_ordem_real() -> None:
    # duas pegged sozinhas no mesmo nível, sem nenhuma LIMIT por trás:
    # nenhuma das duas pode sustentar o preço da outra.
    engine = MatchingEngine()
    real = Order(Side.SELL, OrderType.LIMIT, qty=10, price=20.0)
    engine.submit(real)

    p1 = Order(Side.SELL, OrderType.PEGGED, qty=5, peg_reference=PegReference.OFFER)
    p2 = Order(Side.SELL, OrderType.PEGGED, qty=5, peg_reference=PegReference.OFFER)
    engine.submit(p1)
    engine.submit(p2)
    assert p1.price == 20.0 and p2.price == 20.0

    # remove a única ordem real do book
    engine.cancel(real.id)

    # sem `real`, não deveria sobrar nenhuma referência válida (só
    # existem as duas pegged) -> ambas ficam pendentes, fora do book
    assert p1.price is None
    assert p2.price is None
    assert engine.book.get_order(p1.id) is None
    assert engine.book.get_order(p2.id) is None
    assert engine.book.best_ask() is None


def test_cancel_pegged_pendente() -> None:
    engine = MatchingEngine()
    p = Order(Side.BUY, OrderType.PEGGED, qty=10, peg_reference=PegReference.BID)
    engine.submit(p)  # pendente, nunca entrou no book

    cancelled = engine.cancel(p.id)

    assert cancelled is p
    assert engine.cancel(p.id) is None  # já foi removida


def test_cancel_pegged_resting() -> None:
    engine = MatchingEngine()
    engine.submit(Order(Side.BUY, OrderType.LIMIT, qty=5, price=9.0))
    p = Order(Side.BUY, OrderType.PEGGED, qty=10, peg_reference=PegReference.BID)
    engine.submit(p)
    assert engine.book.get_order(p.id) is p

    cancelled = engine.cancel(p.id)

    assert cancelled is p
    assert engine.book.get_order(p.id) is None


def test_modify_pegged_rejeita_new_price() -> None:
    engine = MatchingEngine()
    engine.submit(Order(Side.BUY, OrderType.LIMIT, qty=5, price=9.0))
    p = Order(Side.BUY, OrderType.PEGGED, qty=10, peg_reference=PegReference.BID)
    engine.submit(p)

    try:
        engine.modify(p.id, new_price=9.5)
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass


def test_modify_pegged_reduz_qty_mantem_prioridade() -> None:
    engine = MatchingEngine()
    p = Order(Side.BUY, OrderType.PEGGED, qty=10, peg_reference=PegReference.BID)
    other = Order(Side.BUY, OrderType.PEGGED, qty=10, peg_reference=PegReference.BID)
    engine.submit(Order(Side.BUY, OrderType.LIMIT, qty=5, price=9.0))
    engine.submit(p)
    engine.submit(other)

    trades = engine.modify(p.id, new_qty=4)

    assert trades == []
    assert p.qty == 4
    assert p.price == 9.0
    ids_in_order = [o.id for o in engine.book.bid_orders()]
    assert ids_in_order.index(p.id) < ids_in_order.index(other.id)  # p continua na frente de other


def main() -> None:
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"OK  {test.__name__}")
    print(f"\nTODOS OS TESTES PASSARAM ({len(tests)} testes)")


if __name__ == "__main__":
    main()

