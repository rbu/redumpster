#!/usr/bin/env python
# encoding: utf8

from setuptools import setup

setup(
    name='redumpster',
    version='1.0.0',
    description='dump data. restore data. update dumps.',
    author='rbu',
    license='BSD',
    author_email='rbu@rbu.sh',
    py_modules=['redumpster'],
    test_suite="redumpster.tests",
    install_requires=[
        'sh',
        'docopt',
        'attic',
        'configobj',
    ],
    test_requires=['pyexpect', 'nose', 'watching-testrunner', 'testfixtures'],
    entry_points="""\
        [console_scripts]
        redumpster = redumpster.main:main
    """

)
