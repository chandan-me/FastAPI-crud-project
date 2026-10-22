from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import time
from typing import Dict, List
import uvicorn

# =====================================================================
# PY-EUREKA DISCOVERY SERVICE & REGISTRY SERVER (Port 8761)
# 
# This service acts as the central service registry (similar to Netflix Eureka).
# It maintains an in-memory directory of active service instances and exposes:
#   1. Registry REST API (/eureka/apps) for registration, heartbeats, and queries.
#   2. Stale Lease Eviction: Automatically cleans up offline services.
#   3. Visual Dashboard: A premium HTML interface displaying active services.
# =====================================================================

app = FastAPI(
    title="Demo Discovery Server", 
    description="Netflix Eureka-compatible Service Discovery & Registry"
)

# Registry Storage
# Format: { app_name: { instance_id: { host, port, status, last_heartbeat } } }
REGISTRY: Dict[str, Dict[str, dict]] = {}
START_TIME = time.time()

class InstanceModel(BaseModel):
    instance_id: str
    host: str
    port: int
    status: str = "UP"

# --- Eviction Task (Stale Lease Cleanup) ---
def evict_stale_services():
    """Loops through all instances and evicts those whose heartbeats are stale (> 30s)."""
    now = time.time()
    for app_name in list(REGISTRY.keys()):
        for inst_id in list(REGISTRY[app_name].keys()):
            inst = REGISTRY[app_name][inst_id]
            # If heartbeat is older than 30 seconds, evict
            if now - inst["last_heartbeat"] > 30:
                print(f"[Discovery] Evicting stale instance {inst_id} ({app_name})")
                REGISTRY[app_name].pop(inst_id)
        # Clean up empty app names
        if not REGISTRY[app_name]:
            REGISTRY.pop(app_name)

# Background task wrapper
@app.middleware("http")
async def run_eviction_task(request, call_next):
    evict_stale_services()
    return await call_next(request)


# --- Eureka REST API Endpoints ---

@app.post("/eureka/apps/{app_name}", status_code=status.HTTP_201_CREATED)
def register_instance(app_name: str, instance: InstanceModel):
    """Registers a new microservice instance in the registry."""
    app_key = app_name.upper()
    if app_key not in REGISTRY:
        REGISTRY[app_key] = {}
        
    REGISTRY[app_key][instance.instance_id] = {
        "host": instance.host,
        "port": instance.port,
        "status": instance.status,
        "last_heartbeat": time.time()
    }
    print(f"[Discovery] Registered service: {app_key} -> {instance.host}:{instance.port} (ID: {instance.instance_id})")
    return {"message": "Registered successfully"}

@app.put("/eureka/apps/{app_name}/{instance_id}")
def heartbeat(app_name: str, instance_id: str):
    """Renews instance lease (Heartbeat ping)."""
    app_key = app_name.upper()
    if app_key not in REGISTRY or instance_id not in REGISTRY[app_key]:
        raise HTTPException(status_code=404, detail="Instance not found")
        
    REGISTRY[app_key][instance_id]["last_heartbeat"] = time.time()
    REGISTRY[app_key][instance_id]["status"] = "UP" # Renew status
    return {"message": "Heartbeat renewed"}

@app.delete("/eureka/apps/{app_name}/{instance_id}")
def deregister_instance(app_name: str, instance_id: str):
    """Deregisters a microservice instance on exit/shutdown."""
    app_key = app_name.upper()
    if app_key in REGISTRY and instance_id in REGISTRY[app_key]:
        REGISTRY[app_key].pop(instance_id)
        print(f"[Discovery] Deregistered service: {app_key} (ID: {instance_id})")
        if not REGISTRY[app_key]:
            REGISTRY.pop(app_key)
        return {"message": "Deregistered successfully"}
    raise HTTPException(status_code=404, detail="Instance not found")

@app.get("/eureka/apps")
def get_apps():
    """Returns directory of all active service registrations."""
    # Format compatible with simple gateway resolution
    clean_directory = {}
    for app_name, instances in REGISTRY.items():
        clean_directory[app_name] = []
        for inst_id, details in instances.items():
            clean_directory[app_name].append({
                "instance_id": inst_id,
                "url": f"http://{details['host']}:{details['port']}",
                "status": details["status"]
            })
    return clean_directory


