# +--------------------------------------------------------------------------+
# |  Licensed Materials - Property of IBM                                    |
# |                                                                          |
# | (C) Copyright IBM Corporation 2014.                                      |
# +--------------------------------------------------------------------------+
# | This module complies with Alembic and is                                 |
# | Licensed under the Apache License, Version 2.0 (the "License");          |
# | you may not use this file except in compliance with the License.         |
# | You may obtain a copy of the License at                                  |
# | http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable |
# | law or agreed to in writing, software distributed under the License is   |
# | distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY |
# | KIND, either express or implied. See the License for the specific        |
# | language governing permissions and limitations under the License.        |
# +--------------------------------------------------------------------------+
# | Authors: Rahul Priyadarshi                                               |
# +--------------------------------------------------------------------------+
"""
    Support for IBM DB2 database
"""
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import MetaData, Table
from sqlalchemy.engine import reflection
from sqlalchemy import schema as sa_schema
from sqlalchemy import types as sa_types
from ibm_db_sa import reflection as ibm_db_reflection

from alembic.ddl.impl import DefaultImpl
from alembic.ddl import base
from alembic.ddl.base import ColumnType, RenameTable, AddColumn, ColumnName

class IbmDbImpl(DefaultImpl):
    __dialect__ = 'ibm_db_sa'
    transactional_ddl = True
    
    def get_server_version_info(self, dialect):
        """Returns the DB2 server major and minor version as a list of ints."""
        if hasattr(dialect, 'dbms_ver'):
            return [int(ver_token) for ver_token in dialect.dbms_ver.split('.')[0:2]]
        else:
            return []
    
    def _is_nullable_unique_constraint_supported(self, dialect):
        """Checks to see if the DB2 version is at least 10.5.
        This is needed for checking if unique constraints with null columns are supported.
        """
        if hasattr(dialect, 'dbms_name') and (dialect.dbms_name.find('DB2/') != -1):
            return self.get_server_version_info(dialect) >= [10, 5]
        else:
            return False
        
    def _exec(self, construct, *args, **kw):
        checkReorgSQL = "select TABSCHEMA, TABNAME from SYSIBMADM.ADMINTABINFO where REORG_PENDING = 'Y'"
        if construct == checkReorgSQL:
            return
        
        result = super(IbmDbImpl, self)._exec(construct, *args, **kw)
        conn = self.connection
        res = conn.execute(checkReorgSQL)
        reorgSQLs = []
        if res and res.returns_rows:
            for sName, tName in res:
                reorgSQL = '''CALL SYSPROC.ADMIN_CMD('REORG TABLE "%(sName)s"."%(tName)s"')''' % {'sName': sName, 'tName': tName}
                reorgSQLs.append(reorgSQL)
        
        for sql in reorgSQLs:
            conn.execute(sql)
        return result
            
    def alter_column(self, table_name, column_name,
                        nullable=None,
                        server_default=False,
                        name=None,
                        type_=None,
                        schema=None,
                        autoincrement=None,
                        existing_type=None,
                        existing_server_default=None,
                        existing_nullable=None,
                        existing_autoincrement=None
                    ):
        primary_key_columns = None
        deferred_primary_key = None
        if type_ or name:
            insp = reflection.Inspector.from_engine(self.connection)
            primary_key_columns = insp.get_pk_constraint(table_name, schema).get('constrained_columns')
        if autoincrement is not None or existing_autoincrement is not None:
            util.warn("autoincrement and existing_autoincrement only make sense for MySQL")
        if nullable is not None:
            self._exec(base.ColumnNullable(table_name, column_name,
                                nullable, schema=schema,
                                existing_type=existing_type,
                                existing_server_default=existing_server_default,
                                existing_nullable=existing_nullable,
                                ))
        if server_default is not False:
            self._exec(base.ColumnDefault(
                                table_name, column_name, server_default,
                                schema=schema,
                                existing_type=existing_type,
                                existing_server_default=existing_server_default,
                                existing_nullable=existing_nullable,
                            ))
        if type_ is not None:
            if isinstance(type_, sa_types.Enum):
                try:
                    self._exec("ALTER TABLE %s DROP CHECK %s" %
                               (base.format_table_name(self.dialect.ddl_compiler(self.dialect, None), table_name, schema),
                                type_.name))
                except Exception:
                    pass #continue since check constraint doesn't exist
                
            if primary_key_columns and column_name.lower() in primary_key_columns:
                self._exec("ALTER TABLE %s DROP PRIMARY KEY" % 
                           (base.format_table_name(self.dialect.ddl_compiler(self.dialect, None), table_name, schema)))
                try:
                    self._exec("ALTER TABLE %s ALTER COLUMN %s DROP IDENTITY" % 
                               (base.format_table_name(self.dialect.ddl_compiler(self.dialect, None), table_name, schema),
                                base.format_column_name(self.dialect.ddl_compiler(self.dialect, None), column_name)))
                except Exception:
                    pass #Continue since identity does not exist.
                if name is not None:
                    primary_key_columns.remove(column_name.lower())
                    primary_key_columns.add(name.lower())
                    
                deferred_primary_key = True
                           
            self._exec(base.ColumnType(
                                table_name, column_name, type_, schema=schema,
                                existing_type=existing_type,
                                existing_server_default=existing_server_default,
                                existing_nullable=existing_nullable,
                            ))
        
        if name is not None:
            if primary_key_columns and not deferred_primary_key and column_name.lower() in primary_key_columns:
                self._exec("ALTER TABLE %s DROP PRIMARY KEY" % 
                           (base.format_table_name(self.dialect.ddl_compiler(self.dialect, None), table_name, schema)))
                primary_key_deferred = True
            self._exec(base.ColumnName(
                                table_name, column_name, name, schema=schema,
                                existing_type=existing_type,
                                existing_server_default=existing_server_default,
                                existing_nullable=existing_nullable,
                            ))
            
        if deferred_primary_key:
            self._exec("Alter TABLE %s ADD PRIMARY KEY(%s)" % 
                       (base.format_table_name(self.dialect.ddl_compiler(self.dialect, None), table_name, schema),
                        ','.join(base.format_column_name(self.dialect.ddl_compiler(self.dialect, None), col) for col in primary_key_columns)))
                        
    def add_column(self, table_name, column, schema=None):
        nullable = True
        pk = False
        if not column.nullable:
            nullable = False
            column.nullable = True
        if column.primary_key:
            pk = True
            column.primary_key = False
        super(IbmDbImpl, self).add_column(table_name, column, schema)
        
        if not nullable:
            self._exec(base.ColumnNullable(table_name, column.name, nullable, schema=schema))
        if pk:
            db2reflector = ibm_db_reflection.DB2Reflector(self.bind.dialect)
            other_pk = db2reflector.get_primary_keys(self.connection, table_name, schema)
            if other_pk:
                self._exec("ALTER TABLE %s DROP PRIMARY KEY" % (
                                base.format_table_name(self.dialect.ddl_compiler(self.dialect, None), table_name, schema)))
                try:
                    self._exec("ALTER TABLE %s ALTER COLUMN %s DROP IDENTITY" % (
                                    base.format_table_name(self.dialect.ddl_compiler(self.dialect, None), table_name, schema),
                                    base.format_column_name(self.dialect.ddl_compiler(self.dialect, None), column.name)))
                except Exception:
                    pass #Continue since identity does not exist.
            pk_sql = "ALTER TABLE %s ADD PRIMARY KEY(%s)" % (
                        base.format_table_name(self.dialect.ddl_compiler(self.dialect, None), table_name, schema),
                        base.format_column_name(self.dialect.ddl_compiler(self.dialect, None), column.name))
            self._exec(pk_sql)

    def drop_constraint(self, const):
        """ check for unique constraint created as "unique index exclude nulls" for constraint containing nullable columns
        """
        if isinstance(const, sa_schema.UniqueConstraint):
            if self._is_nullable_unique_constraint_supported(self.dialect):
                const.uConstraint_as_index = True
                db2reflector = ibm_db_reflection.DB2Reflector(self.bind.dialect)
                uni_consts = db2reflector.get_unique_constraints(self.connection, const.table.name)
                for uni_const in uni_consts:
                    if uni_const.get('name') == const.name.lower():
                        const.uConstraint_as_index = False
        self._exec(sa_schema.DropConstraint(const))
        
    def rename_table(self, old_table_name, new_table_name, schema=None):
        db2reflector = ibm_db_reflection.DB2Reflector(self.bind.dialect)
        deff_fks = db2reflector.get_foreign_keys(self.connection, old_table_name, schema)
        inc_fks = db2reflector.get_incoming_foreign_keys(self.connection, old_table_name, schema)
        
        for inc_fk in inc_fks:
            if inc_fk.get('name') not in (deff_fk.get('name') for deff_fk in deff_fks):
                deff_fks.append(inc_fk)
        
        for fk in deff_fks:
            sql_drop_fk = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s"
            fk_table = fk.get('constrained_table') or old_table_name
            fk_schema = fk.get('constrained_schema') or schema
            self._exec( sql_drop_fk % {
                            'table': "%s.%s" % (fk_schema, fk_table) if fk_schema else fk_table,
                            'name': fk.get('name')})
            
        self._exec(base.RenameTable(old_table_name, new_table_name, schema=schema))
        
        for fk in deff_fks: 
            sql_create_fk = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s FOREIGN KEY (%(column)s) REFERENCES %(to_table)s (%(to_column)s)"
            if fk.get('constrained_table') == old_table_name.lower():
                fk['constrained_table'] = new_table_name.lower()
            if fk.get('referred_table') == old_table_name.lower():
                fk['referred_table'] = new_table_name.lower() 
                
            fk_table = fk.get('constrained_table') or new_table_name.lower()
            fk_schema = fk.get('constrained_schema') or schema 
            to_table = fk.get('referred_table')
            to_schema = fk.get('referred_schema')
            self._exec(sql_create_fk % {
                            'table': "%s.%s" % (fk_schema, fk_table) if fk_schema else fk_table,
                            'name': fk.get('name'),
                            'column': ', '.join(fk.get('constrained_columns')),
                            'to_table': "%s:%s" % (to_schema, to_table) if to_schema else to_table,
                            'to_column': ', '.join(fk.get('referred_columns'))})

@compiles(ColumnType, 'ibm_db_sa')
def visit_column_type(element, compiler, **kw):
    return "%s %s %s" % (
        base.alter_table(compiler, element.table_name, element.schema),
        base.alter_column(compiler, element.column_name),
        "SET DATA TYPE %s" % base.format_type(compiler, element.type_)
    )
    
@compiles(ColumnName, 'ibm_db_sa')
def visit_column_name(element, compiler, **kw):
    return "%s RENAME COLUMN %s TO %s" % (
        base.alter_table(compiler, element.table_name, element.schema),
        base.format_column_name(compiler, element.column_name),
        base.format_column_name(compiler, element.newname)
    )

@compiles(RenameTable, 'ibm_db_sa')
def visit_rename_table(element, compiler, **kw):
    return "RENAME TABLE %s TO %s" % (
        base.format_table_name(compiler, element.table_name, element.schema),        
        base.format_table_name(compiler, element.new_table_name, element.schema)
    )
    