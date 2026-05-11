from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from google import genai
from google.genai import types
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import subprocess
import json

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

import subprocess
import threading
import sys
import os

def start_log_agent():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    subprocess.run(
        [sys.executable, "-m", "uvicorn", 
         "log_agent:app", "--port", "8001"],
        cwd=backend_dir  # run from backend folder
    )

thread = threading.Thread(target=start_log_agent, daemon=True)
thread.start()

app = FastAPI(title="DevOps Copilot Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
JENKINS_URL   = os.getenv("JENKINS_URL", "")
JENKINS_USER  = os.getenv("JENKINS_USER", "")
JENKINS_TOKEN = os.getenv("JENKINS_TOKEN", "")

def get_kubernetes_status(namespace: str = "default") -> dict:
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "--all-namespaces", "-o", "json"],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        
        pod_list = []
        for pod in data["items"]:
            restarts = 0
            if pod["status"].get("containerStatuses"):
                restarts = sum(
                    cs["restartCount"] 
                    for cs in pod["status"]["containerStatuses"]
                )
            pod_list.append({
                "name":      pod["metadata"]["name"],
                "namespace": pod["metadata"]["namespace"],
                "status":    pod["status"]["phase"],
                "restarts":  restarts
            })
        
        failing = [p for p in pod_list if p["restarts"] > 2 or p["status"] == "Failed"]
        
        return {
            "cluster":    "minikube",
            "total_pods": len(pod_list),
            "running":    sum(1 for p in pod_list if p["status"] == "Running"),
            "failing":    len(failing),
            "pending":    sum(1 for p in pod_list if p["status"] == "Pending"),
            "pods":       pod_list,
            "issues":     [f"{p['name']} in {p['namespace']} has {p['restarts']} restarts" 
                          for p in failing]
        }
    except Exception as e:
        return {"error": str(e)}


def get_pod_logs(pod_name: str, lines: int = 50) -> dict:
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "--all-namespaces", "-o", "json"],
            capture_output=True, text=True
        )
        pods = json.loads(result.stdout)["items"]
        
        matched = next(
            (p for p in pods 
             if pod_name.lower() in p["metadata"]["name"].lower()),
            None
        )
        
        if not matched:
            return {"error": f"No pod found matching: {pod_name}"}
        
        name = matched["metadata"]["name"]
        ns   = matched["metadata"]["namespace"]
        
        logs = subprocess.run(
            ["kubectl", "logs", name, "-n", ns, f"--tail={lines}"],
            capture_output=True, text=True
        )
        
        return {
            "pod":       name,
            "namespace": ns,
            "lines":     logs.stdout.split("\n") if logs.stdout else ["No logs available"],
            "stderr":    logs.stderr
        }
    except Exception as e:
        return {"error": str(e)}

def get_cicd_pipeline_status(repo: str = "all") -> dict:
    pipelines = [
        {"repo": "myorg/api-service", "status": "success", "commit": "feat: add retry logic",         "ago": "12m ago"},
        {"repo": "myorg/frontend",    "status": "failed",  "commit": "fix: cart calculation",          "ago": "28m ago", "error": "Jest: 3 tests failing in CartComponent.test.js"},
        {"repo": "myorg/infra",       "status": "running", "commit": "chore: update terraform",        "ago": "1m ago"},
        {"repo": "myorg/payment-svc", "status": "success", "commit": "fix: mount ssl cert from secret","ago": "5m ago"},
    ]
    return {"pipelines": pipelines, "passing": 2, "failing": 1, "running": 1}

def get_monitoring_alerts(severity: str = "all") -> dict:
    try:
        import urllib.request

        # get alerts from Prometheus API
        url = "http://localhost:9090/api/v1/alerts"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())

        alerts = []
        for alert in data.get("data", {}).get("alerts", []):
            alerts.append({
                "name":     alert["labels"].get("alertname", "Unknown"),
                "severity": alert["labels"].get("severity", "info"),
                "service":  alert["labels"].get("job", "unknown"),
                "namespace": alert["labels"].get("namespace", ""),
                "message":  alert["annotations"].get("summary", ""),
                "state":    alert["state"]
            })

        if severity != "all":
            alerts = [a for a in alerts
                     if a["severity"] == severity]

        return {
            "active_alerts": len(alerts),
            "critical": sum(1 for a in alerts if a["severity"] == "critical"),
            "warning":  sum(1 for a in alerts if a["severity"] == "warning"),
            "info":     sum(1 for a in alerts if a["severity"] == "info"),
            "alerts":   alerts
        }

    except Exception as e:
        return {
            "error": str(e),
            "hint": "Make sure Prometheus is port-forwarded: kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n monitoring 9090:9090"
        }
