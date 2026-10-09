"""Scrape UAAP men's basketball results from Wikipedia into two CSV files.

uaap_men_games.csv    one row per elimination-round game: season, year, home, away, scores, round
uaap_men_seasons.csv  one row per team and season: elimination-round wins, final place, champion

Each season's page has a results matrix: the row team's score comes first, and (as the pages
state) cells above the diagonal are first-round games. The pages also list every team's
opponents and results in game order; where those disambiguate a pair's two games, we use them
to check the round of each cell.

Usage: python scrape_uaap.py
"""
import io
import re
import time

import numpy as np
import pandas as pd
import requests

TEAMS = ["AdU", "ADMU", "DLSU", "FEU", "NU", "UE", "UP", "UST"]
# seasons with a men's results matrix on Wikipedia (Season 83 was cancelled because of COVID-19)
SEASONS = [66, 71, 72] + list(range(74, 83)) + list(range(84, 89))
HEADERS = {"User-Agent": "bayesian-blog/1.0 (educational notebook)"}

ALIASES = {
    "adu": "AdU", "adamson": "AdU", "admu": "ADMU", "ateneo": "ADMU", "dlsu": "DLSU", "la salle": "DLSU",
    "feu": "FEU", "nu": "NU", "ue": "UE", "up": "UP", "upd": "UP", "ust": "UST",
}
FULL_NAMES = [("Adamson", "AdU"), ("Ateneo", "ADMU"), ("La Salle", "DLSU"), ("FEU", "FEU"), ("NU", "NU"),
              ("UE", "UE"), ("UP", "UP"), ("UST", "UST")]


def team_code(name):
    """Team code from a short name ("La Salle", "ADU") or a full name ("Ateneo Blue Eagles")."""
    name = str(name).strip().strip("[]")
    if name.lower() in ALIASES:
        return ALIASES[name.lower()]
    for key, code in FULL_NAMES:
        if re.search(rf"\b{key}\b", name):
            return code
    return None


def get(url, params=None):
    for attempt in range(5):
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if response.status_code != 429:
            response.raise_for_status()
            return response.text
        time.sleep(5 * 2**attempt)  # rate limited
    response.raise_for_status()


def get_page(season):
    """Raw wikitext and rendered HTML of a season's page, following a redirect if there is one."""
    title = f"UAAP_Season_{season}_basketball_tournaments"
    wikitext = get("https://en.wikipedia.org/w/index.php", {"title": title, "action": "raw"})
    redirect = re.match(r"#REDIRECT\s*\[\[([^\]#|]+)", wikitext, re.I)
    if redirect:
        title = redirect.group(1).replace(" ", "_")
        wikitext = get("https://en.wikipedia.org/w/index.php", {"title": title, "action": "raw"})
    html = get(f"https://en.wikipedia.org/wiki/{title}")
    return wikitext, html


def mens_section(wikitext, html):
    """Restrict both versions of the page to the men's tournament, when the page has several."""
    section = re.search(r"^==\s*Men's tournament\s*==\s*$(.*?)(?=^==[^=])", wikitext, re.S | re.M)
    if section:
        wikitext = section.group(1)
    start = html.find('id="Men\'s_tournament"')
    if start >= 0:
        ends = [html.find(f'id="{s}"', start) for s in ("Women's_tournament", "Juniors'_tournament")]
        html = html[start:min([e for e in ends if e > 0] or [len(html)])]
    return wikitext, html


def parse_score(text):
    match = re.search(r"(\d+)\s*\D+?\s*(\d+)", str(text))
    return (int(match.group(1)), int(match.group(2))) if match else None


def parse_scores(wikitext, html):
    """{(row team, column team): (row score, column score)} from the results matrix."""
    scores = {}
    for m in re.finditer(r"\|\s*match_(\w+?)_(\w+)\s*=\s*(?:\[\[[^|\]]*\|)?\s*(\d+)\s*[–—-]\s*(\d+)", wikitext):
        pair = (team_code(m.group(1)), team_code(m.group(2)))
        if None not in pair and pair not in scores:
            scores[pair] = (int(m.group(3)), int(m.group(4)))
    if len(scores) < 50:  # some older pages use a plain table instead of the results module
        matrix = next(t for t in pd.read_html(io.StringIO(html)) if t.shape == (8, 9)).iloc[:, 1:]
        matrix.columns = [team_code(c) for c in matrix.columns]
        matrix.index = TEAMS
        scores = {(a, b): parse_score(matrix.loc[a, b]) for a in TEAMS for b in TEAMS
                  if a != b and parse_score(matrix.loc[a, b])}
    return scores


