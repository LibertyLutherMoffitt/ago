import subprocess  

# Assumes the rust to be compiled is in input/src.rc and compiles to build/out
def compile():
    subprocess.run(['rustc', './input/src.rc', '-o', './build/out'])
    subprocess.run(['./build/out'])

if __name__ == '__main__':
    compile()