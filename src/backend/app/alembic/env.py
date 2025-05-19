from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
from sqlmodel import SQLModel

from app.core.config.settings import settings

# Load Alembic configurations
config = context.config
fileConfig(config.config_file_name)

# Set the database URL in Alembic config
# When running locally, replace the container name with localhost
db_url = settings.SQLALCHEMY_DATABASE_URI
config.set_main_option("sqlalchemy.url", db_url)

# Import all models so they're registered with SQLModel metadata
# Import order matters to avoid circular references
import app.core.models.user
import app.core.models.refresh_token
import app.core.models.document
import app.core.models.monitoring
import app.core.models.llm
import app.core.models.pipeline
import app.core.models.retrieval

# Target metadata for Alembic - use SQLModel's metadata
target_metadata = SQLModel.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Use connection settings from config instead of imported engine
    # This ensures we use the modified URL with localhost
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
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
