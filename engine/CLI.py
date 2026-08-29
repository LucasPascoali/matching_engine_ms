"""CLI/REPL da Matching Engine.

Uso interativo:
    $ python main.py
    >>> limit buy 100 10.5
    Order created: buy 100 @ 10.5 ID_1
    >>> cancel order ID_1
    Order cancelled
    >>> print book
    ...

Também aceita comandos via stdin (pipe/redirect), uma linha por comando,
o que facilita testes de integração ponta a ponta.

Comandos suportados:
    limit buy|sell <qty> <price>
    market buy|sell <qty>
    peg bid|offer buy|sell <qty>
    cancel order <id>
    modify <id> [price=<novo_preco>] [qty=<nova_qty>]
    print book         (alias: book)
    help
    quit / exit
"""

from __future__ import annotations

import sys

from engine.matching import MatchingEngine
from engine.order import Order, OrderType, PegReference, Side

HELP_TEXT = """\
Comandos disponíveis:
  limit buy|sell <price> <qty>       - envia ordem limit
  market buy|sell <qty>              - envia ordem market (IOC)
  peg bid|offer buy|sell <qty>       - envia ordem pegged
  cancel order <id>                      - cancela ordem por id
  modify <id> [price=<p>] [qty=<q>]      - altera preço e/ou qty
  print book                             - imprime o order book
  help                                   - mostra esta mensagem
  quit / exit                            - encerra
"""

_SIDE_MAP = {"buy": Side.BUY, "sell": Side.SELL}
_PEG_MAP = {"bid": PegReference.BID, "offer": PegReference.OFFER}


class CommandError(Exception):
    """Erro de sintaxe/uso de um comando, reportado ao usuário sem crashar o REPL."""


def _parse_limit(args: list[str]) -> Order:
    # args: [side, price, qty]
    if len(args) != 3:
        raise CommandError("uso: limit buy|sell <price> <qty>")

    side_str, price_str, qty_str = args

    side = _SIDE_MAP.get(side_str.lower())
    if side is None:
        raise CommandError(f"side inválido: '{side_str}' (use buy/sell)")

    try:
        qty = int(qty_str)
    except ValueError:
        raise CommandError(f"qty inválida: '{qty_str}'")

    try:
        price = float(price_str)
    except ValueError:
        raise CommandError(f"price inválido: '{price_str}'")

    return Order(side=side, order_type=OrderType.LIMIT, qty=qty, price=price)


def _parse_market(args: list[str]) -> Order:
    # args: [side, qty]
    if len(args) != 2:
        raise CommandError("uso: market buy|sell <qty>")

    side_str, qty_str = args

    side = _SIDE_MAP.get(side_str.lower())
    if side is None:
        raise CommandError(f"side inválido: '{side_str}' (use buy/sell)")

    try:
        qty = int(qty_str)
    except ValueError:
        raise CommandError(f"qty inválida: '{qty_str}'")

    return Order(side=side, order_type=OrderType.MARKET, qty=qty)


def _parse_peg(args: list[str]) -> Order:
    # args: [bid|offer, side, qty]
    if len(args) != 3:
        raise CommandError("uso: peg bid|offer buy|sell <qty>")

    peg_str, side_str, qty_str = args

    peg_reference = _PEG_MAP.get(peg_str.lower())
    if peg_reference is None:
        raise CommandError(f"peg_reference inválido: '{peg_str}' (use bid/offer)")

    side = _SIDE_MAP.get(side_str.lower())
    if side is None:
        raise CommandError(f"side inválido: '{side_str}' (use buy/sell)")

    try:
        qty = int(qty_str)
    except ValueError:
        raise CommandError(f"qty inválida: '{qty_str}'")

    return Order(
        side=side,
        order_type=OrderType.PEGGED,
        qty=qty,
        peg_reference=peg_reference,
    )


def _parse_modify(tokens: list[str]) -> tuple[str, float | None, int | None]:
    # tokens já sem o "modify" inicial: [id, key=val, key=val, ...]
    if not tokens:
        raise CommandError("uso: modify <id> [price=<p>] [qty=<q>]")

    order_id, *rest = tokens
    new_price: float | None = None
    new_qty: int | None = None

    for token in rest:
        if "=" not in token:
            raise CommandError(f"argumento inválido: '{token}' (use price=<p> ou qty=<q>)")
        key, _, value = token.partition("=")
        key = key.strip().lower()
        value = value.strip()

        if key == "price":
            try:
                new_price = float(value)
            except ValueError:
                raise CommandError(f"price inválido: '{value}'")
        elif key == "qty":
            try:
                new_qty = int(value)
            except ValueError:
                raise CommandError(f"qty inválida: '{value}'")
        else:
            raise CommandError(f"campo desconhecido: '{key}' (use price/qty)")

    if new_price is None and new_qty is None:
        raise CommandError("modify exige ao menos price=<p> ou qty=<q>")

    return order_id, new_price, new_qty


def _format_order_created(order: Order) -> str:
    price = "no peg reference" if order.price is None else f"{order.price:g}"
    return f"Order created: {order.side.value} {order.qty} @ {price} {order.id}"


def handle_command(engine: MatchingEngine, line: str) -> bool:
    """Processa uma linha de comando. Retorna False se o REPL deve encerrar."""
    line = line.strip()
    if not line or line.startswith("#"):
        return True

    tokens = line.split()
    cmd, *args = tokens
    cmd = cmd.lower()

    try:
        if cmd in ("quit", "exit"):
            return False

        elif cmd == "help":
            print(HELP_TEXT, end="")

        elif cmd == "limit":
            order = _parse_limit(args)
            engine.submit(order)
            print(_format_order_created(order))

        elif cmd == "market":
            order = _parse_market(args)
            #print(_format_order_created(order)) sem printar ordens market, pois não ficam no book
            engine.submit(order)

        elif cmd == "peg":
            order = _parse_peg(args)
            engine.submit(order)
            print(_format_order_created(order))

        elif cmd == "cancel":
            # uso: cancel order <id>
            if len(args) != 2 or args[0].lower() != "order":
                raise CommandError("uso: cancel order <id>")
            order_id = args[1]
            cancelled = engine.cancel(order_id)
            if cancelled is None:
                print(f"erro: ordem {order_id} não encontrada")
            else:
                print("Order cancelled")

        elif cmd == "modify":
            order_id, new_price, new_qty = _parse_modify(args)
            engine.modify(order_id, new_price=new_price, new_qty=new_qty)
            print(f"OK: ordem {order_id} modificada")

        elif cmd == "print" or cmd == "book":
            # aceita tanto "print book" quanto "book"
            if cmd == "print" and (not args or args[0].lower() != "book"):
                raise CommandError("uso: print book")
            engine.book.print_book()

        else:
            print(f"comando desconhecido: '{cmd}' (digite 'help')")

    except CommandError as exc:
        print(f"erro: {exc}")
    except ValueError as exc:
        # erros de validação vindos de Order/OrderBook/MatchingEngine
        print(f"erro: {exc}")

    return True


def main() -> None:
    engine = MatchingEngine()
    interactive = sys.stdin.isatty()

    if interactive:
        print("Matching Engine — digite 'help' para ver os comandos, 'quit' para sair.")

    while True:
        if interactive:
            try:
                line = input(">>> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
        else:
            line = sys.stdin.readline()
            if line == "":
                break

        if not handle_command(engine, line):
            break


if __name__ == "__main__":
    main()