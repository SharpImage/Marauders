# marauders_import_template.md

To import full data into the Marauders system, your Excel file can contain the following sheets.
Only the "Scores" sheet is strictly required (players will be auto-created with defaults if missing).

## 1. Sheet: "Scores" (Required)
Columns:
*   `Game Date` (YYYY-MM-DD)
*   `Player Name`
*   `Front Nine`
*   `Back Nine`
*   `Overall`
*   *(Optional NTP columns: `NTP Hole 3`, `NTP Hole 6`, etc.)*

## 2. Sheet: "Players" (Optional)
Use this to set starting handicaps and balances.
Columns:
*   `Player` (Must match names in Scores)
*   `First Name`
*   `Last Name`
*   `Primary Email`
*   `StartingHandicap` (default 0.0)
*   `StartingBalance` (default 0.0)
*   `Active` (YES/NO)

## 3. Sheet: "Transactions" (Optional)
Use this to import manual financial history (e.g. payments).
Columns:
*   `Date`
*   `Player`
*   `PaidIn`
*   `PaidOut`
*   `Description`

## 4. Sheet: "PlaceCuts" (Optional - Config)
Columns:
*   `noOfWinners`
*   `Cut`
*   `no2dPlaces`
*   `Cut2`

## 5. Sheet: "PointsAdjustment" (Optional - Config)
Columns:
*   `StbfPoints`
*   `HndChange`
