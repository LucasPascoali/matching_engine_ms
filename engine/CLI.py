"""CLI/REPL da Matching Engine.

Uso interativo:
    $ python main.py
    > buy limit 100 10.5
    > sell limit 50 10.5
    Trade, price: 10.5, qty: 50
    > book
    ...

Também aceita comandos via stdin (pipe/redirect), uma linha por comando,
o que facilita testes de integração ponta a ponta.

Comandos suportados:
    buy|sell limit <qty> <price>
    buy|sell market <qty>
    buy|sell pegged <qty> bid|offer
    cancel <id>
    modify <id> [price=<novo_preco>] [qty=<nova_qty>]
    book               (alias: print book, print)
    help
    quit / exit
"""

from __future__ import annotations

import sys

from engine.matching import MatchingEngine
from engine.order import Order, OrderType, PegReference, Side

HELP_TEXT = """\
Comandos disponíveis:
  buy|sell limit <qty> <price>       - envia ordem limit
  buy|sell market <qty>              - envia ordem market (IOC)
  buy|sell pegged <qty> bid|offer    - envia ordem pegged
  cancel <id>                            - cancela ordem por id
  modify <id> [price=<p>] [qty=<q>]      - altera preço e/ou qty
  book                                   - imprime o order book
  help                                   - mostra esta mensagem
  quit / exit                            - encerra
"""

_SIDE_MAP = {"buy": Side.BUY, "sell": Side.SELL}
_TYPE_MAP = {
    "limit": OrderType.LIMIT,
    "market": OrderType.MARKET,
    "pegged": OrderType.PEGGED,
}
_PEG_MAP = {"bid": PegReference.BID, "offer": PegReference.OFFER}


class CommandError(Exception):
    """Erro de sintaxe/uso de um comando, reportado ao usuário sem crashar o REPL."""


def _parse_add(tokens: list[str]) -> Order:
    # tokens: [side, type, qty, ...resto]
    if len(tokens) < 3:
        raise CommandError(
            "uso: buy|sell limit|market|pegged <qty> [price|bid|offer]"
        )

    side_str, type_str, qty_str, *rest = tokens

    side = _SIDE_MAP.get(side_str.lower())
    if side is None:
        raise CommandError(f"side inválido: '{side_str}' (use buy/sell)")

    order_type = _TYPE_MAP.get(type_str.lower())
    if order_type is None:
        raise CommandError(
            f"tipo inválido: '{type_str}' (use limit/market/pegged)"
        )

    try:
        qty = int(qty_str)
    except ValueError:
        raise CommandError(f"qty inválida: '{qty_str}'")

    price: float | None = None
    peg_reference: PegReference | None = None

    if order_type == OrderType.LIMIT:
        if not rest:
            raise CommandError("ordem limit exige price: buy limit <qty> <price>")
        try:
            price = float(rest[0])
        except ValueError:
            raise CommandError(f"price inválido: '{rest[0]}'")

    elif order_type == OrderType.MARKET:
        if rest:
            raise CommandError("ordem market não deve receber price")

    elif order_type == OrderType.PEGGED:
        if not rest:
            raise CommandError(
                "ordem pegged exige referência: buy pegged <qty> bid|offer"
            )
        peg_reference = _PEG_MAP.get(rest[0].lower())
        if peg_reference is None:
            raise CommandError(f"peg_reference inválido: '{rest[0]}' (use bid/offer)")

    return Order(
        side=side,
        order_type=order_type,
        qty=qty,
        price=price,
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

        elif cmd == "buy" or cmd == "sell":
            order = _parse_add([cmd] + args)
            engine.submit(order)
            print(f"OK: ordem {order.id} recebida")

        elif cmd == "cancel":
            if not args:
                raise CommandError("uso: cancel <id>")
            cancelled = engine.cancel(args[0])
            if cancelled is None:
                print(f"erro: ordem {args[0]} não encontrada")
            else:
                print(f"OK: ordem {cancelled.id} cancelada")

        elif cmd == "modify":
            order_id, new_price, new_qty = _parse_modify(args)
            engine.modify(order_id, new_price=new_price, new_qty=new_qty)
            print(f"OK: ordem {order_id} modificada")

        elif cmd in ("book", "print"):
            # aceita tanto "book" quanto "print book"
            if cmd == "print" and args and args[0].lower() != "book":
                raise CommandError("uso: book  (ou: print book)")
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
                line = input("> ")
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
