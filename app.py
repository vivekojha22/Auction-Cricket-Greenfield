import streamlit as st
import pandas as pd
from pathlib import Path
from auction_config import load_config
from auction_engine import AuctionEngine


params = st.query_params
mode = params.get("mode", "viewer")
is_admin = mode == "admin"

st.set_page_config(
    page_title="🏏 Cricket Auction",
    page_icon="🏏",
    layout="wide"
)

try:
    config = load_config()
except (OSError, ValueError) as exc:
    st.error(f"Cannot load config.json: {exc}")
    st.stop()

st.title(f"🏏 {config['auction_title']}")

# --------------------------
# Fixed Settings
# --------------------------
CAPTAINS = config["captains"]
STARTING_PURSE = 50.0      # Crores
BASE_PRICE = 0.75           # Crores
INCREMENT = 0.25           # 25 Lakhs

# --------------------------
# Upload Excel
# --------------------------

EXCEL_FILE = Path(__file__).with_name("players.xlsx")

if not EXCEL_FILE.exists():
    st.error(f"{EXCEL_FILE} not found.")
    st.stop()

players_df = pd.read_excel(EXCEL_FILE, engine="openpyxl")

# --------------------------
# Session State
# --------------------------

if st.session_state.get("configured_captains") != CAPTAINS:
    st.session_state.pop("auction", None)
    st.session_state.configured_captains = CAPTAINS.copy()

state_error = None

if "auction" not in st.session_state:

    auction = AuctionEngine(
        players_df,
        CAPTAINS,
        STARTING_PURSE,
        BASE_PRICE,
        INCREMENT
    )

    try:
        auction.load_state()
    except ValueError as exc:
        state_error = str(exc)
    else:
        st.session_state.auction = auction
else:
    auction = st.session_state.auction

# --------------------------
# Sidebar
# --------------------------

st.sidebar.title("Captains")

if st.sidebar.button("🆕 Start New Auction"):

    Path(AuctionEngine.SAVE_FILE).unlink(missing_ok=True)
    st.session_state.clear()
    st.rerun()

if state_error:
    st.error(state_error)
    st.info(
        "Use 'Start New Auction' in the sidebar to discard the saved auction "
        "and use the configured captains, or restore the previous captain names "
        "in config.json to resume it."
    )
    st.stop()

for captain in CAPTAINS:

    purse = auction.purse[captain]
    player_count = len(auction.teams[captain])

    st.sidebar.markdown(f"### {captain}")
    st.sidebar.write(f"💰 Purse : ₹ {purse:.2f} Cr")

    if purse <= 2:
        st.sidebar.error("⚠ Only ₹2 Cr Left!")

    st.sidebar.write(f"👥 Players : {player_count}")

    st.sidebar.divider()

# --------------------------
# Current Player
# --------------------------

player = auction.current_player()

if player is None:

    st.success("Auction Completed!")

    for captain in CAPTAINS:

        st.subheader(captain)

        team = pd.DataFrame(auction.teams[captain])

        if len(team) > 0:
            st.dataframe(team)

    st.download_button(
        "Download Result",
        auction.export_excel(),
        file_name="Auction_Result.xlsx"
    )

    st.stop()

# --------------------------
# Player Details
# --------------------------

col1, col2 = st.columns([2,1])

with col1:

    st.subheader(
        f"Player {auction.current_index+1} / {auction.total_players}"
    )

    st.markdown(f"## {player['Players Name']}")

    for col in player.index:

        if col != "Players Name":
            st.write(f"**{col}** : {player[col]}")

with col2:

    st.metric(
        "Current Bid",
        f"₹ {auction.current_bid:.2f} Cr"
    )

    bidder = auction.highest_bidder

    if bidder is None:
        bidder = "No Bid Yet"

    st.metric(
        "Highest Bidder",
        bidder
    )

st.divider()

# --------------------------
# Bid Buttons
# --------------------------

for row_start in range(0, len(CAPTAINS), 3):
    row_captains = CAPTAINS[row_start:row_start + 3]
    bid_columns = st.columns(len(row_captains))

    for column, captain in zip(bid_columns, row_captains):
        with column:
            st.button(
                f"🏏 {captain} Bid",
                key=f"bid_{captain}",
                disabled=len(auction.teams[captain]) >= 10,
                use_container_width=True,
                on_click=auction.place_bid,
                args=(captain,)
            )

st.divider()

# --------------------------
# Action Buttons
# --------------------------

b1,b2,b3 = st.columns(3)

with b1:

    if st.button("✅ SOLD", use_container_width=True):

        if auction.highest_bidder is None:
            st.warning("No bid placed.")
        else:
            auction.sell_player()
            st.rerun()

with b2:

    if st.button("❌ UNSOLD", use_container_width=True):
        auction.unsold_player()
        st.rerun()

with b3:

    if st.button("↩ NEXT PLAYER", use_container_width=True):
        auction.next_player()
        st.rerun()

# --------------------------
# Sold History
# --------------------------

st.divider()

if st.button("↩️ UNDO LAST SALE", use_container_width=True):

    success = auction.undo_last_sale()

    if success:
        st.success("Last sale has been undone.")
    else:
        st.warning("Nothing to undo.")

    st.rerun()
    
st.subheader("Sold Players")

if len(auction.history) > 0:

    history_df = pd.DataFrame(auction.history)
# Start index from 1
    history_df.index = history_df.index + 1
    st.dataframe(
        history_df,
        use_container_width=True
    )