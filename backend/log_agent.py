from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import google.generativeai as genai
import os
import re
import json
from collections import Counter
from datetime import datetime

app = FastAPI(title="Agentic Log Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ─── Tool Definitions ────────────────────────────────────────────────────────

def parse_log_structure(log_text: str) -> dict:
    """Parse raw logs into structured data."""
    lines = log_text.strip().split("\n")
    entries = []
    level_pattern = re.compile(
        r'(ERROR|WARN(?:ING)?|INFO|DEBUG|CRITICAL|FATAL)', re.IGNORECASE
    )
    timestamp_pattern = re.compile(
        r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'
    )
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        level_match = level_pattern.search(line)
        ts_match = timestamp_pattern.search(line)
        entry = {
            "line": i + 1,
            "raw": line,
            "level": level_match.group(1).upper() if level_match else "INFO",
            "timestamp": ts_match.group(0) if ts_match else None,
        }
        entries.append(entry)
    levels = Counter(e["level"] for e in entries)
    return {
        "total_lines": len(lines),
        "parsed_entries": len(entries),
        "level_counts": dict(levels),
        "has_errors": levels.get("ERROR", 0) + levels.get("CRITICAL", 0) + levels.get("FATAL", 0) > 0,
        "entries": entries[:200],  # cap for context
    }

def extract_error_patterns(log_text: str) -> dict:
    """Extract repeating error patterns and stack traces."""
    lines = log_text.split("\n")
    errors = []
    stack_traces = []
    in_stack = False
    current_stack = []
    for line in lines:
        if re.search(r'(ERROR|CRITICAL|FATAL|Exception|Traceback)', line, re.IGNORECASE):
            errors.append(line)
            in_stack = True
            current_stack = [line]
        elif in_stack and (line.startswith("  ") or line.startswith("\t") or "at " in line):
            current_stack.append(line)
        else:
            if in_stack and current_stack:
                stack_traces.append("\n".join(current_stack))
                current_stack = []
            in_stack = False
    # Cluster similar errors
    error_clusters = {}
    for e in errors:
        key = re.sub(r'[\d\.:\/]+', 'X', e)[:80]
        error_clusters[key] = error_clusters.get(key, 0) + 1
    return {
        "total_errors": len(errors),
        "unique_error_patterns": len(error_clusters),
        "top_errors": sorted(error_clusters.items(), key=lambda x: -x[1])[:5],
        "stack_traces_found": len(stack_traces),
        "sample_errors": errors[:10],
    }

def check_kubernetes_signals(log_text: str) -> dict:
    """Detect Kubernetes-specific issues."""
    signals = {
        "OOMKilled": bool(re.search(r'OOMKilled|out of memory|oom[-_]?kill', log_text, re.I)),
        "CrashLoopBackOff": bool(re.search(r'CrashLoopBackOff|crash.*loop', log_text, re.I)),
        "ImagePullError": bool(re.search(r'ErrImagePull|ImagePullBackOff', log_text, re.I)),
        "NodeNotReady": bool(re.search(r'NotReady|node.*not.*ready', log_text, re.I)),
        "EvictionPressure": bool(re.search(r'eviction|DiskPressure|MemoryPressure', log_text, re.I)),
        "PodPending": bool(re.search(r'Pending.*pod|pod.*pending', log_text, re.I)),
        "ServiceUnavailable": bool(re.search(r'503|Service Unavailable|upstream.*unavailable', log_text, re.I)),
        "TLSError": bool(re.search(r'TLS|certificate.*expired|x509', log_text, re.I)),
    }
    detected = {k: v for k, v in signals.items() if v}
    return {
        "k8s_issues_detected": len(detected),
        "signals": signals,
        "detected_issues": list(detected.keys()),
    }

def analyze_performance_metrics(log_text: str) -> dict:
    """Extract latency and throughput hints from logs."""
    latencies = []
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s*ms', log_text):
        try:
            latencies.append(float(m.group(1)))
        except Exception:
            pass
    http_codes = Counter(re.findall(r'\b([45]\d{2})\b', log_text))
    slow_threshold = 1000
    slow_requests = [l for l in latencies if l > slow_threshold]
    return {
        "latency_samples": len(latencies),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "max_latency_ms": round(max(latencies), 1) if latencies else None,
        "slow_requests_over_1s": len(slow_requests),
        "http_error_codes": dict(http_codes),
        "has_performance_issues": len(slow_requests) > 0 or bool(http_codes),
    }

# ─── Gemini Tool Schema ───────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "parse_log_structure",
        "description": "Parse raw log text to extract structure: log levels, timestamps, entry counts.",
        "parameters": {
            "type": "object",
            "properties": {
                "log_text": {"type": "string", "description": "Raw log text to parse"}
            },
            "required": ["log_text"]
        }
    },
    {
        "name": "extract_error_patterns",
        "description": "Find repeating error patterns, exceptions, and stack traces in logs.",
        "parameters": {
            "type": "object",
            "properties": {
                "log_text": {"type": "string", "description": "Raw log text to analyze"}
            },
            "required": ["log_text"]
        }
    },
    {
        "name": "check_kubernetes_signals",
        "description": "Detect Kubernetes-specific issues like OOMKill, CrashLoopBackOff, ImagePullErrors.",
        "parameters": {
            "type": "object",
            "properties": {
                "log_text": {"type": "string", "description": "Log text to check for K8s signals"}
            },
            "required": ["log_text"]
        }
    },
    {
        "name": "analyze_performance_metrics",
        "description": "Extract latency values, HTTP error codes, and performance signals from logs.",
        "parameters": {
            "type": "object",
            "properties": {
                "log_text": {"type": "string", "description": "Log text to analyze for performance"}
            },
            "required": ["log_text"]
        }
    }
]

