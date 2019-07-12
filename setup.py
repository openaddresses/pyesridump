# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

setup(
    name='esridump',
    version='1.9.3',
    description='Dump geodata from ESRI endpoints to GeoJSON',
    long_description=readme,
    long_description_content_type='text/markdown',
    author='Ian Dees',
    author_email='ian.dees@gmail.com',
    url='https://github.com/openaddresses/pyesridump',
    license='MIT',
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=[
        'requests',
        'six',
    ],
    entry_points={
        'console_scripts': ['esri2geojson=esridump.cli:main'],
    }
)
