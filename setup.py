#!/usr/bin/env python

from setuptools import setup

setup(name='tap-onfleet',
      version='1.0.1',
      description='Singer.io tap for extracting data from the onfleet API',
      author='Stitch',
      url='http://github.com/lambtron/tap-onfleet',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_onfleet'],
      install_requires=[
          'singer-python==5.1.5',
          'requests==2.31.0',
          'backoff==1.3.2'
      ],
      entry_points='''
          [console_scripts]
          tap-onfleet=tap_onfleet:main
      ''',
      packages=['tap_onfleet'],
      package_data = {
          "schemas": ["tap_onfleet/schemas/*.json"]
      },
      include_package_data=True,
)