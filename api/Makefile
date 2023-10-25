
# Default target executed when no arguments are given to make.
all: help

lint:
	black . --check
	isort . --check

format:
	black .
	isort .

test:
	python -m unittest

######################
# HELP
######################

help:
	@echo '----'
	@echo 'format                       - run code formatters'
	@echo 'lint                         - run linters'
	@echo 'test                         - run unit tests'