def get_resource_metrics(service: str = "all") -> dict:
    try:
        # get real CPU and memory from metrics-server
        result = subprocess.run(
            ["kubectl", "top", "pods", 
             "--all-namespaces", "--no-headers"],
            capture_output=True, text=True
        )
        
        if not result.stdout:
            return {"error": "metrics-server not ready yet"}
        
        metrics = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 4:
                metrics.append({
                    "namespace": parts[0],
                    "pod":       parts[1],
                    "cpu":       parts[2],
                    "memory":    parts[3]
                })
        
        # filter by service name if specified
        if service != "all":
            metrics = [m for m in metrics 
                      if service.lower() in m["pod"].lower()]
        
        # find high usage pods
        high_cpu = [m for m in metrics 
                   if int(m["cpu"].replace("m","")) > 100]
        high_mem = [m for m in metrics 
                   if int(m["memory"].replace("Mi","")) > 200]
        
        return {
            "total_pods":    len(metrics),
            "metrics":       metrics,
            "high_cpu_pods": high_cpu,
            "high_mem_pods": high_mem,
            "cluster_summary": {
                "most_cpu": max(metrics, key=lambda x: int(x["cpu"].replace("m","")))["pod"] if metrics else None,
                "most_mem": max(metrics, key=lambda x: int(x["memory"].replace("Mi","")))["pod"] if metrics else None,
            }
        }
    except Exception as e:
        return {"error": str(e)}

def generate_runbook(incident_type: str) -> dict:
    runbooks = {
        "crashloopbackoff": {
            "title": "CrashLoopBackOff Runbook",
            "steps": [
                "kubectl describe pod <pod-name> -n <namespace>",
                "kubectl logs <pod-name> --previous",
                "Check exit code: 137=OOMKilled, 1=app crash",
                "kubectl get events -n <namespace> --sort-by=.lastTimestamp",
                "Fix root cause then: kubectl rollout restart deployment/<n>",
            ],
            "common_causes": ["Missing secret/configmap", "OOMKilled", "App startup crash"],
        },
        "high_latency": {
            "title": "High Latency Runbook",
            "steps": [
                "kubectl top pods -n <namespace>",
                "Check slow query logs in DB",
                "kubectl get hpa -n <namespace>",
                "kubectl scale deployment <n> --replicas=5",
            ],
            "common_causes": ["Slow DB queries", "CPU throttling", "Missing cache"],
        },
    }
    key = incident_type.lower().replace(" ", "_").replace("-", "_")
    for k, v in runbooks.items():
        if k in key or key in k:
            return v
    return {"title": f"Runbook: {incident_type}", "steps": ["Check logs", "Check events", "Escalate"], "common_causes": ["Unknown"]}

def get_jenkins_pipeline_status(job_name: str = "all") -> dict:
    try:
        if not JENKINS_URL:
            return {"error": "JENKINS_URL not set in .env"}

        auth = HTTPBasicAuth(JENKINS_USER, JENKINS_TOKEN)

        res = requests.get(
            f"{JENKINS_URL}/api/json?tree=jobs[name,color,url]",
            auth=auth, timeout=10
        )

        if res.status_code != 200:
            return {"error": f"Jenkins returned {res.status_code}"}

        all_jobs = res.json()["jobs"]

        if job_name != "all":
            all_jobs = [j for j in all_jobs
                       if job_name.lower() in j["name"].lower()]

        results = []
        for job in all_jobs[:10]:
            build_res = requests.get(
                f"{job['url']}lastBuild/api/json",
                auth=auth, timeout=10
            )

            if build_res.status_code != 200:
                continue

            build = build_res.json()

            console_log = ""
            if build.get("result") == "FAILURE":
                log_res = requests.get(
                    f"{job['url']}lastBuild/consoleText",
                    auth=auth, timeout=10
                )
                lines = log_res.text.split("\n")
                console_log = "\n".join(lines[-50:])

            results.append({
                "job":          job["name"],
                "status":       build.get("result", "RUNNING"),
                "duration":     f"{build.get('duration', 0) // 1000}s",
                "build_number": build.get("number", 0),
                "url":          build.get("url", ""),
                "error_log":    console_log[-2000:] if console_log else ""
            })

        failed  = [r for r in results if r["status"] == "FAILURE"]
        success = [r for r in results if r["status"] == "SUCCESS"]

        return {
            "total_jobs":  len(results),
            "failed":      len(failed),
            "success":     len(success),
            "jobs":        results,
            "failed_jobs": failed
        }

    except Exception as e:
        return {"error": str(e)}

TOOL_MAP = {
    "get_kubernetes_status":    get_kubernetes_status,
    "get_pod_logs":             get_pod_logs,
    "get_cicd_pipeline_status": get_cicd_pipeline_status,
    "get_monitoring_alerts":    get_monitoring_alerts,
    "get_resource_metrics":     get_resource_metrics,
    "generate_runbook":         generate_runbook,
    "get_jenkins_pipeline_status": get_jenkins_pipeline_status,
}

