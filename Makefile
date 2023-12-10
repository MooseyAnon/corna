PYTHON := python3.6
current_dir := $(shell pwd)

check: check-coding-standards check-tests

check-coding-standards: check-pylint-main check-isort check-pycodestyle

check-pylint-main:
	/usr/bin/$(PYTHON) -m pylint corna

check-pycodestyle:
	/usr/bin/$(PYTHON) -m pycodestyle corna

check-isort:
	/usr/bin/$(PYTHON) -m isort corna --check --diff --skip venv

check-tests:
	/usr/bin/$(PYTHON) -m pytest -v

venv: venv/bin/activate

venv/bin/activate: requirements.txt
	venv/bin/python -m pip install -r $< --progress-bar off
	touch $@

requirements.txt: | requirements.in
	test -d venv || $(PYTHON) -m venv venv
	# we need this version of pip to work with piptools
	venv/bin/python -m pip install --upgrade pip
	# install piptools
	venv/bin/python -m pip install pip-tools
	# generate requirements.txt
	venv/bin/python -m piptools compile --output-file $@ $<

.PHONY: check check-coding-standards check-pylint-main check-isort \
	check-tests venv requirements.txt venv/bin/activate
