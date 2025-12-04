"""
Chat router - main unified endpoint
Orchestrates the flow: classification -> RAG or build_model workflow
"""
import json
import uuid
import logging
from fastapi import APIRouter, HTTPException
from models import (
    ChatRequest,
    ChatResponse,
    TaskCategory,
    AgentStatus,
    FormField,
    ChatMode
)
from services import (
    TaskClassifier,
    RAGService,
    DataCollector,
    DesignerService,
    CodeSearchService
)
from database import (
    insert_chat_log,
    get_chat_history,
    get_structured_chat_history,
    create_session,
    get_session,
    update_session
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])

# Initialize services (singleton pattern)
classifier = TaskClassifier()
rag_service = RAGService()
data_collector = DataCollector()
designer_service = DesignerService()
code_search_service = CodeSearchService()


def _derive_title(text: str, default: str = "Новый диалог") -> str:
    """Generate a short title for the dialog based on user query"""
    if not text:
        return default
    stripped = text.strip()
    return (stripped[:60] + "…") if len(stripped) > 60 else stripped


def _to_form_models(raw_fields):
    if not raw_fields:
        return None
    return [FormField(**field) for field in raw_fields]


def _summarize_form_data(form_data: dict) -> str:
    if not form_data:
        return ""
    lines = [f"{key}: {value}" for key, value in form_data.items() if value]
    return "Обновлены параметры:\n" + "\n".join(lines)


