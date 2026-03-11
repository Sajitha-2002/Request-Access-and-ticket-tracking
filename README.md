# Nila — AI Workplace Access & Shared Resource Management

Nila is a full-stack, AI-driven workplace access and shared resource management system. It features an animated assistant ("Nila") powered by a LangGraph + DeepSeek AI agent, voice input via Web Speech API, role-based access control, and PDF/CSV/Excel export.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.111, Python 3.11+, SQLAlchemy 2, SQLite |
| Auth | JWT (`python-jose`), bcrypt (`passlib`) |
| AI Agent | LangGraph 0.1, LangChain 0.2, DeepSeek API |
| Export | ReportLab (PDF), Pandas + openpyxl (CSV/Excel) |
| Frontend | React 18, Vite 5, Tailwind CSS 3, Framer Motion 11 |
| Voice | Web Speech API (browser-native) |

---

## Prerequisites

- Python 3.11 or later
- Node.js 18 or later
- A [DeepSeek API key](https://platform.deepseek.com/)

---

## Setup

### 1. Backend

```bash
cd backend

# Create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
copy .env.example .env
# Edit .env and set DEEPSEEK_API_KEY (and optional SMTP settings)

# Seed default users and request types
python seed_data.py

# Start the API server (http://localhost:8000)
python main.py
```

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the development server (http://localhost:5173)
npm run dev
```

---

## Environment Variables (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | *(random)* | JWT signing secret — change in production |
| `DATABASE_URL` | No | `sqlite:///./nila.db` | SQLAlchemy DB URL |
| `DEEPSEEK_API_KEY` | Yes | — | Your DeepSeek API key |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com/v1` | DeepSeek endpoint |
| `DEEPSEEK_MODEL` | No | `deepseek-chat` | Model name |
| `SMTP_HOST` | No | — | Email host (optional) |
| `SMTP_PORT` | No | `587` | Email port |
| `SMTP_USER` | No | — | Email username |
| `SMTP_PASSWORD` | No | — | Email password |
| `SMTP_FROM` | No | — | Sender address |
| `ALLOWED_ORIGINS` | No | `http://localhost:5173` | CORS origins (comma-separated) |

---

## Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@company.com | Admin@1234 |
| Approver | approver@company.com | Approver@1234 |
| Employee | employee@company.com | Employee@1234 |

---

## Features

- **4 Request Types** — Access Request, Software Installation, Shared Resource Booking, General IT Support
- **5-Stage Status Flow** — Submitted → Under Review → Approved / Rejected → Fulfilled → Closed
- **3 Roles** — Admin, Approver, Employee (RBAC enforced on every endpoint)
- **Nila AI Assistant** — LangGraph state machine with intent classification, policy check, and execution routing. Supports English and Tamil
- **Voice Interaction** — Wake word "Hi Nila" via continuous Web Speech API; mic button for ad-hoc input
- **Cmd+K Command Search** — Global modal for fast request lookup and quick navigation
- **Export** — PDF (single request), CSV and Excel (request register with filters)
- **Dashboard** — Role-aware: employee sees own requests; approver/admin sees full register with analytics
- **Auto Request IDs** — Format `REQ-YYYY-XXXX`, unique per year
- **Target Date Calculator** — Base turnaround per type + priority offset (High: -1 day, Medium: -3, Low: -5)

---

## Project Structure

```
Ticket Tracking/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph AI workflow
│   │   ├── routers/         # FastAPI route handlers
│   │   ├── auth.py          # JWT & RBAC
│   │   ├── config.py        # Settings (Pydantic)
│   │   ├── database.py      # SQLAlchemy engine
│   │   ├── models.py        # ORM models
│   │   ├── schemas.py       # Pydantic schemas
│   │   └── services.py      # Business logic helpers
│   ├── main.py              # Uvicorn entry point
│   ├── seed_data.py         # Database seeder
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                 # Created from .env.example
└── frontend/
    ├── src/
    │   ├── components/      # Feature components
    │   ├── context/         # Auth & Nila context providers
    │   ├── hooks/           # useVoice, useWakeWordListener
    │   ├── pages/           # UsersPage, SettingsPage
    │   ├── services/        # Axios API client
    │   ├── App.jsx
    │   └── main.jsx
    ├── tailwind.config.js
    └── vite.config.js
```

---

## API Reference

Interactive API docs are available at `http://localhost:8000/docs` when the backend is running.

Key endpoint groups:

- `POST /api/auth/login` — Obtain JWT
- `GET  /api/requests/` — List requests (role-filtered)
- `POST /api/requests/` — Submit a new request
- `POST /api/requests/{id}/transition` — Change request status
- `POST /api/agent/` — Query the Nila AI agent
- `GET  /api/export/requests/{id}/pdf` — Download PDF
- `GET  /api/export/requests/csv?fmt=excel` — Download CSV or Excel
