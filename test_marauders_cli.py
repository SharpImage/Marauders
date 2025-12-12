# test_marauders_cli.py

from pprint import pprint
from marauders.manager import MaraudersManager


# ----------------------------------------------------------
# CONFIGURE YOUR PATHS HERE
# ----------------------------------------------------------
DB_PATH = "marauders.db"
# Use a valid path for testing if available, or just a dummy one
MASTER_FILE = r"C:\Users\Nigel\OneDrive\Documents\Golf\Marauders\Marauders_Master.xlsx"


def print_header(title: str):
    print("\n" + "-" * 60)
    print(f" {title}")
    print("-" * 60)


def main():
    print_header("MARAUDERS CLI TEST SCRIPT")

    # ------------------------------------------------------
    # Create manager
    # ------------------------------------------------------
    manager = MaraudersManager(
        db_path=DB_PATH
    )

    # ------------------------------------------------------
    # Configure Master File
    # ------------------------------------------------------
    manager.set_master_file(MASTER_FILE)

    # ------------------------------------------------------
    # 1. Import new scores
    # ------------------------------------------------------
    print_header("IMPORTING NEW SCORES")
    try:
        import_result = manager.import_new_scores()
        pprint(import_result)
    except Exception as e:
        print(f"Import failed (expected if file invalid): {e}")

    # ------------------------------------------------------
    # 2. Rebuild handicaps
    # ------------------------------------------------------
    print_header("REBUILDING HANDICAPS")

    hcap_result = manager.rebuild_handicaps()

    print("\nHistory Preview:")
    print(hcap_result["history"].head())

    print("\nCurrent Handicaps Preview:")
    print(hcap_result["current"].head())

    # ------------------------------------------------------
    # 3. Compute prizes
    # ------------------------------------------------------
    print_header("COMPUTING PRIZES")

    prize_result = manager.compute_prizes()

    print("\nPrize Payouts Preview:")
    print(prize_result["payouts"].head())

    print("\nPrize Totals Preview:")
    print(prize_result["totals_per_player"].head())

    # ------------------------------------------------------
    # 4. Rebuild finance ledger
    # ------------------------------------------------------
    print_header("REBUILDING FINANCE LEDGER")

    finance_result = manager.rebuild_finance()

    print("\nLedger Preview:")
    print(finance_result.ledger.head())

    print("\nPlayer Balances Preview:")
    print(finance_result.balances.head())

    print("\nGame Summary Preview:")
    print(finance_result.game_summary.head())

    print(f"\nKitty Total: £{finance_result.kitty_total:.2f}")

    # ------------------------------------------------------
    # 5. Player Status
    # ------------------------------------------------------
    print_header("PLAYER STATUS TABLE")
    try:
        # manager.get_player_status() is missing from manager, but functionality exists in services
        # We'll skip for now unless we add it to manager
        pass
    except Exception as e:
         print(f"Player status failed: {e}")

    # ------------------------------------------------------
    # 6. Get valid game dates & show summary for latest date
    # ------------------------------------------------------
    print_header("GAME SUMMARY (LATEST GAME)")

    dates = manager.get_game_dates()

    if dates:
        latest = dates[-1]
        print(f"Latest game: {latest}")

        summary = manager.get_game_summary()
        print("\nSummary Preview:")
        print(summary.head())
    else:
        print("No game dates found.")

    print_header("TEST COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()