# --- Eureka HTML Dashboard Page ---

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serves a premium visual dashboard summarizing active service nodes."""
    uptime_seconds = int(time.time() - START_TIME)
    uptime_str = f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s"
    
    # Compile active instances table rows
    rows_html = ""
    if not REGISTRY:
        rows_html = """
        <tr>
            <td colspan="5" style="text-align: center; color: rgba(255,255,255,0.4); padding: 2rem;">
                No services currently registered.
            </td>
        </tr>
        """
    else:
        now = time.time()
        for app_name, instances in REGISTRY.items():
            for inst_id, details in instances.items():
                last_seen = int(now - details["last_heartbeat"])
                rows_html += f"""
                <tr>
                    <td><strong>{app_name}</strong></td>
                    <td class="code">{inst_id}</td>
                    <td><a href="http://{details['host']}:{details['port']}" target="_blank">http://{details['host']}:{details['port']}</a></td>
                    <td><span class="status-badge status-up">{details['status']}</span></td>
                    <td>{last_seen}s ago</td>
                </tr>
                """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Demo Discovery Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-gradient: linear-gradient(135deg, #0b132b 0%, #1c2541 100%);
                --card-bg: rgba(28, 37, 65, 0.6);
                --teal-accent: #35a29f;
                --teal-hover: #2b8481;
                --green-up: #4cd137;
                --text-main: #f1f6f9;
                --border-color: rgba(255, 255, 255, 0.05);
            }}
            body {{
                margin: 0;
                padding: 2rem;
                font-family: 'Outfit', sans-serif;
                background: var(--bg-gradient);
                color: var(--text-main);
                min-height: 100vh;
            }}
            .container {{
                max-width: 1100px;
                margin: 0 auto;
            }}
            header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 1.5rem;
                margin-bottom: 2rem;
            }}
            h1 {{
                margin: 0;
                font-size: 2rem;
                font-weight: 700;
                letter-spacing: -0.5px;
            }}
            h1 span {{
                color: var(--teal-accent);
            }}
            .system-stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }}
            .stat-card {{
                background: var(--card-bg);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            }}
            .stat-title {{
                font-size: 0.85rem;
                color: var(--teal-accent);
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 0.5rem;
                font-weight: 600;
            }}
            .stat-value {{
                font-size: 1.5rem;
                font-weight: 700;
            }}
            .registry-card {{
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 2rem;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            }}
            h2 {{
                margin-top: 0;
                margin-bottom: 1.5rem;
                font-size: 1.35rem;
                font-weight: 600;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                text-align: left;
            }}
            th, td {{
                padding: 1rem;
                border-bottom: 1px solid var(--border-color);
            }}
            th {{
                color: var(--teal-accent);
                font-weight: 600;
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            tr:last-child td {{
                border-bottom: none;
            }}
            td a {{
                color: var(--text-main);
                text-decoration: none;
                transition: color 0.2s;
            }}
            td a:hover {{
                color: var(--teal-accent);
            }}
            .code {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                background: rgba(0,0,0,0.2);
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
                border: 1px solid rgba(255,255,255,0.03);
            }}
            .status-badge {{
                display: inline-block;
                padding: 0.25rem 0.65rem;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .status-up {{
                background-color: rgba(76, 209, 55, 0.15);
                color: var(--green-up);
                border: 1px solid var(--green-up);
                box-shadow: 0 0 10px rgba(76, 209, 55, 0.2);
            }}
            .refresh-btn {{
                background: var(--teal-accent);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0.5rem 1.25rem;
                font-weight: 600;
                cursor: pointer;
                font-family: inherit;
                transition: background 0.2s;
            }}
            .refresh-btn:hover {{
                background: var(--teal-hover);
            }}
        </style>
        <script>
            // Auto refresh the dashboard every 5 seconds
            setInterval(() => {{
                window.location.reload();
            }}, 5000);
        </script>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Demo <span>Discovery Server</span></h1>
                <button class="refresh-btn" onclick="window.location.reload()">Refresh Page</button>
            </header>

            <div class="system-stats">
                <div class="stat-card">
                    <div class="stat-title">System Status</div>
                    <div class="stat-value" style="color: var(--green-up);">Active (UP)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Registry Port</div>
                    <div class="stat-value">8761</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Discovery Type</div>
                    <div class="stat-value" style="font-size: 1.15rem; font-family: 'JetBrains Mono'; padding-top: 0.25rem;">Eureka-Compatible</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Server Uptime</div>
                    <div class="stat-value" style="font-family: 'JetBrains Mono'; font-size: 1.35rem; padding-top: 0.15rem;">{uptime_str}</div>
                </div>
            </div>

            <div class="registry-card">
                <h2>Active Services Directory (UP)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Application Name</th>
                            <th>Instance ID</th>
                            <th>Host / URL</th>
                            <th>Lease Status</th>
                            <th>Last Heartbeat</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8761)
