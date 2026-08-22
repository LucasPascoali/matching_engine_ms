from engine.order import Order, OrderType, PegReference, Side

# --- Limit order -------------------------------------------------------
o = Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=100, price=10.0)
assert o.side == Side.BUY
assert o.order_type == OrderType.LIMIT
assert o.qty == 100
assert o.price == 10.0
print("OK: limit buy")

o = Order(side=Side.SELL, order_type=OrderType.LIMIT, qty=50, price=20.5)
assert o.side == Side.SELL
assert o.price == 20.5
print("OK: limit sell")

# --- Market order --------------------------------------------------------
o = Order(side=Side.BUY, order_type=OrderType.MARKET, qty=150)
assert o.price is None
print("OK: market buy")

o = Order(side=Side.SELL, order_type=OrderType.MARKET, qty=200)
assert o.price is None
print("OK: market sell")

# --- Pegged order -------------------------------------------------------
o = Order(side=Side.BUY, order_type=OrderType.PEGGED, qty=150, peg_reference=PegReference.BID)
assert o.peg_reference == PegReference.BID
assert o.price is None
print("OK: pegged to bid")

o = Order(side=Side.SELL, order_type=OrderType.PEGGED, qty=80, peg_reference=PegReference.OFFER)
assert o.peg_reference == PegReference.OFFER
print("OK: pegged to offer")

# --- order_id e original_qty --------------------------------------------
o1 = Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=10, price=10.0)
o2 = Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=10, price=10.0)
assert o1.order_id != o2.order_id
print("OK: order_id unico")

o = Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=100, price=10.0)
o.qty = 40
assert o.original_qty == 100
print("OK: original_qty preservado apos execucao parcial")

# --- Erros de validacao ---------------------------------------------------
try:
    Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=0, price=10.0)
    raise AssertionError("deveria ter lancado erro: qty zero")
except ValueError:
    print("OK: erro esperado - qty zero")

try:
    Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=-5, price=10.0)
    raise AssertionError("deveria ter lancado erro: qty negativa")
except ValueError:
    print("OK: erro esperado - qty negativa")

try:
    Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=10)
    raise AssertionError("deveria ter lancado erro: limit sem price")
except ValueError:
    print("OK: erro esperado - limit sem price")

try:
    Order(side=Side.BUY, order_type=OrderType.MARKET, qty=10, price=10.0)
    raise AssertionError("deveria ter lancado erro: market com price")
except ValueError:
    print("OK: erro esperado - market com price")

try:
    Order(side=Side.BUY, order_type=OrderType.PEGGED, qty=10)
    raise AssertionError("deveria ter lancado erro: pegged sem peg_reference")
except ValueError:
    print("OK: erro esperado - pegged sem peg_reference")

try:
    Order(side=Side.BUY, order_type=OrderType.LIMIT, qty=10, price=10.0, peg_reference=PegReference.BID)
    raise AssertionError("deveria ter lancado erro: limit com peg_reference")
except ValueError:
    print("OK: erro esperado - limit com peg_reference")

try:
    Order(side=Side.BUY, order_type=OrderType.MARKET, qty=10, peg_reference=PegReference.OFFER)
    raise AssertionError("deveria ter lancado erro: market com peg_reference")
except ValueError:
    print("OK: erro esperado - market com peg_reference")

print("\nTodos os testes passaram.")
