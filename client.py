import sys
import tkinter as tk

from interface import GameGUI

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python client.py <seu_nome>")
        sys.exit(1)

    root = tk.Tk()
    app = GameGUI(root, sys.argv[1])
    root.mainloop()
