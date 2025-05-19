import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config.settings import settings

async def test_connection():
    """Test database connection using project settings."""
    print(f"Attempting to connect to: {settings.SQLALCHEMY_DATABASE_URI}")
    
    # Create async engine with echo for verbose output
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
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