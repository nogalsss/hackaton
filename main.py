import sys
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    app = root / "Front-end" / "app.py"

    if not app.exists():
        print(f"No encontré {app}")
        sys.exit(1)

    # Lanza Streamlit igual que si lo hicieras a mano
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app)], cwd=str(root))


if __name__ == "__main__":
    main()
