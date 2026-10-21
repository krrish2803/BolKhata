from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings
import logging

logger = logging.getLogger(__name__)

client: AsyncIOMotorClient = None
db: AsyncIOMotorDatabase = None

async def connect_db():
    global client, db
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=500, connectTimeoutMS=500)
        db = client[settings.DATABASE_NAME]
        
        # Test connection
        await client.admin.command('ping')
        logger.info("Successfully connected to external MongoDB")
        await init_db_indexes(db)
    except Exception as e:
        if settings.ENV == "prod":
            logger.critical(f"FATAL: Production mode (ENV=prod) requires reachable external MongoDB at {settings.MONGODB_URI}. Failed with: {e}")
            raise RuntimeError(f"Database connection failed in production: {e}")
        logger.warning(f"External MongoDB unavailable ({e}). Initializing seamless in-memory database fallback for zero-setup demo/testing.")
        from mongomock_motor import AsyncMongoMockClient
        client = AsyncMongoMockClient()
        db = client[settings.DATABASE_NAME]
        await init_db_indexes(db)

async def close_db():
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed")

async def init_db_indexes(database: AsyncIOMotorDatabase):
    """
    Ensure all workspace indexes, unique name indexes, and TTL indexes are established:
    - workspaces: expiresAt TTL index (24h)
    - drafts: createdAt TTL index (1h)
    - customers: workspaceId, unique (workspaceId, name)
    - items: workspaceId, unique (workspaceId, name)
    - entries: workspaceId
    """
    try:
        # 1. workspaces TTL index
        await database.workspaces.create_index("expiresAt", expireAfterSeconds=0)
        
        # 2. drafts TTL index (1 hour = 3600 seconds from createdAt)
        await database.drafts.create_index("createdAt", expireAfterSeconds=3600)
        
        # 3. customers
        await database.customers.create_index("workspaceId")
        await database.customers.create_index([("workspaceId", 1), ("name", 1)], unique=True)
        
        # 4. items
        await database.items.create_index("workspaceId")
        await database.items.create_index([("workspaceId", 1), ("name", 1)], unique=True)
        
        # 5. entries
        await database.entries.create_index("workspaceId")
        await database.entries.create_index([("workspaceId", 1), ("createdAt", -1)])
        
        # 6. users
        await database.users.create_index("phone", unique=True)
        await database.users.create_index("workspaceId")

        # 7. auth_lockouts & rate_limits TTL collection (Mongo-backed with TTL index)
        await database.auth_lockouts.create_index("expiresAt", expireAfterSeconds=0)
        await database.rate_limits.create_index("expiresAt", expireAfterSeconds=0)
        
        logger.info("MongoDB indexes verified & created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")

def get_db() -> AsyncIOMotorDatabase:
    global db, client
    if db is None:
        from mongomock_motor import AsyncMongoMockClient
        client = AsyncMongoMockClient()
        db = client[settings.DATABASE_NAME]
    return db
