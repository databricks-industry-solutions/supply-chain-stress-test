from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Response, Request, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, RedirectResponse, FileResponse
from typing import Dict, List, Optional
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointStateReady
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime, timedelta
import json
import httpx
import time  
import logging
import asyncio
import mlflow
import mlflow.entities

from frontend_application.utils.chat_database import ChatDatabase
from collections import defaultdict
from contextlib import asynccontextmanager
from frontend_application.utils.models import MessageRequest, MessageResponse, ChatHistoryItem, ChatHistoryResponse, CreateChatRequest, RegenerateRequest, FeedbackRequest, FeedbackResponse
from frontend_application.utils.config import SERVING_ENDPOINT_NAME, DATABRICKS_HOST, MLFLOW_EXPERIMENT_ID
from frontend_application.utils import *
from frontend_application.utils.logging_handler import with_logging
from frontend_application.utils.app_state import app_state
from frontend_application.utils.dependencies import (
    get_chat_db,
    get_chat_history_cache,
    get_message_handler,
    get_streaming_handler,
    get_request_handler,
    get_streaming_semaphore,
    get_request_queue,
    get_streaming_support_cache
)
from frontend_application.utils.data_classes import StreamingContext, RequestContext, HandlerContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This will output to console
    ]
)

logger = logging.getLogger(__name__)
load_dotenv(override=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await app_state.startup(app)
    yield
    await app_state.shutdown(app)

app = FastAPI(lifespan=lifespan)

class CachedStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

class SPAStaticFiles(StaticFiles):
    """Custom StaticFiles that serves index.html for SPA routes"""
    async def get_response(self, path: str, scope):
        
        # Static files should NOT come here - they should go to /static mount
        if path.startswith("static/"):
            # Try to serve it anyway from the static directory
            try:
                static_path = path[7:]  # Remove 'static/' prefix
                response = await super().get_response(f"static/{static_path}", scope)
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
                return response
            except Exception as static_error:
                raise static_error
        
        # For root path, serve index.html
        if path == "" or path == "/" or path == ".":
            path = "index.html"
        
        try:
            response = await super().get_response(path, scope)
            return response
        except Exception as e:
            # If file not found and it's not an API route, serve index.html for SPA routing
            if "not found" in str(e).lower() and not path.startswith("chat-api"):
                try:
                    response = await super().get_response("index.html", scope)
                    return response
                except Exception as fallback_error:
                    raise e
            raise e

# Create API app first
api_app = FastAPI()

# Check if frontend build directory exists
frontend_dir = "frontend_application/frontend/build-chat-app"
static_dir = os.path.join(frontend_dir, "static")

if not os.path.exists(frontend_dir):
    logger.warning(f"Frontend build directory not found at {frontend_dir}")
elif not os.path.exists(static_dir):
    logger.warning(f"Static directory not found at {static_dir}")

# Mount in order of specificity (most specific first)
# 1. API routes
app.mount("/chat-api", api_app)

# 2. Static assets (must be before root mount)
if os.path.exists(static_dir):
    static_files = StaticFiles(directory=static_dir)
    app.mount("/static", static_files)
else:
    logger.error(f"Static directory not found: {static_dir}")

# 3. SPA for the main UI (catch-all, must be last)
ui_app = SPAStaticFiles(directory=frontend_dir, html=True)
app.mount("/", ui_app)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get auth headers
async def get_auth_headers(
    token: str = Depends(get_token)
) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="No access token provided in header or environment variable")
    return {"Authorization": f"Bearer {token}"}
    

# Routes
@api_app.get("/")
async def root():
    return {"message": "Procurement Bot API is running"}

# API Routes
@api_app.get("/config")
async def get_config():
    """Get frontend configuration values"""
    return {
        "databricks_host": DATABRICKS_HOST,
        "mlflow_experiment_id": MLFLOW_EXPERIMENT_ID,
        "serving_endpoint_name": SERVING_ENDPOINT_NAME
    }

