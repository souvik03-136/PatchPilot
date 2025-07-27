import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from flask import Flask, jsonify, request
from flask_cors import CORS
import time
import uuid
import psutil
import threading
import os
from datetime import datetime, timedelta
import sys
import traceback
from dotenv import load_dotenv
import json
import logging
from werkzeug.serving import is_running_from_reloader

# Disable noisy logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Disable specific noisy loggers
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)

# Load environment variables early
load_dotenv()

# Add project root to Python path for proper imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Try to import agent system components with absolute imports
AGENT_SYSTEM_AVAILABLE = False
try:
    from agents.agent_system import AgentSystem
    from agents.models import AnalysisContext, CodeSnippet, Vulnerability, QualityIssue
    from agents.github_integration import GitHubIntegration
    from agents.security_agent import SecurityAgent
    from agents.quality_agent import QualityAgent
    from agents.logic_agent import LogicAgent
    from agents.decision_agent import DecisionAgent
    
    AGENT_SYSTEM_AVAILABLE = True
    print("Agent system successfully imported")
    
except ImportError as e:
    print(f"Warning: Could not import agent system: {e}")
    print("Running without agent system - some features will be limited")
    AgentSystem = None
    AnalysisContext = None
    CodeSnippet = None
    GitHubIntegration = None
    SecurityAgent = None
    QualityAgent = None
    LogicAgent = None
    DecisionAgent = None

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
    "github": {"token": os.getenv("GITHUB_TOKEN", ""), "webhook_secret": os.getenv("GITHUB_WEBHOOK_SECRET", "")},
    "notifications": {"email": os.getenv("ADMIN_EMAIL", ""), "slack_webhook": os.getenv("SLACK_WEBHOOK", "")},
    "security": {"block_critical": True, "require_2fa": True}
}
analysis_history = []
analysis_queue = []

# Thread lock for thread-safe operations
thread_lock = threading.Lock()

# Add this function to save/load tasks from disk
def load_tasks():
    global pull_requests, analysis_history
    try:
        with open('tasks.json', 'r') as f:
            data = json.load(f)
            pull_requests = {k: v for k, v in data.get('pull_requests', {}).items()}
            analysis_history = data.get('analysis_history', [])
        print(f"Loaded {len(pull_requests)} active tasks and {len(analysis_history)} historical tasks")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"No existing task data found or error loading: {e}")
        pass

def save_tasks():
    try:
        with open('tasks.json', 'w') as f:
            json.dump({
                "pull_requests": pull_requests,
                "analysis_history": analysis_history
            }, f, default=str)
    except Exception as e:
        print(f"Error saving tasks: {e}")

# Call this at app startup
load_tasks()

# Initialize agents globally if available
agents = {}
if AGENT_SYSTEM_AVAILABLE:
    try:
        print("Initializing agents...")
        agents = {
            "security": SecurityAgent(provider=agent_configs["security"]["provider"]),
            "quality": QualityAgent(provider=agent_configs["quality"]["provider"]),
            "logic": LogicAgent(provider=agent_configs["logic"]["provider"]),  # Fixed parameter
            "decision": DecisionAgent(provider=agent_configs["decision"]["provider"])
        }
        print(f"Agents initialized: {list(agents.keys())}")
    except Exception as e:
        print(f"Error initializing agents: {str(e)}")
        traceback.print_exc()
        agents = {}

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok", 
        "timestamp": datetime.utcnow().isoformat(),
        "agent_system_available": AGENT_SYSTEM_AVAILABLE,
        "agents_initialized": len(agents)
    })

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "message": "PatchPilot Backend API",
        "version": "1.0.0",
        "status": "running",
        "agent_system": "available" if AGENT_SYSTEM_AVAILABLE else "unavailable",
        "endpoints": {
            "health": "/health",
            "metrics": "/api/metrics",
            "repositories": "/api/repositories",
            "analysis": "/api/analysis/pr",
            "security": "/api/analysis/security",
            "logic": "/api/analysis/logic",
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
        "agent_system_status": "available" if AGENT_SYSTEM_AVAILABLE else "unavailable",
        "endpoints": [
            "GET /health - Health check",
            "GET /api/metrics - System metrics",
            "GET /api/repositories - List repositories",
            "POST /api/repositories - Add repository",
            "POST /api/analysis/pr - Analyze pull request",
            "POST /api/analysis/security - Security analysis",
            "GET /api/analytics - Get analytics data",
            "GET /api/agents/status - Agent status"
        ]
    })

