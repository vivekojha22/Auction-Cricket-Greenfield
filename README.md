# Cricket Auction

## Configure captains

Edit `config.json` in this folder:

```json
{
  "auction_title": "My Cricket Auction",
  "captains": ["Captain One", "Captain Two", "Captain Three", "Captain Four"]
}
```

You can add or remove captains. Names must be non-empty and unique (ignoring
case). The title is optional and defaults to "Cricket Auction".
All captain displays, bid buttons, teams, purses, and result exports use these
names. Long names or names containing Excel-special characters are adjusted
only in exported worksheet tabs; the full names remain in the result data.

Keep using the existing `players.xlsx` in this folder. No upload is needed.
The spreadsheet must contain the `Players Name` column; other columns are
displayed as player details. The starting purse remains 50 Cr per captain,
the base price 0.75 Cr, the bid increment 0.25 Cr, and the team limit 10 players.

After changing the configuration, refresh the browser (or select Streamlit's
Rerun). If the saved auction belongs to different captains, the app will stop
and explain the mismatch. Restore the original names to resume, or click
**Start New Auction** in the sidebar to discard the old auction and start with
the new captains. Back up `auction_state.pkl` first if you need the old results.

## Run

From this folder:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Tests

```powershell
python -m unittest test_configuration
```