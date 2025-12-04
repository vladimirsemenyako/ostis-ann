"""
Documents management router
"""
import os
import logging
import shutil
from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List
from models import DocumentInfo, DocumentUploadResponse, DeleteDocumentRequest
from database import (
    insert_document_record,
    delete_document_record,
    get_all_documents,
    index_document,
    delete_document_from_vectorstore
)
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and index a document to the vector store
    
    Supported formats: PDF, DOCX, HTML
    """
    logger.info(f"Uploading document: {file.filename}")
    
    # Check file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.allowed_file_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.allowed_file_extensions)}"
        )
    
    # Save temporary file
    temp_file_path = os.path.join(settings.temp_upload_dir, f"temp_{file.filename}")
    
    try:
        # Write file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Insert document record
        file_id = insert_document_record(file.filename)
        
        # Index to vector store
        success = index_document(temp_file_path, file_id)
        
        if success:
            logger.info(f"Successfully uploaded and indexed document: {file.filename} (id: {file_id})")
            return DocumentUploadResponse(
                message=f"Document '{file.filename}' successfully uploaded and indexed",
                file_id=file_id,
                filename=file.filename
            )
        else:
            # Rollback: delete document record
            delete_document_record(file_id)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to index document: {file.filename}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading document: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.get("/list", response_model=List[DocumentInfo])
async def list_documents():
    """
    List all uploaded documents
    
    Returns list of documents with metadata
    """
    try:
        documents = get_all_documents()
        logger.debug(f"Retrieved {len(documents)} documents")
        return documents
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing documents: {str(e)}"
        )


@router.delete("/delete")
async def delete_document(request: DeleteDocumentRequest):
    """
    Delete a document from both database and vector store
    """
    file_id = request.file_id
    logger.info(f"Deleting document with id: {file_id}")
    
    try:
        # Delete from vector store
        vectorstore_success = delete_document_from_vectorstore(file_id)
        
        if vectorstore_success:
            # Delete from database
            db_success = delete_document_record(file_id)
            
            if db_success:
                logger.info(f"Successfully deleted document with id: {file_id}")
                return {
                    "success": True,
                    "message": f"Successfully deleted document with id {file_id}"
                }
            else:
                logger.warning(f"Deleted from vectorstore but failed to delete from database: {file_id}")
                return {
                    "success": False,
                    "message": f"Deleted from vectorstore but failed to delete from database"
                }
        else:
            logger.error(f"Failed to delete document from vectorstore: {file_id}")
            return {
                "success": False,
                "message": f"Failed to delete document from vectorstore"
            }
    
    except Exception as e:
        logger.error(f"Error deleting document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document: {str(e)}"
        )

