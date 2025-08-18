"""Base repository class for The Robot Overlord API."""

from abc import ABC
from abc import abstractmethod
from typing import Any
from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection


class BaseRepository[T](ABC):
    """Base repository class with common database operations."""

    def __init__(self, table_name: str):
        self.table_name = table_name

    @abstractmethod
    def _record_to_model(self, record: Record) -> T:
        """Convert database record to model instance."""

    async def get_by_pk(self, pk: UUID) -> T | None:
        """Get a record by primary key."""
        query = f"SELECT * FROM {self.table_name} WHERE pk = $1"

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, pk)
            return self._record_to_model(record) if record else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """Get all records with pagination."""
        query = f"""
            SELECT * FROM {self.table_name}
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit, offset)
            return [self._record_to_model(record) for record in records]

    async def count(
        self, where_clause: str = "", params: list[Any] | None = None
    ) -> int:
        """Count records with optional where clause."""
        if params is None:
            params = []

        query = f"SELECT COUNT(*) FROM {self.table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        async with get_db_connection() as connection:
            result = await connection.fetchval(query, *params)
            return result or 0

    async def exists(self, pk: UUID) -> bool:
        """Check if a record exists by primary key."""
        query = f"SELECT EXISTS(SELECT 1 FROM {self.table_name} WHERE pk = $1)"

        async with get_db_connection() as connection:
            result = await connection.fetchval(query, pk)
            return bool(result)

    async def delete_by_pk(self, pk: UUID) -> bool:
        """Delete a record by primary key."""
        query = f"DELETE FROM {self.table_name} WHERE pk = $1"

        async with get_db_connection() as connection:
            result = await connection.execute(query, pk)
            return result == "DELETE 1"

    async def create_from_dict(self, data: dict[str, Any]) -> T:
        """Create a new record."""
        columns = list(data.keys())
        placeholders = [f"${i + 1}" for i in range(len(columns))]
        values = list(data.values())

        query = f"""
            INSERT INTO {self.table_name} ({", ".join(columns)})
            VALUES ({", ".join(placeholders)})
            RETURNING *
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, *values)
            if record is None:
                raise ValueError(f"Failed to create record in {self.table_name}")
            return self._record_to_model(record)

    async def update_from_dict(self, pk: UUID, data: dict[str, Any]) -> T | None:
        """Update a record by primary key."""
        if not data:
            return await self.get_by_pk(pk)

        # Add updated_at timestamp
        data["updated_at"] = "NOW()"

        set_clauses = []
        values = []
        param_count = 1

        for column, value in data.items():
            if value == "NOW()":
                set_clauses.append(f"{column} = NOW()")
            else:
                set_clauses.append(f"{column} = ${param_count}")
                values.append(value)
                param_count += 1

        values.append(pk)  # Add PK for WHERE clause

        query = f"""
            UPDATE {self.table_name}
            SET {", ".join(set_clauses)}
            WHERE pk = ${param_count}
            RETURNING *
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, *values)
            return self._record_to_model(record) if record else None

    async def find_by(self, **kwargs) -> list[T]:
        """Find records by field values."""
        if not kwargs:
            return await self.get_all()

        conditions = []
        values = []
        param_count = 1

        for field, value in kwargs.items():
            conditions.append(f"{field} = ${param_count}")
            values.append(value)
            param_count += 1

        query = f"""
            SELECT * FROM {self.table_name}
            WHERE {" AND ".join(conditions)}
            ORDER BY created_at DESC
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, *values)
            return [self._record_to_model(record) for record in records]

    async def find_one_by(self, **kwargs) -> T | None:
        """Find a single record by field values."""
        results = await self.find_by(**kwargs)
        return results[0] if results else None