@app.route('/api/analysis/security', methods=['POST'])
def analyze_security():
    data = request.json
    if not data or 'code_snippets' not in data:
        return jsonify({"error": "Missing code_snippets in request"}), 400
    
    code_snippets = data.get('code_snippets', [])
    if not code_snippets:
        return jsonify({"error": "No code snippets provided"}), 400
    
    # Create a new analysis task
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "type": "security",
        "code_snippets": code_snippets,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "results": None,
        "error": None
    }
    
    # Thread-safe operations - store task BEFORE starting thread
    with thread_lock:
        analysis_queue.append(task)
        pull_requests[task_id] = task
        save_tasks()  # Save new task
    
    # Start processing in background AFTER storing the task
    threading.Thread(target=process_security_analysis, args=(task_id,), daemon=True).start()
    
    return jsonify({
        "message": "Security analysis started",
        "task_id": task_id,
        "status": "queued"
    }), 202

def process_security_analysis(task_id):
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
            save_tasks()  # Save after modification
        
        # Initialize results
        security_issues = []
        errors = []
        
        if AGENT_SYSTEM_AVAILABLE and "security" in agents:
            try:
                # Create analysis context
                context = AnalysisContext(
                    repo_name="security_analysis",
                    pr_id=task_id,
                    code_snippets=[
                        CodeSnippet(
                            file_path=snippet["file_path"],
                            content=snippet["content"],
                            language=snippet.get("language", "unknown")
                        ) for snippet in task["code_snippets"]
                    ]
                )
                
                # Run security agent
                print(f"Running security analysis for task {task_id}")
                response = agents["security"].analyze(context)
                
                if response.success:
                    security_issues = [issue.model_dump() for issue in response.results]
                    print(f"Security analysis found {len(security_issues)} issues")
                else:
                    errors = response.errors
                    print(f"Security analysis failed: {errors}")
                    
            except Exception as e:
                error_msg = f"Agent analysis failed: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
        
        # If agent system not available or failed, use basic pattern matching
        if not security_issues and not errors:
            print("Using fallback security analysis")
            for snippet in task["code_snippets"]:
                issues = analyze_snippet_patterns(snippet)
                security_issues.extend(issues)
        
        # Generate decision based on actual results
        critical_count = sum(1 for i in security_issues if i.get("severity") == "critical")
        high_count = sum(1 for i in security_issues if i.get("severity") == "high")
        medium_count = sum(1 for i in security_issues if i.get("severity") == "medium")
        
        if critical_count > 0:
            decision = {
                "decision": "BLOCK",
                "risk_level": "critical",
                "summary": f"Found {critical_count} critical security issue{'s' if critical_count != 1 else ''}",
                "recommendations": ["Fix critical security issues immediately", "Review security best practices"]
            }
        elif high_count > 0:
            decision = {
                "decision": "REQUEST_CHANGES",
                "risk_level": "high", 
                "summary": f"Found {high_count} high severity security issue{'s' if high_count != 1 else ''}",
                "recommendations": ["Address high severity security issues", "Consider security review"]
            }
        elif medium_count > 0:
            decision = {
                "decision": "REQUEST_CHANGES",
                "risk_level": "medium",
                "summary": f"Found {medium_count} medium severity security issue{'s' if medium_count != 1 else ''}",
                "recommendations": ["Address medium severity issues when possible"]
            }
        else:
            decision = {
                "decision": "APPROVE",
                "risk_level": "low",
                "summary": "No significant security issues found",
                "recommendations": ["No immediate action required"]
            }
        
        # Generate results
        results = {
            "security_issues": security_issues,
            "total_issues": len(security_issues),
            "severity_breakdown": {
                "critical": critical_count,
                "high": high_count,
                "medium": medium_count,
                "low": len(security_issues) - critical_count - high_count - medium_count
            },
            "decision": decision,
            "errors": errors,
            "analysis_method": "agent_system" if AGENT_SYSTEM_AVAILABLE and "security" in agents else "pattern_matching"
        }
        
        with thread_lock:
            task["results"] = results
            task["status"] = "completed"
            task["completed_at"] = datetime.utcnow().isoformat()
            
            # Keep task in pull_requests for status checks
            pull_requests[task_id] = task
            
            # Add to history
            analysis_history.append(task.copy())
            save_tasks()  # Save after modification
        
        print(f"Security analysis task {task_id} completed successfully with {len(security_issues)} issues")
        
    except Exception as e:
        error_msg = f"Error processing security analysis task {task_id}: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        with thread_lock:
            if task_id in pull_requests:
                pull_requests[task_id]["status"] = "error"
                pull_requests[task_id]["error"] = error_msg
                save_tasks()  # Save after modification

