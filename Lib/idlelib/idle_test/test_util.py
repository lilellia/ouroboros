"""Test util, coverage 100%"""

from idlelib import util
import unittest


class UtilTest(unittest.TestCase):
    def test_extensions(self):
        for extension in (".pyi", ".py", ".pyw"):
            self.assertIn(extension, util.py_extensions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
