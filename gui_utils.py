import tkinter as tk
import os
import logging

# --- Constants Defined Here ---
ICON_FILENAME = "oceans.ico"
MIN_BUTTON_WIDTH = 100
CURRENCY_SYMBOL = "₱"
APPROX_PRODUCT_BUTTON_WIDTH_WITH_SPACING = 120

# --- Key Product Names for UI ---
PRODUCT_REFILL_20 = "Refill (20)"
PRODUCT_REFILL_25 = "Refill (25)"
PRODUCT_CUSTOM_SALE = "Custom Sale"
PRODUCT_CONTAINER = "Container"

# --- Shared Colors for Listbox/Treeview Selection ---
LISTBOX_SELECT_BG = "#3CB371"
LISTBOX_SELECT_FG = "#FFFFFF"
# --- Status Bar Colors ---
STATUS_SUCCESS_BG = "#90EE90"
STATUS_SUCCESS_FG = "#006400"
STATUS_ERROR_BG = "#FFB6C1"
STATUS_ERROR_FG = "#A52A2A"
STATUS_INFO_BG = "#ADD8E6"
STATUS_INFO_FG = "#00008B"
STATUS_DEFAULT_BG = "#98FB98"
STATUS_DEFAULT_FG = "#006400"

# --- NEW: Custom Sale Button Colors ---
CUSTOM_SALE_BUTTON_BG = "#FFD700"  # Gold
CUSTOM_SALE_BUTTON_FG = "#4B0082"  # Indigo (for good contrast on gold)
CUSTOM_SALE_BUTTON_ACTIVE_BG = "#FFA500" # Orange (when active/hovered)


# --- Helper Function to Center Windows ---
def center_window(window, width=None, height=None):
    """Centers a tkinter window on the screen."""
    window.update_idletasks()
    try:
        w = width if width else window.winfo_width()
        h = height if height else window.winfo_height()
    except tk.TclError:
        w = width if width else window.winfo_reqwidth()
        h = height if height else window.winfo_reqheight()

    w = max(1, w)
    h = max(1, h)
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = max(0, (sw // 2) - (w // 2))
    y = max(0, (sh // 2) - (h // 2))
    window.geometry(f'{w}x{h}+{x}+{y}')


# --- Helper Function to Set Icon ---
def set_window_icon(window):
    """Sets the window icon, handling potential errors."""
    if os.path.exists(ICON_FILENAME):
        try:
            window.iconbitmap(ICON_FILENAME)
            logging.debug(f"Icon '{ICON_FILENAME}' set for window '{window.title()}'.")
        except tk.TclError as e:
            if "bitmap" in str(e).lower() and "not defined" in str(e).lower():
                 logging.warning(f"Could not set icon '{ICON_FILENAME}' for {window.title()}. "
                       f".ico format might not be supported on this OS/Tcl version.")
            else:
                logging.error(f"Error setting icon '{ICON_FILENAME}' for {window.title()}: {e}.")
        except Exception as e:
             logging.exception(f"Unexpected error setting icon for {window.title()}.")
    else:
         logging.warning(f"Icon file '{ICON_FILENAME}' not found for window '{window.title()}'.")
