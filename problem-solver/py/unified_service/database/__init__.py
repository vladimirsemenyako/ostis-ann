"""
Database modules for the unified service
"""
from .db_utils import (
    get_db_connection,
    init_database,
    insert_chat_log,
    get_chat_history,
    insert_document_record,
    delete_document_record,
    get_all_documents,
    get_document_by_filename,
    create_session,
    get_session,
    update_session,
    list_sessions,
    get_structured_chat_history,
    delete_old_sessions,
    delete_session
)
from .vector_store import (
    get_vectorstore,
    index_document,
    delete_document_from_vectorstore,
    search_documents,
    get_retriever
)

__all__ = [
    "get_db_connection",
    "init_database",
    "insert_chat_log",
    "get_chat_history",
    "insert_document_record",
    "get_document_by_filename",
    "delete_document_record",
    "get_all_documents",
    "create_session",
    "get_session",
    "update_session",
    "list_sessions",
    "get_structured_chat_history",
    "delete_old_sessions",
    "delete_session",
    "get_vectorstore",
    "index_document",
    "delete_document_from_vectorstore",
    "search_documents",
    "get_retriever"
]

