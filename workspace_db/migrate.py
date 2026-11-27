"""Apply checked, forward-only SQL migrations transactionally.

Set DATABASE_URL in the environment before invoking this module. A database
backup should be available before applying changes to an existing database.
"""

import asyncio
import hashlib
import os
from pathlib import Path

MIGRATIONS = Path(__file__).parent / "migrations"
LOCK_ID = 7198452154901


def load_migrations(directory: Path = MIGRATIONS):
    files = sorted(directory.glob("[0-9][0-9][0-9]_*.sql"))
    if not files:
        raise RuntimeError("No migration files found")
    versions = [path.name[:3] for path in files]
    if len(versions) != len(set(versions)):
        raise RuntimeError("Duplicate migration version")
    return [(path.name, path.read_bytes()) for path in files]


async def apply_migrations(connection, migrations):
    async with connection.transaction():
        await connection.execute("SELECT pg_advisory_xact_lock($1)", LOCK_ID)
        await connection.execute("""CREATE TABLE IF NOT EXISTS workspace_schema_migrations (
            filename TEXT PRIMARY KEY,
            checksum TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
        applied = {row["filename"]: row["checksum"] for row in await connection.fetch(
            "SELECT filename, checksum FROM workspace_schema_migrations"
        )}
        known = {name for name, _ in migrations}
        if applied.keys() - known:
            raise RuntimeError("Database contains unknown workspace migrations")
        for name, contents in migrations:
            checksum = hashlib.sha256(contents).hexdigest()
            if name in applied:
                if applied[name] != checksum:
                    raise RuntimeError(f"Checksum mismatch for {name}")
                continue
            await connection.execute(contents.decode("utf-8"))
            await connection.execute(
                "INSERT INTO workspace_schema_migrations (filename, checksum) VALUES ($1, $2)",
                name, checksum,
            )


async def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL must be set explicitly")
    import asyncpg
    connection = await asyncpg.connect(url)
    try:
        await apply_migrations(connection, load_migrations())
    finally:
        await connection.close()
    print("Workspace migrations applied or already current.")


if __name__ == "__main__":
    asyncio.run(main())
