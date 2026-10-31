# NetCoop AI

NetCoop AI is a hackathon project for multi-agent network fault diagnosis and interoperability. The planned system will coordinate specialized agents to analyze network performance, infrastructure, connectivity, fault correlation, and recommendations. This repository contains the initial frontend and backend scaffolding; the agents have not been implemented.

## Project structure

```text
NetCoop-AI/
|-- backend/
|   |-- agents/
|   |-- data/
|   |-- models/
|   |-- orchestrator/
|   |-- services/
|   |-- main.py
|   `-- requirements.txt
`-- frontend/
    |-- public/
    |-- src/
    |   |-- components/ui/  # Place reusable 21st.dev components here
    |   |-- lib/utils.js    # cn() helper for component class names
    |   `-- App.jsx
    `-- package.json
```

## Requirements

- Node.js 20.19+ (or 22.12+) and npm
- Python 3.10+

## Run the frontend

```powershell
cd frontend
npm install
npm run dev
```

Vite prints the local development URL. To create a production build, run `npm run build` from `frontend/`.

Tailwind CSS is configured through the Vite plugin. The `@/` import alias points to `frontend/src/`, and `src/lib/utils.js` exports `cn()` for combining Tailwind class names used by custom components.

## Run the backend

From the repository root, create and activate a virtual environment, then install the backend dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; its health endpoint is `/health`. Interactive API documentation is at `/docs`.

For macOS or Linux, use `python3 -m venv .venv`, `source .venv/bin/activate`, then run the pip and uvicorn commands above.

The frontend and backend run independently. No credentials or external services are required for this starter setup.
