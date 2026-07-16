import sqlite3
import logging
from typing import Self, Any

"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃       ┏┓┓•┓    ┓•          ┃
┃       ┣┛┃┃┣┓┏┏┓┃┃╋┏┓       ┃
┃       ┃ ┗┗┗┛┛┗┫┗┗┗┗        ┃
┃               ┗            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""

"""Copyright 2026 Pecific007 <pecific2007@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."""


logger = logging.getLogger(__name__)


class Database:
    """This class handles connection with database"""

    def __init__(self, path: str, **kwargs):
        self.con = sqlite3.connect(path, **kwargs)
        logger.info("Connected to database: %s", path)
        self.con.execute("PRAGMA foreign_keys = ON")
        logger.info("Turned on foreign keys:Executed: PRAGMA foreign_keys = ON")

    def __enter__(self) -> Self:
        return self

    def close(self) -> None:
        logger.info("Disconnected from database.")
        self.con.close()

    def __exit__(self, *_):
        self.close()


class Column:
    """This is a helper class to manage columns"""

    def __init__(
        self,
        sql_type: str,
        pk: bool = False,
        null: bool = True,
        ai: bool = False,  # ai = autoincrement
        unique: bool = False,
        default: Any = None,
    ):
        self.sql_type = sql_type
        self.pk = pk
        self.null = null
        self.autoincrement = ai
        self.unique = unique
        self.default = default

    def to_sql(self, table_name: str) -> str:
        """
        This builds the sql syntax for adding a column
        """
        segs = [table_name, self.sql_type]  # segments of column statement
        if self.pk:
            segs.append("PRIMARY KEY")
        if not self.null:
            segs.append("NOT NULL")
        if self.autoincrement:
            segs.append("AUTOINCREMENT")
        if self.unique:
            segs.append("UNIQUE")
        if self.default is not None:
            if isinstance(self.default, str):
                segs.append(f"DEFAULT '{self.default}'")
            else:
                segs.append(f"DEFAULT {self.default}")
        return " ".join(segs)


class Col:
    def __init__(self, name: str):
        self.name = name


class C:
    """This is a helper class to deal with (multiple) conditions"""

    def __init__(self, col: str, op: str, val: Any):
        self.col = col
        self.op = op.upper()
        self.val = val
        self.negated = False
        self.connector = "AND"
        self.children: list[C] = [self]

    def __or__(self, other: "C") -> "C":
        """
        Gets called when `where(C(<condition>) | C(<condition>))`
        It is equivalent to `where <condition> OR <condition>`
        """
        node = C.__new__(C)
        node.children = [self, other]
        node.connector = "OR"
        node.negated = False
        return node

    def __and__(self, other: "C") -> "C":
        """
        Gets called when `where(C(<condition>) & C(<condition>))`
        It is equivalent to `where <condition> AND <condition>`
        """
        node = C.__new__(C)
        node.children = [self, other]
        node.connector = "AND"
        node.negated = False
        return node

    def __invert__(self) -> "C":
        """This just turns AND|OR doncitions negative"""
        self.negated = True
        return self


