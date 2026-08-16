import re
import sys

# Write the config.c file

never = ["marshal", "_imp", "_ast", "__main__", "builtins", "sys", "gc", "_warnings"]


def makeconfig(infp, outfp, modules, with_ifdef=0):
    m1 = re.compile("-- ADDMODULE MARKER 1 --")
    m2 = re.compile("-- ADDMODULE MARKER 2 --")
    for line in infp:
        outfp.write(line)
        if m1 and m1.search(line):
            m1 = None
            for mod in modules:
                if mod in never:
                    continue
                if with_ifdef:
                    outfp.write(f"#ifndef PyInit_{mod}\n")
                outfp.write(f"extern PyObject* PyInit_{mod}(void);\n")
                if with_ifdef:
                    outfp.write("#endif\n")
        elif m2 and m2.search(line):
            m2 = None
            for mod in modules:
                if mod in never:
                    continue
                outfp.write(f'\t{{"{mod}", PyInit_{mod}}},\n')
    if m1:
        sys.stderr.write("MARKER 1 never found\n")
    elif m2:
        sys.stderr.write("MARKER 2 never found\n")


# Test program.


def test():
    if not sys.argv[3:]:
        print("usage: python makeconfig.py config.c.in outputfile", end=" ")
        print("modulename ...")
        sys.exit(2)
    if sys.argv[1] == "-":
        infp = sys.stdin
    else:
        infp = open(sys.argv[1])  # noqa: SIM115
    if sys.argv[2] == "-":
        outfp = sys.stdout
    else:
        outfp = open(sys.argv[2], "w")  # noqa: SIM115
    makeconfig(infp, outfp, sys.argv[3:])
    if outfp != sys.stdout:
        outfp.close()
    if infp != sys.stdin:
        infp.close()


if __name__ == "__main__":
    test()
