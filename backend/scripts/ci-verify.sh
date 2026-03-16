#!/usr/bin/env bash

set -euo pipefail
set -x

python app/tests_pre_start.py
ruff check app tests
mypy app tests
bash scripts/prestart.sh
bash scripts/test.sh "${@}"
