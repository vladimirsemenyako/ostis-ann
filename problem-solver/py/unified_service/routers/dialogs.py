"""
Dialog management endpoints
"""
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException

from models import (
    DialogInfo,
    DialogMessage,
    CreateDialogRequest,
    UpdateDialogRequest,
    TaskCategory,
    ChatMode
)
from database import (
    list_sessions,
    create_session,
    get_session,
    get_structured_chat_history,
    update_session,
    delete_session
)

router = APIRouter(prefix="/api/v1/dialogs", tags=["dialogs"])


def _parse_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        # SQLite default format "YYYY-MM-DD HH:MM:SS"
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def _build_dialog_info(row: dict) -> DialogInfo:
    return DialogInfo(
        session_id=row["session_id"],
        title=row.get("title") or row.get("original_query") or "Новый диалог",
        category=TaskCategory(row["category"]) if row.get("category") else None,
        chat_mode=row.get("chat_mode", "auto"),
        last_message=row.get("last_message"),
        created_at=_parse_timestamp(row["created_at"]),
        updated_at=_parse_timestamp(row["updated_at"])
    )


@router.get("", response_model=List[DialogInfo])
async def list_dialogs():
    """Return list of saved dialogs"""
    try:
        sessions = list_sessions()
        return [_build_dialog_info(entry) for entry in sessions]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=DialogInfo)
async def create_dialog(payload: CreateDialogRequest):
    """Create a new dialog session"""
    session_id = str(uuid.uuid4())
    try:
        # Handle chat_mode - can be ChatMode enum or string
        chat_mode_value = 'auto'
        if payload.chat_mode:
            if isinstance(payload.chat_mode, ChatMode):
                chat_mode_value = payload.chat_mode.value
            else:
                chat_mode_value = str(payload.chat_mode)
        
        create_session(
            session_id=session_id,
            title=payload.title or "Новый диалог",
            chat_mode=chat_mode_value
        )
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=500, detail="Failed to retrieve created session")
        return _build_dialog_info(session)
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/{session_id}", response_model=DialogInfo)
async def update_dialog(session_id: str, payload: UpdateDialogRequest):
    """Update dialog metadata"""
    try:
        update_session(
            session_id=session_id,
            title=payload.title,
            is_active=payload.is_active
        )
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Dialog not found")
        return _build_dialog_info(session)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{session_id}/messages", response_model=List[DialogMessage])
async def get_dialog_messages(session_id: str):
    """Load full dialog history"""
    try:
        history = get_structured_chat_history(session_id)
        messages: List[DialogMessage] = []
        for item in history:
            messages.append(
                DialogMessage(
                    id=item["id"],
                    role=item["role"],
                    content=item["content"],
                    timestamp=_parse_timestamp(item["timestamp"]),
                    category=TaskCategory(item["category"]) if item.get("category") else None,
                    meta=item.get("meta")
                )
            )
        return messages
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{session_id}")
async def delete_dialog(session_id: str):
    """Delete a dialog and all its messages"""
    try:
        success = delete_session(session_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete dialog")
        return {"success": True, "message": f"Dialog {session_id} deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

