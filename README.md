# Poker Hand Extractor

## How to run locally

1. Create a python virtual environment at backend folder:

```bash
cd backend
python -m venv .venv
```

2. Activate the python virtual environment:

```bash
.\backend\poker\Scripts\Activate.ps1
```

3. Run uvicorn to start the backend:

```bash
uvicorn src.api.main:app --reload
```

4. Open a new terminal:

```bash
cd frontend
pnpm run dev
```
