# bayesian-blog
Check out the Jupyter notebooks!

1. `basketball outcomes using probabilistic programming.ipynb` models UAAP Season 79 (2016) men's basketball with a Bayesian model of each team's offensive and defensive strength. It fits the model with [PyMC](https://www.pymc.io), simulates the second half of the season and the playoffs, and checks the predictions against what actually happened.
2. `uaap basketball across seasons.ipynb` extends the model to every season with results on Wikipedia, from 2003 to 2025. Team strengths evolve from season to season, and a pace effect captures fast and slow games. It looks at what carries over between seasons and what champions look like, and backtests how predictable each season was, halfway through and before it started.

## Running it

Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

## Data

- `uaap_79_as_of_oct_5_2016.csv`: Season 79's results halfway through the season, which the first notebook is fit on.
- `uaap_79_full_season.csv`: Season 79's full results, a fallback for when scraping Wikipedia fails.
- `uaap_men_games.csv` and `uaap_men_seasons.csv`: every elimination-round game, and every team's final place and champion, for 17 seasons. Run `python scrape_uaap.py` to scrape them again.
- `uaap_backtest_games.csv` and `uaap_backtest_teams.csv`: the second notebook's backtest results, which take about an hour to compute. Delete them to recompute.
