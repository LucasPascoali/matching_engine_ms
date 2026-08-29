# tests/__main__.py
import importlib
import pkgutil
import sys

def main():
    package = "tests"
    for _, modname, _ in pkgutil.iter_modules(__import__(package).__path__):
        if modname.startswith("test_") or modname.startswith("terst_"):
            module = importlib.import_module(f"{package}.{modname}")
            if hasattr(module, "main"):
                module.main()

if __name__ == "__main__":
    main()