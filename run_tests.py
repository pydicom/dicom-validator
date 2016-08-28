#! /usr/bin/env python
import sys
import unittest


def run_tests():
    test_suite = unittest.TestLoader().discover('dcm_spec_tools')
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    sys.exit(0 if run_tests() else 1)
