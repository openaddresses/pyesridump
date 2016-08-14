# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.me') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='esri-dump',
    version='0.1.0',
    description='Dump geodata from ESRI endpoints to GeoJSON',
    long_description=readme,
    author='Ian Dees',
    author_email='ian.dees@gmail.com',
    url='https://github.com/openaddresses/pyesridump',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
