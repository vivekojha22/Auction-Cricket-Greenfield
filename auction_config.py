import json
from pathlib import Path
from typing import TypedDict


class AuctionConfig(TypedDict):
    auction_title: str
    captains: list[str]


CONFIG_FILE = Path(__file__).with_name("config.json")


def load_config(path: Path = CONFIG_FILE) -> AuctionConfig:
    with path.open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    if not isinstance(config, dict):
        raise ValueError("Configuration must be a JSON object.")

    captains = config.get("captains")
    if not isinstance(captains, list) or not captains:
        raise ValueError("'captains' must be a non-empty list of names.")
    if any(not isinstance(name, str) or not name.strip() for name in captains):
        raise ValueError("Each captain must have a non-empty name.")

    captains = [name.strip() for name in captains]
    if len({name.casefold() for name in captains}) != len(captains):
        raise ValueError("Captain names must be unique (ignoring case).")

    title = config.get("auction_title", "Cricket Auction")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("'auction_title' must be a non-empty string.")

    return {"auction_title": title.strip(), "captains": captains}
