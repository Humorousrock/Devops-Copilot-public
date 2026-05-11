# 🤖 DevOps Copilot — Agentic AI Assistant

An AI-powered DevOps Copilot built with Google Gemini that autonomously investigates infrastructure issues using the ReAct pattern (Reason → Act → Observe → Answer).

## 🚀 What It Does

This is NOT just a chatbot — it is a real AI agent that:
- Autonomously decides which tools to call
- Fetches real data from your infrastructure
- Reasons about the results
- Gives you root cause and exact fix commands

## 🧠 How The Agent Works (ReAct Pattern)
You ask one question
↓
Gemini reasons: "what tools do I need?"
↓
Calls tools automatically (up to 6 rounds)
↓
Reads results, reasons again
↓
Synthesizes final answer with fix commands

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| AI Model | Google Gemini 2.0 |
| Backend | Python + FastAPI |
| Frontend | HTML + CSS + JavaScript |
| Kubernetes | Minikube / EKS |
| CI/CD | Jenkins + Docker |
| Monitoring | Prometheus + Grafana |
| Metrics | Kubernetes metrics-server |
| Container | Docker + Docker Compose |

## 🔧 7 Agentic Tools

| # | Tool | Status | Description |
|---|---|---|---|
| 1 | get_kubernetes_status | Real | Pod health, restarts, cluster status |
| 2 | get_pod_logs | Real | Real kubectl logs from any pod |
| 3 | get_cicd_pipeline_status | Simulated | GitHub Actions pipelines |
| 4 | get_monitoring_alerts | Real | Prometheus/Grafana alerts |
| 5 | get_resource_metrics | Real | CPU/memory via metrics-server |
| 6 | generate_runbook | Real | Step-by-step incident fix guide |
| 7 | get_jenkins_pipeline_status | Real | Jenkins build errors and console logs |

## 📁 Project Structure
devops-copilot/
├── backend/
│   ├── copilot.py         Main AI agent with 7 tools
│   └── log_agent.py       Log analyzer agent
├── frontend/
│   ├── copilot.html       Copilot chat UI
│   └── log-agent.html     Log analyzer UI
├── .env.example           Environment variables template
├── docker-compose.yml     Run with Docker
├── deployment.yaml        Deploy to Kubernetes
└── README.md

## ⚙️ Setup and Installation

### Prerequisites
- Python 3.9+
- Docker Desktop
- Minikube (for local Kubernetes)
- Jenkins (optional)
- Prometheus (optional)

### Step 1 - Clone the repo
```bash
git clone https://github.xxxxxxxxx
cd devops-copilot
```

### Step 2 - Create .env file
GEMINI_API_KEY=your_gemini_key
JENKINS_URL=http://localhost:8080
JENKINS_USER=your_jenkins_user
JENKINS_TOKEN=your_jenkins_token

Get your Gemini API key at https://aistudio.google.com/apikey

### Step 3 - Install dependencies
```bash
cd backend
pip install fastapi uvicorn google-genai python-dotenv requests
```

### Step 4 - Start the backend
```bash
uvicorn copilot:app --reload --port 8000
```

Log Analyzer starts automatically on port 8001.

### Step 5 - Open the frontend

Open frontend/copilot.html in your browser.

## 🐳 Run With Docker Compose

```bash
docker-compose up --build
```

## ☸️ Deploy to Kubernetes

```bash
kubectl apply -f deployment.yaml
```

## 🔌 Real Infrastructure Setup

### Minikube - Local Kubernetes
```bash
minikube start --driver=docker
minikube addons enable metrics-server
```

### Jenkins - Docker
```bash
docker run -d -p 8080:8080 --name jenkins jenkins/jenkins:lts
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Open http://localhost:8080 to set up Jenkins.

### Prometheus - Monitoring
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace
kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n monitoring 9090:9090
```

Open http://localhost:9090 to view Prometheus.

## 🏗️ Architecture
Browser (copilot.html)
↓
FastAPI Backend port 8000
↓
Google Gemini AI
↓
7 Tool Functions
↓
Real Infrastructure
kubectl - Kubernetes
Jenkins API
Prometheus API
metrics-server

## 📊 Two Tools In One Project

### DevOps Copilot
Chat interface for DevOps questions. Ask anything about your cluster, pipelines, and alerts. The agent automatically calls the right tools and gives you actionable fixes.

### Log Analyzer
Paste any log file and the agent runs 4 specialist tools to find the root cause. Works with Kubernetes logs, Jenkins console output, Nginx logs, application logs, and any plain text logs.

## 📝 What This Project Demonstrates

### GenAI Skills
- Google Gemini API integration
- Function and tool calling
- Agentic ReAct pattern
- Multi-step reasoning
- Prompt engineering

### DevOps Skills
- Kubernetes monitoring and debugging
- Jenkins CI/CD pipeline monitoring
- Prometheus alerting
- Docker containerization
- Kubernetes manifests and Helm charts
- Infrastructure as Code

### Development Skills
- Python and FastAPI
- REST API design
- Frontend development with HTML CSS JavaScript
- Environment management
- Project structure and documentation

## 🎯 Same Architecture As

- GitHub Copilot
- AWS DevOps Guru
- Datadog AI Assistant
- PagerDuty AI

## 🚦 Current Tool Status
Tool 1 - Kubernetes Status    - Real data from minikube
Tool 2 - Pod Logs             - Real kubectl logs
Tool 3 - GitHub Actions       - Simulated data
Tool 4 - Prometheus Alerts    - Real Prometheus API
Tool 5 - Resource Metrics     - Real metrics-server
Tool 6 - Runbook Generator    - Always real
Tool 7 - Jenkins Pipelines    - Real Jenkins API

## 📄 License

MIT License

## 👤 Author

Aman Rana
GitHub: https://github.com/Humorousrock

<img width="1907" height="917" alt="image" src="https://github.com/user-attachments/assets/f3864843-5532-43e5-96d7-abfa4c363acc" />

<img width="1912" height="933" alt="image" src="https://github.com/user-attachments/assets/0c869047-eb79-4c49-bb07-b225c0bb92fb" />

