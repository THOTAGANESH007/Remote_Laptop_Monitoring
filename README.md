# Autonomous Cloud Architect

Turn ideas into production-ready code via your mobile phone.

## Summary
An end-to-end autonomous agent system that transforms a simple text prompt into a fully coded, GitHub-synced application. By leveraging local LLMs on AWS and a sandboxed execution environment, it provides a private, secure, and zero-cost-per-token development pipeline.

## The Vision
Imagine lying on your couch, having a project idea, typing it into a mobile dashboard, and receiving a notification 5 minutes later saying: **Build Complete. Code pushed to GitHub.** That is exactly what this system does.

## System Architecture
The system follows a **Brain-Orchestrator-Worker** pattern:
- Mobile UI sends a request via HTTPS and API Key to the **FastAPI Orchestrator**.
- The Orchestrator triggers the **Docker Cage**.
- The Docker Cage requests logic from the **Ollama / Qwen2.5 Brain**.
- The Docker Cage writes the resulting code to the **AWS File System**.
- The system auto-pushes the code to a **GitHub Repo**.
- The Orchestrator sends a push notification via [ntfy.sh](https://ntfy.sh).

## Tech Stack
- **Frontend:** HTML5, JS, and CSS3 for a dark-themed Mobile Dashboard.
- **Orchestrator:** FastAPI (Python) for API Routing, Security, and Build Management.
- **Worker:** Aider-Chat running in Docker as the hands that write and edit the code.
- **Brain:** Qwen2.5-Coder:7B local LLM running via Ollama.
- **Networking:** Nginx and Certbot for SSL Encryption and Reverse Proxy.
- **DevOps:** PM2 and GitHub Actions for process persistence and version control.

## The Security Model
To prevent an autonomous AI from compromising the server, the system implements:
- **Isolation:** Aider runs inside a Docker Container and cannot access the host OS.
- **Identity Mapping:** Uses specific user IDs so the AI doesn't create files as root.
- **Traffic Shield:** Nginx blocks common bot scanners and hides sensitive paths.
- **Encrypted Tunnel:** Full HTTPS implementation via Let's Encrypt.

## Implementation Roadmap
1. **Phase 1:** Provisioned AWS m7i-flex.large with 8GB RAM, optimized with a 4GB Swap file, and deployed Ollama with the Qwen2.5-Coder model.
2. **Phase 2:** Built a FastAPI backend for asynchronous build requests, integrated ntfy.sh for notifications, and developed a mobile-first Vision UI and Dashboard.
3. **Phase 3:** Configured SSH Ed25519 keys for passwordless GitHub syncing, automated the Git pipeline, and set up Nginx to route traffic.

## Directory Structure
| File/Folder | Description |
|--------------|--------------|
| `server.py` | The Orchestrator (FastAPI) |
| `index.html` | The Vision Input UI |
| `dashboard.html` | The Project Browser |
| `.gitignore` | Secret shielding |
| `projects folder` | Workspace containing generated apps, build logs, and agent metadata |

## Usage Guide
1. Navigate to [thotaganesh.me](https://thotaganesh.me) on your mobile device.
2. Enter your project name, and enter secret API key (thala713), and your detailed idea in the prompt field.
3. Hit "Launch Build" button to execute.
4. Close the browser; when your phone buzzes via ntfy.sh (Install in playstore and subscribe to aws_notifier to get the notification when build complete) notification channel — your app is ready!
5. Review either through the Dashboard or check your GitHub repository for final code output.

## Configuration
The system relies on environment variables stored in the bashrc file for security:

AGENT_ACCESS_TOKEN: Your private key for API access.
AGENT_NTFY_TOPIC: Your unique notification channel.  
AGENT_MODEL: The current active LLM.  

