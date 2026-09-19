"""Registers PyMySQL as the MySQL driver, for every entry point.

Namecheap's shared hosting has no MySQL C headers, so mysqlclient cannot be
built there. PyMySQL speaks the same protocol and can stand in for the
`MySQLdb` module that Django's mysql backend imports.

This lives here rather than in passenger_wsgi.py because that file is only
loaded when Passenger serves a request. Management commands -- `migrate`,
`createcachetable`, `collectstatic`, anything the deploy runs -- never import
it, and would fail with "Error loading MySQLdb module" before touching the
database. Django imports this package to reach config.settings, whichever way
it was started, so the shim is in place for all of them.

Doing nothing when mysqlclient is present keeps local development on the real
driver, and doing nothing when neither exists keeps SQLite working without
PyMySQL installed at all.
"""
try:  # pragma: no cover - depends on which driver the host has
    import MySQLdb  # noqa: F401
except ImportError:
    try:
        import pymysql

        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
