import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
import datetime
import os
import sqlite3 # Keep for potential direct use or error catching if needed

# Import helpers and db operations
import db_operations
import gui_utils # Import the new utils module

# --- Custom Dialog for Price Input ---
class PriceInputDialog(tk.Toplevel):
    def __init__(self, parent, title, prompt, initialvalue=None):
        super().__init__(parent)
        self.title(title)
        gui_utils.set_window_icon(self) # Set icon
        self.result = None # Store the entered price

        dialog_width = 300
        dialog_height = 130
        # Use helper function to center relative to parent
        gui_utils.center_window(self, dialog_width, dialog_height)

        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text=prompt, wraplength=dialog_width - 20).grid(row=0, column=0, padx=10, pady=(10, 5), sticky='w')

        self.price_var = tk.StringVar()
        if initialvalue is not None:
            self.price_var.set(str(initialvalue))

        vcmd = (self.register(self.validate_price), '%P')
        self.price_entry = ttk.Entry(self, textvariable=self.price_var, validate='key', validatecommand=vcmd)
        self.price_entry.grid(row=1, column=0, padx=10, pady=5, sticky='ew')
        self.price_entry.focus_set()
        self.price_entry.select_range(0, tk.END)

        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, pady=10)

        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok, width=10)
        ok_button.pack(side=tk.LEFT, padx=5)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel, width=10)
        cancel_button.pack(side=tk.LEFT, padx=5)

        self.bind('<Return>', lambda event=None: self.on_ok())
        self.bind('<Escape>', lambda event=None: self.on_cancel())
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.wait_window(self)

    def validate_price(self, P):
        """Allow only digits and at most one decimal point."""
        if P == "": return True
        try:
            if P.count('.') <= 1 and all(c.isdigit() or c == '.' for c in P):
                 if P.startswith('0') and len(P) > 1 and not P.startswith('0.'):
                     return False
                 return True
            else:
                return False
        except ValueError:
            return False

    def on_ok(self):
        price_str = self.price_var.get().strip()
        if not price_str:
            messagebox.showwarning("Missing Input", "Please enter a price.", parent=self)
            return
        try:
            price = float(price_str)
            if price < 0:
                raise ValueError("Price cannot be negative.")
            self.result = price
            self.destroy()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid non-negative number for the price.", parent=self)

    def on_cancel(self):
        self.result = None
        self.destroy()


# --- Customer Selection Dialog Class ---
class CustomerSelectionDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Select or Enter Customer")
        gui_utils.set_window_icon(self)

        dialog_width = 350
        dialog_height = 150 # Reverted height
        self.result = None
        # Use helper function to center relative to parent
        gui_utils.center_window(self, dialog_width, dialog_height)

        self.transient(parent)
        self.grab_set()
        self.columnconfigure(0, weight=1)
        # Configure only 3 rows now
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=0)

        ttk.Label(self, text="Select existing or enter new customer:").grid(row=0, column=0, pady=(10, 5), padx=10, sticky='w')

        # Fetch the latest list of customers each time dialog opens
        self.customer_names_list = db_operations.fetch_distinct_customer_names()
        self.customer_var = tk.StringVar()
        # Use Combobox again
        self.customer_combobox = ttk.Combobox(self, textvariable=self.customer_var, values=self.customer_names_list)
        self.customer_combobox.grid(row=1, column=0, pady=5, padx=10, sticky='ew')
        self.customer_combobox.focus_set()

        # Button frame
        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, pady=10) # Buttons back on row 2
        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok)
        ok_button.pack(side=tk.LEFT, padx=10)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=10)

        self.bind('<Return>', lambda event=None: self.on_ok())
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.wait_window(self)

    def on_ok(self):
        """Handle OK button click. Add new customer if necessary."""
        selected_name = self.customer_var.get().strip()
        if not selected_name:
            self.result = "N/A"
        else:
            self.result = selected_name
            is_new = True
            # Check against the *full* list fetched initially
            for existing_name in self.customer_names_list:
                if selected_name.lower() == existing_name.lower():
                    is_new = False
                    break
            if is_new and selected_name != 'N/A':
                print(f"Adding new customer from selection dialog: {selected_name}")
                if not db_operations.add_customer_to_db(selected_name, None, None):
                    print(f"Warning: Could not add new customer '{selected_name}' via selection dialog.")
                    pass
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

