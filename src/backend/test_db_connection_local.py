import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config.settings import settings
import os

async def test_connection():
    """Test database connection using modified connection settings for local testing."""
    # Create a modified connection string that uses localhost instead of container name
    db_uri = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@localhost:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    
    print(f"Attempting to connect to: {db_uri}")
    
    # Create async engine with echo for verbose output
    engine = create_async_engine(db_uri, echo=True)
    
    try:
        # Test connection with a simple query
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Connection successful! Result: {result.scalar()}")
    except Exception as e:
        print(f"Connection failed with error: {e}")
    finally:
        # Dispose of the engine
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection()) 