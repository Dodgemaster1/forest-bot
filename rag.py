import asyncio
import io
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Settings, SimpleDirectoryReader, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.llms.groq import Groq

from dirs import EMBEDDINGS_DIR, FOREST_ARCHIVE_DIR

load_dotenv()

# Settings.embed_model = FastEmbedEmbedding(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
# Settings.embed_model = FastEmbedEmbedding(model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
Settings.embed_model = FastEmbedEmbedding(model_name="intfloat/multilingual-e5-large")
Settings.llm = Groq(
    model="openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
    max_tokens=3000,
    additional_kwargs={
        "top_p": 1,
        "reasoning_effort": "low",
    },
)
Settings.node_parser = SentenceSplitter(
    chunk_size=512,
    chunk_overlap=50,
)


class RAG:
    def __init__(self) -> None:
        self.setup()
        self._reload_query_engine()

    def setup(self) -> None:
        if not EMBEDDINGS_DIR.exists():
            documents = SimpleDirectoryReader(FOREST_ARCHIVE_DIR).load_data(num_workers=6)
            self.index = VectorStoreIndex.from_documents(
                documents, transformations=[Settings.node_parser], show_progress=True
            )
            self.index.storage_context.persist(persist_dir=str(EMBEDDINGS_DIR))
        else:
            storage_context = StorageContext.from_defaults(persist_dir=str(EMBEDDINGS_DIR))
            self.index = load_index_from_storage(storage_context)

    async def add_document(self, document: io.BytesIO, save_name: str) -> None:
        await asyncio.to_thread(self._add_document, document, save_name)

    def _add_document(self, document: io.BytesIO, save_name: str) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / save_name
            file_path.write_bytes(document.getbuffer())

            documents = SimpleDirectoryReader(tmp_dir).load_data()

            if documents:
                self.index.insert(documents[0])
                self._reload_query_engine()
                self.index.storage_context.persist(persist_dir=str(EMBEDDINGS_DIR))

    async def generate_answer(self, query: str) -> tuple[str, str]:
        response = await self.query_engine.aquery(query)
        return str(response), response.source_nodes[0].metadata.get("file_name", "") if response.source_nodes else ""

    def _reload_query_engine(self) -> None:
        self.query_engine = self.index.as_query_engine(
            similarity_top_k=3,
            response_mode="compact",
        )


if __name__ == "__main__":
    _rag = RAG()
