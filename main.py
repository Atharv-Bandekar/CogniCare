from src.database.db import init_db
from src.ui.app import CogniCareApp


def main():
    # Initialize DB Schema
    init_db()

    # Launch CustomTkinter App
    app = CogniCareApp()
    app.mainloop()


if __name__ == "__main__":
    main()