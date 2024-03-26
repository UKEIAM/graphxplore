import setuptools

print(setuptools.find_packages())

setuptools.setup(
    name='graphxplore',
    version='0.9.0',
    description='meta data extraction, cleaning, and transformation as well as data exploration using association graphs and dashboards',
    author='Louis Bellmann',
    url='https://github.com/UKEIAM/graphxplore',
    packages=setuptools.find_packages(),
    requires=['py2neo', 'chardet']
)
