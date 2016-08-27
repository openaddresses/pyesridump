# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='esridump',
    version='1.1.1',
    description='Dump geodata from ESRI endpoints to GeoJSON',
    long_description=readme,
    author='Ian Dees',
    author_email='ian.dees@gmail.com',
    url='https://github.com/openaddresses/pyesridump',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=[
        'requests',
        'simplejson',
    ],
    entry_points={
        'console_scripts': ['esri2geojson=esridump.cli:main'],
    }
)