def analyze_snippet_patterns(snippet):
    """Pattern-based security analysis fallback"""
    issues = []
    content = snippet["content"].lower()
    original_content = snippet["content"]
    lines = original_content.split('\n')
    
    # Security patterns to check
    patterns = [
        {
            "pattern": ["password", "secret", "key", "token"],
            "indicators": ["=", ":", "const", "var", "let"],
            "type": "Hardcoded Secret",
            "severity": "critical",
            "description": "Potential hardcoded credentials found"
        },
        {
            "pattern": ["admin", "root", "password"],
            "indicators": ["==", "===", "!="],
            "type": "Insecure Comparison", 
            "severity": "high",
            "description": "Direct string comparison may be vulnerable to timing attacks"
        },
        {
            "pattern": ["sql", "query", "execute"],
            "indicators": ["+", "format", "concatenat"],
            "type": "SQL Injection Risk",
            "severity": "high", 
            "description": "Potential SQL injection vulnerability"
        },
        {
            "pattern": ["eval", "exec", "system"],
            "indicators": ["(", "input", "request"],
            "type": "Code Injection Risk",
            "severity": "critical",
            "description": "Dynamic code execution with user input"
        }
    ]
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        for pattern_def in patterns:
            if any(p in line_lower for p in pattern_def["pattern"]) and \
               any(ind in line_lower for ind in pattern_def["indicators"]):
                issues.append({
                    "type": pattern_def["type"],
                    "severity": pattern_def["severity"],
                    "description": pattern_def["description"],
                    "line": i + 1,
                    "file": snippet["file_path"],
                    "confidence": 0.7,
                    "code_snippet": line.strip()
                })
    
    return issues

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
            "active_tasks": threading.active_count() - 1,
            "agent_system_available": AGENT_SYSTEM_AVAILABLE,
            "initialized_agents": list(agents.keys()) if agents else []
        }
    })

# Agent status endpoint
@app.route('/api/agents/status', methods=['GET'])
def get_agent_status():
    if not AGENT_SYSTEM_AVAILABLE:
        return jsonify({
            "status": "unavailable",
            "message": "Agent system not available",
            "agents": {}
        })
    
    status = {}
    for agent_name, config in agent_configs.items():
        is_initialized = agent_name in agents
        status[agent_name] = {
            "status": "active" if is_initialized else "not_initialized",
            "provider": config["provider"],
            "model": config["model"],
            "temperature": config["temperature"],
            "last_used": datetime.utcnow().isoformat() if is_initialized else None
        }
    
    return jsonify({
        "status": "available",
        "agents": status,
        "total_agents": len(status),
        "active_agents": len([a for a in status.values() if a["status"] == "active"])
    })

# Repository management
@app.route('/api/repositories', methods=['GET'])
def get_repositories():
    return jsonify({
        "repositories": repositories,
        "total": len(repositories)
    })

