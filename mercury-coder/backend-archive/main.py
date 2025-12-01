"""
Mercury Coder - Python Backend
FastAPI server for Amazon Bedrock integration (Simple Chat)
"""

import os
import json
import uuid
import sqlite3
import asyncio
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import threading
import tempfile
import shutil
from datetime import datetime
import logging

# Memory system
from memory import MemoryManager
from memory.history_summarizer import HistorySummarizer

# Tools system
from tools import get_tool_definitions, ToolExecutor, ToolRecommender

# Multi-agent system
from agents import OrchestratorAgent
from agents.task import WorkflowStage

# Load environment variables first, before importing boto3
from dotenv import load_dotenv
load_dotenv()

# Set bearer token if API key is available (before importing boto3)
bedrock_api_key = os.getenv('BEDROCK_API_KEY')
if bedrock_api_key:
    os.environ['AWS_BEARER_TOKEN_BEDROCK'] = bedrock_api_key

import boto3
from botocore.exceptions import ClientError

app = FastAPI(title="Mercury Coder Backend")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to electron app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize memory manager
memory_manager = MemoryManager()
history_summarizer = HistorySummarizer(max_messages=20, summary_threshold=30)

# Initialize top-tier AI agent components
from agents.feedback_loop import FeedbackLoopManager
from context.file_graph import FileGraph
from tools.diff_engine import DiffEngine
from tools.ast_tools import ASTTools
from tools.code_validator import CodeValidator
from agents.proactive_search import ProactiveSearchManager
from context.pattern_matcher import PatternMatcher

# Initialize components (will be passed to agents and tools)
feedback_loop_manager = FeedbackLoopManager(max_retries=2, enabled=True)  # Reduced from 3 to 2
file_graph = FileGraph()
diff_engine = DiffEngine()
ast_tools = ASTTools()
code_validator = CodeValidator(ast_tools=ast_tools)
pattern_matcher = PatternMatcher(memory_manager=memory_manager, vector_store=memory_manager.vector_store)
proactive_search_manager = ProactiveSearchManager(
    memory_manager=memory_manager,
    file_graph=file_graph
)

# Setup logger
logger = logging.getLogger("mercury.main")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Setup debug logging to file
DEBUG_LOG_FILE = os.path.join(os.path.dirname(__file__), "debug_tools.log")

