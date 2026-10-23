import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from auction_config import load_config
from auction_engine import AuctionEngine


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config_path = Path(self.directory.name) / "config.json"
        self.save_path = Path(self.directory.name) / "auction_state.pkl"
        self.save_patch = patch.object(AuctionEngine, "SAVE_FILE", self.save_path)
        self.save_patch.start()
        self.addCleanup(self.save_patch.stop)

    def load(self, config):
        self.config_path.write_text(json.dumps(config), encoding="utf-8")
        return load_config(self.config_path)

    def engine(self, captains):
        return AuctionEngine(
            pd.DataFrame({"Players Name": ["Player One", "Player Two"]}),
            captains,
            base_price=0.75,
        )

    def test_configured_names_and_default_title(self):
        self.assertEqual(
            self.load({"captains": [" Alice ", "Bob", "Charlie", "Dana"]}),
            {
                "auction_title": "Cricket Auction",
                "captains": ["Alice", "Bob", "Charlie", "Dana"],
            },
        )
        self.assertEqual(self.load({"captains": ["Solo"]})["captains"], ["Solo"])

    def test_invalid_configs(self):
        for config in (
            [],
            {},
            {"captains": []},
            {"captains": "Alice"},
            {"captains": [" "]},
            {"captains": [12]},
            {"captains": ["Alice", " alice "]},
            {"captains": ["Alice"], "auction_title": ""},
        ):
            with self.subTest(config=config), self.assertRaises(ValueError):
                self.load(config)
        self.config_path.write_text("{invalid json", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_config(self.config_path)

    def test_saved_auction_preserved_on_captain_mismatch(self):
        original = self.engine(["Alice", "Bob"])
        original.place_bid("Alice")
        self.assertEqual(original.current_bid, 0.75)
        original.sell_player()
        saved_bytes = self.save_path.read_bytes()

        changed = self.engine(["Charlie"])
        with self.assertRaisesRegex(ValueError, "different captains"):
            changed.load_state()
        self.assertEqual(self.save_path.read_bytes(), saved_bytes)
        self.assertEqual(changed.teams, {"Charlie": []})

        resumed = self.engine(["Bob", "Alice"])
        self.assertTrue(resumed.load_state())
        self.assertEqual(len(resumed.teams["Alice"]), 1)
        self.assertEqual(resumed.purse["Alice"], 49.25)

    def test_export_handles_captain_names(self):
        captains = [
            "North/West", "North:West", "Auction Summary",
            "A" * 40, "A" * 39 + "B", "'Captain'",
        ]
        auction = self.engine(captains)
        auction.place_bid(captains[0])
        auction.sell_player()
        workbook = pd.ExcelFile(BytesIO(auction.export_excel()))
        self.assertEqual(len(workbook.sheet_names), len(captains) + 3)
        self.assertTrue(all(len(name) <= 31 for name in workbook.sheet_names))
        self.assertEqual(
            workbook.parse("Auction Summary")["Captain"].tolist(), captains
        )

    def test_dynamic_ui_and_bidding(self):
        for captains in (["Solo"], ["Alice", "Bob", "Charlie", "Dana"]):
            with self.subTest(captains=captains), patch(
                "auction_config.load_config",
                return_value={"auction_title": "Test Auction", "captains": captains},
            ):
                app = AppTest.from_file(
                    str(Path(__file__).with_name("app.py"))
                ).run(timeout=20)
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len(app.error), 0)
                buttons = [
                    b for b in app.button if b.key and b.key.startswith("bid_")
                ]
                self.assertEqual(
                    {b.key for b in buttons}, {f"bid_{name}" for name in captains}
                )
                app.button(key=f"bid_{captains[-1]}").click().run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(app.session_state["auction"].highest_bidder, captains[-1])
                self.assertEqual(app.session_state["auction"].current_bid, 0.75)

    def test_existing_session_uses_updated_captains(self):
        with patch(
            "auction_config.load_config",
            return_value={"auction_title": "Test", "captains": ["Original"]},
        ) as config_loader:
            app = AppTest.from_file(
                str(Path(__file__).with_name("app.py"))
            ).run(timeout=20)
            config_loader.return_value = {
                "auction_title": "Updated", "captains": ["New One", "New Two"]
            }
            app.run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.title[0].value, "\U0001f3cf Updated")
            self.assertEqual(
                app.session_state["auction"].captains, ["New One", "New Two"]
            )

    def test_ui_reports_invalid_configuration(self):
        with patch(
            "auction_config.load_config",
            side_effect=ValueError("Captain names must be unique."),
        ):
            app = AppTest.from_file(
                str(Path(__file__).with_name("app.py"))
            ).run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertIn("Captain names must be unique", app.error[0].value)

    def test_ui_blocks_mismatched_save_until_explicit_reset(self):
        self.engine(["Old Captain"]).save_state()
        saved_bytes = self.save_path.read_bytes()
        with patch(
            "auction_config.load_config",
            return_value={"auction_title": "New Auction", "captains": ["New Captain"]},
        ):
            app = AppTest.from_file(
                str(Path(__file__).with_name("app.py"))
            ).run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertIn("different captains", app.error[0].value)
            self.assertEqual(self.save_path.read_bytes(), saved_bytes)
            app.sidebar.button[0].click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.error), 0)
            self.assertEqual(app.session_state["auction"].captains, ["New Captain"])


if __name__ == "__main__":
    unittest.main()
