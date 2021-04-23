#!/bin/bash

. venv/bin/activate
find . -type f | grep -v venv | grep '\.py$' | xargs -I {} mypy {}
