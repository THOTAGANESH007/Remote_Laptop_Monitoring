from fastapi import FastAPI, BackgroundTasks, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
import requests

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- CONFIGURATION ---
ACCESS_TOKEN = os.environ.get("AGENT_ACCESS_TOKEN") 
MODEL_NAME = os.environ.get("AGENT_MODEL", "ollama/qwen2.5-coder:3b")
NTFY_TOPIC = os.environ.get("AGENT_NTFY_TOPIC")

# Define Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

if not os.path.exists(PROJECTS_DIR):
    os.makedirs(PROJECTS_DIR)

@app.post("/build")
async def start_build(data: dict, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    if x_api_key != ACCESS_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized")
    idea = data.get("idea")
    folder_name = data.get("name", "project").replace(" ", "_")
    background_tasks.add_task(run_aider, idea, folder_name)
    return {"message": f"Building '{folder_name}'..."}

@app.get("/list-projects")
async def list_projects(x_api_key: str = Header(None)):
    if x_api_key != ACCESS_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    projects = []
    # Scans ONLY the projects folder instead of the home directory
    for entry in os.scandir(PROJECTS_DIR):
        if entry.is_dir() and not entry.name.startswith('.'):
            projects.append({"name": entry.name, "modified": os.path.getmtime(entry.path)})
    
    return sorted(projects, key=lambda x: x['modified'], reverse=True)

@app.get("/list-project-files/{project_name}")
async def list_project_files(project_name: str, x_api_key: str = Header(None)):
    if x_api_key != ACCESS_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Look strictly inside the projects folder
    path = os.path.join(PROJECTS_DIR, project_name)
    
    if not os.path.exists(path): 
        raise HTTPException(status_code=404, detail="Project folder not found")
        
    files = []
    for entry in os.scandir(path):
        # --- HIDE HIDDEN FILES AND BUILD.LOG ---
        if not entry.name.startswith('.') and entry.name != 'build.log': 
            files.append({
                "name": entry.name, 
                "is_dir": entry.is_dir(),
                "size": f"{os.path.getsize(entry.path) / 1024:.1f} KB"
            })
    return sorted(files, key=lambda x: (not x['is_dir'], x['name']))

def run_aider(idea, folder_name):
    os.environ["OLLAMA_API_BASE"] = "http://host.docker.internal:11434"
    os.environ["OPENAI_API_KEY"] = "none"
    
    full_path = os.path.join(PROJECTS_DIR, folder_name)
    os.makedirs(full_path, exist_ok=True)

    uid = os.getuid()
    gid = os.getgid()    

    cmd = [
        "docker", "run", "--rm",
        "--user", f"{uid}:{gid}",
        "-v", f"{full_path}:/app:z",
        "-w", "/app",
        "-e", "HOME=/app",
        "--add-host=host.docker.internal:host-gateway",
        "-e", "OLLAMA_API_BASE=http://host.docker.internal:11434",
        "paulgauthier/aider", 
        "--model", "ollama/qwen2.5-coder:3b",
        "--edit-format", "whole",     # Forces small models to actually write
        "--no-check-update",
        "--yes",
        "--message", idea
    ]
    
    with open(f"{full_path}/build.log", "w") as log:
        subprocess.run(cmd, cwd=full_path, stdout=log, stderr=log)

    # AUTO PUSH TO GITHUB
    try:
        # Add all new files in the base repository
        subprocess.run(["git", "add", "."], cwd=BASE_DIR)
        # Commit with a timestamp and the idea
        commit_msg = f"Auto-build: {folder_name} - {idea[:20]}..."
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=BASE_DIR)
        # Push to GitHub
        subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR)
        print(f"Successfully pushed {folder_name} to GitHub.")
    except Exception as e:
        print(f"Git Push failed: {e}")

    # SEND NOTIFICATION WHEN FINISHED
    if NTFY_TOPIC:
        try:
            requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", 
                data=f"Build for '{folder_name}' is finished!",
                headers={
                    "Title": "Project Architect",
                    "Priority": "high"
                }
            )
        except Exception as e:
            print(f"Notification failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
