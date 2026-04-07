import os
import re
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


_schema_name_re = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def get_database_schema() -> str | None:
    """Return the desired Postgres schema name, if configured.

    Set one of:
      - DB_SCHEMA
      - POSTGRES_SCHEMA
      - DATABASE_SCHEMA
    """

    schema = (
        os.getenv("DB_SCHEMA")
        or os.getenv("POSTGRES_SCHEMA")
        or os.getenv("DATABASE_SCHEMA")
        or ""
    ).strip()

    if not schema:
        return None

    if not _schema_name_re.match(schema):
        raise RuntimeError(
            "Invalid DB schema name in DB_SCHEMA/POSTGRES_SCHEMA/DATABASE_SCHEMA. "
            "Use only letters, numbers and underscore, starting with a letter/underscore."
        )

    return schema

class DatabaseConnection:
    """
    Classe para gerenciar conexões SQLAlchemy com o banco de dados.

    A aplicação foi migrada para Postgres. Configure a URL via env var:
      DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname

    Compatibilidade:
    - Ainda aceita receber uma URL explícita no construtor.
    """

    def __init__(self, database_url: str | None = None, schema: str | None = None):
        self.database_url = (database_url or get_database_url()).strip()
        if not self.database_url:
            raise RuntimeError(
                "DATABASE_URL não configurada. Ex.: postgresql+psycopg://user:pass@localhost:5432/wireguard_manager"
            )

        self.schema = schema if schema is not None else get_database_schema()

        # Use a cached engine per URL (safe for typical Flask usage).
        self.engine = get_engine(self.database_url, self.schema)
    
    def get_engine(self):
        """Retorna o engine SQLAlchemy"""
        return self.engine


def get_database_url() -> str:
    # Preferência: DATABASE_URL (padrão do ecossistema), depois SQLALCHEMY_DATABASE_URI.
    return (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("DATABASE_URI")
        or ""
    )


@lru_cache(maxsize=8)
def get_engine(database_url: str, schema: str | None = None) -> Engine:
    connect_args = {}

    # Only apply schema/search_path to Postgres.
    if schema and database_url.startswith("postgresql"):
        # Keep public as fallback for extensions/default objects.
        connect_args["options"] = f"-csearch_path={schema},public"

    return create_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def ensure_database_schema(engine: Engine | None = None) -> None:
    """Garante que as tabelas existem no banco.

    Nota: isso cria tabelas ausentes (idempotente), mas não faz ALTER em schema existente.
    Para migrações versionadas, o ideal é Alembic.
    """

    from app.models.base import Base
    # Importa modelos para registrar no metadata
    import app.models  # noqa: F401

    eng = engine or DatabaseConnection().engine
    Base.metadata.create_all(bind=eng)