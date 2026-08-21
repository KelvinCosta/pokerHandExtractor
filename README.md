# Poker Analytics & Behavioral Audit SaaS 🃏 

An advanced **Business Intelligence (BI)** and **Behavioral Audit via Artificial Intelligence** system focused on the Professional Poker ecosystem (players, teams, and stables).

This software was designed to process large volumes of hand histories, find technical leaks (money drains), and use AI agents to conduct psychological interviews focused on evaluating the player's level of denial and victimhood (Tilt) after losing periods (downswings).

---

## 🎯 Key Features

### 📊 Telemetry Dashboard (BI)
A dense dashboard focused on technical performance with 11 views, including:
- **General Health:** Global KPIs like Total Profit, bb/100, Hands Played, and Trends.
- **Pre and Post-Flop Engines:** Aggression and effectiveness metrics (VPIP, PFR, C-Bet, W$SD, WWSF).
- **Rivalry Mapping:** Ranking of opponents who extract the most value from the hero, along with a tagging system.
- **Big Pots Audit:** Advanced filters for analyzing critical decisions on the River.
- **MDA (Mass Data Analysis):** Analysis of general behavior and trends across the player population (Field).

---

## 🚀 How to Run the Project

There are two ways to run the project: using the Executable or running from source (Developer Mode).

### 🟢 Option 1: Using the Executables (Recommended for Users)
You don't need to configure databases or install Python/Node.js. Everything comes packaged and ready to run.

1. Go to the **[Releases](../../releases/latest)** tab on GitHub.
2. Download the executable for your operating system:
   - **Windows:** Download and run `PokerApp.exe`
   - **Ubuntu/Linux:** Download and run the `PokerApp` file
3. The backend server will initialize and a native application window will open automatically!

---

### 🛠️ Option 2: From Source Code (For Developers)

The project is split into a frontend (Next.js) and a backend (Python/FastAPI).

**1. Setting up the Backend (Python):**
Open a terminal in the root folder and run:
```bash
cd backend
python -m venv .venv
```
Activate the virtual environment (Windows PowerShell):
```bash
.\.venv\Scripts\Activate.ps1
```
*(On Linux use: `source .venv/bin/activate`)*

Install dependencies and start the server:
```bash
pip install -r requirements.txt
uvicorn src.api.main:app --reload
```

**2. Setting up the Frontend (Next.js):**
Open a **new terminal** in the root folder and run:
```bash
cd frontend
pnpm install
pnpm run dev
```
*(The frontend will be served locally and connect to the backend automatically).*

---

## 🏗️ Tech Stack

- **Frontend:** Next.js (React), Tailwind CSS, Shadcn/UI (Premium Dark Mode B2B aesthetics).
- **Backend:** Python, FastAPI.
- **Data Processing:** DuckDB and Polars (Ultra-fast aggregation in Parquet).
- **Database / Persistence:** SQLAlchemy.
- **Packaging:** PyInstaller & PyWebView.

## 📄 License

This project is open-source and licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**.
Use, modification, and distribution are permitted as long as all modifications or derivative network services are also open-source under the same license. This license ensures code protection while the software is monetized under a SaaS model.
