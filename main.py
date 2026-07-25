import tkinter as tk
from src.database.db import init_db
from src.ui.app import CogniCareApp


def main():
    # Initialize DB Schema
    init_db()
    
    # Launch UI
    root = tk.Tk()
    app = CogniCareApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()