"""
Entry point module, in case you use `python -m hexrec`.


Why does this file exist, and why __main__? For more info, read:

- https://www.python.org/dev/peps/pep-0338/
- https://docs.python.org/2/using/cmdline.html#cmdoption-m
- https://docs.python.org/3/using/cmdline.html#cmdoption-m
"""
from .cli import main as _main


def main(module_name):
    if module_name == '__main__':
        _main()


main(__name__)