def debug_log(message: str):
    """Log debug message to both console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    try:
        with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
            f.flush()  # Ensure it's written immediately
    except Exception as e:
        print(f"⚠ Failed to write to debug log: {e}")

# Clear log file on startup
try:
    with open(DEBUG_LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== Debug Log Started at {datetime.now()} ===\n")
except Exception:
    pass

# Bedrock API configuration
bedrock_client = None
bedrock_region = None

REGION_CODE_MAP = {
    'us-east-1': 'us',
    'us-east-2': 'us',
    'us-west-1': 'us',
    'us-west-2': 'us',
    'eu-west-1': 'eu',
    'eu-west-2': 'eu',
    'eu-west-3': 'eu',
    'eu-central-1': 'eu',
    'eu-north-1': 'eu',
    'ap-southeast-1': 'ap',
    'ap-southeast-2': 'ap',
    'ap-northeast-1': 'ap',
    'ap-south-1': 'ap',
    'ca-central-1': 'ca',
    'sa-east-1': 'sa',
}

def get_bedrock_client():
    """
    Get Bedrock client using API key authentication.
    AWS_BEARER_TOKEN_BEDROCK should already be set at module import time.
    """
    global bedrock_client, bedrock_region
    
    if bedrock_client is None:
        bedrock_region = os.getenv('AWS_REGION', 'us-east-1')
        bedrock_api_key = os.getenv('BEDROCK_API_KEY')
        
        if bedrock_api_key:
            # Ensure bearer token is set (should already be set at import time)
            if 'AWS_BEARER_TOKEN_BEDROCK' not in os.environ:
                os.environ['AWS_BEARER_TOKEN_BEDROCK'] = bedrock_api_key
            
            # Create Bedrock Runtime client
            # When AWS_BEARER_TOKEN_BEDROCK is set, boto3 (>= 1.34.0) will use it automatically
            try:
                from botocore.config import Config
                
                # Configure timeouts to prevent hanging
                boto_config = Config(
                    connect_timeout=30,      # 30s to establish connection
                    read_timeout=180,        # 3 minutes for response (Claude can be slow)
                    retries={
                        'max_attempts': 3,
                        'mode': 'adaptive'   # Adaptive retry with backoff
                    }
                )
                
                bedrock_client = boto3.client(
                    service_name='bedrock-runtime',
                    region_name=bedrock_region,
                    config=boto_config
                )
                print(f"✓ Bedrock API configured for region: {bedrock_region}")
                print("✓ Using Bedrock API key authentication via boto3")
                print(f"✓ Bearer token configured (length: {len(bedrock_api_key)})")
            except Exception as e:
                error_msg = str(e)
                if "Unable to locate credentials" in error_msg:
                    raise Exception(
                        f"Unable to locate credentials. This usually means:\n"
                        f"1. boto3 version is too old (need >= 1.34.0 for bearer token support)\n"
                        f"2. Run: pip install --upgrade boto3\n"
                        f"3. Current error: {error_msg}"
                    )
                raise Exception(f"Failed to create Bedrock client: {error_msg}")
        else:
            print("✗ Bedrock API key not found")
            print("  Please set BEDROCK_API_KEY in .env file")
    
    return bedrock_client, bedrock_region


def possible_inference_profile_ids(model_id: str, region: Optional[str]) -> List[str]:
    """
    Generate possible inference profile IDs based on common naming patterns.
    Inference profiles often follow patterns like:
    - us.anthropic.claude-sonnet-4-5-20250929-v1:0
    - us-east-1.anthropic.claude-sonnet-4-5-20250929-v1:0
    - anthropic.claude-sonnet-4-5-20250929-v1:0 (without region prefix)
    """
    region_code = REGION_CODE_MAP.get(region or 'us-east-1', 'us')
    region_name = region or 'us-east-1'
    
    candidates = [
        # Pattern: {region_code}.{model_id}
        f"{region_code}.{model_id}",
        # Pattern: {region_code}.anthropic.{model_name}
        model_id.replace('anthropic.', f'{region_code}.anthropic.'),
        # Pattern: {region_name}.{model_id}
        f"{region_name}.{model_id}",
        # Pattern: {region_name}.anthropic.{model_name}
        model_id.replace('anthropic.', f'{region_name}.anthropic.'),
        # Pattern: Just the model ID (some profiles don't have region prefix)
        model_id,
        # Pattern: Extract just the model name part
        model_id.split('.')[-1] if '.' in model_id else model_id,
    ]
    
    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for candidate in candidates:
        if candidate not in seen:
            unique.append(candidate)
            seen.add(candidate)
    
    return unique

def _get_inference_profile_sync(model_id: str, region: str) -> Optional[str]:
    """
    Synchronous version of inference profile lookup for use in thread pool.
    Tries multiple strategies to find the right inference profile.
    """
    print(f"🚀 [BEDROCK] _get_inference_profile_sync called with model_id={model_id}, region={region}")
    try:
        print(f"🔧 [BEDROCK] Creating Bedrock Control Plane client for region {region}...")
        bedrock_control = get_bedrock_control_client(region)
        if not bedrock_control:
            print(f"⚠️ [BEDROCK] Could not create control client for region {region}")
            return None
        
        print(f"✅ [BEDROCK] Control client created successfully")
        print(f"🔍 [BEDROCK] Looking up inference profiles in region {region} for model {model_id}")
        
        # List inference profiles
        try:
            response = bedrock_control.list_inference_profiles()
            profiles = response.get('inferenceProfileSummaries', [])
            print(f"📋 [BEDROCK] Found {len(profiles)} inference profiles")
        except Exception as e:
            print(f"⚠️ [BEDROCK] Could not list inference profiles: {e}")
            # Try common regions if current region fails
            common_regions = ['us-east-1', 'us-east-2', 'us-west-2', 'eu-west-1']
            for alt_region in common_regions:
                if alt_region == region:
                    continue
                try:
                    print(f"🔄 [BEDROCK] Trying region {alt_region}...")
                    alt_client = get_bedrock_control_client(alt_region)
                    response = alt_client.list_inference_profiles()
                    profiles = response.get('inferenceProfileSummaries', [])
                    print(f"✅ [BEDROCK] Found {len(profiles)} profiles in {alt_region}")
                    bedrock_control = alt_client
                    region = alt_region
                    break
                except Exception:
                    continue
            else:
                return None
        
        if not profiles:
            print(f"⚠️ [BEDROCK] No inference profiles found")
            return None
        
        # Strategy 1: Find a profile that contains this model by checking model list
        print(f"🔍 [BEDROCK] Strategy 1: Checking model lists in profiles...")
        for profile in profiles:
            profile_id = profile.get('inferenceProfileId') or profile.get('inferenceProfileArn', '')
            
            # Check if this profile contains the model
            try:
                profile_details = bedrock_control.get_inference_profile(
                    inferenceProfileIdentifier=profile_id
                )
                # Check if the model is in the profile's model list
                models_in_profile = profile_details.get('modelList', [])
                for model in models_in_profile:
                    if model.get('modelId') == model_id:
                        print(f"✅ [BEDROCK] Found profile {profile_id} containing model {model_id}")
                        return profile_id
            except Exception as e:
                # If get_inference_profile fails, try the next profile
                continue
        
        # Strategy 2: Pattern matching on profile IDs
        print(f"🔍 [BEDROCK] Strategy 2: Pattern matching profile IDs...")
        possible_profile_ids = possible_inference_profile_ids(model_id, region)
        
        # Check if any of these patterns match existing profiles
        for profile in profiles:
            profile_id = profile.get('inferenceProfileId') or profile.get('inferenceProfileArn', '')
            # Try exact match first
            if profile_id in possible_profile_ids:
                print(f"✅ [BEDROCK] Found exact match: {profile_id}")
                return profile_id
            # Try substring match
            for pattern in possible_profile_ids:
                if pattern in profile_id or profile_id in pattern:
                    print(f"✅ [BEDROCK] Found pattern match: {profile_id} (matched {pattern})")
                    return profile_id
        
        # Strategy 3: Try profiles that contain the model name
        print(f"🔍 [BEDROCK] Strategy 3: Searching by model name...")
        model_name = model_id.split('.')[-1]  # e.g., "claude-sonnet-4-5-20250929-v1:0"
        for profile in profiles:
            profile_id = profile.get('inferenceProfileId') or profile.get('inferenceProfileArn', '')
            if model_name in profile_id:
                print(f"✅ [BEDROCK] Found profile by model name: {profile_id}")
                return profile_id
        
        print(f"⚠️ [BEDROCK] No matching inference profile found for {model_id}")
        return None
    except Exception as e:
        # If list_inference_profiles doesn't exist or fails, return None
        print(f"❌ [BEDROCK] Error getting inference profiles: {e}")
        import traceback
        traceback.print_exc()
        return None

async def get_inference_profile_for_model(model_id: str, region: str) -> Optional[str]:
    """
    Try to find an inference profile for a model that requires one.
    Returns the inference profile ID/ARN if found, None otherwise.
    
    Inference profiles follow a naming pattern like: us.anthropic.claude-sonnet-4-5-20250929-v1:0
    where the prefix is the region code.
    """
    try:
        bedrock_control = get_bedrock_control_client(region)
        
        def _list_profiles():
            try:
                # List inference profiles
                response = bedrock_control.list_inference_profiles()
                profiles = response.get('inferenceProfileSummaries', [])
                
                # Find a profile that contains this model
                for profile in profiles:
                    profile_id = profile.get('inferenceProfileId') or profile.get('inferenceProfileArn', '')
                    
                    # Check if this profile contains the model
                    try:
                        profile_details = bedrock_control.get_inference_profile(
                            inferenceProfileIdentifier=profile_id
                        )
                        # Check if the model is in the profile's model list
                        models_in_profile = profile_details.get('modelList', [])
                        for model in models_in_profile:
                            if model.get('modelId') == model_id:
                                # Return the profile ID (not ARN) for use in API calls
                                return profile_id
                    except Exception as detail_error:
                        # If get_inference_profile fails, try the next profile
                        continue
                
                # If no profile found by checking details, try pattern matching
                # Inference profiles often follow pattern: {region}.{model_id}
                possible_profile_ids = possible_inference_profile_ids(model_id, region)
                
                # Check if any of these patterns match existing profiles
                for profile in profiles:
                    profile_id = profile.get('inferenceProfileId') or profile.get('inferenceProfileArn', '')
                    if any(pattern in profile_id for pattern in possible_profile_ids):
                        return profile_id
                
                return None
            except Exception as e:
                # If list_inference_profiles doesn't exist or fails, return None
                print(f"Error listing inference profiles: {e}")
                return None
        
        profile_id = await asyncio.to_thread(_list_profiles)
        return profile_id
    except Exception as e:
        print(f"Warning: Could not get inference profiles: {e}")
        return None

async def invoke_bedrock_model(
    model_id: str, 
    system_prompt: str, 
    user_message: str = None,
    max_tokens: int = 8192,
    tools: Optional[List[Dict[str, Any]]] = None,
    messages: Optional[List[Dict[str, Any]]] = None,  # NEW: Native messages support
    enable_thinking: bool = False,  # NEW: Enable Claude's thinking feature
    response_format: Optional[Dict[str, Any]] = None,  # NEW: Structured outputs support
) -> dict:
    """
    Invoke Bedrock API using boto3 invoke_model() with API key authentication.
    
    Supports native Claude tool calling when tools parameter is provided.
    Claude will return structured tool_use responses - no JSON parsing needed!
    
    Args:
        model_id: The Bedrock model ID
        system_prompt: System prompt for the model
        user_message: Legacy single user message (deprecated, use messages instead)
        max_tokens: Maximum tokens in response (default 8192 for large files)
        tools: Optional list of tool definitions for native tool calling
        messages: Native Messages API format - list of message dicts with role/content
        response_format: Optional structured output format (JSON schema) for guaranteed valid JSON
    """
    client, region = get_bedrock_client()
    
    if not client:
        raise Exception("Bedrock API key not configured")
    
    # Build messages array - support both legacy and native formats
    if messages:
        # Native format: use messages directly
        api_messages = messages
    elif user_message:
        # Legacy format: wrap single message
        api_messages = [{"role": "user", "content": user_message}]
    else:
        raise Exception("Either 'messages' or 'user_message' must be provided")
    
    # Prepare the request body in Anthropic Claude format
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": api_messages
    }
    
    # Add native tool definitions if provided
    # This enables Claude to return structured tool_use responses!
    if tools:
        request_body["tools"] = tools
    
    # Add structured output format if provided (guarantees valid JSON)
    if response_format:
        request_body["response_format"] = response_format
    
    # NOTE: Extended thinking is NOT supported in invoke_model with Messages API
    # It's only available via the Converse API (handled in _invoke_with_profile and _try_converse_directly)
    # For Claude Sonnet 4.5+, the code will automatically use Converse API which supports thinking
    
    body = json.dumps(request_body)
    
    def _invoke_with_profile(profile_id: str):
        """Helper to invoke with a specific profile ID"""
        try:
            # Try invoke_model with profile (includes tools in body)
            response = client.invoke_model(
                modelId=profile_id,
                contentType="application/json",
                accept="application/json",
                body=body
            )
            response_body = json.loads(response['body'].read())
            return response_body
        except ClientError:
            # If invoke_model fails, try converse WITH TOOLS
            try:
                # Convert api_messages to converse format
                converse_messages = []
                for msg in api_messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    
                    # Handle different content formats
                    if isinstance(content, str):
                        converse_messages.append({
                            "role": role,
                            "content": [{"text": content}]
                        })
                    elif isinstance(content, list):
                        # Already in list format, convert items
                        converted_content = []
                        for item in content:
                            if isinstance(item, dict):
                                if item.get("type") == "text":
                                    converted_content.append({"text": item.get("text", "")})
                                elif item.get("type") == "tool_result":
                                    converted_content.append({
                                        "toolResult": {
                                            "toolUseId": item.get("tool_use_id", ""),
                                            "content": [{"text": str(item.get("content", ""))}]
                                        }
                                    })
                                elif item.get("type") == "tool_use":
                                    converted_content.append({
                                        "toolUse": {
                                            "toolUseId": item.get("id", ""),
                                            "name": item.get("name", ""),
                                            "input": item.get("input", {})
                                        }
                                    })
                            else:
                                converted_content.append({"text": str(item)})
                        if converted_content:
                            converse_messages.append({
                                "role": role,
                                "content": converted_content
                            })
                
                converse_params = {
                    "modelId": profile_id,
                    "messages": converse_messages if converse_messages else [{"role": "user", "content": [{"text": "Continue"}]}],
                    "system": [{"text": system_prompt}],
                    "inferenceConfig": {
                        "maxTokens": max_tokens
                    }
                }
                
                # Enable thinking if requested
                if enable_thinking:
                    converse_params["thinkingConfig"] = {
                        "type": "enabled"
                    }
                
                # Add tools to converse() if provided - THIS WAS MISSING!
                if tools:
                    converse_params["toolConfig"] = {
                        "tools": [
                            {
                                "toolSpec": {
                                    "name": t["name"],
                                    "description": t.get("description", ""),
                                    "inputSchema": {"json": t.get("input_schema", {})}
                                }
                            }
                            for t in tools
                        ]
                    }
                
                converse_response = client.converse(**converse_params)
                
                # Convert converse response format - handle text, toolUse, and thinking
                content_list = []
                if 'output' in converse_response:
                    message = converse_response['output'].get('message', {})
                    content = message.get('content', [])
                    for item in content:
                        if 'text' in item:
                            content_list.append({
                                "type": "text",
                                "text": item['text']
                            })
                        elif 'toolUse' in item:
                            # Convert converse toolUse to invoke_model format
                            tool_use = item['toolUse']
                            content_list.append({
                                "type": "tool_use",
                                "id": tool_use.get('toolUseId', ''),
                                "name": tool_use.get('name', ''),
                                "input": tool_use.get('input', {})
                            })
                        elif 'thinking' in item:
                            # Handle thinking blocks from converse API
                            thinking_text = item['thinking']
                            content_list.append({
                                "type": "thinking",
                                "text": thinking_text
                            })
                
                return {"content": content_list if content_list else [{"type": "text", "text": ""}]}
            except Exception as converse_error:
                raise Exception(f"Both invoke_model and converse failed with profile {profile_id}: {str(converse_error)}")
    
    def _try_converse_directly(model_identifier: str):
        """Try Converse API directly with model ID - sometimes works even when invoke_model doesn't"""
        try:
            # Convert api_messages to converse format
            converse_messages = []
            for msg in api_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if isinstance(content, str):
                    converse_messages.append({
                        "role": role,
                        "content": [{"text": content}]
                    })
                elif isinstance(content, list):
                    converted_content = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                converted_content.append({"text": item.get("text", "")})
                            elif item.get("type") == "tool_result":
                                converted_content.append({
                                    "toolResult": {
                                        "toolUseId": item.get("tool_use_id", ""),
                                        "content": [{"text": str(item.get("content", ""))}]
                                    }
                                })
                        else:
                            converted_content.append({"text": str(item)})
                    if converted_content:
                        converse_messages.append({
                            "role": role,
                            "content": converted_content
                        })
            
            converse_params = {
                "modelId": model_identifier,
                "messages": converse_messages if converse_messages else [{"role": "user", "content": [{"text": "Continue"}]}],
                "system": [{"text": system_prompt}],
                "inferenceConfig": {
                    "maxTokens": max_tokens
                }
            }
            
            if enable_thinking:
                converse_params["thinkingConfig"] = {"type": "enabled"}
            
            if tools:
                converse_params["toolConfig"] = {
                    "tools": [
                        {
                            "toolSpec": {
                                "name": t["name"],
                                "description": t.get("description", ""),
                                "inputSchema": {"json": t.get("input_schema", {})}
                            }
                        }
                        for t in tools
                    ]
                }
            
            converse_response = client.converse(**converse_params)
            
            # Convert converse response format
            content_list = []
            if 'output' in converse_response:
                message = converse_response['output'].get('message', {})
                content = message.get('content', [])
                for item in content:
                    if 'text' in item:
                        content_list.append({"type": "text", "text": item['text']})
                    elif 'toolUse' in item:
                        tool_use = item['toolUse']
                        content_list.append({
                            "type": "tool_use",
                            "id": tool_use.get('toolUseId', ''),
                            "name": tool_use.get('name', ''),
                            "input": tool_use.get('input', {})
                        })
                    elif 'thinking' in item:
                        content_list.append({
                            "type": "thinking",
                            "text": item['thinking']
                        })
            
            return {"content": content_list if content_list else [{"type": "text", "text": ""}]}
        except Exception as e:
            return None  # Return None to indicate failure, don't raise
    
    # Check if this model typically requires inference profiles or extended thinking
    # Claude Sonnet 4.5 and newer models often require inference profiles
    # Extended thinking ONLY works with Converse API, not invoke_model
    models_requiring_profiles = [
        'claude-sonnet-4-5',
        'claude-sonnet-4',
        'claude-opus-4',
        'claude-4'
    ]
    model_requires_profile = any(m in model_id.lower() for m in models_requiring_profiles)
    
    def _invoke():
        try:
            # For models that require inference profiles OR when thinking is enabled,
            # try Converse API first (thinking only works with Converse API)
            if model_requires_profile or enable_thinking:
                reason = "requires inference profile" if model_requires_profile else "thinking enabled"
                print(f"🔍 [BEDROCK] Model {model_id} {reason}, trying Converse API first...")
                converse_result = _try_converse_directly(model_id)
                if converse_result:
                    print(f"✅ [BEDROCK] Converse API worked directly with model ID!")
                    return converse_result
                else:
                    print(f"⚠️ [BEDROCK] Converse API failed, trying invoke_model...")
            
            # Try using invoke_model() with the model ID directly
            try:
                response = client.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=body
                )
                response_body = json.loads(response['body'].read())
                return response_body
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_msg = e.response.get('Error', {}).get('Message', str(e))
                
                # If the error indicates inference profile is needed, try Converse API first
                if 'inference profile' in error_msg.lower() or error_code == 'ValidationException':
                    if not model_requires_profile and not enable_thinking:  # Only try if we haven't already
                        print(f"🔍 [BEDROCK] Model requires inference profile, trying Converse API directly with model ID...")
                        converse_result = _try_converse_directly(model_id)
                        if converse_result:
                            print(f"✅ [BEDROCK] Converse API worked directly with model ID!")
                            return converse_result
                        else:
                            print(f"⚠️ [BEDROCK] Converse API failed, trying inference profile lookup...")
                    
                    # If Converse API also fails, find and use inference profile
                    # First, try to get inference profile from Bedrock Control Plane
                    print(f"🔍 [BEDROCK] Model requires inference profile, looking up available profiles...")
                    print(f"🔍 [BEDROCK] Model ID: {model_id}, Region: {region}")
                    try:
                        profile_id = _get_inference_profile_sync(model_id, region)
                        print(f"🔍 [BEDROCK] Lookup result: {profile_id}")
                    except Exception as lookup_error:
                        print(f"❌ [BEDROCK] Inference profile lookup exception: {lookup_error}")
                        import traceback
                        traceback.print_exc()
                        profile_id = None
                    
                    if profile_id:
                        print(f"✅ [BEDROCK] Found inference profile: {profile_id}")
                        try:
                            return _invoke_with_profile(profile_id)
                        except Exception as profile_error:
                            print(f"⚠️ [BEDROCK] Profile {profile_id} failed: {profile_error}")
                            # Fall through to pattern matching
                    else:
                        print(f"⚠️ [BEDROCK] No inference profile found via API lookup, trying pattern matching...")
                    
                    # Fallback: try pattern matching
                    possible_profile_ids = possible_inference_profile_ids(model_id, region)
                    print(f"🔍 [BEDROCK] Trying pattern matching with: {possible_profile_ids}")

                    # Try each possible profile ID
                    for profile_id in possible_profile_ids:
                        try:
                            print(f"🔄 [BEDROCK] Trying profile: {profile_id}")
                            return _invoke_with_profile(profile_id)
                        except Exception as profile_error:
                            print(f"⚠️ [BEDROCK] Profile {profile_id} failed: {profile_error}")
                            # Try next pattern
                            continue
                    
                    # If all patterns fail, raise helpful error
                    raise Exception(
                        f"Model {model_id} requires an inference profile. "
                        f"Tried patterns: {possible_profile_ids}. "
                        f"Original error: {error_msg}. "
                        f"Please check AWS Bedrock console for available inference profiles or use a different model."
                    )
                else:
                    # For other errors, raise as-is
                    raise Exception(f"Bedrock API error ({error_code}): {error_msg}")
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            raise Exception(f"Bedrock API error ({error_code}): {error_msg}")
        except Exception as e:
            raise Exception(f"Failed to invoke Bedrock API: {str(e)}")
    
    # Run the synchronous boto3 call in a thread pool
    response = await asyncio.to_thread(_invoke)
    return response


