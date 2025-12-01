"""
Intelligent Router - Uses AI to semantically understand intent and route tasks.

This replaces static keyword matching with dynamic AI-powered decision making.
The router uses an LLM to understand the semantic intent of requests and 
intelligently route them to appropriate agents or workflows.
"""

import logging
import json
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger("mercury.agents.orchestration.intelligent_router")


class RouteDecision(Enum):
    """Routing decision types."""
    CONVERSATIONAL = "conversational"  # Simple response, no tools
    RESEARCHER_ONLY = "researcher_only"  # Research/explore only
    CODER_DIRECT = "coder_direct"  # Direct to coder (create/modify files)
    ANALYZER_DIRECT = "analyzer_direct"  # Direct to analyzer
    FULL_WORKFLOW = "full_workflow"  # Full explore→plan→execute→validate
    

class IntentType(Enum):
    """Intent classification."""
    GREETING = "greeting"
    QUESTION = "question"
    EXPLORATION = "exploration"  # Understand/explore codebase
    CREATION = "creation"  # Create new files/code
    MODIFICATION = "modification"  # Modify existing files
    VALIDATION = "validation"  # Check/test/validate code
    REFACTORING = "refactoring"  # Large-scale code changes
    

class IntelligentRouter:
    """
    AI-powered semantic router that understands intent and routes intelligently.
    
    This replaces static keyword matching with dynamic LLM-based decision making.
    """
    
    def __init__(
        self,
        invoke_bedrock_model,
        model_id: str,
        researcher=None,
        coder=None,
        analyzer=None,
        status_emitter=None
    ):
        """
        Initialize intelligent router.
        
        Args:
            invoke_bedrock_model: Function to invoke Bedrock model
            model_id: Model ID for LLM calls
            researcher: ResearcherAgent instance
            coder: CoderAgent instance
            analyzer: AnalyzerAgent instance
            status_emitter: StatusEmitter instance
        """
        self.invoke_bedrock_model = invoke_bedrock_model
        self.model_id = model_id
        self.researcher = researcher
        self.coder = coder
        self.analyzer = analyzer
        self.status_emitter = status_emitter
        
        # Cache routing decisions for similar requests
        self._routing_cache: Dict[str, Tuple[RouteDecision, IntentType]] = {}
    
    async def analyze_intent(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[RouteDecision, IntentType, Dict[str, Any]]:
        """
        Use AI to analyze the semantic intent of a request.
        
        Args:
            user_request: User's request text
            context: Optional context (project state, conversation history, etc.)
            
        Returns:
            Tuple of (RouteDecision, IntentType, reasoning_dict)
        """
        # Check cache first (for exact matches)
        cache_key = f"{user_request.strip().lower()}:{context.get('is_empty_directory') if context else False}"
        if cache_key in self._routing_cache:
            logger.info(f"[INTELLIGENT_ROUTER] Using cached routing decision for: {user_request[:50]}")
            decision, intent = self._routing_cache[cache_key]
            return decision, intent, {"cached": True}
        
        # Build context information for the AI
        context_info = ""
        if context:
            if context.get("is_empty_directory") or context.get("is_new_project"):
                context_info += "\n- This is an empty/new project directory"
            if context.get("conversation_history"):
                recent = context.get("recent_messages", [])[-2:] if context.get("recent_messages") else []
                if recent:
                    context_info += f"\n- Recent conversation: {json.dumps(recent[-1]) if recent else 'None'}"
        
        # System prompt for intent analysis
        system_prompt = """You are an intelligent task routing system. Your job is to analyze user requests and determine:
1. The semantic INTENT (what does the user actually want to do?)
2. The best ROUTING decision (which agent or workflow should handle this?)

**Intent Types:**
- GREETING: Simple greetings, acknowledgments (hi, hello, thanks, ok)
- QUESTION: Questions about code, explanations (what, how, why, explain)
- EXPLORATION: Understanding/exploring codebase (show me, find, search, read)
- CREATION: Creating NEW files/code (create, make, build, write, add NEW, do [something new])
- MODIFICATION: Modifying EXISTING files (edit, change, update, modify, refactor)
- VALIDATION: Testing/checking code (test, validate, check, lint, analyze)
- REFACTORING: Large-scale code reorganization

**Routing Decisions:**
- CONVERSATIONAL: Simple response, no tools needed (greetings, simple acknowledgments)
- RESEARCHER_ONLY: Research/exploration only, no code changes (ONLY for "show me", "find", "read", "search")
- CODER_DIRECT: Route directly to coder agent (for ALL creation/modification tasks - the coder writes files immediately)
- ANALYZER_DIRECT: Route to analyzer (for validation/testing)
- FULL_WORKFLOW: Complex multi-step work needing full explore→plan→execute→validate

**CRITICAL ROUTING RULES (MUST FOLLOW):**

FILE CREATION = ALWAYS CODER_DIRECT (NOT RESEARCHER_ONLY!)
- "do a [anything]" = CREATION → CODER_DIRECT (e.g., "do a landing page", "do a script")
- "create [anything]" = CREATION → CODER_DIRECT (e.g., "create landing page", "create file")
- "make [anything]" = CREATION → CODER_DIRECT (e.g., "make website", "make form")
- "write [anything]" = CREATION → CODER_DIRECT (e.g., "write html", "write script")
- "build [anything]" = CREATION → CODER_DIRECT (e.g., "build page", "build component")
- "add [file/code]" = CREATION → CODER_DIRECT (e.g., "add button", "add form")

EXPLORATION = ONLY RESEARCHER_ONLY
- "show me [code]" = EXPLORATION → RESEARCHER_ONLY (NOT creation!)
- "find [pattern]" = EXPLORATION → RESEARCHER_ONLY
- "read [file]" = EXPLORATION → RESEARCHER_ONLY
- "search [codebase]" = EXPLORATION → RESEARCHER_ONLY

**EXAMPLES OF CORRECT ROUTING:**
✅ "do a landing page" → CREATION intent → CODER_DIRECT
✅ "create html file" → CREATION intent → CODER_DIRECT
✅ "make a website" → CREATION intent → CODER_DIRECT
✅ "write landing page" → CREATION intent → CODER_DIRECT
✅ "show me the config" → EXPLORATION intent → RESEARCHER_ONLY
✅ "hi" → GREETING intent → CONVERSATIONAL

**WRONG ROUTING (DO NOT DO THIS):**
❌ "do a landing page" → EXPLORATION → RESEARCHER_ONLY (WRONG! This is CREATION → CODER_DIRECT)
❌ "create file" → EXPLORATION → RESEARCHER_ONLY (WRONG! This is CREATION → CODER_DIRECT)

RESPOND ONLY WITH JSON in this exact format:
{
  "intent": "CREATION|GREETING|QUESTION|EXPLORATION|MODIFICATION|VALIDATION|REFACTORING",
  "routing": "CONVERSATIONAL|RESEARCHER_ONLY|CODER_DIRECT|ANALYZER_DIRECT|FULL_WORKFLOW",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why this routing makes sense"
}"""

        user_message = f"""Analyze this request and determine intent + routing:

Request: "{user_request}"

Context:{context_info if context_info else " None"}

Respond with JSON only."""

        try:
            # Call LLM for semantic analysis
            response = await self.invoke_bedrock_model(
                model_id=self.model_id,
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                max_tokens=512,
                tools=None,
                enable_thinking=False
            )
            
            # Extract response
            text_parts = []
            content = response.get("content", [])
            for block in content:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            
            response_text = "".join(text_parts)
            
            # Parse JSON response
            # Find JSON in response (might have markdown code blocks)
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                analysis = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
            
            # Extract decisions
            intent_str = analysis.get("intent", "QUESTION").upper()
            routing_str = analysis.get("routing", "RESEARCHER_ONLY").upper()
            confidence = analysis.get("confidence", 0.8)
            reasoning = analysis.get("reasoning", "AI routing decision")
            
            # Convert to enums
            try:
                intent = IntentType[intent_str]
            except KeyError:
                logger.warning(f"Unknown intent: {intent_str}, defaulting to QUESTION")
                intent = IntentType.QUESTION
            
            try:
                routing = RouteDecision[routing_str]
            except KeyError:
                logger.warning(f"Unknown routing: {routing_str}, defaulting to RESEARCHER_ONLY")
                routing = RouteDecision.RESEARCHER_ONLY
            
            logger.info(f"[INTELLIGENT_ROUTER] Intent: {intent.value}, Routing: {routing.value}, Confidence: {confidence}")
            logger.info(f"[INTELLIGENT_ROUTER] Reasoning: {reasoning}")
            
            # Cache the decision
            self._routing_cache[cache_key] = (routing, intent)
            
            return routing, intent, {
                "confidence": confidence,
                "reasoning": reasoning,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"[INTELLIGENT_ROUTER] AI analysis failed: {e}, falling back to heuristics")
            # Fallback to simple heuristics
            return self._fallback_routing(user_request, context)
    
    def _fallback_routing(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[RouteDecision, IntentType, Dict[str, Any]]:
        """Fallback routing using simple heuristics if AI fails."""
        request_lower = user_request.lower().strip()
        words = request_lower.split()
        
        # Simple conversational
        greetings = ["hi", "hello", "hey", "thanks", "thank you", "ok", "okay"]
        if any(word == request_lower for word in greetings):
            return RouteDecision.CONVERSATIONAL, IntentType.GREETING, {"fallback": True}
        
        # AGGRESSIVE creation detection - catch all "create/make/do/build/write/add" patterns
        # This is the PRIMARY routing logic - be aggressive about catching creation tasks
        creation_verbs = ["create", "make", "build", "write", "add", "implement", "develop"]
        do_patterns = ["do a ", "do an ", "do "]  # "do a landing page", "do landing page", etc.
        file_indicators = [
            "file", "files", "page", "landing page", "website", "site", "web",
            "html", "css", "javascript", "js", "script", "component", "form",
            "button", "nav", "navigation", "header", "footer", "section",
            ".html", ".css", ".js", ".jsx", ".tsx", ".vue", ".py", ".java"
        ]
        
        # Check for "do a/an/[space]" patterns first (highest priority)
        has_do_pattern = any(pattern in request_lower for pattern in do_patterns)
        
        # Check for creation verbs in first 3 words
        has_creation_verb = any(verb in words[:3] for verb in creation_verbs)
        
        # Check for file/web indicators anywhere
        has_file_indicator = any(indicator in request_lower for indicator in file_indicators)
        
        # ROUTE TO CODER if:
        # 1. Has "do a/an" pattern (e.g., "do a landing page") - HIGHEST PRIORITY
        # 2. Has creation verb + file indicator (e.g., "create a website", "make html file")
        # 3. Has creation verb in short request (<= 6 words) - assume it's file creation
        if has_do_pattern:
            logger.info(f"[FALLBACK_ROUTER] 'do a/an' pattern detected → CODER_DIRECT")
            return RouteDecision.CODER_DIRECT, IntentType.CREATION, {"fallback": True, "reason": "do_pattern"}
        
        if has_creation_verb and has_file_indicator:
            logger.info(f"[FALLBACK_ROUTER] Creation verb + file indicator → CODER_DIRECT")
            return RouteDecision.CODER_DIRECT, IntentType.CREATION, {"fallback": True, "reason": "creation_with_file"}
        
        if has_creation_verb and len(words) <= 6:
            logger.info(f"[FALLBACK_ROUTER] Short creation request → CODER_DIRECT")
            return RouteDecision.CODER_DIRECT, IntentType.CREATION, {"fallback": True, "reason": "short_creation"}
        
        # Exploration keywords ONLY if no creation verbs
        explore_keywords = ["show", "read", "find", "search", "explore", "list", "display", "what", "where", "how"]
        if any(kw in request_lower for kw in explore_keywords) and not has_creation_verb:
            return RouteDecision.RESEARCHER_ONLY, IntentType.EXPLORATION, {"fallback": True}
        
        # Default: If we have any creation verb at all, route to coder (aggressive)
        if has_creation_verb:
            logger.info(f"[FALLBACK_ROUTER] Creation verb detected, defaulting to CODER_DIRECT")
            return RouteDecision.CODER_DIRECT, IntentType.CREATION, {"fallback": True, "reason": "default_creation"}
        
        # Final fallback to researcher
        return RouteDecision.RESEARCHER_ONLY, IntentType.QUESTION, {"fallback": True}
    
    async def route_task(
        self,
        user_request: str,
        project_path: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route a task intelligently based on AI analysis.
        
        Args:
            user_request: User's request
            project_path: Project path
            session_id: Session ID
            context: Additional context
            
        Returns:
            Task execution result
        """
        # Analyze intent using AI
        routing_decision, intent, reasoning = await self.analyze_intent(user_request, context)
        
        logger.info(f"[INTELLIGENT_ROUTER] Routing '{user_request[:50]}...' as {routing_decision.value} (intent: {intent.value})")
        
        # Route based on AI decision
        if routing_decision == RouteDecision.CONVERSATIONAL:
            return await self._handle_conversational(user_request, reasoning)
        
        elif routing_decision == RouteDecision.CODER_DIRECT:
            return await self._route_to_coder(user_request, project_path, session_id, context, reasoning)
        
        elif routing_decision == RouteDecision.RESEARCHER_ONLY:
            return await self._route_to_researcher(user_request, project_path, session_id, context, reasoning)
        
        elif routing_decision == RouteDecision.ANALYZER_DIRECT:
            return await self._route_to_analyzer(user_request, project_path, session_id, context, reasoning)
        
        elif routing_decision == RouteDecision.FULL_WORKFLOW:
            # Signal that full workflow is needed
            return {
                "success": True,
                "needs_full_workflow": True,
                "intent": intent.value,
                "reasoning": reasoning
            }
        
        else:
            # Default fallback
            return await self._route_to_researcher(user_request, project_path, session_id, context, reasoning)
    
    async def _handle_conversational(self, user_request: str, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """Handle conversational requests with fast direct response."""
        if not self.invoke_bedrock_model:
            return {"success": True, "result": {"message": "Hello! How can I help you?"}}
        
        system_prompt = "You are a helpful AI assistant. Respond naturally and briefly."
        response = await self.invoke_bedrock_model(
            model_id=self.model_id,
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": user_request}],
            max_tokens=256,
            tools=None
        )
        
        text_parts = []
        for block in response.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        
        response_text = "".join(text_parts)
        
        return {
            "success": True,
            "result": {"message": response_text},
            "message": response_text,
            "agent": "conversational",
            "routing_reasoning": reasoning
        }
    
    async def _route_to_coder(
        self,
        user_request: str,
        project_path: Optional[str],
        session_id: Optional[str],
        context: Optional[Dict[str, Any]],
        reasoning: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route task directly to coder agent."""
        if not self.coder:
            return {"success": False, "error": "Coder agent not available"}
        
        task = {"description": user_request, "project_path": project_path}
        result = await self.coder.execute(task, context=context)
        
        return {
            "success": result.get("success"),
            "result": result,
            "agent": "coder",
            "routing_reasoning": reasoning
        }
    
    async def _route_to_researcher(
        self,
        user_request: str,
        project_path: Optional[str],
        session_id: Optional[str],
        context: Optional[Dict[str, Any]],
        reasoning: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route task to researcher agent."""
        if not self.researcher:
            return {"success": False, "error": "Researcher agent not available"}
        
        task = {"description": user_request, "project_path": project_path}
        result = await self.researcher.execute(task, context=context)
        
        return {
            "success": result.get("success"),
            "result": result,
            "agent": "researcher",
            "routing_reasoning": reasoning
        }
    
    async def _route_to_analyzer(
        self,
        user_request: str,
        project_path: Optional[str],
        session_id: Optional[str],
        context: Optional[Dict[str, Any]],
        reasoning: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route task to analyzer agent."""
        if not self.analyzer:
            return {"success": False, "error": "Analyzer agent not available"}
        
        task = {"description": user_request, "project_path": project_path}
        result = await self.analyzer.execute(task, context=context)
        
        return {
            "success": result.get("success"),
            "result": result,
            "agent": "analyzer",
            "routing_reasoning": reasoning
        }