def parse_game_logs(wikitext):
    """Each team's opponents and results in game order, from the match-up results lists."""
    opponents, results = {}, {}
    for key, value in re.findall(r"\|\s*opp_([^=|\n]+?)\s*=\s*([^\n|}]+)", wikitext)[:8]:
        opponents[key] = [team_code(x) for x in value.split("/") if x.strip()]
    for key, value in re.findall(r"\|\s*res_([^=|\n]+?)\s*=\s*([^\n|}]+)", wikitext):
        if key in opponents and key not in results:
            results[key] = [x.strip().upper() in ("W", "OTW") for x in value.split("/") if x.strip()]
    logs = {}
    for key, opps in opponents.items():
        # numbered lists (opp_1, opp_2, ...) are identified by the one team missing from the opponents
        missing = [t for t in TEAMS if t not in opps]
        team = team_code(key) or (missing[0] if len(missing) == 1 else None)
        if team and key in results and len(opps) == len(results[key]) == 14:
            logs[team] = list(zip(opps, results[key]))
    return logs if len(logs) == 8 else None


def scrape_season(season):
    wikitext, full_html = get_page(season)
    wikitext, html = mens_section(wikitext, full_html)
    scores = parse_scores(wikitext, html)
    logs = parse_game_logs(wikitext)

    games, checked, flipped = [], 0, 0
    for i, a in enumerate(TEAMS):
        for b in TEAMS[i + 1:]:
            upper, lower = scores.get((a, b)), scores.get((b, a))
            upper_round = 1
            if logs and upper and lower:
                meetings = [won for opp, won in logs[a] if opp == b]
                if len(meetings) == 2 and meetings[0] != meetings[1]:  # the two games had different winners
                    checked += 1
                    if (upper[0] > upper[1]) != meetings[0]:
                        upper_round, flipped = 2, flipped + 1
            if upper:
                games.append([season, a, b, *upper, upper_round])
            if lower:
                games.append([season, b, a, *lower, 3 - upper_round])
    games = pd.DataFrame(games, columns=["season", "home", "away", "home_score", "away_score", "round"])

    winners = np.where(games.home_score > games.away_score, games.home, games.away)
    wins = pd.Series(winners).value_counts().reindex(TEAMS, fill_value=0)

    # final elimination-round places: the standings table whose wins match the results matrix
    # (allowing for games missing from the matrix; some pages title the column "Teamvte")
    played = pd.concat([games.home, games.away]).value_counts().reindex(TEAMS, fill_value=0)
    place = None
    for table in pd.read_html(io.StringIO(html)):
        team_col = next((c for c in map(str, table.columns) if c.startswith("Team")), None)
        if team_col and {"Pos", "W"} <= set(map(str, table.columns)):
            rows = {team_code(t): (int(re.sub(r"\D", "", str(p)) or 0), int(re.sub(r"\D", "", str(w)) or -1))
                    for p, t, w in zip(table.Pos, table[team_col], table.W)}
            if all(t in rows and wins[t] <= rows[t][1] <= wins[t] + 14 - played[t] for t in TEAMS):
                place = pd.Series({t: rows[t][0] for t in TEAMS})
                break
    if place is None:  # no standings table: rank by wins (tied teams share a place)
        place = wins.rank(ascending=False, method="min").astype(int)

    finals = next(t for t in pd.read_html(io.StringIO(full_html))
                  if re.match(r"(Men's|Seniors') [Ff]inals", str(t.columns[0])))
    finals = finals.set_index(finals.columns[0])
    champion = team_code(finals["Wins"].astype(str).str.extract(r"(\d+)")[0].astype(float).idxmax())

    teams = pd.DataFrame({"season": season, "team": TEAMS, "wins": wins.values, "place": place[TEAMS].values,
                          "champion": [t == champion for t in TEAMS]})
    print(f"Season {season}: {len(games)} games, champion {champion}, "
          f"round check: {checked - flipped}/{checked} pairs follow the upper-triangle convention")
    return games, teams


def season_year(season):
    """Calendar year the season was played (Season 84 was played in 2022, after the cancelled Season 83)."""
    return 2022 if season == 84 else season + 1937


if __name__ == "__main__":
    all_games, all_teams = [], []
    for season in SEASONS:
        games, teams = scrape_season(season)
        all_games.append(games)
        all_teams.append(teams)
        time.sleep(1)
    games = pd.concat(all_games, ignore_index=True)
    teams = pd.concat(all_teams, ignore_index=True)
    games.insert(1, "year", games.season.map(season_year))
    teams.insert(1, "year", teams.season.map(season_year))
    games.to_csv("uaap_men_games.csv", index=False)
    teams.to_csv("uaap_men_seasons.csv", index=False)
