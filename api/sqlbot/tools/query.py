from typing import Optional

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools.sql_database.tool import QuerySQLDataBaseTool


class FakeAsyncQuerySQLDataBaseTool(QuerySQLDataBaseTool):
    """Tool for querying a SQL database.
    Fake because it is not async at all, it's just a wrapper around the sync version.
    """

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
