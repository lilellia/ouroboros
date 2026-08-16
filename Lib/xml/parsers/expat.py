"""Interface to the Expat non-validating XML parser."""

from pyexpat import *
import sys

# provide pyexpat submodules as xml.parsers.expat submodules
sys.modules["xml.parsers.expat.model"] = model
sys.modules["xml.parsers.expat.errors"] = errors
