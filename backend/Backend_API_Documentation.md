# PatchPilot Backend API Documentation

## Overview

The backend is built with Flask and provides RESTful APIs for managing repositories, analyzing code, and monitoring system metrics.

## Table of Contents

1. [Architecture](#architecture)
2. [Getting Started](#getting-started)
3. [API Endpoints](#api-endpoints)
4. [Data Models](#data-models)
5. [Configuration](#configuration)
6. [Error Handling](#error-handling)
7. [Development](#development)

## Architecture

### Core Components

- **Flask Web Framework**: Main application server
- **In-Memory Storage**: Temporary data storage for repositories, pull requests, and analysis results
- **Multi-threaded Analysis**: Background processing for code analysis tasks
- **AI Agent System**: Configurable AI agents for different analysis types
- **CORS Support**: Cross-origin resource sharing enabled

### Key Features

- Real-time code analysis
- Security vulnerability detection
- Code quality assessment
- Logic error identification
- System monitoring and metrics
- Repository management
- Configurable AI agents

## Getting Started

### Prerequisites

- Python 3.11+
- Flask 2.3.3+
- Required dependencies (see requirements.txt)

### Installation

```bash
cd PatchPilot/backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export BACKEND_PORT=8000
export DEBUG=True

# Run the application
python app.py
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_PORT` | 8000 | Port number for the backend server |
| `DEBUG` | True | Enable/disable debug mode |

## API Endpoints

### Health & System Endpoints

#### GET `/health`
Health check endpoint to verify service availability.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-07-16T10:30:00.000Z"
}
```

#### GET `/`
Root endpoint providing API information and available endpoints.

**Response:**
```json
{
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
}
```

#### GET `/api`
API information endpoint with detailed endpoint descriptions.

**Response:**
```json
{
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
}
```

### System Metrics

#### GET `/api/metrics`
Retrieve system performance metrics and application statistics.

**Response:**
```json
{
  "system": {
    "cpu": 25.5,
    "memory": {
      "total": 8589934592,
      "available": 4294967296,
      "percent": 50.0
    },
    "disk": {
      "total": 1000000000000,
      "used": 500000000000,
      "percent": 50.0
    }
  },
  "application": {
    "repositories": 5,
    "pull_requests": 10,
    "queue_size": 2,
    "active_tasks": 3
  }
}
```

### Repository Management

#### GET `/api/repositories`
List all registered repositories.

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "url": "https://github.com/user/repo",
    "webhook_secret": "secret123",
    "created_at": "2025-07-16T10:00:00.000Z"
  }
]
```

#### POST `/api/repositories`
Add a new repository to the system.

**Request Body:**
```json
{
  "repo_url": "https://github.com/user/repo",
  "webhook_secret": "your-webhook-secret"
}
```

**Response:**
```json
{
  "message": "Repository added",
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### DELETE `/api/repositories/{id}`
Remove a repository from the system.

**Response:**
```json
{
  "message": "Repository deleted"
}
```

### Code Analysis

#### POST `/api/analysis/pr`
Analyze a pull request for security, quality, and logic issues.

**Request Body:**
```json
{
  "pr_url": "https://github.com/user/repo/pull/123",
  "analysis_mode": "standard"
}
```

**Response:**
```json
{
  "message": "Analysis started",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

#### POST `/api/analysis/security`
Perform security-focused analysis on code snippets.

**Request Body:**
```json
{
  "code_snippets": [
    {
      "file_path": "src/config.py",
      "content": "admin_pass = 'superSecret123'\nif password == user_input:\n    return True"
    }
  ]
}
```

**Response:**
```json
{
  "message": "Security analysis started",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

#### GET `/api/analysis/status/{task_id}`
Check the status of an analysis task.

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2025-07-16T10:00:00.000Z",
  "started_at": "2025-07-16T10:00:05.000Z",
  "completed_at": "2025-07-16T10:00:10.000Z",
  "results": {
    "security_issues": [...],
    "quality_issues": [...],
    "logic_issues": [...],
    "decision": {...}
  }
}
```

### AI Agent Management

#### GET `/api/agents/status`
Get the status of all AI agents.

**Response:**
```json
{
  "security": {
    "status": "active",
    "provider": "gemini",
    "model": "gemini-1.5-flash",
    "last_used": "2025-07-16T10:00:00.000Z"
  },
  "quality": {
    "status": "active",
    "provider": "gemini",
    "model": "gemini-1.5-flash",
    "last_used": "2025-07-16T10:00:00.000Z"
  },
  "logic": {
    "status": "active",
    "provider": "gemini",
    "model": "gemini-1.5-flash",
    "last_used": "2025-07-16T10:00:00.000Z"
  },
  "context": {
    "status": "active",
    "provider": "gemini",
    "model": "gemini-1.5-pro",
    "last_used": "2025-07-16T10:00:00.000Z"
  },
  "decision": {
    "status": "active",
    "provider": "gemini",
    "model": "gemini-1.5-pro",
    "last_used": "2025-07-16T10:00:00.000Z"
  }
}
```

#### GET `/api/agents/config`
Get current AI agent configurations.

**Response:**
```json
{
  "security": {
    "provider": "gemini",
    "model": "gemini-1.5-flash",
    "temperature": 0.2
  },
  "quality": {
    "provider": "gemini",
    "model": "gemini-1.5-flash",
    "temperature": 0.3
  },
  "logic": {
    "provider": "gemini",
    "model": "gemini-1.5-flash",
    "temperature": 0.4
  },
  "context": {
    "provider": "gemini",
    "model": "gemini-1.5-pro",
    "temperature": 0.1
  },
  "decision": {
    "provider": "gemini",
    "model": "gemini-1.5-pro",
    "temperature": 0.1
  }
}
```

#### POST `/api/agents/config`
Update AI agent configurations.

**Request Body:**
```json
{
  "security": {
    "provider": "gemini",
    "model": "gemini-1.5-flash",
    "temperature": 0.2
  },
  "quality": {
    "temperature": 0.4
  }
}
```

**Response:**
```json
{
  "message": "Agent configurations updated"
}
```

### Analytics

#### GET `/api/analytics`
Get analytics data for specified time range.

**Query Parameters:**
- `range`: Time range (24h, 7d, 30d) - default: 7d

**Response:**
```json
{
  "time_range": "7d",
  "analysis_count": 25,
  "issue_types": {
    "security": 15,
    "quality": 30,
    "logic": 10
  },
  "success_rate": 95.0,
  "avg_duration": 8.5
}
```

### Settings Management

#### POST `/api/settings/github`
Update GitHub integration settings.

**Request Body:**
```json
{
  "token": "ghp_newtoken",
  "webhook_secret": "newsecret"
}
```

**Response:**
```json
{
  "message": "GitHub settings updated"
}
```

#### POST `/api/settings/notifications`
Update notification settings.

**Request Body:**
```json
{
  "email": "admin@example.com",
  "slack_webhook": "https://hooks.slack.com/services/..."
}
```

**Response:**
```json
{
  "message": "Notification settings updated"
}
```

#### POST `/api/settings/security`
Update security settings.

**Request Body:**
```json
{
  "block_critical": true,
  "require_2fa": true
}
```

**Response:**
```json
{
  "message": "Security settings updated"
}
```

## Data Models

### Repository Model
```json
{
  "id": "string (UUID)",
  "url": "string",
  "webhook_secret": "string",
  "created_at": "string (ISO 8601)"
}
```

### Analysis Task Model
```json
{
  "id": "string (UUID)",
  "pr_url": "string",
  "status": "string (queued|processing|completed|error)",
  "mode": "string",
  "created_at": "string (ISO 8601)",
  "started_at": "string (ISO 8601)",
  "completed_at": "string (ISO 8601)",
  "results": "object",
  "error": "string"
}
```

### Security Issue Model
```json
{
  "type": "string",
  "severity": "string (low|medium|high|critical)",
  "description": "string",
  "line": "number",
  "file": "string",
  "confidence": "number (0-1)"
}
```

### Quality Issue Model
```json
{
  "type": "string",
  "severity": "string (low|medium|high|critical)",
  "description": "string",
  "line": "number",
  "file": "string"
}
```

### Logic Issue Model
```json
{
  "file": "string",
  "analysis": "string",
  "suggestions": ["string"]
}
```

### Decision Model
```json
{
  "decision": "string (APPROVE|REQUEST_CHANGES|REJECT)",
  "risk_level": "string (low|medium|high|critical)",
  "summary": "string",
  "recommendations": ["string"]
}
```

## Configuration

### AI Agent Configuration
The system supports five types of AI agents:

1. **Security Agent**: Focuses on vulnerability detection
2. **Quality Agent**: Analyzes code quality and maintainability
3. **Logic Agent**: Identifies logical errors and improvements
4. **Context Agent**: Provides contextual understanding
5. **Decision Agent**: Makes final approval/rejection decisions

### Default Agent Settings
```json
{
  "security": {
    "provider": "gemini",
    "model": "gemini-1.5-flash",
    "temperature": 0.2
  },
  "quality": {
    "provider": "gemini",
    "model": "gemini-1.5-flash",
    "temperature": 0.3
  },
  "logic": {
    "provider": "gemini",
    "model": "gemini-1.5-flash",
    "temperature": 0.4
  },
  "context": {
    "provider": "gemini",
    "model": "gemini-1.5-pro",
    "temperature": 0.1
  },
  "decision": {
    "provider": "gemini",
    "model": "gemini-1.5-pro",
    "temperature": 0.1
  }
}
```

### Security Analysis Rules

The security analyzer checks for:

1. **Hardcoded Secrets**: Detects hardcoded passwords, API keys, and tokens
2. **Insecure Comparisons**: Identifies direct string comparisons that may be vulnerable to timing attacks
3. **SQL Injection**: Looks for potential SQL injection vulnerabilities
4. **XSS Vulnerabilities**: Checks for cross-site scripting risks
5. **Authentication Issues**: Identifies weak authentication patterns

## Error Handling

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `202 Accepted`: Request accepted for processing
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

### Error Response Format
```json
{
  "error": "Error message",
  "details": "Additional error details (optional)"
}
```

## Development

### Thread Safety
The application uses threading locks to ensure thread-safe access to shared data structures:
- `repositories`: List of registered repositories
- `pull_requests`: Dictionary of analysis tasks
- `analysis_history`: Historical analysis data
- `analysis_queue`: Queue of pending analysis tasks

### Background Processing
Analysis tasks are processed in background threads to avoid blocking the main application. Each task goes through the following states:
1. `queued`: Task created and added to queue
2. `processing`: Task being analyzed
3. `completed`: Analysis finished successfully
4. `error`: Analysis failed

### Monitoring
The system provides comprehensive monitoring through:
- System metrics (CPU, memory, disk usage)
- Application metrics (task counts, queue size)
- Agent status monitoring
- Analysis history and analytics

### Testing
To test the API endpoints:

```bash
# Health check
curl http://localhost:8000/health

# Start PR analysis
curl -X POST http://localhost:8000/api/analysis/pr \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/user/repo/pull/123"}'

# Check analysis status
curl http://localhost:8000/api/analysis/status/{task_id}

# Get system metrics
curl http://localhost:8000/api/metrics
```


For production deployment, consider using a WSGI server like Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Security Considerations

1. **Input Validation**: All endpoints validate input data
2. **CORS Configuration**: CORS is configured for specific origins in production
3. **Rate Limiting**: Consider implementing rate limiting for production use
4. **Authentication**: Add authentication middleware for production deployment
5. **Logging**: Implement comprehensive logging for security monitoring
6. **Environment Variables**: Use environment variables for sensitive configuration