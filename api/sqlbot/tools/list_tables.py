import json
from typing import Any, Optional

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools.sql_database.tool import ListSQLDatabaseTool
from pydantic import RedisDsn
from pydantic.v1 import root_validator


class CustomListTablesTool(ListSQLDatabaseTool):
    """Tool for getting tables names.
    Fake because it is not async at all, it's just a wrapper around the sync version.
    """

    name: str = "sql_db_list_tables"
    description: str = (
        "Use this tool to list all tables in the database. "
        "Input to this tool is an empty string, output is a dict with table names as keys and table descriptions as values."
    )

    redis_url: str = "redis://localhost:6379"
    key_prefix: str = "sqlbot:tables:"
    client: Any = None
    # aclient: Any = None

    @root_validator(pre=True)
    def validate_environment(cls, values):
        from redis import Redis

        values["client"] = Redis.from_url(values["redis_url"], decode_responses=True)
        # TODO: async redis need to manually close the connection pool
        # from redis.asyncio import Redis as ARedis
        # values["aclient"] = ARedis.from_url(values["redis_url"], decode_responses=True)
        return values

    def _run(
        self,
        tool_input: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for a specific table."""
        usable_tables = self.db.get_usable_table_names()
        res = {}
        for key in self.client.scan_iter(f"{self.key_prefix}*"):
            table_name = key.removeprefix(self.key_prefix)
            if table_name in usable_tables:
                res[table_name] = self.client.get(key)
        return json.dumps(res, ensure_ascii=False)

    async def _arun(
        self,
        tool_input: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for a specific table."""
        # TODO: async redis need to manually close the connection pool
        return self._run(tool_input, run_manager)
