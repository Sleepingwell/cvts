DOC_BUILD_DIR=/tmp/cvts-pages

.PHONY: initial-setup setup-valhalla venv sphinx-doc push-doc clean

initial-setup: setup-valhalla venv sphinx-doc

setup-valhalla:
	./setup-valhalla.sh

venv: clean
	rm -rf venv
	virtualenv -p python3 venv
	. ./venv/bin/activate && pip install -e .[dev]

sphinx-doc: clean-sphinx-doc
	. ./venv/bin/activate \
	    && cd doc && sphinx-apidoc -f -o ./source ../cvts \
	    && rm -f ./source/modules.rst
	echo "   :imported-members:" >> doc/source/cvts.rst
	echo "   :imported-members:" >> doc/source/cvts.tasks.rst
	. ./venv/bin/activate \
	    && cd doc/source \
	    && PYTHONPATH=$(CURDIR) sphinx-build -b html . ../build

push-doc: sphinx-doc
	if [ ! -d $(DOC_BUILD_DIR) ]; then git worktree add $(DOC_BUILD_DIR) gh-pages; fi
	cp -r doc/build/* $(DOC_BUILD_DIR) && \
	    cd $(DOC_BUILD_DIR) && \
	    git add -A && \
	    git commit -m "Updates of Documenation."
	git push -f origin gh-pages
	rm -rf $(DOC_BUILD_DIR)
	git worktree prune

clean: clean-sphinx-doc
	rm -rf build/ dist/ *.egg-info
	find . -name '__pycache__' -type d -exec rm -rf {} +
	find . -type f \( -iname '*.pyc' -o -iname '*.pyo' -o -iname '*~' \) -exec rm -f {} +

clean-sphinx-doc:
	rm -rf doc/build doc/source/cvts* $(DOC_BUILD_DIR)
