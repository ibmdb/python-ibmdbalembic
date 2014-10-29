IBM_DB_ALEMBIC
==============
The IBM_DB_ALEMBIC adaptor provides the Python/Alembic interface to IBM Data Servers.


Prerequisites
-------------
1. Python 2.6.x or above
2. Alembic 0.6.5 or above
3. SQLAlchemy 0.7.3 or above
4. IBM_DB_SA 0.3.2 or above
4. IBM_DB driver and IBM_DB_DBI wrapper 1.0.1 or higher

Install and COnfiguration
==========================
The IBM_DB_ALEMBIC Python Egg component (.egg) can be installed using the standard setuptools provided by the Python Easy Install through Python Entreprise 
Application Kit community portal:
  http://peak.telecommunity.com/DevCenter/EasyInstall

Please follow the steps provided to Install "Easy Install" in the link above and follow up with these additional steps to install IBM_DB_SA:

  1. To install IBM_DB_ALEMBIC component available in the remote repositories
  (pypi.python.org):
    Windows:
      > easy_install ibm_db_alembic
    Linux/Unix:
      $ sudo easy_install ibm_db_alembic
  
  2. To install IBM_DB_ALEMBIC from source
    Standard Python setup should be used::
        python setup.py install
        
Connecting
----------
To allow ibm_db_alembic loaded up when alembic runs, edit env.py file and import IbmDbImpl "from ibm_db_alembic import IbmDbImpl"
