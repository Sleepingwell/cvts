# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sphinx_theme
# import sys
# sys.path.insert(0, os.path.abspath('.'))

os.environ['BUILDING_CVTS_DOC'] = 'True'


# -- Project information -----------------------------------------------------

project = 'cvts'
copyright = '2021, Simon Knapp'
author = 'Simon Knapp'

# The full version, including alpha/beta/rc tags
release = '0.0.2'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx_autodoc_typehints']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "neo_rtd_theme"
html_theme_path = [sphinx_theme.get_html_theme_path(html_theme)]

html_theme = 'agogo'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

# -- Options for intersphinx -------------------------------------------------
intersphinx_mapping = {'python': ('https://docs.python.org/3', None),
                       'numpy': ('https://docs.scipy.org/doc/numpy', None),
                       'pandas': ('http://pandas.pydata.org/pandas-docs/dev', None),
                       'shapely': ('http://shapely.readthedocs.io/en/latest', None)}

# -- Options for autodoc -----------------------------------------------------
autodoc_typehints = "description"
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'private-members': False,
    'inherited-members': False}
