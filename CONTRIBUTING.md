# Contributing to dicom-validator

We welcome any contributions that help to improve `dicom-validator` for the community.
Contributions may include bug reports, bug fixes, new features, infrastructure enhancements, or
documentation updates.

## How to contribute

### Reporting Bugs

If you think you found a bug in `dicom-validator`, you can [create an issue](https://help.github.com/articles/creating-an-issue/).
Before filing the bug, please check, if it still exists in the [main branch](https://github.com/pydicom/dicom-validator).
If you can reproduce the problem, please provide enough information so that it can be reproduced.
This includes:
  * the Python version
  * the installed `pydicom` version
  * if possible, an anonymized DICOM file that can be used to reproduce the problem
  * the stack trace in case of an unexpected exception

### Proposing Enhancements

If you are missing some feature, or have an idea for improving the current behavior,
please create a respective issue. This can be used to discuss if and how this can be implemented.

### Contributing Code

The preferred workflow for contributing code is to
[fork](https://help.github.com/articles/fork-a-repo/) the [repository](https://github.com/pydicom/dicom-validator)
on GitHub, clone it, develop on a feature branch, and
[create a pull request](https://help.github.com/articles/creating-a-pull-request-from-a-fork) when done.
There are a few things to consider for contributing code:
  * We ensure a consistent coding style by using [black](https://pypi.org/project/black/) auto-format in a
    pre-commit hook; you can locally install
    [pre-commit](https://pypi.org/project/pre-commit/) to run the linter tests on check-in or on demand (`pre-commit run --all-files`).
  * Use [NumPy-style docstrings](https://numpydoc.readthedocs.io/en/latest/format.html) to document new public classes or methods.
  * Provide unit tests for bug fixes or new functionality - check the existing tests for examples.
  * Provide meaningful commit messages - it is ok to amend the commits to improve the comments.
  * Check that the automatic GitHub Action CI tests all pass for your pull request.
  * Be ready to adapt your changes after a code review.

### Contributing Documentation
The documentation is written as
[ReStructured Text (rst)](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
and located in *doc/source*.
[Read the Docs](https://readsthedocs.com/) creates HTML pages from these sources and from the docstrings
in the Python files using [sphinx](https://www.sphinx-doc.org) and publishes them.

If you want to improve the documentation, you are very welcome to adapt the documentation sources and/or
the docstrings and create a respective pull request. A preview of the documentation generated from each pull request
is provided by *Read the Docs*, linked to from the pull request.

To build the documentation locally, you first have to install the needed dependencies:
```
python -m pip install dicom-validator[docs]
```
Now you can change into the *doc* directory and build the documentation:
```
cd doc
python -m sphinx -T -W --keep-going -b html -d _build/doctrees . html
```
The created documentation will be located under *doc/html*.
