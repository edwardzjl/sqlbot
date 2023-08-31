"""Toolkit for interacting with a SQL database."""

from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.tools import BaseTool
from langchain.tools.sql_database.tool import QuerySQLCheckerTool

from sqlbot.agent.tools import (
    FakeAsyncInfoSQLDatabaseTool,
    FakeAsyncListSQLDatabaseTool,
    FakeAsyncQuerySQLDataBaseTool,
)


class CustomSQLDatabaseToolkit(SQLDatabaseToolkit):
    def get_tools(self) -> list[BaseTool]:
        """Get the tools in the toolkit."""
        list_sql_database_tool_description = (
            "Use this tool to list all table names in the database. "
            "Input to this tool is an empty string, output is a comma separated list of table names in the database."
        )
        list_sql_database_tool = FakeAsyncListSQLDatabaseTool(
            db=self.db, description=list_sql_database_tool_description
        )
        info_sql_database_tool_description = (
            "Use this tool to get the schema of specific tables. "
            "Input to this tool is a comma-separated list of tables, output is the "
            "schema and sample rows for those tables. "
            "Be sure that the tables actually exist by calling "
            f"{list_sql_database_tool.name} first! "
            "Example Input: 'table1, table2, table3'"
        )
        info_sql_database_tool = FakeAsyncInfoSQLDatabaseTool(
            db=self.db, description=info_sql_database_tool_description
        )
        query_sql_database_tool_description = (
            "Use this tool to execute query and get result from the database. "
            "Input to this tool is a SQL query, output is a result from the database. "
            "If the query is not correct, an error message will be returned. "
            "If an error is returned, rewrite the query and try again. "
            "If you encounter an issue with Unknown column "
            f"'xxxx' in 'field list', or no such column 'xxxx', use {info_sql_database_tool.name} "
            "to query the correct table columns."
        )
        query_sql_database_tool = FakeAsyncQuerySQLDataBaseTool(
            db=self.db, description=query_sql_database_tool_description
        )
        query_sql_checker_tool_description = (
            "Use this tool to check if your query is correct before executing "
            "it. Always use this tool before executing a query with "
            f"{query_sql_database_tool.name}!"
        )
        query_sql_checker_tool = QuerySQLCheckerTool(
            db=self.db, llm=self.llm, description=query_sql_checker_tool_description
        )
        return [
            query_sql_database_tool,
            info_sql_database_tool,
            list_sql_database_tool,
            query_sql_checker_tool,
        ]
