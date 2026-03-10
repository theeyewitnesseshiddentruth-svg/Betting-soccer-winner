import os
import json
import csv
import math
import requests
import random
from datetime import datetime, timedelta, timezone

# ====== CONFIG ======
API_KEY = ""  # <-- Paste your API-Football key here
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

FIXTURE_FILE = "fixtures_today.csv"
TEAMS_FILE = "teams.json"

# Example: All leagues you want
LEAGUES = {
    "Premier League": 39,
    "La Liga": 140,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
    "Portugal - Segunda Liga": 94,
    "Egypt - Premier League": 60
}

# ====== HELPERS ======
def poisson_probability(lmbda, k):
    return (lmbda**k) * math.exp(-lmbda) / math.factorial(k)

def predict_first_half_goals(home_avg=1, away_avg=1):
    prob_no_goals = poisson_probability(home_avg, 0) * poisson_probability(away_avg, 0)
    return "Over 0.5" if prob_no_goals < 0.5 else "Under 0.5"

def convert_utc_to_utc2(utc_time_str):
    try:
        utc_time = datetime.fromisoformat(utc_time_str.replace("Z","+00:00"))
        utc2_time = utc_time + timedelta(hours=2)
        return utc2_time.strftime("%Y-%m-%d %H:%M")
    except:
        return utc_time_str

# ====== FETCH TODAY’S FIXTURES ======
def fetch_fixtures(date=None, league_id=None):
    params = {"date": date}
    if league_id:
        params["league"] = league_id
    try:
        resp = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json().get("response", [])
        fixtures = []
        for f in data:
            teams = f.get("teams", {})
            home = teams.get("home", {}).get("name","Unknown")
            away = teams.get("away", {}).get("name","Unknown")
            league = f.get("league", {}).get("name","Unknown League")
            fixture_time = f.get("fixture", {}).get("date","Unknown")
            status = f.get("fixture", {}).get("status", {}).get("short","NS")
            home_score = f.get("score", {}).get("fulltime", {}).get("home") or 0
            away_score = f.get("score", {}).get("fulltime", {}).get("away") or 0
            odds = round(random.uniform(1.5,3.0),2)  # placeholder
            fixtures.append({
                "home": home, "away": away, "league": league, "kickoff": fixture_time,
                "status": status, "home_score": home_score, "away_score": away_score,
                "odds": odds
            })
        return fixtures
    except Exception as e:
        print(f"API fetch failed for league {league_id}: {e}")
        return []

def save_fixtures_csv(fixtures, filename=FIXTURE_FILE):
    df = []
    for f in fixtures:
        df.append({
            "home": f["home"], "away": f["away"], "league": f["league"],
            "kickoff": f["kickoff"], "status": f["status"],
            "home_score": f["home_score"], "away_score": f["away_score"],
            "odds": f["odds"]
        })
    keys = df[0].keys() if df else []
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(df)

# ====== TEAM STATS ======
teams_stats = {}
if os.path.exists(TEAMS_FILE):
    with open(TEAMS_FILE, "r") as f:
        teams_stats = json.load(f)

def update_team_stats(league_id, league_name):
    """Fetch last 10 matches per team and update teams.json"""
    try:
        params = {"league": league_id, "season": datetime.now().year, "last": 10}
        resp = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json().get("response", [])

        for f in data:
            teams = f.get("teams", {})
            home = teams.get("home", {}).get("name")
            away = teams.get("away", {}).get("name")
            score = f.get("score", {}).get("fulltime", {})
            home_score = score.get("home",0)
            away_score = score.get("away",0)
            date = f.get("fixture",{}).get("date","").split("T")[0]
            result_home = "W" if home_score>away_score else "D" if home_score==away_score else "L"
            result_away = "W" if away_score>home_score else "D" if home_score==away_score else "L"

            for team, opp, goals_for, goals_against, res, home_flag in [
                (home, away, home_score, away_score, result_home, True),
                (away, home, away_score, home_score, result_away, False)
            ]:
                if team not in teams_stats:
                    teams_stats[team] = {"league": league_name, "matches": [], "stats": {}}
                matches = teams_stats[team]["matches"]
                if len(matches)==10:
                    matches.pop(0)
                matches.append({
                    "date": date, "home": home_flag, "opponent": opp,
                    "goals_for": goals_for, "goals_against": goals_against, "result": res
                })
                # recalc stats
                total = len(matches)
                wins = sum(1 for m in matches if m["result"]=="W")
                draws = sum(1 for m in matches if m["result"]=="D")
                losses = total - wins - draws
                avg_for = sum(m["goals_for"] for m in matches)/total
                avg_against = sum(m["goals_against"] for m in matches)/total
                over_2_5 = sum(1 for m in matches if (m["goals_for"]+m["goals_against"])>2)/total*100
                btts = sum(1 for m in matches if m["goals_for"]>0 and m["goals_against"]>0)/total*100
                teams_stats[team]["stats"] = {
                    "avg_goals_for": round(avg_for,2),
                    "avg_goals_against": round(avg_against,2),
                    "win_pct": round(wins/total*100,2),
                    "draw_pct": round(draws/total*100,2),
                    "loss_pct": round(losses/total*100,2),
                    "over_2_5_pct": round(over_2_5,2),
                    "btts_pct": round(btts,2)
                }

        with open(TEAMS_FILE, "w") as f:
            json.dump(teams_stats,f,indent=2)
    except Exception as e:
        print(f"Failed to update {league_name}: {e}")