class Query:
    """
    This is the query builder.
    The most important piece of this ORM
    Has simplified functions to run Sqlite queries.
    """

    def __init__(self, table_name: str, con: sqlite3.Connection):
        self._table_name = table_name
        self._con = con
        self._stmt = ""
        self._params = []

    def exec(self) -> sqlite3.Cursor:
        """Executes query built by the builder."""
        logger.debug("Executing: %s %s", self._stmt, self._params)
        result = self._con.execute(self._stmt, self._params)
        self._con.commit()
        return result

    def exec_raw(self, sql: str, sql_params: tuple | list = []) -> sqlite3.Cursor:
        """Executes raw sql queries"""
        logger.debug("EXECUTING: %s %s", sql, sql_params)
        result = self._con.execute(sql, sql_params)
        self._con.commit()
        return result

    def select(self, *columns: str) -> Self:
        """
        Selects from table.
        Ex: `MyTable.query().select("col1", "col2").exec()`
        will produce: `SELECT col1, col2 FROM mytable`
        """
        cols = ", ".join(columns)
        self._stmt += f"SELECT {cols} FROM {self._table_name}"
        return self

    def order_by(self, by: str | dict) -> Self:
        if isinstance(by, str):
            self._stmt += f" ORDER BY {by}"
        else:
            cols = ", ".join(f"{k} {v}" for k, v in by.items())
            self._stmt += f" ORDER BY {cols}"
        return self

    def group_by(self, by: str) -> Self:
        self._stmt += f" GROUP BY {by} "
        return self

    def limit(self, limit: Any) -> Self:
        self._stmt += f" LIMIT {limit} "
        return self

    def insert(self, subquery: Query | None = None, **values) -> Self:  # noqa: F821 -- Shut up Ruff lsp!
        """
        Insert a value into the table.
        Ex: `MyTable.query().insert(col1="val1", col2="val2").exec()`
        will produce: `INSERT INTO mytable (col1, col2) VALUES (?, ?)`
                      with parameters: ['val1', 'val2']
        Or: `OtherTable.query().insert(MyTable.query().select("*")).exec()`
        will produce: `INSERT INTO othertable SELECT * FROM mytable`
        """
        stmt = [f"INSERT INTO {self._table_name}"]
        if subquery is not None:
            stmt.append(subquery._stmt)
            self._params.extend(subquery._params)
        else:
            cols = ", ".join(values.keys())
            placeholders = ", ".join("?" * len(values))
            stmt.append(f"({cols}) VALUES({placeholders})")
            self._params.extend(values.values())
        self._stmt += " ".join(stmt)
        return self

    def _build_condition(self, node: C) -> str:
        """
        This is the main logic behind condition processing
        The `C` object produces a tree, this method will traverse that tree
        recursively for each child and turn them into valid conditions
        with AND/OR connectors
        """
        if len(node.children) == 1:
            # special if clause for `IN` operators
            # if operator is "IN"
            if node.op == "IN":
                # If a query is passed as value
                if isinstance(node.val, Query):
                    self._params.extend(node.val._params)
                    return f"{node.col} IN ({node.val._stmt})"
                else:
                    # if any other value is passed as value
                    placeholders = ", ".join("?" * len(node.val))
                    self._params.extend(node.val)
                    return f"{node.col} IN ({placeholders})"
            # For the join queries
            if isinstance(node.val, Col):
                return f"{node.col} {node.op} {node.val.name}"
            # for olny one condition
            self._params.append(node.val)
            condition = f"{node.col} {node.op} ?"
            return f"NOT ({condition})" if node.negated else condition
        # for more than one conditions.
        segs = [self._build_condition(child) for child in node.children]
        joined = f"({f' {node.connector} '.join(segs)})"
        return f"NOT ({joined})" if node.negated else joined

    def where(self, condition: C) -> Self:
        """
        This for conditions. Conditions can be passed as `C` object instances.
        Ex:
            `MyTable.query().select("*").where(C("col1", "=", "val1")).exec()`

        Multiple conditions:
            Connect multiple conditions with `AND` (using `&` <- ampersand) and `OR` (using `|` <- pipe)
            `MyTable.query().select("*").where(C("col1", "=", "val1") | C("col2", "=", "val2").exec()`

        Any operator can be passed to the condition, ex:
            `MyTable.query().select("*").where(C("col1", "LIKE", "%1")).exec()`

        Conditions with a query value can also be passed in:
            `OtherTable.query().select("*").where(C("col1", "IN", MyTable.query().select("col1"))).exec()`
        """
        self._stmt += f" WHERE {self._build_condition(condition)}"
        return self

    def update(self, **kwargs) -> Self:
        """
        This is similar to `insert` without the queries.
        Ex: `MyTable.query().update(col1="val2").exec()`
        """
        cols = ", ".join(f"{k} = ?" for k in kwargs.keys())
        self._params.extend(kwargs.values())
        self._stmt += f"UPDATE {self._table_name} SET {cols}"
        return self

    def join(self, reference_table: type, on: C, how: str = "INNER") -> Self:
        """
        reference_talble is the table to join with
        on: is a C object. Ex: `C("MyTable.id", "=", Col("OtherTable.id"))`
        how: is how the join happens. INNER, OUTER, etc.
        Ex: `MyTable.query()
            .select("*")
            .join(OtherTable, C("MyTable.id", "=", Col("OtherTable.id")), "OUTER").exec()`
        """

        _VALID_JOINS = {
            "INNER",
            "LEFT",
            "LEFT OUTER",
            "RIGHT",
            "RIGHT OUTER",
            "FULL",
            "FULL OUTER",
            "CROSS",
        }
        how = how.upper()
        if how not in _VALID_JOINS:
            raise ValueError(
                f"Invalid join type {how!r}. Must be one of: {_VALID_JOINS}"
            )
        self._stmt += (
            f" {how} JOIN {reference_table._table_name} ON {self._build_condition(on)}"
        )
        return self

    def delete(self) -> Self:
        """Deleting a column from table. append `.where()` to specify what to delete"""
        self._stmt += f"DELETE FROM {self._table_name}"
        return self


