import sys
import os
from cx_Freeze import setup, Executable

# --- !!! IMPORTANT: Update this path if necessary !!! ---
# Find your base Python installation directory (not the venv)
# Example: C:\Users\YourUser\AppData\Local\Programs\Python\Python311
# You can often find it by activating your venv and running:
# python -c "import sys; print(sys.base_prefix)"
PYTHON_INSTALL_DIR = os.path.dirname(os.path.dirname(os.__file__))
# --- Adjust TCL/TK version if needed (check folders in PYTHON_INSTALL_DIR\tcl) ---
TCL_VERSION = "tcl8.6"
TK_VERSION = "tk8.6"

# Define paths to TCL/TK DLLs and libraries relative to the Python installation
TCL_DLL = os.path.join(PYTHON_INSTALL_DIR, 'DLLs', 'tcl86t.dll') # Adjust 86 if needed
TK_DLL = os.path.join(PYTHON_INSTALL_DIR, 'DLLs', 'tk86t.dll')   # Adjust 86 if needed
TCL_LIB_PATH = os.path.join(PYTHON_INSTALL_DIR, 'tcl', TCL_VERSION)
TK_LIB_PATH = os.path.join(PYTHON_INSTALL_DIR, 'tcl', TK_VERSION)

# Check if DLLs and Lib paths exist
if not os.path.exists(TCL_DLL):
    print(f"ERROR: Cannot find {TCL_DLL}")
if not os.path.exists(TK_DLL):
    print(f"ERROR: Cannot find {TK_DLL}")
if not os.path.exists(TCL_LIB_PATH):
    print(f"ERROR: Cannot find {TCL_LIB_PATH}")
if not os.path.exists(TK_LIB_PATH):
    print(f"ERROR: Cannot find {TK_LIB_PATH}")


# --- Application Information ---
APP_NAME = "SEASIDE Water Refilling Station POS"
VERSION = "1.0"
DESCRIPTION = "Point of Sale system for SEASIDE Water Refilling Station"
AUTHOR = "SEASIDEWRS" # Replace with your name/company
MAIN_SCRIPT = "main.py"
ICON_FILE = "oceans.ico"
# Optional: Database file to include (will be placed next to exe)
# Set to None if you don't want to include an initial DB
DATABASE_FILE = "pos_system.db"

# --- Build Options ---

# Files to include directly alongside the executable
# We include the icon and optionally the database
include_files = [(ICON_FILE, ICON_FILE)]
if DATABASE_FILE and os.path.exists(DATABASE_FILE):
    include_files.append((DATABASE_FILE, DATABASE_FILE))
else:
    print(f"Warning: Database file '{DATABASE_FILE}' not found, not including.")

# Include TCL/TK libraries explicitly for Tkinter to work reliably
# The destination path should match the expected structure
include_files.extend([
    (TCL_DLL, os.path.basename(TCL_DLL)), # Copy DLLs to root build dir
    (TK_DLL, os.path.basename(TK_DLL)),
    (TCL_LIB_PATH, f"lib/{TCL_VERSION}"), # Copy tcl8.6 folder into lib/tcl8.6
    (TK_LIB_PATH, f"lib/{TK_VERSION}")    # Copy tk8.6 folder into lib/tk8.6
])


# Dependencies are usually detected automatically, but adding them explicitly can help.
# Especially needed for libraries used indirectly or via plugins.
packages_to_include = ["tkinter", "sqlite3", "datetime", "os", "dateutil", "tkcalendar"]

# Exclude packages you know you don't need (optional, can reduce size)
packages_to_exclude = []

build_exe_options = {
    "packages": packages_to_include,
    "excludes": packages_to_exclude,
    "include_files": include_files,
    # "include_msvcr": True, # Include MS VC++ runtime (good for portability) - Requires appropriate runtime installed or bundled
}

# --- Base for GUI applications on Windows ---
# Use "Win32GUI" to hide the console window. Use None for console apps.
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# --- Executable Definition ---
executables = [
    Executable(
        MAIN_SCRIPT,
        base=base,
        target_name="SeasidePOS.exe", # Name of the output executable
        icon=ICON_FILE
    )
]

# --- MSI Installer Options (Optional) ---
# For creating a simple MSI installer directly
# Requires cx_Freeze >= 6.0
msi_options = {
    "add_to_path": False, # Don't add application to system PATH
    "initial_target_dir": rf"%ProgramFiles%\{APP_NAME}", # Install location
    # Add upgrades code for handling updates smoothly
    # Generate a new GUID for each version: https://www.guidgenerator.com/
    "upgrade_code": "{PUT-YOUR-UPGRADE-GUID-HERE}", # !!! IMPORTANT: Generate a unique GUID !!!
}

setup_options = {
    "build_exe": build_exe_options,
    "bdist_msi": msi_options,
}


# --- Setup Function ---
setup(
    name=APP_NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    options=setup_options,
    executables=executables
)

print("\n--- Build Process Complete ---")
print(f"Executable and dependencies should be in the 'build\\exe...' folder.")
print(f"If you ran 'bdist_msi', the MSI installer should be in the 'dist' folder.")
