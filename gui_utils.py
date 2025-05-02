import tkinter as tk
import os

# --- Constants Defined Here ---
ICON_FILENAME = "oceans.ico" # Using the requested icon name
MIN_BUTTON_WIDTH = 100 # Minimum width in pixels for product buttons
CURRENCY_SYMBOL = "₱" # Moved from db_operations for easier GUI access if needed elsewhere

# --- Helper Function to Center Windows ---
def center_window(window, width=None, height=None):
    """Centers a tkinter window on the screen."""
    window.update_idletasks() # Ensure window dimensions are calculated
    w = width if width else window.winfo_reqwidth()
    h = height if height else window.winfo_reqheight()
    # Ensure width and height are positive before calculating position
    w = max(1, w)
    h = max(1, h)
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    window.geometry(f'{w}x{h}+{x}+{y}')


# --- Helper Function to Set Icon ---
def set_window_icon(window):
    """Sets the window icon, handling potential errors."""
    if os.path.exists(ICON_FILENAME):
        try:
            window.iconbitmap(ICON_FILENAME)
        except tk.TclError as e:
            # More specific error message for common .ico issues on non-Windows
            if "bitmap" in str(e).lower() and "not defined" in str(e).lower():
                 print(f"Warning: Could not set icon '{ICON_FILENAME}' for {window.title()}. "
                       f".ico format might not be supported on this OS or Tcl/Tk version. "
                       f"Consider using .png or .gif with PhotoImage if needed.")
            else:
                print(f"Error setting icon '{ICON_FILENAME}' for {window.title()}: {e}.")
        except Exception as e:
             print(f"An unexpected error occurred while setting icon for {window.title()}: {e}")
    else:
         print(f"Warning: Icon file '{ICON_FILENAME}' not found for {window.title()}.")

