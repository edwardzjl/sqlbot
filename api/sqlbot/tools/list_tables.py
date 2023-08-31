from typing import Optional

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools.sql_database.tool import ListSQLDatabaseTool


class FakeAsyncListTablesTool(ListSQLDatabaseTool):
    """Tool for getting tables names.
    Fake because it is not async at all, it's just a wrapper around the sync version.
    """

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
