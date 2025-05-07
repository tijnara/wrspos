import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
import datetime
import os
# import sqlite3 # Not directly used here

import db_operations
import gui_utils


# --- Custom Dialog for Price Input ---
class PriceInputDialog(tk.Toplevel):
    def __init__(self, parent, title, prompt, initialvalue=None):
        super().__init__(parent)
        self.title(title)
        gui_utils.set_window_icon(self)
        self.result = None

        dialog_width = 300
        dialog_height = 130
        gui_utils.center_window(self, dialog_width, dialog_height)

        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)  # Typically, small input dialogs are fixed size
        self.columnconfigure(0, weight=1)  # Allow entry to expand if window were resizable

        ttk.Label(self, text=prompt, wraplength=dialog_width - 20).grid(row=0, column=0, padx=10, pady=(10, 5),
                                                                        sticky='w')

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
                if P.startswith('0') and len(P) > 1 and not P.startswith('0.'):  # Prevent "07"
                    return False
                return True
            else:
                return False
        except ValueError:  # Should not happen with the checks above but good practice
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
            messagebox.showerror("Invalid Input", "Please enter a valid non-negative number for the price.",
                                 parent=self)

    def on_cancel(self):
        self.result = None
        self.destroy()


# --- Customer Selection Dialog Class (Modified for Entry + Listbox) ---
class CustomerSelectionDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Select or Enter Customer")
        gui_utils.set_window_icon(self)

        dialog_width = 350
        dialog_height = 300  # Increased height for listbox, can be resized
        self.result = None
        gui_utils.center_window(self, dialog_width, dialog_height)

        self.transient(parent)
        self.grab_set()

        # Make this dialog resizable
        self.resizable(True, True)
        self.minsize(dialog_width, 250)  # Set a minimum practical size

        # Configure main column and listbox row to expand
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # Listbox frame row

        ttk.Label(self, text="Enter or select customer name:").grid(row=0, column=0, pady=(10, 2), padx=10, sticky='w')

        self.all_customer_names = db_operations.fetch_distinct_customer_names()
        if 'N/A' in self.all_customer_names:
            self.all_customer_names.remove('N/A')

        self.customer_var = tk.StringVar()
        self.customer_entry = ttk.Entry(self, textvariable=self.customer_var, width=40)
        self.customer_entry.grid(row=1, column=0, pady=(0, 2), padx=10, sticky='ew')  # Entry expands horizontally
        self.customer_entry.focus_set()
        self.customer_entry.bind('<KeyRelease>', self.update_suggestions)

        # Frame for Listbox and Scrollbar (this frame will contain the listbox)
        self.list_frame = ttk.Frame(self)  # Store as instance variable
        self.list_frame.grid(row=2, column=0, padx=10, pady=(0, 5), sticky='nsew')  # Frame expands
        self.list_frame.rowconfigure(0, weight=1)  # Row inside list_frame expands
        self.list_frame.columnconfigure(0, weight=1)  # Column inside list_frame expands

        self.suggestion_listbox = tk.Listbox(self.list_frame, height=5, exportselection=False)
        self.suggestion_listbox.grid(row=0, column=0, sticky='nsew')  # Listbox expands within its frame
        self.suggestion_listbox.bind('<Double-Button-1>', self.on_suggestion_select)
        self.suggestion_listbox.bind('<Return>', self.on_suggestion_select)

        list_scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.suggestion_listbox.yview)
        self.suggestion_listbox.configure(yscrollcommand=list_scrollbar.set)
        list_scrollbar.grid(row=0, column=1, sticky='ns')

        self.list_frame.grid_remove()  # Initially hide

        # Button frame (Row 3)
        button_frame = ttk.Frame(self)
        button_frame.grid(row=3, column=0, pady=10)
        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok)
        ok_button.pack(side=tk.LEFT, padx=10)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=10)

        self.bind('<Return>', lambda event=None: self.on_ok())
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.wait_window(self)

    def update_suggestions(self, event=None):
        """Filter customer list based on typed text and show in listbox."""
        current_text = self.customer_var.get()
        typed_lower = current_text.lower()

        # Simplified key check, primarily for printable chars and backspace/delete
        if event and event.keysym and len(event.keysym) > 1 and event.keysym not in ('BackSpace', 'Delete', 'Shift_L',
                                                                                     'Shift_R', 'Control_L',
                                                                                     'Control_R'):
            if not event.keysym.startswith('F'):  # Allow F-keys
                return

        self.suggestion_listbox.delete(0, tk.END)

        if not current_text:
            self.list_frame.grid_remove()
            return

        suggestions = [name for name in self.all_customer_names if name.lower().startswith(typed_lower)]

        if suggestions:
            for name in suggestions[:10]:
                self.suggestion_listbox.insert(tk.END, name)
            self.list_frame.grid()  # Show the listbox frame
        else:
            self.list_frame.grid_remove()

    def on_suggestion_select(self, event=None):
        """Update entry field when a suggestion is clicked or Enter is pressed on listbox."""
        selection_indices = self.suggestion_listbox.curselection()
        if selection_indices:
            selected_name = self.suggestion_listbox.get(selection_indices[0])
            self.customer_var.set(selected_name)
            self.list_frame.grid_remove()
            self.customer_entry.icursor(tk.END)
            self.customer_entry.focus_set()

    def on_ok(self):
        """Handle OK button click. Add new customer if necessary."""
        selected_name = self.customer_var.get().strip()
        if not selected_name:
            self.result = "N/A"  # Default to N/A if empty
        else:
            self.result = selected_name
            is_new = True
            current_db_names = db_operations.fetch_distinct_customer_names()
            for existing_name in current_db_names:
                if selected_name.lower() == existing_name.lower():
                    is_new = False
                    self.result = existing_name  # Use the existing cased name
                    break
            if is_new and selected_name != 'N/A':
                logging.info(f"Adding new customer from dialog: {selected_name}")
                if not db_operations.add_customer_to_db(selected_name, None, None):
                    logging.warning(f"Could not add new customer '{selected_name}' via dialog (db_operations failed).")
                    # Optionally show error, or let db_operations handle it
                    # For now, we proceed with the name entered by user even if DB add failed.
                    # Caller should be aware.
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
        gui_utils.set_window_icon(self)
        self.result = None

        dialog_width = 350
        dialog_height = 210
        gui_utils.center_window(self, dialog_width, dialog_height)

        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)  # Typically, small input dialogs are fixed size

        # Configure columns for expansion if it were resizable
        self.columnconfigure(1, weight=1)  # Allow entry/combobox to expand

        ttk.Label(self, text="Product:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.product_var = tk.StringVar()
        self.product_combobox = ttk.Combobox(self, textvariable=self.product_var, values=self.product_names,
                                             state="readonly")
        if self.product_names:
            self.product_var.set(self.product_names[0])
        self.product_combobox.grid(row=0, column=1, padx=10, pady=10, sticky='ew')

        ttk.Label(self, text="Custom Price:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        self.price_var = tk.StringVar()
        vcmd_price = (self.register(self.validate_price), '%P')
        self.price_entry = ttk.Entry(self, textvariable=self.price_var, validate='key', validatecommand=vcmd_price)
        self.price_entry.grid(row=1, column=1, padx=10, pady=5, sticky='ew')

        ttk.Label(self, text="Quantity:").grid(row=2, column=0, padx=10, pady=5, sticky='w')
        self.qty_var = tk.StringVar(value='1')
        vcmd_qty = (self.register(self.validate_quantity), '%P')
        self.qty_entry = ttk.Entry(self, textvariable=self.qty_var, validate='key', validatecommand=vcmd_qty, width=5)
        self.qty_entry.grid(row=2, column=1, padx=10, pady=5, sticky='w')

        self.price_entry.focus_set()

        button_frame = ttk.Frame(self)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)
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
                if P.startswith('0') and len(P) > 1 and not P.startswith('0.'):  # Prevent "07"
                    return False
                return True
            else:
                return False
        except ValueError:
            return False

    def validate_quantity(self, P):
        """Allow only positive integers for quantity."""
        if P == "": return True
        if P.isdigit() and int(P) > 0:
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
            messagebox.showerror("Invalid Quantity", "Please enter a valid positive whole number for the quantity.",
                                 parent=self)
            return

        self.result = (product_name, custom_price, quantity)
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()
