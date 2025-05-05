import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import filedialog
import datetime
import os
import sqlite3
import shutil
import logging # Added logging module

# --- External Libraries ---
from dateutil.relativedelta import relativedelta, MO, SU
try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None

# --- Import Project Modules ---
import db_operations
import gui_utils
from gui_dialogs import PriceInputDialog, CustomerSelectionDialog, CustomPriceDialog
from gui_customer_manager import CustomerListWindow
from gui_history_window import SalesHistoryWindow

# --- Configure Logging ---
# Basic configuration: Log INFO and above to a file, WARNING and above to console
logging.basicConfig(
    level=logging.INFO, # Set the minimum level for the file handler
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    filename='pos_app.log', # Log file name
    filemode='a' # Append to the log file
)
# Console handler for warnings and errors
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING) # Minimum level for console
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)


# --- Main Application Class ---
class POSApp:
    def __init__(self, root):
        """Initialize the POS Application."""
        logging.info("Initializing POS Application...")
        self.root = root
        self._configure_root_window()
        self._setup_styles()
        self._initialize_variables()
        self._setup_ui()
        self._bind_shortcuts()
        self._load_initial_data()
        logging.info("POS Application Initialized Successfully.")

    # --- Initialization and Setup Methods ---

    def _configure_root_window(self):
        """Configure the main application window."""
        self.root.title("SEASIDE Water Refilling Station - POS")
        app_width = 850
        app_height = 750
        self.root.geometry(f"{app_width}x{app_height}")
        self.root.minsize(700, 600)
        self.root.resizable(False, False)
        gui_utils.set_window_icon(self.root) # gui_utils might have its own logging/print
        gui_utils.center_window(self.root, app_width, app_height)
        # Configure main layout weights
        self.root.columnconfigure(0, weight=1) # Product frame column
        self.root.columnconfigure(1, weight=1) # Sale frame column
        self.root.rowconfigure(0, weight=1)    # Main content row
        self.root.rowconfigure(1, weight=0)    # Status bar row

    def _setup_styles(self):
        """Configures ttk styles for the application."""
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            logging.warning("'clam' theme not available, using default.") # Replaced print

        # --- Define Apple Green Theme Colors ---
        BG_COLOR = "#F0FFF0"       # Honeydew
        BUTTON_BG = "#98FB98"      # PaleGreen
        BUTTON_FG = "#006400"      # DarkGreen
        BUTTON_ACTIVE = "#90EE90"  # LightGreen
        FINALIZE_BG = "#3CB371"    # MediumSeaGreen
        FINALIZE_ACTIVE = "#66CDAA" # MediumAquaMarine
        LABEL_FG = "#2F4F4F"       # DarkSlateGray
        HEADER_FG = "#1E8449"      # Darker Green
        TOTAL_FG = "#006400"       # DarkGreen
        TREE_HEADING_BG = "#D0F0C0" # Tea Green Light
        TREE_HEADING_FG = "#1E8449" # Darker Green
        TREE_ROW_BG_ODD = "#FFFFFF" # White
        TREE_ROW_BG_EVEN = "#F5FFFA" # MintCream
        STATUS_BG = "#98FB98"      # PaleGreen
        STATUS_FG = "#006400"      # DarkGreen
        SELECT_BG = "#90EE90"      # LightGreen (for selections)
        # Define more prominent selection colors for listbox
        LISTBOX_SELECT_BG = "#3CB371" # MediumSeaGreen (matches finalize button)
        LISTBOX_SELECT_FG = "#FFFFFF" # White

        # --- Configure Styles ---
        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('App.TFrame', background=BG_COLOR)
        self.style.configure('TLabel', background=BG_COLOR, foreground=LABEL_FG, font=('Arial', 10))
        self.style.configure('Header.TLabel', background=BG_COLOR, foreground=HEADER_FG, font=('Arial', 12, 'bold'))
        self.style.configure('Total.TLabel', background=BG_COLOR, foreground=TOTAL_FG, font=('Arial', 14, 'bold'))
        self.style.configure('Status.TLabel', background=STATUS_BG, foreground=STATUS_FG, font=('Arial', 9))
        self.style.configure('TButton', background=BUTTON_BG, foreground=BUTTON_FG, font=('Arial', 9), padding=5, borderwidth=1, relief='raised')
        self.style.map('TButton', background=[('active', BUTTON_ACTIVE)])
        self.style.configure('Product.TButton', font=('Arial', 10, 'bold'), padding=(5, 10))
        self.style.configure('Action.TButton', padding=4, font=('Arial', 9))
        self.style.configure('Finalize.TButton', background=FINALIZE_BG, foreground='white', font=('Arial', 10, 'bold'), padding=6)
        self.style.map('Finalize.TButton', background=[('active', FINALIZE_ACTIVE)])
        self.style.configure("Custom.Treeview", rowheight=25, fieldbackground=TREE_ROW_BG_ODD, background=TREE_ROW_BG_ODD, foreground=LABEL_FG)
        self.style.map("Custom.Treeview", background=[('selected', SELECT_BG)])
        self.style.configure("Custom.Treeview.Heading", background=TREE_HEADING_BG, foreground=TREE_HEADING_FG, font=('Arial', 10, 'bold'), relief="flat")
        self.style.map("Custom.Treeview.Heading", background=[('active', BUTTON_ACTIVE)])
        self.style.configure('TEntry', fieldbackground='white', foreground='black')
        self.style.configure('TCombobox', fieldbackground='white', foreground='black')
        self.style.configure('TScrollbar', background=BUTTON_BG, troughcolor=BG_COLOR, borderwidth=0)
        self.style.map('TScrollbar', background=[('active', BUTTON_ACTIVE)])
        self.style.configure('TLabelFrame', background=BG_COLOR, borderwidth=1, relief="groove")
        self.style.configure('TLabelFrame.Label', background=BG_COLOR, foreground=HEADER_FG, font=('Arial', 11, 'bold'))

        # Store listbox selection colors for use in widget creation
        self.listbox_select_bg = LISTBOX_SELECT_BG
        self.listbox_select_fg = LISTBOX_SELECT_FG

    def _initialize_variables(self):
        """Initialize instance variables."""
        logging.info("Initializing database...")
        db_operations.initialize_db() # Ensure DB is ready
        logging.info("Database initialized.")
        self.products = self.load_products()
        self.current_sale = {}
        self.total_amount = 0.0
        self.history_window = None
        self.customer_list_window = None
        self.first_product_button = None
        self.status_bar_job = None
        self.current_customer_name = "N/A"
        self.status_var = tk.StringVar()
        self.customer_display_var = tk.StringVar(value=f"Customer: {self.current_customer_name}")

    def _setup_ui(self):
        """Create and layout the main UI components."""
        logging.debug("Setting up UI...")
        self._setup_menu()
        self._setup_frames()
        self._setup_status_bar()
        self._setup_product_panel()
        self._setup_sale_panel()
        logging.debug("UI setup complete.")

    def _setup_menu(self):
        """Creates the main menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Backup Database...", command=self.backup_database)
        file_menu.add_command(label="Restore Database...", command=self.restore_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

    def _setup_frames(self):
        """Create and grid the main frames."""
        self.product_frame = ttk.Frame(self.root, padding="5", style='App.TFrame')
        self.sale_frame = ttk.Frame(self.root, padding="5", style='App.TFrame')
        self.product_frame.grid(row=0, column=0, sticky="nsew")
        self.sale_frame.grid(row=0, column=1, sticky="nsew")

        # Configure product frame grid
        self.product_frame.columnconfigure(0, weight=1)
        self.product_frame.columnconfigure(1, weight=0)
        self.product_frame.rowconfigure(0, weight=0)
        self.product_frame.rowconfigure(1, weight=1) # Product button canvas row
        self.product_frame.rowconfigure(2, weight=0) # Separator/Label row
        self.product_frame.rowconfigure(3, weight=1) # Product management list area
        self.product_frame.rowconfigure(4, weight=0) # Mgmt buttons row

        # Configure sale frame grid
        self.sale_frame.columnconfigure(0, weight=1)
        self.sale_frame.columnconfigure(1, weight=0)
        self.sale_frame.rowconfigure(0, weight=0)
        self.sale_frame.rowconfigure(1, weight=1) # Sale Treeview row
        self.sale_frame.rowconfigure(2, weight=0)
        self.sale_frame.rowconfigure(3, weight=0)
        self.sale_frame.rowconfigure(4, weight=0)

    def _setup_status_bar(self):
        """Create the status bar."""
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2), style='Status.TLabel')
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky='ew')

    def _setup_product_panel(self):
        """Create widgets for the product selection and management panel."""
        # --- Product Buttons Area ---
        ttk.Label(self.product_frame, text="Add to Sale", font=("Arial", 12, "bold"), style='Header.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 2), sticky='w')
        self.product_canvas = tk.Canvas(self.product_frame, bg=self.style.lookup('App.TFrame', 'background'), highlightthickness=0)
        product_scrollbar = ttk.Scrollbar(self.product_frame, orient="vertical", command=self.product_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.product_canvas, style='App.TFrame')
        self.product_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="scrollable_frame") # Added tag
        self.product_canvas.configure(yscrollcommand=product_scrollbar.set)
        self.product_canvas.grid(row=1, column=0, sticky="nsew")
        product_scrollbar.grid(row=1, column=1, sticky="ns")
        # Bind events for scrolling and resizing
        self.scrollable_frame.bind('<Configure>', self._configure_scrollable_frame)
        self.product_canvas.bind('<Configure>', self._configure_scrollable_frame_width) # Bind canvas configure too

        # --- Product Management Area ---
        ttk.Separator(self.product_frame, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky='ew', pady=10)
        ttk.Label(self.product_frame, text="Manage Products", font=("Arial", 12, "bold"), style='Header.TLabel').grid(row=2, column=0, columnspan=2, pady=(5, 2), sticky='w')

        self.product_list_frame = ttk.Frame(self.product_frame, style='App.TFrame')
        self.product_list_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=2)
        self.product_list_frame.rowconfigure(0, weight=1)
        self.product_list_frame.columnconfigure(0, weight=1)
        # ***MODIFIED***: Apply new selection colors directly to the Listbox
        self.product_listbox = tk.Listbox(
            self.product_list_frame,
            exportselection=False,
            bg="#FFFFFF",
            fg="#000000",
            selectbackground=self.listbox_select_bg, # Use stored style color
            selectforeground=self.listbox_select_fg, # Use stored style color
            borderwidth=1,
            relief="sunken"
        )
        product_list_scrollbar = ttk.Scrollbar(self.product_list_frame, orient="vertical", command=self.product_listbox.yview)
        self.product_listbox.configure(yscrollcommand=product_list_scrollbar.set)
        self.product_listbox.grid(row=0, column=0, sticky="nsew")
        product_list_scrollbar.grid(row=0, column=1, sticky="ns")

        product_mgmt_button_frame = ttk.Frame(self.product_frame, style='App.TFrame')
        product_mgmt_button_frame.grid(row=4, column=0, columnspan=2, pady=5, sticky='w')
        self.add_product_button = ttk.Button(product_mgmt_button_frame, text="Add New Product", command=self.prompt_new_item, style='Action.TButton')
        self.edit_product_button = ttk.Button(product_mgmt_button_frame, text="Edit Product", command=self.prompt_edit_item, style='Action.TButton')
        self.remove_product_button = ttk.Button(product_mgmt_button_frame, text="Remove Product", command=self.remove_selected_product_permanently, style='Action.TButton')
        self.view_customers_button = ttk.Button(product_mgmt_button_frame, text="Manage Customers", command=self.view_customers, style='Action.TButton')
        self.add_product_button.pack(side=tk.LEFT, padx=2)
        self.edit_product_button.pack(side=tk.LEFT, padx=2)
        self.remove_product_button.pack(side=tk.LEFT, padx=2)
        self.view_customers_button.pack(side=tk.LEFT, padx=2)

    def _setup_sale_panel(self):
        """Create widgets for the current sale panel."""
        ttk.Label(self.sale_frame, text="Current Sale", font=("Arial", 14, "bold"), style='Header.TLabel').grid(row=0, column=0, columnspan=2, pady=5, sticky='w')

        # Sale Treeview
        columns = ("item", "quantity", "price", "subtotal")
        self.sale_tree = ttk.Treeview(self.sale_frame, columns=columns, show="headings", selectmode="browse", style="Custom.Treeview")
        self.sale_tree.heading("item", text="Item")
        self.sale_tree.heading("quantity", text="Qty")
        self.sale_tree.heading("price", text="Price")
        self.sale_tree.heading("subtotal", text="Subtotal")
        self.sale_tree.column("item", anchor=tk.W, width=150, stretch=True)
        self.sale_tree.column("quantity", anchor=tk.CENTER, width=40, stretch=False)
        self.sale_tree.column("price", anchor=tk.E, width=80, stretch=False)
        self.sale_tree.column("subtotal", anchor=tk.E, width=90, stretch=False)
        sale_scrollbar = ttk.Scrollbar(self.sale_frame, orient="vertical", command=self.sale_tree.yview)
        self.sale_tree.configure(yscrollcommand=sale_scrollbar.set)
        self.sale_tree.grid(row=1, column=0, sticky="nsew", padx=(5,0), pady=2)
        sale_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0,5), pady=2)

        # Customer Selection Area
        customer_frame = ttk.Frame(self.sale_frame, style='App.TFrame')
        customer_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=(5,2))
        customer_frame.columnconfigure(1, weight=1)
        self.select_customer_button = ttk.Button(customer_frame, text="Select Customer (Ctrl+C)", command=self.select_customer_for_sale, style='Action.TButton')
        self.customer_display_label = ttk.Label(customer_frame, textvariable=self.customer_display_var, anchor=tk.W, style='TLabel')
        self.select_customer_button.grid(row=0, column=0, padx=(0, 5))
        self.customer_display_label.grid(row=0, column=1, sticky='ew')

        # Finalize/Total Area
        finalize_total_frame = ttk.Frame(self.sale_frame, style='App.TFrame')
        finalize_total_frame.grid(row=3, column=0, columnspan=2, pady=(2,5), sticky="ew")
        finalize_total_frame.columnconfigure(0, weight=1)
        finalize_total_frame.columnconfigure(1, weight=0)
        finalize_total_frame.columnconfigure(2, weight=0)
        self.finalize_button = ttk.Button(finalize_total_frame, text="Finalize Sale (Ctrl+F)", command=self.finalize_sale, style='Finalize.TButton')
        self.total_label = ttk.Label(finalize_total_frame, text=f"{gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 14, "bold"), style='Total.TLabel')
        self.finalize_button.grid(row=0, column=1, padx=(5, 10), sticky="e")
        self.total_label.grid(row=0, column=2, padx=(0, 5), sticky="e")

        # Other Sale Action Buttons
        other_sale_actions_frame = ttk.Frame(self.sale_frame, style='App.TFrame')
        other_sale_actions_frame.grid(row=4, column=0, columnspan=2, pady=(0, 5), sticky="e")
        self.history_button = ttk.Button(other_sale_actions_frame, text="View History (Ctrl+H)", command=self.view_sales_history, style='Action.TButton')
        self.clear_button = ttk.Button(other_sale_actions_frame, text="Clear Sale", command=self.clear_sale, style='Action.TButton')
        self.remove_item_button = ttk.Button(other_sale_actions_frame, text="Remove Item", command=self.remove_selected_item_from_sale, style='Action.TButton')
        self.decrease_qty_button = ttk.Button(other_sale_actions_frame, text="- Qty", command=self.decrease_item_quantity, style='Action.TButton')
        # Pack buttons right-to-left
        self.history_button.pack(side=tk.RIGHT, padx=2)
        self.clear_button.pack(side=tk.RIGHT, padx=2)
        self.remove_item_button.pack(side=tk.RIGHT, padx=2)
        self.decrease_qty_button.pack(side=tk.RIGHT, padx=2)

    def _bind_shortcuts(self):
        """Binds keyboard shortcuts to application functions."""
        logging.debug("Binding keyboard shortcuts...")
        self.root.bind('<F1>', self.focus_first_product)
        self.root.bind('<Control-f>', lambda event=None: self.finalize_sale())
        self.root.bind('<Control-h>', lambda event=None: self.view_sales_history())
        self.root.bind('<Control-c>', lambda event=None: self.select_customer_for_sale())
        self.root.bind('<KeyPress-1>', self._handle_refill_20_shortcut)
        self.root.bind('<KeyPress-2>', self._handle_refill_25_shortcut)
        self.root.bind('<KeyPress-3>', self._handle_custom_price_shortcut)
        logging.debug("Shortcuts bound.")

    def _load_initial_data(self):
        """Load and display initial data after UI setup."""
        logging.info("Loading initial data...")
        self.populate_product_buttons()
        self.populate_product_management_list()
        self.update_sale_display()
        self.show_status("Ready", duration=None)
        logging.info("Initial data loaded.")

    # --- Action/Logic Methods (Remain largely unchanged) ---

    def show_status(self, message, duration=3000):
        """Displays a message in the status bar."""
        logging.debug(f"Status bar: '{message}' (duration: {duration})")
        self.status_var.set(message)
        if self.status_bar_job:
            self.root.after_cancel(self.status_bar_job)
            self.status_bar_job = None
        if duration:
            self.status_bar_job = self.root.after(duration, self.clear_status)

    def clear_status(self):
        """Clears the status bar."""
        logging.debug("Clearing status bar.")
        self.status_var.set("")
        self.status_bar_job = None

    def _handle_refill_20_shortcut(self, event=None):
        """Adds 'Refill (20)' to the sale."""
        product_name = "Refill (20)"
        logging.info(f"Shortcut '1' pressed for '{product_name}'.")
        if product_name in self.products: self.add_item(product_name)
        else:
            logging.warning(f"Product '{product_name}' not found for shortcut.")
            self.show_status(f"Product '{product_name}' not found.", 3000)

    def _handle_refill_25_shortcut(self, event=None):
        """Adds 'Refill (25)' to the sale."""
        product_name = "Refill (25)"
        logging.info(f"Shortcut '2' pressed for '{product_name}'.")
        if product_name in self.products: self.add_item(product_name)
        else:
            logging.warning(f"Product '{product_name}' not found for shortcut.")
            self.show_status(f"Product '{product_name}' not found.", 3000)

    def _handle_custom_price_shortcut(self, event=None):
        """Opens the custom price dialog."""
        logging.info("Shortcut '3' pressed, opening custom price dialog.")
        self.prompt_custom_item()

    def focus_first_product(self, event=None):
        """Sets focus to the first product button."""
        logging.debug("F1 pressed, attempting to focus first product button.")
        if self.first_product_button and self.first_product_button.winfo_exists():
            self.first_product_button.focus_set()
            self.show_status("Focused first product button (F1)", 2000)
            logging.debug("Focus set to first product button.")
        else:
            logging.warning("No product buttons found to focus (F1).")
            self.show_status("No product buttons found.", 2000)

    def backup_database(self):
        """Creates a backup copy of the database file."""
        source_db = db_operations.DATABASE_FILENAME
        logging.info(f"Initiating database backup from '{source_db}'.")
        if not os.path.exists(source_db):
            logging.error(f"Backup failed: Database file '{source_db}' not found.")
            messagebox.showerror("Backup Error", f"Database '{source_db}' not found.", parent=self.root)
            return
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_filename = f"pos_backup_{timestamp}.db"
        backup_path = filedialog.asksaveasfilename(parent=self.root, title="Save Backup As", initialfile=suggested_filename, defaultextension=".db", filetypes=[("DB files", "*.db"), ("All", "*.*")])
        if not backup_path:
            logging.info("Database backup cancelled by user.")
            self.show_status("Backup cancelled.", 3000)
            return
        try:
            shutil.copy2(source_db, backup_path)
            logging.info(f"Database successfully backed up to '{backup_path}'.")
            self.show_status(f"Backup successful: {os.path.basename(backup_path)}", 5000)
        except Exception as e:
            logging.exception(f"Error during database backup to '{backup_path}'.") # Includes traceback
            messagebox.showerror("Backup Failed", f"Error: {e}", parent=self.root)
            self.show_status("Backup failed.", 5000)


    def restore_database(self):
        """Restores the database from a backup file."""
        target_db = db_operations.DATABASE_FILENAME
        logging.warning("Database restore initiated.")
        warning_msg = "WARNING: Restoring will OVERWRITE current data!\nApplication will close. Restart manually.\nProceed?"
        if not messagebox.askyesno("Confirm Restore", warning_msg, icon='warning', parent=self.root):
            logging.info("Database restore cancelled by user confirmation.")
            self.show_status("Restore cancelled.", 3000)
            return
        backup_path = filedialog.askopenfilename(parent=self.root, title="Select Backup to Restore", filetypes=[("DB files", "*.db"), ("All", "*.*")])
        if not backup_path:
            logging.info("Database restore cancelled by user file selection.")
            self.show_status("Restore cancelled.", 3000)
            return
        if not os.path.exists(backup_path):
            logging.error(f"Restore failed: Selected backup file '{backup_path}' not found.")
            messagebox.showerror("Restore Error", "Backup file not found.", parent=self.root)
            return
        if not backup_path.lower().endswith(".db"):
             logging.warning(f"Selected restore file '{backup_path}' does not end with .db.")
             if not messagebox.askyesno("Confirm File Type", "File lacks .db extension. Restore anyway?", icon='warning', parent=self.root):
                 logging.info("Database restore cancelled due to file extension confirmation.")
                 self.show_status("Restore cancelled.", 3000)
                 return
        try:
            logging.info(f"Attempting restore from '{backup_path}' to '{target_db}'. Closing secondary windows.")
            # Attempt to close secondary windows gracefully
            if self.history_window and tk.Toplevel.winfo_exists(self.history_window):
                logging.debug("Destroying history window.")
                self.history_window.destroy()
            if self.customer_list_window and tk.Toplevel.winfo_exists(self.customer_list_window):
                logging.debug("Destroying customer list window.")
                self.customer_list_window.destroy()
            self.root.update_idletasks(); self.root.after(100) # Brief pause

            shutil.copy2(backup_path, target_db)
            logging.info(f"Database successfully restored from '{backup_path}'. Application will close.")
            messagebox.showinfo("Restore Successful", f"Restored from:\n{os.path.basename(backup_path)}\n\nApplication will close. Please restart.", parent=self.root)
            self.root.destroy()
        except Exception as e:
            logging.exception(f"Error during database restore from '{backup_path}'.") # Includes traceback
            messagebox.showerror("Restore Failed", f"Error: {e}", parent=self.root)
            self.show_status("Restore failed.", 5000)


    def _configure_scrollable_frame(self, event):
        """Reset the scroll region to encompass the inner frame."""
        self.product_canvas.configure(scrollregion=self.product_canvas.bbox("all"))

    def _configure_scrollable_frame_width(self, event):
        """Adjusts the width of the inner frame within the canvas."""
        # Only adjust width if the canvas exists and the frame window item exists
        if hasattr(self, 'product_canvas') and self.product_canvas.find_withtag("scrollable_frame"):
             # Check if width is valid (greater than 0)
             if event.width > 0:
                 self.product_canvas.itemconfigure("scrollable_frame", width=event.width)
             else:
                 logging.debug(f"Scrollable frame width configuration skipped due to zero width event.")


    def load_products(self):
        """Loads products from the SQLite database."""
        logging.info(f"Loading products from '{db_operations.DATABASE_FILENAME}'...")
        products = db_operations.fetch_products_from_db() # db_operations might log errors
        if not products:
             logging.warning("No products found in database.")
        else:
             logging.info(f"Loaded {len(products)} products.")
        return products

    def populate_product_buttons(self, available_width=None):
        """Populates the product buttons in the scrollable frame."""
        logging.debug("Populating product buttons...")
        # Clear existing buttons first
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.first_product_button = None # Reset focus target

        # --- Define the desired order and specific items ---
        refill_20_name = "Refill (20)"
        refill_25_name = "Refill (25)"
        custom_sale_name = "Custom Sale"
        other_priority = ["Container"]

        ordered_products_for_buttons = []
        remaining_products = self.products.copy()

        def add_product_if_exists(name):
            if name in remaining_products:
                ordered_products_for_buttons.append((name, remaining_products[name]))
                del remaining_products[name]
                return True
            logging.debug(f"Product '{name}' not found in remaining products for priority ordering.")
            return False

        # --- Apply the specific order ---
        add_product_if_exists(refill_20_name)
        add_product_if_exists(refill_25_name)
        custom_sale_exists = custom_sale_name in remaining_products
        if custom_sale_exists:
            ordered_products_for_buttons.append((custom_sale_name, remaining_products[custom_sale_name]))
            del remaining_products[custom_sale_name]
        else:
            logging.warning(f"Product '{custom_sale_name}' not found, button will not be created.")

        for name in other_priority: add_product_if_exists(name)
        ordered_products_for_buttons.extend(sorted(remaining_products.items()))

        # --- Grid layout logic ---
        max_cols = 4
        for i in range(max_cols): self.scrollable_frame.columnconfigure(i, weight=1)

        row_num, col_num = 0, 0
        for idx, (name, price) in enumerate(ordered_products_for_buttons):
            btn_text = f"{name}\n({gui_utils.CURRENCY_SYMBOL}{price:.2f})"
            # Determine command based on product name
            button_command = self.prompt_custom_item if name == custom_sale_name else lambda n=name: self.add_item(n)

            btn = ttk.Button(self.scrollable_frame, text=btn_text, command=button_command, style='Product.TButton')
            btn.grid(row=row_num, column=col_num, padx=2, pady=2, sticky="ew")
            if idx == 0: self.first_product_button = btn # Set F1 focus target

            col_num = (col_num + 1) % max_cols
            if col_num == 0: row_num += 1

        # Update scroll region
        self.scrollable_frame.update_idletasks()
        self.product_canvas.configure(scrollregion=self.product_canvas.bbox("all"))
        # Explicitly set the width of the inner frame initially
        self.root.update_idletasks() # Ensure canvas width is calculated
        if hasattr(self, 'product_canvas') and self.product_canvas.find_withtag("scrollable_frame"):
             canvas_width = self.product_canvas.winfo_width()
             if canvas_width > 0:
                 self.product_canvas.itemconfigure("scrollable_frame", width=canvas_width)
        logging.debug("Product buttons populated.")


    def populate_product_management_list(self):
        """Clears and repopulates the product management listbox."""
        logging.debug("Populating product management list...")
        self.product_listbox.delete(0, tk.END)
        for name, price in sorted(self.products.items()):
            self.product_listbox.insert(tk.END, f"{name} ({gui_utils.CURRENCY_SYMBOL}{price:.2f})")
        logging.debug("Product management list populated.")

    def _get_selected_product_details(self):
        """Gets name and price of the selected product in the listbox."""
        indices = self.product_listbox.curselection()
        if not indices:
            logging.warning("Attempted action without selecting a product in management list.")
            messagebox.showwarning("No Selection", "Select a product first.", parent=self.root)
            return None, None
        selected_text = self.product_listbox.get(indices[0])
        try:
            parts = selected_text.split(f' ({gui_utils.CURRENCY_SYMBOL}')
            if len(parts) == 2:
                name = parts[0].strip()
                price = float(parts[1].rstrip(')').strip())
                logging.debug(f"Selected product details: Name='{name}', Price={price}")
                return name, price
            raise ValueError(f"Format error: {selected_text}")
        except Exception as e:
             logging.exception(f"Error parsing product details from listbox text: '{selected_text}'") # Includes traceback
             messagebox.showerror("Error", f"Parse error: {e}", parent=self.root)
             return None, None

    def prompt_new_item(self):
        """Prompts for new product details and adds it."""
        logging.info("Prompting for new product.")
        name = simpledialog.askstring("New Product", "Name:", parent=self.root)
        if not name or not name.strip():
            logging.info("New product entry cancelled or empty.")
            return
        name = name.strip()
        if name in self.products:
             logging.warning(f"Attempted to add duplicate product: '{name}'.")
             messagebox.showwarning("Exists", f"'{name}' already exists.", parent=self.root)
             return
        price_dialog = PriceInputDialog(self.root, "New Price", f"Price for {name}:")
        price = price_dialog.result
        if price is not None:
            logging.info(f"Attempting to add new product: Name='{name}', Price={price}")
            if db_operations.insert_product_to_db(name, price): # db_operations should log errors
                self.products[name] = price
                self.populate_product_buttons()
                self.populate_product_management_list()
                logging.info(f"Product '{name}' added successfully.")
                self.show_status(f"'{name}' added.", 3000)
            # else: db_operations handles showing messagebox on failure

    def prompt_edit_item(self):
        """Prompts for updated details of a selected product."""
        logging.info("Initiating edit product prompt.")
        original_name, original_price = self._get_selected_product_details()
        if original_name is None: return # Message shown in helper
        new_name = simpledialog.askstring("Edit Name", "New name:", initialvalue=original_name, parent=self.root)
        if not new_name or not new_name.strip():
            logging.info("Product name edit cancelled or empty.")
            return
        new_name = new_name.strip()
        price_dialog = PriceInputDialog(self.root, "Edit Price", f"New price for {new_name}:", initialvalue=f"{original_price:.2f}")
        new_price = price_dialog.result
        if new_price is not None:
            logging.info(f"Attempting to update product '{original_name}' to Name='{new_name}', Price={new_price}")
            if new_name != original_name and new_name in self.products:
                 logging.warning(f"Edit failed: Product name '{new_name}' already exists.")
                 messagebox.showerror("Exists", f"'{new_name}' already exists.", parent=self.root)
                 return
            if db_operations.update_product_in_db(original_name, new_name, new_price): # db_operations should log errors
                if original_name in self.products: del self.products[original_name]
                self.products[new_name] = new_price
                self.populate_product_buttons()
                self.populate_product_management_list()
                logging.info(f"Product '{original_name}' updated successfully to '{new_name}'.")
                self.show_status(f"'{original_name}' updated.", 3000)
            # else: db_operations handles showing messagebox on failure

    def remove_selected_product_permanently(self):
        """Permanently removes the selected product."""
        logging.info("Initiating remove product prompt.")
        product_name, _ = self._get_selected_product_details()
        if product_name is None: return # Message shown in helper
        if messagebox.askyesno("Confirm Delete", f"Delete '{product_name}' permanently?", parent=self.root):
            logging.warning(f"Attempting permanent deletion of product '{product_name}'.")
            if db_operations.delete_product_from_db(product_name): # db_operations should log errors
                if product_name in self.products: del self.products[product_name]
                self.populate_product_buttons()
                self.populate_product_management_list()
                logging.info(f"Product '{product_name}' deleted successfully.")
                self.show_status(f"'{product_name}' deleted.", 3000)
            # else: db_operations handles showing messagebox on failure
        else:
            logging.info(f"Deletion of product '{product_name}' cancelled by user.")
            self.show_status("Product deletion cancelled.", 2000)


    def add_item(self, name, override_price=None, quantity_to_add=1):
        """Adds an item to the current sale."""
        current_price = override_price if override_price is not None else self.products.get(name)
        if current_price is None:
             logging.error(f"Attempted to add non-existent product '{name}'.")
             messagebox.showerror("Error", f"Product '{name}' not found.", parent=self.root)
             return
        item_key = f"{name}__{current_price:.2f}"
        if item_key in self.current_sale:
             self.current_sale[item_key]['quantity'] += quantity_to_add
             logging.info(f"Incremented quantity for '{name}' (Price: {current_price:.2f}) by {quantity_to_add}. New quantity: {self.current_sale[item_key]['quantity']}.")
        else:
            self.current_sale[item_key] = {'name': name, 'price': current_price, 'quantity': quantity_to_add}
            logging.info(f"Added new item '{name}' (Price: {current_price:.2f}, Quantity: {quantity_to_add}) to sale.")
        self.show_status(f"Added {quantity_to_add} x {name}", 2000)
        self.update_sale_display()

    def prompt_custom_item(self):
        """Opens dialog for custom price/quantity item."""
        logging.info("Opening custom price/quantity dialog.")
        product_names_list = sorted(list(self.products.keys()))
        if not product_names_list:
            logging.warning("Cannot open custom price dialog: No products defined.")
            messagebox.showwarning("No Products", "No products defined.", parent=self.root)
            return
        dialog = CustomPriceDialog(self.root, product_names_list)
        result = dialog.result
        if result:
            name, price, qty = result
            logging.info(f"Custom item details received: Name='{name}', Price={price}, Quantity={qty}.")
            self.add_item(name, override_price=price, quantity_to_add=qty)
        else:
            logging.info("Custom price/quantity dialog cancelled.")

    def decrease_item_quantity(self):
        """Decreases quantity of selected item in the sale."""
        selected_id = self.sale_tree.focus()
        if not selected_id:
            logging.warning("Attempted to decrease quantity with no item selected.")
            messagebox.showwarning("No Selection", "Select item to decrease.", parent=self.root)
            return
        if selected_id in self.current_sale:
            item_name = self.current_sale[selected_id]['name']
            current_quantity = self.current_sale[selected_id]['quantity']
            if current_quantity > 1:
                self.current_sale[selected_id]['quantity'] -= 1
                logging.info(f"Decreased quantity for '{item_name}'. New quantity: {self.current_sale[selected_id]['quantity']}.")
                self.show_status(f"Decreased {item_name} qty.", 2000)
            else:
                del self.current_sale[selected_id]
                logging.info(f"Removed '{item_name}' from sale (quantity was 1).")
                self.show_status(f"Removed {item_name}.", 2000)
            self.update_sale_display(preserve_selection=selected_id if selected_id in self.current_sale else None)
        else:
            logging.error(f"Attempted to decrease quantity for non-existent sale item key '{selected_id}'.")


    def remove_selected_item_from_sale(self):
        """Removes selected item from the current sale."""
        selected_id = self.sale_tree.focus()
        if not selected_id:
            logging.warning("Attempted to remove item with no item selected.")
            messagebox.showwarning("No Selection", "Select item to remove.", parent=self.root)
            return
        if selected_id in self.current_sale:
            item_name = self.current_sale[selected_id]['name']
            if messagebox.askyesno("Confirm Remove", f"Remove '{item_name}'?", parent=self.root):
                logging.info(f"Removing item '{item_name}' (key: {selected_id}) from sale.")
                del self.current_sale[selected_id]
                self.update_sale_display()
                self.show_status(f"Removed {item_name}.", 3000)
            else:
                logging.info(f"Removal of item '{item_name}' cancelled by user.")
                self.show_status("Item removal cancelled.", 2000)
        else:
            logging.error(f"Attempted to remove non-existent sale item key '{selected_id}'.")


    def update_sale_display(self, preserve_selection=None):
        """Updates the sale Treeview and total."""
        logging.debug("Updating sale display...")
        # Ensure tags are configured (safe to call multiple times)
        try:
            self.sale_tree.tag_configure('oddrow', background="#FFFFFF")
            self.sale_tree.tag_configure('evenrow', background="#F5FFFA")
        except tk.TclError: pass # Ignore if style not ready

        for i in self.sale_tree.get_children(): self.sale_tree.delete(i)
        self.total_amount = 0.0
        new_selection_id = None
        for i, (key, details) in enumerate(sorted(self.current_sale.items(), key=lambda item: item[1]['name'])):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            subtotal = details['price'] * details['quantity']
            item_id = self.sale_tree.insert("", tk.END, iid=key, values=(details['name'], details['quantity'], f"{gui_utils.CURRENCY_SYMBOL}{details['price']:.2f}", f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"), tags=(tag,))
            if preserve_selection == key: new_selection_id = item_id
            self.total_amount += subtotal
        self.total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{self.total_amount:.2f}")
        if new_selection_id:
            logging.debug(f"Reselecting item in sale tree: {new_selection_id}")
            self.sale_tree.focus(new_selection_id)
            self.sale_tree.selection_set(new_selection_id)
        else:
             self.sale_tree.focus(''); self.sale_tree.selection_set('')
        logging.debug(f"Sale display updated. Total: {self.total_amount:.2f}")

    def clear_sale(self):
        """Clears the current sale."""
        if not self.current_sale:
            logging.info("Clear sale requested, but sale is already empty.")
            self.show_status("Sale is already empty.", 2000)
            return
        if messagebox.askyesno("Confirm Clear", "Clear current sale?", parent=self.root):
            logging.info("Clearing current sale.")
            self.current_sale = {}
            self.current_customer_name = "N/A"
            self.customer_display_var.set(f"Customer: {self.current_customer_name}")
            self.update_sale_display()
            self.show_status("Sale cleared.", 3000)
            logging.info("Sale cleared successfully.")
        else:
            logging.info("Clear sale cancelled by user.")
            self.show_status("Clear sale cancelled.", 2000)


    def select_customer_for_sale(self):
        """Opens dialog to select customer for the sale."""
        logging.info("Opening customer selection dialog.")
        dialog = CustomerSelectionDialog(self.root)
        name = dialog.result
        if name is not None:
            self.current_customer_name = name
            self.customer_display_var.set(f"Customer: {self.current_customer_name}")
            logging.info(f"Customer selected for sale: '{self.current_customer_name}'.")
            self.show_status(f"Customer: {self.current_customer_name}", 3000)
        else:
            logging.info("Customer selection cancelled.")
            self.show_status("Customer selection cancelled.", 2000)


    def generate_receipt_text(self, sale_id, timestamp_obj, customer_name):
        """Generates text for the sale receipt."""
        receipt = f"--- SEASIDE Water Refilling Station ---\n"
        receipt += f"Sale ID: {sale_id}\n"
        receipt += f"Date: {timestamp_obj.strftime('%Y-%m-%d %H:%M:%S')}\n"
        receipt += f"Customer: {customer_name}\n"
        receipt += "--------------------------------------\n"
        receipt += "{:<18} {:>3} {:>7} {:>8}\n".format("Item", "Qty", "Price", "Subtotal")
        receipt += "--------------------------------------\n"
        for details in sorted(self.current_sale.values(), key=lambda item: item['name']):
            subtotal = details['quantity'] * details['price']
            receipt += "{:<18} {:>3d} {:>7} {:>8}\n".format(
                details['name'][:18], details['quantity'],
                f"{gui_utils.CURRENCY_SYMBOL}{details['price']:.2f}",
                f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"
            )
        receipt += "======================================\n"
        receipt += "{:<29} {:>8}\n".format("TOTAL:", f"{gui_utils.CURRENCY_SYMBOL}{self.total_amount:.2f}")
        receipt += "--------------------------------------\n"
        receipt += "        Thank you!\n"
        return receipt

    def finalize_sale(self):
        """Finalizes the current sale, saves to DB, shows receipt."""
        logging.info("Attempting to finalize sale.")
        if not self.current_sale:
             logging.warning("Finalize sale failed: Sale is empty.")
             messagebox.showwarning("Empty Sale", "Cannot finalize empty sale.", parent=self.root)
             return
        if self.current_customer_name == "N/A":
            logging.warning("Finalize sale failed: No customer selected.")
            messagebox.showwarning("No Customer", "Select customer first.", parent=self.root)
            return
        ts = datetime.datetime.now()
        items_for_db = {d['name']: {'price': d['price'], 'quantity': d['quantity']} for d in self.current_sale.values()}
        logging.info(f"Finalizing sale for customer '{self.current_customer_name}' with {len(items_for_db)} distinct item types.")
        sale_id = db_operations.save_sale_record(ts, self.total_amount, self.current_customer_name)
        if sale_id and db_operations.save_sale_items_records(sale_id, items_for_db):
            receipt = self.generate_receipt_text(sale_id, ts, self.current_customer_name)
            logging.info(f"Sale {sale_id} successfully saved to database.")
            logging.debug(f"--- Receipt {sale_id} ---\n{receipt}\n---------------") # Log receipt details at debug level
            messagebox.showinfo(f"Sale Finalized - ID: {sale_id}", receipt, parent=self.root)
            # Clear sale state after successful save and receipt display
            self.current_sale = {}
            self.current_customer_name = "N/A"
            self.customer_display_var.set(f"Customer: {self.current_customer_name}")
            self.update_sale_display()
            self.show_status(f"Sale {sale_id} recorded.", 3000)
        else:
            logging.error(f"Failed to save sale record or items for customer '{self.current_customer_name}'. Sale ID received: {sale_id}")
            self.show_status("Error saving sale.", 5000) # Keep status generic for user

    def view_sales_history(self):
        """Opens the sales history window."""
        logging.info("Opening sales history window.")
        if DateEntry is None:
             logging.error("Cannot open sales history: tkcalendar library not found.")
             messagebox.showerror("Missing Library", "tkcalendar not installed.\npip install tkcalendar", parent=self.root)
             return
        if self.history_window is None or not tk.Toplevel.winfo_exists(self.history_window):
            logging.debug("Creating new SalesHistoryWindow instance.")
            self.history_window = SalesHistoryWindow(self.root)
            self.history_window.grab_set()
        else:
            logging.debug("Bringing existing SalesHistoryWindow to front.")
            self.history_window.deiconify(); self.history_window.lift(); self.history_window.focus_set(); self.history_window.grab_set()

    def view_customers(self):
        """Opens the customer management window."""
        logging.info("Opening customer management window.")
        if self.customer_list_window is None or not tk.Toplevel.winfo_exists(self.customer_list_window):
            logging.debug("Creating new CustomerListWindow instance.")
            self.customer_list_window = CustomerListWindow(self.root)
            self.customer_list_window.grab_set()
        else:
            logging.debug("Bringing existing CustomerListWindow to front.")
            self.customer_list_window.deiconify(); self.customer_list_window.lift(); self.customer_list_window.focus_set(); self.customer_list_window.grab_set()

