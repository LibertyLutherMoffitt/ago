import sys


from src.AgoParser import parser
from src.AgoSemanticChecker import AgoSemanticChecker


def main(file):
    with open(file, "r") as f:
        semantics = AgoSemanticChecker()
        parser.parse(f.read() + "\n", semantics=semantics)
        if len(semantics.errors) == 0:
            print("Semantic Check ran -- no errors.")
        else:
            print("ERRORS:")
            for error in semantics.errors:
                print("-", str(error))


if __name__ == "__main__":
    main(sys.argv[1])
