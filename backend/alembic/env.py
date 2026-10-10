import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure the project root and backend folder are on sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
project_root = os.path.abspath(os.path.join(backend_dir, ".."))

for path in [project_root, backend_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.config import settings
from backend.models import Base

# Alembic Config object
config = context.config

# Interpret config file for logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Dynamically set sqlalchemy.url from our application settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Model metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        configuration = {}
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connect_args = {}
    if "postgresql" in settings.DATABASE_URL:
        connect_args = {"connect_timeout": 2}
    elif "sqlite" in settings.DATABASE_URL:
        connect_args = {"check_same_thread": False}

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
