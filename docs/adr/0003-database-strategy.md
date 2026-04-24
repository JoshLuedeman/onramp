# Database Strategy

- **Status:** accepted
- **Date:** 2024-10-01
- **Deciders:** OnRamp founding team

## Context and Problem Statement

OnRamp needs a database strategy that supports a productive local development workflow with zero external dependencies while providing production-grade performance and reliability on Azure. The backend is async Python (FastAPI), so the ORM and database drivers must support async I/O natively. The application stores projects, questionnaire state, generated architectures, compliance results, deployment records, and audit logs.

## Decision Drivers

- Async-first — the FastAPI backend uses `async/await` throughout
- Easy local development — developers should run `./dev.sh` and have a working database immediately
- Production-grade Azure integration — Azure SQL with managed identity, automatic backups, geo-replication
- Schema migration support — versioned, reversible migrations for CI/CD
- Multi-tenant data isolation — tenants must not access each other's data

## Considered Options

1. SQLAlchemy 2.0 async with SQLite (dev) / Azure SQL (prod)
2. SQLAlchemy 2.0 async with PostgreSQL everywhere (Azure Database for PostgreSQL)
3. Prisma (Node.js ORM) with PostgreSQL

## Decision Outcome

**Chosen option:** "SQLAlchemy 2.0 async with SQLite (dev) / Azure SQL (prod)", because it provides zero-dependency local development, a mature Python ORM with first-class async support, and native Azure SQL integration for production.

### Positive Consequences

- **Zero-dependency local dev** — SQLite requires no database server. `./dev.sh` works out of the box.
- **SQLAlchemy 2.0** is the most mature Python ORM with comprehensive async support via `AsyncSession`.
- **Alembic** provides robust, versioned schema migrations with autogeneration from model changes.
- **Azure SQL** in production provides automatic backups, geo-replication, built-in security, and managed identity authentication.
- **Pydantic + SQLAlchemy integration** keeps request validation and database models in sync.
- **Docker Compose** option provides SQL Server 2022 for developers who want full SQL Server compatibility locally.

### Negative Consequences

- **Two database drivers** — `aiosqlite` for development and `aioodbc` for production. While SQLAlchemy abstracts most differences, SQL dialect edge cases (e.g., JSON column support, date functions) can cause dev/prod parity issues.
- **Careful session management** — async SQLAlchemy requires explicit session lifecycle management (`async with AsyncSession()`) to avoid connection leaks.
- **SQLite limitations in development** — no concurrent writes, limited ALTER TABLE support, no stored procedures. Complex queries may behave differently than on Azure SQL.
- **ODBC driver dependency** — `aioodbc` requires the ODBC Driver 18 for SQL Server to be installed in the production container image.

## Pros and Cons of the Options

### SQLAlchemy Async with SQLite / Azure SQL

- ✅ Good, because SQLite needs no server — instant local development.
- ✅ Good, because SQLAlchemy 2.0 async is mature and well-documented.
- ✅ Good, because Azure SQL is the native Azure relational database with the best Azure integration.
- ✅ Good, because Alembic migrations are proven and widely adopted.
- ❌ Bad, because two drivers increase the risk of dev/prod differences.
- ❌ Bad, because SQLite does not support all SQL Server features.

### SQLAlchemy Async with PostgreSQL Everywhere

- ✅ Good, because same database engine in dev and prod eliminates dialect differences.
- ✅ Good, because PostgreSQL has rich JSON, array, and full-text search support.
- ❌ Bad, because local development requires running a PostgreSQL server (Docker or installed).
- ❌ Bad, because Azure Database for PostgreSQL has less integration with Azure-native features than Azure SQL.
- ❌ Bad, because the target audience (Azure customers) is more likely to have Azure SQL expertise.

### Prisma with PostgreSQL

- ✅ Good, because Prisma provides excellent developer experience with auto-generated types.
- ✅ Good, because single-language stack if the backend were Node.js.
- ❌ Bad, because Prisma is a Node.js ORM — it does not support Python.
- ❌ Bad, because introducing Node.js for the ORM would create a mixed runtime dependency.
- ❌ Bad, because Prisma's migration system is less flexible than Alembic for complex migrations.

## Links

- [SQLAlchemy 2.0 async documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic documentation](https://alembic.sqlalchemy.org/)
- [Azure SQL documentation](https://learn.microsoft.com/azure/azure-sql/)
- [backend/app/db/](../../backend/app/db/) — database session and initialization
- [backend/app/models/](../../backend/app/models/) — SQLAlchemy models
- [docs/architecture.md](../architecture.md)