# --- Custom Price Dialog Class ---
class CustomPriceDialog(tk.Toplevel):
    def __init__(self, parent, product_names):
        super().__init__(parent)
        self.parent = parent
        self.product_names = product_names
        self.title("Add Custom Price Item")
        gui_utils.set_window_icon(self) # Use helper function
        self.result = None

        dialog_width = 350
        dialog_height = 210
        # Use helper function to center relative to parent
        gui_utils.center_window(self, dialog_width, dialog_height)

        self.transient(parent)
        self.grab_set()
        self.columnconfigure(1, weight=1) # Allow entry/combobox to expand

        # Widgets
        ttk.Label(self, text="Product:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.product_var = tk.StringVar()
        self.product_combobox = ttk.Combobox(self, textvariable=self.product_var, values=self.product_names, state="readonly")
        if self.product_names:
            self.product_var.set(self.product_names[0])
        self.product_combobox.grid(row=0, column=1, padx=10, pady=10, sticky='ew')

        ttk.Label(self, text="Custom Price:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        self.price_var = tk.StringVar()
        vcmd_price = (self.register(self.validate_price), '%P')
        self.price_entry = ttk.Entry(self, textvariable=self.price_var, validate='key', validatecommand=vcmd_price)
        self.price_entry.grid(row=1, column=1, padx=10, pady=5, sticky='ew')

        # Quantity Entry
        ttk.Label(self, text="Quantity:").grid(row=2, column=0, padx=10, pady=5, sticky='w')
        self.qty_var = tk.StringVar(value='1') # Default quantity to 1
        vcmd_qty = (self.register(self.validate_quantity), '%P')
        self.qty_entry = ttk.Entry(self, textvariable=self.qty_var, validate='key', validatecommand=vcmd_qty, width=5)
        self.qty_entry.grid(row=2, column=1, padx=10, pady=5, sticky='w') # Align left

        self.price_entry.focus_set() # Focus on price entry initially

        # Button frame
        button_frame = ttk.Frame(self)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15) # Moved down
        ok_button = ttk.Button(button_frame, text="Add to Sale", command=self.on_ok)
        ok_button.pack(side=tk.LEFT, padx=10)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=10)

        self.bind('<Return>', lambda event=None: self.on_ok())
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.wait_window(self)

    def validate_price(self, P):
        """Allow only digits and at most one decimal point."""
        if P == "": return True
        try:
            if P.count('.') <= 1 and all(c.isdigit() or c == '.' for c in P):
                 return True
            else:
                return False
        except ValueError:
            return False

    def validate_quantity(self, P):
        """Allow only positive integers for quantity."""
        if P == "": return True # Allow empty
        if P.isdigit() and int(P) > 0: # Check if it's digits and greater than 0
            return True
        else:
            return False

    def on_ok(self):
        product_name = self.product_var.get()
        price_str = self.price_var.get()
        qty_str = self.qty_var.get()

        if not product_name:
            messagebox.showwarning("Missing Product", "Please select a product.", parent=self)
            return
        if not price_str:
             messagebox.showwarning("Missing Price", "Please enter a custom price.", parent=self)
             return
        if not qty_str:
             messagebox.showwarning("Missing Quantity", "Please enter a quantity.", parent=self)
             return

        try:
            custom_price = float(price_str)
            if custom_price < 0: raise ValueError("Price cannot be negative.")
        except ValueError:
            messagebox.showerror("Invalid Price", "Please enter a valid positive number for the price.", parent=self)
            return

        try:
            quantity = int(qty_str)
            if quantity <= 0: raise ValueError("Quantity must be positive.")
        except ValueError:
             messagebox.showerror("Invalid Quantity", "Please enter a valid positive whole number for the quantity.", parent=self)
             return

        # Store all three values in the result
        self.result = (product_name, custom_price, quantity)
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

