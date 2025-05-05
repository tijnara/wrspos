import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import filedialog
import datetime
import os
import sqlite3
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
# Assuming basicConfig called in main.py

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
        self._load_initial_data() # This will now update the latest customer label
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
        # Note: StringVars (status_var, customer_display_var, latest_customer_name_var)
        # are created and managed by the POSAppUI instance (self.ui)

    def _setup_styles(self):
        """Configures ttk styles for the application."""
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            logging.warning("'clam' theme not available, using default.")

        # --- Define Theme Colors ---
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
        self.style.map("Custom.Treeview", background=[('selected', LISTBOX_SELECT_BG)], foreground=[('selected', LISTBOX_SELECT_FG)])
        self.style.configure("Custom.Treeview.Heading", background=TREE_HEADING_BG, foreground=TREE_HEADING_FG, font=('Arial', 10, 'bold'), relief="flat")
        self.style.map("Custom.Treeview.Heading", background=[('active', BUTTON_ACTIVE)])
        self.style.configure('TEntry', fieldbackground='white', foreground='black')
        self.style.configure('TCombobox', fieldbackground='white', foreground='black')
        self.style.configure('TScrollbar', background=BUTTON_BG, troughcolor=BG_COLOR, borderwidth=0)
        self.style.map('TScrollbar', background=[('active', BUTTON_ACTIVE)])
        self.style.configure('TLabelFrame', background=BG_COLOR, borderwidth=1, relief="groove")
        self.style.configure('TLabelFrame.Label', background=BG_COLOR, foreground=HEADER_FG, font=('Arial', 11, 'bold'))

        # Store listbox colors for UI class
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

        # Menu commands
        self._setup_menu() # Ensure menu commands are linked

        # Bind scrollable frame events
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
        self.populate_product_buttons()
        self.populate_product_management_list()
        self.update_sale_display()
        self._update_latest_customer_label() # Update latest customer on startup
        self.show_status("Ready", duration=None)
        logging.info("Initial data loaded.")

    # --- NEW Method ---
    def _update_latest_customer_label(self):
        """Fetches and updates the label showing the latest used customer."""
        logging.debug("Updating latest used customer label.")
        latest_name = db_operations.fetch_latest_customer_name()
        display_text = f"Latest Customer: {latest_name}" if latest_name else "Latest Customer: None"
        # Access the StringVar via the UI instance
        self.ui.latest_customer_name_var.set(display_text)
        logging.debug(f"Latest customer label set to: '{display_text}'")


    # --- Action/Logic Methods ---

    def show_status(self, message, duration=3000):
        """Displays a message in the status bar via the UI instance."""
        logging.debug(f"Status bar: '{message}' (duration: {duration})")
        self.ui.status_var.set(message) # Access UI's status_var
        if self.status_bar_job:
            self.root.after_cancel(self.status_bar_job)
            self.status_bar_job = None
        if duration:
            self.status_bar_job = self.root.after(duration, self.clear_status)

    def clear_status(self):
        """Clears the status bar via the UI instance."""
        logging.debug("Clearing status bar.")
        self.ui.status_var.set("") # Access UI's status_var
        self.status_bar_job = None

    def _handle_refill_20_shortcut(self, event=None):
        """Adds 'Refill (20)' to the sale using constant."""
        product_name = gui_utils.PRODUCT_REFILL_20
        logging.info(f"Shortcut '1' pressed for '{product_name}'.")
        if product_name in self.products: self.add_item(product_name)
        else:
            logging.warning(f"Product '{product_name}' not found for shortcut.")
            self.show_status(f"Product '{product_name}' not found.", 3000)

    def _handle_refill_25_shortcut(self, event=None):
        """Adds 'Refill (25)' to the sale using constant."""
        product_name = gui_utils.PRODUCT_REFILL_25
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
        """Sets focus to the first product button in the UI."""
        logging.debug("F1 pressed, attempting to focus first product button.")
        if self.ui.first_product_button and self.ui.first_product_button.winfo_exists():
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
            if self.history_window and tk.Toplevel.winfo_exists(self.history_window):
                logging.debug("Destroying history window.")
                self.history_window.destroy()
            if self.customer_list_window and tk.Toplevel.winfo_exists(self.customer_list_window):
                logging.debug("Destroying customer list window.")
                self.customer_list_window.destroy()
            self.root.update_idletasks(); self.root.after(100)

            shutil.copy2(backup_path, target_db)
            logging.info(f"Database successfully restored from '{backup_path}'. Application will close.")
            messagebox.showinfo("Restore Successful", f"Restored from:\n{os.path.basename(backup_path)}\n\nApplication will close. Please restart.", parent=self.root)
            self.root.destroy()
        except Exception as e:
            logging.exception(f"Error during database restore from '{backup_path}'.")
            messagebox.showerror("Restore Failed", f"Error: {e}", parent=self.root)
            self.show_status("Restore failed.", 5000)

    def _configure_scrollable_frame(self, event):
        """Callback to reset the scroll region of the product canvas."""
        self.ui.product_canvas.configure(scrollregion=self.ui.product_canvas.bbox("all"))

    def _configure_scrollable_frame_width(self, event):
        """Callback to adjust the width of the inner frame in the product canvas."""
        if hasattr(self.ui, 'product_canvas') and self.ui.product_canvas.find_withtag("scrollable_frame"):
             if event.width > 0:
                 self.ui.product_canvas.itemconfigure("scrollable_frame", width=event.width)
             else:
                 logging.debug(f"Scrollable frame width config skipped (zero width event).")

    def load_products(self):
        """Loads products from the database."""
        logging.info(f"Loading products from '{db_operations.DATABASE_FILENAME}'...")
        products = db_operations.fetch_products_from_db()
        if not products: logging.warning("No products found in database.")
        else: logging.info(f"Loaded {len(products)} products.")
        return products

    def populate_product_buttons(self, available_width=None):
        """Populates the product buttons in the UI's scrollable frame."""
        logging.debug("Populating product buttons...")
        scrollable_frame = self.ui.scrollable_frame
        product_canvas = self.ui.product_canvas

        for widget in scrollable_frame.winfo_children(): widget.destroy()
        self.ui.first_product_button = None # Reset focus target in UI

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
            logging.debug(f"Product '{name}' not found for priority ordering.")
            return False

        add_product_if_exists(refill_20_name)
        add_product_if_exists(refill_25_name)
        custom_sale_exists = custom_sale_name in remaining_products
        if custom_sale_exists:
            ordered_products_for_buttons.append((custom_sale_name, remaining_products[custom_sale_name]))
            del remaining_products[custom_sale_name]
        else: logging.warning(f"'{custom_sale_name}' not found, button not created.")
        for name in other_priority:
            if name: add_product_if_exists(name)
        ordered_products_for_buttons.extend(sorted(remaining_products.items()))

        max_cols = 4
        for i in range(max_cols): scrollable_frame.columnconfigure(i, weight=1)

        row_num, col_num = 0, 0
        for idx, (name, price) in enumerate(ordered_products_for_buttons):
            btn_text = f"{name}\n({gui_utils.CURRENCY_SYMBOL}{price:.2f})"
            button_command = self.prompt_custom_item if name == custom_sale_name else lambda n=name: self.add_item(n)
            btn = ttk.Button(scrollable_frame, text=btn_text, command=button_command, style='Product.TButton')
            btn.grid(row=row_num, column=col_num, padx=2, pady=2, sticky="ew")
            if idx == 0: self.ui.first_product_button = btn

            col_num = (col_num + 1) % max_cols
            if col_num == 0: row_num += 1

        scrollable_frame.update_idletasks()
        product_canvas.configure(scrollregion=product_canvas.bbox("all"))
        self.root.update_idletasks()
        if hasattr(self.ui, 'product_canvas') and product_canvas.find_withtag("scrollable_frame"):
             canvas_width = product_canvas.winfo_width()
             if canvas_width > 0: product_canvas.itemconfigure("scrollable_frame", width=canvas_width)
        logging.debug("Product buttons populated.")

    def populate_product_management_list(self):
        """Populates the product management listbox in the UI."""
        logging.debug("Populating product management list...")
        self.ui.product_listbox.delete(0, tk.END)
        for name, price in sorted(self.products.items()):
            self.ui.product_listbox.insert(tk.END, f"{name} ({gui_utils.CURRENCY_SYMBOL}{price:.2f})")
        logging.debug("Product management list populated.")

    def _get_selected_product_details(self):
        """Gets details from the selected product in the UI's listbox."""
        indices = self.ui.product_listbox.curselection()
        if not indices:
            logging.warning("Action attempted without product selection.")
            messagebox.showwarning("No Selection", "Select a product first.", parent=self.root)
            return None, None
        selected_text = self.ui.product_listbox.get(indices[0])
        try:
            parts = selected_text.split(f' ({gui_utils.CURRENCY_SYMBOL}')
            if len(parts) == 2:
                name = parts[0].strip()
                price = float(parts[1].rstrip(')').strip())
                logging.debug(f"Selected product: Name='{name}', Price={price}")
                return name, price
            raise ValueError(f"Format error: {selected_text}")
        except Exception as e:
             logging.exception(f"Error parsing listbox text: '{selected_text}'")
             messagebox.showerror("Error", f"Parse error: {e}", parent=self.root)
             return None, None

    def prompt_new_item(self):
        """Prompts for new product details and adds it."""
        logging.info("Prompting for new product.")
        name = simpledialog.askstring("New Product", "Name:", parent=self.root)
        if not name or not name.strip(): logging.info("New product cancelled."); return
        name = name.strip()
        if name in self.products:
             logging.warning(f"Duplicate product add attempt: '{name}'.")
             messagebox.showwarning("Exists", f"'{name}' already exists.", parent=self.root)
             return
        price_dialog = PriceInputDialog(self.root, "New Price", f"Price for {name}:")
        price = price_dialog.result
        if price is not None:
            logging.info(f"Attempting add: Name='{name}', Price={price}")
            if db_operations.insert_product_to_db(name, price):
                self.products[name] = price
                self.populate_product_buttons()
                self.populate_product_management_list()
                logging.info(f"Product '{name}' added.")
                self.show_status(f"'{name}' added.", 3000)

    def prompt_edit_item(self):
        """Prompts for updated details of a selected product."""
        logging.info("Initiating edit product.")
        original_name, original_price = self._get_selected_product_details()
        if original_name is None: return
        new_name = simpledialog.askstring("Edit Name", "New name:", initialvalue=original_name, parent=self.root)
        if not new_name or not new_name.strip(): logging.info("Edit cancelled."); return
        new_name = new_name.strip()
        price_dialog = PriceInputDialog(self.root, "Edit Price", f"New price for {new_name}:", initialvalue=f"{original_price:.2f}")
        new_price = price_dialog.result
        if new_price is not None:
            logging.info(f"Attempting update '{original_name}' to Name='{new_name}', Price={new_price}")
            if new_name != original_name and new_name in self.products:
                 logging.warning(f"Edit failed: Name '{new_name}' exists.")
                 messagebox.showerror("Exists", f"'{new_name}' already exists.", parent=self.root)
                 return
            if db_operations.update_product_in_db(original_name, new_name, new_price):
                if original_name in self.products: del self.products[original_name]
                self.products[new_name] = new_price
                self.populate_product_buttons()
                self.populate_product_management_list()
                logging.info(f"Product '{original_name}' updated to '{new_name}'.")
                self.show_status(f"'{original_name}' updated.", 3000)

    def remove_selected_product_permanently(self):
        """Permanently removes the selected product."""
        logging.info("Initiating remove product.")
        product_name, _ = self._get_selected_product_details()
        if product_name is None: return
        if messagebox.askyesno("Confirm Delete", f"Delete '{product_name}' permanently?", parent=self.root):
            logging.warning(f"Attempting deletion of '{product_name}'.")
            if db_operations.delete_product_from_db(product_name):
                if product_name in self.products: del self.products[product_name]
                self.populate_product_buttons()
                self.populate_product_management_list()
                logging.info(f"Product '{product_name}' deleted.")
                self.show_status(f"'{product_name}' deleted.", 3000)
        else:
            logging.info(f"Deletion of '{product_name}' cancelled.")
            self.show_status("Deletion cancelled.", 2000)

    def add_item(self, name, override_price=None, quantity_to_add=1):
        """Adds an item to the current sale."""
        current_price = override_price if override_price is not None else self.products.get(name)
        if current_price is None:
             logging.error(f"Add item failed: Product '{name}' not found.")
             messagebox.showerror("Error", f"Product '{name}' not found.", parent=self.root)
             return
        item_key = f"{name}__{current_price:.2f}"
        if item_key in self.current_sale:
             self.current_sale[item_key]['quantity'] += quantity_to_add
             logging.info(f"Incremented '{name}' qty by {quantity_to_add}. New: {self.current_sale[item_key]['quantity']}.")
        else:
            self.current_sale[item_key] = {'name': name, 'price': current_price, 'quantity': quantity_to_add}
            logging.info(f"Added '{name}' (Price: {current_price:.2f}, Qty: {quantity_to_add}) to sale.")
        self.show_status(f"Added {quantity_to_add} x {name}", 2000)
        self.update_sale_display()

    def prompt_custom_item(self):
        """Opens dialog for custom price/quantity item."""
        logging.info("Opening custom price/qty dialog.")
        product_names_list = sorted(list(self.products.keys()))
        if not product_names_list:
            logging.warning("Custom price dialog: No products defined.")
            messagebox.showwarning("No Products", "No products defined.", parent=self.root)
            return
        dialog = CustomPriceDialog(self.root, product_names_list)
        result = dialog.result
        if result:
            name, price, qty = result
            logging.info(f"Custom item received: Name='{name}', Price={price}, Qty={qty}.")
            self.add_item(name, override_price=price, quantity_to_add=qty)
        else:
            logging.info("Custom price/qty dialog cancelled.")

    def decrease_item_quantity(self):
        """Decreases quantity of selected item in the sale UI."""
        selected_id = self.ui.sale_tree.focus()
        if not selected_id:
            logging.warning("Decrease qty: No item selected.")
            messagebox.showwarning("No Selection", "Select item to decrease.", parent=self.root)
            return
        if selected_id in self.current_sale:
            item_name = self.current_sale[selected_id]['name']
            if self.current_sale[selected_id]['quantity'] > 1:
                self.current_sale[selected_id]['quantity'] -= 1
                logging.info(f"Decreased qty for '{item_name}'. New: {self.current_sale[selected_id]['quantity']}.")
                self.show_status(f"Decreased {item_name} qty.", 2000)
            else:
                del self.current_sale[selected_id]
                logging.info(f"Removed '{item_name}' (qty was 1).")
                self.show_status(f"Removed {item_name}.", 2000)
            self.update_sale_display(preserve_selection=selected_id if selected_id in self.current_sale else None)
        else:
            logging.error(f"Decrease qty failed: Key '{selected_id}' not in current sale.")

    def remove_selected_item_from_sale(self):
        """Removes selected item from the current sale UI."""
        selected_id = self.ui.sale_tree.focus()
        if not selected_id:
            logging.warning("Remove item: No item selected.")
            messagebox.showwarning("No Selection", "Select item to remove.", parent=self.root)
            return
        if selected_id in self.current_sale:
            item_name = self.current_sale[selected_id]['name']
            if messagebox.askyesno("Confirm Remove", f"Remove '{item_name}'?", parent=self.root):
                logging.info(f"Removing '{item_name}' (key: {selected_id}).")
                del self.current_sale[selected_id]
                self.update_sale_display()
                self.show_status(f"Removed {item_name}.", 3000)
            else:
                logging.info(f"Removal of '{item_name}' cancelled.")
                self.show_status("Removal cancelled.", 2000)
        else:
            logging.error(f"Remove item failed: Key '{selected_id}' not in current sale.")

    def update_sale_display(self, preserve_selection=None):
        """Updates the sale Treeview and total in the UI."""
        logging.debug("Updating sale display...")
        sale_tree = self.ui.sale_tree
        total_label = self.ui.total_label
        try:
            sale_tree.tag_configure('oddrow', background="#FFFFFF")
            sale_tree.tag_configure('evenrow', background="#F5FFFA")
        except tk.TclError: pass

        for i in sale_tree.get_children(): sale_tree.delete(i)
        self.total_amount = 0.0
        new_selection_id = None
        for i, (key, details) in enumerate(sorted(self.current_sale.items(), key=lambda item: item[1]['name'])):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            subtotal = details['price'] * details['quantity']
            item_id = sale_tree.insert("", tk.END, iid=key, values=(details['name'], details['quantity'], f"{gui_utils.CURRENCY_SYMBOL}{details['price']:.2f}", f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"), tags=(tag,))
            if preserve_selection == key: new_selection_id = item_id
            self.total_amount += subtotal
        total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{self.total_amount:.2f}")
        if new_selection_id:
            logging.debug(f"Reselecting sale tree item: {new_selection_id}")
            sale_tree.focus(new_selection_id)
            sale_tree.selection_set(new_selection_id)
        else:
             sale_tree.focus(''); sale_tree.selection_set('')
        logging.debug(f"Sale display updated. Total: {self.total_amount:.2f}")

    def clear_sale(self):
        """Clears the current sale data and UI."""
        if not self.current_sale: logging.info("Clear sale: Already empty."); return
        if messagebox.askyesno("Confirm Clear", "Clear current sale?", parent=self.root):
            logging.info("Clearing current sale.")
            self.current_sale = {}
            self.current_customer_name = "N/A"
            self.ui.customer_display_var.set(f"Customer: {self.current_customer_name}") # Update UI var
            self.update_sale_display()
            self.show_status("Sale cleared.", 3000)
            logging.info("Sale cleared.")
        else:
            logging.info("Clear sale cancelled.")
            self.show_status("Clear cancelled.", 2000)

    def select_customer_for_sale(self):
        """Opens dialog to select customer for the sale."""
        logging.info("Opening customer selection dialog.")
        dialog = CustomerSelectionDialog(self.root)
        name = dialog.result
        if name is not None:
            self.current_customer_name = name
            self.ui.customer_display_var.set(f"Customer: {self.current_customer_name}") # Update UI var
            logging.info(f"Customer selected: '{self.current_customer_name}'.")
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
        logging.info("Attempting finalize sale.")
        if not self.current_sale: logging.warning("Finalize failed: Empty sale."); messagebox.showwarning("Empty Sale", "Cannot finalize empty sale.", parent=self.root); return
        if self.current_customer_name == "N/A": logging.warning("Finalize failed: No customer."); messagebox.showwarning("No Customer", "Select customer first.", parent=self.root); return
        ts = datetime.datetime.now()
        items_for_db = {d['name']: {'price': d['price'], 'quantity': d['quantity']} for d in self.current_sale.values()}
        logging.info(f"Finalizing sale for '{self.current_customer_name}' with {len(items_for_db)} item types.")
        sale_id = db_operations.save_sale_record(ts, self.total_amount, self.current_customer_name)
        if sale_id and db_operations.save_sale_items_records(sale_id, items_for_db):
            receipt = self.generate_receipt_text(sale_id, ts, self.current_customer_name)
            logging.info(f"Sale {sale_id} saved.")
            logging.debug(f"--- Receipt {sale_id} ---\n{receipt}\n---------------")
            messagebox.showinfo(f"Sale Finalized - ID: {sale_id}", receipt, parent=self.root)
            # Clear state
            self.current_sale = {}
            # --- MODIFIED: Update latest customer label after finalizing ---
            previous_customer = self.current_customer_name # Store before resetting
            self.current_customer_name = "N/A"
            self.ui.customer_display_var.set(f"Customer: {self.current_customer_name}") # Update UI var
            self._update_latest_customer_label() # Update the latest customer display
            self.update_sale_display()
            self.show_status(f"Sale {sale_id} recorded.", 3000)
        else:
            logging.error(f"Failed to save sale/items for '{self.current_customer_name}'. Sale ID: {sale_id}")
            self.show_status("Error saving sale.", 5000)

    def view_sales_history(self):
        """Opens the sales history window."""
        logging.info("Opening sales history.")
        if DateEntry is None: logging.error("tkcalendar not found."); messagebox.showerror("Missing Library", "tkcalendar not installed.", parent=self.root); return
        if self.history_window is None or not tk.Toplevel.winfo_exists(self.history_window):
            logging.debug("Creating SalesHistoryWindow.")
            self.history_window = SalesHistoryWindow(self.root) # Assumes SalesHistoryWindow takes root
            self.history_window.grab_set()
        else:
            logging.debug("Focusing existing SalesHistoryWindow.")
            self.history_window.deiconify(); self.history_window.lift(); self.history_window.focus_set(); self.history_window.grab_set()

    def view_customers(self):
        """Opens the customer management window."""
        logging.info("Opening customer management.")
        if self.customer_list_window is None or not tk.Toplevel.winfo_exists(self.customer_list_window):
            logging.debug("Creating CustomerListWindow.")
            self.customer_list_window = CustomerListWindow(self.root) # Assumes CustomerListWindow takes root
            self.customer_list_window.grab_set()
        else:
            logging.debug("Focusing existing CustomerListWindow.")
            self.customer_list_window.deiconify(); self.customer_list_window.lift(); self.customer_list_window.focus_set(); self.customer_list_window.grab_set()

