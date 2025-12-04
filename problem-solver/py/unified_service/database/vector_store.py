"""
ChromaDB vector store utilities
"""
import logging
from typing import List, Optional
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredHTMLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from config import settings
from utils.exceptions import DatabaseException

logger = logging.getLogger(__name__)

# Initialize components
_text_splitter = None
_embedding_function = None
_vectorstore = None


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """Get text splitter instance"""
    global _text_splitter
    if _text_splitter is None:
        _text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len
        )
    return _text_splitter


def get_embedding_function() -> HuggingFaceEmbeddings:
    """Get embedding function instance"""
    global _embedding_function
    if _embedding_function is None:
        logger.info(f"Initializing embeddings with model: {settings.embedding_model}")
        _embedding_function = HuggingFaceEmbeddings(
            model_name=settings.embedding_model
        )
    return _embedding_function


def get_vectorstore() -> Chroma:
    """Get vector store instance"""
    global _vectorstore
    if _vectorstore is None:
        logger.info(f"Initializing Chroma with persist directory: {settings.chroma_persist_directory}")
        _vectorstore = Chroma(
            persist_directory=settings.chroma_persist_directory,
            embedding_function=get_embedding_function()
        )
    return _vectorstore


def load_and_split_document(file_path: str) -> List[Document]:
    """
    Load and split document into chunks
    
    Args:
        file_path: Path to document file
        
    Returns:
        List of document chunks
    """
    try:
        # Determine loader based on file extension
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith('.docx'):
            loader = Docx2txtLoader(file_path)
        elif file_path.endswith('.html'):
            loader = UnstructuredHTMLLoader(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")
        
        # Load and split
        documents = loader.load()
        total_chars = sum(len(doc.page_content) for doc in documents)
        text_splitter = get_text_splitter()
        chunks = text_splitter.split_documents(documents)
        
        # Calculate statistics
        if chunks:
            chunk_sizes = [len(chunk.page_content) for chunk in chunks]
            avg_chunk_size = sum(chunk_sizes) / len(chunks)
            min_chunk_size = min(chunk_sizes)
            max_chunk_size = max(chunk_sizes)
            
            # Estimate tokens (approximate: 1 token ≈ 3-4 chars for Russian/English mixed text)
            # Using 3.5 as average for mixed content
            avg_tokens_per_chunk = int(avg_chunk_size / 3.5)
            total_tokens = int(total_chars / 3.5)
            
            logger.info(
                f"Loaded and split {file_path}: {len(documents)} pages, "
                f"{total_chars:,} total chars ({total_tokens:,} est. tokens) → {len(chunks)} chunks\n"
                f"  Chunk stats: avg {avg_chunk_size:.0f} chars ({avg_tokens_per_chunk} tokens), "
                f"min {min_chunk_size}, max {max_chunk_size} (target: {settings.chunk_size} chars, ~{int(settings.chunk_size/3.5)} tokens)"
            )
        else:
            logger.warning(f"No chunks created from {file_path}")
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error loading document {file_path}: {e}")
        raise DatabaseException(f"Failed to load document: {str(e)}")


def index_document(file_path: str, file_id: int) -> bool:
    """
    Index document to vector store
    
    Args:
        file_path: Path to document file
        file_id: Document ID
        
    Returns:
        True if successful
    """
    try:
        logger.info(f"Starting to index document: {file_path} (file_id: {file_id})")
        
        # Load and split document
        chunks = load_and_split_document(file_path)
        logger.info(f"Document split into {len(chunks)} chunks")
        
        # Add file_id to metadata
        for chunk in chunks:
            chunk.metadata['file_id'] = file_id
            chunk.metadata['source'] = file_path
        
        # Add to vector store
        vectorstore = get_vectorstore()
        logger.info(f"Adding {len(chunks)} chunks to vector store...")
        vectorstore.add_documents(chunks)
        logger.info(f"Successfully added chunks to vector store")
        
        # Verify indexing with multiple checks
        logger.info(f"Verifying indexing for file_id {file_id}...")
        
        # Check 1: Count chunks by file_id
        try:
            all_docs = vectorstore.get(where={"file_id": file_id})
            indexed_count = len(all_docs.get('ids', [])) if all_docs else 0
            logger.info(f"Verification 1: Found {indexed_count} chunks with file_id {file_id} in vector store")
            
            if indexed_count != len(chunks):
                logger.warning(
                    f"Mismatch: expected {len(chunks)} chunks, but found {indexed_count} in vector store. "
                    f"This might indicate a partial indexing issue."
                )
        except Exception as e:
            logger.warning(f"Could not verify chunk count: {e}")
        
        # Check 2: Test search functionality
        try:
            test_results = vectorstore.similarity_search("test", k=min(3, len(chunks)), filter={"file_id": file_id})
            logger.info(f"Verification 2: Search test returned {len(test_results)} chunks (expected: {min(3, len(chunks))})")
            
            if test_results:
                sample_chunk = test_results[0]
                logger.debug(f"Sample chunk preview: {sample_chunk.page_content[:100]}...")
        except Exception as e:
            logger.warning(f"Search verification failed: {e}")
        
        logger.info(f"✅ Successfully indexed document {file_path} (file_id: {file_id})")
        
        return True
        
    except Exception as e:
        logger.error(f"Error indexing document: {e}", exc_info=True)
        raise DatabaseException(f"Failed to index document: {str(e)}")


def delete_document_from_vectorstore(file_id: int) -> bool:
    """
    Delete document from vector store
    
    Args:
        file_id: Document ID
        
    Returns:
        True if successful
    """
    try:
        vectorstore = get_vectorstore()
        
        # Get document chunks before deletion
        try:
            docs = vectorstore.get(where={"file_id": file_id})
            chunk_count = len(docs.get('ids', [])) if docs else 0
            logger.info(f"Found {chunk_count} chunks for file_id {file_id} before deletion")
        except Exception as e:
            logger.warning(f"Could not count chunks before deletion: {e}")
            chunk_count = 0
        
        # Delete chunks
        vectorstore._collection.delete(where={"file_id": file_id})
        
        # Verify deletion
        try:
            remaining = vectorstore.get(where={"file_id": file_id})
            remaining_count = len(remaining.get('ids', [])) if remaining else 0
            if remaining_count > 0:
                logger.warning(f"Warning: {remaining_count} chunks still remain after deletion for file_id {file_id}")
            else:
                logger.info(f"✅ Successfully deleted all {chunk_count} chunks for file_id {file_id}")
        except Exception as e:
            logger.warning(f"Could not verify deletion: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error deleting document with file_id {file_id}: {e}", exc_info=True)
        raise DatabaseException(f"Failed to delete document: {str(e)}")


def search_documents(query: str, k: int = None) -> List[Document]:
    """
    Search documents in vector store
    
    Args:
        query: Search query
        k: Number of results to return
        
    Returns:
        List of relevant documents
    """
    try:
        vectorstore = get_vectorstore()
        k = k or settings.chroma_search_k
        
        results = vectorstore.similarity_search(query, k=k)
        
        if results:
            # Log search statistics
            result_sizes = [len(r.page_content) for r in results]
            avg_size = sum(result_sizes) / len(result_sizes)
            total_tokens = int(sum(result_sizes) / 3.5)
            logger.debug(
                f"Found {len(results)} documents for query: '{query[:50]}...' "
                f"(avg {avg_size:.0f} chars/chunk, ~{total_tokens} total tokens)"
            )
        else:
            logger.debug(f"No results found for query: '{query[:50]}...'")
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise DatabaseException(f"Failed to search documents: {str(e)}")


def get_retriever(k: int = None):
    """
    Get retriever for RAG chain
    
    Args:
        k: Number of documents to retrieve
        
    Returns:
        Vector store retriever
    """
    vectorstore = get_vectorstore()
    k = k or settings.chroma_search_k
    return vectorstore.as_retriever(search_kwargs={"k": k})

