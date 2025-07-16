# backend/app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import time
import uuid
import psutil
import threading
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# In-memory storage
repositories = []
pull_requests = {}
agent_configs = {
    "security": {"provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.2},
    "quality": {"provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.3},
    "logic": {"provider": "gemini", "model": "gemini-1.5-flash", "temperature": 0.4},
    "context": {"provider": "gemini", "model": "gemini-1.5-pro", "temperature": 0.1},
    "decision": {"provider": "gemini", "model": "gemini-1.5-pro", "temperature": 0.1}
}
settings = {
    "github": {"token": "ghp_yourtoken", "webhook_secret": "yoursecret"},
    "notifications": {"email": "admin@example.com", "slack_webhook": ""},
    "security": {"block_critical": True, "require_2fa": True}
}
analysis_history = []
analysis_queue = []

# Thread lock for thread-safe operations
thread_lock = threading.Lock()

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "message": "PatchPilot Backend API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "metrics": "/api/metrics",
            "repositories": "/api/repositories",
            "analysis": "/api/analysis/pr",
            "analytics": "/api/analytics",
            "agents": "/api/agents/status"
        }
    })

@app.route('/api', methods=['GET'])
def api_info():
    return jsonify({
        "name": "PatchPilot API",
        "version": "1.0.0",
        "description": "AI-powered code review and analysis platform",
        "endpoints": [
            "GET /health - Health check",
            "GET /api/metrics - System metrics",
            "GET /api/repositories - List repositories",
            "POST /api/repositories - Add repository",
            "POST /api/analysis/pr - Analyze pull request",
            "GET /api/analytics - Get analytics data",
            "GET /api/agents/status - Agent status"
        ]
    })

# System metrics endpoint
@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return jsonify({
        "system": {
            "cpu": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "percent": disk.percent
            }
        },
        "application": {
            "repositories": len(repositories),
            "pull_requests": len(pull_requests),
            "queue_size": len(analysis_queue),
            "active_tasks": threading.active_count() - 1
        }
    })

# Agent status endpoint
@app.route('/api/agents/status', methods=['GET'])
def get_agent_status():
    status = {}
    for agent, config in agent_configs.items():
        status[agent] = {
            "status": "active",
            "provider": config["provider"],
            "model": config["model"],
            "last_used": datetime.utcnow().isoformat()
        }
    return jsonify(status)

# Repository management
@app.route('/api/repositories', methods=['GET'])
def get_repositories():
    return jsonify(repositories)

@app.route('/api/repositories', methods=['POST'])
def add_repository():
    data = request.json
    repo = {
        "id": str(uuid.uuid4()),
        "url": data.get('repo_url'),
        "webhook_secret": data.get('webhook_secret'),
        "created_at": datetime.utcnow().isoformat()
    }
    repositories.append(repo)
    return jsonify({"message": "Repository added", "id": repo["id"]}), 201

@app.route('/api/repositories/<id>', methods=['DELETE'])
def delete_repository(id):
    global repositories
    repositories = [r for r in repositories if r["id"] != id]
    return jsonify({"message": "Repository deleted"})

# PR analysis endpoint
@app.route('/api/analysis/pr', methods=['POST'])
def analyze_pr():
    data = request.json
    pr_url = data.get('pr_url')
    analysis_mode = data.get('analysis_mode', 'standard')
    
    # Create a new analysis task
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "pr_url": pr_url,
        "status": "queued",
        "mode": analysis_mode,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "results": None
    }
    
    # Thread-safe operations
    with thread_lock:
        # Add to queue and store in pull_requests BEFORE starting thread
        analysis_queue.append(task)
        pull_requests[task_id] = task
    
    # Start processing in background
    threading.Thread(target=process_analysis_task, args=(task_id,)).start()
    
    return jsonify({
        "message": "Analysis started",
        "task_id": task_id,
        "status": "queued"
    }), 202

