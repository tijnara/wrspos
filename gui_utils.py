import tkinter as tk
import os
import logging
from tkinter import ttk

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


# --- Fonts ---
DEFAULT_FONT = ("Arial", 10)
HEADER_FONT = ("Arial", 12, "bold")
BUTTON_FONT = ("Arial", 10, "bold")

# --- Theme Colors ---
PRIMARY_COLOR = "#4CAF50"  # Green
SECONDARY_COLOR = "#FFFFFF"  # White
TEXT_COLOR = "#000000"  # Black

# --- Dark Mode Theme Colors ---
DARK_PRIMARY_COLOR = "#2E2E2E"  # Dark gray
DARK_SECONDARY_COLOR = "#1C1C1C"  # Almost black
DARK_TEXT_COLOR = "#FFFFFF"  # White

# --- Function to Toggle Themes ---
current_theme = "light"

def toggle_theme():
    """Toggles between light and dark themes."""
    global current_theme
    if current_theme == "light":
        current_theme = "dark"
        ttk.Style().configure("TButton", background=DARK_PRIMARY_COLOR, foreground=DARK_TEXT_COLOR)
    else:
        current_theme = "light"
        ttk.Style().configure("TButton", background=PRIMARY_COLOR, foreground=TEXT_COLOR)

# --- Utility Function for Styling Buttons ---
def style_button(button):
    """Applies consistent styling to a button."""
    button.configure(
        bg=PRIMARY_COLOR,
        fg=SECONDARY_COLOR,
        font=BUTTON_FONT,
        activebackground="#45a049",
        activeforeground=SECONDARY_COLOR
    )

# --- Utility Function for Styling Labels ---
def style_label(label):
    """Applies consistent styling to a label."""
    label.configure(
        bg=SECONDARY_COLOR,
        fg=TEXT_COLOR,
        font=DEFAULT_FONT
    )

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

class Tooltip:
    """Create a tooltip for a given widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, _, cy = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0,0,0,0)
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()
