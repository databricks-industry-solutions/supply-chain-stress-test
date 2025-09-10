import json
import time
from typing import AsyncGenerator, Optional, Dict
from fastapi.responses import StreamingResponse
import httpx
from utils.models import MessageResponse
from utils import *
from utils.data_utils import create_response_data
import logging
import uuid
from utils.request_handler import RequestHandler
from datetime import datetime
from utils.config import SERVING_ENDPOINT_NAME
logger = logging.getLogger(__name__)
class StreamingHandler:

    @staticmethod
    async def handle_streaming_response(
        response: httpx.Response,
        request_data: Dict,
        headers: Dict,
        session_id: str,
        message_id: str,
        user_id: str,
        user_info: Dict,
        original_timestamp: str,
        start_time: float,
        first_token_time: Optional[float],
        accumulated_content: str,
        sources: Optional[Dict],
        ttft: Optional[float],
        request_handler: RequestHandler,
        message_handler,
        streaming_support_cache,
        supports_trace,
        update_flag: bool
    ) -> AsyncGenerator[str, None]:
        """Handle streaming response from the model with integrated tool calls and responses."""
        # Initialize variables
        trace_id = None
        accumulated_tool_calls = []
        accumulated_tool_responses = []
        
        try:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    try:
                        json_str = line[6:]
                        data = json.loads(json_str)
                        # Record time of first token
                        if first_token_time is None:
                            first_token_time = time.time()
                            ttft = first_token_time - start_time
                            
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            
                            # Capture tool calls if present
                            if 'tool_calls' in delta:
                                accumulated_tool_calls.extend(delta['tool_calls'])
                                print(f"Tool calls captured (choices): {len(delta['tool_calls'])} calls")
                            
                            # Always add content to accumulated_content
                            if content:
                                accumulated_content += content
                                print(f"Added choices content: {len(content)} chars, total: {len(accumulated_content)}")
                            
                            # Extract sources and trace_id using the request_handler method
                            if 'databricks_output' in data or 'trace' in data or 'trace_id' in data:
                                sources, trace_id = await request_handler.extract_sources_from_trace(data)
                            
                            # Stream all content immediately (always stream, even if no new content to show updates)
                            response_data = create_response_data(
                                message_id,
                                accumulated_content,  # Stream full accumulated content
                                sources,
                                ttft if first_token_time is not None else None,
                                time.time() - start_time,
                                original_timestamp,
                                trace_id,
                                accumulated_tool_calls if accumulated_tool_calls else None
                            )
                            yield f"data: {json.dumps(response_data)}\n\n"
                        elif "delta" in data:
                            # Check for trace information in delta responses as well
                            if 'databricks_output' in data or 'trace' in data or 'trace_id' in data:
                                new_sources, new_trace_id = await request_handler.extract_sources_from_trace(data)
                                print(f"New sources: {new_sources}, New trace_id: {new_trace_id}")
                                if new_sources:
                                    sources = new_sources
                                if new_trace_id:
                                    trace_id = new_trace_id
                            
                            delta = data["delta"]
                            if delta["role"] == "assistant" and "tool_calls" in delta:
                                # Capture tool calls
                                accumulated_tool_calls.extend(delta['tool_calls'])
                                print(f"Tool calls captured (delta): {len(delta['tool_calls'])} calls")
                                
                                # Add tool call content to accumulated_content for single response
                                for tool_call in delta['tool_calls']:
                                    tool_name = tool_call.get('function', {}).get('name', 'unknown_tool')
                                    tool_args = tool_call.get('function', {}).get('arguments', '{}')
                                    
                                    # Format tool call for inclusion in content with clear delimiters
                                    try:
                                        args_dict = json.loads(tool_args) if tool_args != '{}' else {}
                                        if args_dict:
                                            # Pretty print arguments as JSON
                                            formatted_args = json.dumps(args_dict, indent=2, ensure_ascii=False)
                                            tool_content = f"\n\n<!-- TOOL_START -->\n🔧 Using tool: {tool_name}\n\nTool: {tool_name}\nArguments:\n{formatted_args}\n<!-- TOOL_END -->\n"
                                        else:
                                            tool_content = f"\n\n<!-- TOOL_START -->\n🔧 Using tool: {tool_name}\n\nTool: {tool_name}\nArguments: (none)\n<!-- TOOL_END -->\n"
                                    except Exception as e:
                                        print(f"Error parsing tool args: {e}")
                                        tool_content = f"\n\n<!-- TOOL_START -->\n🔧 Using tool: {tool_name}\n\nTool: {tool_name}\nArguments: {tool_args}\n<!-- TOOL_END -->\n"
                                    
                                    accumulated_content += tool_content
                                    print(f"Added tool call to content: {tool_name}")
                                
                                # Add any additional content from the delta
                                if delta.get("content"):
                                    accumulated_content += delta["content"]
                                
                                # Stream updated content
                                response_data = create_response_data(
                                    message_id,
                                    accumulated_content,
                                    sources,
                                    ttft if first_token_time is not None else None,
                                    time.time() - start_time,
                                    original_timestamp,
                                    trace_id,  # Pass the extracted trace_id
                                    accumulated_tool_calls if accumulated_tool_calls else None
                                )
                                yield f"data: {json.dumps(response_data)}\n\n"
                                
                            elif delta["role"] == "tool":
                                # Capture tool response and add to content
                                if delta.get("content"):
                                    accumulated_tool_responses.append(delta["content"])
                                    print(f"Tool response captured: {len(delta['content'])} characters")
                                    
                                    # Try to parse and pretty-print JSON content
                                    try:
                                        # First try to parse as JSON
                                        parsed_content = json.loads(delta['content'])
                                        formatted_content = json.dumps(parsed_content, indent=2, ensure_ascii=False)
                                        tool_response_content = f"\n\n<!-- TOOL_RESPONSE_START -->\n🔧 Tool response:\n\n{formatted_content}\n<!-- TOOL_RESPONSE_END -->\n"
                                    except (json.JSONDecodeError, TypeError):
                                        try:
                                            # Try to evaluate as Python literal (for dict/list syntax)
                                            import ast
                                            parsed_content = ast.literal_eval(delta['content'])
                                            formatted_content = json.dumps(parsed_content, indent=2, ensure_ascii=False)
                                            tool_response_content = f"\n\n<!-- TOOL_RESPONSE_START -->\n🔧 Tool response:\n\n{formatted_content}\n<!-- TOOL_RESPONSE_END -->\n"
                                        except (ValueError, SyntaxError):
                                            # If neither works, try to parse as key=value pairs and convert to JSON
                                            try:
                                                # Split by comma and parse key=value pairs
                                                pairs = delta['content'].split(',')
                                                result = {}
                                                current_key = None
                                                current_value = ""
                                                in_list = False
                                                bracket_count = 0
                                                
                                                for pair in pairs:
                                                    pair = pair.strip()
                                                    if '=' in pair and not in_list:
                                                        if current_key:
                                                            # Process previous key-value
                                                            try:
                                                                result[current_key] = ast.literal_eval(current_value.strip())
                                                            except:
                                                                result[current_key] = current_value.strip()
                                                        
                                                        # Start new key-value
                                                        key, value = pair.split('=', 1)
                                                        current_key = key.strip()
                                                        current_value = value
                                                        
                                                        # Check if we're starting a list
                                                        if '[' in current_value:
                                                            in_list = True
                                                            bracket_count = current_value.count('[') - current_value.count(']')
                                                    else:
                                                        # Continue building current value
                                                        current_value += ',' + pair
                                                        if in_list:
                                                            bracket_count += pair.count('[') - pair.count(']')
                                                            if bracket_count <= 0:
                                                                in_list = False
                                                
                                                # Process final key-value
                                                if current_key:
                                                    try:
                                                        result[current_key] = ast.literal_eval(current_value.strip())
                                                    except:
                                                        result[current_key] = current_value.strip()
                                                
                                                formatted_content = json.dumps(result, indent=2, ensure_ascii=False)
                                                tool_response_content = f"\n\n<!-- TOOL_RESPONSE_START -->\n🔧 Tool response:\n\n{formatted_content}\n<!-- TOOL_RESPONSE_END -->\n"
                                            except Exception:
                                                # Final fallback: use original content
                                                tool_response_content = f"\n\n<!-- TOOL_RESPONSE_START -->\n🔧 Tool response:\n\n{delta['content']}\n<!-- TOOL_RESPONSE_END -->\n"
                                    
                                    accumulated_content += tool_response_content
                                    print(f"Added tool response to content")
                                    
                                    # Stream updated content with tool response
                                    response_data = create_response_data(
                                        message_id,
                                        accumulated_content,
                                        sources,
                                        ttft if first_token_time is not None else None,
                                        time.time() - start_time,
                                        original_timestamp,
                                        trace_id,  # Pass the extracted trace_id
                                        accumulated_tool_calls if accumulated_tool_calls else None,
                                        accumulated_tool_responses if accumulated_tool_responses else None
                                    )
                                    yield f"data: {json.dumps(response_data)}\n\n"
                                    
                            elif delta["role"] == "assistant" and delta.get("content"):
                                content = delta['content']
                                
                                # Always append to accumulated_content for single response
                                accumulated_content += content
                                print(f"Added regular content: {len(content)} chars, total: {len(accumulated_content)}")
                                
                                # Stream updated content
                                response_data = create_response_data(
                                    message_id,
                                    accumulated_content,
                                    sources,
                                    ttft if first_token_time is not None else None,
                                    time.time() - start_time,
                                    original_timestamp,
                                    trace_id,  # Pass the extracted trace_id
                                    accumulated_tool_calls if accumulated_tool_calls else None
                                )
                                yield f"data: {json.dumps(response_data)}\n\n"    
                    except json.JSONDecodeError:
                        continue
            if update_flag:
                updated_message = message_handler.update_message(
                                    session_id=session_id,
                                    message_id=message_id,
                                    user_id=user_id,
                                    content=accumulated_content,
                                    sources=sources,
                                    timestamp=original_timestamp,
                                    metrics={
                                        "timeToFirstToken": ttft,
                                        "totalTime": time.time() - start_time
                                    },
                                    tool_calls=accumulated_tool_calls if accumulated_tool_calls else None
                                )
            else:
                assistant_message = message_handler.create_message(
                                    message_id=message_id,
                                    content=accumulated_content,
                                    role="assistant",
                                    session_id=session_id,
                                    user_id=user_id,
                                    user_info=user_info,
                                    sources=sources,
                                    metrics={'timeToFirstToken': ttft, 'totalTime': time.time() - start_time},
                                    trace_id=trace_id,
                                    tool_calls=accumulated_tool_calls if accumulated_tool_calls else None
                                )
                streaming_support_cache['endpoints'][SERVING_ENDPOINT_NAME] = {
                    'supports_streaming': True,
                    'supports_trace': supports_trace,
                    'last_checked': datetime.now()
                }

            # Debug: Print accumulated content length
            print(f"Final response - accumulated_content length: {len(accumulated_content)}")
            print(f"Final response - tool_calls count: {len(accumulated_tool_calls) if accumulated_tool_calls else 0}")
            print(f"Final response - tool_responses count: {len(accumulated_tool_responses) if accumulated_tool_responses else 0}")
            
            # Only yield the final done event, not duplicate content
            yield "event: done\ndata: {}\n\n"
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def handle_non_streaming_response(
        request_handler,
        url: str,
        headers: Dict,
        request_data: Dict,
        session_id: str,
        user_id: str,
        user_info: Dict,
        message_handler
    ) -> AsyncGenerator[str, None]:
        """Handle non-streaming response from the model."""
        try:
            start_time = time.time()
            response = await request_handler.enqueue_request(url, headers, request_data)
            response_data = await request_handler.handle_databricks_response(response, start_time)
            
            assistant_message = message_handler.create_message(
                message_id=str(uuid.uuid4()),
                content=response_data["content"],
                role="assistant",
                session_id=session_id,
                user_id=user_id,
                user_info=user_info,
                sources=response_data.get("sources"),
                metrics=response_data.get("metrics"),
                trace_id=response_data.get("trace_id"),
                tool_calls=response_data.get("tool_calls")
            )
            
            yield f"data: {assistant_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception as e:
            logger.error(f"Error in non-streami ng response: {str(e)}")
            error_message = message_handler.create_error_message(
                session_id=session_id,
                user_id=user_id,
                error_content="Request timed out. " + str(e) + " Please try again later."
            )
            yield f"data: {error_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n"

    @staticmethod
    async def handle_streaming_regeneration(
        response: httpx.Response,
        request_data: Dict,
        headers: Dict,
        session_id: str,
        message_id: str,
        user_id: str,
        user_info: Dict,
        original_timestamp: str,
        start_time: float,
        first_token_time: Optional[float],
        accumulated_content: str,
        sources: Optional[Dict],
        ttft: Optional[float],
        request_handler: RequestHandler,
        message_handler,
        streaming_support_cache,
        supports_trace,
        update_flag: bool
    ) -> AsyncGenerator[str, None]:
        """Handle streaming message regeneration."""
        try:
            async for response_chunk in StreamingHandler.handle_streaming_response(
                response, request_data, headers, session_id, message_id, user_id,user_info,
                original_timestamp, start_time, first_token_time, accumulated_content,
                sources, ttft, request_handler, message_handler, streaming_support_cache, supports_trace, update_flag    
            ):
                yield response_chunk
        except Exception as e:
            logger.error(f"Error in streaming regeneration: {str(e)}")
            error_message = message_handler.create_error_message(
                session_id=session_id,
                user_id=user_id,
                error_content="Failed to regenerate response. " + str(e)
            )
            yield f"data: {error_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n" 

    @staticmethod
    async def handle_non_streaming_regeneration(
        request_handler,
        session_id: str,
        message_id: str,
        url: str,
        headers: Dict,
        request_data: Dict,
        user_id: str,
        user_info: Dict,
        original_timestamp: str,
        first_token_time: Optional[float],
        sources: Optional[Dict],
        ttft: Optional[float],
        message_handler
    ) -> AsyncGenerator[str, None]:
        """Handle non-streaming message regeneration."""    
        try:
            start_time = time.time()
            response = await request_handler.enqueue_request(url, headers, request_data)
            response_data = await request_handler.handle_databricks_response(response, start_time)
            
            update_message = message_handler.update_message(
                session_id=session_id,
                message_id=message_id,
                user_id=user_id,
                content=response_data["content"],
                sources=response_data.get("sources", []),
                timestamp=original_timestamp,
                metrics=response_data.get("metrics", {}),
                tool_calls=response_data.get("tool_calls")
            )
            
            yield f"data: {update_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n"   
        except Exception as e:
            logger.error(f"Error in non-streaming regeneration: {str(e)}")
            error_message = message_handler.update_message(
                session_id=session_id,
                message_id=message_id,
                user_id=user_id,
                content="Failed to regenerate response. " + str(e) + " Please try again.",
                sources=[],
                timestamp=original_timestamp,
                metrics=None
            )
            yield f"data: {error_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n" 