TOOL_MAP = {
    "parse_log_structure": parse_log_structure,
    "extract_error_patterns": extract_error_patterns,
    "check_kubernetes_signals": check_kubernetes_signals,
    "analyze_performance_metrics": analyze_performance_metrics,
}

# ─── Agentic Loop ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert DevOps SRE AI agent. When given logs, you MUST use your tools 
to systematically analyze them before forming conclusions. Always:
1. First call parse_log_structure to understand the log format
2. Call extract_error_patterns to find errors and exceptions
3. Call check_kubernetes_signals to detect K8s issues
4. Call analyze_performance_metrics to find latency/HTTP issues
5. Then synthesize a root cause analysis with clear sections:
   - Summary
   - Critical Issues (if any)
   - Root Cause (your best diagnosis)
   - Remediation Steps (specific commands/fixes)
   - Prevention Recommendations

Be specific. Reference actual log lines. Provide kubectl/bash commands where relevant."""

class AnalyzeRequest(BaseModel):
    log_text: str
    gemini_key: Optional[str] = None

class AgentStep(BaseModel):
    type: str       # "tool_call" | "tool_result" | "thinking" | "final"
    name: Optional[str] = None
    input: Optional[dict] = None
    output: Optional[dict] = None
    text: Optional[str] = None

class AnalyzeResponse(BaseModel):
    steps: list[AgentStep]
    final_analysis: str
    stats: dict

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_logs(req: AnalyzeRequest):
    api_key = req.gemini_key or GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="No GEMINI_API_KEY provided")

    genai.configure(api_key=api_key)

    gemini_tools = genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        k: genai.protos.Schema(type=genai.protos.Type.STRING, description=v["description"])
                        for k, v in t["parameters"]["properties"].items()
                    },
                    required=t["parameters"].get("required", [])
                )
            )
            for t in TOOLS
        ]
    )

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
        tools=[gemini_tools]
    )

    steps: list[AgentStep] = []
    messages = [{"role": "user", "parts": [f"Analyze these logs:\n\n{req.log_text}"]}]

    MAX_ITERATIONS = 8
    final_text = ""

    for iteration in range(MAX_ITERATIONS):
        response = model.generate_content(messages)
        candidate = response.candidates[0]

        has_function_call = False
        tool_responses = []

        for part in candidate.content.parts:
            if hasattr(part, 'function_call') and part.function_call.name:
                fc = part.function_call
                has_function_call = True
                tool_name = fc.name
                tool_args = dict(fc.args)

                # Inject the actual log text if missing
                if "log_text" not in tool_args or not tool_args["log_text"]:
                    tool_args["log_text"] = req.log_text

                steps.append(AgentStep(
                    type="tool_call",
                    name=tool_name,
                    input={"tool": tool_name}
                ))

                if tool_name in TOOL_MAP:
                    result = TOOL_MAP[tool_name](**tool_args)
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}

                steps.append(AgentStep(
                    type="tool_result",
                    name=tool_name,
                    output=result
                ))

                tool_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=tool_name,
                            response={"result": result}
                        )
                    )
                )

            elif hasattr(part, 'text') and part.text:
                if not has_function_call:
                    final_text += part.text

        if has_function_call and tool_responses:
            messages.append({"role": "model", "parts": candidate.content.parts})
            messages.append({"role": "user", "parts": tool_responses})
        else:
            break

    if not final_text:
        # One more pass to get the summary
        response = model.generate_content(messages)
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'text') and part.text:
                final_text += part.text

    steps.append(AgentStep(type="final", text=final_text))

    # Build top-level stats
    stats = {}
    for step in steps:
        if step.type == "tool_result" and step.output:
            if step.name == "parse_log_structure":
                stats["total_lines"] = step.output.get("total_lines", 0)
                stats["level_counts"] = step.output.get("level_counts", {})
            elif step.name == "extract_error_patterns":
                stats["total_errors"] = step.output.get("total_errors", 0)
                stats["unique_patterns"] = step.output.get("unique_error_patterns", 0)
            elif step.name == "check_kubernetes_signals":
                stats["k8s_issues"] = step.output.get("detected_issues", [])
            elif step.name == "analyze_performance_metrics":
                stats["avg_latency_ms"] = step.output.get("avg_latency_ms")
                stats["slow_requests"] = step.output.get("slow_requests_over_1s", 0)

    return AnalyzeResponse(steps=steps, final_analysis=final_text, stats=stats)
