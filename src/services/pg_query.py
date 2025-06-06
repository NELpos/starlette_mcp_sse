import asyncpg
import os
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server for PostgreSQL queries
pg_query_mcp = FastMCP("pg_query")

# --- Configuration ---
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "mydatabase")

DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Global connection pool
_db_pool: Optional[asyncpg.Pool] = None

async def get_db_pool() -> asyncpg.Pool:
    """Initializes and returns the database connection pool."""
    global _db_pool
    if _db_pool is None:
        try:
            _db_pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=10)
            print(f"Successfully connected to PostgreSQL database: {DB_NAME} on {DB_HOST}:{DB_PORT}")
        except Exception as e:
            print(f"Error creating PostgreSQL connection pool: {e}")
            raise
    return _db_pool

async def _execute_query(query: str, params: Optional[List[Any]] = None, fetch_all: bool = False, fetch_one: bool = False, execute_only: bool = False) -> Any:
    """
    Internal helper to execute SQL queries.
    Manages connection acquisition and release.
    """
    if not DB_USER or not DB_HOST or not DB_NAME: # Simple check
        return {"error": "Database connection details (DB_USER, DB_HOST, DB_NAME) must be configured in environment variables."}

    pool = await get_db_pool()
    async with pool.acquire() as connection:
        async with connection.transaction(): # Start a transaction
            try:
                if fetch_all:
                    rows = await connection.fetch(query, *params if params else [])
                    return [dict(row) for row in rows]
                elif fetch_one:
                    row = await connection.fetchrow(query, *params if params else [])
                    return dict(row) if row else None
                elif execute_only: # For INSERT, UPDATE, DELETE that don't need to return rows by default
                    status = await connection.execute(query, *params if params else [])
                    # status is like 'INSERT 0 1' or 'UPDATE 5'
                    return {"status": status}
                else: # Default for statements like INSERT ... RETURNING
                    # This is more flexible if the query itself specifies what to return
                    result = await connection.fetch(query, *params if params else [])
                    return [dict(row) for row in result]

            except asyncpg.PostgresError as e:
                # More specific error handling can be added here
                return {"error": f"Database query error: {type(e).__name__} - {str(e)}", "query": query, "params": params}
            except Exception as e:
                return {"error": f"An unexpected error occurred during query execution: {str(e)}", "query": query, "params": params}

