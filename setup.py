import setuptools

print(setuptools.find_packages())

setuptools.setup(
    name='graphxplore',
    version='0.9.0',
    description='meta data extraction, cleaning, and transformation as well as data exploration using graph representations and dashboards',
    author='Louis Bellmann',
    url='https://github.com/UKEIAM/graphxplore',
    packages=setuptools.find_packages(),
    python_requires='>=3.10',
    requires=['py2neo', 'chardet', 'plotly']
)
