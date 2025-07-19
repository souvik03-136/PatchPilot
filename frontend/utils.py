import os
import requests
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get backend URL from environment
BACKEND_URL = os.getenv("BACKEND_URL")

def check_backend_connection():
    """Check if backend is available"""
    if not BACKEND_URL:
        return False
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def call_backend_api(endpoint, data=None, method="GET"):
    """Make API call to backend"""
    if not BACKEND_URL:
        return {"status": "error", "message": "Backend URL not configured"}
    
    try:
        url = f"{BACKEND_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            return {"status": "error", "message": f"Unsupported HTTP method: {method}"}
        
        # Handle both 200 (OK) and 202 (Accepted) as success
        if response.status_code in [200, 202]:
            return {"status": "success", "data": response.json()}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}
    
def init_session_state():
    """Initialize session state variables"""
    if 'backend_connected' not in st.session_state:
        st.session_state.backend_connected = check_backend_connection()
    if 'analysis_history' not in st.session_state:
        st.session_state.analysis_history = []
    if 'current_analysis' not in st.session_state:
        st.session_state.current_analysis = None
    if 'backend_url' not in st.session_state:
        st.session_state.backend_url = BACKEND_URL
    if 'refresh_triggered' not in st.session_state:
        st.session_state.refresh_triggered = False

def apply_custom_styles():
    """Inject custom CSS styles"""
    st.markdown("""
    <style>
        .main-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .critical-alert {
            background: #fee;
            border-left: 4px solid #dc3545;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .warning-alert {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .success-alert {
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .info-alert {
            background: #d1ecf1;
            border-left: 4px solid #17a2b8;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .agent-status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
            margin: 2px;
        }
        .agent-active {
            background: #28a745;
            color: white;
        }
        .agent-idle {
            background: #6c757d;
            color: white;
        }
        .agent-error {
            background: #dc3545;
            color: white;
        }
        .loading-spinner {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100px;
        }
    </style>
    """, unsafe_allow_html=True)