def extract_bedrock_text(response: dict) -> str:
    """
    Normalize Bedrock responses (invoke_model or converse) into plain text.
    """
    if not response:
        return ""

    content = response.get('content')
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if 'text' in item and isinstance(item['text'], str):
                    return item['text']
                if item.get('type') == 'text' and isinstance(item.get('text'), str):
                    return item['text']
    return ""


def stream_bedrock_events(
    model_id: str, 
    system_prompt: str, 
    user_message: str = None,
    messages: Optional[List[Dict[str, Any]]] = None,
    max_tokens: int = 2048,
    tools: Optional[List[Dict[str, Any]]] = None
):
    """
    Blocking generator that yields raw Bedrock streaming events.
    
    Args:
        model_id: Bedrock model ID
        system_prompt: System prompt
        user_message: Legacy single user message (deprecated, use messages)
        messages: Messages array in Claude API format (preferred)
        max_tokens: Maximum tokens in response
        tools: Optional list of tool definitions
    """
    client, region = get_bedrock_client()
    if not client:
        raise Exception("Bedrock API key not configured")

    # Build messages array
    if messages:
        api_messages = messages
    elif user_message:
        api_messages = [{"role": "user", "content": user_message}]
    else:
        raise Exception("Either 'messages' or 'user_message' must be provided")

    body_dict = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": api_messages
    }
    
    # Add tools if provided
    if tools:
        body_dict["tools"] = tools
    
    body = json.dumps(body_dict)

    def _invoke(model_identifier: str):
        return client.invoke_model_with_response_stream(
            modelId=model_identifier,
            body=body,
            contentType="application/json",
            accept="application/json"
        )

    try:
        response = _invoke(model_id)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        if 'inference profile' in error_msg.lower() or error_code == 'ValidationException':
            candidates = possible_inference_profile_ids(model_id, region)
            for profile_id in candidates:
                try:
                    response = _invoke(profile_id)
                    break
                except ClientError:
                    continue
            else:
                raise Exception(
                    f"Model {model_id} requires an inference profile. "
                    f"Tried profiles: {candidates}. Original error: {error_msg}"
                )
        else:
            raise

    for event in response.get('body', []):
        if 'chunk' in event:
            try:
                chunk = event['chunk']['bytes']
                decoded = chunk.decode('utf-8')
                payload = json.loads(decoded)
                yield payload
            except Exception:
                continue
        elif 'internalServerException' in event:
            message = event['internalServerException'].get('message', 'Internal server error')
            raise Exception(message)
        elif 'validationException' in event:
            message = event['validationException'].get('message', 'Validation error')
            raise Exception(message)
        elif 'throttlingException' in event:
            message = event['throttlingException'].get('message', 'Throttled by Bedrock')
            raise Exception(message)


