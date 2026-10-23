import pandas as pd
from io import BytesIO
import random
import pickle
import os
import re
from pathlib import Path


class AuctionEngine:
    SAVE_FILE = Path(__file__).with_name("auction_state.pkl")
    def __init__(
        self,
        players_df,
        captains,
        starting_purse=50.0,
        base_price=1.0,
        increment=0.25
    ):

        # Clean column names
        players_df.columns = [str(c).strip() for c in players_df.columns]

        self.players = players_df.sample(frac=1).reset_index(drop=True)

        self.total_players = len(self.players)
        self.current_index = 0

        self.captains = captains

        self.starting_purse = starting_purse
        self.base_price = base_price
        self.increment = increment

        self.current_bid = base_price
        self.highest_bidder = None

        self.history = []
        self.unsold = []

        # Captain Purse
        self.purse = {
            captain: starting_purse
            for captain in captains
        }

        # Captain Teams
        self.teams = {
            captain: []
            for captain in captains
        }

    # -----------------------------------------------------
    # Current Player
    # -----------------------------------------------------

    def current_player(self):

        if self.current_index >= self.total_players:
            return None

        return self.players.iloc[self.current_index]
     
    # -----------------------------------------------------
    # Bid
    # -----------------------------------------------------

    def place_bid(self, captain):

        if self.current_player() is None:
            return

        if len(self.teams[captain]) >= 10:
            return

        if self.highest_bidder is None:
            bid = self.base_price
        else:
            bid = self.current_bid + self.increment

        if bid > self.purse[captain]:
            return

        self.current_bid = bid
        self.highest_bidder = captain
       
# ---- save file


    def save_state(self):

        state = {
            "players": self.players,
            "current_index": self.current_index,
            "current_bid": self.current_bid,
            "highest_bidder": self.highest_bidder,
            "history": self.history,
            "unsold": self.unsold,
            "teams": self.teams,
            "purse": self.purse,
            "total_players": self.total_players
        }

        with open(self.SAVE_FILE, "wb") as f:
            pickle.dump(state, f)


    def load_state(self):

        if not os.path.exists(self.SAVE_FILE):
            return False

        with open(self.SAVE_FILE, "rb") as f:
            state = pickle.load(f)

        if (
            set(state["teams"]) != set(self.captains)
            or set(state["purse"]) != set(self.captains)
        ):
            raise ValueError(
                "The saved auction uses different captains from config.json."
            )

        self.players = state["players"]
        self.current_index = state["current_index"]
        self.current_bid = state["current_bid"]
        self.highest_bidder = state["highest_bidder"]
        self.history = state["history"]
        self.unsold = state["unsold"]
        self.teams = state["teams"]
        self.purse = state["purse"]
        self.total_players = state["total_players"]

        return True
#---

    # -----------------------------------------------------
    # Sell Player
    # -----------------------------------------------------

    def sell_player(self):

        if self.highest_bidder is None:
            return

        player = self.current_player()

        player_dict = player.to_dict()

# Store the exact player key once
        player_dict["Player"] = player_dict.get( "Players Name",player_dict.get("Players Name", ""))

        player_dict["Sold Price"] = self.current_bid
        player_dict["Captain"] = self.highest_bidder

        # Add to Team
        self.teams[self.highest_bidder].append(player_dict)

        # Deduct Purse
        self.purse[self.highest_bidder] -= self.current_bid

        # History
        self.history.append({
            "Player": player_dict.get("Players Name", ""),
            "Captain": self.highest_bidder,
            "Price (Cr)": self.current_bid
        })

        self.next_player()
        self.save_state()



    def undo_last_sale(self):

        if len(self.history) == 0:
         return False

        last_sale = self.history.pop()

        player_name = last_sale["Player"]
        captain = last_sale["Captain"]
        price = last_sale["Price (Cr)"]

        # Refund purse
        self.purse[captain] += price

        # Remove player from captain team
        self.teams[captain] = [
            p for p in self.teams[captain]
            if p.get("Players Name") != player_name
        ]

        # Move auction back one player
        if self.current_index > 0:
            self.current_index -= 1

        # Reset bidding
        self.current_bid = self.base_price
        self.highest_bidder = None

        self.save_state()

        return True
      
    # -----------------------------------------------------
    # Unsold
    # -----------------------------------------------------
    

    def unsold_player(self):

        player = self.current_player()

        if player is not None:
            self.unsold.append(player.to_dict())

        self.next_player()
        self.save_state()

    # -----------------------------------------------------
    # Next Player
    # -----------------------------------------------------

    def next_player(self):

        self.current_index += 1

        self.current_bid = self.base_price
        self.highest_bidder = None
    
    # -----------------------------------------------------
    # Export Excel
    # -----------------------------------------------------

    def export_excel(self):

        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:

            summary = []
            used_sheet_names = {
                "auction summary", "sold history", "unsold players"
            }

            for captain in self.captains:

                team = self.teams[captain]
                # Excel sheet names have stricter rules than captain names.
                base_name = re.sub(r"[\\/*?:\[\]\x00-\x1f]", "_", captain)
                base_name = base_name.strip("'")[:31] or "Team"
                sheet_name = base_name
                suffix = 2
                while sheet_name.casefold() in used_sheet_names:
                    ending = f" ({suffix})"
                    sheet_name = base_name[:31 - len(ending)] + ending
                    suffix += 1
                used_sheet_names.add(sheet_name.casefold())

                if len(team) == 0:
                    team_df = pd.DataFrame(columns=[
                        "Sl No",
                        "Players Name",
                        "Availability",
                        "All Rounder",
                        "Batting",
                        "Bowling",
                        "Wicket Keeping",
                        "Sold Price (Cr)"
                    ])
                else:

                    rows = []

                    for i, p in enumerate(team, start=1):

                        rows.append({
                            "Sl No": i,
                            "Players Name": p.get("Players Name", ""),
                            "Availability": p.get("Availability for tournament", ""),
                            "All Rounder": p.get("Skill -Allrounder (batting+Bowling)", ""),
                            "Batting": p.get("Skill-Batting", ""),
                            "Bowling": p.get("Skill-Bowling", ""),
                            "Wicket Keeping": p.get("Skill-Wicket Keeping", ""),
                            "Sold Price (Cr)": p.get("Sold Price", "")
                        })

                    team_df = pd.DataFrame(rows)

                team_df.to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=False
                )

                spent = self.starting_purse - self.purse[captain]

                summary.append({
                    "Captain": captain,
                    "Players Bought": len(self.teams[captain]),
                    "Total Spent (Cr)": round(spent, 2),
                    "Balance (Cr)": round(self.purse[captain], 2)
                })

            # Summary Sheet
            summary_df = pd.DataFrame(summary)

            summary_df.to_excel(
                writer,
                sheet_name="Auction Summary",
                index=False
            )

            # Sold History
            pd.DataFrame(self.history).to_excel(
                writer,
                sheet_name="Sold History",
                index=False
            )

            # Unsold Players
            pd.DataFrame(self.unsold).to_excel(
                writer,
                sheet_name="Unsold Players",
                index=False
            )

        output.seek(0)

        return output.getvalue()
