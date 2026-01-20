# Marauders Golf Society Management System

This repository contains the backend and frontend code for the Marauders Golf Society management system. It handles scoring, handicaps, finance, and reporting.

## Project Structure

*   **marauders/**: The core Python package containing the business logic.
    *   **repositories/**: Data access layer.
    *   **services/**: Business logic layer.
    *   **utils/**: Utility functions.
    *   `manager.py`: Central controller that coordinates services and repositories.
    *   `database.py`: Database connection wrapper.
*   **gui/**: The graphical user interface (built with PySide6/Qt).
*   **run_gui.py**: Entry point to launch the GUI.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install pandas pyside6 openpyxl
    ```

2.  **Database**:
    The system uses an SQLite database (`marauders.db`). It will be created automatically on the first run.

    You need to set the path to the master Excel file in the settings (via the GUI or `test_marauders_cli.py`) to import scores.

3.  **Run the GUI**:
    ```bash
    python run_gui.py
    ```

## Development

*   **Database**: The `marauders.database.Database` class handles SQLite connections. It uses `pandas` for easy data retrieval.
*   **Settings**: Application settings are stored in the `GlobalSettings` table in the database, managed by `marauders.repositories.settings_repo.SettingsRepository`.

## Testing

You can use the CLI test script to verify core functionality:

```bash
python test_marauders_cli.py
```
