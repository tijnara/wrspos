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
import gui_utils  # gui_utils will now provide APPROX_PRODUCT_BUTTON_WIDTH_WITH_SPACING
from gui_dialogs import PriceInputDialog, CustomerSelectionDialog, CustomPriceDialog
from gui_customer_manager import CustomerListWindow
from gui_history_window import SalesHistoryWindow
from pos_app_ui import POSAppUI


# --- Main Application Logic Class ---
class POSAppLogic:
    def __init__(self, root):
        """Initialize the POS Application Logic."""
        logging.info("Initializing POS Application Logic...")
        self.root = root
        self._initialize_variables()
        self._setup_styles()
        self.ui = POSAppUI(root, self.style)
        self._connect_ui_commands()
        self._bind_shortcuts()
        self._load_initial_data()
        logging.info("POS Application Logic Initialized Successfully.")

    # --- Initialization and Setup Methods ---

    def _initialize_variables(self):
        """Initialize instance variables for logic."""
        logging.info("Initializing database...")
        db_operations.initialize_db()
        logging.info("Database initialized.")
        self.products = self.load_products()
        self.current_sale = {}
        self.total_amount = 0.0
        self.history_window = None
        self.customer_list_window = None
        self.status_bar_job = None
        self.current_customer_name = "N/A"

    def _setup_styles(self):
        """Configures ttk styles for the application."""
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            logging.warning("'clam' theme not available, using default.")

        BG_COLOR = "#F0FFF0"
        BUTTON_BG = "#98FB98"
        BUTTON_FG = "#006400"
        BUTTON_ACTIVE = "#90EE90"
        FINALIZE_BG = "#3CB371"
        FINALIZE_ACTIVE = "#66CDAA"
        LABEL_FG = "#2F4F4F"
        HEADER_FG = "#1E8449"
        TOTAL_FG = "#006400"
        TREE_HEADING_BG = "#D0F0C0"
        TREE_HEADING_FG = "#1E8449"
        TREE_ROW_BG_ODD = "#FFFFFF"
        TREE_ROW_BG_EVEN = "#F5FFFA"
        STATUS_BG = "#98FB98"
        STATUS_FG = "#006400"
        LISTBOX_SELECT_BG = "#3CB371"
        LISTBOX_SELECT_FG = "#FFFFFF"

        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('App.TFrame', background=BG_COLOR)
        self.style.configure('TLabel', background=BG_COLOR, foreground=LABEL_FG, font=('Arial', 10))
        self.style.configure('Header.TLabel', background=BG_COLOR, foreground=HEADER_FG, font=('Arial', 12, 'bold'))
        self.style.configure('Total.TLabel', background=BG_COLOR, foreground=TOTAL_FG, font=('Arial', 14, 'bold'))
        self.style.configure('Status.TLabel', background=STATUS_BG, foreground=STATUS_FG, font=('Arial', 9))
        self.style.configure('TButton', background=BUTTON_BG, foreground=BUTTON_FG, font=('Arial', 9), padding=5,
                             borderwidth=1, relief='raised')
        self.style.map('TButton', background=[('active', BUTTON_ACTIVE)])
        self.style.configure('Product.TButton', font=('Arial', 10, 'bold'), padding=(5, 10))
        self.style.configure('Action.TButton', padding=4, font=('Arial', 9))
        self.style.configure('Finalize.TButton', background=FINALIZE_BG, foreground='white', font=('Arial', 10, 'bold'),
                             padding=6)
        self.style.map('Finalize.TButton', background=[('active', FINALIZE_ACTIVE)])
        self.style.configure("Custom.Treeview", rowheight=25, fieldbackground=TREE_ROW_BG_ODD,
                             background=TREE_ROW_BG_ODD, foreground=LABEL_FG)
        self.style.map("Custom.Treeview", background=[('selected', LISTBOX_SELECT_BG)],
                       foreground=[('selected', LISTBOX_SELECT_FG)])
        self.style.configure("Custom.Treeview.Heading", background=TREE_HEADING_BG, foreground=TREE_HEADING_FG,
                             font=('Arial', 10, 'bold'), relief="flat")
        self.style.map("Custom.Treeview.Heading", background=[('active', BUTTON_ACTIVE)])
        self.style.configure('TEntry', fieldbackground='white', foreground='black')
        self.style.configure('TCombobox', fieldbackground='white', foreground='black')
        self.style.configure('TScrollbar', background=BUTTON_BG, troughcolor=BG_COLOR, borderwidth=0)
        self.style.map('TScrollbar', background=[('active', BUTTON_ACTIVE)])
        self.style.configure('TLabelFrame', background=BG_COLOR, borderwidth=1, relief="groove")
        self.style.configure('TLabelFrame.Label', background=BG_COLOR, foreground=HEADER_FG, font=('Arial', 11, 'bold'))
        self.style.listbox_select_bg = LISTBOX_SELECT_BG
        self.style.listbox_select_fg = LISTBOX_SELECT_FG

    def _connect_ui_commands(self):
        """Connect button commands from the UI instance to logic methods."""
        logging.debug("Connecting UI commands to logic...")
        self.ui.add_product_button.config(command=self.prompt_new_item)
        self.ui.edit_product_button.config(command=self.prompt_edit_item)
        self.ui.remove_product_button.config(command=self.remove_selected_product_permanently)
        self.ui.view_customers_button.config(command=self.view_customers)
        self.ui.select_customer_button.config(command=self.select_customer_for_sale)
        self.ui.finalize_button.config(command=self.finalize_sale)
        self.ui.history_button.config(command=self.view_sales_history)
        self.ui.clear_button.config(command=self.clear_sale)
        self.ui.remove_item_button.config(command=self.remove_selected_item_from_sale)
        self.ui.decrease_qty_button.config(command=self.decrease_item_quantity)
        self._setup_menu()
        self.ui.scrollable_frame.bind('<Configure>', self._configure_scrollable_frame)
        self.ui.product_canvas.bind('<Configure>', self._configure_scrollable_frame_width)
        logging.debug("UI commands connected.")

    def _setup_menu(self):
        """Creates the main menu bar and connects commands."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Backup Database...", command=self.backup_database)
        file_menu.add_command(label="Restore Database...", command=self.restore_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

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
        # Defer product button population slightly to allow canvas to get its initial size
        self.root.after(50, self.populate_product_buttons)
        self.populate_product_management_list()
        self.update_sale_display()
        self._update_latest_customer_label()
        self.show_status("Ready", duration=None)
        logging.info("Initial data loaded.")

    def _update_latest_customer_label(self):
        """Fetches and updates the label showing the latest used customer via the UI instance."""
        logging.debug("Updating latest used customer label.")
        latest_name = db_operations.fetch_latest_customer_name()
        display_text = f"Latest Customer: {latest_name}" if latest_name else "Latest Customer: None"
        if hasattr(self.ui, 'latest_customer_name_var'):
            self.ui.latest_customer_name_var.set(display_text)
        logging.debug(f"Latest customer label set to: '{display_text}'")

    def show_status(self, message, duration=3000):
        """Displays a message in the status bar via the UI instance."""
        logging.debug(f"Status bar: '{message}' (duration: {duration})")
        if hasattr(self.ui, 'status_var'):
            self.ui.status_var.set(message)
            if self.status_bar_job:
                self.root.after_cancel(self.status_bar_job)
                self.status_bar_job = None
            if duration:
                self.status_bar_job = self.root.after(duration, self.clear_status)

    def clear_status(self):
        """Clears the status bar via the UI instance."""
        logging.debug("Clearing status bar.")
        if hasattr(self.ui, 'status_var'):
            self.ui.status_var.set("")
        self.status_bar_job = None

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
        self.prompt_custom_item()

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
            if self.history_window and tk.Toplevel.winfo_exists(self.history_window):
                logging.debug("Destroying history window before restore.")
                self.history_window.destroy()
            if self.customer_list_window and tk.Toplevel.winfo_exists(self.customer_list_window):
                logging.debug("Destroying customer list window before restore.")
                self.customer_list_window.destroy()

            self.root.update_idletasks()
            self.root.after(100)

            shutil.copy2(backup_path, target_db)
            logging.info(f"Database successfully restored from '{backup_path}'. Application will close.")
            messagebox.showinfo("Restore Successful",
                                f"Restored from:\n{os.path.basename(backup_path)}\n\nApplication will close. Please restart.",
                                parent=self.root)
            self.root.destroy()
        except Exception as e:
            logging.exception(f"Error during database restore from '{backup_path}'.")
            messagebox.showerror("Restore Failed", f"Error: {e}", parent=self.root)
            self.show_status("Restore failed.", 5000)

    def _configure_scrollable_frame(self, event):
        """Callback to reset the scroll region of the product canvas based on the scrollable_frame's content."""
        if hasattr(self.ui, 'product_canvas') and self.ui.product_canvas:
            # This ensures the scrollbar knows the full extent of the content in scrollable_frame
            self.ui.product_canvas.configure(scrollregion=self.ui.product_canvas.bbox("all"))

    def _configure_scrollable_frame_width(self, event):
        """Callback to adjust the width of the inner frame (scrollable_frame) in the product canvas to match the canvas width."""
        # This is important for layouts where the inner frame should fill the canvas width (e.g., for horizontal scrolling or ensuring content uses available width)
        if hasattr(self.ui, 'product_canvas') and self.ui.product_canvas.find_withtag(
                "scrollable_frame"):  # Check if the window item exists
            if event.width > 0:  # Ensure valid width from event
                self.ui.product_canvas.itemconfigure("scrollable_frame", width=event.width)
            else:
                # This might happen if the canvas is temporarily 0 width during layout changes.
                logging.debug(f"Scrollable frame width configuration skipped due to zero width event on canvas.")

    def load_products(self):
        """Loads products from the database via db_operations."""
        logging.info(f"Loading products from '{db_operations.DATABASE_FILENAME}'...")
        products = db_operations.fetch_products_from_db()
        if not products:
            logging.warning("No products found in database.")
        else:
            logging.info(f"Loaded {len(products)} products.")
        return products

    def populate_product_buttons(self):
        """Populates the product buttons in the UI's scrollable frame, dynamically adjusting columns."""
        logging.debug("Populating product buttons dynamically...")
        if not hasattr(self.ui, 'scrollable_frame') or not hasattr(self.ui, 'product_canvas'):
            logging.error("UI elements for product buttons not initialized. Cannot populate.")
            return

        scrollable_frame = self.ui.scrollable_frame
        product_canvas = self.ui.product_canvas

        # Ensure canvas width is up-to-date for calculation
        # This is crucial. update_idletasks() forces Tkinter to process pending geometry calculations.
        product_canvas.update_idletasks()
        canvas_width = product_canvas.winfo_width()
        logging.debug(f"Product canvas width for dynamic columns: {canvas_width}")

        # Calculate number of columns based on canvas width and approximate button width
        # APPROX_PRODUCT_BUTTON_WIDTH_WITH_SPACING should be defined in gui_utils.py
        if canvas_width > 0 and gui_utils.APPROX_PRODUCT_BUTTON_WIDTH_WITH_SPACING > 0:
            num_cols = max(1, canvas_width // gui_utils.APPROX_PRODUCT_BUTTON_WIDTH_WITH_SPACING)
        else:
            # Fallback if width is not available (e.g., window not fully drawn yet on initial call)
            num_cols = 4  # Default to 4 columns
            logging.warning(
                f"Canvas width is {canvas_width} (or approx button width is 0), falling back to {num_cols} columns for product buttons.")

        logging.info(f"Calculated number of columns for product buttons: {num_cols}")

        # Clear existing buttons before repopulating
        for widget in scrollable_frame.winfo_children():
            widget.destroy()
        self.ui.first_product_button = None  # Reset the reference for F1 focus

        # --- Product Ordering Logic (remains the same) ---
        refill_20_name = gui_utils.PRODUCT_REFILL_20
        refill_25_name = gui_utils.PRODUCT_REFILL_25
        custom_sale_name = gui_utils.PRODUCT_CUSTOM_SALE
        other_priority = [gui_utils.PRODUCT_CONTAINER]

        ordered_products_for_buttons = []
        remaining_products = self.products.copy()

        def add_product_if_exists(name):
            if name in remaining_products:
                ordered_products_for_buttons.append((name, remaining_products[name]))
                del remaining_products[name]
                return True
            logging.debug(f"Product '{name}' not found in remaining products for priority ordering.")
            return False

        add_product_if_exists(refill_20_name)
        add_product_if_exists(refill_25_name)

        custom_sale_exists = custom_sale_name in remaining_products
        if custom_sale_exists:
            ordered_products_for_buttons.append((custom_sale_name, remaining_products[custom_sale_name]))
            del remaining_products[custom_sale_name]
        else:
            logging.warning(f"Product '{custom_sale_name}' not found in database, its button will not be created.")

        for name in other_priority:
            if name: add_product_if_exists(name)

        ordered_products_for_buttons.extend(sorted(remaining_products.items()))
        # --- End of Product Ordering Logic ---

        # Configure columns in the scrollable_frame based on the dynamic num_cols
        for i in range(num_cols):
            # weight=1 allows columns to expand and share space
            # minsize ensures buttons don't get too squished if many columns are calculated for a wide canvas
            # uniform group makes columns share space equally if they have the same weight
            scrollable_frame.columnconfigure(i, weight=1, minsize=gui_utils.MIN_BUTTON_WIDTH,
                                             uniform="product_button_column")

        row_num, col_num = 0, 0
        for idx, (name, price) in enumerate(ordered_products_for_buttons):
            btn_text = f"{name}\n({gui_utils.CURRENCY_SYMBOL}{price:.2f})"
            button_command = self.prompt_custom_item if name == custom_sale_name else lambda n=name: self.add_item(n)

            btn = ttk.Button(scrollable_frame, text=btn_text, command=button_command, style='Product.TButton')
            # sticky="nsew" makes the button fill the entire grid cell, both horizontally and vertically.
            btn.grid(row=row_num, column=col_num, padx=2, pady=2, sticky="nsew")
            if idx == 0:
                self.ui.first_product_button = btn  # For F1 shortcut

            col_num = (col_num + 1) % num_cols  # Move to next column, wrap around using dynamic num_cols
            if col_num == 0:
                row_num += 1  # Move to next row after filling all columns

        # After adding all buttons, update the scrollable_frame's dimensions
        scrollable_frame.update_idletasks()
        # Configure the canvas's scrollregion to encompass all content in scrollable_frame
        product_canvas.configure(scrollregion=product_canvas.bbox("all"))

        # Ensure the inner frame (scrollable_frame) width is correctly set within the canvas.
        # This is important especially if the number of columns results in a scrollable_frame
        # that is narrower than the canvas itself (though with weighted columns, it should expand).
        self.root.update_idletasks()  # Allow Tkinter to process geometry changes
        if product_canvas.find_withtag("scrollable_frame"):
            current_canvas_width = product_canvas.winfo_width()
            if current_canvas_width > 0:
                product_canvas.itemconfigure("scrollable_frame", width=current_canvas_width)
        logging.debug(f"Product buttons populated with {num_cols} columns.")

    def populate_product_management_list(self):
        """Populates the product management listbox in the UI."""
        logging.debug("Populating product management list...")
        if hasattr(self.ui, 'product_listbox') and self.ui.product_listbox:
            self.ui.product_listbox.delete(0, tk.END)
            for name, price in sorted(self.products.items()):
                self.ui.product_listbox.insert(tk.END, f"{name} ({gui_utils.CURRENCY_SYMBOL}{price:.2f})")
        logging.debug("Product management list populated.")

    def _get_selected_product_details(self):
        """Gets details (name, price) from the selected product in the UI's listbox."""
        if not hasattr(self.ui, 'product_listbox') or not self.ui.product_listbox:
            logging.error("Product listbox not available in UI to get selection.")
            return None, None

        indices = self.ui.product_listbox.curselection()
        if not indices:
            logging.warning("Action attempted without product selection in management list.")
            messagebox.showwarning("No Selection", "Select a product from the list first.", parent=self.root)
            return None, None

        selected_text = self.ui.product_listbox.get(indices[0])
        try:
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

        if name in self.products:
            logging.warning(f"Attempted to add duplicate product: '{name}'.")
            messagebox.showwarning("Product Exists", f"A product named '{name}' already exists.", parent=self.root)
            return

        price_dialog = PriceInputDialog(self.root, "New Product Price", f"Enter Price for {name}:")
        price = price_dialog.result

        if price is not None:
            logging.info(f"Attempting to add new product: Name='{name}', Price={price}")
            if db_operations.insert_product_to_db(name, price):
                self.products[name] = price
                self.populate_product_buttons()
                self.populate_product_management_list()
                logging.info(f"Product '{name}' added successfully.")
                self.show_status(f"Product '{name}' added.", 3000)
        else:
            logging.info("Price entry for new product cancelled.")

    def prompt_edit_item(self):
        """Prompts for updated details of a selected product."""
        logging.info("Initiating edit product process.")
        original_name, original_price = self._get_selected_product_details()
        if original_name is None: return

        new_name = simpledialog.askstring("Edit Product Name", "Enter New Name:", initialvalue=original_name,
                                          parent=self.root)
        if not new_name or not new_name.strip():
            logging.info("Product name edit cancelled or name was empty.")
            return
        new_name = new_name.strip()

        price_dialog = PriceInputDialog(self.root, "Edit Product Price", f"Enter New Price for {new_name}:",
                                        initialvalue=f"{original_price:.2f}")
        new_price = price_dialog.result

        if new_price is not None:
            logging.info(f"Attempting to update product '{original_name}' to Name='{new_name}', Price={new_price}")
            if new_name != original_name and new_name in self.products:
                logging.warning(f"Edit failed: New product name '{new_name}' already exists for a different product.")
                messagebox.showerror("Name Exists", f"A product named '{new_name}' already exists.", parent=self.root)
                return

            if db_operations.update_product_in_db(original_name, new_name, new_price):
                if original_name in self.products:
                    del self.products[original_name]
                self.products[new_name] = new_price

                self.populate_product_buttons()
                self.populate_product_management_list()
                logging.info(f"Product '{original_name}' updated successfully to '{new_name}'.")
                self.show_status(f"Product '{original_name}' updated.", 3000)
        else:
            logging.info("Price entry for product edit cancelled.")

    def remove_selected_product_permanently(self):
        """Permanently removes the selected product from database and UI."""
        logging.info("Initiating remove product process.")
        product_name, _ = self._get_selected_product_details()
        if product_name is None: return

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete '{product_name}'?",
                               parent=self.root):
            logging.warning(f"Attempting permanent deletion of product '{product_name}'.")
            if db_operations.delete_product_from_db(product_name):
                if product_name in self.products:
                    del self.products[product_name]

                self.populate_product_buttons()
                self.populate_product_management_list()
                logging.info(f"Product '{product_name}' deleted successfully.")
                self.show_status(f"Product '{product_name}' deleted.", 3000)
        else:
            logging.info(f"Deletion of product '{product_name}' cancelled by user.")
            self.show_status("Product deletion cancelled.", 2000)

    def add_item(self, name, override_price=None, quantity_to_add=1):
        """Adds an item to the current sale dictionary and updates UI."""
        current_price = override_price if override_price is not None else self.products.get(name)

        if current_price is None:
            logging.error(f"Attempted to add non-existent or price-less product '{name}'.")
            messagebox.showerror("Product Error", f"Product '{name}' not found or has no price.", parent=self.root)
            return

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
        product_names_list = sorted(list(self.products.keys()))

        if not product_names_list:
            logging.warning("Cannot open custom price dialog: No products defined in the system.")
            messagebox.showwarning("No Products", "No products are defined. Please add products first.",
                                   parent=self.root)
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
        """Decreases quantity of selected item in the sale UI, or removes if quantity becomes zero."""
        if not hasattr(self.ui, 'sale_tree') or not self.ui.sale_tree: return

        selected_id = self.ui.sale_tree.focus()
        if not selected_id:
            logging.warning("Attempted to decrease quantity with no item selected in sale tree.")
            messagebox.showwarning("No Selection", "Please select an item from the sale to decrease its quantity.",
                                   parent=self.root)
            return

        if selected_id in self.current_sale:
            item_name = self.current_sale[selected_id]['name']
            current_quantity = self.current_sale[selected_id]['quantity']

            if current_quantity > 1:
                self.current_sale[selected_id]['quantity'] -= 1
                logging.info(
                    f"Decreased quantity for '{item_name}'. New quantity: {self.current_sale[selected_id]['quantity']}.")
                self.show_status(f"Decreased {item_name} quantity.", 2000)
            else:
                del self.current_sale[selected_id]
                logging.info(f"Removed '{item_name}' from sale (quantity was 1 and was decreased).")
                self.show_status(f"Removed {item_name}.", 2000)

            self.update_sale_display(preserve_selection=selected_id if selected_id in self.current_sale else None)
        else:
            logging.error(
                f"Attempted to decrease quantity for non-existent sale item key '{selected_id}'. This might indicate a mismatch between UI and internal sale state.")

    def remove_selected_item_from_sale(self):
        """Removes selected item entirely from the current sale UI."""
        if not hasattr(self.ui, 'sale_tree') or not self.ui.sale_tree: return

        selected_id = self.ui.sale_tree.focus()
        if not selected_id:
            logging.warning("Attempted to remove item with no item selected in sale tree.")
            messagebox.showwarning("No Selection", "Please select an item from the sale to remove.", parent=self.root)
            return

        if selected_id in self.current_sale:
            item_name = self.current_sale[selected_id]['name']
            if messagebox.askyesno("Confirm Remove", f"Remove '{item_name}' from the current sale?", parent=self.root):
                logging.info(f"Removing item '{item_name}' (key: {selected_id}) from sale upon user confirmation.")
                del self.current_sale[selected_id]
                self.update_sale_display()
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

        try:
            sale_tree.tag_configure('oddrow', background=self.style.lookup("Custom.Treeview", "background"))
            sale_tree.tag_configure('evenrow', background="#F5FFFA")
        except tk.TclError:
            logging.warning("Could not configure Treeview tags, style might not be fully ready.")
            pass

        for i in sale_tree.get_children(): sale_tree.delete(i)

        self.total_amount = 0.0
        new_selection_id = None

        sorted_sale_items = sorted(self.current_sale.items(), key=lambda item: item[1]['name'])

        for i, (key, details) in enumerate(sorted_sale_items):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            subtotal = details['price'] * details['quantity']
            item_id_in_tree = sale_tree.insert("", tk.END, iid=key, values=(
                details['name'],
                details['quantity'],
                f"{gui_utils.CURRENCY_SYMBOL}{details['price']:.2f}",
                f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"
            ), tags=(tag,))

            if preserve_selection == key:
                new_selection_id = item_id_in_tree

            self.total_amount += subtotal

        total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{self.total_amount:.2f}")

        if new_selection_id:
            logging.debug(f"Reselecting item in sale tree: {new_selection_id}")
            sale_tree.focus(new_selection_id)
            sale_tree.selection_set(new_selection_id)
        else:
            sale_tree.focus('');
            sale_tree.selection_set('')

        logging.debug(f"Sale display updated. Total amount: {self.total_amount:.2f}")

    def clear_sale(self):
        """Clears the current sale data and resets customer in UI."""
        if not self.current_sale:
            logging.info("Clear sale requested, but sale is already empty.")
            self.show_status("Sale is already empty.", 2000)
            return

        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the current sale?", parent=self.root):
            logging.info("Clearing current sale upon user confirmation.")
            self.current_sale = {}
            self.current_customer_name = "N/A"
            if hasattr(self.ui, 'customer_display_var'):
                self.ui.customer_display_var.set(f"Customer: {self.current_customer_name}")
            self.update_sale_display()
            self.show_status("Sale cleared.", 3000)
            logging.info("Sale cleared successfully.")
        else:
            logging.info("Clear sale cancelled by user.")
            self.show_status("Clear sale cancelled.", 2000)

    def select_customer_for_sale(self):
        """Opens dialog to select or enter a customer for the current sale."""
        logging.info("Opening customer selection dialog for current sale.")
        dialog = CustomerSelectionDialog(self.root)
        name = dialog.result

        if name is not None:
            self.current_customer_name = name
            if hasattr(self.ui, 'customer_display_var'):
                self.ui.customer_display_var.set(f"Customer: {self.current_customer_name}")
            logging.info(f"Customer selected for sale: '{self.current_customer_name}'.")
            self.show_status(f"Customer set to: {self.current_customer_name}", 3000)
        else:
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

        for details in sorted(self.current_sale.values(), key=lambda item: item['name']):
            subtotal = details['quantity'] * details['price']
            receipt += "{:<18} {:>3d} {:>7} {:>8}\n".format(
                details['name'][:18],
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

        ts = datetime.datetime.now()

        items_for_db = []
        for item_key in self.current_sale:
            details = self.current_sale[item_key]
            items_for_db.append({
                'name': details['name'],
                'price': details['price'],
                'quantity': details['quantity']
            })

        logging.info(
            f"Finalizing sale for customer '{self.current_customer_name}' with {len(items_for_db)} line item(s).")

        sale_id = db_operations.save_sale_record(ts, self.total_amount, self.current_customer_name)

        if sale_id:
            if db_operations.save_sale_items_records(sale_id, items_for_db):
                receipt = self.generate_receipt_text(sale_id, ts, self.current_customer_name)
                logging.info(f"Sale {sale_id} and its items successfully saved to database.")
                logging.debug(f"--- Receipt for Sale ID: {sale_id} ---\n{receipt}\n---------------")

                messagebox.showinfo(f"Sale Finalized - ID: {sale_id}", receipt, parent=self.root)

                previous_customer = self.current_customer_name
                self.current_sale = {}
                self.current_customer_name = "N/A"
                if hasattr(self.ui, 'customer_display_var'):
                    self.ui.customer_display_var.set(f"Customer: {self.current_customer_name}")

                self._update_latest_customer_label()
                self.update_sale_display()
                self.show_status(f"Sale {sale_id} recorded successfully.", 3000)
            else:
                logging.error(
                    f"Failed to save sale ITEMS for Sale ID {sale_id} (Customer: '{self.current_customer_name}'). The main sale record might have been saved. Consider manual DB check or rollback logic.")
                self.show_status("Error saving sale items. Sale may be partially saved.", 5000)
        else:
            logging.error(f"Failed to save main sale record for customer '{self.current_customer_name}'.")
            self.show_status("Error saving sale header.", 5000)

    def view_sales_history(self):
        """Opens the sales history window, ensuring tkcalendar is available."""
        logging.info("Opening sales history window.")
        if DateEntry is None:
            logging.error("Cannot open sales history: tkcalendar library not found.")
            messagebox.showerror("Missing Library",
                                 "The 'tkcalendar' library is required for this feature but was not found.\nPlease install it (e.g., pip install tkcalendar) and restart the application.",
                                 parent=self.root)
            return

        if self.history_window is None or not tk.Toplevel.winfo_exists(self.history_window):
            logging.debug("Creating new SalesHistoryWindow instance.")
            self.history_window = SalesHistoryWindow(self.root)
            self.history_window.grab_set()
        else:
            logging.debug("Bringing existing SalesHistoryWindow to front.")
            self.history_window.deiconify()
            self.history_window.lift()
            self.history_window.focus_set()
            self.history_window.grab_set()

    def view_customers(self):
        """Opens the customer management window."""
        logging.info("Opening customer management window.")
        if self.customer_list_window is None or not tk.Toplevel.winfo_exists(self.customer_list_window):
            logging.debug("Creating new CustomerListWindow instance.")
            self.customer_list_window = CustomerListWindow(self.root)
            self.customer_list_window.grab_set()
        else:
            logging.debug("Bringing existing CustomerListWindow to front.")
            self.customer_list_window.deiconify()
            self.customer_list_window.lift()
            self.customer_list_window.focus_set()
            self.customer_list_window.grab_set()
