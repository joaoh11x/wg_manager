from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from sqlalchemy import Integer, MetaData, Table, create_engine, func, select, text
from sqlalchemy.engine import Connection, Engine

# Allow running this script directly: ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load env vars from .env at project root (so running locally "just works")
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

from app.models.base import Base  # noqa: E402
import app.models  # noqa: F401, E402  # register models


def _sqlite_url(sqlite_path: str) -> str:
    p = Path(sqlite_path)
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    return f"sqlite+pysqlite:///{p}"


def _get_database_url() -> str:
    return (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("DATABASE_URI")
        or ""
    )


def _iter_rows_in_chunks(
    conn: Connection,
    stmt,
    chunk_size: int,
) -> Iterable[list[dict]]:
    result = conn.execute(stmt).mappings()
    while True:
        chunk = result.fetchmany(chunk_size)
        if not chunk:
            break
        yield [dict(row) for row in chunk]


def _table_is_empty(conn: Connection, table: Table) -> bool:
    count = conn.execute(select(func.count()).select_from(table)).scalar_one()
    return int(count) == 0


def _truncate_tables_postgres(conn: Connection, tables: list[Table]) -> None:
    # TRUNCATE all tables in one statement to avoid FK ordering issues.
    # Only used when user explicitly requests wiping the target.
    names = ", ".join(f'"{t.name}"' for t in tables)
    conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


def _sync_postgres_sequence(conn: Connection, table: Table) -> None:
    # Only meaningful on PostgreSQL.
    if conn.dialect.name != "postgresql":
        return

    # Adjust sequence for single integer PK tables (so next insert doesn't collide).
    pk_cols = [c for c in table.columns if c.primary_key]
    if len(pk_cols) != 1:
        return

    pk = pk_cols[0]
    if not isinstance(pk.type, Integer):
        return

    seq = conn.execute(
        text("SELECT pg_get_serial_sequence(:tbl, :col)"),
        {"tbl": table.name, "col": pk.name},
    ).scalar()

    if not seq:
        return

    max_id = conn.execute(
        text(f'SELECT COALESCE(MAX("{pk.name}"), 0) FROM "{table.name}"')
    ).scalar()
    conn.execute(text("SELECT setval(:seq::regclass, :val, true)"), {"seq": seq, "val": int(max_id)})


def _ensure_postgres_destination(engine: Engine, postgres_url: str) -> None:
    # Fail fast if the provided URL is not actually Postgres.
    # This avoids silently migrating SQLite -> SQLite when DATABASE_URL points to sqlite.
    if engine.dialect.name != "postgresql":
        raise SystemExit(
            "O destino não parece ser Postgres. "
            f"Dialeto detectado: {engine.dialect.name}. "
            "Informe um --postgres-url começando com 'postgresql+...' (ou ajuste DATABASE_URL). "
            f"Valor atual: {postgres_url}"
        )


