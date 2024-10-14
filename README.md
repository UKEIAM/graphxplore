# GraphXplore: Visual exploration and easy preprocessing of data

[![unittest workflow](https://github.com/UKEIAM/graphxplore/actions/workflows/unittest.yml/badge.svg)](https://github.com/UKEIAM/graphxplore/actions/workflows/unittest.yml)
[![Documentation Status](https://readthedocs.org/projects/graphxplore/badge/?version=latest)](https://graphxplore.readthedocs.io/en/latest/?badge=latest)

<img src="https://ukeiam.github.io/graphxplore/graphxplore_icon.png" alt="drawing" width="100"/>

## About

GraphXplore is a tool for visually exploring, cleaning and transforming your data, as well as defining and sharing 
metadata and mappings with others. You can access GraphXplore as a Python package, or use its graphical user interface 
application. The app can either be run as a local webserver or a standalone desktop app.
GraphXplore does not require advanced knowledge about statistics or data science and the app can be used without prior 
coding/scripting skills. The tool was designed with the application to the medical research domain in mind, but can be 
generally used with any data source. 

## Installation

- Python package: Install from PyPi with `pip install graphxplore`, or checkout versions at the 
  [PyPI GraphXplore project site](https://pypi.org/project/graphxplore/)
  - Alternatively, you can clone this repository, checkout a specific commit and use that version via `sys.path`,
    `pip install -e` or `conda develop`
- Desktop app: [Download the installer](https://github.com/UKEIAM/graphxplore/releases)
  - Alternatively, you can clone this repository, checkout a specific commit, use [NPM](https://www.npmjs.com/) and run 
    the [installation script](./frontend/build_release.sh)
- Local webserver: Clone this repository, install streamlit with `pip install streamlit==1.39.0`, navigate to 
  `frontend/GraphXplore` and run `streamlit run streamlit_app.py`

## Documentation

In the [GraphXplore user guide](https://ukeiam.github.io/graphxplore/) you can find detailed information about the 
data-related tasks that you can work in with GraphXplore, as well as its functionalities. Additionally, the same 
information is given in the app via various how-to pages and tooltips.

For information on coding with GraphXplore, read the [Python package code documentation](https://graphxplore.readthedocs.io/en/latest/).