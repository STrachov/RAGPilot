from sqlmodel import SQLModel

# SQLModel replaces the need for a separate Base class
# This file is kept for backward compatibility
# New models should use SQLModel directly with table=True

# For Alembic migrations and schema reflection
SQLModel.metadata  # Access metadata for schema generation