def migrate(sqlite_path: str, postgres_url: str, wipe_target: bool, chunk_size: int) -> None:
    sqlite_file = Path(sqlite_path)
    if not sqlite_file.is_absolute():
        sqlite_file = (PROJECT_ROOT / sqlite_file).resolve()
    if not sqlite_file.exists():
        raise SystemExit(f"SQLite não encontrado: {sqlite_file}")

    src_engine = create_engine(_sqlite_url(str(sqlite_file)), future=True)
    dst_engine = create_engine(postgres_url, pool_pre_ping=True, future=True)

    _ensure_postgres_destination(dst_engine, postgres_url)

    # Ensure target schema exists based on ORM
    Base.metadata.create_all(bind=dst_engine)

    # Reflect source (actual columns in the SQLite file)
    src_meta = MetaData()
    src_meta.reflect(bind=src_engine)

    orm_tables = list(Base.metadata.sorted_tables)
    orm_names = {t.name for t in orm_tables}

    with src_engine.connect() as src_conn, dst_engine.begin() as dst_conn:
        if wipe_target:
            _truncate_tables_postgres(dst_conn, orm_tables)
        else:
            # Fail fast if target isn't empty (prevents duplicate/unique conflicts)
            for t in orm_tables:
                if not _table_is_empty(dst_conn, t):
                    raise SystemExit(
                        f"Tabela de destino não está vazia: {t.name}. Use --wipe-target para limpar antes de migrar."
                    )

        for orm_table in orm_tables:
            src_table = src_meta.tables.get(orm_table.name)
            if src_table is None:
                # table didn't exist in SQLite; keep Postgres empty and rely on defaults.
                continue

            # Only copy columns that exist in the SQLite source.
            src_colnames = set(src_table.columns.keys())
            dst_cols = [c for c in orm_table.columns if c.name in src_colnames]
            if not dst_cols:
                continue

            stmt = select(*[src_table.c[c.name] for c in dst_cols])

            total = 0
            for chunk in _iter_rows_in_chunks(src_conn, stmt, chunk_size=chunk_size):
                dst_conn.execute(orm_table.insert(), chunk)
                total += len(chunk)

            print(f"✅ Migrated {total} rows into {orm_table.name}")

        # Optionally migrate extra tables present in SQLite but not represented in ORM.
        # This helps migrating legacy/unused tables without losing data.
        if os.getenv("MIGRATE_EXTRA_TABLES", "").lower() in {"1", "true", "yes", "on"}:
            extra_src_tables = [t for name, t in src_meta.tables.items() if name not in orm_names]
            if extra_src_tables:
                extra_dst_meta = MetaData()
                extra_dst_tables: list[Table] = []
                for t in extra_src_tables:
                    extra_dst_tables.append(t.to_metadata(extra_dst_meta))
                extra_dst_meta.create_all(bind=dst_conn)

                for src_table in extra_src_tables:
                    dst_table = extra_dst_meta.tables[src_table.name]
                    stmt = select(*list(src_table.c))
                    total = 0
                    for chunk in _iter_rows_in_chunks(src_conn, stmt, chunk_size=chunk_size):
                        dst_conn.execute(dst_table.insert(), chunk)
                        total += len(chunk)
                    print(f"✅ Migrated {total} rows into extra table {src_table.name}")

        # Fix sequences
        for t in orm_tables:
            _sync_postgres_sequence(dst_conn, t)

    print("🎉 Migração concluída")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrar dados do SQLite (legado) para Postgres")
    parser.add_argument(
        "--sqlite-path",
        default=os.getenv("SQLITE_PATH", "database.db"),
        help="Caminho do arquivo SQLite (ex.: database.db)",
    )
    parser.add_argument(
        "--postgres-url",
        default=_get_database_url(),
        help="URL do Postgres (ex.: postgresql+psycopg://user:pass@host:5432/dbname)",
    )
    parser.add_argument(
        "--wipe-target",
        action="store_true",
        help="Apaga (TRUNCATE) as tabelas no Postgres antes de migrar",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Tamanho do lote para inserts (default: 1000)",
    )
    parser.add_argument(
        "--include-extra-tables",
        action="store_true",
        help="Também migra tabelas que existam no SQLite mas não estejam no ORM (define MIGRATE_EXTRA_TABLES=1)",
    )

    args = parser.parse_args()

    if not args.postgres_url:
        raise SystemExit(
            "Postgres URL não informada. Use --postgres-url ou defina DATABASE_URL. "
            "Ex.: postgresql+psycopg://user:pass@localhost:5432/wireguard_manager"
        )

    if args.include_extra_tables:
        os.environ["MIGRATE_EXTRA_TABLES"] = "1"

    migrate(
        sqlite_path=args.sqlite_path,
        postgres_url=args.postgres_url,
        wipe_target=bool(args.wipe_target),
        chunk_size=int(args.chunk_size),
    )


if __name__ == "__main__":
    main()