def process_analysis_task(task_id):
    try:
        # Wait a bit to ensure task is in dictionary
        time.sleep(0.1)
        
        with thread_lock:
            task = pull_requests.get(task_id)
            if not task:
                print(f"Error: Task {task_id} not found in pull_requests")
                return
            
            task["status"] = "processing"
            task["started_at"] = datetime.utcnow().isoformat()
        
        # Simulate analysis work
        time.sleep(5)  # Simulate processing time
        
        # Generate mock analysis results
        results = {
            "security_issues": [
                {
                    "type": "Hardcoded Secret",
                    "severity": "high",
                    "description": "API key found in source code",
                    "line": 42,
                    "file": "config.py"
                }
            ],
            "quality_issues": [
                {
                    "type": "Code Complexity",
                    "severity": "medium",
                    "description": "Function too long (35 lines)",
                    "line": 15,
                    "file": "utils.py"
                }
            ],
            "logic_issues": [
                {
                    "file": "app.py",
                    "analysis": "Potential null pointer exception",
                    "suggestions": ["Add null check before accessing object"]
                }
            ],
            "decision": {
                "decision": "REQUEST_CHANGES",
                "risk_level": "medium",
                "summary": "1 security issue and 1 quality issue found",
                "recommendations": [
                    "Replace hardcoded API key with environment variable",
                    "Refactor long function into smaller units"
                ]
            }
        }
        
        with thread_lock:
            task["results"] = results
            task["status"] = "completed"
            task["completed_at"] = datetime.utcnow().isoformat()
            
            # Add to history
            analysis_history.append(task.copy())
            
        print(f"Analysis task {task_id} completed successfully")
        
    except Exception as e:
        print(f"Error processing analysis task {task_id}: {str(e)}")
        with thread_lock:
            if task_id in pull_requests:
                pull_requests[task_id]["status"] = "error"
                pull_requests[task_id]["error"] = str(e)

# Analytics endpoint
@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    time_range = request.args.get('range', '7d')
    
    # Calculate time filter
    now = datetime.utcnow()
    if time_range == '24h':
        start_time = now - timedelta(hours=24)
    elif time_range == '30d':
        start_time = now - timedelta(days=30)
    else:  # 7d
        start_time = now - timedelta(days=7)
    
    # Filter completed analyses in time range
    completed_analyses = []
    for t in analysis_history:
        if t["status"] == "completed" and t.get("completed_at"):
            try:
                completed_at = datetime.fromisoformat(t["completed_at"])
                if completed_at > start_time:
                    completed_analyses.append(t)
            except ValueError:
                continue
    
    # Generate metrics
    issue_counts = {
        "security": 0,
        "quality": 0,
        "logic": 0
    }
    
    for t in completed_analyses:
        if t.get("results"):
            issue_counts["security"] += len(t["results"].get("security_issues", []))
            issue_counts["quality"] += len(t["results"].get("quality_issues", []))
            issue_counts["logic"] += len(t["results"].get("logic_issues", []))
    
    return jsonify({
        "time_range": time_range,
        "analysis_count": len(completed_analyses),
        "issue_types": issue_counts,
        "success_rate": 95.0,
        "avg_duration": 8.5
    })

# Agent configuration
@app.route('/api/agents/config', methods=['GET'])
def get_agent_config():
    return jsonify(agent_configs)

@app.route('/api/agents/config', methods=['POST'])
def update_agent_config():
    data = request.json
    for agent, config in data.items():
        if agent in agent_configs:
            agent_configs[agent].update(config)
    return jsonify({"message": "Agent configurations updated"})

# Settings endpoints
@app.route('/api/settings/github', methods=['POST'])
def update_github_settings():
    data = request.json
    settings["github"].update(data)
    return jsonify({"message": "GitHub settings updated"})

@app.route('/api/settings/notifications', methods=['POST'])
def update_notification_settings():
    data = request.json
    settings["notifications"].update(data)
    return jsonify({"message": "Notification settings updated"})

@app.route('/api/settings/security', methods=['POST'])
def update_security_settings():
    data = request.json
    settings["security"].update(data)
    return jsonify({"message": "Security settings updated"})

# Get task status
@app.route('/api/analysis/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = pull_requests.get(task_id)
    if task:
        return jsonify({
            "task_id": task_id,
            "status": task["status"],
            "created_at": task["created_at"],
            "started_at": task.get("started_at"),
            "completed_at": task.get("completed_at"),
            "results": task.get("results"),
            "error": task.get("error")
        })
    return jsonify({"error": "Task not found"}), 404

if __name__ == '__main__':
    # Load environment variables
    port = int(os.getenv('BACKEND_PORT', 8000))
    debug = os.getenv('DEBUG', 'True') == 'True'
    
    print(f"Starting PatchPilot Backend on port {port}")
    print(f"Debug mode: {debug}")
    
    # Start the server
    app.run(host='0.0.0.0', port=port, debug=debug)