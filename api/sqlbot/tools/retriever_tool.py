from typing import List, Optional

from langchain.callbacks.manager import CallbackManagerForToolRun
from langchain.tools import BaseTool
from langchain.schema import BaseRetriever, Document


from pydantic.v1 import root_validator


class RetrieverTool(BaseTool):
    name = "sql_get_similar_examples"
    description = """Use this tool to gain an understanding of comparable examples that can be customized to fit the user's question. Always use this tool as an initial step. The input for this tool should be the user's question. The output is a JSON object, where the key represents a question similar to the user's question, and the corresponding value is the accurate SQL query that resolves that question."""
    retriever: BaseRetriever

    @root_validator(pre=True)
    def validate_environment(cls, values):
        return values

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Document]:
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
