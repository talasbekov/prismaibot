#!/usr/bin/env bash

set -e
set -x

coverage run -m pytest tests/
coverage report
rm -rf htmlcov
coverage html -d htmlcov --title "${@-coverage}"
