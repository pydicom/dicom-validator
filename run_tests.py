#! /usr/bin/env python
import sys
import unittest

if __name__ == '__main__':
    test_suite = unittest.TestLoader().discover('dcm_spec_tools')
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    sys.exit(0 if result.wasSuccessful() else 1)
