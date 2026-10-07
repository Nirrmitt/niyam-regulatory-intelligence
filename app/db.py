from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import asyncpg


class PoolManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[asyncpg.Pool]:
        pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)
        self.pool = pool
        try:
            yield pool
        finally:
            await pool.close()
            self.pool = None
