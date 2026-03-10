import os
import json
import requests
from datetime import datetime
import pandas as pd
from predictor import predict_first_half_goals, calculate_ev, pick_best_market

API_KEY = ""
BASE_URL = "https://v3.football.api-sports.io/fixtures"
HEADERS = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': 'v3.football.api-sports.io'}

LEAGUES_FILE = "leagues.json"
TEAMS_FILE = "teams.json"

# ====== LOAD LEAGUES ======
with open(LEAGUES_FILE) as f:
    LEAGUES = json.load(f)

# ====== FETCH FIXTURES (1 per league) ======
def fetch_league_fixtures(league_id, league_name):
    filename = f"fixtures_{league_id}.csv"
    if os.path.exists(filename):
        os.remove(filename)
    try:
        params = {"league": league_id, "season": datetime.now().year}
        resp = requests.get(BASE_URL, headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json().get("response", [])
        fixtures = []
        for f in data:
            home = f.get("teams", {}).get("home", {}).get("name","Unknown")
            away = f.get("teams", {}).get("away", {}).get("name","Unknown")
            kickoff = f.get("fixture", {}).get("date","Unknown")
            status = f.get("fixture", {}).get("status", {}).get("short","NS")
            fixtures.append({
                "home": home, "away": away, "league": league_name,
                "kickoff": kickoff, "status": status,
                "home_score": 0, "away_score":0,
                "home_odds": 1.8, "away_odds": 2.5
            })
        if fixtures:
            pd.DataFrame(fixtures).to_csv(filename, index=False)
        return fixtures
    except Exception as e:
        print(f"API fetch failed for {league_name}: {e}")
        return []

# ====== LOAD TEAMS JSON ======
if os.path.exists(TEAMS_FILE):
    with open(TEAMS_FILE) as f:
        teams_stats = json.load(f)
else:
    teams_stats = {}

# ====== MAIN WORKFLOW ======
all_fixtures = []
for league_name, league_id in LEAGUES.items():
    league_fixtures = fetch_league_fixtures(league_id, league_name)
    all_fixtures.extend(league_fixtures)

# Add dummy confidence stats per match (simulate ML output)
for f in all_fixtures:
    f.update({
        "home_win": round(0.6 + 0.4*random.random(),2),
        "away_win": round(0.6 + 0.4*random.random(),2),
        "draw": round(0.5 + 0.4*random.random(),2),
        "over_2_5": round(0.5 + 0.4*random.random(),2),
        "under_2_5": round(0.5 + 0.4*random.random(),2),
        "btts_yes": round(0.5 + 0.4*random.random(),2),
        "btts_no": round(0.5 + 0.4*random.random(),2),
    })

# Pick best market per match
predictions = pick_best_market(all_fixtures)

# Display like your ticket
for i,p in enumerate(predictions,1):
    print(f"{i}. [{p['league']}] {p['home']} vs {p['away']}")
    print(f"Time      : {p['kickoff']} {p['status']} ⚡")
    print(f"Pick      : {p['best_market']} 🎯 Confidence: {p['best_conf']}\n")
