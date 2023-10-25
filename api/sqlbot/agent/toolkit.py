"""Toolkit for interacting with a SQL database."""

from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.tools import BaseTool
from langchain.tools.sql_database.tool import QuerySQLCheckerTool
from pydantic import RedisDsn

from sqlbot.tools import (
    CustomListTablesTool,
    CustomTableSchemaTool,
    FakeAsyncQuerySQLDataBaseTool,
)
from sqlbot.tools.prompt import QUERY_CHECKER


class SQLBotToolkit(SQLDatabaseToolkit):
    redis_url: str = "redis://localhost:6379"
    conversation_id: str

    def get_tools(self) -> list[BaseTool]:
        """Get the tools in the toolkit."""
        list_tables_tool = CustomListTablesTool(db=self.db, redis_url=self.redis_url)
        table_schema_tool_description = (
            "Use this tool to get the schema of specific tables. "
            "Input to this tool is a comma-separated list of tables, output is the "
            "schema and sample rows for those tables. "
            "Be sure that the tables actually exist by calling "
            f"{list_tables_tool.name} first! "
            "Example Input: 'table1, table2, table3'"
        )
        table_schema_tool = CustomTableSchemaTool(
            db=self.db,
            description=table_schema_tool_description,
            redis_url=self.redis_url,
        )
        query_sql_database_tool_description = (
            "Use this tool to execute query and get result from the database. "
            "Input to this tool is a SQL query, output is a result from the database. "
            "If the query is not correct, an error message will be returned. "
            "If an error is returned, rewrite the query and try again. "
            "If you encounter an issue with Unknown column "
            f"'xxxx' in 'field list', or no such column 'xxxx', use {table_schema_tool.name} "
            "to get the correct table columns."
        )
        query_sql_database_tool = FakeAsyncQuerySQLDataBaseTool(
            db=self.db,
            description=query_sql_database_tool_description,
            # callbacks=[human_approval_callback_handler],
        )
        query_sql_checker_tool_description = (
            "Use this tool to check if your query is correct before executing "
            "it. Always use this tool before executing a query with "
            f"{query_sql_database_tool.name}!"
        )
        query_sql_checker_tool = QuerySQLCheckerTool(
            db=self.db,
            llm=self.llm,
            description=query_sql_checker_tool_description,
            template=QUERY_CHECKER,
        )
        return [
            list_tables_tool,
            table_schema_tool,
            query_sql_checker_tool,
            query_sql_database_tool,
        ]
