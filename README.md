# NC Early Vote Tracker

A free, self-updating dashboard that compares North Carolina's 2026 early and mail vote with the 2018 and 2022 midterms, lined up by days before Election Day.

**Live site:** https://movebeyondfptp.github.io/EV-Model/

It's built to test a claim, not to make one: early vote data shows *who* has voted (by registration, age, race, county), not *how* they voted. The "What would a lead look like?" panel lets you set vote-choice assumptions and shows how far they move the answer, then runs the same assumptions on 2022's early vote and checks them against the actual 2022 U.S. Senate result.

## How it works

| Piece | What it does | Cost |
|---|---|---|
| `pipeline/build.py` | Downloads the statewide absentee/early vote file from the [NC State Board of Elections](https://www.ncsbe.gov/results-data/absentee-data), keeps accepted ballots (one per voter), and writes daily aggregates to `docs/data/*.json` | free |
| `.github/workflows/update.yml` | Runs the pipeline twice a day and commits the new JSON | free on public repos |
| `docs/index.html` | Static dashboard (GitHub Pages), Chart.js bundled locally | free |

The 2018 and 2022 baselines are built once and then reused. Raw files never get committed; only the small summaries do.

## Running it

- **Refresh now:** Actions tab → *Update early vote data* → *Run workflow*. Tick *force* to rebuild the baselines.
- **Locally:** `pip install -r requirements.txt && python pipeline/build.py`, then serve `docs/` (`python -m http.server -d docs`).

## Method notes

- Counts are accepted ballots, deduplicated by NCID, keeping the earliest accepted return.
- Days before Election Day are computed from each ballot's return date. Ballots accepted after Election Day are counted on day 0.
- Prior-cycle curves are rebuilt from the final files, so they can differ slightly from what was published on each day at the time.
- The "final early vote if pace holds" tile scales today's count by how the remaining days went in each prior cycle.
- The preliminary projection starts from the last comparable result for each race (set in `pipeline/states/<state>.json`) and moves it by part of the change in the early electorate's party mix. How much it counts is calibrated on a past pair of cycles (2020 to 2024 for NC) and shrunk toward 50%.
- Party is voter registration. "Third party" groups Libertarian, Green, No Labels, Justice for All and others.
- Rules differ by cycle (photo ID, the end of the three-day mail ballot grace period, early voting schedules), so treat differences from 2018 and 2022 with care.

## Extending it

- **First-time and lapsed voters:** join ballots to the NCSBE voter history file (`ncvhis`) to see what share of 2026 early voters skipped 2022. The file is large, so do it inside the Action and commit only the summary.
- **2024 comparison:** add `2024: date(2024, 11, 5)` to `ELECTIONS` in `build.py`, keeping in mind presidential turnout isn't comparable to a midterm.
