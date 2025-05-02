import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
import datetime
import os
import sqlite3 # Keep for error catching if needed

# --- External Libraries ---
from dateutil.relativedelta import relativedelta, MO, SU
try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None

# --- Import Project Modules ---
import db_operations
import gui_utils # Import the new utils module
# Import dialogs (assuming they are in the same directory or package)
from gui_dialogs import PriceInputDialog, CustomerSelectionDialog, CustomPriceDialog
# --- Import the separated window classes ---
from gui_customer_manager import CustomerListWindow
from gui_history_window import SalesHistoryWindow


# --- Main Application Class ---
class POSApp:
    def __init__(self, root):
        """Initialize the POS Application."""
        self.root = root
        self.root.title("SEASIDE Water Refilling Station - POS")
        app_width = 850
        app_height = 750
        # self.root.state('zoomed') # REMOVED: Don't start maximized
        self.root.geometry(f"{app_width}x{app_height}") # Set initial size
        self.root.minsize(700, 600)

        # Use helper function to set icon for main window
        gui_utils.set_window_icon(self.root)

        # Center the main window on startup
        gui_utils.center_window(self.root, app_width, app_height)

        db_operations.initialize_db()

        self.products = self.load_products()
        self.current_sale = {}
        self.total_amount = 0.0
        self.history_window = None
        self.customer_list_window = None

        # --- Configure Main Layout ---
        # --- CHANGE: Set both columns to equal weight ---
        self.root.columnconfigure(0, weight=1) # Product frame
        self.root.columnconfigure(1, weight=1) # Sale frame (was 2)
        self.root.rowconfigure(0, weight=1)

        # --- Create Frames ---
        self.product_frame = ttk.Frame(root, padding="5") # Reduced padding
        self.sale_frame = ttk.Frame(root, padding="5")    # Reduced padding
        self.product_frame.grid(row=0, column=0, sticky="nsew")
        self.sale_frame.grid(row=0, column=1, sticky="nsew")

        # Configure product frame grid rows/columns for resizing
        self.product_frame.columnconfigure(0, weight=1)
        self.product_frame.columnconfigure(1, weight=0)
        self.product_frame.rowconfigure(1, weight=1) # Product button area
        self.product_frame.rowconfigure(2, weight=0) # Custom button row
        self.product_frame.rowconfigure(4, weight=1) # Product management list area
        self.product_frame.rowconfigure(3, weight=0) # Separator/Label fixed height
        self.product_frame.rowconfigure(5, weight=0) # Buttons fixed height

        # Configure sale frame grid rows/columns for resizing
        self.sale_frame.columnconfigure(0, weight=1)
        self.sale_frame.columnconfigure(1, weight=0)
        self.sale_frame.rowconfigure(1, weight=1)
        self.sale_frame.rowconfigure(0, weight=0)
        self.sale_frame.rowconfigure(2, weight=0)
        self.sale_frame.rowconfigure(3, weight=0)

        # --- Populate Product Frame (Sale Buttons) ---
        ttk.Label(self.product_frame, text="Add to Sale", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 2), sticky='w') # Reduced font/pady
        self.product_canvas = tk.Canvas(self.product_frame)
        product_scrollbar = ttk.Scrollbar(self.product_frame, orient="vertical", command=self.product_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.product_canvas)
        self.product_canvas.bind('<Configure>', lambda e: self.product_canvas.configure(scrollregion=self.product_canvas.bbox("all")))
        self.product_canvas_window = self.product_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        # --- Remove binding that caused re-layout on resize ---
        # self.scrollable_frame.bind('<Configure>', self._configure_scrollable_frame)
        self.product_canvas.configure(yscrollcommand=product_scrollbar.set)
        self.product_canvas.grid(row=1, column=0, sticky="nsew")
        product_scrollbar.grid(row=1, column=1, sticky="ns")
        self.populate_product_buttons() # Initial population

        # --- Product Management Section ---
        ttk.Separator(self.product_frame, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky='ew', pady=10) # Reduced pady
        ttk.Label(self.product_frame, text="Manage Products", font=("Arial", 12, "bold")).grid(row=3, column=0, columnspan=2, pady=(5, 2), sticky='w') # Reduced font/pady

        self.product_list_frame = ttk.Frame(self.product_frame)
        self.product_list_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=2) # Reduced pady
        self.product_list_frame.rowconfigure(0, weight=1)
        self.product_list_frame.columnconfigure(0, weight=1)
        self.product_listbox = tk.Listbox(self.product_list_frame, exportselection=False)
        self.product_listbox.grid(row=0, column=0, sticky="nsew")
        product_list_scrollbar = ttk.Scrollbar(self.product_list_frame, orient="vertical", command=self.product_listbox.yview)
        self.product_listbox.configure(yscrollcommand=product_list_scrollbar.set)
        product_list_scrollbar.grid(row=0, column=1, sticky="ns")
        self.populate_product_management_list()

        product_mgmt_button_frame = ttk.Frame(self.product_frame)
        product_mgmt_button_frame.grid(row=5, column=0, columnspan=2, pady=5, sticky='w') # Reduced pady
        self.add_product_button = ttk.Button(product_mgmt_button_frame, text="Add New Product", command=self.prompt_new_item)
        self.add_product_button.pack(side=tk.LEFT, padx=2) # Reduced padx
        self.edit_product_button = ttk.Button(product_mgmt_button_frame, text="Edit Product", command=self.prompt_edit_item)
        self.edit_product_button.pack(side=tk.LEFT, padx=2)
        self.remove_product_button = ttk.Button(product_mgmt_button_frame, text="Remove Product", command=self.remove_selected_product_permanently)
        self.remove_product_button.pack(side=tk.LEFT, padx=2)
        self.view_customers_button = ttk.Button(product_mgmt_button_frame, text="Manage Customers", command=self.view_customers)
        self.view_customers_button.pack(side=tk.LEFT, padx=2)


        # --- Populate Sale Frame ---
        ttk.Label(self.sale_frame, text="Current Sale", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=5, sticky='w') # Reduced font/pady
        columns = ("item", "quantity", "price", "subtotal")
        self.sale_tree = ttk.Treeview(self.sale_frame, columns=columns, show="headings", selectmode="browse")
        self.sale_tree.heading("item", text="Item")
        self.sale_tree.heading("quantity", text="Qty")
        self.sale_tree.heading("price", text="Price")
        self.sale_tree.heading("subtotal", text="Subtotal")
        self.sale_tree.column("item", anchor=tk.W, width=150, stretch=True)
        self.sale_tree.column("quantity", anchor=tk.CENTER, width=40, stretch=False)
        self.sale_tree.column("price", anchor=tk.E, width=80, stretch=False)
        self.sale_tree.column("subtotal", anchor=tk.E, width=90, stretch=False)
        self.sale_tree.grid(row=1, column=0, sticky="nsew", padx=(5,0), pady=2) # Reduced pady
        sale_scrollbar = ttk.Scrollbar(self.sale_frame, orient="vertical", command=self.sale_tree.yview)
        self.sale_tree.configure(yscrollcommand=sale_scrollbar.set)
        sale_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0,5), pady=2) # Reduced pady

        # --- Finalize Button and Total Label Frame (Row 2) ---
        finalize_total_frame = ttk.Frame(self.sale_frame)
        finalize_total_frame.grid(row=2, column=0, columnspan=2, pady=(5,2), sticky="ew") # Reduced pady
        finalize_total_frame.columnconfigure(0, weight=1)
        finalize_total_frame.columnconfigure(1, weight=0)
        finalize_total_frame.columnconfigure(2, weight=0)

        self.finalize_button = ttk.Button(finalize_total_frame, text="Finalize Sale", command=self.finalize_sale)
        self.finalize_button.grid(row=0, column=1, padx=(5, 10), sticky="e")

        self.total_label = ttk.Label(finalize_total_frame, text=f"{gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 14, "bold"))
        self.total_label.grid(row=0, column=2, padx=(0, 5), sticky="e")


        # --- Other Sale Action Buttons Frame (Row 3) ---
        other_sale_actions_frame = ttk.Frame(self.sale_frame)
        other_sale_actions_frame.grid(row=3, column=0, columnspan=2, pady=(0, 5), sticky="e") # Reduced pady

        self.history_button = ttk.Button(other_sale_actions_frame, text="View History", command=self.view_sales_history)
        self.history_button.pack(side=tk.RIGHT, padx=2) # Reduced padx

        self.clear_button = ttk.Button(other_sale_actions_frame, text="Clear Sale", command=self.clear_sale)
        self.clear_button.pack(side=tk.RIGHT, padx=2)

        self.remove_item_button = ttk.Button(other_sale_actions_frame, text="Remove Item", command=self.remove_selected_item_from_sale)
        self.remove_item_button.pack(side=tk.RIGHT, padx=2)

        self.decrease_qty_button = ttk.Button(other_sale_actions_frame, text="- Qty", command=self.decrease_item_quantity)
        self.decrease_qty_button.pack(side=tk.RIGHT, padx=2)


        self.update_sale_display()

    # --- Helper for Scrollable Frame Resizing ---
    def _configure_scrollable_frame(self, event):
        """Reset the scroll region to encompass the inner frame"""
        # --- Removed re-population on resize ---
        self.product_canvas.configure(scrollregion=self.product_canvas.bbox("all"))
        self.product_canvas.itemconfig(self.product_canvas_window, width=event.width)


    # --- Product Persistence Methods (SQLite) ---
    def load_products(self):
        """Loads products from the SQLite database."""
        print(f"Loading products from database file '{db_operations.DATABASE_FILENAME}'...")
        products = db_operations.fetch_products_from_db()
        if not products:
             print("No products found in database.")
        else:
             print(f"Loaded {len(products)} products.")
        return products

    # --- Product Handling Methods ---
    def populate_product_buttons(self, available_width=None): # Keep parameter for potential future use
        """Clears and repopulates the product buttons with a fixed 4-column layout."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # --- Use fixed 4 columns ---
        max_cols = 4
        for i in range(max_cols):
            self.scrollable_frame.columnconfigure(i, weight=1)

        row_num, col_num = 0, 0
        sorted_products = sorted(self.products.items())
        for name, price in sorted_products:
            btn_text = f"{name}\n({gui_utils.CURRENCY_SYMBOL}{price:.2f})"
            btn = ttk.Button(
                self.scrollable_frame,
                text=btn_text,
                command=lambda n=name: self.add_item(n),
            )
            btn.grid(row=row_num, column=col_num, padx=2, pady=2, sticky="ew")
            col_num += 1
            if col_num >= max_cols:
                col_num = 0
                row_num += 1

        # Add Custom Price Button below the grid
        custom_button = ttk.Button(self.scrollable_frame, text="Custom Price Item", command=self.prompt_custom_item)
        custom_button.grid(row=row_num + 1, column=0, columnspan=max_cols, pady=(10, 5), sticky='ew')

        self.scrollable_frame.update_idletasks()
        self.product_canvas.configure(scrollregion=self.product_canvas.bbox("all"))


    def populate_product_management_list(self):
        """Clears and repopulates the product management listbox."""
        self.product_listbox.delete(0, tk.END)
        sorted_products = sorted(self.products.items())
        for name, price in sorted_products:
            self.product_listbox.insert(tk.END, f"{name} ({gui_utils.CURRENCY_SYMBOL}{price:.2f})")

    def _get_selected_product_details(self):
        """Helper method to get the name and price of the selected product in the listbox."""
        selection_indices = self.product_listbox.curselection()
        if not selection_indices:
            messagebox.showwarning("No Selection", "Please select a product from the 'Manage Products' list first.")
            return None, None
        selected_index = selection_indices[0]
        selected_text = self.product_listbox.get(selected_index)
        try:
            parts = selected_text.split(f' ({gui_utils.CURRENCY_SYMBOL}')
            product_name = parts[0]
            price_str = parts[1].rstrip(')')
            price = float(price_str)
            return product_name, price
        except Exception as e:
             messagebox.showerror("Error", f"Could not parse selected product details: {e}")
             print(f"Error parsing listbox text '{selected_text}': {e}")
             return None, None

    def prompt_new_item(self):
        """Opens dialogs to get new product name and price, adds it to DB and UI."""
        name = simpledialog.askstring("New Product", "Enter product name:", parent=self.root)
        if not name: return
        if name in self.products:
             messagebox.showwarning("Product Exists", f"Product '{name}' already exists.", parent=self.root)
             return

        # Use custom dialog for price
        price_dialog = PriceInputDialog(self.root, "New Product Price", f"Enter price for {name}:")
        price = price_dialog.result # Get result from custom dialog

        if price is not None: # Check if dialog wasn't cancelled
            try:
                # Price is already validated as float by the dialog
                if db_operations.insert_product_to_db(name, price):
                    self.products[name] = price
                    self.populate_product_buttons() # Re-populate with fixed layout
                    self.populate_product_management_list()
                    print(f"Added new product to DB and UI: {name} - {gui_utils.CURRENCY_SYMBOL}{price:.2f}")
                    messagebox.showinfo("Success", f"Product '{name}' added successfully.", parent=self.root)
            except Exception as e: # Catch potential DB errors
                 messagebox.showerror("Database Error", f"Could not save product to database.\n{e}", parent=self.root)


    def prompt_edit_item(self):
        """Gets selected product, prompts for new details, updates DB and UI."""
        original_name, original_price = self._get_selected_product_details()
        if original_name is None: return
        new_name = simpledialog.askstring("Edit Product", "Enter new product name:", initialvalue=original_name, parent=self.root)
        if not new_name: return

        # Use custom dialog for price
        price_dialog = PriceInputDialog(self.root, "Edit Product Price", f"Enter new price for {new_name}:", initialvalue=f"{original_price:.2f}")
        new_price = price_dialog.result # Get result from custom dialog

        if new_price is not None: # Check if dialog wasn't cancelled
            try:
                # Price is already validated as float by the dialog
                if new_name != original_name and new_name in self.products:
                     messagebox.showerror("Edit Error", f"Cannot rename to '{new_name}'.\nA product with that name already exists.", parent=self.root)
                     return
                if db_operations.update_product_in_db(original_name, new_name, new_price):
                    if original_name in self.products:
                         del self.products[original_name]
                    self.products[new_name] = new_price
                    self.populate_product_buttons() # Re-populate with fixed layout
                    self.populate_product_management_list()
                    messagebox.showinfo("Success", f"Product '{original_name}' updated successfully.", parent=self.root)
            except Exception as e: # Catch potential DB errors
                 messagebox.showerror("Database Error", f"Could not update product in database.\n{e}", parent=self.root)


    def remove_selected_product_permanently(self):
        """Gets selection from listbox, confirms, deletes from DB and updates UI."""
        product_name, _ = self._get_selected_product_details()
        if product_name is None: return
        confirmed = messagebox.askyesno("Confirm Permanent Deletion",
                                        f"Are you sure you want to permanently delete '{product_name}'?\n"
                                        "This cannot be undone.", parent=self.root)
        if not confirmed: return
        if db_operations.delete_product_from_db(product_name):
            if product_name in self.products:
                 del self.products[product_name]
            self.populate_product_buttons() # Re-populate with fixed layout
            self.populate_product_management_list()
            messagebox.showinfo("Success", f"Product '{product_name}' permanently deleted.", parent=self.root)

    # --- Sale Handling Methods ---
    def add_item(self, name, override_price=None, quantity_to_add=1):
        """Adds an item to the current sale or increments its quantity."""
        if override_price is not None:
            price_to_use = override_price
            print(f"Using override price for {name}: {price_to_use}")
        elif name in self.products:
             price_to_use = self.products[name]
        else:
             messagebox.showerror("Error", f"Product '{name}' not found in product list.")
             return

        if name in self.current_sale:
            if override_price is not None:
                 if self.current_sale[name]['price'] != override_price:
                     print(f"Updating price for {name} in current sale to override price: {override_price}")
                 self.current_sale[name]['price'] = override_price
            self.current_sale[name]['quantity'] += quantity_to_add
        else:
            self.current_sale[name] = {'price': price_to_use, 'quantity': quantity_to_add}

        print(f"Added/Updated {name}. Current sale: {self.current_sale}")
        self.update_sale_display()

    def prompt_custom_item(self):
        """Opens a dialog to select a product and enter a custom price and quantity."""
        dialog = CustomPriceDialog(self.root, list(self.products.keys()))
        result = dialog.result
        if result:
            product_name, custom_price, quantity = result
            if product_name and custom_price is not None and quantity is not None:
                self.add_item(product_name, override_price=custom_price, quantity_to_add=quantity)
            elif product_name:
                 if custom_price is None:
                     messagebox.showwarning("Invalid Price", "Please enter a valid custom price.", parent=self.root)
                 if quantity is None:
                      messagebox.showwarning("Invalid Quantity", "Please enter a valid quantity.", parent=self.root)


    def decrease_item_quantity(self):
        """Decreases the quantity of the selected item in the sale tree."""
        selected_item_id = self.sale_tree.focus()
        if not selected_item_id:
            messagebox.showwarning("No Selection", "Please select an item from the 'Current Sale' list to decrease quantity.")
            return
        try:
            item_values = self.sale_tree.item(selected_item_id, 'values')
            item_name = item_values[0]
        except IndexError:
             messagebox.showerror("Error", "Could not retrieve selected item details.")
             return
        if item_name in self.current_sale:
            current_quantity = self.current_sale[item_name]['quantity']
            if current_quantity > 1:
                self.current_sale[item_name]['quantity'] -= 1
                print(f"Decreased quantity for {item_name}.")
            else:
                print(f"Quantity for {item_name} is 1. Removing item.")
                del self.current_sale[item_name]
            self.update_sale_display(preserve_selection=item_name)
        else:
             messagebox.showerror("Error", "Could not find the selected item in the current sale data.")

    def remove_selected_item_from_sale(self):
        """Removes the currently selected item from the sale tree (current sale only)."""
        selected_item_id = self.sale_tree.focus()
        if not selected_item_id:
            messagebox.showwarning("No Selection", "Please select an item from the 'Current Sale' list to remove.")
            return
        try:
            item_values = self.sale_tree.item(selected_item_id, 'values')
            item_name = item_values[0]
        except IndexError:
             messagebox.showerror("Error", "Could not retrieve selected item details.")
             return
        if item_name in self.current_sale:
            confirmed = messagebox.askyesno("Confirm Remove Item", f"Are you sure you want to remove all '{item_name}' from the current sale?")
            if confirmed:
                del self.current_sale[item_name]
                self.update_sale_display()
                print(f"Removed {item_name} from current sale display.")
        else:
             messagebox.showerror("Error", "Could not find the selected item in the current sale data.")

    def update_sale_display(self, preserve_selection=None):
        """Updates the Treeview and total label, optionally preserving selection."""
        selected_id_to_preserve = None
        if preserve_selection is None:
            selected_id_to_preserve = self.sale_tree.focus()

        for i in self.sale_tree.get_children():
            self.sale_tree.delete(i)

        self.total_amount = 0.0
        sorted_sale_items = sorted(self.current_sale.items())
        new_selection_id = None

        for name, details in sorted_sale_items:
            price = details['price']
            quantity = details['quantity']
            subtotal = price * quantity
            price_str = f"{gui_utils.CURRENCY_SYMBOL}{price:.2f}"
            subtotal_str = f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"
            item_id = self.sale_tree.insert("", tk.END, values=(name, quantity, price_str, subtotal_str))

            if preserve_selection is not None and name == preserve_selection:
                new_selection_id = item_id
            elif preserve_selection is None and selected_id_to_preserve:
                 try:
                     if self.sale_tree.exists(selected_id_to_preserve):
                         original_selected_name = self.sale_tree.item(selected_id_to_preserve, 'values')[0]
                         if original_selected_name == name:
                             new_selection_id = item_id
                     else:
                         selected_id_to_preserve = None
                 except (tk.TclError, IndexError):
                     selected_id_to_preserve = None

            self.total_amount += subtotal

        self.total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{self.total_amount:.2f}")

        if new_selection_id:
            print(f"Reselecting item ID: {new_selection_id}")
            self.sale_tree.focus(new_selection_id)
            self.sale_tree.selection_set(new_selection_id)
        elif selected_id_to_preserve and not self.sale_tree.exists(selected_id_to_preserve):
             self.sale_tree.focus('')
             self.sale_tree.selection_set('')
        elif preserve_selection is None and not new_selection_id:
             self.sale_tree.focus('')
             self.sale_tree.selection_set('')


    def clear_sale(self):
        """Clears the current sale data and updates the display."""
        if not self.current_sale: return
        confirmed = messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the current sale?")
        if confirmed:
            self.current_sale = {}
            self.update_sale_display()
            print("Sale cleared.")

    def generate_receipt_text(self, sale_id, timestamp_obj, customer_name):
        """Generates a simple text receipt for the current sale."""
        receipt = f"--- SEASIDE Water Refilling Station ---\n"
        receipt += f"Sale ID: {sale_id}\n"
        receipt += f"Date: {timestamp_obj.strftime('%Y-%m-%d %H:%M:%S')}\n"
        receipt += f"Customer: {customer_name}\n"
        receipt += "--------------------------------------\n"
        receipt += "{:<18} {:>3} {:>7} {:>8}\n".format("Item", "Qty", "Price", "Subtotal")
        receipt += "--------------------------------------\n"
        for name, details in sorted(self.current_sale.items()):
            qty = details['quantity']
            price = details['price']
            subtotal = qty * price
            price_str = f"{gui_utils.CURRENCY_SYMBOL}{price:.2f}"
            subtotal_str = f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"
            receipt += "{:<18} {:>3d} {:>7} {:>8}\n".format(name[:18], qty, price_str, subtotal_str)
        receipt += "======================================\n"
        total_str = f"{gui_utils.CURRENCY_SYMBOL}{self.total_amount:.2f}"
        receipt += "{:<29} {:>8}\n".format("TOTAL:", total_str)
        receipt += "--------------------------------------\n"
        receipt += "        Thank you!\n"
        return receipt

    def finalize_sale(self):
        """Prompts for customer name using custom dialog, records sale, generates receipt, clears sale."""
        if not self.current_sale:
             messagebox.showwarning("Empty Sale", "Cannot finalize an empty sale.")
             return

        dialog = CustomerSelectionDialog(self.root)
        customer_name = dialog.result
        if customer_name is None:
             print("Sale cancelled by user (customer selection).")
             return
        if not customer_name.strip():
            customer_name = "N/A"

        current_timestamp_obj = datetime.datetime.now()
        sale_id = db_operations.save_sale_record(current_timestamp_obj, self.total_amount, customer_name)
        if sale_id is None: return

        items_saved = db_operations.save_sale_items_records(sale_id, self.current_sale)
        if not items_saved: return

        receipt_text = self.generate_receipt_text(sale_id, current_timestamp_obj, customer_name)
        print("--- Receipt ---")
        print(receipt_text)
        print("---------------")
        messagebox.showinfo(f"Sale Finalized - ID: {sale_id}", receipt_text)

        self.current_sale = {}
        self.update_sale_display()
        print(f"Sale {sale_id} finalized and recorded.")

    def view_sales_history(self):
        """Opens the sales history window."""
        if DateEntry is None:
             messagebox.showerror("Missing Library",
                                  "Required library 'tkcalendar' is not installed.\n"
                                  "Please install it using:\n"
                                  "pip install tkcalendar")
             return

        if self.history_window is None or not tk.Toplevel.winfo_exists(self.history_window):
            # --- Use the imported class ---
            self.history_window = SalesHistoryWindow(self.root)
            self.history_window.grab_set()
        else:
            self.history_window.deiconify()
            self.history_window.lift()
            self.history_window.focus_set()

    def view_customers(self):
        """Opens the customer management window."""
        if self.customer_list_window is None or not tk.Toplevel.winfo_exists(self.customer_list_window):
            # --- Use the imported class ---
            self.customer_list_window = CustomerListWindow(self.root)
            self.customer_list_window.grab_set()
        else:
            self.customer_list_window.deiconify()
            self.customer_list_window.lift()
            self.customer_list_window.focus_set()