# ====== BET SUGGESTIONS ======
def suggest_bet(f):
    home_stats = teams_stats.get(f["home"], {}).get("stats", {})
    away_stats = teams_stats.get(f["away"], {}).get("stats", {})

    # Simple confidence calculation
    home_conf = home_stats.get("win_pct",50)/100
    away_conf = away_stats.get("win_pct",50)/100
    draw_conf = max(0,1-home_conf-away_conf)
    over_conf = max(home_stats.get("over_2_5_pct",50), away_stats.get("over_2_5_pct",50))/100
    btts_conf = max(home_stats.get("btts_pct",50), away_stats.get("btts_pct",50))/100

    # Pick highest confidence market
    markets = {
        "Home Win": home_conf,
        "Draw": draw_conf,
        "Away Win": away_conf,
        "Over 2.5": over_conf,
        "BTTS Yes": btts_conf
    }
    pick = max(markets, key=markets.get)
    confidence = markets[pick]

    # First-half goals
    fh = predict_first_half_goals(home_stats.get("avg_goals_for",1), away_stats.get("avg_goals_for",1))

    return {
        **f,
        "kickoff_utc2": convert_utc_to_utc2(f["kickoff"]),
        "pick": pick,
        "confidence": round(confidence*100,1),
        "fh": fh
    }

# ====== DISPLAY ======
def display_section(title, matches):
    print(f"\n{title}\n{'='*60}")
    for idx,m in enumerate(matches,1):
        print(f"{idx}️⃣ [{m['league']}]\n{m['home']} vs {m['away']}\nTime: {m['kickoff_utc2']} {m['status']}\nPick: {m['pick']} 🎯 Confidence: {m['confidence']}% | 1H-O/U: {m['fh']}\n{'-'*60}")

# ====== MAIN ======
if __name__=="__main__":
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1️⃣ Update stats per league (1 API request per league)
    for league_name, league_id in LEAGUES.items():
        update_team_stats(league_id, league_name)

    # 2️⃣ Fetch today’s fixtures (1 API request per league)
    all_fixtures = []
    for league_name, league_id in LEAGUES.items():
        fixtures = fetch_fixtures(today, league_id)
        all_fixtures.extend(fixtures)
    save_fixtures_csv(all_fixtures)

    # 3️⃣ Make predictions
    predictions = [suggest_bet(f) for f in all_fixtures if f["status"]=="NS" and f["home"] in teams_stats and f["away"] in teams_stats]

    # 4️⃣ Split sections for ticket display
    now = datetime.now(timezone.utc)
    soon = [p for p in predictions if now <= datetime.fromisoformat(p['kickoff'].replace("Z","+00:00")).replace(tzinfo=timezone.utc) <= now + timedelta(hours=2)]
    top10 = sorted(predictions, key=lambda x: x["confidence"], reverse=True)[:10]
    pool500 = sorted(predictions, key=lambda x: x["confidence"], reverse=True)[10:22]
    acc1000 = sorted(predictions, key=lambda x: x["confidence"], reverse=True)[22:40]

    # 5️⃣ Display
    display_section("🔵 Top 10 of the Day (HDA Only)", top10)
    display_section("🟣 500 Odds Pool", pool500)
    display_section("💥 1000 Accumulator", acc1000)
    display_section("🚄 2-Hour Train Bets", soon)