# Modify the chat endpoint to handle sessions
@api_app.post("/chat")
async def chat(
    message: MessageRequest,
    user_info: dict = Depends(get_user_info),
    headers: dict = Depends(get_auth_headers),
    chat_db: ChatDatabase = Depends(get_chat_db),
    chat_history_cache: ChatHistoryCache = Depends(get_chat_history_cache),
    message_handler: MessageHandler = Depends(get_message_handler),
    streaming_handler: StreamingHandler = Depends(get_streaming_handler),
    request_handler: RequestHandler = Depends(get_request_handler),
    streaming_semaphore: asyncio.Semaphore = Depends(get_streaming_semaphore),
    request_queue: asyncio.Queue = Depends(get_request_queue),
    streaming_support_cache: dict = Depends(get_streaming_support_cache)
):
    try:
        user_id = user_info["user_id"]
        is_first_message = chat_db.is_first_message(message.session_id, user_id)
        user_message = message_handler.create_message(
            message_id=str(uuid.uuid4()),
            content=message.content,
            role="user",
            session_id=message.session_id,
            user_id=user_id,
            user_info=user_info,
            is_first_message=is_first_message
        )
        # Load chat history with caching
        chat_history = await load_chat_history(message.session_id, user_id, is_first_message, chat_history_cache, chat_db)
        
        async def generate():
            streaming_timeout = httpx.Timeout(
                connect=8.0,
                read=300.0,  # 5 minutes for streaming read operations
                write=8.0,
                pool=8.0
            )
            # Get the serving endpoint name from the request
            serving_endpoint_name = SERVING_ENDPOINT_NAME
            endpoint_url = f"https://{DATABRICKS_HOST}/serving-endpoints/{serving_endpoint_name}/invocations"
            
            supports_streaming, supports_trace = await check_endpoint_capabilities(
                serving_endpoint_name, streaming_support_cache
            )
            logger.info(
                f"ednpoint {serving_endpoint_name} supports_streaming: {(supports_streaming, supports_trace)}"
            )
            request_data = {
                "messages": [
                    *([{"role": msg["role"], "content": msg["content"]} for msg in chat_history[:-1]] 
                        if message.include_history else []),
                    {"role": "user", "content": message.content}
                ]
            }
            request_data["databricks_options"] = {"return_trace": bool(supports_trace)}
            # Use session_id as thread_id for agent/assistant endpoints
            request_data["custom_inputs"] = {"thread_id": message.session_id}

            if not supports_streaming:
                async for response_chunk in streaming_handler.handle_non_streaming_response(
                    request_handler, endpoint_url, headers, request_data, message.session_id, user_id, user_info, message_handler
                ):
                    yield response_chunk
            else:
                async with streaming_semaphore:
                    async with httpx.AsyncClient(timeout=streaming_timeout) as streaming_client:
                        try:
                            request_data["stream"] = True
                            assistant_message_id = str(uuid.uuid4())
                            first_token_time = None
                            accumulated_content = ""
                            ttft = None
                            start_time = time.time()

                            async with streaming_client.stream('POST', 
                                endpoint_url,
                                headers=headers,
                                json=request_data,
                                timeout=streaming_timeout
                            ) as response:
                                if response.status_code == 200:
                                    
                                    async for response_chunk in streaming_handler.handle_streaming_response(
                                    response, request_data, headers, message.session_id, assistant_message_id,
                                        user_id, user_info, None, start_time, first_token_time,
                                        accumulated_content, None, ttft, request_handler, message_handler, 
                                        streaming_support_cache, supports_trace, False
                                    ):
                                        # print( "Response chunk: ", response_chunk) 
                                        yield response_chunk

                                else:
                                    raise Exception("Streaming not supported")
                        except (httpx.ReadTimeout, httpx.HTTPError, Exception) as e:
                            logger.error(f"Streaming failed with error: {str(e)}, falling back to non-streaming")
                            if serving_endpoint_name in streaming_support_cache['endpoints']:
                                streaming_support_cache['endpoints'][serving_endpoint_name].update({
                                    'supports_streaming': False,
                                    'last_checked': datetime.now()
                                })
                            
                            request_data["stream"] = False
                            # Add a random query parameter to avoid any caching
                            url = f"{endpoint_url}?nocache={uuid.uuid4()}"
                            logger.info(f"Making fallback request with fresh connection to {url}")
                            try:
                                async for response_chunk in streaming_handler.handle_non_streaming_response(
                                    request_handler, url, headers, request_data, message.session_id, user_id, user_info, message_handler
                                ):
                                    yield response_chunk
                            except Exception as fallback_error:
                                logger.error(f"Non-streaming fallback also failed: {str(fallback_error)}")
                                # Create error message
                                error_message = message_handler.create_error_message(
                                    session_id=message.session_id,
                                    user_id=user_id,
                                    error_content="The request is taking longer than expected. Please try again with a simpler query."
                                )
                                yield f"data: {error_message.model_dump_json()}\n\n"
                                yield "event: done\ndata: {}\n\n"
                        

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )

    except httpx.HTTPStatusError as http_err:
        friendly_msg = None
        if http_err.response is not None and http_err.response.status_code == 429:
            friendly_msg = "The service is currently experiencing high demand. Please wait a moment and try again."
        error_message = message_handler.create_error_message(
            session_id=message.session_id,
            user_id=user_id,
            error_content=friendly_msg or ("An error occurred while processing your request. " + str(http_err))
        )

        async def error_generate():
            yield f"data: {error_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(
            error_generate(),
            media_type="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )
    except Exception as e:
        error_message = message_handler.create_error_message(
            session_id=message.session_id,
            user_id=user_id,
            error_content="An error occurred while processing your request. " + str(e)
        )

        async def error_generate():
            yield f"data: {error_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(
            error_generate(),
            media_type="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )

