"""List all available codec modules.

(c) Copyright 2005, Marc-Andre Lemburg (mal@lemburg.com).

    Licensed to PSF under a Contributor Agreement.

"""

import codecs
import encodings
import os

_debug = 0


def listcodecs(dir):
    names = []
    for filename in os.listdir(dir):
        if filename[-3:] != ".py":
            continue
        name = filename[:-3]
        # Check whether we've found a true codec
        try:
            codecs.lookup(name)
        except LookupError:
            # Codec not found
            continue
        except Exception as reason:  # noqa: BLE001
            # Probably an error from importing the codec; still it's
            # a valid code name
            if _debug:
                print(f"* problem importing codec {name!r}: {reason}")
        names.append(name)
    return names


if __name__ == "__main__":
    names = listcodecs(encodings.__path__[0])
    names.sort()
    print("all_codecs = [")
    for name in names:
        print(f"    {name!r},")
    print("]")
