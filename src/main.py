import json
import os
import pprint
import sys

from tatsu import parse
from tatsu.util import asjson

f = open(os.environ.get("AGO_GRAMMAR", "./src/Ago.g4"), "r")
GRAMMAR = f.read()
f.close()


def main(file):
    with open(file, "r") as f:
        ast = parse(GRAMMAR, f.read())
        print("PPRINT")
        pprint.pprint(ast, indent=2, width=20)
        print()

        print("JSON")
        print(json.dumps(asjson(ast), indent=2))
        print()


if __name__ == "__main__":
    main(sys.argv[1])
