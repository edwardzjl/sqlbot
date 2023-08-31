from typing import Optional

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools.sql_database.tool import (
    InfoSQLDatabaseTool,
    ListSQLDatabaseTool,
    QuerySQLDataBaseTool,
)


class FakeAsyncListSQLDatabaseTool(ListSQLDatabaseTool):
    """Tool for getting tables names."""

    name = "sql_db_list_tables"
    description = """
    Use this tool to list all table names in the database.
    Input to this tool is an empty string, output is a comma separated list of table names in the database.
    """

    async def _arun(
        self,
        tool_input: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for a specific table."""
        return self._run(tool_input, run_manager)


class FakeAsyncInfoSQLDatabaseTool(InfoSQLDatabaseTool):
    """Tool for getting metadata about a SQL database."""

    name = "sql_db_schema"
    description = """
    Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables.    

    Example Input: "table1, table2, table3"
    """

    async def _arun(
        self,
        table_names: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for tables in a comma-separated list."""
        return self._run(table_names, run_manager)


class FakeAsyncQuerySQLDataBaseTool(QuerySQLDataBaseTool):
    """Tool for querying a SQL database."""

    name = "sql_db_query"
    description = """
    Input to this tool is a detailed and correct SQL query, output is a result from the database.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    """

    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute the query, return the results or an error message."""
        return self._run(query, run_manager)
