from setuptools import setup, find_packages

setup(
    name='cvts',
    description='Tools for working with commercial vehicles GPS traces in Vietnam',
    author='Simon Knapp',
    author_email='simon.knapp@csiro.au',
    version='0.0.2',
    python_requires='>=3',
    packages=find_packages(),
    scripts=[
        'bin/anonymizeregos',
        'bin/collectionnames',
        'bin/createpgdb',
        'bin/csv2json',
        'bin/json2geojson',
        'bin/processall',
        'bin/processtraces',
        'bin/testmongoconnection'],
    install_requires=[
        'dataclasses',
        'luigi',
        'nptyping',
        'numpy',
        'pandas',
        'pyshp',
        'psycopg2-binary', # couldn't get 'non-binary' to install.
        'scipy',
        'shapely',
        'sklearn',
        'sqlalchemy',
        'tqdm'],
    extras_require={
        "dev": [
            "ipython",
            "pytest",
            "sphinx",
            "sphinx-autodoc-typehints"],
        "mongo": [
            "pymongo"]}
)
