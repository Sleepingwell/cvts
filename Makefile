.PHONY: initial-setup venv sphinx-doc clean clean-build clean-sphinx-doc

initial-setup: setup-valhalla venv sphinx-doc

setup-valhalla:
	./setup-valhalla.sh

venv: clean
	virtualenv -p python3 venv
	. ./venv/bin/activate && pip install -e .[dev]

sphinx-doc:
	. ./venv/bin/activate \
	    && cd doc && sphinx-apidoc -f -o ./source ../cvts \
	    && rm -f ./source/modules.rst
	echo "   :imported-members:" >> doc/source/cvts.rst
	echo "   :imported-members:" >> doc/source/cvts.tasks.rst
	. ./venv/bin/activate \
	    && cd doc/source \
	    && PYTHONPATH=$(CURDIR) sphinx-build -b html . ../build
	if [ ! -d ../cvts-pages ]; then git worktree add ../cvts-pages gh-pages; fi
	cp -r doc/build/* ../cvts-pages/ && \
	    cd ../cvts-pages && \
	    git add -A && \
	    git commit -m "Updates of Documenation."

push-doc:
	git push -f origin gh-pages

clean: clean-build clean-sphinx-doc
	find . -name '__pycache__' -type d -exec rm -rf {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

clean-build:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info

clean-sphinx-doc:
	rm -rf doc/build
	rm -f doc/source/cvts*
