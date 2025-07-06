### Frontend Brief: PATCHPILOT AI Dashboard

#### Overview
The PatchPilot AI frontend is a Streamlit-based dashboard that provides real-time monitoring and management of code quality and security analysis. It connects to a backend API to fetch data, perform analyses, and manage system configurations. The interface features a modern, responsive design with custom styling and intuitive navigation.

#### Key Features
1. **Dashboard**: System metrics, agent status, and repository overview
2. **PR Analysis**: Analyze GitHub pull requests for security/quality issues
3. **Repository Manager**: Connect/disconnect code repositories
4. **Analytics**: Visualize issue trends and metrics
5. **Agent Configuration**: Tune AI analysis parameters
6. **System Settings**: Configure integrations and security

#### Required Backend Endpoints
The frontend expects the backend to implement these RESTful endpoints:

| Endpoint | Method | Parameters | Response | Purpose |
|----------|--------|------------|----------|---------|
| `/health` | GET | - | 200 OK | Health check |
| `/api/metrics` | GET | - | System metrics | Dashboard stats |
| `/api/agents/status` | GET | - | Agent statuses | Agent monitoring |
| `/api/repositories` | GET | - | Repository list | Repo management |
| `/api/repositories` | POST | JSON: {repo_url, webhook_secret} | Success message | Add repository |
| `/api/repositories/{id}` | DELETE | - | Success message | Remove repository |
| `/api/analysis/pr` | POST | JSON: {pr_url, analysis_mode} | Analysis results | PR analysis |
| `/api/analytics` | GET | ?range={time_range} | Analytics data | Metrics visualization |
| `/api/agents/config` | GET | - | Agent configurations | Get agent settings |
| `/api/agents/config` | POST | JSON: agent config | Success message | Update agent settings |
| `/api/settings/github` | POST | JSON: github settings | Success message | Save GitHub config |
| `/api/settings/notifications` | POST | JSON: notification settings | Success message | Save notifications |
| `/api/settings/security` | POST | JSON: security settings | Success message | Save security config |

#### Session State Management
The frontend maintains these session variables:
- `backend_connected`: Connection status to backend
- `analysis_history`: List of previous PR analyses
- `current_analysis`: Results of latest analysis
- `backend_url`: Current backend API endpoint

#### File Structure
```
frontend/
├── .env                    # Environment variables
├── app.py                  # Main application
├── utils.py                # Helper functions
├── components/
│   └── sidebar.py          # Navigation sidebar
└── pages/
    ├── dashboard.py        # Dashboard view
    ├── pr_analysis.py      # PR analysis tools
    ├── repository_manager.py # Repo management
    ├── analytics.py        # Data visualization
    ├── agent_configuration.py # Agent settings
    └── settings.py         # System configuration
```

#### Environment Variables
Create `.env` file with:
```env
# Backend configuration
BACKEND_URL=http://localhost:8000
```

#### How to Run
1. **Prerequisites**:
   - Python 3.8+
   - Streamlit, requests, python-dotenv packages

2. **Install dependencies**:
   ```bash
   pip install streamlit requests python-dotenv
   ```

3. **Set up environment**:
   - Create `.env` file with your backend URL
   - Ensure backend server is running

4. **Run the application**:
   ```bash
   streamlit run app.py
   ```

5. **Access the dashboard**:
   - Open browser to `http://localhost:8501`

#### Development Notes
1. **Custom Styling**:
   - CSS styles are injected via `utils.apply_custom_styles()`
   - Includes custom cards, alerts, and status indicators

2. **Error Handling**:
   - All API calls include try/except blocks
   - User-friendly error messages displayed
   - Connection status visible in sidebar

3. **Performance**:
   - Heavy operations show progress indicators
   - Session state minimizes redundant API calls
   - Components lazy-load data on demand

4. **Responsive Design**:
   - Uses Streamlit columns for layout
   - Adapts to different screen sizes
   - Mobile-friendly components

#### Testing
1. **Connection Test**:
   - Use sidebar to verify backend connection
   - Update backend URL if needed

2. **Sample Workflow**:
   - Add test repository in Repository Manager
   - Analyze sample PR in PR Analysis
   - Verify results display correctly
   - Check agent status updates

#### Troubleshooting
- **Backend not connected**:
  - Verify backend server is running
  - Check `.env` file configuration
  - Test connection via sidebar

- **Missing data**:
  - Confirm backend implements required endpoints
  - Check browser console for errors

- **Styling issues**:
  - Clear browser cache
  - Verify custom CSS injection

