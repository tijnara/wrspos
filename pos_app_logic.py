import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import filedialog
import datetime
import os
# import sqlite3 # Not directly used here, db_operations handles it
import shutil
import logging

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
from pos_app_ui import POSAppUI


# --- Configure Logging ---
# Assuming basicConfig called in main.py by the main application script.
# If this module were run standalone, basicConfig would be needed here.
# logger = logging.getLogger(__name__) # It's good practice for modules to get their own logger

# --- Main Application Logic Class ---
class POSAppLogic:
    def __init__(self, root):
        """Initialize the POS Application Logic."""
        logging.info("Initializing POS Application Logic...")
        self.root = root
        self._initialize_variables()
        self._setup_styles()  # Style setup needs to happen before UI creation if UI uses styled widgets
        self.ui = POSAppUI(root, self.style)  # Pass the configured style to the UI
        self._connect_ui_commands()
        self._bind_shortcuts()
        self._load_initial_data()
        logging.info("POS Application Logic Initialized Successfully.")

    # --- Initialization and Setup Methods ---

    def _initialize_variables(self):
        """Initialize instance variables for logic."""
        logging.info("Initializing database...")
        db_operations.initialize_db()  # Ensure DB is ready
        logging.info("Database initialized.")
        self.products = self.load_products()
        self.current_sale = {}  # Stores items in the current transaction
        self.total_amount = 0.0
        self.history_window = None  # Reference to SalesHistoryWindow instance
        self.customer_list_window = None  # Reference to CustomerListWindow instance
        self.status_bar_job = None  # For managing status bar auto-clear
        self.current_customer_name = "N/A"  # Default customer
        # StringVars for UI elements are now managed within self.ui (POSAppUI instance)

    def _setup_styles(self):
        """Configures ttk styles for the application."""
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use('clam')  # A common theme that works well
        except tk.TclError:
            logging.warning("'clam' theme not available, using default.")

        # --- Define Theme Colors (Example: Apple Green Theme) ---
        BG_COLOR = "#F0FFF0"  # Honeydew (overall background)
        BUTTON_BG = "#98FB98"  # PaleGreen (standard buttons)
        BUTTON_FG = "#006400"  # DarkGreen (text on standard buttons)
        BUTTON_ACTIVE = "#90EE90"  # LightGreen (button when hovered/pressed)
        FINALIZE_BG = "#3CB371"  # MediumSeaGreen (finalize sale button)
        FINALIZE_ACTIVE = "#66CDAA"  # MediumAquaMarine (finalize active)
        LABEL_FG = "#2F4F4F"  # DarkSlateGray (standard labels)
        HEADER_FG = "#1E8449"  # Darker Green (for header labels)
        TOTAL_FG = "#006400"  # DarkGreen (for the total amount display)
        TREE_HEADING_BG = "#D0F0C0"  # Tea Green Light (Treeview headings)
        TREE_HEADING_FG = "#1E8449"  # Darker Green (text on Treeview headings)
        TREE_ROW_BG_ODD = "#FFFFFF"  # White (odd rows in Treeview)
        TREE_ROW_BG_EVEN = "#F5FFFA"  # MintCream (even rows in Treeview)
        STATUS_BG = "#98FB98"  # PaleGreen (status bar background)
        STATUS_FG = "#006400"  # DarkGreen (status bar text)
        LISTBOX_SELECT_BG = "#3CB371"  # MediumSeaGreen (selected item in Listbox)
        LISTBOX_SELECT_FG = "#FFFFFF"  # White (text of selected item in Listbox)

        # --- Configure Styles ---
        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('App.TFrame', background=BG_COLOR)  # Specific style for main frames
        self.style.configure('TLabel', background=BG_COLOR, foreground=LABEL_FG, font=('Arial', 10))
        self.style.configure('Header.TLabel', background=BG_COLOR, foreground=HEADER_FG, font=('Arial', 12, 'bold'))
        self.style.configure('Total.TLabel', background=BG_COLOR, foreground=TOTAL_FG, font=('Arial', 14, 'bold'))
        self.style.configure('Status.TLabel', background=STATUS_BG, foreground=STATUS_FG, font=('Arial', 9))
        self.style.configure('TButton', background=BUTTON_BG, foreground=BUTTON_FG, font=('Arial', 9), padding=5,
                             borderwidth=1, relief='raised')
        self.style.map('TButton', background=[('active', BUTTON_ACTIVE)])
        self.style.configure('Product.TButton', font=('Arial', 10, 'bold'),
                             padding=(5, 10))  # Larger padding for product buttons
        self.style.configure('Action.TButton', padding=4, font=('Arial', 9))  # Smaller action buttons
        self.style.configure('Finalize.TButton', background=FINALIZE_BG, foreground='white', font=('Arial', 10, 'bold'),
                             padding=6)
        self.style.map('Finalize.TButton', background=[('active', FINALIZE_ACTIVE)])
        # Custom Treeview style for alternating row colors and selection
        self.style.configure("Custom.Treeview", rowheight=25, fieldbackground=TREE_ROW_BG_ODD,
                             background=TREE_ROW_BG_ODD, foreground=LABEL_FG)
        self.style.map("Custom.Treeview", background=[('selected', LISTBOX_SELECT_BG)],
                       foreground=[('selected', LISTBOX_SELECT_FG)])  # Use listbox selection colors for tree
        self.style.configure("Custom.Treeview.Heading", background=TREE_HEADING_BG, foreground=TREE_HEADING_FG,
                             font=('Arial', 10, 'bold'), relief="flat")
        self.style.map("Custom.Treeview.Heading",
                       background=[('active', BUTTON_ACTIVE)])  # Optional: highlight heading on active
        self.style.configure('TEntry', fieldbackground='white', foreground='black')
        self.style.configure('TCombobox', fieldbackground='white', foreground='black')
        self.style.configure('TScrollbar', background=BUTTON_BG, troughcolor=BG_COLOR, borderwidth=0)
        self.style.map('TScrollbar', background=[('active', BUTTON_ACTIVE)])
        self.style.configure('TLabelFrame', background=BG_COLOR, borderwidth=1, relief="groove")
        self.style.configure('TLabelFrame.Label', background=BG_COLOR, foreground=HEADER_FG, font=('Arial', 11, 'bold'))

        # Store listbox selection colors for UI class if it needs them directly (e.g., for tk.Listbox)
        self.style.listbox_select_bg = LISTBOX_SELECT_BG
        self.style.listbox_select_fg = LISTBOX_SELECT_FG

    def _connect_ui_commands(self):
        """Connect button commands from the UI instance to logic methods."""
        logging.debug("Connecting UI commands to logic...")
        # Product Management Buttons
        self.ui.add_product_button.config(command=self.prompt_new_item)
        self.ui.edit_product_button.config(command=self.prompt_edit_item)
        self.ui.remove_product_button.config(command=self.remove_selected_product_permanently)
        self.ui.view_customers_button.config(command=self.view_customers)

        # Sale Panel Buttons
        self.ui.select_customer_button.config(command=self.select_customer_for_sale)
        self.ui.finalize_button.config(command=self.finalize_sale)
        self.ui.history_button.config(command=self.view_sales_history)
        self.ui.clear_button.config(command=self.clear_sale)
        self.ui.remove_item_button.config(command=self.remove_selected_item_from_sale)
        self.ui.decrease_qty_button.config(command=self.decrease_item_quantity)

        # Menu commands are setup in _setup_menu which is called by POSAppUI if menu is part of UI
        # If menu is directly on root here, then _setup_menu needs to be called here.
        # Based on previous structure, menu was part of POSApp (now POSAppLogic)
        self._setup_menu()

        # Bind scrollable frame events (these are UI interactions, but logic needs to respond)
        self.ui.scrollable_frame.bind('<Configure>', self._configure_scrollable_frame)
        self.ui.product_canvas.bind('<Configure>', self._configure_scrollable_frame_width)

        logging.debug("UI commands connected.")

    def _setup_menu(self):
        """Creates the main menu bar and connects commands."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)  # Attach menubar to the root window

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Backup Database...", command=self.backup_database)
        file_menu.add_command(label="Restore Database...", command=self.restore_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        # Add more menus (e.g., "Manage", "View") as needed

    def _bind_shortcuts(self):
        """Binds keyboard shortcuts to application functions."""
        logging.debug("Binding keyboard shortcuts...")
        self.root.bind('<F1>', self.focus_first_product)
        self.root.bind('<Control-f>', lambda event=None: self.finalize_sale())  # Ctrl+F for Finalize
        self.root.bind('<Control-h>', lambda event=None: self.view_sales_history())  # Ctrl+H for History
        self.root.bind('<Control-c>', lambda event=None: self.select_customer_for_sale())  # Ctrl+C for Customer
        # Number shortcuts for quick add (ensure these products exist or handle gracefully)
        self.root.bind('<KeyPress-1>', self._handle_refill_20_shortcut)
        self.root.bind('<KeyPress-2>', self._handle_refill_25_shortcut)
        self.root.bind('<KeyPress-3>', self._handle_custom_price_shortcut)  # For "Custom Sale"
        logging.debug("Shortcuts bound.")

    def _load_initial_data(self):
        """Load and display initial data after UI setup."""
        logging.info("Loading initial data...")
        self.populate_product_buttons()  # Populates product buttons in the UI
        self.populate_product_management_list()  # Populates the listbox for managing products
        self.update_sale_display()  # Clears and updates the current sale treeview
        self._update_latest_customer_label()  # Fetch and display the latest customer
        self.show_status("Ready", duration=None)  # Set initial status bar message
        logging.info("Initial data loaded.")

    def _update_latest_customer_label(self):
        """Fetches and updates the label showing the latest used customer via the UI instance."""
        logging.debug("Updating latest used customer label.")
        latest_name = db_operations.fetch_latest_customer_name()  # Fetch from DB
        display_text = f"Latest Customer: {latest_name}" if latest_name else "Latest Customer: None"
        if hasattr(self.ui, 'latest_customer_name_var'):  # Check if UI element exists
            self.ui.latest_customer_name_var.set(display_text)
        logging.debug(f"Latest customer label set to: '{display_text}'")

    # --- Action/Logic Methods ---

    def show_status(self, message, duration=3000):
        """Displays a message in the status bar via the UI instance."""
        logging.debug(f"Status bar: '{message}' (duration: {duration})")
        if hasattr(self.ui, 'status_var'):  # Ensure UI and its var are initialized
            self.ui.status_var.set(message)
            if self.status_bar_job:
                self.root.after_cancel(self.status_bar_job)
                self.status_bar_job = None
            if duration:  # If duration is None, message stays until cleared or overwritten
                self.status_bar_job = self.root.after(duration, self.clear_status)

    def clear_status(self):
        """Clears the status bar via the UI instance."""
        logging.debug("Clearing status bar.")
        if hasattr(self.ui, 'status_var'):
            self.ui.status_var.set("")
        self.status_bar_job = None  # Clear any pending job

    def _handle_refill_20_shortcut(self, event=None):
        """Adds 'Refill (20)' to the sale using constant from gui_utils."""
        product_name = gui_utils.PRODUCT_REFILL_20
        logging.info(f"Shortcut '1' pressed for '{product_name}'.")
        if product_name in self.products:
            self.add_item(product_name)
        else:
            logging.warning(f"Product '{product_name}' not found for shortcut.")
            self.show_status(f"Product '{product_name}' not found.", 3000)

    def _handle_refill_25_shortcut(self, event=None):
        """Adds 'Refill (25)' to the sale using constant from gui_utils."""
        product_name = gui_utils.PRODUCT_REFILL_25
        logging.info(f"Shortcut '2' pressed for '{product_name}'.")
        if product_name in self.products:
            self.add_item(product_name)
        else:
            logging.warning(f"Product '{product_name}' not found for shortcut.")
            self.show_status(f"Product '{product_name}' not found.", 3000)

    def _handle_custom_price_shortcut(self, event=None):
        """Opens the custom price dialog (associated with "Custom Sale" product)."""
        logging.info("Shortcut '3' pressed, opening custom price dialog.")
        self.prompt_custom_item()  # This method handles the "Custom Sale" logic

    def focus_first_product(self, event=None):
        """Sets focus to the first product button in the UI."""
        logging.debug("F1 pressed, attempting to focus first product button.")
        if hasattr(self.ui,
                   'first_product_button') and self.ui.first_product_button and self.ui.first_product_button.winfo_exists():
            self.ui.first_product_button.focus_set()
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
        backup_path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Backup As",
            initialfile=suggested_filename,
            defaultextension=".db",
            filetypes=[("DB files", "*.db"), ("All files", "*.*")]
        )
        if not backup_path:
            logging.info("Database backup cancelled by user.")
            self.show_status("Backup cancelled.", 3000)
            return
        try:
            shutil.copy2(source_db, backup_path)
            logging.info(f"Database successfully backed up to '{backup_path}'.")
            self.show_status(f"Backup successful: {os.path.basename(backup_path)}", 5000)
        except Exception as e:
            logging.exception(f"Error during database backup to '{backup_path}'.")
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

        backup_path = filedialog.askopenfilename(
            parent=self.root,
            title="Select Backup to Restore",
            filetypes=[("DB files", "*.db"), ("All files", "*.*")]
        )
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
            if not messagebox.askyesno("Confirm File Type", "File lacks .db extension. Restore anyway?", icon='warning',
                                       parent=self.root):
                logging.info("Database restore cancelled due to file extension confirmation.")
                self.show_status("Restore cancelled.", 3000)
                return
        try:
            logging.info(f"Attempting restore from '{backup_path}' to '{target_db}'. Closing secondary windows.")
            # Attempt to close secondary windows gracefully before restore
            if self.history_window and tk.Toplevel.winfo_exists(self.history_window):
                logging.debug("Destroying history window before restore.")
                self.history_window.destroy()
            if self.customer_list_window and tk.Toplevel.winfo_exists(self.customer_list_window):
                logging.debug("Destroying customer list window before restore.")
                self.customer_list_window.destroy()

            self.root.update_idletasks()  # Process window closures
            self.root.after(100)  # Brief pause to allow UI to settle

            shutil.copy2(backup_path, target_db)
            logging.info(f"Database successfully restored from '{backup_path}'. Application will close.")
            messagebox.showinfo("Restore Successful",
                                f"Restored from:\n{os.path.basename(backup_path)}\n\nApplication will close. Please restart.",
                                parent=self.root)
            self.root.destroy()  # Close the application
        except Exception as e:
            logging.exception(f"Error during database restore from '{backup_path}'.")
            messagebox.showerror("Restore Failed", f"Error: {e}", parent=self.root)
            self.show_status("Restore failed.", 5000)

    def _configure_scrollable_frame(self, event):
        """Callback to reset the scroll region of the product canvas based on the scrollable_frame's content."""
        if hasattr(self.ui, 'product_canvas') and self.ui.product_canvas:
            self.ui.product_canvas.configure(scrollregion=self.ui.product_canvas.bbox("all"))

    def _configure_scrollable_frame_width(self, event):
        """Callback to adjust the width of the inner frame in the product canvas to match the canvas width."""
        if hasattr(self.ui, 'product_canvas') and self.ui.product_canvas.find_withtag("scrollable_frame"):
            if event.width > 0:  # Ensure valid width
                self.ui.product_canvas.itemconfigure("scrollable_frame", width=event.width)
            else:
                logging.debug(f"Scrollable frame width configuration skipped due to zero width event.")

    def load_products(self):
        """Loads products from the database via db_operations."""
        logging.info(f"Loading products from '{db_operations.DATABASE_FILENAME}'...")
        products = db_operations.fetch_products_from_db()  # This function in db_operations should handle its own errors/logging
        if not products:
            logging.warning("No products found in database.")
        else:
            logging.info(f"Loaded {len(products)} products.")
        return products

    def populate_product_buttons(self, available_width=None):
        """Populates the product buttons in the UI's scrollable frame."""
        logging.debug("Populating product buttons...")
        # Ensure UI elements are ready
        if not hasattr(self.ui, 'scrollable_frame') or not hasattr(self.ui, 'product_canvas'):
            logging.error("UI elements for product buttons not initialized. Cannot populate.")
            return

        scrollable_frame = self.ui.scrollable_frame
        product_canvas = self.ui.product_canvas

        for widget in scrollable_frame.winfo_children(): widget.destroy()  # Clear existing buttons
        self.ui.first_product_button = None  # Reset F1 focus target in UI

        # Define product order using constants from gui_utils
        refill_20_name = gui_utils.PRODUCT_REFILL_20
        refill_25_name = gui_utils.PRODUCT_REFILL_25
        custom_sale_name = gui_utils.PRODUCT_CUSTOM_SALE
        other_priority = [gui_utils.PRODUCT_CONTAINER]  # Example, can be extended

        ordered_products_for_buttons = []
        remaining_products = self.products.copy()  # Work with a copy

        def add_product_if_exists(name):  # Helper to add to ordered list
            if name in remaining_products:
                ordered_products_for_buttons.append((name, remaining_products[name]))
                del remaining_products[name]  # Remove from remaining to avoid duplication
                return True
            logging.debug(f"Product '{name}' not found in remaining products for priority ordering.")
            return False

        # Apply the specific order
        add_product_if_exists(refill_20_name)
        add_product_if_exists(refill_25_name)

        custom_sale_exists = custom_sale_name in remaining_products  # Check if "Custom Sale" product exists
        if custom_sale_exists:
            # "Custom Sale" product might have a price of 0.00 in DB, it's a trigger
            ordered_products_for_buttons.append((custom_sale_name, remaining_products[custom_sale_name]))
            del remaining_products[custom_sale_name]
        else:
            logging.warning(f"Product '{custom_sale_name}' not found in database, its button will not be created.")

        for name in other_priority:  # Add other priority items
            if name: add_product_if_exists(name)  # Check if name is not None/empty

        # Add remaining products, sorted alphabetically
        ordered_products_for_buttons.extend(sorted(remaining_products.items()))

        # Grid layout logic for buttons
        max_cols = 4  # Number of columns for product buttons
        for i in range(max_cols): scrollable_frame.columnconfigure(i, weight=1,
                                                                   uniform="prod_btn_col")  # Ensure columns resize uniformly

        row_num, col_num = 0, 0
        for idx, (name, price) in enumerate(ordered_products_for_buttons):
            btn_text = f"{name}\n({gui_utils.CURRENCY_SYMBOL}{price:.2f})"
            # "Custom Sale" button triggers a special dialog, others add item directly
            button_command = self.prompt_custom_item if name == custom_sale_name else lambda n=name: self.add_item(n)

            btn = ttk.Button(scrollable_frame, text=btn_text, command=button_command, style='Product.TButton')
            btn.grid(row=row_num, column=col_num, padx=2, pady=2, sticky="ew")
            if idx == 0: self.ui.first_product_button = btn  # Set F1 focus target to the very first button

            col_num = (col_num + 1) % max_cols
            if col_num == 0: row_num += 1

        scrollable_frame.update_idletasks()  # Ensure frame dimensions are updated
        product_canvas.configure(scrollregion=product_canvas.bbox("all"))  # Update scroll region

        # Explicitly set the width of the inner frame initially after population
        self.root.update_idletasks()  # Ensure canvas width is calculated
        if hasattr(self.ui, 'product_canvas') and product_canvas.find_withtag("scrollable_frame"):
            canvas_width = product_canvas.winfo_width()
            if canvas_width > 0: product_canvas.itemconfigure("scrollable_frame", width=canvas_width)
        logging.debug("Product buttons populated.")

    def populate_product_management_list(self):
        """Populates the product management listbox in the UI."""
        logging.debug("Populating product management list...")
        if hasattr(self.ui, 'product_listbox') and self.ui.product_listbox:
            self.ui.product_listbox.delete(0, tk.END)  # Clear existing items
            for name, price in sorted(self.products.items()):  # Sort products alphabetically
                self.ui.product_listbox.insert(tk.END, f"{name} ({gui_utils.CURRENCY_SYMBOL}{price:.2f})")
        logging.debug("Product management list populated.")

    def _get_selected_product_details(self):
        """Gets details (name, price) from the selected product in the UI's listbox."""
        if not hasattr(self.ui, 'product_listbox') or not self.ui.product_listbox:
            logging.error("Product listbox not available in UI to get selection.")
            return None, None

        indices = self.ui.product_listbox.curselection()
        if not indices:  # No item selected
            logging.warning("Action attempted without product selection in management list.")
            messagebox.showwarning("No Selection", "Select a product from the list first.", parent=self.root)
            return None, None

        selected_text = self.ui.product_listbox.get(indices[0])
        try:
            # Parsing logic: "ProductName (₱Price)"
            parts = selected_text.split(f' ({gui_utils.CURRENCY_SYMBOL}')
            if len(parts) == 2:
                name = parts[0].strip()
                price_str = parts[1].rstrip(')').strip()
                price = float(price_str)
                logging.debug(f"Selected product for management: Name='{name}', Price={price}")
                return name, price
            raise ValueError(f"Unexpected format in listbox: {selected_text}")
        except Exception as e:
            logging.exception(f"Error parsing product details from listbox text: '{selected_text}'")
            messagebox.showerror("Parse Error", f"Could not parse product details from list.\nError: {e}",
                                 parent=self.root)
            return None, None

    def prompt_new_item(self):
        """Prompts for new product details and adds it to the database and UI."""
        logging.info("Prompting for new product.")
        name = simpledialog.askstring("New Product", "Enter Product Name:", parent=self.root)
        if not name or not name.strip():
            logging.info("New product entry cancelled or name was empty.")
            return
        name = name.strip()

        if name in self.products:  # Check if product already exists (case-sensitive for dict keys)
            logging.warning(f"Attempted to add duplicate product: '{name}'.")
            messagebox.showwarning("Product Exists", f"A product named '{name}' already exists.", parent=self.root)
            return

        price_dialog = PriceInputDialog(self.root, "New Product Price", f"Enter Price for {name}:")
        price = price_dialog.result  # This dialog returns float or None

        if price is not None:  # User entered a price and clicked OK
            logging.info(f"Attempting to add new product: Name='{name}', Price={price}")
            if db_operations.insert_product_to_db(name, price):  # db_operations handles its own error messages
                self.products[name] = price  # Add to local cache
                self.populate_product_buttons()  # Refresh product buttons
                self.populate_product_management_list()  # Refresh management list
                logging.info(f"Product '{name}' added successfully.")
                self.show_status(f"Product '{name}' added.", 3000)
            # else: db_operations.insert_product_to_db shows its own error messagebox on failure
        else:
            logging.info("Price entry for new product cancelled.")

    def prompt_edit_item(self):
        """Prompts for updated details of a selected product."""
        logging.info("Initiating edit product process.")
        original_name, original_price = self._get_selected_product_details()
        if original_name is None: return  # Message already shown by _get_selected_product_details

        new_name = simpledialog.askstring("Edit Product Name", "Enter New Name:", initialvalue=original_name,
                                          parent=self.root)
        if not new_name or not new_name.strip():
            logging.info("Product name edit cancelled or name was empty.")
            return
        new_name = new_name.strip()

        price_dialog = PriceInputDialog(self.root, "Edit Product Price", f"Enter New Price for {new_name}:",
                                        initialvalue=f"{original_price:.2f}")
        new_price = price_dialog.result

        if new_price is not None:  # User entered a price and clicked OK
            logging.info(f"Attempting to update product '{original_name}' to Name='{new_name}', Price={new_price}")
            # Check if the new name conflicts with an *existing different* product
            if new_name != original_name and new_name in self.products:
                logging.warning(f"Edit failed: New product name '{new_name}' already exists for a different product.")
                messagebox.showerror("Name Exists", f"A product named '{new_name}' already exists.", parent=self.root)
                return

            if db_operations.update_product_in_db(original_name, new_name, new_price):
                # Update local cache
                if original_name in self.products:
                    del self.products[original_name]
                self.products[new_name] = new_price

                self.populate_product_buttons()  # Refresh UI
                self.populate_product_management_list()
                logging.info(f"Product '{original_name}' updated successfully to '{new_name}'.")
                self.show_status(f"Product '{original_name}' updated.", 3000)
            # else: db_operations.update_product_in_db shows its own error messagebox
        else:
            logging.info("Price entry for product edit cancelled.")

    def remove_selected_product_permanently(self):
        """Permanently removes the selected product from database and UI."""
        logging.info("Initiating remove product process.")
        product_name, _ = self._get_selected_product_details()  # We only need the name for deletion
        if product_name is None: return  # Message shown in helper

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete '{product_name}'?",
                               parent=self.root):
            logging.warning(f"Attempting permanent deletion of product '{product_name}'.")
            if db_operations.delete_product_from_db(product_name):
                if product_name in self.products:
                    del self.products[product_name]  # Remove from local cache

                self.populate_product_buttons()  # Refresh UI
                self.populate_product_management_list()
                logging.info(f"Product '{product_name}' deleted successfully.")
                self.show_status(f"Product '{product_name}' deleted.", 3000)
            # else: db_operations.delete_product_from_db shows its own error messagebox
        else:
            logging.info(f"Deletion of product '{product_name}' cancelled by user.")
            self.show_status("Product deletion cancelled.", 2000)

    def add_item(self, name, override_price=None, quantity_to_add=1):
        """Adds an item to the current sale dictionary and updates UI."""
        current_price = override_price if override_price is not None else self.products.get(name)

        if current_price is None:  # Should not happen if products are loaded correctly
            logging.error(f"Attempted to add non-existent or price-less product '{name}'.")
            messagebox.showerror("Product Error", f"Product '{name}' not found or has no price.", parent=self.root)
            return

        # Use a key that combines name and price to handle items with same name but different prices (e.g. custom price)
        item_key = f"{name}__{current_price:.2f}"

        if item_key in self.current_sale:
            self.current_sale[item_key]['quantity'] += quantity_to_add
            logging.info(
                f"Incremented quantity for '{name}' (Price: {current_price:.2f}) by {quantity_to_add}. New quantity: {self.current_sale[item_key]['quantity']}.")
        else:
            self.current_sale[item_key] = {'name': name, 'price': current_price, 'quantity': quantity_to_add}
            logging.info(f"Added new item '{name}' (Price: {current_price:.2f}, Quantity: {quantity_to_add}) to sale.")

        self.show_status(f"Added {quantity_to_add} x {name}", 2000)
        self.update_sale_display()

    def prompt_custom_item(self):
        """Opens dialog for adding an item with a custom price/quantity."""
        logging.info("Opening custom price/quantity dialog.")
        product_names_list = sorted(list(self.products.keys()))  # Get available product names

        if not product_names_list:  # Check if there are any products to select from
            logging.warning("Cannot open custom price dialog: No products defined in the system.")
            messagebox.showwarning("No Products", "No products are defined. Please add products first.",
                                   parent=self.root)
            return

        dialog = CustomPriceDialog(self.root, product_names_list)  # Pass product names for combobox
        result = dialog.result  # This dialog returns (name, price, qty) or None

        if result:
            name, price, qty = result
            logging.info(f"Custom item details received: Name='{name}', Price={price}, Quantity={qty}.")
            self.add_item(name, override_price=price, quantity_to_add=qty)  # Add to sale
        else:
            logging.info("Custom price/quantity dialog cancelled.")

    def decrease_item_quantity(self):
        """Decreases quantity of selected item in the sale UI, or removes if quantity becomes zero."""
        if not hasattr(self.ui, 'sale_tree') or not self.ui.sale_tree: return

        selected_id = self.ui.sale_tree.focus()  # Get the IID of the focused item
        if not selected_id:  # No item selected
            logging.warning("Attempted to decrease quantity with no item selected in sale tree.")
            messagebox.showwarning("No Selection", "Please select an item from the sale to decrease its quantity.",
                                   parent=self.root)
            return

        if selected_id in self.current_sale:  # selected_id is the item_key
            item_name = self.current_sale[selected_id]['name']
            current_quantity = self.current_sale[selected_id]['quantity']

            if current_quantity > 1:
                self.current_sale[selected_id]['quantity'] -= 1
                logging.info(
                    f"Decreased quantity for '{item_name}'. New quantity: {self.current_sale[selected_id]['quantity']}.")
                self.show_status(f"Decreased {item_name} quantity.", 2000)
            else:  # Quantity is 1, so decreasing it means removing the item
                del self.current_sale[selected_id]
                logging.info(f"Removed '{item_name}' from sale (quantity was 1 and was decreased).")
                self.show_status(f"Removed {item_name}.", 2000)

            # Update display, try to preserve selection if item still exists
            self.update_sale_display(preserve_selection=selected_id if selected_id in self.current_sale else None)
        else:
            logging.error(
                f"Attempted to decrease quantity for non-existent sale item key '{selected_id}'. This might indicate a mismatch between UI and internal sale state.")

    def remove_selected_item_from_sale(self):
        """Removes selected item entirely from the current sale UI."""
        if not hasattr(self.ui, 'sale_tree') or not self.ui.sale_tree: return

        selected_id = self.ui.sale_tree.focus()  # Get IID of focused item
        if not selected_id:
            logging.warning("Attempted to remove item with no item selected in sale tree.")
            messagebox.showwarning("No Selection", "Please select an item from the sale to remove.", parent=self.root)
            return

        if selected_id in self.current_sale:  # selected_id is the item_key
            item_name = self.current_sale[selected_id]['name']
            if messagebox.askyesno("Confirm Remove", f"Remove '{item_name}' from the current sale?", parent=self.root):
                logging.info(f"Removing item '{item_name}' (key: {selected_id}) from sale upon user confirmation.")
                del self.current_sale[selected_id]
                self.update_sale_display()  # Refresh the sale display
                self.show_status(f"Removed {item_name}.", 3000)
            else:
                logging.info(f"Removal of item '{item_name}' cancelled by user.")
                self.show_status("Item removal cancelled.", 2000)
        else:
            logging.error(
                f"Attempted to remove non-existent sale item key '{selected_id}'. Mismatch between UI and sale state likely.")

    def update_sale_display(self, preserve_selection=None):
        """Updates the sale Treeview and total amount in the UI."""
        logging.debug("Updating sale display...")
        if not hasattr(self.ui, 'sale_tree') or not hasattr(self.ui, 'total_label'):
            logging.error("Sale tree or total label not available in UI. Cannot update sale display.")
            return

        sale_tree = self.ui.sale_tree
        total_label = self.ui.total_label

        # Configure tags for alternating row colors (safe to call multiple times)
        try:
            sale_tree.tag_configure('oddrow', background=self.style.lookup("Custom.Treeview",
                                                                           "background"))  # Use base background for odd
            sale_tree.tag_configure('evenrow', background="#F5FFFA")  # MintCream for even
        except tk.TclError:
            logging.warning("Could not configure Treeview tags, style might not be fully ready.")
            pass

        for i in sale_tree.get_children(): sale_tree.delete(i)  # Clear existing items

        self.total_amount = 0.0
        new_selection_id = None  # To reselect item if preserve_selection is used

        # Sort items by name for consistent display
        sorted_sale_items = sorted(self.current_sale.items(), key=lambda item: item[1]['name'])

        for i, (key, details) in enumerate(sorted_sale_items):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            subtotal = details['price'] * details['quantity']
            # Insert item into treeview, using 'key' (which is "name__price") as IID
            item_id_in_tree = sale_tree.insert("", tk.END, iid=key, values=(
                details['name'],
                details['quantity'],
                f"{gui_utils.CURRENCY_SYMBOL}{details['price']:.2f}",
                f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"
            ), tags=(tag,))

            if preserve_selection == key:  # If this item was meant to be reselected
                new_selection_id = item_id_in_tree  # Store its IID in the tree

            self.total_amount += subtotal

        total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{self.total_amount:.2f}")

        if new_selection_id:  # If an item needs to be reselected
            logging.debug(f"Reselecting item in sale tree: {new_selection_id}")
            sale_tree.focus(new_selection_id)
            sale_tree.selection_set(new_selection_id)
        else:  # Otherwise, clear focus and selection
            sale_tree.focus('');
            sale_tree.selection_set('')

        logging.debug(f"Sale display updated. Total amount: {self.total_amount:.2f}")

    def clear_sale(self):
        """Clears the current sale data and resets customer in UI."""
        if not self.current_sale:  # If sale is already empty
            logging.info("Clear sale requested, but sale is already empty.")
            self.show_status("Sale is already empty.", 2000)
            return

        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the current sale?", parent=self.root):
            logging.info("Clearing current sale upon user confirmation.")
            self.current_sale = {}  # Reset sale data
            self.current_customer_name = "N/A"  # Reset customer
            if hasattr(self.ui, 'customer_display_var'):
                self.ui.customer_display_var.set(f"Customer: {self.current_customer_name}")
            self.update_sale_display()  # Refresh UI
            self.show_status("Sale cleared.", 3000)
            logging.info("Sale cleared successfully.")
        else:
            logging.info("Clear sale cancelled by user.")
            self.show_status("Clear sale cancelled.", 2000)

    def select_customer_for_sale(self):
        """Opens dialog to select or enter a customer for the current sale."""
        logging.info("Opening customer selection dialog for current sale.")
        dialog = CustomerSelectionDialog(self.root)  # Parent is the main root window
        name = dialog.result  # Dialog handles its own logic, returns name or None

        if name is not None:  # If a name was selected/entered and OK was pressed
            self.current_customer_name = name
            if hasattr(self.ui, 'customer_display_var'):
                self.ui.customer_display_var.set(f"Customer: {self.current_customer_name}")
            logging.info(f"Customer selected for sale: '{self.current_customer_name}'.")
            self.show_status(f"Customer set to: {self.current_customer_name}", 3000)
        else:  # Dialog was cancelled
            logging.info("Customer selection cancelled.")
            self.show_status("Customer selection cancelled.", 2000)

    def generate_receipt_text(self, sale_id, timestamp_obj, customer_name):
        """Generates formatted text for the sale receipt."""
        receipt = f"--- SEASIDE Water Refilling Station ---\n"
        receipt += f"Official Receipt\n"
        receipt += f"Sale ID: {sale_id}\n"
        receipt += f"Date: {timestamp_obj.strftime('%Y-%m-%d %H:%M:%S')}\n"
        receipt += f"Customer: {customer_name}\n"
        receipt += "--------------------------------------\n"
        receipt += "{:<18} {:>3} {:>7} {:>8}\n".format("Item", "Qty", "Price", "Subtotal")
        receipt += "--------------------------------------\n"

        # Iterate through sorted items for consistent receipt order
        for details in sorted(self.current_sale.values(), key=lambda item: item['name']):
            subtotal = details['quantity'] * details['price']
            receipt += "{:<18} {:>3d} {:>7} {:>8}\n".format(
                details['name'][:18],  # Truncate item name if too long
                details['quantity'],
                f"{gui_utils.CURRENCY_SYMBOL}{details['price']:.2f}",
                f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"
            )
        receipt += "======================================\n"
        receipt += "{:<29} {:>8}\n".format("TOTAL:", f"{gui_utils.CURRENCY_SYMBOL}{self.total_amount:.2f}")
        receipt += "--------------------------------------\n"
        receipt += "        Thank you, Come Again!\n"
        return receipt

    def finalize_sale(self):
        """Finalizes the current sale: saves to DB, shows receipt, and clears current sale state."""
        logging.info("Attempting to finalize sale.")
        if not self.current_sale:
            logging.warning("Finalize sale failed: Sale is empty.")
            messagebox.showwarning("Empty Sale", "Cannot finalize an empty sale.", parent=self.root)
            return
        if self.current_customer_name == "N/A":
            logging.warning("Finalize sale failed: No customer selected.")
            messagebox.showwarning("No Customer", "Please select a customer for the sale.", parent=self.root)
            return

        ts = datetime.datetime.now()  # Timestamp for the sale

        # --- CORRECTED: Prepare items_for_db as a LIST of DICTIONARIES ---
        items_for_db = []
        for item_key in self.current_sale:  # Iterate through the keys of current_sale
            details = self.current_sale[item_key]
            items_for_db.append({
                'name': details['name'],
                'price': details['price'],
                'quantity': details['quantity']
            })
        # --- End of correction ---

        logging.info(
            f"Finalizing sale for customer '{self.current_customer_name}' with {len(items_for_db)} line item(s).")

        # Save the main sale record
        sale_id = db_operations.save_sale_record(ts, self.total_amount, self.current_customer_name)

        if sale_id:  # If sale header was saved successfully
            # Save the individual sale items
            if db_operations.save_sale_items_records(sale_id, items_for_db):  # Pass the list
                receipt = self.generate_receipt_text(sale_id, ts, self.current_customer_name)
                logging.info(f"Sale {sale_id} and its items successfully saved to database.")
                logging.debug(f"--- Receipt for Sale ID: {sale_id} ---\n{receipt}\n---------------")

                messagebox.showinfo(f"Sale Finalized - ID: {sale_id}", receipt, parent=self.root)

                # Clear sale state after successful save and receipt display
                previous_customer = self.current_customer_name  # Store before resetting
                self.current_sale = {}
                self.current_customer_name = "N/A"  # Reset to default customer
                if hasattr(self.ui, 'customer_display_var'):
                    self.ui.customer_display_var.set(f"Customer: {self.current_customer_name}")

                self._update_latest_customer_label()  # Update the "Latest Customer" display
                self.update_sale_display()  # Clear the sale UI
                self.show_status(f"Sale {sale_id} recorded successfully.", 3000)
            else:
                # This case means save_sale_items_records failed
                logging.error(
                    f"Failed to save sale ITEMS for Sale ID {sale_id} (Customer: '{self.current_customer_name}'). The main sale record might have been saved. Consider manual DB check or rollback logic.")
                # db_operations.save_sale_items_records should show its own error via messagebox
                self.show_status("Error saving sale items. Sale may be partially saved.", 5000)
        else:
            # This case means save_sale_record (header) failed
            logging.error(f"Failed to save main sale record for customer '{self.current_customer_name}'.")
            # db_operations.save_sale_record should show its own error via messagebox
            self.show_status("Error saving sale header.", 5000)

    def view_sales_history(self):
        """Opens the sales history window, ensuring tkcalendar is available."""
        logging.info("Opening sales history window.")
        if DateEntry is None:  # Check if tkcalendar was imported successfully
            logging.error("Cannot open sales history: tkcalendar library not found.")
            messagebox.showerror("Missing Library",
                                 "The 'tkcalendar' library is required for this feature but was not found.\nPlease install it (e.g., pip install tkcalendar) and restart the application.",
                                 parent=self.root)
            return

        if self.history_window is None or not tk.Toplevel.winfo_exists(self.history_window):
            logging.debug("Creating new SalesHistoryWindow instance.")
            self.history_window = SalesHistoryWindow(self.root)  # Pass root as parent
            self.history_window.grab_set()  # Make it modal
        else:  # Window already exists
            logging.debug("Bringing existing SalesHistoryWindow to front.")
            self.history_window.deiconify()  # Show if minimized
            self.history_window.lift()  # Bring to top
            self.history_window.focus_set()  # Give focus
            self.history_window.grab_set()  # Re-grab if necessary

    def view_customers(self):
        """Opens the customer management window."""
        logging.info("Opening customer management window.")
        if self.customer_list_window is None or not tk.Toplevel.winfo_exists(self.customer_list_window):
            logging.debug("Creating new CustomerListWindow instance.")
            self.customer_list_window = CustomerListWindow(self.root)  # Pass root as parent
            self.customer_list_window.grab_set()  # Make it modal
        else:  # Window already exists
            logging.debug("Bringing existing CustomerListWindow to front.")
            self.customer_list_window.deiconify()
            self.customer_list_window.lift()
            self.customer_list_window.focus_set()
            self.customer_list_window.grab_set()
