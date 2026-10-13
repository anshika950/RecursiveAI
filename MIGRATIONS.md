# Database Migrations

This project does **not** use a migration tool (e.g. Alembic). Tables are
created at startup via `Base.metadata.create_all(bind=engine)` in
`app/main.py`'s lifespan handler, which only creates tables that don't
exist yet — it never alters an existing table's columns.

## In development

If you change a model in `app/models.py` (add/remove/rename a column, add
a new table that an existing table now references, etc.), the simplest
fix for local development is:

```bash
rm app.db
# restart the server — create_all() will rebuild the schema from scratch
```

This loses local data, which is fine for a dev SQLite file but **is not**
a real migration strategy.

## A real fix (not yet done)

A follow-up would introduce [Alembic](https://alembic.sqlalchemy.org/) to
generate versioned migration scripts, so schema changes can be applied to
an existing database (including in production) without dropping data.
This is a known, intentional gap in the current setup, not an oversight.
