PYTHON := python3.6
current_dir := $(shell pwd)

check: check-coding-standards check-tests

check-coding-standards: check-pylint-main check-isort check-pycodestyle

check-pylint-main: venv
	venv/bin/python -m pylint corna

check-pycodestyle: venv
	venv/bin/python -m pycodestyle corna

check-isort: venv
	venv/bin/python -m isort corna --check --diff --skip venv

requirements.txt: venv
	venv/bin/python -m piptools compile --output-file $@ $<

check-tests: venv
	venv/bin/python -m pytest -v

venv: venv/bin/activate

venv/bin/activate:
	test -d venv || $(PYTHON) -m venv venv
	# we need this version of pip to work with piptools
	venv/bin/python -m pip install pip==20.0.2
	# install piptools
	venv/bin/python -m pip install pip-tools
	venv/bin/python -m pip install -r $< --progress-bar off
	touch $@

.PHONY: check check-coding-standards check-pylint-main check-isort \
	check-tests venv