@app.route('/api/repositories', methods=['POST'])
def add_repository():
    data = request.json
    if not data or 'repo_url' not in data:
        return jsonify({"error": "Missing repo_url in request"}), 400
    
    repo = {
        "id": str(uuid.uuid4()),
        "url": data.get('repo_url'),
        "webhook_secret": data.get('webhook_secret', ''),
        "created_at": datetime.utcnow().isoformat(),
        "status": "active"
    }
    repositories.append(repo)
    return jsonify({"message": "Repository added successfully", "repository": repo}), 201

@app.route('/api/repositories/<id>', methods=['DELETE'])
def delete_repository(id):
    global repositories
    original_count = len(repositories)
    repositories = [r for r in repositories if r["id"] != id]
    
    if len(repositories) < original_count:
        return jsonify({"message": "Repository deleted successfully"})
    else:
        return jsonify({"error": "Repository not found"}), 404

# PR analysis endpoint
@app.route('/api/analysis/pr', methods=['POST'])
def analyze_pr():
    data = request.json
    if not data or 'pr_url' not in data:
        return jsonify({"error": "Missing pr_url in request"}), 400
    
    pr_url = data.get('pr_url')
    analysis_mode = data.get('analysis_mode', 'standard')
    
    # Create a new analysis task
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "type": "pr",
        "pr_url": pr_url,
        "status": "queued",
        "mode": analysis_mode,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "results": None,
        "error": None
    }
    
    # Thread-safe operations
    with thread_lock:
        analysis_queue.append(task)
        pull_requests[task_id] = task
        save_tasks()  # Save new task
    
    # Start processing in background
    threading.Thread(target=process_analysis_task, args=(task_id,), daemon=True).start()
    
    return jsonify({
        "message": "Analysis started",
        "task_id": task_id,
        "status": "queued",
        "pr_url": pr_url
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
            save_tasks()  # Save after modification

        results = {}
        errors = []
        
        if AGENT_SYSTEM_AVAILABLE and agents:
            try:
                # Extract repo name and PR ID from URL
                pr_url = task["pr_url"]
                if "/pull/" not in pr_url:
                    raise ValueError("Invalid PR URL format")
                
                parts = pr_url.split('/')
                if len(parts) < 7:
                    raise ValueError("Invalid GitHub PR URL")
                
                repo_owner = parts[-4]
                repo_name = parts[-3]
                pr_id = int(parts[-1])
                full_repo_name = f"{repo_owner}/{repo_name}"
                
                print(f"Processing PR analysis for {full_repo_name}#{pr_id}")
                
                # Initialize GitHub integration
                github = GitHubIntegration()
                
                # Get PR details
                pr_details = github.get_pr_details(full_repo_name, pr_id)
                if not pr_details:
                    raise Exception("Failed to get PR details from GitHub")
                
                # Get code snippets
                code_snippets = []
                for file_info in pr_details['files']:
                    # Skip removed files
                    if file_info['status'] == 'removed':
                        continue
                        
                    content = github.get_file_content(full_repo_name, file_info['filename'], pr_details['head_sha'])
                    if content:
                        snippet = CodeSnippet(
                            file_path=file_info['filename'],
                            content=content,
                            language=file_info['filename'].split('.')[-1] if '.' in file_info['filename'] else 'unknown'
                        )
                        code_snippets.append(snippet)
                
                print(f"Extracted {len(code_snippets)} code snippets")
                
                # Create analysis context
                context = AnalysisContext(
                    repo_name=full_repo_name,
                    pr_id=str(pr_id),
                    author=pr_details['author'],
                    commit_history=pr_details['commits_data'],
                    previous_issues=[],
                    code_snippets=code_snippets
                )
                
                # Initialize and run agent system with CPU device
                agent_system = AgentSystem(device="cpu")
                
                print(f"Starting workflow analysis for {full_repo_name}#{pr_id}")
                print(f"Code snippets: {len(code_snippets)}")
                
                # Run analysis
                start_time = time.time()
                analysis_results = agent_system.analyze_pull_request(context)
                duration = time.time() - start_time
                
                print(f"Analysis completed in {duration:.2f} seconds")
                print(f"Security issues: {len(analysis_results.get('security_issues', []))}")
                print(f"Quality issues: {len(analysis_results.get('quality_issues', []))}")
                print(f"Logic issues: {len(analysis_results.get('logic_issues', []))}")
                print(f"Decision: {analysis_results.get('decision', {}).get('decision', 'UNKNOWN')}")
                
                # Format results for frontend - Fixed result handling
                security_issues = analysis_results.get("security_issues", [])
                quality_issues = analysis_results.get("quality_issues", [])
                logic_issues = analysis_results.get("logic_issues", [])
                
                results = {
                    "security_issues": [issue.model_dump() for issue in security_issues],
                    "quality_issues": [issue.model_dump() for issue in quality_issues],
                    "logic_issues": logic_issues,  # Already dictionaries from LogicAgent
                    "decision": analysis_results.get("decision", {}),
                    "pr_details": pr_details,
                    "analysis_duration": duration,
                    "total_issues": len(security_issues) + len(quality_issues) + len(logic_issues)
                }
                
                print(f"Analysis results: {len(security_issues)} security, {len(quality_issues)} quality, {len(logic_issues)} logic issues")
                
            except Exception as e:
                error_msg = f"Error during PR analysis: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                errors.append(error_msg)
                results = {"error": error_msg, "errors": errors}
        else:
            # Agent system not available
            error_msg = "Agent system not available - cannot perform full PR analysis"
            print(error_msg)
            results = {
                "error": error_msg,
                "security_issues": [],
                "quality_issues": [],
                "logic_issues": [],
                "decision": {
                    "decision": "MANUAL_REVIEW",
                    "risk_level": "unknown",
                    "summary": "Analysis not available - manual review required",
                    "recommendations": ["Set up agent system for automated analysis"]
                }
            }
        
        with thread_lock:
            task["results"] = results
            task["status"] = "completed"
            task["completed_at"] = datetime.utcnow().isoformat()
            
            # Keep task in pull_requests for status checks
            pull_requests[task_id] = task
            
            # Add to history
            analysis_history.append(task.copy())
            save_tasks()  # Save after modification
            
        print(f"Analysis task {task_id} completed")
        
    except Exception as e:
        error_msg = f"Error processing analysis task {task_id}: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        with thread_lock:
            if task_id in pull_requests:
                pull_requests[task_id]["status"] = "error"
                pull_requests[task_id]["error"] = error_msg
                save_tasks()  # Save after modification

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
    
    # Generate metrics from actual data
    issue_counts = {"security": 0, "quality": 0, "logic": 0}
    total_duration = 0
    successful_analyses = 0
    
    for t in completed_analyses:
        if t.get("results") and not t["results"].get("error"):
            successful_analyses += 1
            
            # Count issues from actual results
            if "security_issues" in t["results"]:
                issue_counts["security"] += len(t["results"]["security_issues"])
            if "quality_issues" in t["results"]:
                issue_counts["quality"] += len(t["results"]["quality_issues"])
            if "logic_issues" in t["results"]:
                issue_counts["logic"] += len(t["results"]["logic_issues"])
            
            # Calculate duration if available
            if t.get("started_at") and t.get("completed_at"):
                try:
                    start = datetime.fromisoformat(t["started_at"])
                    end = datetime.fromisoformat(t["completed_at"])
                    duration = (end - start).total_seconds()
                    total_duration += duration
                except ValueError:
                    pass
    
    # Calculate success rate and average duration
    success_rate = (successful_analyses / len(completed_analyses) * 100) if completed_analyses else 0
    avg_duration = (total_duration / successful_analyses) if successful_analyses > 0 else 0
    
    return jsonify({
        "time_range": time_range,
        "analysis_count": len(completed_analyses),
        "successful_analyses": successful_analyses,
        "failed_analyses": len(completed_analyses) - successful_analyses,
        "issue_types": issue_counts,
        "total_issues": sum(issue_counts.values()),
        "success_rate": round(success_rate, 1),
        "avg_duration": round(avg_duration, 1)
    })

# Agent configuration
@app.route('/api/agents/config', methods=['GET'])
def get_agent_config():
    return jsonify({
        "configs": agent_configs,
        "agent_system_available": AGENT_SYSTEM_AVAILABLE
    })

@app.route('/api/agents/config', methods=['POST'])
def update_agent_config():
    data = request.json
    if not data:
        return jsonify({"error": "No configuration data provided"}), 400
    
    updated_agents = []
    for agent, config in data.items():
        if agent in agent_configs:
            agent_configs[agent].update(config)
            updated_agents.append(agent)
    
    return jsonify({
        "message": "Agent configurations updated",
        "updated_agents": updated_agents
    })

# Settings endpoints
@app.route('/api/settings/github', methods=['GET'])
def get_github_settings():
    # Don't expose sensitive data
    safe_settings = settings["github"].copy()
    if "token" in safe_settings:
        safe_settings["token"] = "***" if safe_settings["token"] else ""
    return jsonify(safe_settings)

@app.route('/api/settings/github', methods=['POST'])
def update_github_settings():
    data = request.json
    if not data:
        return jsonify({"error": "No settings data provided"}), 400
    
    settings["github"].update(data)
    return jsonify({"message": "GitHub settings updated"})

@app.route('/api/settings/notifications', methods=['POST'])
def update_notification_settings():
    data = request.json
    if not data:
        return jsonify({"error": "No settings data provided"}), 400
    
    settings["notifications"].update(data)
    return jsonify({"message": "Notification settings updated"})

@app.route('/api/settings/security', methods=['POST'])
def update_security_settings():
    data = request.json
    if not data:
        return jsonify({"error": "No settings data provided"}), 400
    
    settings["security"].update(data)
    return jsonify({"message": "Security settings updated"})

# Modify the task status endpoint
@app.route('/api/analysis/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    # Check active tasks first
    if task_id in pull_requests:
        task = pull_requests[task_id]
        return jsonify({
            "task_id": task_id,
            "status": task["status"],
            "created_at": task["created_at"],
            "started_at": task.get("started_at"),
            "completed_at": task.get("completed_at"),
            "results": task.get("results"),
            "error": task.get("error")
        })
    
    # Check historical tasks
    for task in analysis_history:
        if task["id"] == task_id:
            return jsonify({
                "task_id": task_id,
                "status": "completed",
                "created_at": task["created_at"],
                "started_at": task.get("started_at"),
                "completed_at": task.get("completed_at"),
                "results": task.get("results"),
                "error": task.get("error")
            })
    
    return jsonify({"error": "Task not found"}), 404

def background_processor():
    """Continuously process tasks in the background"""
    print("Background processor started")
    while True:
        try:
            # Process analysis queue
            if analysis_queue:
                with thread_lock:
                    if analysis_queue:  # Double check after acquiring lock
                        task = analysis_queue.pop(0)
                        save_tasks()  # Save after modification
                    else:
                        task = None
                
                if task:
                    task_id = task["id"]
                    print(f"Processing task {task_id} from background queue")
                    
                    if task["type"] == "pr":
                        process_analysis_task(task_id)
                    elif task["type"] == "security":
                        process_security_analysis(task_id)
            
            time.sleep(1)
        except Exception as e:
            print(f"Background processor error: {str(e)}")
            time.sleep(5)

if __name__ == '__main__':
    # Load environment variables
    port = int(os.getenv('BACKEND_PORT', 8000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"Starting PatchPilot Backend on port {port}")
    print(f"Debug mode: {debug}")
    print(f"Agent system available: {AGENT_SYSTEM_AVAILABLE}")
    if AGENT_SYSTEM_AVAILABLE:
        print(f"Initialized agents: {list(agents.keys())}")
    
    # Only start the main app in the main thread
    if not is_running_from_reloader():
        # Start background processor in main thread
        threading.Thread(target=background_processor, daemon=True).start()
    
    # Start the server without reloader
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)