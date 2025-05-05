import tkinter as tk
from tkinter import messagebox
import logging # Import logging

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
    # Log warning instead of printing
    logging.warning("'tkcalendar' library not found. Date range summary will be disabled.")
    pass

# --- Import Application Logic Class ---
# Import the main logic class which now handles UI creation internally
try:
    from pos_app_logic import POSAppLogic
except ImportError as e:
     # Log the error before showing messagebox
     logging.exception("Failed to import POSAppLogic from pos_app_logic.py.")
     messagebox.showerror("Import Error",
                          f"Could not import necessary classes from pos_app_logic.py.\n"
                          f"Ensure the file exists in the same directory.\nError: {e}")
     exit()
except Exception as e: # Catch other potential errors during import
     logging.exception("An unexpected error occurred during application import.")
     messagebox.showerror("Error", f"An unexpected error occurred during import:\n{e}")
     exit()


# --- Configure Logging (Call basicConfig here, once) ---
logging.basicConfig(
    level=logging.INFO, # Minimum level for file logging
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    filename='pos_app.log', # Log file name
    filemode='a' # Append mode
)
# Console handler for warnings and errors
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING) # Minimum level for console output
formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s') # Simpler console format
console_handler.setFormatter(formatter)
# Add console handler to the root logger
logging.getLogger().addHandler(console_handler)


# --- Run the Application ---
if __name__ == "__main__":
    logging.info("Application starting...")
    root = tk.Tk()
    try:
        # Instantiate the logic class, which handles UI creation
        app_logic = POSAppLogic(root)
        root.mainloop()
        logging.info("Application finished.")
    except Exception as e:
        # Catch any unexpected error during app initialization or main loop
        logging.exception("An unhandled error occurred during application execution.") # Log traceback
        messagebox.showerror("Application Error", f"An unexpected error occurred:\n{e}")

