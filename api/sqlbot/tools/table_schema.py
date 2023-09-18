from typing import Any, Optional

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools.sql_database.tool import InfoSQLDatabaseTool

from pydantic import RedisDsn, root_validator


class CustomTableSchemaTool(InfoSQLDatabaseTool):
    """Tool for getting metadata about a SQL database.
    Fake because it is not async at all, it's just a wrapper around the sync version.
    """

    name = "sql_db_schema"
    description = """
    Input to this tool is a comma-separated list of table names, output is the schemas and sample rows for those tables.    

    Example Input: "table1, table2, table3"
    """
    redis_url: RedisDsn = "redis://localhost:6379"
    key_prefix: str = "sqlbot:schemas:"
    client: Any = None

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
        table_names: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for tables in a comma-separated list."""
        _table_names = [tn.strip() for tn in table_names.split(",")]
        return self.get_table_info_no_throw(_table_names)

    async def _arun(
        self,
        table_names: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get the schema for tables in a comma-separated list."""
        return self._run(table_names, run_manager)

    def get_table_info_no_throw(self, table_names: Optional[list[str]] = None) -> str:
        """Get information about specified tables.

        Follows best practices as specified in: Rajkumar et al, 2022
        (https://arxiv.org/abs/2204.00498)

        If `sample_rows_in_table_info`, the specified number of sample rows will be
        appended to each table description. This can increase performance as
        demonstrated in the paper.
        """
        try:
            return self.get_table_info(table_names)
        except ValueError as e:
            """Format the error message"""
            return f"Error: {e}"

    def get_table_info(self, table_names: Optional[list[str]] = None) -> str:
        """Get information about specified tables.

        Follows best practices as specified in: Rajkumar et al, 2022
        (https://arxiv.org/abs/2204.00498)

        If `sample_rows_in_table_info`, the specified number of sample rows will be
        appended to each table description. This can increase performance as
        demonstrated in the paper.
        """
        all_table_names = self.db.get_usable_table_names()
        if table_names is not None:
            missing_tables = set(table_names).difference(all_table_names)
            if missing_tables:
                raise ValueError(f"table_names {missing_tables} not found in database")
            all_table_names = table_names

        meta_tables = [
            tbl
            for tbl in self.db._metadata.sorted_tables
            if tbl.name in set(all_table_names)
            and not (self.db.dialect == "sqlite" and tbl.name.startswith("sqlite_"))
        ]

        has_extra_info = (
            self.db._indexes_in_table_info or self.db._sample_rows_in_table_info
        )
        tables = []
        for table in meta_tables:
            table_info = self.client.get(f"{self.key_prefix}{table.name}")
            if not table_info:
                # maybe handle table schema missing?
                continue
            if has_extra_info:
                table_info += "\n\n/*"
            if self.db._indexes_in_table_info:
                table_info += f"\n{self.db._get_table_indexes(table)}\n"
            if self.db._sample_rows_in_table_info:
                table_info += f"\n{self.db._get_sample_rows(table)}\n"
            if has_extra_info:
                table_info += "*/"
            tables.append(table_info)

        final_str = "\n\n".join(tables)
        return final_str
