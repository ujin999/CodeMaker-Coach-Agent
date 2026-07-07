from typing import List
from langchain_core.documents import Document

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        class RecursiveCharacterTextSplitter:
            """Fallback RecursiveCharacterTextSplitter when the dependency is missing in the environment."""
            
            def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150, **kwargs):
                self.chunk_size = chunk_size
                self.chunk_overlap = chunk_overlap

            def split_text(self, text: str) -> List[str]:
                chunks = []
                if not text:
                    return chunks
                start = 0
                while start < len(text):
                    end = start + self.chunk_size
                    chunks.append(text[start:end])
                    # Prevent infinite loop if chunk_size is too small or overlap is too large
                    step = self.chunk_size - self.chunk_overlap
                    if step <= 0:
                        step = self.chunk_size
                    if start + step >= len(text):
                        break
                    start += step
                return chunks

            def split_documents(self, documents: List[Document]) -> List[Document]:
                chunks = []
                for doc in documents:
                    text_chunks = self.split_text(doc.page_content)
                    for chunk_text in text_chunks:
                        chunks.append(Document(page_content=chunk_text, metadata=doc.metadata.copy()))
                return chunks


def split_documents(
    documents: List[Document], 
    chunk_size: int = 1000, 
    chunk_overlap: int = 150
) -> List[Document]:
    """Splits Documents into smaller chunks using RecursiveCharacterTextSplitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True
    )
    return splitter.split_documents(documents)
