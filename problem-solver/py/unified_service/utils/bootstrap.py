"""
Bootstrap helpers (documents, datasets, etc.)
"""
import os
import logging
from typing import List

from config import settings
from database import (
    insert_document_record,
    delete_document_record,
    get_document_by_filename,
    index_document
)

logger = logging.getLogger(__name__)


async def bootstrap_documents():
    """Index static documents defined in settings.bootstrap_documents"""
    documents: List[str] = settings.bootstrap_documents or []
    if not documents:
        return
    
    for doc_path in documents:
        abs_path = os.path.abspath(doc_path)
        if not os.path.exists(abs_path):
            logger.warning("Bootstrap document not found: %s", abs_path)
            continue
        
        filename = os.path.basename(abs_path)
        if get_document_by_filename(filename):
            logger.info("Bootstrap document already indexed: %s", filename)
            continue
        
        logger.info("Indexing bootstrap document: %s", filename)
        try:
            file_id = insert_document_record(filename)
            index_document(abs_path, file_id)
            logger.info("Successfully indexed %s (id=%s)", filename, file_id)
        except Exception as exc:
            logger.error("Failed to index bootstrap document %s: %s", filename, exc, exc_info=True)
            try:
                delete_document_record(file_id)
            except Exception:
                logger.warning("Rollback for bootstrap document %s failed", filename)

