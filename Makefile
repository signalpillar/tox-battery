run-tests:
	tox -- py.test --pep8 tests

run-tests-continuously:
	tox -e py35 -- py.test -vv --pep8 --looponfail tests

upload-to-pypi:
	python setup.py sdist bdist_wheel upload