def translate_stream_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convert Bedrock stream event into a simple payload for the frontend.
    """
    if not event:
        return None

    event_type = event.get("type")

    if event_type == "content_block_delta":
        delta = event.get("delta", {})
        if delta.get("type") == "text_delta":
            return {"type": "delta", "text": delta.get("text", "")}
        elif delta.get("type") == "input_json_delta":
            # Tool use input streaming - return the raw event too for accumulation
            partial_json = delta.get("partial_json", "")
            debug_log(f"📥 Input JSON delta received: {partial_json[:100]}...")
            return {
                "type": "tool_input_delta",
                "text": partial_json,
                "raw_event": event  # Keep raw event for reference
            }
    elif event_type == "message_start":
        return {"type": "status", "message": "Assistant is composing a response…"}
    elif event_type == "message_delta":
        usage = event.get("usage", {})
        if usage:
            return {"type": "metadata", "usage": usage}
    elif event_type == "message_stop":
        return {"type": "status", "message": "Finalizing response…"}
    elif event_type == "content_block_start":
        content = event.get("content_block", {})
        if content.get("type") == "text":
            return {"type": "status", "message": "Generating text…"}
        elif content.get("type") == "tool_use":
            # Tool use started - the content_block IS the tool_use object
            # (not nested under a "tool_use" key)
            tool_id = content.get("id")
            tool_name = content.get("name")
            tool_input = content.get("input", {})
            
            # Debug logging
            debug_log(f"🔧 Tool use started: {tool_name} (id: {tool_id})")
            debug_log(f"   Initial input: {tool_input}")
            debug_log(f"   Full content block: {json.dumps(content, indent=2)}")
            
            return {
                "type": "tool_use_start",
                "tool_use_id": tool_id,
                "name": tool_name,
                "input": tool_input
            }
    elif event_type == "content_block_stop":
        # content_block_stop doesn't include content type, so we always emit it
        # The handler will check if there's an active tool_use to process
        return {"type": "content_block_stop"}
    elif event_type == "metadata":
        usage = event.get("usage", {})
        if usage:
            return {"type": "metadata", "usage": usage}
    return None


def format_sse_payload(data: Dict[str, Any]) -> str:
    return f"data: {json.dumps(data)}\n\n"


# Request/Response models
class ChatMessage(BaseModel):
    message: str
    context: Optional[Dict] = None

class ChatResponse(BaseModel):
    response: str
    success: bool = True
    error: Optional[str] = None

class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    description: str
    status: str  # "active", "legacy", "available"

class AvailableModelsResponse(BaseModel):
    models: List[ModelInfo]
    current_model: str
    success: bool = True

class SetModelRequest(BaseModel):
    model_id: str
    region: Optional[str] = None

class SetModelResponse(BaseModel):
    model_id: str
    success: bool = True
    message: str

@app.get("/")
async def root():
    client, _ = get_bedrock_client()
    configured = client is not None
    
    return {
        "status": "online",
        "service": "Mercury Coder Backend",
        "bedrock_available": configured,
        "credentials_status": "configured" if configured else "not configured - check BEDROCK_API_KEY in .env file"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

def get_bedrock_control_client(region: str = None):
    """
    Get Bedrock control plane client for listing models
    """
    if region is None:
        region = os.getenv('AWS_REGION', 'us-east-1')
    
    bedrock_api_key = os.getenv('BEDROCK_API_KEY')
    if bedrock_api_key and 'AWS_BEARER_TOKEN_BEDROCK' not in os.environ:
        os.environ['AWS_BEARER_TOKEN_BEDROCK'] = bedrock_api_key
    
    try:
        from botocore.config import Config
        
        # Add timeout config
        boto_config = Config(
            connect_timeout=30,
            read_timeout=60,
            retries={'max_attempts': 2, 'mode': 'standard'}
        )
        
        client = boto3.client(
            service_name='bedrock',
            region_name=region,
            config=boto_config
        )
        return client
    except Exception as e:
        raise Exception(f"Failed to create Bedrock control client: {str(e)}")

@app.get("/api/models/available", response_model=AvailableModelsResponse)
async def get_available_models(region: Optional[str] = Query(None, description="AWS region to fetch models from")):
    """
    Get list of available Bedrock models from AWS API
    """
    try:
        if region is None:
            region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Get Bedrock control client
        bedrock_client = get_bedrock_control_client(region)
        
        def _list_models():
            try:
                # List foundation models
                response = bedrock_client.list_foundation_models()
                return response.get('modelSummaries', [])
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_msg = e.response.get('Error', {}).get('Message', str(e))
                raise Exception(f"Bedrock API error ({error_code}): {error_msg}")
            except Exception as e:
                raise Exception(f"Failed to list models: {str(e)}")
        
        # Run in thread pool
        model_summaries = await asyncio.to_thread(_list_models)
        
        # Convert to ModelInfo format
        models = []
        for model in model_summaries:
            # Extract provider from model ID (e.g., "anthropic.claude-3-5-sonnet" -> "Anthropic")
            provider_name = model.get('providerName', 'Unknown')
            if provider_name:
                # Capitalize first letter
                provider = provider_name.capitalize()
            else:
                # Fallback: extract from model ID
                model_id = model.get('modelId', '')
                if '.' in model_id:
                    provider = model_id.split('.')[0].capitalize()
                else:
                    provider = 'Unknown'
            
            # Determine status
            model_lifecycle = model.get('modelLifecycle', {})
            status = model_lifecycle.get('status', 'available')
            if status == 'ACTIVE':
                status = 'active'
            elif status == 'LEGACY':
                status = 'legacy'
            else:
                status = 'available'
            
            models.append(ModelInfo(
                id=model.get('modelId', ''),
                name=model.get('modelName', model.get('modelId', 'Unknown')),
                provider=provider,
                description=model.get('modelName', '') or f"{provider} model",
                status=status
            ))
        
        # Sort: active first, then by name
        models.sort(key=lambda x: (x.status != 'active', x.name))
        
        current_model = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        
        return AvailableModelsResponse(
            models=models,
            current_model=current_model,
            success=True
        )
    except Exception as e:
        # Fallback to hardcoded list if API fails
        print(f"Warning: Failed to fetch models from Bedrock: {e}")
        models = [
            ModelInfo(
                id="anthropic.claude-3-5-sonnet-20241022-v2:0",
                name="Claude 3.5 Sonnet v2",
                provider="Anthropic",
                description="Most capable model, balanced performance (November 2024)",
                status="active"
            ),
            ModelInfo(
                id="anthropic.claude-3-5-haiku-20241022-v1:0",
                name="Claude 3.5 Haiku",
                provider="Anthropic",
                description="Fastest and most cost-effective (November 2024)",
                status="active"
            )
        ]
        current_model = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        return AvailableModelsResponse(
            models=models,
            current_model=current_model,
            success=True
        )

@app.get("/api/models/current")
async def get_current_model():
    """
    Get currently configured model
    """
    current_model = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
    return {
        "model_id": current_model,
        "success": True
    }

@app.post("/api/models/set", response_model=SetModelResponse)
async def set_model(request: SetModelRequest):
    """
    Set the active Bedrock model and region (updates .env file)
    """
    try:
        import os.path
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        
        # Read current .env file
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update BEDROCK_MODEL_ID line
        updated_model = False
        updated_region = False
        for i, line in enumerate(lines):
            if line.startswith('BEDROCK_MODEL_ID='):
                lines[i] = f'BEDROCK_MODEL_ID={request.model_id}\n'
                updated_model = True
            elif request.region and line.startswith('AWS_REGION='):
                lines[i] = f'AWS_REGION={request.region}\n'
                updated_region = True
        
        # Add if not found
        if not updated_model:
            lines.append(f'BEDROCK_MODEL_ID={request.model_id}\n')
        if request.region and not updated_region:
            lines.append(f'AWS_REGION={request.region}\n')
        
        # Write back to .env
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        # Update environment variable in current process
        os.environ['BEDROCK_MODEL_ID'] = request.model_id
        if request.region:
            os.environ['AWS_REGION'] = request.region
            # Reset bedrock client to use new region
            global bedrock_client, bedrock_region
            bedrock_client = None
            bedrock_region = request.region
        
        return SetModelResponse(
            model_id=request.model_id,
            success=True,
            message=f"Model updated to {request.model_id}" + (f" in region {request.region}" if request.region else "")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update model: {str(e)}")

@app.get("/api/regions")
async def get_available_regions():
    """
    Get list of AWS regions that support Bedrock
    """
    # AWS regions that support Bedrock
    bedrock_regions = [
        "us-east-1", "us-east-2", "us-west-1", "us-west-2",
        "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", "eu-north-1",
        "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ap-south-1",
        "ca-central-1", "sa-east-1"
    ]
    
    current_region = os.getenv('AWS_REGION', 'us-east-1')
    
    return {
        "regions": bedrock_regions,
        "current_region": current_region,
        "success": True
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatMessage):
    """
    Send a message to the AI assistant using Amazon Bedrock
    """
    context = request.context or {}
    try:
        client, _ = get_bedrock_client()
        if not client:
            return ChatResponse(
                response="AWS Bedrock is not configured. Please set BEDROCK_API_KEY in .env file.",
                success=False,
                error="Bedrock API key not available"
            )

        model_id = context.get('modelId') or os.getenv(
            'BEDROCK_MODEL_ID',
            'anthropic.claude-3-5-sonnet-20241022-v2:0'
        )

        project_path = context.get('projectPath')
        session_id = context.get('sessionId') or str(uuid.uuid4())

        # Retrieve relevant context from memory
        memory_context = memory_manager.get_context_for_query(
            query=request.message,
            project_path=project_path,
            limit=5
        )

        # Get optimized conversation history (with summarization if needed)
        conversation_history = memory_manager.get_optimized_conversation_history(
            project_path=project_path,
            session_id=session_id,
            max_tokens=6000,  # Reserve tokens for system prompt and response
            keep_recent=10
        )

        # Enhanced system prompt with memory guidance
        system_prompt = (
            "You are a concise yet thorough AI coding assistant. "
            "Provide actionable guidance based on the project context.\n\n"
            "# MEMORY & CONTEXT USAGE\n"
            "You have access to memory from past conversations. When you see 'Relevant Memories' or 'Similar Past Tasks' in your instructions:\n"
            "- Review the context carefully\n"
            "- Apply similar patterns if applicable\n"
            "- Learn from past successes\n"
            "- Avoid repeating past mistakes\n\n"
            "Use this context to inform your decisions and approach."
        )

        # Add memory context to system prompt if available
        if memory_context:
            system_prompt += f"\n\n{memory_context}"

        # Build messages array for Claude API
        # Include conversation history if available
        messages = []
        
        # Add conversation history (already in Claude format)
        messages.extend(conversation_history)
        
        # Add current user message
        user_message = request.message
        if context.get('activeFile'):
            user_message += f"\n\nActive file: {context.get('activeFile')}"
        if project_path:
            user_message += f"\n\nProject path: {project_path}"
        
        messages.append({
            "role": "user",
            "content": user_message
        })

        # Use messages API instead of single user_message
        response = await invoke_bedrock_model(
            model_id=model_id,
            system_prompt=system_prompt,
            messages=messages,  # Use messages array
            max_tokens=2048
        )

        ai_response = extract_bedrock_text(response)

        if not ai_response:
            print(f"Unexpected response format: {json.dumps(response, indent=2)}")
            raise Exception(f"Unexpected API response format. Response keys: {list(response.keys())}")

        # Save conversation to memory
        try:
            memory_manager.save_conversation(
                project_path=project_path,
                session_id=session_id,
                user_message=request.message,
                assistant_response=ai_response,
                metadata=context
            )
        except Exception as mem_error:
            # Don't fail the request if memory save fails
            print(f"Warning: Failed to save to memory: {mem_error}")

        return ChatResponse(response=ai_response, success=True)

    except Exception as e:
        error_msg = str(e)
        return ChatResponse(
            response=f"Error: {error_msg}",
            success=False,
            error=error_msg
        )

@app.post("/api/chat/stream")
async def chat_stream(request: ChatMessage):
    """
    Stream AI responses as Server-Sent Events so the UI can render partial output.
    Handles tool calls and executes them, feeding results back to the model.
    """
    context = request.context or {}
    model_id = context.get('modelId') or os.getenv(
        'BEDROCK_MODEL_ID',
        'anthropic.claude-3-5-sonnet-20241022-v2:0'
    )

    project_path = context.get('projectPath')
    session_id = context.get('sessionId') or str(uuid.uuid4())

    # Initialize tool executor and recommender
    tool_executor = ToolExecutor(
        project_root=project_path,
        feedback_loop_manager=feedback_loop_manager,
        file_graph=file_graph,
        diff_engine=diff_engine,
        ast_tools=ast_tools,
        code_validator=code_validator
    )
    # Set tool executor in feedback loop manager
    feedback_loop_manager.tool_executor = tool_executor
    tools = get_tool_definitions()
    
    # Initialize tool recommender with vector store from memory manager
    tool_recommender = ToolRecommender(vector_store=memory_manager.vector_store)
    
    # Always initialize orchestrator - it will decide workflow complexity
    from agents import OrchestratorAgent
    debug_log("🔧 Initializing OrchestratorAgent...")
    orchestrator = OrchestratorAgent(
        memory_manager=memory_manager,
        tool_executor=tool_executor,
        tool_recommender=tool_recommender,
        model_id=model_id,
        invoke_bedrock_model=invoke_bedrock_model,
        all_tools=tools,
        file_graph=file_graph,
        pattern_matcher=pattern_matcher,
        proactive_search_manager=proactive_search_manager,
        feedback_loop_manager=feedback_loop_manager
    )
    debug_log("✅ OrchestratorAgent initialized successfully")

    # Retrieve relevant context from memory
    memory_context = memory_manager.get_context_for_query(
        query=request.message,
        project_path=project_path,
        limit=5
    )
    
    # Get tool recommendations based on user query
    recommended_tools = tool_recommender.recommend_tools(
        query=request.message,
        limit=5,
        use_vector_search=True
    )

    # Get optimized conversation history (with summarization if needed)
    conversation_history = memory_manager.get_optimized_conversation_history(
        project_path=project_path,
        session_id=session_id,
        max_tokens=6000,  # Reserve tokens for system prompt and response
        keep_recent=10
    )

    # Enhanced system prompt with memory and tool guidance
    system_prompt = (
        "You are a concise yet thorough AI coding assistant. "
        "Provide actionable guidance based on the project context.\n\n"
        "# MEMORY & CONTEXT USAGE\n"
        "You have access to memory from past conversations. When you see 'Relevant Memories' or 'Similar Past Tasks' in your instructions:\n"
        "- Review the context carefully\n"
        "- Apply similar patterns if applicable\n"
        "- Learn from past successes\n"
        "- Avoid repeating past mistakes\n\n"
    )
    
    # Add detailed tool descriptions with recommendations
    tool_descriptions = tool_recommender.get_tool_descriptions_for_prompt(
        recommended_tools=recommended_tools if recommended_tools else None,
        include_all=True  # Include all tools but highlight recommended ones
    )
    system_prompt += f"\n{tool_descriptions}\n"
    
    # Add recommended tools context if available
    if recommended_tools:
        recommended_context = tool_recommender.get_recommended_tools_context(
            query=request.message,
            limit=3
        )
        if recommended_context:
            system_prompt += f"\n{recommended_context}\n"

    # Add memory context to system prompt if available
    if memory_context:
        system_prompt += f"\n\n{memory_context}"

    # Build messages array for streaming
    messages = []
    
    # Add conversation history (already in Claude format)
    messages.extend(conversation_history)
    
    # Add current user message
    user_message = request.message
    if context.get('activeFile'):
        user_message += f"\n\nActive file: {context.get('activeFile')}"
    if project_path:
        user_message += f"\n\nProject path: {project_path}"
    
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    # Always use orchestrator - it decides workflow complexity
    if orchestrator:
        debug_log("🤖 Using orchestrator for autonomous workflow")
        # Use thread-safe queue for cross-thread communication
        import queue as thread_queue
        status_queue = thread_queue.Queue()
        
        def status_callback(status_update: Dict[str, Any]):
            """Callback for workflow status updates."""
            debug_log(f"📥 Status callback received: {status_update.get('type')} - {status_update.get('message')}")
            try:
                status_queue.put_nowait(status_update)
                debug_log(f"✅ Status update queued successfully")
            except Exception as e:
                debug_log(f"❌ Failed to queue status update: {e}")
        
        orchestrator.set_status_callback(status_callback)
        
        # Run orchestrator workflow in background thread
        def run_workflow():
            try:
                debug_log(f"🔄 Starting workflow thread for: {request.message[:100]}")
                
                # Build context with conversation history for smart follow-up detection
                workflow_context = {
                    "conversation_history": conversation_history,
                    "memory_context": memory_context,
                    "recent_messages": conversation_history[-3:] if conversation_history else []  # Last 3 messages for context
                }
                
                result = asyncio.run(orchestrator.execute_workflow(
                    user_request=request.message,
                    project_path=project_path,
                    session_id=session_id,
                    context=workflow_context
                ))
                debug_log(f"✅ Workflow completed: success={result.get('success')}")
                
                # Log actual response text if available
                if result.get("success"):
                    if result.get("simple_task"):
                        task_result = result.get("result", {})
                        response_text = None
                        if isinstance(task_result, dict):
                            response_text = task_result.get("message") or task_result.get("result", {}).get("message")
                        if response_text:
                            debug_log(f"💬 AI Response: {response_text[:200]}...")
                    else:
                        # Complex workflow - try to extract from execution
                        execution = result.get("execution", {})
                        debug_log(f"📊 Execution result keys: {list(execution.keys()) if execution else 'None'}")
                
                # Send final result
                if result.get("success"):
                    plan = result.get("plan", {})
                    
                    # Extract actual response text for simple tasks
                    response_text = None
                    if result.get("simple_task"):
                        # Simple task - extract message from result
                        task_result = result.get("result", {})
                        if isinstance(task_result, dict):
                            response_text = task_result.get("message") or task_result.get("result", {}).get("message")
                        elif isinstance(task_result, str):
                            response_text = task_result
                    else:
                        # Complex workflow - extract from execution results
                        execution_result = result.get("execution", {})
                        if execution_result:
                            # Try to get message from last completed task
                            plan_data = result.get("plan", {})
                            if plan_data and isinstance(plan_data, dict):
                                tasks = plan_data.get("tasks", [])
                                for task in reversed(tasks):  # Check from last task
                                    if task.get("status") == "completed":
                                        task_result = task.get("result", {})
                                        if task_result:
                                            response_text = task_result.get("message") or task_result.get("result", {}).get("message")
                                            if response_text:
                                                break
                    
                    status_queue.put_nowait({
                        "type": "workflow_complete",
                        "success": True,
                        "plan": plan,
                        "message": response_text or "Workflow completed successfully!",
                        "response_text": response_text  # Include actual response
                    })
                else:
                    error_msg = result.get("error", "Workflow failed")
                    stage = result.get("stage", "unknown")
                    debug_log(f"❌ Workflow failed: {error_msg} (stage: {stage})")
                    debug_log(f"   Full result: {result}")
                    status_queue.put_nowait({
                        "type": "workflow_complete",
                        "success": False,
                        "error": error_msg,
                        "stage": stage,
                        "message": f"Workflow failed: {error_msg}",
                        "details": result
                    })
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                error_msg = str(e)
                debug_log(f"❌ Exception in workflow thread: {e}")
                debug_log(f"   Traceback:\n{error_trace}")
                logger.error(f"Workflow error: {e}", exc_info=True)
                status_queue.put_nowait({
                    "type": "workflow_complete",
                    "success": False,
                    "error": error_msg,
                    "message": f"Workflow error: {error_msg}",
                    "stage": "error",
                    "traceback": error_trace
                })
        
        # Start workflow in background
        workflow_thread = threading.Thread(target=run_workflow, daemon=True)
        workflow_thread.start()
        
        # Stream workflow updates
        async def event_generator():
            debug_log("🚀 Starting workflow event generator")
            yield format_sse_payload({"type": "status", "message": "Starting autonomous workflow..."})
            
            while True:
                try:
                    # Check if queue has items (non-blocking check)
                    if not status_queue.empty():
                        payload = status_queue.get_nowait()
                        # Better logging for workflow_complete events
                        if payload.get("type") == "workflow_complete":
                            success = payload.get("success", False)
                            error = payload.get("error", "")
                            stage = payload.get("stage", "")
                            message = payload.get("message", "")
                            debug_log(f"📤 Streaming workflow_complete: success={success}, error={error}, stage={stage}, message={message}")
                            debug_log(f"   Full payload: {json.dumps(payload, indent=2)}")
                        else:
                            debug_log(f"📤 Streaming payload: {payload.get('type')} - {payload.get('message', '')}")
                        if payload.get("type") == "workflow_complete":
                            yield format_sse_payload(payload)
                            yield format_sse_payload({"type": "done"})
                            break
                        yield format_sse_payload(payload)
                    else:
                        # Queue is empty - check if thread is done
                        if not workflow_thread.is_alive():
                            # Thread finished - check for any remaining items
                            if not status_queue.empty():
                                continue  # Process remaining items
                            debug_log("🛑 Workflow thread finished, closing stream")
                            yield format_sse_payload({"type": "done"})
                            break
                        # Wait a bit before checking again
                        await asyncio.sleep(0.1)
                except Exception as e:
                    debug_log(f"❌ Error in event generator: {e}")
                    # Check if thread is still alive
                    if not workflow_thread.is_alive():
                        debug_log("🛑 Workflow thread finished, closing stream")
                        yield format_sse_payload({"type": "done"})
                        break
                    await asyncio.sleep(0.1)
                    continue
        
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # Continue with normal chat flow if not autonomous mode
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    full_response = []  # Collect full response for saving to memory
    max_tool_iterations = 10  # Prevent infinite tool loops
    tool_iteration = 0

    def handle_tool_calls(current_messages: List[Dict], current_tool_calls: List[Dict]) -> List[Dict]:
        """Execute tool calls and add results to messages (synchronous, runs in thread)."""
        nonlocal tool_iteration
        tool_iteration += 1
        
        if tool_iteration > max_tool_iterations:
            queue.put_nowait({
                "type": "error",
                "message": "Maximum tool iterations reached. Stopping to prevent infinite loop."
            })
            return current_messages
        
        # Add assistant message with tool uses
        assistant_content = []
        for tool_call in current_tool_calls:
            assistant_content.append({
                "type": "tool_use",
                "id": tool_call["id"],
                "name": tool_call["name"],
                "input": tool_call["input"]
            })
        
        current_messages.append({
            "role": "assistant",
            "content": assistant_content
        })
        
        # Execute tools and collect results
        tool_results = []
        for tool_call in current_tool_calls:
            tool_name = tool_call["name"]
            tool_input = tool_call["input"]
            tool_id = tool_call["id"]
            
            # Notify frontend about tool execution
            debug_log(f"🔨 Executing tool: {tool_name} with input: {tool_input}")
            queue.put_nowait({
                "type": "tool_execution",
                "tool_use_id": tool_id,
                "name": tool_name,
                "input": tool_input
            })
            
            # Execute tool
            result = tool_executor.execute(tool_name, tool_input)
            debug_log(f"🔨 Tool {tool_name} result: success={result.get('success')}, error={result.get('error', 'none')}")
            
            # Save tool usage to memory for learning
            try:
                memory_manager.save_tool_usage(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_result=result,
                    user_query=request.message,
                    project_path=project_path,
                    success=result.get("success", False)
                )
            except Exception as e:
                logger.warning(f"Failed to save tool usage: {e}")
            
            # Notify frontend about tool result
            queue.put_nowait({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "name": tool_name,
                "result": result
            })
            
            # Format result for Claude
            if result.get("success"):
                result_content = json.dumps(result.get("result", {}), indent=2)
            else:
                result_content = f"Error: {result.get('error', 'Unknown error')}"
            
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result_content
            })
        
        # Add tool results to messages
        current_messages.append({
            "role": "user",
            "content": tool_results
        })
        
        return current_messages

    def producer():
        nonlocal messages, full_response, tool_iteration
        
        try:
            while tool_iteration <= max_tool_iterations:
                # Use non-streaming for tool execution rounds (simpler)
                # Only stream the final text response
                if tool_iteration > 0:
                    # We're in a tool execution round - use non-streaming
                    # Run in thread pool to avoid blocking
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(invoke_bedrock_model(
                                model_id=model_id,
                                system_prompt=system_prompt,
                                messages=messages,
                                max_tokens=16384,
                                tools=tools
                            ))
                        )
                        response = future.result()
                    
                    # Extract tool calls and text from response
                    content = response.get("content", [])
                    tool_calls = []
                    text_parts = []
                    
                    for block in content:
                        if block.get("type") == "tool_use":
                            tool_calls.append({
                                "id": block.get("id"),
                                "name": block.get("name"),
                                "input": block.get("input", {})
                            })
                        elif block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                    
                    # If we have tool calls, execute them
                    if tool_calls:
                        messages = handle_tool_calls(messages, tool_calls)
                        tool_iteration += 1
                        continue
                    else:
                        # Final text response - stream it
                        final_text = "".join(text_parts)
                        if final_text:
                            full_response.append(final_text)
                            # Stream the text in chunks for better UX
                            chunk_size = 50
                            for i in range(0, len(final_text), chunk_size):
                                chunk = final_text[i:i+chunk_size]
                                queue.put_nowait({"type": "delta", "text": chunk})
                        break
                else:
                    # First iteration - stream the response
                    current_tool_calls = []
                    current_text = []
                    current_tool_use = None
                    tool_input_buffer = {}  # Buffer for streaming tool inputs
                    
                    for raw_event in stream_bedrock_events(
                        model_id=model_id,
                        system_prompt=system_prompt,
                        messages=messages,
                        max_tokens=16384,  # Increased for large file operations
                        tools=tools
                    ):
                        # Debug: log raw event type
                        event_type = raw_event.get("type", "unknown")
                        if event_type in ["content_block_start", "content_block_delta", "content_block_stop"]:
                            debug_log(f"📦 Raw event: {event_type}")
                            if event_type == "content_block_start":
                                content = raw_event.get("content_block", {})
                                if content.get("type") == "tool_use":
                                    debug_log(f"   Tool use block: {json.dumps(content, indent=2)}")
                            elif event_type == "content_block_delta":
                                delta = raw_event.get("delta", {})
                                if delta.get("type") == "input_json_delta":
                                    debug_log(f"   Input delta: {delta.get('partial_json', '')[:100]}")
                        
                        payload = translate_stream_event(raw_event)
                        if not payload:
                            continue
                        
                        # Handle tool use events
                        if payload.get("type") == "tool_use_start":
                            tool_id = payload.get("tool_use_id")
                            tool_name = payload.get("name")
                            tool_input = payload.get("input", {}) or {}
                            
                            if not tool_id:
                                debug_log(f"⚠ ERROR: tool_use_start received without tool_use_id!")
                                debug_log(f"   Payload: {json.dumps(payload, indent=2)}")
                                continue
                            
                            current_tool_use = {
                                "id": tool_id,
                                "name": tool_name,
                                "input": tool_input
                            }
                            tool_input_buffer[tool_id] = ""  # Initialize buffer
                            debug_log(f"✓ Initialized tool buffer for {tool_id} ({tool_name})")
                            queue.put_nowait(payload)
                        elif payload.get("type") == "tool_input_delta":
                            # Accumulate streaming tool input
                            tool_id = current_tool_use.get("id") if current_tool_use else None
                            
                            if not tool_id:
                                debug_log(f"⚠ WARNING: tool_input_delta received but no current_tool_use!")
                                debug_log(f"   Payload: {payload}")
                                # Try to find tool_id from raw event if available
                                raw_event = payload.get("raw_event", {})
                                if raw_event:
                                    # The tool_id might be in the event structure
                                    debug_log(f"   Raw event: {json.dumps(raw_event, indent=2)}")
                                continue
                            
                            if tool_id not in tool_input_buffer:
                                tool_input_buffer[tool_id] = ""
                            
                            delta_text = payload.get("text", "")
                            if delta_text:
                                tool_input_buffer[tool_id] += delta_text
                                debug_log(f"📝 Accumulating input for {tool_id}: {len(tool_input_buffer[tool_id])} chars")
                                debug_log(f"   Buffer content: {tool_input_buffer[tool_id][:200]}...")
                                
                                # Send tool_input_delta to frontend for live preview
                                queue.put_nowait({
                                    "type": "tool_input_delta",
                                    "tool_use_id": tool_id,
                                    "text": delta_text
                                })
                                
                                # Update current_tool_use input in real-time for UI
                                try:
                                    # Try to parse accumulated JSON
                                    accumulated = tool_input_buffer[tool_id]
                                    if accumulated:
                                        parsed = json.loads(accumulated)
                                        current_tool_use["input"] = parsed
                                        debug_log(f"✓ Parsed input for {tool_id}: {parsed}")
                                except json.JSONDecodeError:
                                    # Not complete JSON yet, that's okay - will parse on stop
                                    debug_log(f"   JSON incomplete, waiting for more chunks...")
                                    pass
                                except Exception as e:
                                    debug_log(f"⚠ Error parsing input: {e}")
                            else:
                                debug_log(f"⚠ WARNING: tool_input_delta has no text content!")
                        elif payload.get("type") in ["tool_use_stop", "content_block_stop"]:
                            # content_block_stop signals end of current block
                            # If we have an active tool_use, finalize it
                            if current_tool_use:
                                tool_id = current_tool_use.get("id")
                                tool_name = current_tool_use.get("name", "unknown")
                                
                                # Parse accumulated input if we have it
                                if tool_id and tool_id in tool_input_buffer and tool_input_buffer[tool_id]:
                                    try:
                                        # The buffer contains the complete JSON
                                        accumulated_input = tool_input_buffer[tool_id].strip()
                                        if accumulated_input:
                                            parsed_input = json.loads(accumulated_input)
                                            current_tool_use["input"] = parsed_input
                                            debug_log(f"✓ Tool {tool_name} input parsed from buffer: {parsed_input}")
                                        else:
                                            debug_log(f"⚠ Tool {tool_name} buffer is empty!")
                                    except json.JSONDecodeError as e:
                                        # If parsing fails, log and use what we have from start event
                                        debug_log(f"⚠ Could not parse tool input JSON for {tool_name}: {accumulated_input[:100]}... Error: {e}")
                                        debug_log(f"  Full accumulated input: {accumulated_input}")
                                        debug_log(f"  Using input from start event: {current_tool_use.get('input', {})}")
                                else:
                                    # No accumulated input, use what we got from start event
                                    existing_input = current_tool_use.get('input', {})
                                    debug_log(f"ℹ Tool {tool_name} input from start event: {existing_input}")
                                    if not existing_input or existing_input == {}:
                                        debug_log(f"   ⚠ WARNING: Tool {tool_name} has empty input and no input_json_delta events were received!")
                                        debug_log(f"   This might indicate a problem with tool input streaming.")
                                
                                # Validate input before adding
                                final_input = current_tool_use.get("input", {})
                                if not final_input or final_input == {}:
                                    debug_log(f"⚠ CRITICAL: Tool {tool_name} will be executed with empty input!")
                                
                                # Only add tool call if it has a name
                                if current_tool_use.get("name"):
                                    # Make a deep copy to preserve the input
                                    import copy
                                    tool_call_copy = copy.deepcopy({
                                        "id": current_tool_use.get("id"),
                                        "name": current_tool_use.get("name"),
                                        "input": final_input
                                    })
                                    current_tool_calls.append(tool_call_copy)
                                    debug_log(f"✓ Added tool call: {tool_call_copy['name']} with input: {tool_call_copy.get('input', {})}")
                                else:
                                    debug_log(f"⚠ Skipping tool call without name: {current_tool_use}")
                                
                                if tool_id and tool_id in tool_input_buffer:
                                    del tool_input_buffer[tool_id]
                                current_tool_use = None
                            queue.put_nowait(payload)
                        elif payload.get("type") == "tool_input_delta":
                            # Already handled above - accumulate and send to frontend
                            # Don't queue again here, it's already queued in the handler above
                            pass
                        elif payload.get("type") == "delta" and payload.get("text"):
                            text = payload.get("text", "")
                            current_text.append(text)
                            full_response.append(text)
                            queue.put_nowait(payload)
                        else:
                            queue.put_nowait(payload)
                    
                    # After stream completes, check if we need to get the final message
                    # to extract complete tool calls (they might not be fully captured in stream)
                    debug_log(f"📊 Stream completed. Tool calls collected: {len(current_tool_calls)}, Text chunks: {len(current_text)}")
                    debug_log(f"   Tool input buffers: {list(tool_input_buffer.keys())}")
                    
                    # Check for incomplete tool calls (stream ended before content_block_stop)
                    # This happens with large tool inputs like write_file with big content
                    incomplete_tool_call = False
                    
                    if current_tool_use and not current_tool_calls:
                        debug_log(f"⚠ Stream ended with incomplete tool call: {current_tool_use.get('name')}")
                        debug_log(f"   Buffer has {len(tool_input_buffer.get(current_tool_use.get('id'), ''))} chars")
                        debug_log("   This typically happens with large file writes (CSS, etc.)")
                        debug_log("   Falling back to non-streaming API to get complete tool input...")
                        incomplete_tool_call = True
                    
                    # Also check if we have pending buffers but no tool calls
                    # This means the stream ended mid-tool-call
                    if tool_input_buffer and not current_tool_calls:
                        debug_log(f"⚠ Stream ended with pending tool input buffers: {list(tool_input_buffer.keys())}")
                        for buf_id, buf_content in tool_input_buffer.items():
                            debug_log(f"   Buffer {buf_id}: {len(buf_content)} chars")
                            debug_log(f"   Content preview: {buf_content[:200]}...")
                        debug_log("   Falling back to non-streaming API...")
                        incomplete_tool_call = True
                    
                    # Force fallback if we detected incomplete tool call
                    if incomplete_tool_call:
                        current_text = []  # Clear text to trigger fallback
                    
                    # If we have tool calls, execute them and continue
                    if current_tool_calls:
                        debug_log(f"✓ Executing {len(current_tool_calls)} tool call(s)")
                        for tc in current_tool_calls:
                            tool_input = tc.get('input', {})
                            debug_log(f"   - {tc.get('name')}: {tool_input}")
                            # Validate that input is not empty (unless tool doesn't require input)
                            if not tool_input or tool_input == {}:
                                debug_log(f"   ⚠ WARNING: Tool {tc.get('name')} has empty input!")
                        messages = handle_tool_calls(messages, current_tool_calls)
                        tool_iteration += 1
                        continue
                    elif not current_text or incomplete_tool_call:
                        # No tool calls and no text - OR we detected incomplete tool call
                        # Use non-streaming API which handles large payloads better
                        debug_log("🔄 Using non-streaming API to get complete response...")
                        debug_log(f"   Reason: {'incomplete tool call' if incomplete_tool_call else 'no content from stream'}")
                        
                        try:
                            import concurrent.futures
                            
                            # Use a longer timeout for large file operations
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                debug_log("   Calling invoke_bedrock_model with max_tokens=32768...")
                                future = executor.submit(
                                    lambda: asyncio.run(invoke_bedrock_model(
                                        model_id=model_id,
                                        system_prompt=system_prompt,
                                        messages=messages,
                                        max_tokens=32768,  # Maximum for large file writes
                                        tools=tools
                                    ))
                                )
                                response = future.result(timeout=180)  # 3 minute timeout for large files
                            
                            debug_log(f"   Non-streaming API returned successfully")
                            
                            # Extract tool calls and text
                            content = response.get("content", [])
                            tool_calls = []
                            text_parts = []
                            
                            for block in content:
                                if block.get("type") == "tool_use":
                                    tool_calls.append({
                                        "id": block.get("id"),
                                        "name": block.get("name"),
                                        "input": block.get("input", {})
                                    })
                                elif block.get("type") == "text":
                                    text_parts.append(block.get("text", ""))
                            
                            if tool_calls:
                                debug_log(f"✓ Found {len(tool_calls)} tool call(s) in final message")
                                for tc in tool_calls:
                                    debug_log(f"   - {tc.get('name')}: {tc.get('input', {})}")
                                messages = handle_tool_calls(messages, tool_calls)
                                tool_iteration += 1
                                continue
                            elif text_parts:
                                final_text = "".join(text_parts)
                                full_response.append(final_text)
                                chunk_size = 50
                                for i in range(0, len(final_text), chunk_size):
                                    chunk = final_text[i:i+chunk_size]
                                    queue.put_nowait({"type": "delta", "text": chunk})
                                break
                        except Exception as e:
                            debug_log(f"⚠ Error fetching final message: {e}")
                            import traceback
                            debug_log(traceback.format_exc())
                    else:
                        # No tool calls collected from stream
                        # Check if we got any text - if so, we're done
                        if current_text:
                            # We got text response, no tools
                            full_response.extend(current_text)
                            break
                        else:
                            # No tool calls and no text - might be an issue
                            # Try using non-streaming API to get complete response
                            debug_log("⚠ No tool calls or text from stream, trying non-streaming API...")
                            try:
                                import concurrent.futures
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(
                                        lambda: asyncio.run(invoke_bedrock_model(
                                            model_id=model_id,
                                            system_prompt=system_prompt,
                                            messages=messages,
                                            max_tokens=16384,
                                            tools=tools
                                        ))
                                    )
                                    response = future.result()
                                
                                # Extract tool calls and text
                                content = response.get("content", [])
                                tool_calls = []
                                text_parts = []
                                
                                for block in content:
                                    if block.get("type") == "tool_use":
                                        tool_calls.append({
                                            "id": block.get("id"),
                                            "name": block.get("name"),
                                            "input": block.get("input", {})
                                        })
                                    elif block.get("type") == "text":
                                        text_parts.append(block.get("text", ""))
                                
                                if tool_calls:
                                    debug_log(f"✓ Found {len(tool_calls)} tool call(s) via non-streaming API")
                                    for tc in tool_calls:
                                        debug_log(f"   - {tc.get('name')}: {tc.get('input', {})}")
                                    messages = handle_tool_calls(messages, tool_calls)
                                    tool_iteration += 1
                                    continue
                                elif text_parts:
                                    final_text = "".join(text_parts)
                                    full_response.append(final_text)
                                    chunk_size = 50
                                    for i in range(0, len(final_text), chunk_size):
                                        chunk = final_text[i:i+chunk_size]
                                        queue.put_nowait({"type": "delta", "text": chunk})
                                    break
                            except Exception as e:
                                print(f"⚠ Error in fallback non-streaming API: {e}")
                                break
                    
        except Exception as exc:
            queue.put_nowait({"type": "error", "message": str(exc)})
        finally:
            # Save conversation to memory after streaming completes
            if full_response:
                ai_response = "".join(full_response)
                try:
                    memory_manager.save_conversation(
                        project_path=project_path,
                        session_id=session_id,
                        user_message=request.message,
                        assistant_response=ai_response,
                        metadata=context
                    )
                except Exception as mem_error:
                    # Don't fail if memory save fails
                    print(f"Warning: Failed to save to memory: {mem_error}")
            
            queue.put_nowait({"__done": True})

    threading.Thread(target=producer, daemon=True).start()

    async def event_generator():
        yield format_sse_payload({"type": "status", "message": "Connecting to Bedrock…"})
        while True:
            payload = await queue.get()
            if payload.get("__done"):
                yield format_sse_payload({"type": "done"})
                break
            yield format_sse_payload(payload)

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)


# Whisper model configuration
WHISPER_MODELS = [
    {"id": "tiny", "name": "Tiny (~39 MB)", "size": "~39 MB", "description": "Fastest, least accurate"},
    {"id": "base", "name": "Base (~74 MB)", "size": "~74 MB", "description": "Good balance"},
    {"id": "small", "name": "Small (~244 MB)", "size": "~244 MB", "description": "Better accuracy"},
    {"id": "medium", "name": "Medium (~769 MB)", "size": "~769 MB", "description": "Good accuracy"},
    {"id": "large-v2", "name": "Large v2 (~1550 MB)", "size": "~1550 MB", "description": "Best accuracy"},
    {"id": "large-v3", "name": "Large v3 (~1550 MB)", "size": "~1550 MB", "description": "Latest, best accuracy"},
]

whisper_model_cache = {}
whisper_model_lock = threading.Lock()


class WhisperModelInfo(BaseModel):
    id: str
    name: str
    size: str
    description: str
    downloaded: bool = False


class WhisperModelsResponse(BaseModel):
    models: List[WhisperModelInfo]
    current_model: Optional[str] = None
    success: bool = True


class WhisperDownloadRequest(BaseModel):
    model_id: str


class WhisperDownloadResponse(BaseModel):
    model_id: str
    success: bool = True
    message: str


class WhisperTranscribeRequest(BaseModel):
    model_id: Optional[str] = None


class WhisperTranscribeResponse(BaseModel):
    text: str
    language: Optional[str] = None
    success: bool = True


def check_whisper_model_downloaded(model_id: str) -> bool:
    """Check if a Whisper model is already downloaded."""
    try:
        # Whisper stores models in ~/.cache/whisper/
        model_path = os.path.join(os.path.expanduser("~"), ".cache", "whisper", f"{model_id}.pt")
        return os.path.exists(model_path)
    except Exception:
        return False


def get_whisper_model(model_id: str):
    """Get or load a Whisper model."""
    with whisper_model_lock:
        if model_id in whisper_model_cache:
            return whisper_model_cache[model_id]
        
        try:
            import whisper
            print(f"Loading Whisper model: {model_id}")
            model = whisper.load_model(model_id)
            whisper_model_cache[model_id] = model
            print(f"Whisper model {model_id} loaded successfully")
            return model
        except Exception as e:
            print(f"Error loading Whisper model {model_id}: {e}")
            raise Exception(f"Failed to load Whisper model: {str(e)}")


@app.get("/api/whisper/models", response_model=WhisperModelsResponse)
async def get_whisper_models():
    """Get list of available Whisper models and their download status."""
    try:
        models = []
        current_model = os.getenv('WHISPER_MODEL', 'base')
        
        for model in WHISPER_MODELS:
            downloaded = check_whisper_model_downloaded(model['id'])
            models.append(WhisperModelInfo(
                id=model['id'],
                name=model['name'],
                size=model['size'],
                description=model['description'],
                downloaded=downloaded
            ))
        
        return WhisperModelsResponse(
            models=models,
            current_model=current_model,
            success=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Whisper models: {str(e)}")


@app.post("/api/whisper/download")
async def download_whisper_model_stream(request: WhisperDownloadRequest):
    """Download a Whisper model with progress streaming."""
    try:
        # Validate model ID
        model_ids = [m['id'] for m in WHISPER_MODELS]
        if request.model_id not in model_ids:
            raise HTTPException(status_code=400, detail=f"Invalid model ID. Must be one of: {', '.join(model_ids)}")
        
        # Check if already downloaded
        if check_whisper_model_downloaded(request.model_id):
            async def already_downloaded():
                yield format_sse_payload({"type": "complete", "message": f"Model {request.model_id} is already downloaded", "progress": 100})
            return StreamingResponse(already_downloaded(), media_type="text/event-stream")
        
        async def progress_generator():
            loop = asyncio.get_running_loop()
            progress_queue = asyncio.Queue()
            
            def download_with_progress():
                try:
                    import whisper
                    import sys
                    
                    # Send initial status
                    loop.call_soon_threadsafe(
                        progress_queue.put_nowait,
                        {"type": "status", "message": f"Starting download of {request.model_id}...", "progress": 0}
                    )
                    
                    # Capture stdout to monitor tqdm progress
                    class ProgressCapture:
                        def __init__(self, queue, loop):
                            self.queue = queue
                            self.loop = loop
                            self.last_percent = 0
                            self.buffer = ""
                            
                        def write(self, text):
                            self.buffer += text
                            # Look for percentage indicators from tqdm
                            if '%' in text:
                                try:
                                    # Extract percentage from tqdm output
                                    parts = text.split('%')
                                    if len(parts) > 0:
                                        percent_part = parts[0].strip().split()[-1]
                                        percent = float(percent_part)
                                        if abs(percent - self.last_percent) >= 1:  # Update every 1%
                                            self.last_percent = percent
                                            self.loop.call_soon_threadsafe(
                                                self.queue.put_nowait,
                                                {"type": "progress", "progress": int(percent), "message": f"Downloading... {int(percent)}%"}
                                            )
                                except (ValueError, IndexError):
                                    pass
                            # Still write to actual stdout
                            sys.__stdout__.write(text)
                            
                        def flush(self):
                            sys.__stdout__.flush()
                    
                    # Redirect stdout
                    old_stdout = sys.stdout
                    sys.stdout = ProgressCapture(progress_queue, loop)
                    
                    try:
                        whisper.load_model(request.model_id)
                        
                        loop.call_soon_threadsafe(
                            progress_queue.put_nowait,
                            {"type": "complete", "progress": 100, "message": f"Model {request.model_id} downloaded successfully!"}
                        )
                    finally:
                        sys.stdout = old_stdout
                        loop.call_soon_threadsafe(progress_queue.put_nowait, {"type": "done"})
                        
                except Exception as e:
                    loop.call_soon_threadsafe(
                        progress_queue.put_nowait,
                        {"type": "error", "message": str(e)}
                    )
            
            # Start download in background thread
            threading.Thread(target=download_with_progress, daemon=True).start()
            
            # Stream progress updates
            while True:
                try:
                    update = await asyncio.wait_for(progress_queue.get(), timeout=60)
                    
                    if update.get("type") == "done":
                        # Update environment variable
                        os.environ['WHISPER_MODEL'] = request.model_id
                        break
                    elif update.get("type") == "error":
                        yield format_sse_payload({"type": "error", "message": update.get("message", "Unknown error")})
                        break
                    else:
                        yield format_sse_payload(update)
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield format_sse_payload({"type": "status", "message": "Download in progress..."})
        
        return StreamingResponse(
            progress_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download model: {str(e)}")


@app.delete("/api/whisper/models/{model_id}")
async def delete_whisper_model(model_id: str):
    """Delete a Whisper model from disk."""
    try:
        # Validate model ID
        model_ids = [m['id'] for m in WHISPER_MODELS]
        if model_id not in model_ids:
            raise HTTPException(status_code=400, detail=f"Invalid model ID. Must be one of: {', '.join(model_ids)}")
        
        # Check if model is downloaded
        if not check_whisper_model_downloaded(model_id):
            raise HTTPException(status_code=404, detail=f"Model {model_id} is not downloaded")
        
        # Get model path
        model_path = os.path.join(os.path.expanduser("~"), ".cache", "whisper", f"{model_id}.pt")
        
        # Remove from cache if loaded
        with whisper_model_lock:
            if model_id in whisper_model_cache:
                del whisper_model_cache[model_id]
        
        # Delete the file
        try:
            os.remove(model_path)
            print(f"Deleted Whisper model: {model_id} from {model_path}")
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete model file: {str(e)}")
        
        return {"success": True, "message": f"Model {model_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")


@app.post("/api/whisper/transcribe", response_model=WhisperTranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    model_id: Optional[str] = Form(None)
):
    """Transcribe audio file using Whisper."""
    try:
        # Use default model if not specified
        if not model_id:
            model_id = os.getenv('WHISPER_MODEL', 'base')
        
        print(f"[Transcribe] Received audio file: {file.filename}, content_type: {file.content_type}")
        print(f"[Transcribe] Using model: {model_id}")
        
        # Validate model ID
        model_ids = [m['id'] for m in WHISPER_MODELS]
        if model_id not in model_ids:
            raise HTTPException(status_code=400, detail=f"Invalid model ID. Must be one of: {', '.join(model_ids)}")
        
        # Get file extension from filename
        file_ext = os.path.splitext(file.filename or 'audio.wav')[1] or '.wav'
        print(f"[Transcribe] File extension: {file_ext}")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content_bytes = await file.read()
            tmp_file.write(content_bytes)
            tmp_path = tmp_file.name
            file_size = len(content_bytes)
        
        print(f"[Transcribe] Saved to: {tmp_path}, size: {file_size} bytes")
        
        # Minimum size check: require at least 5KB for transcription
        if file_size < 5000:  # Less than 5KB
            raise HTTPException(
                status_code=400, 
                detail=f"Audio file too small ({file_size} bytes). Minimum size: 5KB. Please record longer audio."
            )
        
        try:
            def transcribe():
                model = get_whisper_model(model_id)
                print(f"[Transcribe] Starting transcription...")
                result = model.transcribe(tmp_path, fp16=False)  # Disable fp16 for compatibility
                print(f"[Transcribe] Transcription result: {result}")
                return result
            
            # Run transcription in thread pool
            result = await asyncio.to_thread(transcribe)
            
            transcribed_text = result.get('text', '').strip()
            detected_language = result.get('language')
            
            print(f"[Transcribe] Text: '{transcribed_text}', Language: {detected_language}")
            
            if not transcribed_text:
                print("[Transcribe] WARNING: Empty transcription result")
                raise Exception("No speech detected in audio. Please try speaking louder or closer to the microphone.")
            
            return WhisperTranscribeResponse(
                text=transcribed_text,
                language=detected_language,
                success=True
            )
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
                print(f"[Transcribe] Cleaned up temp file")
            except Exception as e:
                print(f"[Transcribe] Failed to clean up temp file: {e}")
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Transcribe] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
# Memory API endpoints
class MemoryItem(BaseModel):
    id: int
    memory_type: str
    title: Optional[str] = None
    content: str
    importance: float
    usage_count: int
    created_at: str
    updated_at: Optional[str] = None

class ConversationItem(BaseModel):
    id: int
    role: str
    content: str
    message_index: int
    created_at: str

class TaskSummaryItem(BaseModel):
    id: int
    task_goal: str
    summary: str
    success: bool
    created_at: str

class MemoryListResponse(BaseModel):
    memories: List[MemoryItem]
    total: int
    success: bool = True

class ConversationListResponse(BaseModel):
    conversations: List[ConversationItem]
    total: int
    success: bool = True

class TaskSummaryListResponse(BaseModel):
    summaries: List[TaskSummaryItem]
    total: int
    success: bool = True

@app.get("/api/memory/list", response_model=MemoryListResponse)
async def list_memories(
    project_path: Optional[str] = Query(None),
    memory_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List memories with optional filtering."""
    try:
        conn = sqlite3.connect(memory_manager.db.db_path)
        conn.row_factory = sqlite3.Row
        
        conditions = []
        params = []
        
        if project_path:
            conditions.append("(project_path = ? OR project_path IS NULL)")
            params.append(project_path)
        
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM memories{where_clause}"
        total = conn.execute(count_query, params).fetchone()["total"]
        
        # Get memories
        query = f"""
            SELECT * FROM memories
            {where_clause}
            ORDER BY importance DESC, usage_count DESC, created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        
        conn.close()
        
        memories = [
            MemoryItem(
                id=row["id"],
                memory_type=row["memory_type"],
                title=row["title"] if "title" in row.keys() else None,
                content=row["content"],
                importance=row["importance"],
                usage_count=row["usage_count"],
                created_at=row["created_at"],
                updated_at=row["updated_at"] if "updated_at" in row.keys() else None
            )
            for row in rows
        ]
        
        return MemoryListResponse(memories=memories, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/search")
async def search_memories(
    query: str = Query(..., min_length=1),
    project_path: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50)
):
    """Search memories by content."""
    try:
        memories = memory_manager.db.search_memories(
            project_path=project_path,
            query=query,
            limit=limit
        )
        
        result = [
            {
                "id": m["id"],
                "memory_type": m["memory_type"],
                "title": m.get("title"),
                "content": m["content"],
                "importance": m["importance"],
                "usage_count": m["usage_count"],
                "created_at": m["created_at"]
            }
            for m in memories
        ]
        
        return {"memories": result, "total": len(result), "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/memory/{memory_id}")
async def delete_memory(memory_id: int):
    """Delete a memory."""
    try:
        conn = sqlite3.connect(memory_manager.db.db_path)
        conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()
        conn.close()
        
        # Also delete from vector store if enabled
        if memory_manager.vector_store.is_enabled():
            memory_manager.vector_store.delete_memory(str(memory_id))
        
        return {"success": True, "message": "Memory deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/conversations", response_model=ConversationListResponse)
async def list_conversations(
    project_path: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List conversation messages."""
    try:
        conn = sqlite3.connect(memory_manager.db.db_path)
        conn.row_factory = sqlite3.Row
        
        conditions = []
        params = []
        
        if project_path:
            conditions.append("(project_path = ? OR project_path IS NULL)")
            params.append(project_path)
        
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM conversations{where_clause}"
        total = conn.execute(count_query, params).fetchone()["total"]
        
        # Get conversations
        query = f"""
            SELECT * FROM conversations
            {where_clause}
            ORDER BY created_at DESC, message_index DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        
        conn.close()
        
        conversations = [
            ConversationItem(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                message_index=row["message_index"],
                created_at=row["created_at"]
            )
            for row in rows
        ]
        
        return ConversationListResponse(conversations=conversations, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/task-summaries", response_model=TaskSummaryListResponse)
async def list_task_summaries(
    project_path: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List task summaries."""
    try:
        conn = sqlite3.connect(memory_manager.db.db_path)
        conn.row_factory = sqlite3.Row
        
        conditions = []
        params = []
        
        if project_path:
            conditions.append("(project_path = ? OR project_path IS NULL)")
            params.append(project_path)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM task_summaries{where_clause}"
        total = conn.execute(count_query, params).fetchone()["total"]
        
        # Get summaries
        query = f"""
            SELECT * FROM task_summaries
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        
        conn.close()
        
        summaries = [
            TaskSummaryItem(
                id=row["id"],
                task_goal=row["task_goal"],
                summary=row["summary"],
                success=bool(row["success"]),
                created_at=row["created_at"]
            )
            for row in rows
        ]
        
        return TaskSummaryListResponse(summaries=summaries, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/stats")
async def get_memory_stats(project_path: Optional[str] = Query(None)):
    """Get memory statistics."""
    try:
        conn = sqlite3.connect(memory_manager.db.db_path)
        conn.row_factory = sqlite3.Row
        
        conditions = []
        params = []
        if project_path:
            conditions.append("(project_path = ? OR project_path IS NULL)")
            params.append(project_path)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Count memories by type
        memory_types = conn.execute(f"""
            SELECT memory_type, COUNT(*) as count
            FROM memories
            {where_clause}
            GROUP BY memory_type
        """, params).fetchall()
        
        # Count conversations
        conv_count = conn.execute(f"""
            SELECT COUNT(*) as total FROM conversations{where_clause}
        """, params).fetchone()["total"]
        
        # Count task summaries
        task_count = conn.execute(f"""
            SELECT COUNT(*) as total FROM task_summaries{where_clause}
        """, params).fetchone()["total"]
        
        conn.close()
        
        return {
            "success": True,
            "stats": {
                "total_memories": sum(m["count"] for m in memory_types),
                "memory_types": {m["memory_type"]: m["count"] for m in memory_types},
                "total_conversations": conv_count,
                "total_task_summaries": task_count,
                "vector_store_enabled": memory_manager.vector_store.is_enabled()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

