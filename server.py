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
    ignore = [".pm2", ".ssh", ".cache", "my_remote_loptop", "venv", ".local", ".config", "lost+found"]
    home_dir = os.path.expanduser("~")
    projects = []
    for entry in os.scandir(home_dir):
        if entry.is_dir() and entry.name not in ignore and not entry.name.startswith('.'):
            projects.append({"name": entry.name, "modified": os.path.getmtime(entry.path)})
    return sorted(projects, key=lambda x: x['modified'], reverse=True)

@app.get("/list-project-files/{project_name}")
async def list_project_files(project_name: str, x_api_key: str = Header(None)):
    if x_api_key != ACCESS_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized")
    path = os.path.abspath(os.path.expanduser(f"~/{project_name}"))
    if not os.path.exists(path): raise HTTPException(status_code=404)
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
    os.environ["OLLAMA_API_BASE"] = "http://localhost:11434"
    os.environ["OPENAI_API_KEY"] = "none"
    base_path = os.path.dirname(os.path.abspath(__file__))
    projects_root = os.path.join(base_path, "projects")
    full_path = os.path.join(projects_root, folder_name)
    os.makedirs(full_path, exist_ok=True)
    cmd = ["aider", "--model", MODEL_NAME, "--no-check-update", "--no-git", "--yes", "--message", idea]
    with open(f"{full_path}/build.log", "w") as log:
        subprocess.run(cmd, cwd=full_path, stdout=log, stderr=log)

    # AUTO PUSH TO GITHUB
    try:
        # Add all new files in the projects folder
        subprocess.run(["git", "add", "."], cwd=base_path)
        # Commit with a timestamp and the idea
        commit_msg = f"Auto-build: {folder_name} - {idea[:20]}..."
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=base_path)
        # Push to GitHub
        subprocess.run(["git", "push", "origin", "main"], cwd=base_path)
        print(f"Successfully pushed {folder_name} to GitHub.")
    except Exception as e:
        print(f"Git Push failed: {e}")

    # SEND NOTIFICATION WHEN FINISHED
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", 
            data=f"Build for '{folder_name}' is finished!",
            headers={
                "Title": "Project Architect",
                "Priority": "high",
                "Tags": "rocket,white_check_mark"
            }
        )
    except Exception as e:
        print(f"Notification failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