@pg_query_mcp.tool()
async def select_from_table(
    table_name: str,
    columns: Union[List[str], str] = "*",
    where_clause: Optional[str] = None,
    query_params: Optional[List[Any]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Selects data from a specified table.
    Supports dynamic columns, WHERE clauses, ordering, and pagination.
    For vector similarity search, columns can include distance calculations (e.g., 'embedding <=> $1 AS distance')
    and order_by can use this distance.

    Args:
        table_name: The name of the table to query.
        columns: A list of column names or a single string (e.g., "*", "id, name", "data, embedding <=> $1 AS distance").
        where_clause: The WHERE clause string (e.g., "status = $1 AND category = $2", "id = $1"). Placeholders ($1, $2) are used for query_params.
        query_params: A list of parameters to substitute into the where_clause.
        order_by: The ORDER BY clause string (e.g., "created_at DESC", "distance ASC").
        limit: The maximum number of rows to return.
        offset: The number of rows to skip before starting to return rows.
    """
    if isinstance(columns, list):
        col_str = ", ".join(columns)
    else:
        col_str = columns

    query = f"SELECT {col_str} FROM {table_name}"
    current_param_idx = 0

    # Re-index parameters if they are already in where_clause
    # This is a simplified approach; a more robust SQL builder might be needed for complex scenarios.
    # For now, we assume query_params are ordered correctly for the where_clause.
    
    if where_clause:
        query += f" WHERE {where_clause}"
        if query_params:
             # Example: if where_clause is "name = $1 and age > $2", query_params = ["John", 30]
             # No re-indexing needed if params are passed in order.
            pass


    if order_by:
        query += f" ORDER BY {order_by}"
    if limit is not None:
        current_param_idx += 1
        query += f" LIMIT ${current_param_idx + (len(query_params) if query_params else 0)}"
        query_params = (query_params or []) + [limit]
    if offset is not None:
        current_param_idx += 1
        query += f" OFFSET ${current_param_idx + (len(query_params) -1 if query_params and limit is not None else len(query_params) if query_params else 0)}" # Adjust index carefully
        query_params = (query_params or []) + [offset]


    return await _execute_query(query, params=query_params, fetch_all=True)

@pg_query_mcp.tool()
async def insert_into_table(
    table_name: str,
    data: Dict[str, Any],
    returning_columns: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Inserts a new row into the specified table.

    Args:
        table_name: The name of the table.
        data: A dictionary where keys are column names and values are the values to insert.
        returning_columns: Optional list of column names to return after insertion (e.g., ["id"]).
    """
    columns = ", ".join(data.keys())
    placeholders = ", ".join([f"${i+1}" for i in range(len(data))])
    values = list(data.values())

    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    if returning_columns:
        query += f" RETURNING {', '.join(returning_columns)}"
        return await _execute_query(query, params=values, fetch_all=True) # fetch_all to handle multiple returning cols or if one day we support multi-row insert here
    else:
        return await _execute_query(query, params=values, execute_only=True)


@pg_query_mcp.tool()
async def update_table(
    table_name: str,
    set_values: Dict[str, Any],
    where_clause: str,
    query_params: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Updates existing rows in the specified table.

    Args:
        table_name: The name of the table.
        set_values: A dictionary of columns to update and their new values.
        where_clause: The WHERE clause to specify which rows to update (e.g., "id = $1").
        query_params: Parameters for the WHERE clause and set_values if placeholders are used there.
                      Order should be: [params_for_set_clause..., params_for_where_clause...]
    """
    set_clauses = []
    current_param_idx = 1
    update_params = []

    for key, value in set_values.items():
        set_clauses.append(f"{key} = ${current_param_idx}")
        update_params.append(value)
        current_param_idx += 1
    
    set_str = ", ".join(set_clauses)
    
    # Adjust placeholders in where_clause if needed
    # For simplicity, assume where_clause placeholders start after set_values placeholders
    # e.g., if set_values has 2 items, where_clause "id = $3"
    # This requires careful construction of query_params by the caller or GenAI
    
    query = f"UPDATE {table_name} SET {set_str} WHERE {where_clause}"
    
    final_params = update_params + (query_params if query_params else [])
    
    return await _execute_query(query, params=final_params, execute_only=True)

@pg_query_mcp.tool()
async def delete_from_table(
    table_name: str,
    where_clause: str,
    query_params: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Deletes rows from the specified table.

    Args:
        table_name: The name of the table.
        where_clause: The WHERE clause to specify which rows to delete (e.g., "status = $1").
        query_params: Parameters for the WHERE clause.
    """
    query = f"DELETE FROM {table_name} WHERE {where_clause}"
    return await _execute_query(query, params=query_params, execute_only=True)

if __name__ == "__main__":
    import asyncio

    async def main():
        # Example: Ensure your .env file has DB_USER, DB_PASSWORD, DB_HOST, DB_NAME
        # And that the database and tables exist.
        print("PostgreSQL Query MCP Server - Standalone Test Mode")
        print(f"Attempting to connect to: {DB_URL}")

        # This is just to initialize the pool for testing if run directly
        try:
            await get_db_pool() 
            print("DB Pool should be initialized if credentials are correct.")
            # Example usage (requires a 'test_items' table)
            # await _execute_query("CREATE TABLE IF NOT EXISTS test_items (id SERIAL PRIMARY KEY, name TEXT, value INT);")
            # print(await insert_into_table("test_items", {"name": "Test Item", "value": 100}, returning_columns=["id"]))
            # print(await select_from_table("test_items", where_clause="name = $1", query_params=["Test Item"]))
        except Exception as e:
            print(f"Error in main test: {e}")
        finally:
            if _db_pool:
                await _db_pool.close()
                print("DB Pool closed.")
    
    # To run the MCP server itself (this part is more for integration with Starlette)
    # pg_query_mcp.run(transport="sse") 
    # For direct script execution, the above main() is for testing connection and tools.
    
    if not all(os.environ.get(var) for var in ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"]):
        print("Error: Database environment variables (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME) must be set.")
    else:
        asyncio.run(main())
        print("\nTo run the full MCP server, integrate with Starlette and run through server.py.")
        print("Available tools:")
        for tool_name in pg_query_mcp.tools:
            print(f"- {tool_name}")
