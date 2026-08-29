from engine.order import Order, OrderType, Side
from engine.order_book import OrderBook

# --- Insercao basica e best_bid/best_ask --------------------------------
book = OrderBook()
book.add_order(Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=200, price=10.0))
book.add_order(Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=100, price=9.99))
book.add_order(Order(side=Side.SELL, order_type=OrderType.LIMIT, qty=100, price=10.5))

assert book.best_bid() == 10.0
assert book.best_ask() == 10.5
print("OK: insercao, best_bid e best_ask")

# --- print_book bate com o exemplo do enunciado -------------------------
print()
book.print_book()
print()

# --- FIFO dentro do mesmo nivel de preco (nao agregado) ------------------
book2 = OrderBook()
o1 = Order(side=Side.SELL, order_type=OrderType.LIMIT, qty=100, price=20.0)
o2 = Order(side=Side.SELL, order_type=OrderType.LIMIT, qty=200, price=20.0)
book2.add_order(o1)
book2.add_order(o2)

asks = book2.ask_orders()
assert len(asks) == 2, "nao deveria agregar ordens do mesmo preco"
assert asks[0].id == o1.id, "mais antiga deve vir primeiro"
assert asks[1].id == o2.id
print("OK: FIFO preservado, ordens do mesmo preco nao sao agregadas")

# --- Melhor preco ordena corretamente com varios niveis -------------------
book3 = OrderBook()
book3.add_order(Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=10, price=9.0))
book3.add_order(Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=10, price=11.0))
book3.add_order(Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=10, price=10.0))
bid_prices = [o.price for o in book3.bid_orders()]
assert bid_prices == [11.0, 10.0, 9.0], "bids devem vir do maior para o menor preco"
print("OK: ordenacao de bids do melhor para o pior preco")

book3.add_order(Order(side=Side.SELL, order_type=OrderType.LIMIT, qty=10, price=15.0))
book3.add_order(Order(side=Side.SELL, order_type=OrderType.LIMIT, qty=10, price=13.0))
book3.add_order(Order(side=Side.SELL, order_type=OrderType.LIMIT, qty=10, price=14.0))
ask_prices = [o.price for o in book3.ask_orders()]
assert ask_prices == [13.0, 14.0, 15.0], "asks devem vir do menor para o maior preco"
print("OK: ordenacao de asks do melhor para o pior preco")

book4 = OrderBook()
# --- get_order por id ------------------------------------------------------
o = Order(side=Side.SELL, order_type=OrderType.LIMIT, qty=30, price=12.0)
book4.add_order(o)
assert book4.get_order(o.id) is o
assert book4.get_order("id_que_nao_existe") is None
print("OK: get_order por id")

# --- book vazio nao quebra ---------------------------------------------
book5 = OrderBook()
assert book5.best_bid() is None
assert book5.best_ask() is None
assert book5.bid_orders() == []
assert book5.ask_orders() == []
book5.print_book()
print("OK: book vazio")

# --- market e pegged ainda nao sao suportados no book (ainda sem matching) -
try:
    book5.add_order(Order(side=Side.BUY, order_type=OrderType.MARKET, qty=10))
    raise AssertionError("deveria ter lancado NotImplementedError para market")
except NotImplementedError:
    print("OK: erro esperado - market order ainda nao suportada no book")

print("\nTodos os testes passaram.")
