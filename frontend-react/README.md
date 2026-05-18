# Zynexra React Frontend

Lightweight React + Vite frontend for consuming Zynexra structured audit results.

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

Set the backend URL with:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## API Strategy

The app submits contract files to:

```text
POST /ask_file
```

with form fields:

```text
mode=AUDIT
response_format=json
```

The Streamlit frontend remains in `frontend/` during migration.
