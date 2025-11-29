import tatsu

GRAMMAR = None
with open('./src/Ago.g4') as f:
    GRAMMAR = f.read()

parser = tatsu.compile(GRAMMAR)

