# Database Operations

## Overview

OnRamp uses **SQLAlchemy 2.0 async** as the ORM and **Alembic** for schema migrations. The database strategy differs by environment:

| Environment | Database | Driver | Connection |
|-------------|----------|--------|------------|
| Development | SQLite | `aiosqlite` | Local file (`onramp.db`) |
| Docker Compose | SQL Server 2022 | `aioodbc` | `localhost:1433` |
| Production | Azure SQL | `aioodbc` | Azure SQL endpoint with managed identity or credentials |

---

## Schema Migrations with Alembic

### Creating a New Migration

After modifying SQLAlchemy models in `backend/app/models/`:

```bash
cd backend
alembic revision --autogenerate -m "add column X to table Y"
```

This generates a new migration file in `backend/alembic/versions/`. **Always review the generated migration** — autogenerate does not detect all changes (e.g., column renames, data migrations).

### Applying Migrations

```bash
# Apply all pending migrations
cd backend
alembic upgrade head

# Apply one migration forward
alembic upgrade +1

# Check current state
alembic current

# View migration history
alembic history --verbose
```

### Rolling Back Migrations

```bash
# Roll back one migration
alembic downgrade -1

# Roll back to a specific revision
alembic downgrade <revision-id>

# Roll back all migrations
alembic downgrade base
```

> ⚠️ **Warning:** Always review the `downgrade()` function in the migration file before rolling back. Some migrations drop columns or tables, which causes **permanent data loss**.

### Migration Best Practices

- **One migration per PR** — keep migrations small and reviewable.
- **Test both directions** — run `upgrade` and `downgrade` locally before pushing.
- **Never edit a migration that has been applied in production** — create a new migration instead.
- **Use explicit column types** — avoid relying on SQLAlchemy's type inference for cross-database compatibility.
- **Handle data migrations separately** — if you need to transform data, create a dedicated data migration rather than mixing DDL and DML.

---

## Seed Data Management

OnRamp seeds reference data (compliance frameworks, questionnaire questions, archetypes) on startup via `app/db/seed.py`. The seed function runs during the application `lifespan` startup event.

### How Seeding Works

1. The `seed_database()` function is called during `lifespan` startup in `main.py`.
2. It inserts or updates reference data using upsert logic (insert if not exists, update if changed).
3. Seeding is idempotent — running it multiple times produces the same result.

### Resetting Seed Data

**Development (SQLite):**
```bash
cd backend
rm -f onramp.db
# Restart the backend — the database and seed data are recreated automatically.
```

**Docker Compose:**
```bash
docker compose down -v   # Remove volumes (deletes database)
docker compose up -d     # Recreate and re-seed
```

### Adding New Seed Data

1. Add seed records to the appropriate section in `backend/app/db/seed.py`.
2. Use upsert patterns to ensure idempotency.
3. Create an Alembic migration if the seed data requires new tables or columns.

---

## Backup and Restore

### Development (SQLite)

SQLite data is stored in `backend/onramp.db`. To back up:

```bash
cp backend/onramp.db backend/onramp.db.backup
```

To restore:

```bash
cp backend/onramp.db.backup backend/onramp.db
# Restart the backend
```

### Production (Azure SQL)

Azure SQL provides automatic backups with configurable retention.

**Check backup status:**
```bash
az sql db show --server <server-name> --name <db-name> --resource-group <rg-name> \
  --query "{retention: retentionDays, earliestRestore: earliestRestoreDate}" -o table
```

**Point-in-time restore:**
```bash
az sql db restore \
  --dest-name <restored-db-name> \
  --server <server-name> \
  --resource-group <rg-name> \
  --name <source-db-name> \
  --time "2024-01-15T10:00:00Z"
```

**Long-term retention (LTR):**
```bash
# Configure weekly backups retained for 4 weeks
az sql db ltr-policy set \
  --server <server-name> \
  --resource-group <rg-name> \
  --name <db-name> \
  --weekly-retention P4W
```

---

## Connection String Formats

### SQLite (Development)

The default for local development. No configuration required — the application creates `onramp.db` in the backend directory.

```
sqlite+aiosqlite:///./onramp.db
```

### SQL Server (Docker Compose)

Used when running the full stack via `docker compose`:

```
mssql+aioodbc://sa:YourPassword@localhost:1433/onramp?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes
```

### Azure SQL (Production)

**With credentials:**
```
mssql+aioodbc://user:password@server.database.windows.net:1433/onramp?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes
```

**With managed identity (recommended):**
```
mssql+aioodbc://@server.database.windows.net:1433/onramp?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&Authentication=ActiveDirectoryMsi
```

Set the connection string via the `ONRAMP_DATABASE_URL` environment variable. When this variable is not set, the application defaults to SQLite.

---

## Common Database Tasks

### Inspect the Current Schema

```bash
cd backend

# Show current Alembic revision
alembic current

# Show all tables (SQLite)
python -c "
import sqlite3
conn = sqlite3.connect('onramp.db')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\").fetchall()
for t in tables:
    print(t[0])
conn.close()
"
```

### Run a Query Against the Dev Database

```bash
cd backend
python -c "
import sqlite3
conn = sqlite3.connect('onramp.db')
# Example: count projects
result = conn.execute('SELECT COUNT(*) FROM projects').fetchone()
print(f'Projects: {result[0]}')
conn.close()
"
```

### Check for Pending Migrations

```bash
cd backend
alembic check
# Returns exit code 0 if models match the database, non-zero if migrations are needed.
```

### Resolve a Migration Conflict

If two branches create migrations with conflicting `down_revision` values:

1. Identify the conflicting head revisions:
   ```bash
   alembic heads
   ```
2. Create a merge migration:
   ```bash
   alembic merge heads -m "merge branch migrations"
   ```
3. Review and test the merge migration.