@api_app.get("/chats", response_model=ChatHistoryResponse)
async def get_chat_history(user_info: dict = Depends(get_user_info),chat_db: ChatDatabase = Depends(get_chat_db)):
    user_id = user_info["user_id"]
    logger.info(f"Getting chat history for user_id: {user_id}")
    chat_history = chat_db.get_chat_history(user_id)
    return chat_history

# Add logout endpoint
@api_app.get("/logout")
async def logout():
    return RedirectResponse(url=f"https://{os.getenv('DATABRICKS_HOST')}/login.html", status_code=303)

@api_app.get("/user-info")
async def login(
    user_info: dict = Depends(get_user_info),
):
    """Login endpoint for PAT authentication"""
    try:
        return user_info
    except httpx.HTTPStatusError as http_err:
        logger.error("Login failed with HTTP error: %s", str(http_err))
        resp = getattr(http_err, "response", None)
        if resp is not None:
            logger.error("Response status: %s", getattr(resp, "status_code", None))
            logger.error("Response body: %s", getattr(resp, "text", None))
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(http_err)}")
    except Exception as e:
        logger.error("Login failed with error: %s", str(e))
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

@api_app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user_info: dict = Depends(get_user_info),
    chat_db: ChatDatabase = Depends(get_chat_db)
):
    """Delete a specific session and all its chat history"""
    try:
        user_id = user_info.get('user_id')
        result = chat_db.delete_session_api(session_id, user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

@api_app.delete("/sessions")
async def delete_user_sessions(
    user_info: dict = Depends(get_user_info),
    chat_db: ChatDatabase = Depends(get_chat_db)
):
    """Delete all sessions for the current user"""
    try:
        user_id = user_info.get('user_id')
        result = chat_db.delete_user_sessions_api(user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting user sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete user sessions: {str(e)}")

@api_app.post("/rate-message")
async def rate_message(
    request: dict,
    user_info: dict = Depends(get_user_info),
    chat_db: ChatDatabase = Depends(get_chat_db)
):
    """Rate a message with thumbs up or down"""
    try:
        message_id = request.get('message_id')
        session_id = request.get('session_id')
        rating = request.get('rating')
        user_id = user_info.get('user_id')
        
        if not all([message_id, session_id, rating, user_id]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        if rating not in ['up', 'down']:
            raise HTTPException(status_code=400, detail="Rating must be 'up' or 'down'")
        
        success = chat_db.update_message_rating(message_id, user_id, rating)
        if success:
            return {"message": "Message rated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to rate message")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rating message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to rate message: {str(e)}")

@api_app.delete("/rate-message")
async def delete_rating(
    request: dict,
    user_info: dict = Depends(get_user_info),
    chat_db: ChatDatabase = Depends(get_chat_db)
):
    """Remove a message rating"""
    try:
        message_id = request.get('message_id')
        session_id = request.get('session_id')
        user_id = user_info.get('user_id')
        
        if not all([message_id, session_id, user_id]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        success = chat_db.update_message_rating(message_id, user_id, None)
        if success:
            return {"message": "Rating removed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to remove rating")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing rating: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to remove rating: {str(e)}")

@api_app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    user_info: dict = Depends(get_user_info),
    chat_db: ChatDatabase = Depends(get_chat_db)
):
    """
    Submit user feedback linked to trace
    """
    try:
        logger.info(f"Received feedback request: message_id={feedback.message_id}, rating={feedback.rating}")
        
        # Try to log to MLflow if we have a valid trace_id, but don't fail if it doesn't work
        if feedback.trace_id:
            try:
                # Log feedback using mlflow.log_feedback (MLflow 3 API)
                mlflow.log_feedback(
                    trace_id=feedback.trace_id,
                    name="user_feedback",
                    value=True if feedback.rating == "up" else False,
                    rationale=feedback.comment if feedback.comment else None,
                    source=mlflow.entities.AssessmentSource(
                        source_type="HUMAN",
                        source_id=user_info.get('displayName') or user_info.get('email') or "user",
                    ),
                )
                logger.info(f"Feedback logged to MLflow for trace_id: {feedback.trace_id}")
            except Exception as mlflow_error:
                logger.warning(f"Failed to log feedback to MLflow (this is expected if no trace exists): {str(mlflow_error)}")
                # Continue with database update even if MLflow fails
        else:
            logger.info("No trace_id provided, skipping MLflow logging")

        # Always update the message rating in our database
        user_id = user_info.get('user_id')
        if user_id:
            success = chat_db.update_message_rating(feedback.message_id, user_id, feedback.rating)
            if success:
                logger.info(f"Feedback rating updated in database for message: {feedback.message_id}")
            else:
                logger.warning(f"Failed to update rating in database for message: {feedback.message_id}")
        else:
            logger.warning("No user_id found in user_info")

        return FeedbackResponse(success=True, message="Feedback submitted successfully")

    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        return FeedbackResponse(
            success=False, message=f"Error submitting feedback: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