def _build_agent_meta(status: AgentStatus, **extra):
    meta = {"status": status.value}
    for key, value in extra.items():
        if value is not None:
            meta[key] = value
    return meta


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main unified chat endpoint
    
    Flow:
    1. Classify query (informational vs build_model)
    2. If informational: Use RAG to answer
    3. If build_model: Collect data -> Design model -> Search code
    """
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"Chat request - Session: {session_id}, Query: {request.query[:100]}...")
    
    try:
        # Check if this is a continuation of build_model session
        session_data = get_session(session_id)
        
        # Only continue build_model workflow if we have active session AND user is responding
        if session_data and session_data.get("category") == TaskCategory.BUILD_MODEL.value:
            # Check if workflow is already completed by looking at recent chat history with metadata
            workflow_completed = False
            try:
                structured_history = get_structured_chat_history(session_id)
                if structured_history:
                    # Check last assistant message for completion indicators
                    for msg in reversed(structured_history):
                        if msg.get("role") == "assistant":
                            meta = msg.get("meta", {})
                            # Check if workflow was completed (has recommended_model in meta)
                            if meta and meta.get("recommended_model"):
                                workflow_completed = True
                                logger.info(
                                    f"Build_model workflow already completed for session {session_id} "
                                    f"(found recommendation: {meta.get('recommended_model')}), ignoring duplicate request"
                                )
                                break
                            # Also check response content for completion markers
                            response = msg.get("content", "")
                            if "[BUILD_MODEL_COMPLETE]" in msg.get("content", "") or "Рекомендуемая модель:" in response:
                                workflow_completed = True
                                logger.info(f"Build_model workflow already completed (found completion marker), ignoring duplicate request")
                                break
                            break
            except Exception as e:
                logger.warning(f"Could not check workflow completion status: {e}")
            
            if not workflow_completed:
                # Check if user is providing a response (not starting a new conversation)
                if request.user_response or request.form_data:
                    # Continue build_model workflow
                    return await _handle_build_model_continuation(
                        session_id,
                        request,
                        session_data
                    )
                # If no user_response, treat as new query (user might want to start over)
                logger.info(f"Build_model session exists but no user_response provided, treating as new query")
            else:
                # Workflow already completed - treat as informational query to allow continued conversation
                logger.info(f"Build_model workflow already completed, treating request as informational query")
                # Use RAG to answer the query naturally
                return await _handle_informational(session_id, request)
        
        # Determine category based on chat_mode
        if request.chat_mode == ChatMode.CONSULTANT:
            category = TaskCategory.INFORMATIONAL
            logger.info(f"Chat mode: CONSULTANT - forcing informational category")
        elif request.chat_mode == ChatMode.DESIGNER:
            category = TaskCategory.BUILD_MODEL
            logger.info(f"Chat mode: DESIGNER - forcing build_model category")
        else:
            # AUTO mode - classify query
            category = await classifier.classify(request.query)
            logger.info(f"Chat mode: AUTO - classified as: {category.value}")
        
        # Get chat_mode from session if exists, otherwise use request
        session_data = get_session(session_id)
        chat_mode_value = None
        if request.chat_mode:
            chat_mode_value = request.chat_mode.value
        elif session_data and session_data.get("chat_mode"):
            chat_mode_value = session_data.get("chat_mode")
        else:
            chat_mode_value = "auto"
        
        # Create session
        create_session(
            session_id=session_id,
            category=category.value,
            original_query=request.query,
            title=_derive_title(request.query),
            chat_mode=chat_mode_value
        )
        
        # Route to appropriate handler
        if category == TaskCategory.INFORMATIONAL:
            return await _handle_informational(session_id, request)
        
        elif category == TaskCategory.BUILD_MODEL:
            return await _handle_build_model_start(session_id, request)
        
        else:  # UNCLEAR
            return await _handle_unclear(session_id, request)
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        
        # Log error
        try:
            insert_chat_log(
                session_id=session_id,
                user_query=request.query,
                agent_response=f"Error: {str(e)}",
                category="error"
            )
        except:
            pass
        
        return ChatResponse(
            status=AgentStatus.ERROR,
            message=f"Произошла ошибка при обработке запроса: {str(e)}",
            session_id=session_id
        )


async def _handle_informational(session_id: str, request: ChatRequest) -> ChatResponse:
    """Handle informational queries using RAG"""
    logger.info(f"Handling informational query for session {session_id}")
    
    try:
        # Get chat history
        chat_history = get_chat_history(session_id)
        
        # Get answer from RAG
        answer = await rag_service.answer_query(
            query=request.query,
            chat_history=chat_history
        )
        
        # Log chat
        insert_chat_log(
            session_id=session_id,
            user_query=request.query,
            agent_response=answer,
            category=TaskCategory.INFORMATIONAL.value,
            agent_meta=_build_agent_meta(
                AgentStatus.COMPLETE,
                category=TaskCategory.INFORMATIONAL.value
            )
        )
        
        logger.info(f"Informational query answered (length: {len(answer)} chars)")
        
        # For informational queries, status is always COMPLETE (answer provided)
        # But we don't mark dialog as "finished" - user can continue conversation
        return ChatResponse(
            status=AgentStatus.COMPLETE,
            message=answer,
            session_id=session_id,
            category=TaskCategory.INFORMATIONAL
        )
    
    except Exception as e:
        logger.error(f"Error handling informational query: {e}")
        raise


async def _handle_build_model_start(session_id: str, request: ChatRequest) -> ChatResponse:
    """Start build_model workflow"""
    logger.info(f"Starting build_model workflow for session {session_id}")
    
    try:
        submitted_form = request.form_data or {}
        updated_data, form_field_defs, is_complete, guidance = await data_collector.collect_data(
            collected_data=submitted_form
        )
        public_data = data_collector.sanitize_data(updated_data)
        form_fields = _to_form_models(form_field_defs)
        
        # Update session
        update_session(
            session_id=session_id,
            category=TaskCategory.BUILD_MODEL.value,
            collected_data=json.dumps(public_data)
        )
        
        # Log chat
        agent_meta = _build_agent_meta(
            AgentStatus.QUESTION if not is_complete else AgentStatus.COMPLETE,
            category=TaskCategory.BUILD_MODEL.value,
            collected_data=public_data,
            form_fields=form_field_defs
        )
        insert_chat_log(
            session_id=session_id,
            user_query=request.query,
            agent_response=guidance,
            category=TaskCategory.BUILD_MODEL.value,
            agent_meta=agent_meta
        )
        
        if is_complete:
            # Data collection complete - proceed to design and search
            return await _complete_build_model_workflow(
                session_id=session_id,
                original_query=request.query,
                collected_data=public_data
            )
        else:
            # Need more data
            logger.info(f"Data collection in progress, awaiting structured input.")
            return ChatResponse(
                status=AgentStatus.QUESTION,
                message=guidance,
                session_id=session_id,
                category=TaskCategory.BUILD_MODEL,
                collected_data=public_data,
                form_fields=form_fields
            )
    
    except Exception as e:
        logger.error(f"Error starting build_model workflow: {e}")
        raise


async def _handle_build_model_continuation(
    session_id: str,
    request: ChatRequest,
    session_data: dict
) -> ChatResponse:
    """Continue build_model workflow with user response"""
    logger.info(f"Continuing build_model workflow for session {session_id}")
    
    try:
        # Get collected data
        collected_data_str = session_data.get("collected_data", "{}")
        collected_data = json.loads(collected_data_str) if collected_data_str else {}
        
        form_updates = {k: v for k, v in (request.form_data or {}).items() if v}
        if form_updates:
            collected_data.update(form_updates)
        
        text_response = request.user_response or (request.query if not form_updates else None)
        
        updated_data, form_field_defs, is_complete, guidance = await data_collector.collect_data(
            collected_data=collected_data,
            text_response=text_response
        )
        public_data = data_collector.sanitize_data(updated_data)
        form_fields = _to_form_models(form_field_defs)
        
        # Update session
        update_session(
            session_id=session_id,
            collected_data=json.dumps(public_data)
        )
        
        user_message = text_response or request.query
        if form_updates:
            user_message = _summarize_form_data(form_updates)
        
        # Log chat
        agent_meta = _build_agent_meta(
            AgentStatus.QUESTION if not is_complete else AgentStatus.COMPLETE,
            category=TaskCategory.BUILD_MODEL.value,
            collected_data=public_data,
            form_fields=form_field_defs
        )
        insert_chat_log(
            session_id=session_id,
            user_query=user_message,
            agent_response=guidance,
            category=TaskCategory.BUILD_MODEL.value,
            agent_meta=agent_meta
        )
        
        if is_complete:
            # Data collection complete - proceed to design and search
            original_query = session_data.get("original_query", request.query)
            return await _complete_build_model_workflow(
                session_id=session_id,
                original_query=original_query,
                collected_data=public_data
            )
        else:
            # Need more data
            logger.info("Data collection continuing, waiting for structured input.")
            return ChatResponse(
                status=AgentStatus.QUESTION,
                message=guidance,
                session_id=session_id,
                category=TaskCategory.BUILD_MODEL,
                collected_data=public_data,
                form_fields=form_fields
            )
    
    except Exception as e:
        logger.error(f"Error continuing build_model workflow: {e}")
        raise


async def _complete_build_model_workflow(
    session_id: str,
    original_query: str,
    collected_data: dict
) -> ChatResponse:
    """Complete build_model workflow: design model and search code"""
    logger.info(f"Completing build_model workflow for session {session_id}")
    
    try:
        # Build task description from collected data
        task_description = f"{original_query}\nДанные: {collected_data.get('data', '')}\nПризнаки: {collected_data.get('features', '')}\nЦель: {collected_data.get('output', '')}\nМетрика: {collected_data.get('metric_goal', '')}"
        
        # Design model
        recommendation = await designer_service.analyze_task(task_description)
        
        logger.info(f"Model recommendation: {recommendation.recommended_model.value} (confidence: {recommendation.confidence:.2f})")
        
        # Search for code/model
        search_results = await code_search_service.search_for_model(
            recommendation=recommendation,
            task_description=task_description
        )
        
        # Build final message
        final_message = (
            f"✅ Данные собраны!\n\n"
            f"📊 Рекомендуемая модель: {recommendation.recommended_model.value}\n"
            f"🎯 Уверенность: {recommendation.confidence:.0%}\n"
            f"💡 Обоснование: {recommendation.reasoning}\n\n"
        )
        
        if recommendation.alternative_models:
            alt_models = ", ".join([m.value for m in recommendation.alternative_models])
            final_message += f"🔄 Альтернативы: {alt_models}\n\n"
        
        if search_results.get("best_link"):
            final_message += f"🔗 Лучшая реализация: {search_results['best_link']}\n"
        
        if search_results.get("other_links"):
            final_message += f"\n📚 Другие варианты:\n"
            for link in search_results['other_links'][:3]:
                final_message += f"  • {link}\n"
        
        # Log final result
        agent_meta = _build_agent_meta(
            AgentStatus.COMPLETE,
            category=TaskCategory.BUILD_MODEL.value,
            collected_data=collected_data,
            recommended_model=recommendation.recommended_model.value,
            confidence=recommendation.confidence,
            best_link=search_results.get("best_link"),
            other_links=search_results.get("other_links")
        )
        insert_chat_log(
            session_id=session_id,
            user_query="[BUILD_MODEL_COMPLETE]",
            agent_response=final_message,
            category=TaskCategory.BUILD_MODEL.value,
            agent_meta=agent_meta
        )
        
        logger.info(f"Build_model workflow completed successfully")
        
        return ChatResponse(
            status=AgentStatus.COMPLETE,
            message=final_message,
            session_id=session_id,
            category=TaskCategory.BUILD_MODEL,
            collected_data=collected_data,
            recommended_model=recommendation.recommended_model,
            confidence=recommendation.confidence,
            reasoning=recommendation.reasoning,
            alternative_models=recommendation.alternative_models,
            best_link=search_results.get("best_link"),
            other_links=search_results.get("other_links", [])
        )
    
    except Exception as e:
        logger.error(f"Error completing build_model workflow: {e}")
        raise


async def _handle_unclear(session_id: str, request: ChatRequest) -> ChatResponse:
    """Handle unclear queries - default to RAG"""
    logger.info(f"Handling unclear query for session {session_id}, defaulting to RAG")
    
    try:
        # Get chat history
        chat_history = get_chat_history(session_id)
        
        # Get answer from RAG
        answer = await rag_service.answer_query(
            query=request.query,
            chat_history=chat_history
        )
        
        # Log chat
        insert_chat_log(
            session_id=session_id,
            user_query=request.query,
            agent_response=answer,
            category=TaskCategory.UNCLEAR.value,
            agent_meta=_build_agent_meta(
                AgentStatus.COMPLETE,
                category=TaskCategory.UNCLEAR.value
            )
        )
        
        logger.info(f"Unclear query answered via RAG")
        
        return ChatResponse(
            status=AgentStatus.COMPLETE,
            message=answer,
            session_id=session_id,
            category=TaskCategory.UNCLEAR
        )
    
    except Exception as e:
        logger.error(f"Error handling unclear query: {e}")
        raise

