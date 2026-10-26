import os
import sqlite3
import sys

REQUIRED = ["streamlit", "networkx", "plotly", "pandas", "pyvis"]


def main():
    print(f"Python version : {sys.version.split()[0]}")
    print(f"SQLite version : {sqlite3.sqlite_version}")
    print("-" * 40)

    missing = []
    for name in REQUIRED:
        try:
            module = __import__(name)
            version = getattr(module, "__version__", "unknown")
            print(f"[OK]      {name:<10} {version}")
        except ImportError:
            print(f"[MISSING] {name}")
            missing.append(name)
    for folder in ["data", "notebooks", "reports"]:
        os.makedirs(folder, exist_ok=True)
    print("-" * 40)
    print("Project folders ready: data/, notebooks/, reports/")

    if missing:
        print("\nSetup INCOMPLETE. Run: pip install -r requirements.txt")
        sys.exit(1)
    print("\nSetup COMPLETE. All libraries are installed.")


if __name__ == "__main__":
    main()