GEMINI_TOOLS = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="get_kubernetes_status",
        description="Get current Kubernetes cluster status: pod health, restarts, pending pods.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={
            "namespace": types.Schema(type=types.Type.STRING, description="K8s namespace (default: default)")
        })
    ),
    types.FunctionDeclaration(
        name="get_pod_logs",
        description="Fetch recent logs from a specific Kubernetes pod.",
        parameters=types.Schema(type=types.Type.OBJECT,
            properties={
                "pod_name": types.Schema(type=types.Type.STRING, description="Pod name or partial name"),
                "lines":    types.Schema(type=types.Type.STRING, description="Number of lines")
            },
            required=["pod_name"]
        )
    ),
    types.FunctionDeclaration(
        name="get_cicd_pipeline_status",
        description="Check GitHub Actions CI/CD pipeline status.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={
            "repo": types.Schema(type=types.Type.STRING, description="Repo filter (default: all)")
        })
    ),
    types.FunctionDeclaration(
        name="get_monitoring_alerts",
        description="Get active Prometheus/Grafana alerts by severity.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={
            "severity": types.Schema(type=types.Type.STRING, description="critical, warning, info, or all")
        })
    ),
    types.FunctionDeclaration(
        name="get_resource_metrics",
        description="Get CPU, memory, latency metrics for services.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={
            "service": types.Schema(type=types.Type.STRING, description="Service name (default: all)")
        })
    ),
    types.FunctionDeclaration(
        name="generate_runbook",
        description="Generate step-by-step incident runbook.",
        parameters=types.Schema(type=types.Type.OBJECT,
            properties={"incident_type": types.Schema(type=types.Type.STRING, description="e.g. crashloopbackoff, high_latency")},
            required=["incident_type"]
        )
    ),
    types.FunctionDeclaration(
    name="get_jenkins_pipeline_status",
    description="Fetch Jenkins pipeline status, build errors and console logs for failed jobs.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "job_name": types.Schema(
                type=types.Type.STRING,
                description="Jenkins job name to check (default: all)"
            )
        }
    )
),
])

SYSTEM_PROMPT = """You are an expert DevOps Copilot AI agent with real-time cluster access via tools.
Always call tools before answering — never guess about system state.
Specialties: Kubernetes, CI/CD, Prometheus alerts, incident response.
Be direct. Give kubectl/bash commands. Use markdown for formatting.

IMPORTANT RULES:
- For ANY question about Jenkins pipelines, jobs or builds → always call get_jenkins_pipeline_status with job_name="all"
- For ANY question about Kubernetes pods, nodes, cluster → always call get_kubernetes_status
- For ANY question about logs → always call get_pod_logs
- For ANY question about alerts → always call get_monitoring_alerts
- For ANY question about CPU, memory, metrics → always call get_resource_metrics
- NEVER say you cannot check something — always try the tool first!"""

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]
    gemini_key: Optional[str] = None

class ToolCall(BaseModel):
    name: str
    result: dict

class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolCall]

@app.get("/health")
def health():
    return {"status": "ok", "key_loaded": bool(GEMINI_API_KEY)}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    api_key = req.gemini_key or GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="No GEMINI_API_KEY found. Add it to your .env file.")

    client = genai.Client(api_key=api_key)

    history = []
    for m in req.messages[:-1]:
        role = "user" if m.role == "user" else "model"
        history.append(types.Content(role=role, parts=[types.Part(text=m.content)]))
    history.append(types.Content(role="user", parts=[types.Part(text=req.messages[-1].content)]))

    tool_calls_made: list[ToolCall] = []
    final_text = ""

    for _ in range(6):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[GEMINI_TOOLS],
            )
        )

        candidate = response.candidates[0]
        has_tool_call = False
        tool_response_parts = []

        for part in candidate.content.parts:
            if part.function_call:
                has_tool_call = True
                fc = part.function_call
                args = dict(fc.args) if fc.args else {}
                fn = TOOL_MAP.get(fc.name)
                if fn:
                    try:
                        if "lines" in args:
                            args["lines"] = int(args["lines"])
                        result = fn(**args)
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"Unknown tool: {fc.name}"}

                tool_calls_made.append(ToolCall(name=fc.name, result=result))
                tool_response_parts.append(types.Part(
                    function_response=types.FunctionResponse(name=fc.name, response={"result": result})
                ))
            elif part.text:
                final_text += part.text

        if has_tool_call:
            history.append(candidate.content)
            history.append(types.Content(role="user", parts=tool_response_parts))
        else:
            break

    return ChatResponse(reply=final_text, tool_calls=tool_calls_made)