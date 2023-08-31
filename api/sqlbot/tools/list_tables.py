import json
from typing import Any, Optional

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools.sql_database.tool import ListSQLDatabaseTool
from pydantic import root_validator


class FakeAsyncListTablesTool(ListSQLDatabaseTool):
    """Tool for getting tables names.
    Fake because it is not async at all, it's just a wrapper around the sync version.
    """

    name: str = "sql_db_list_tables"
    description: str = """
    Use this tool to list all tables in the database.
    Input to this tool is an empty string, output is a comma separated list of table names in the database.
    """
    schema_file: str = "schema.json"
    schemas: Any = None

    @root_validator(pre=True)
    def load_schemas(cls, values):
        if "schema_file" in values:
            with open(values["schema_file"]) as f:
                values["schemas"] = json.load(f)
        # TODO: error handling

    def _run(
        self,
        tool_input: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for a specific table."""
        return {
            table_name: self.schemas[table_name]
            for table_name in self.db.get_usable_table_names()
        }

    async def _arun(
        self,
        tool_input: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for a specific table."""
        return self._run(tool_input, run_manager)
