# GraphXplore: Visual exploration and easy preprocessing of data

[![unittest workflow](https://github.com/UKEIAM/graphxplore/actions/workflows/unittest.yml/badge.svg)](https://github.com/UKEIAM/graphxplore/actions/workflows/unittest.yml)

<img src="./frontend/GraphXplore/graphxplore_icon.png" alt="drawing" width="100"/>

## About

GraphXplore is a tool for visually exploring, cleaning and transforming your data, as well as defining and sharing 
metadata and mappings with others. You can access GraphXplore as a Python package, or use its graphical user interface 
application. The app can either be run as a local webserver or a standalone desktop app.
GraphXplore does not require advanced knowledge about statistics or data science and the app can be used without prior 
coding/scripting skills. The tool was designed with the application to the medical research domain in mind, but can be 
generally used with any data source. 

## Installation

- Python package: Install from PyPi with `pip install graphxplore`, or checkout versions at ( :hammer: TODO insert pypi link)
  - Alternatively, you can clone this repository, checkout a specific commit and use that version via `sys.path`,
    `pip install -e` or `conda develop`
- Desktop app: Download the installer for a specific release from ( :hammer: TODO insert release link)
  - Alternatively, you can clone this repository, checkout a specific commit, use [NPM](https://www.npmjs.com/) and run 
    the [installation script](./frontend/build_release.sh)
- Local webserver: Clone this repository, install streamlit with `pip install streamlit`, navigate to 
  `frontend/GraphXplore` and run `streamlit run streamlit_app.py`

## Documentation

You can find detailed information about the data-related tasks that you can work in with GraphXplore, as well as its 
functionalities at ( :hammer: TODO insert GitHub pages link). Additionally, the same information is given in the app via various 
how-to pages and tooltips.

To read the Python package code documentation navigate to ( :hammer: TODO insert readthedocs link)
