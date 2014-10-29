#!/usr/bin/env python

from setuptools import setup
import os
import re


v = open(os.path.join(os.path.dirname(__file__), 'ibm_db_alembic', '__init__.py'))
VERSION = re.compile(r".*__version__ = '(.*?)'", re.S).match(v.read()).group(1)
v.close()

readme = os.path.join(os.path.dirname(__file__), 'README.rst')

setup(
         name='ibm_db_alembic',
         version=VERSION,
         license='Apache License 2.0',
         description='Alembic support for IBM Data Servers',
         author='IBM Application Development Team',
         author_email='opendev@us.ibm.com',
         url='http://pypi.python.org/pypi/ibm_db_alembic/',
         keywords='Alembic database interface IBM Data Servers DB2',
         classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: Apache Software License',
            'Operating System :: OS Independent',
            'Topic :: Databases :: Front-end'
        ],
         long_description=open(readme).read(),
         platforms='All',
         install_requires=['alembic>=0.6.5', 'ibm_db_sa>=0.3.2'],
         packages=['ibm_db_alembic'],
        
         zip_safe=False,
     )
