# CVTS

Misc stuff related to the CVTS project.

More complete documentation available [here](https://cvts.github.io/cvts/).



## Contents

- **bin**: Python scripts used in this project.

- **convert.py**: Python script for making sure the example data is
  appropriately anonymised."""

- **cvts**: Python code used in this project, structured as a Python package.

- **doc**: Sphinx documentation. Make this with `make sphinx-doc` (requires
  that you have run `make initial-setup` some time previously) and then access
  it at *doc/build/index.html*

- **Makefile**: Some common tasks.

- **requirements.txt**: Python requirements.

- **setup.py**: Setup script for the python package.

- **setup-valhalla.sh**: Setup script for Valhalla.

- **test.csv**: A test 'track' (can be prepared with *bin/csv2json*).

- **test.json**: The example data contained in *test.csv* converted for input by
  *bin/csv2json*. This is only here for ease of reference.

- **test.sh**: A test script that downloads and prepares the data for Vietnam
  and runs an example CSV file against the
  [trace_attributes](https://valhalla.readthedocs.io/en/latest/api/map-matching/api-reference/#outputs-of-trace_attributes)
  service in 'one shot' mode. **Must be run in this folder.**

- **[windows](./windows/README.md)**: Stuff for setting up on windows...
  probably way out of date.



## Getting started

```bash
# Clone this repository
git clone git@github.com:cvts/cvts.git && cd cvts

# setup Valhalla
./setup-valhalla.sh

# make a virtual env
# Note that this installs for dev
make venv

# get the Vietnam data, set it up, and check that it is all working
./test.sh

# You deactivate the virtual env with
deactivate
```


Alternatively, for development in particular, you might say

```bash
make initial-setup
. venv/bin/activate
./test.sh
deactivate
```



## Config

Configuration is controlled by *cvts/settings.py*. This expects the environment
variable *CVTS_WORK_PATH* to be set, which specifies the root folder for input/output
data. One can optionally set specify the the following environment variables

### Environment Variables

#### General

- *CVTS_MONGO_CONNECTION_STRING*: A connection string for a MongoDB. If this is
  specified, then raw data will be read from that DB. In the present setup, the
  string would look something like:

  *mongodb://<username>:<password>@<host-ip-or-name>:27017/wb*.

- *CVTS_DEBUG*: Run in debug. `False` can be represented by *0* or *False*
  (anything else will be treated as `True`.

- *CVTS_WORK_PATH*: The working directory. Defaults to *~/.cvts*.

- *CVTS_RAW_PATH*: The directory in which the raw data is stored. This must be
  specified unless the environment variable *CVTS_MONGO_CONNECTION_STRING* is
  set.

- *CVTS_ANON_RAW_PATH*: The directory in which to store the outputs of
  *bin/anonymizeregos*. If not specified, this will be created under the
  directory specified by *CVTS_WORK_PATH*.

- *CVTS_BOUNDARIES_PATH*: The directory in regional shape files are stored. If
  not specified it will be assumed to be under under the directory specified by
  *CVTS_WORK_PATH*. If that is not present and boundaries are required,
  something will go bang.

- *CVTS_CONFIG_PATH*: The directory in which the configuration data is stored
  (see the [documentation for the config directory](doc/README-config-folder.md
  for details). If that is not present and boundaries are required, something
  will go bang.

- *CVTS_OUTPUT_PATH*: The directory where outputs will be saved. If not
  specified, this will be created under the directory specified by
  *CVTS_WORK_PATH*.
