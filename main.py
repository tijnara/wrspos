import tkinter as tk
from tkinter import messagebox

# --- Check Dependencies ---
try:
    from dateutil.relativedelta import relativedelta, MO, SU
except ImportError:
    messagebox.showerror("Missing Library",
                         "Required library 'python-dateutil' is not installed.\n"
                         "Please install it using:\n"
                         "pip install python-dateutil")
    exit()

try:
    from tkcalendar import DateEntry
except ImportError:
    print("Warning: 'tkcalendar' library not found. Date range summary will be disabled.")
    # We don't exit here, just disable the feature in the history window if opened
    pass

# --- Import GUI Class ---
# This assumes gui_classes.py is in the same directory
try:
    from gui_classes import POSApp
except ImportError as e:
     messagebox.showerror("Import Error",
                          f"Could not import necessary classes from gui_classes.py.\n"
                          f"Ensure the file exists in the same directory.\nError: {e}")
     exit()
except Exception as e: # Catch other potential errors during import
     messagebox.showerror("Error", f"An unexpected error occurred during import:\n{e}")
     exit()


# --- Run the Application ---
if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = POSApp(root)
        root.mainloop()
    except Exception as e:
        # Catch any unexpected error during app initialization or main loop
        messagebox.showerror("Application Error", f"An unexpected error occurred:\n{e}")
        print(f"FATAL ERROR: {e}")

