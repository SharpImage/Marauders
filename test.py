# test_game_report.py

from datetime import date
from marauders.manager import MaraudersManager

def main():
    manager = MaraudersManager(db_path="marauders.db")

    # TODO: set to an actual game date that exists in your Scores
    game_date = date(2025, 10, 14)

    html = manager.build_game_report_html(game_date)

    # Write it to a file so you can open in a browser and copy into email
    out_file = f"game_report_{game_date.isoformat()}.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report written to {out_file}")

if __name__ == "__main__":
    main()
