# CSC1108-Flight-Map-Routing

Simple Flask app for a flight route dashboard demo.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## Quick Check

1. Select `From`, `To`, and optimization mode.
2. Click `Find Route`.
3. Confirm the results page shows best route, distance, price, and stops.
