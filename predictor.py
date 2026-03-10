import math
import random

# ====== HELPERS ======
def poisson_probability(lmbda, k):
    return (lmbda**k) * math.exp(-lmbda) / math.factorial(k)

def predict_first_half_goals(home_avg=1, away_avg=1):
    prob_no_goals = poisson_probability(home_avg, 0) * poisson_probability(away_avg, 0)
    return "Over 0.5" if prob_no_goals < 0.5 else "Under 0.5"

def calculate_ev(confidence, odds):
    return round(confidence * odds - (1-confidence), 2)

def pick_best_market(predictions):
    """
    For each match, pick highest-confidence market:
    Home Win / Away Win / Draw / Over 2.5 / Under 2.5 / BTTS Yes / No
    """
    best = []
    for p in predictions:
        # Example: only keep highest-confidence pick
        markets = {
            "Home Win": p.get("home_win",0),
            "Away Win": p.get("away_win",0),
            "Draw": p.get("draw",0),
            "Over 2.5": p.get("over_2_5",0),
            "Under 2.5": p.get("under_2_5",0),
            "BTTS Yes": p.get("btts_yes",0),
            "BTTS No": p.get("btts_no",0)
        }
        best_market = max(markets, key=lambda k: markets[k])
        p["best_market"] = best_market
        p["best_conf"] = round(markets[best_market],2)
        best.append(p)
    return best
