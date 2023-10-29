PYTHON := python3.6
current_dir := $(shell pwd)

check: check-coding-standards

check-coding-standards: check-pylint-main

check-pylint-main: venv
	venv/bin/python -m pylint corna

requirements.txt: venv
	venv/bin/python -m piptools compile --output-file $@ $<

venv: venv/bin/activate

venv/bin/activate:
	test -d venv || $(PYTHON) -m venv venv
	# we need this version of pip to work with piptools
	venv/bin/python -m pip install pip==20.0.2
	# install piptools
	venv/bin/python -m pip install pip-tools
	venv/bin/python -m pip install -r $< --progress-bar off
	touch $@
