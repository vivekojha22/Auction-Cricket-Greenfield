import pandas as pd
from io import BytesIO


class DataManager:
    """
    Handles reading and writing auction data.
    """

    @staticmethod
    def load_players(uploaded_file):
        """
        Load players from uploaded Excel file.
        """

        df = pd.read_excel(uploaded_file)

        # Remove blank rows
        df = df.dropna(how="all")

        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]

        # Remove duplicate players
        if "Players Name" in df.columns:
            df = df.drop_duplicates(subset=["Players Name"])

        df.reset_index(drop=True, inplace=True)

        return df

    @staticmethod
    def export_results(auction):

        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:

            # -------------------------
            # Summary
            # -------------------------

            summary = []

            for captain in auction.captains:

                spent = auction.starting_purse - auction.purse[captain]

                summary.append({
                    "Captain": captain,
                    "Players Bought": len(auction.teams[captain]),
                    "Amount Spent (Cr)": round(spent, 2),
                    "Balance (Cr)": round(auction.purse[captain], 2)
                })

            pd.DataFrame(summary).to_excel(
                writer,
                sheet_name="Summary",
                index=False
            )

            # -------------------------
            # Team Sheets
            # -------------------------

            for captain in auction.captains:

                team_df = pd.DataFrame(auction.teams[captain])

                if team_df.empty:
                    team_df = pd.DataFrame(columns=[
                        "Player Name",
                        "Sold Price",
                        "Captain"
                    ])

                team_df.to_excel(
                    writer,
                    sheet_name=captain,
                    index=False
                )

            # -------------------------
            # Sold History
            # -------------------------

            history_df = pd.DataFrame(auction.history)

            history_df.to_excel(
                writer,
                sheet_name="Auction History",
                index=False
            )

            # -------------------------
            # Unsold Players
            # -------------------------

            unsold_df = pd.DataFrame(auction.unsold)

            unsold_df.to_excel(
                writer,
                sheet_name="Unsold",
                index=False
            )

        output.seek(0)

        return output.getvalue()