class ModelMeta(type):
    """
    This is the metaclass for the table class.
    This class initializes the table name, columns, etc. based on
    the values defined in the class.
    """

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        if cls.__name__ == "model":
            return cls
        cls._columns = {k: v for k, v in namespace.items() if isinstance(v, Column)}  # type: ignore -- more lsp bs
        cls._table_name = name  # type: ignore
        return cls


class table(metaclass=ModelMeta):
    """
    This is our main class that implements the Sqlite table related functionalities
    Usage:
        - Define a class that inherits from the `table` class.
          `class MyTable(table):`
        - In that class define the columns like:
          `id = table.Int(pk=True)`
          `name = table.Text(null=False)`
          `user_id = table.Float(null=False, unique=True)`
        - Call method `create` to create table and
          `destroy` (will rename later) to drop it
    """

    # NOTE: Before creating a table makesure you are connected to a database.
    # After connecting call `table.use()` and pass the Database object as an argument.

    _db: Database | None = None
    _table_name: str
    _columns: dict[Any, Any]
    _no_database_connection_error = "No database connected.\nConnect to a database by initializing an instance of Database class\nand call the `table.use()` method and pass that instance."

    # columns:
    Blob = lambda **kw: Column("BLOB", **kw)  # noqa: E731 -- Shut up Ruff lsp
    Bool = lambda **kw: Column("BOOLEAN", **kw)  # noqa: E731
    Float = lambda **kw: Column("REAL", **kw)  # noqa: E731
    Int = lambda **kw: Column("INTEGER", **kw)  # noqa: E731
    Json = lambda **kw: Column("JSON", **kw)  # noqa: E731
    Text = lambda **kw: Column("TEXT", **kw)  # noqa: E731
    Numeric = lambda **kw: Column("NUMERIC", **kw)  # noqa: E731

    @staticmethod
    def ForeignKey(reference_table: type, reference_col: str = "id") -> Column:
        reference_col_type = reference_table._columns[reference_col].sql_type
        return Column(
            f"{reference_col_type} REFERENCES {reference_table._table_name}({reference_col})"
        )

    @classmethod
    def use(cls, db: Database):
        # Makes use of the database passed in
        cls._db = db

    @classmethod
    def create(cls) -> None:
        """Creates the table."""
        if cls._db is None:
            raise RuntimeError(cls._no_database_connection_error)
        cols = ", ".join(c.to_sql(n) for n, c in cls._columns.items())
        sql = f"CREATE TABLE IF NOT EXISTS {cls._table_name}({cols})"
        cls._db.con.execute(sql)
        cls._db.con.commit()
        logger.info("Table %s created.", cls._table_name)

    @classmethod
    def destroy(cls) -> None:
        """Drops the table."""
        if cls._db is None:
            raise RuntimeError(cls._no_database_connection_error)
        sql = f"DROP TABLE IF EXISTS {cls._table_name}"
        cls._db.con.execute(sql)
        cls._db.con.commit()
        logger.info("Table %s dropped.", cls._table_name)

    @classmethod
    def query(cls) -> Query:
        """
        Returns a query builder.
        """
        if cls._db is None:
            raise RuntimeError(cls._no_database_connection_error)
        return Query(cls._table_name, cls._db.con)
