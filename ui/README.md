# Web UI for SRE Autonomous Agent

A modern web interface for the SRE Autonomous Agent, providing real-time incident monitoring, alert submission, and postmortem management.

## Features

### 🏠 Dashboard
- Real-time incident statistics
- Activity timeline
- Alert source distribution
- Quick access to recent incidents

### 🚨 Alert Submission
Three ways to submit alerts:
1. **Manual Entry** - Fill in a form with alert details
2. **Template-based** - Use pre-configured example alerts
3. **JSON Upload** - Upload alert files directly

### 📊 Incident Monitoring
- Visual timeline of all incidents
- Filterable incident list
- Detailed incident views
- Status tracking

### 📝 Postmortems
- Browse all generated postmortems
- Download reports in Markdown format
- Search and filter capabilities
- Timeline visualization

### ⚙️ Settings
- Environment configuration
- Guardrails management
- API key configuration
- Notification settings

## Technology Stack

- **Frontend**: Streamlit (Python-based web framework)
- **Backend**: FastAPI (REST API)
- **Visualization**: Plotly, Pandas
- **Data**: File-based storage (JSON, Markdown)

## Getting Started

### Prerequisites
- Python 3.11+
- Dependencies installed: `pip install -r requirements.txt`
- Environment variables configured in `.env`

### Launch UI

```bash
# Start Streamlit UI
./run-ui.sh

# Or manually
streamlit run ui/app.py --server.port 8501
```

Access at: **http://localhost:8501**

### Launch API Server

```bash
# Start FastAPI backend
./run-api.sh

# Or manually
uvicorn ui.api:app --host 0.0.0.0 --port 8000 --reload
```

API docs at: **http://localhost:8000/docs**

## API Endpoints

### Core Endpoints

- `POST /api/alerts` - Submit new alert
- `GET /api/incidents` - List all incidents
- `GET /api/incidents/{id}` - Get incident details
- `GET /api/stats` - Get system statistics
- `GET /api/alerts/examples` - Get example templates

### Example: Submit Alert

```bash
curl -X POST http://localhost:8000/api/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "status": "firing",
    "commonLabels": {
      "alertname": "PodCrashLooping",
      "severity": "critical",
      "namespace": "production",
      "pod": "myapp-7d4f9c6b5-abc123"
    },
    "commonAnnotations": {
      "description": "Pod is crash looping",
      "summary": "CRITICAL: PodCrashLooping"
    },
    "startsAt": "2026-01-01T00:00:00Z"
  }'
```

## Architecture

```
┌─────────────────┐
│  Streamlit UI   │ (Port 8501)
│   (Frontend)    │
└────────┬────────┘
         │
         │ Direct Python calls
         │
         ▼
┌─────────────────┐
│  FastAPI Server │ (Port 8000)
│   (REST API)    │
└────────┬────────┘
         │
         │ Invokes
         ▼
┌─────────────────┐
│  LangGraph App  │
│  (Agent Logic)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  File System    │
│ (Postmortems,   │
│   Alerts)       │
└─────────────────┘
```

## Customization

### Styling
Modify the CSS in `ui/app.py` to change colors, fonts, and layout.

### Components
Add new pages by creating functions in `ui/app.py`:
```python
def render_my_new_page():
    st.title("My New Page")
    # Your content here
```

### API Routes
Add new endpoints in `ui/api.py`:
```python
@app.get("/api/my-endpoint")
async def my_endpoint():
    return {"data": "value"}
```

## Troubleshooting

### Port Already in Use
```bash
# Kill process on port 8501
lsof -ti:8501 | xargs kill -9

# Or use different port
streamlit run ui/app.py --server.port 8502
```

### Missing Dependencies
```bash
pip install -r requirements.txt
```

### Can't Find Postmortems
Ensure the `postmortems/` directory exists and contains `.md` files.

## Future Enhancements

- [ ] Real-time WebSocket updates
- [ ] User authentication and RBAC
- [ ] Slack integration
- [ ] Advanced filtering and search
- [ ] Metrics dashboards with Prometheus
- [ ] Log viewer with Loki integration
- [ ] Approval workflow UI
- [ ] Multi-cluster support

## Contributing

To add new features to the UI:
1. Create feature branch: `git checkout -b feature/ui-enhancement`
2. Make changes to `ui/app.py` or `ui/api.py`
3. Test locally with `./run-ui.sh`
4. Submit pull request

## License

Same as parent project - see main README.md
