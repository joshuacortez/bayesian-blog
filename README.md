# bayesian-blog
Check out the Jupyter notebook!

`basketball outcomes using probabilistic programming.ipynb` models UAAP Season 79 men's basketball with a Bayesian model of each team's offensive and defensive strength. It fits the model with [PyMC](https://www.pymc.io), simulates the second half of the season, and checks the predictions against what actually happened.

## Running it

Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

The notebook scrapes the full season's results from Wikipedia. If that fails, it falls back to the saved copy in `uaap_79_full_season.csv`. The model is fit on `uaap_79_as_of_oct_5_2016.csv`, the results halfway through the season.
