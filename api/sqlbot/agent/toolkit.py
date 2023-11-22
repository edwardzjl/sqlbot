"""Toolkit for interacting with a SQL database."""
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.tools import BaseTool
from langchain.tools.sql_database.tool import (
    InfoSQLDatabaseTool,
    QuerySQLCheckerTool,
    QuerySQLDataBaseTool,
)

from sqlbot.tools import QUERY_CHECKER_PROMPT, ListTableTool


class SQLBotToolkit(SQLDatabaseToolkit):
    redis_url: str = "redis://localhost:6379"

    def get_tools(self) -> list[BaseTool]:
        """Get the tools in the toolkit."""
        list_table_tool = ListTableTool(db=self.db, redis_url=self.redis_url)

        table_schema_tool_name = "table_schema_tool"
        table_schema_tool_desc = f"""
- {table_schema_tool_name}:
  - Description: {table_schema_tool_name} can be used to get schema of specific tables. Be sure that the tables actually exist by calling {list_table_tool.name} first!
  - Usage Schema: When involking {table_schema_tool_name}, ensure that you provide a JSON object adhering to the following schema:

    ```yaml
    ToolRequest:
      type: object
      properties:
        tool_name:
          type: string
          enum: ["{table_schema_tool_name}"]
        tool_input:
          type: string
          description: a comma-separated list of table names for which you wish to retrieve the schema
      required: [tool_name, tool_input]
    ```"""
        table_schema_tool = InfoSQLDatabaseTool(
            db=self.db,
            name=table_schema_tool_name,
            description=table_schema_tool_desc,
        )

        query_executor_tool_name = "query_executor"
        query_executor_tool_desc = f"""
- {query_executor_tool_name}:
  - Description: {query_executor_tool_name} can be used to execute query and get result from the database. If the query is not correct, an error message will be returned. If an error is returned, rewrite the query and try again. If you encounter an issue with Unknown column 'xxxx' in 'field list', or no such column 'xxxx', use {table_schema_tool.name} to get the correct table columns.
  - Usage Schema: When involking {query_executor_tool_name}, ensure that you provide a JSON object adhering to the following schema:

    ```yaml
    ToolRequest:
      type: object
      properties:
        tool_name:
          type: string
          enum: ["{query_executor_tool_name}"]
        tool_input:
          type: string
          description: the SQL query you want to execute
      required: [tool_name, tool_input]
    ```"""
        query_executor_tool = QuerySQLDataBaseTool(
            db=self.db,
            name=query_executor_tool_name,
            description=query_executor_tool_desc,
        )

        query_checker_tool_name = "query_checker"
        query_checker_tool_desc = f"""
- {query_checker_tool_name}:
  - Description: {query_checker_tool_name} can be used to check if your query is correct before executing it. Always use this tool before executing a query with {query_executor_tool.name}.
  - Usage Schema: When involking {query_checker_tool_name}, ensure that you provide a JSON object adhering to the following schema:

    ```yaml
    ToolRequest:
      type: object
      properties:
        tool_name:
          type: string
          enum: ["{query_checker_tool_name}"]
        tool_input:
          type: string
          description: the SQL query you want to check
      required: [tool_name, tool_input]
    ```"""
        query_checker_tool = QuerySQLCheckerTool(
            db=self.db,
            llm=self.llm,
            name=query_checker_tool_name,
            description=query_checker_tool_desc,
            template=QUERY_CHECKER_PROMPT,
        )

        return [
            list_table_tool,
            table_schema_tool,
            query_checker_tool,
            query_executor_tool,
        ]
