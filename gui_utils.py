import tkinter as tk
import os
import logging # Added logging

# --- Constants Defined Here ---
ICON_FILENAME = "oceans.ico" # Using the requested icon name
MIN_BUTTON_WIDTH = 100 # Minimum width in pixels for product buttons
CURRENCY_SYMBOL = "₱" # Moved from db_operations for easier GUI access if needed elsewhere

# --- Key Product Names for UI ---\
# Define names used for specific buttons/shortcuts here
# IMPORTANT: These MUST exactly match the ProductName in the database
PRODUCT_REFILL_20 = "Refill (20)"
PRODUCT_REFILL_25 = "Refill (25)"
PRODUCT_CUSTOM_SALE = "Custom Sale" # Name of the button that triggers custom price dialog
PRODUCT_CONTAINER = "Container" # Example if you want to prioritize this too

# --- NEW CONSTANT for dynamic button layout ---
APPROX_PRODUCT_BUTTON_WIDTH_WITH_SPACING = 120 # Estimated total width a button needs (button width + horizontal spacing)


# --- Helper Function to Center Windows ---
def center_window(window, width=None, height=None):
    """Centers a tkinter window on the screen."""
    window.update_idletasks() # Ensure window dimensions are calculated
    # Use winfo_width/height if available after update, fallback to reqwidth/height
    try:
        w = width if width else window.winfo_width()
        h = height if height else window.winfo_height()
    except tk.TclError: # Fallback if window info isn't ready
        w = width if width else window.winfo_reqwidth()
        h = height if height else window.winfo_reqheight()

    # Ensure width and height are positive before calculating position
    w = max(1, w)
    h = max(1, h)
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    # Calculate position, ensuring it's not negative
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
            # More specific error message for common .ico issues on non-Windows
            if "bitmap" in str(e).lower() and "not defined" in str(e).lower():
                 logging.warning(f"Could not set icon '{ICON_FILENAME}' for {window.title()}. "
                       f".ico format might not be supported on this OS/Tcl version.")
            else:
                logging.error(f"Error setting icon '{ICON_FILENAME}' for {window.title()}: {e}.")
        except Exception as e:
             logging.exception(f"Unexpected error setting icon for {window.title()}.") # Log traceback
    else:
         logging.warning(f"Icon file '{ICON_FILENAME}' not found for window '{window.title()}'.")
