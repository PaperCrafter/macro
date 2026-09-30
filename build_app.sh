#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON="/usr/bin/python3"
SCRIPT="$DIR/../Resources/macro_app.py"
exec $PYTHON "$SCRIPT" "$@"
