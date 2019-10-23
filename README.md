
# FS-LAB 

A plugin for Jendrik Seipp's [Lab](https://lab.readthedocs.io/en/latest/) 
to run experiments for the FS planner. 


## Installation

At the moment the plugin is _not_ released on PyPI.
You can use the latest release on the Github repository by using: 

    pip install -U git+https://github.com/aig-upf/fslab.git

### Development installation
We recommend cloning from the Github repository and doing a dev installation
(the`-e` flag for `pip`) on a [virtual environment](https://docs.python.org/3/tutorial/venv.html):
    
    git clone https://github.com/aig-upf/fslab
    cd fslab
    pip install -e .

This will install the project in "editable mode", meaning that any modification to the files
is immediately reflected in the _installed_ library.

### Software Requirements
The plugin has been tested on Python >= 3.6

## License
Tarski is licensed under the [GNU General Public License, version 3](LICENSE).
