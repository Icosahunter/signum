setup:
    #!/usr/bin/env sh
    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install -r requirements.txt

build: setup
    #!/usr/bin/env sh
    source .venv/bin/activate
    rm -r -f dist
    python3 -m build

install: build
    python3 -m pip install --force-reinstall ./dist/*.whl

test: setup
    #!/usr/bin/env sh
    source .venv/bin/activate
    cd test
    rm -r -f dist
    python3 ../src/signum/main.py
