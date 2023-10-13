from typing import List, Optional

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from langchain.schema import BaseRetriever, Document


from pydantic.v1 import root_validator


class TableRelationshipTool(BaseTool):
    name = "sql_db_table_relationship"
    description = """Use this tool to establish a comprehensive understanding of the relationship between tables. The input for this tool should be the comma separated list of table names, where the key signifies a relationship that can be utilized for the user's question, while the corresponding value represents the precise table join query."""
    retriever: BaseRetriever

    @root_validator(pre=True)
    def validate_environment(cls, values):
        return values

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Document]:
        # TODO: cast input queries to list.
        docs = self.retriever.get_relevant_documents(query=query)
        result = {}
        for doc in docs:
            result[doc.page_content] = doc.metadata["sql_query"]
        return result

    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Document]:
        return self._run(query, run_manager)
