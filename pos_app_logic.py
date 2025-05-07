import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import filedialog
import datetime
import os
import shutil
import logging

from dateutil.relativedelta import relativedelta, MO, SU

try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None

import db_operations
import gui_utils  # For color constants
from gui_dialogs import PriceInputDialog, CustomerSelectionDialog, CustomPriceDialog
from gui_customer_manager import CustomerListWindow
from gui_history_window import SalesHistoryWindow
from pos_app_ui import POSAppUI


class POSAppLogic:
    def __init__(self, root):
        logging.info("Initializing POS Application Logic...")
        self.root = root
        self._initialize_variables()
        self._setup_styles()
        self.ui = POSAppUI(root, self.style)
        self._connect_ui_commands()
        self._bind_shortcuts()
        self._load_initial_data()
        logging.info("POS Application Logic Initialized Successfully.")

    def _initialize_variables(self):
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

        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('App.TFrame', background=BG_COLOR)
        self.style.configure('TLabel', background=BG_COLOR, foreground=LABEL_FG, font=('Arial', 10))
        self.style.configure('Header.TLabel', background=BG_COLOR, foreground=HEADER_FG, font=('Arial', 12, 'bold'))
        self.style.configure('Total.TLabel', background=BG_COLOR, foreground=TOTAL_FG, font=('Arial', 14, 'bold'))

        self.style.configure('Status.TLabel', background=gui_utils.STATUS_DEFAULT_BG,
                             foreground=gui_utils.STATUS_DEFAULT_FG, font=('Arial', 9))
        self.style.configure('Status.Success.TLabel', background=gui_utils.STATUS_SUCCESS_BG,
                             foreground=gui_utils.STATUS_SUCCESS_FG, font=('Arial', 9, 'bold'))
        self.style.configure('Status.Error.TLabel', background=gui_utils.STATUS_ERROR_BG,
                             foreground=gui_utils.STATUS_ERROR_FG, font=('Arial', 9, 'bold'))
        self.style.configure('Status.Info.TLabel', background=gui_utils.STATUS_INFO_BG,
                             foreground=gui_utils.STATUS_INFO_FG, font=('Arial', 9))

        self.style.configure('TButton', background=BUTTON_BG, foreground=BUTTON_FG, font=('Arial', 9), padding=5,
                             borderwidth=1, relief='raised')
        self.style.map('TButton', background=[('active', BUTTON_ACTIVE)])

        # Standard Product Button Style
        self.style.configure('Product.TButton', font=('Arial', 10, 'bold'), padding=(5, 10))

        # --- NEW: Custom Sale Button Style ---
        self.style.configure('CustomSale.Product.TButton',
                             font=('Arial', 10, 'bold', 'italic'),  # Added italic for more distinction
                             padding=(5, 10),
                             background=gui_utils.CUSTOM_SALE_BUTTON_BG,
                             foreground=gui_utils.CUSTOM_SALE_BUTTON_FG,
                             borderwidth=2,  # Slightly thicker border
                             relief='raised')
        self.style.map('CustomSale.Product.TButton',
                       background=[('active', gui_utils.CUSTOM_SALE_BUTTON_ACTIVE_BG)],
                       relief=[('pressed', 'sunken'), ('active', 'raised')])

        self.style.configure('Action.TButton', padding=4, font=('Arial', 9))
        self.style.configure('Finalize.TButton', background=FINALIZE_BG, foreground='white', font=('Arial', 10, 'bold'),
                             padding=6)
        self.style.map('Finalize.TButton', background=[('active', FINALIZE_ACTIVE)])

        self.style.configure("Custom.Treeview", rowheight=25, fieldbackground=TREE_ROW_BG_ODD,
                             background=TREE_ROW_BG_ODD, foreground=LABEL_FG)
        self.style.map("Custom.Treeview",
                       background=[('selected', gui_utils.LISTBOX_SELECT_BG)],
                       foreground=[('selected', gui_utils.LISTBOX_SELECT_FG)])

        self.style.configure("Custom.Treeview.Heading", background=TREE_HEADING_BG, foreground=TREE_HEADING_FG,
                             font=('Arial', 10, 'bold'), relief="flat")
        self.style.map("Custom.Treeview.Heading", background=[('active', BUTTON_ACTIVE)])
        self.style.configure('TEntry', fieldbackground='white', foreground='black')
        self.style.configure('TCombobox', fieldbackground='white', foreground='black')
        self.style.configure('TScrollbar', background=BUTTON_BG, troughcolor=BG_COLOR, borderwidth=0)
        self.style.map('TScrollbar', background=[('active', BUTTON_ACTIVE)])
        self.style.configure('TLabelFrame', background=BG_COLOR, borderwidth=1, relief="groove")
        self.style.configure('TLabelFrame.Label', background=BG_COLOR, foreground=HEADER_FG, font=('Arial', 11, 'bold'))

    def _connect_ui_commands(self):
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
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Backup Database...", command=self.backup_database)
        file_menu.add_command(label="Restore Database...", command=self.restore_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

    def _bind_shortcuts(self):
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
        logging.info("Loading initial data...")
        self.root.after(50, self.populate_product_buttons)
        self.populate_product_management_list()
        self.update_sale_display()
        self._update_latest_customer_label()
        self.show_status("Ready", duration=None, status_type="info")
        logging.info("Initial data loaded.")

    def _update_latest_customer_label(self):
        logging.debug("Updating latest used customer label.")
        latest_name = db_operations.fetch_latest_customer_name()
        display_text = f"Latest Customer: {latest_name}" if latest_name else "Latest Customer: None"
        if hasattr(self.ui, 'latest_customer_name_var'):
            self.ui.latest_customer_name_var.set(display_text)
        logging.debug(f"Latest customer label set to: '{display_text}'")

    def show_status(self, message, duration=3000, status_type="default"):
        logging.debug(f"Status bar: '{message}' (type: {status_type}, duration: {duration})")
        if hasattr(self.ui, 'status_var') and hasattr(self.ui, 'status_bar'):
            self.ui.status_var.set(message)
            style_map = {
                "success": "Status.Success.TLabel",
                "error": "Status.Error.TLabel",
                "info": "Status.Info.TLabel",
                "default": "Status.TLabel"
            }
            chosen_style = style_map.get(status_type.lower(), "Status.TLabel")
            self.ui.status_bar.config(style=chosen_style)
            if self.status_bar_job:
                self.root.after_cancel(self.status_bar_job)
                self.status_bar_job = None
            if duration:
                self.status_bar_job = self.root.after(duration, lambda: self.clear_status(revert_style=True))
        else:
            logging.warning("Status bar UI element not available.")

    def clear_status(self, revert_style=False):
        logging.debug("Clearing status bar.")
        if hasattr(self.ui, 'status_var'):
            self.ui.status_var.set("")
        if revert_style and hasattr(self.ui, 'status_bar'):
            self.ui.status_bar.config(style="Status.TLabel")
        self.status_bar_job = None

    def _handle_refill_20_shortcut(self, event=None):
        product_name = gui_utils.PRODUCT_REFILL_20
        logging.info(f"Shortcut '1' pressed for '{product_name}'.")
        if product_name in self.products:
            self.add_item(product_name)
        else:
            logging.warning(f"Product '{product_name}' not found for shortcut.")
            self.show_status(f"Product '{product_name}' not found.", 3000, status_type="error")

    def _handle_refill_25_shortcut(self, event=None):
        product_name = gui_utils.PRODUCT_REFILL_25
        logging.info(f"Shortcut '2' pressed for '{product_name}'.")
        if product_name in self.products:
            self.add_item(product_name)
        else:
            logging.warning(f"Product '{product_name}' not found for shortcut.")
            self.show_status(f"Product '{product_name}' not found.", 3000, status_type="error")

    def _handle_custom_price_shortcut(self, event=None):
        logging.info("Shortcut '3' pressed, opening custom price dialog.")
        self.prompt_custom_item()

    def focus_first_product(self, event=None):
        logging.debug("F1 pressed, attempting to focus first product button.")
        if hasattr(self.ui,
                   'first_product_button') and self.ui.first_product_button and self.ui.first_product_button.winfo_exists():
            self.ui.first_product_button.focus_set()
            self.show_status("Focused first product button (F1)", 2000, status_type="info")
            logging.debug("Focus set to first product button.")
        else:
            logging.warning("No product buttons found to focus (F1).")
            self.show_status("No product buttons found.", 2000, status_type="warning")

    def backup_database(self):
        source_db = db_operations.DATABASE_FILENAME
        logging.info(f"Initiating database backup from '{source_db}'.")
        if not os.path.exists(source_db):
            logging.error(f"Backup failed: Database file '{source_db}' not found.")
            messagebox.showerror("Backup Error", f"Database '{source_db}' not found.", parent=self.root)
            self.show_status("Backup failed: DB not found.", 5000, status_type="error")
            return
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_filename = f"pos_backup_{timestamp}.db"
        backup_path = filedialog.asksaveasfilename(
            parent=self.root, title="Save Backup As", initialfile=suggested_filename,
            defaultextension=".db", filetypes=[("DB files", "*.db"), ("All files", "*.*")]
        )
        if not backup_path:
            logging.info("Database backup cancelled by user.")
            self.show_status("Backup cancelled.", 3000, status_type="info")
            return
        try:
            shutil.copy2(source_db, backup_path)
            logging.info(f"Database successfully backed up to '{backup_path}'.")
            self.show_status(f"Backup successful: {os.path.basename(backup_path)}", 5000, status_type="success")
        except Exception as e:
            logging.exception(f"Error during database backup to '{backup_path}'.")
            messagebox.showerror("Backup Failed", f"Error: {e}", parent=self.root)
            self.show_status("Backup failed.", 5000, status_type="error")

    def restore_database(self):
        target_db = db_operations.DATABASE_FILENAME
        logging.warning("Database restore initiated.")
        warning_msg = "WARNING: Restoring will OVERWRITE current data!\nApplication will close. Restart manually.\nProceed?"
        if not messagebox.askyesno("Confirm Restore", warning_msg, icon='warning', parent=self.root):
            logging.info("Database restore cancelled by user confirmation.")
            self.show_status("Restore cancelled.", 3000, status_type="info")
            return

        backup_path = filedialog.askopenfilename(
            parent=self.root, title="Select Backup to Restore",
            filetypes=[("DB files", "*.db"), ("All files", "*.*")]
        )
        if not backup_path:
            logging.info("Database restore cancelled by user file selection.")
            self.show_status("Restore cancelled.", 3000, status_type="info")
            return

        if not os.path.exists(backup_path):
            logging.error(f"Restore failed: Selected backup file '{backup_path}' not found.")
            messagebox.showerror("Restore Error", "Backup file not found.", parent=self.root)
            self.show_status("Restore failed: Backup not found.", 5000, status_type="error")
            return

        if not backup_path.lower().endswith(".db"):
            logging.warning(f"Selected restore file '{backup_path}' does not end with .db.")
            if not messagebox.askyesno("Confirm File Type", "File lacks .db extension. Restore anyway?", icon='warning',
                                       parent=self.root):
                logging.info("Database restore cancelled due to file extension confirmation.")
                self.show_status("Restore cancelled.", 3000, status_type="info")
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
            self.show_status("Restore successful! Restarting...", duration=None, status_type="success")
            self.root.update_idletasks()
            messagebox.showinfo("Restore Successful",
                                f"Restored from:\n{os.path.basename(backup_path)}\n\nApplication will close. Please restart.",
                                parent=self.root)
            self.root.destroy()
        except Exception as e:
            logging.exception(f"Error during database restore from '{backup_path}'.")
            messagebox.showerror("Restore Failed", f"Error: {e}", parent=self.root)
            self.show_status("Restore failed.", 5000, status_type="error")

    def _configure_scrollable_frame(self, event):
        if hasattr(self.ui, 'product_canvas') and self.ui.product_canvas:
            self.ui.product_canvas.configure(scrollregion=self.ui.product_canvas.bbox("all"))

    def _configure_scrollable_frame_width(self, event):
        if hasattr(self.ui, 'product_canvas') and self.ui.product_canvas.find_withtag("scrollable_frame"):
            if event.width > 0:
                self.ui.product_canvas.itemconfigure("scrollable_frame", width=event.width)
            else:
                logging.debug(f"Scrollable frame width configuration skipped due to zero width event on canvas.")

    def load_products(self):
        logging.info(f"Loading products from '{db_operations.DATABASE_FILENAME}'...")
        products = db_operations.fetch_products_from_db()
        if not products:
            logging.warning("No products found in database.")
        else:
            logging.info(f"Loaded {len(products)} products.")
        return products

    def populate_product_buttons(self):
        logging.debug("Populating product buttons dynamically...")
        if not hasattr(self.ui, 'scrollable_frame') or not hasattr(self.ui, 'product_canvas'):
            logging.error("UI elements for product buttons not initialized. Cannot populate.")
            return

        scrollable_frame = self.ui.scrollable_frame
        product_canvas = self.ui.product_canvas
        product_canvas.update_idletasks()
        canvas_width = product_canvas.winfo_width()
        logging.debug(f"Product canvas width for dynamic columns: {canvas_width}")

        if canvas_width > 0 and gui_utils.APPROX_PRODUCT_BUTTON_WIDTH_WITH_SPACING > 0:
            num_cols = max(1, canvas_width // gui_utils.APPROX_PRODUCT_BUTTON_WIDTH_WITH_SPACING)
        else:
            num_cols = 4
            logging.warning(f"Canvas width is {canvas_width}, falling back to {num_cols} columns.")

        logging.info(f"Calculated number of columns for product buttons: {num_cols}")

        for widget in scrollable_frame.winfo_children():
            widget.destroy()
        self.ui.first_product_button = None

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
        else:
            logging.warning(f"Product '{custom_sale_name}' not found, button not created.")
        for name in other_priority:
            if name: add_product_if_exists(name)
        ordered_products_for_buttons.extend(sorted(remaining_products.items()))

        for i in range(num_cols):
            scrollable_frame.columnconfigure(i, weight=1, minsize=gui_utils.MIN_BUTTON_WIDTH,
                                             uniform="product_button_column")

        row_num, col_num = 0, 0
        for idx, (name, price) in enumerate(ordered_products_for_buttons):
            btn_text = f"{name}\n({gui_utils.CURRENCY_SYMBOL}{price:.2f})"

            # --- MODIFIED: Apply special style for Custom Sale button ---
            current_button_style = 'Product.TButton'
            if name == custom_sale_name:
                current_button_style = 'CustomSale.Product.TButton'

            button_command = self.prompt_custom_item if name == custom_sale_name else lambda n=name: self.add_item(n)

            btn = ttk.Button(scrollable_frame, text=btn_text, command=button_command, style=current_button_style)
            # --- End of modification ---

            btn.grid(row=row_num, column=col_num, padx=2, pady=2, sticky="nsew")
            if idx == 0:
                self.ui.first_product_button = btn
            col_num = (col_num + 1) % num_cols
            if col_num == 0:
                row_num += 1

        scrollable_frame.update_idletasks()
        product_canvas.configure(scrollregion=product_canvas.bbox("all"))
        self.root.update_idletasks()
        if product_canvas.find_withtag("scrollable_frame"):
            current_canvas_width = product_canvas.winfo_width()
            if current_canvas_width > 0:
                product_canvas.itemconfigure("scrollable_frame", width=current_canvas_width)
        logging.debug(f"Product buttons populated with {num_cols} columns.")

    def populate_product_management_list(self):
        logging.debug("Populating product management list...")
        if hasattr(self.ui, 'product_listbox') and self.ui.product_listbox:
            self.ui.product_listbox.delete(0, tk.END)
            for name, price in sorted(self.products.items()):
                self.ui.product_listbox.insert(tk.END, f"{name} ({gui_utils.CURRENCY_SYMBOL}{price:.2f})")
        logging.debug("Product management list populated.")

    def _get_selected_product_details(self):
        if not hasattr(self.ui, 'product_listbox') or not self.ui.product_listbox:
            logging.error("Product listbox not available.")
            return None, None
        indices = self.ui.product_listbox.curselection()
        if not indices:
            logging.warning("Action attempted without product selection.")
            messagebox.showwarning("No Selection", "Select a product from the list first.", parent=self.root)
            return None, None
        selected_text = self.ui.product_listbox.get(indices[0])
        try:
            parts = selected_text.split(f' ({gui_utils.CURRENCY_SYMBOL}')
            if len(parts) == 2:
                name = parts[0].strip()
                price_str = parts[1].rstrip(')').strip()
                price = float(price_str)
                logging.debug(f"Selected product: Name='{name}', Price={price}")
                return name, price
            raise ValueError(f"Format error: {selected_text}")
        except Exception as e:
            logging.exception(f"Error parsing listbox text: '{selected_text}'")
            messagebox.showerror("Error", f"Parse error: {e}", parent=self.root)
            return None, None

    def prompt_new_item(self):
        logging.info("Prompting for new product.")
        name = simpledialog.askstring("New Product", "Enter Product Name:", parent=self.root)
        if not name or not name.strip():
            logging.info("New product cancelled.")
            self.show_status("Add product cancelled.", status_type="info")
            return
        name = name.strip()
        if name in self.products:
            logging.warning(f"Duplicate product add: '{name}'.")
            messagebox.showwarning("Exists", f"'{name}' already exists.", parent=self.root)
            self.show_status(f"'{name}' already exists.", status_type="error")
            return
        price_dialog = PriceInputDialog(self.root, "New Product Price", f"Enter Price for {name}:")
        price = price_dialog.result
        if price is not None:
            logging.info(f"Attempting add: Name='{name}', Price={price}")
            if db_operations.insert_product_to_db(name, price):
                self.products[name] = price
                self.populate_product_buttons()
                self.populate_product_management_list()
                logging.info(f"Product '{name}' added.")
                self.show_status(f"'{name}' added successfully.", status_type="success")
        else:
            self.show_status("Add product cancelled (no price).", status_type="info")

    def prompt_edit_item(self):
        logging.info("Initiating edit product.")
        original_name, original_price = self._get_selected_product_details()
        if original_name is None: return
        new_name = simpledialog.askstring("Edit Name", "New name:", initialvalue=original_name, parent=self.root)
        if not new_name or not new_name.strip():
            logging.info("Edit cancelled.")
            self.show_status("Edit product cancelled.", status_type="info")
            return
        new_name = new_name.strip()
        price_dialog = PriceInputDialog(self.root, "Edit Price", f"New price for {new_name}:",
                                        initialvalue=f"{original_price:.2f}")
        new_price = price_dialog.result
        if new_price is not None:
            logging.info(f"Attempting update '{original_name}' to Name='{new_name}', Price={new_price}")
            if new_name != original_name and new_name in self.products:
                logging.warning(f"Edit failed: Name '{new_name}' exists.")
                messagebox.showerror("Exists", f"'{new_name}' already exists.", parent=self.root)
                self.show_status(f"'{new_name}' already exists.", status_type="error")
                return
            if db_operations.update_product_in_db(original_name, new_name, new_price):
                if original_name in self.products: del self.products[original_name]
                self.products[new_name] = new_price
                self.populate_product_buttons()
                self.populate_product_management_list()
                logging.info(f"Product '{original_name}' updated to '{new_name}'.")
                self.show_status(f"'{original_name}' updated.", status_type="success")
        else:
            self.show_status("Edit product cancelled (no price).", status_type="info")

    def remove_selected_product_permanently(self):
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
                self.show_status(f"'{product_name}' deleted.", status_type="success")
        else:
            logging.info(f"Deletion of '{product_name}' cancelled.")
            self.show_status("Deletion cancelled.", status_type="info")

    def add_item(self, name, override_price=None, quantity_to_add=1):
        current_price = override_price if override_price is not None else self.products.get(name)
        if current_price is None:
            logging.error(f"Add item failed: Product '{name}' not found.")
            messagebox.showerror("Error", f"Product '{name}' not found.", parent=self.root)
            self.show_status(f"Error: '{name}' not found.", status_type="error")
            return
        item_key = f"{name}__{current_price:.2f}"
        if item_key in self.current_sale:
            self.current_sale[item_key]['quantity'] += quantity_to_add
            logging.info(
                f"Incremented '{name}' qty by {quantity_to_add}. New: {self.current_sale[item_key]['quantity']}.")
        else:
            self.current_sale[item_key] = {'name': name, 'price': current_price, 'quantity': quantity_to_add}
            logging.info(f"Added '{name}' (Price: {current_price:.2f}, Qty: {quantity_to_add}) to sale.")
        self.show_status(f"Added {quantity_to_add} x {name}", status_type="success")
        self.update_sale_display()

    def prompt_custom_item(self):
        logging.info("Opening custom price/qty dialog.")
        product_names_list = sorted(list(self.products.keys()))
        if not product_names_list:
            logging.warning("Custom price dialog: No products defined.")
            messagebox.showwarning("No Products", "No products defined.", parent=self.root)
            self.show_status("No products defined to customize.", status_type="warning")
            return
        dialog = CustomPriceDialog(self.root, product_names_list)
        result = dialog.result
        if result:
            name, price, qty = result
            logging.info(f"Custom item received: Name='{name}', Price={price}, Qty={qty}.")
            self.add_item(name, override_price=price, quantity_to_add=qty)
        else:
            logging.info("Custom price/qty dialog cancelled.")
            self.show_status("Custom item cancelled.", status_type="info")

    def decrease_item_quantity(self):
        if not hasattr(self.ui, 'sale_tree') or not self.ui.sale_tree: return
        selected_id = self.ui.sale_tree.focus()
        if not selected_id:
            logging.warning("Decrease qty: No item selected.")
            messagebox.showwarning("No Selection", "Select item to decrease.", parent=self.root)
            self.show_status("Select item to decrease quantity.", status_type="info")
            return
        if selected_id in self.current_sale:
            item_name = self.current_sale[selected_id]['name']
            if self.current_sale[selected_id]['quantity'] > 1:
                self.current_sale[selected_id]['quantity'] -= 1
                logging.info(f"Decreased qty for '{item_name}'. New: {self.current_sale[selected_id]['quantity']}.")
                self.show_status(f"Decreased {item_name} qty.", status_type="info")
            else:
                del self.current_sale[selected_id]
                logging.info(f"Removed '{item_name}' (qty was 1).")
                self.show_status(f"Removed {item_name}.", status_type="info")
            self.update_sale_display(preserve_selection=selected_id if selected_id in self.current_sale else None)
        else:
            logging.error(f"Decrease qty failed: Key '{selected_id}' not in current sale.")
            self.show_status("Error decreasing quantity.", status_type="error")

    def remove_selected_item_from_sale(self):
        if not hasattr(self.ui, 'sale_tree') or not self.ui.sale_tree: return
        selected_id = self.ui.sale_tree.focus()
        if not selected_id:
            logging.warning("Remove item: No item selected.")
            messagebox.showwarning("No Selection", "Select item to remove.", parent=self.root)
            self.show_status("Select item to remove.", status_type="info")
            return
        if selected_id in self.current_sale:
            item_name = self.current_sale[selected_id]['name']
            if messagebox.askyesno("Confirm Remove", f"Remove '{item_name}'?", parent=self.root):
                logging.info(f"Removing '{item_name}' (key: {selected_id}).")
                del self.current_sale[selected_id]
                self.update_sale_display()
                self.show_status(f"Removed {item_name}.", status_type="success")
            else:
                logging.info(f"Removal of '{item_name}' cancelled.")
                self.show_status("Removal cancelled.", status_type="info")
        else:
            logging.error(f"Remove item failed: Key '{selected_id}' not in current sale.")
            self.show_status("Error removing item.", status_type="error")

    def update_sale_display(self, preserve_selection=None):
        logging.debug("Updating sale display...")
        if not hasattr(self.ui, 'sale_tree') or not hasattr(self.ui, 'total_label'):
            logging.error("UI elements not ready for sale display update.")
            return

        sale_tree = self.ui.sale_tree
        total_label = self.ui.total_label
        try:
            sale_tree.tag_configure('oddrow', background=self.style.lookup("Custom.Treeview", "background"))
            sale_tree.tag_configure('evenrow', background="#F5FFFA")
        except tk.TclError:
            logging.warning("Could not configure Treeview tags for sale display.")
            pass

        for i in sale_tree.get_children(): sale_tree.delete(i)
        self.total_amount = 0.0
        new_selection_id = None
        sorted_sale_items = sorted(self.current_sale.items(), key=lambda item: item[1]['name'])
        for i, (key, details) in enumerate(sorted_sale_items):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            subtotal = details['price'] * details['quantity']
            item_id_in_tree = sale_tree.insert("", tk.END, iid=key, values=(
                details['name'], details['quantity'],
                f"{gui_utils.CURRENCY_SYMBOL}{details['price']:.2f}",
                f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"
            ), tags=(tag,))
            if preserve_selection == key:
                new_selection_id = item_id_in_tree
            self.total_amount += subtotal
        total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{self.total_amount:.2f}")
        if new_selection_id:
            logging.debug(f"Reselecting sale tree item: {new_selection_id}")
            sale_tree.focus(new_selection_id)
            sale_tree.selection_set(new_selection_id)
        else:
            sale_tree.focus('');
            sale_tree.selection_set('')
        logging.debug(f"Sale display updated. Total: {self.total_amount:.2f}")

    def clear_sale(self):
        if not self.current_sale:
            logging.info("Clear sale: Already empty.")
            self.show_status("Sale is already empty.", status_type="info")
            return
        if messagebox.askyesno("Confirm Clear", "Clear current sale?", parent=self.root):
            logging.info("Clearing current sale.")
            self.current_sale = {}
            self.current_customer_name = "N/A"
            if hasattr(self.ui, 'customer_display_var'):
                self.ui.customer_display_var.set(f"Customer: {self.current_customer_name}")
            self.update_sale_display()
            self.show_status("Sale cleared.", status_type="success")
            logging.info("Sale cleared.")
        else:
            logging.info("Clear sale cancelled.")
            self.show_status("Clear sale cancelled.", status_type="info")

    def select_customer_for_sale(self):
        logging.info("Opening customer selection dialog.")
        dialog = CustomerSelectionDialog(self.root)
        name = dialog.result
        if name is not None:
            self.current_customer_name = name
            if hasattr(self.ui, 'customer_display_var'):
                self.ui.customer_display_var.set(f"Customer: {self.current_customer_name}")
            logging.info(f"Customer selected: '{self.current_customer_name}'.")
            self.show_status(f"Customer: {self.current_customer_name}", status_type="info")
        else:
            logging.info("Customer selection cancelled.")
            self.show_status("Customer selection cancelled.", status_type="info")

    def generate_receipt_text(self, sale_id, timestamp_obj, customer_name):
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
                details['name'][:18], details['quantity'],
                f"{gui_utils.CURRENCY_SYMBOL}{details['price']:.2f}",
                f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"
            )
        receipt += "======================================\n"
        receipt += "{:<29} {:>8}\n".format("TOTAL:", f"{gui_utils.CURRENCY_SYMBOL}{self.total_amount:.2f}")
        receipt += "--------------------------------------\n"
        receipt += "        Thank you, Come Again!\n"
        return receipt

    def finalize_sale(self):
        logging.info("Attempting finalize sale.")
        if not self.current_sale:
            logging.warning("Finalize failed: Empty sale.")
            messagebox.showwarning("Empty Sale", "Cannot finalize empty sale.", parent=self.root)
            self.show_status("Cannot finalize an empty sale.", status_type="error")
            return
        if self.current_customer_name == "N/A":
            logging.warning("Finalize failed: No customer.")
            messagebox.showwarning("No Customer", "Select customer first.", parent=self.root)
            self.show_status("Please select a customer.", status_type="error")
            return
        ts = datetime.datetime.now()
        items_for_db = []
        for item_key in self.current_sale:
            details = self.current_sale[item_key]
            items_for_db.append({
                'name': details['name'], 'price': details['price'], 'quantity': details['quantity']
            })
        logging.info(f"Finalizing sale for '{self.current_customer_name}' with {len(items_for_db)} item types.")
        sale_id = db_operations.save_sale_record(ts, self.total_amount, self.current_customer_name)
        if sale_id and db_operations.save_sale_items_records(sale_id, items_for_db):
            receipt = self.generate_receipt_text(sale_id, ts, self.current_customer_name)
            logging.info(f"Sale {sale_id} saved.")
            logging.debug(f"--- Receipt {sale_id} ---\n{receipt}\n---------------")
            messagebox.showinfo(f"Sale Finalized - ID: {sale_id}", receipt, parent=self.root)
            previous_customer = self.current_customer_name
            self.current_sale = {}
            self.current_customer_name = "N/A"
            if hasattr(self.ui, 'customer_display_var'):
                self.ui.customer_display_var.set(f"Customer: {self.current_customer_name}")
            self._update_latest_customer_label()
            self.update_sale_display()
            self.show_status(f"Sale {sale_id} recorded.", status_type="success")
        else:
            logging.error(f"Failed to save sale/items for '{self.current_customer_name}'. Sale ID: {sale_id}")
            self.show_status("Error saving sale.", status_type="error")

    def view_sales_history(self):
        logging.info("Opening sales history.")
        if DateEntry is None:
            logging.error("tkcalendar not found.")
            messagebox.showerror("Missing Library", "tkcalendar not installed.", parent=self.root)
            self.show_status("tkcalendar library missing for history.", status_type="error")
            return
        if self.history_window is None or not tk.Toplevel.winfo_exists(self.history_window):
            logging.debug("Creating SalesHistoryWindow.")
            self.history_window = SalesHistoryWindow(self.root)
            self.history_window.grab_set()
        else:
            logging.debug("Focusing existing SalesHistoryWindow.")
            self.history_window.deiconify();
            self.history_window.lift();
            self.history_window.focus_set();
            self.history_window.grab_set()

    def view_customers(self):
        logging.info("Opening customer management.")
        if self.customer_list_window is None or not tk.Toplevel.winfo_exists(self.customer_list_window):
            logging.debug("Creating CustomerListWindow.")
            self.customer_list_window = CustomerListWindow(self.root)
            self.customer_list_window.grab_set()
        else:
            logging.debug("Focusing existing CustomerListWindow.")
            self.customer_list_window.deiconify();
            self.customer_list_window.lift();
            self.customer_list_window.focus_set();
            self.customer_list_window.grab_set()
