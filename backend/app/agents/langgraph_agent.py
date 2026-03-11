"""
LangGraph-based Nila agent: Intent → Policy → Execution → Output
Uses DeepSeek (OpenAI-compatible) as the LLM backbone.
"""
from __future__ import annotations
from typing import TypedDict, Optional, Literal, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
from ..config import settings

# ─── LLM Setup ─────────────────────────────────────────────────────────────────

def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        temperature=0.3,
    )


# ─── Agent State ───────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    user_message: str
    language: str
    intent: Optional[str]
    policy_ok: bool
    policy_reason: Optional[str]
    action: Optional[str]
    pre_fill: Optional[dict]
    route: Optional[str]
    response: str
    error: Optional[str]


# ─── System Prompts ────────────────────────────────────────────────────────────

INTENT_SYSTEM = """You are Nila, a professional and friendly AI workplace assistant.
Your role is to understand user requests about workplace access and resources.

Analyze the user's message and identify:
1. intent: one of ["create_request", "track_request", "approve_request", "navigate", "general_query"]
2. request_type: one of ["System Access", "Equipment", "Facility", "General Service"] or null
3. key_details: any extracted details (description, priority hints, etc.)

IMPORTANT: Respond ONLY with a valid JSON object like:
{
  "intent": "create_request",
  "request_type": "Equipment",
  "key_details": {
    "description": "I need a new monitor",
    "priority": "Medium"
  }
}
"""

POLICY_SYSTEM = """You are a policy checker for the Nila workplace access system.
Supported request types: System Access, Equipment, Facility, General Service.
Supported priorities: Low, Medium, High.
Supported intents: create_request, track_request, approve_request, navigate, general_query.

Given the intent and extracted details, decide if this request is valid and aligns with policy.
Respond ONLY with valid JSON:
{
  "policy_ok": true,
  "reason": "Valid equipment request"
}
"""

OUTPUT_SYSTEM_EN = """You are Nila, a professional and friendly AI workplace assistant.
Generate a helpful, concise response in English for the user's request.
Be warm, professional, and action-oriented. Keep responses under 3 sentences.
"""

OUTPUT_SYSTEM_TA = """நீங்கள் நிலா, ஒரு நட்பான மற்றும் தொழில்முறை AI பணியிட உதவியாளர்.
பயனரின் கோரிக்கைக்கு தமிழில் உதவியான, சுருக்கமான பதிலை உருவாக்கவும்.
அன்பாகவும், தொழில்முறையாகவும் இருக்கவும். பதில்கள் 3 வாக்கியங்களுக்கு குறைவாக இருக்க வேண்டும்.
"""

# Route map for navigation intents
ROUTE_MAP = {
    "create_request": "/requests/new",
    "track_request": "/requests",
    "approve_request": "/dashboard",
    "navigate": "/dashboard",
}

FORM_TYPE_MAP = {
    "system access": "System Access Request",
    "equipment": "Equipment Request",
    "facility": "Facility Request",
    "general service": "General Service Request",
}


# ─── Graph Nodes ───────────────────────────────────────────────────────────────

def intent_node(state: AgentState) -> AgentState:
    """Classifies user intent using DeepSeek."""
    try:
        llm = get_llm()
        response = llm.invoke([
            SystemMessage(content=INTENT_SYSTEM),
            HumanMessage(content=state["user_message"]),
        ])
        parsed = json.loads(response.content.strip())
        return {
            **state,
            "intent": parsed.get("intent", "general_query"),
            "pre_fill": parsed.get("key_details"),
            "error": None,
        }
    except Exception as e:
        return {**state, "intent": "general_query", "error": str(e), "pre_fill": None}


def policy_node(state: AgentState) -> AgentState:
    """Validates the request against system policy."""
    try:
        llm = get_llm()
        check_input = json.dumps({
            "intent": state["intent"],
            "pre_fill": state.get("pre_fill"),
            "message": state["user_message"],
        })
        response = llm.invoke([
            SystemMessage(content=POLICY_SYSTEM),
            HumanMessage(content=check_input),
        ])
        parsed = json.loads(response.content.strip())
        return {
            **state,
            "policy_ok": parsed.get("policy_ok", True),
            "policy_reason": parsed.get("reason", ""),
        }
    except Exception:
        return {**state, "policy_ok": True, "policy_reason": "Policy check skipped"}


def execution_node(state: AgentState) -> AgentState:
    """Determines the action and route for the UI."""
    intent = state.get("intent", "general_query")
    pre_fill = state.get("pre_fill") or {}

    # Map request_type from pre_fill to proper form type
    rt_raw = pre_fill.get("request_type", "").lower() if pre_fill else ""
    mapped_type = None
    for key, val in FORM_TYPE_MAP.items():
        if key in rt_raw:
            mapped_type = val
            break

    action = None
    route = None

    if intent == "create_request":
        action = "open_request_form"
        route = "/requests/new"
        if mapped_type:
            pre_fill["request_type_name"] = mapped_type
    elif intent == "track_request":
        action = "navigate_to_register"
        route = "/requests"
    elif intent == "approve_request":
        action = "navigate_to_dashboard"
        route = "/dashboard"
    elif intent == "navigate":
        action = "navigate"
        route = "/dashboard"

    return {**state, "action": action, "route": route, "pre_fill": pre_fill}


def output_node(state: AgentState) -> AgentState:
    """Generates the natural language response for the user."""
    try:
        llm = get_llm()
        system_prompt = OUTPUT_SYSTEM_TA if state.get("language") == "ta" else OUTPUT_SYSTEM_EN
        context = f"User said: {state['user_message']}\nIntent: {state.get('intent')}\nAction: {state.get('action')}"
        if not state.get("policy_ok"):
            context += f"\nPolicy violation: {state.get('policy_reason')}"
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=context),
        ])
        return {**state, "response": response.content.strip()}
    except Exception as e:
        return {
            **state,
            "response": "I'm here to help! How can I assist you with your workplace access or resource needs?",
        }


def policy_router(state: AgentState) -> Literal["execution", "output"]:
    """Routes to execution if policy is ok, otherwise straight to output."""
    return "execution" if state.get("policy_ok", True) else "output"


# ─── Build Graph ───────────────────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("intent", intent_node)
    graph.add_node("policy", policy_node)
    graph.add_node("execution", execution_node)
    graph.add_node("output", output_node)

    graph.set_entry_point("intent")
    graph.add_edge("intent", "policy")
    graph.add_conditional_edges("policy", policy_router, {
        "execution": "execution",
        "output": "output",
    })
    graph.add_edge("execution", "output")
    graph.add_edge("output", END)

    return graph.compile()


_agent_graph = None


def get_agent():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph


# ─── Public API ────────────────────────────────────────────────────────────────

def run_agent(message: str, language: str = "en") -> dict:
    agent = get_agent()
    initial_state: AgentState = {
        "user_message": message,
        "language": language,
        "intent": None,
        "policy_ok": True,
        "policy_reason": None,
        "action": None,
        "pre_fill": None,
        "route": None,
        "response": "",
        "error": None,
    }
    result = agent.invoke(initial_state)
    return {
        "intent": result.get("intent"),
        "response": result.get("response"),
        "action": result.get("action"),
        "pre_fill": result.get("pre_fill"),
        "route": result.get("route"),
    }
