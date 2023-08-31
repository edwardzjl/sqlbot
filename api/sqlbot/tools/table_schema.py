from typing import Optional

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools.sql_database.tool import InfoSQLDatabaseTool


class FakeAsyncTableSchemaTool(InfoSQLDatabaseTool):
    """Tool for getting metadata about a SQL database.
    Fake because it is not async at all, it's just a wrapper around the sync version.
    """

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
