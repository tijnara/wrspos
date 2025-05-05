import tkinter as tk
from tkinter import ttk
import datetime
import logging

# Import project utils if needed for styling or constants
import gui_utils

class CustomerPurchaseDetailWindow(tk.Toplevel):
    """
    A Toplevel window to display detailed purchase history for a customer
    within a specific date range.
    """
    def __init__(self, parent, customer_name, start_date, end_date, purchase_data):
        """
        Initializes the Customer Purchase Detail window.

        Args:
            parent: The parent window (usually the SalesHistoryWindow).
            customer_name: The name of the customer whose details are shown.
            start_date: The start date of the period (datetime.date object).
            end_date: The end date of the period (datetime.date object).
            purchase_data: A list of tuples containing the purchase details:
                           [(TimestampStr, ProductName, Qty, Price, Subtotal), ...]
        """
        super().__init__(parent)
        self.title(f"Purchase Details: {customer_name}")
        gui_utils.set_window_icon(self)

        win_width = 650
        win_height = 450
        self.geometry(f"{win_width}x{win_height}")
        self.minsize(500, 300)
        gui_utils.center_window(self, win_width, win_height)

        self.transient(parent) # Keep window on top of parent
        self.grab_set() # Direct all input to this window

        # --- Configure Layout ---
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1) # Allow treeview row to expand

        # --- Header Label ---
        date_format = "%Y-%m-%d"
        header_text = f"Purchases for {customer_name}\nFrom: {start_date.strftime(date_format)} To: {end_date.strftime(date_format)}"
        ttk.Label(self, text=header_text, justify=tk.CENTER, font=("Arial", 11)).grid(row=0, column=0, pady=10, padx=10, sticky="ew")

        # --- Details Treeview ---
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        columns = ('timestamp', 'product', 'quantity', 'price', 'subtotal')
        self.details_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")

        # Define headings
        self.details_tree.heading('timestamp', text='Date/Time')
        self.details_tree.heading('product', text='Product Name')
        self.details_tree.heading('quantity', text='Qty')
        self.details_tree.heading('price', text='Price')
        self.details_tree.heading('subtotal', text='Subtotal')

        # Define column properties
        self.details_tree.column('timestamp', anchor=tk.W, width=140, stretch=False)
        self.details_tree.column('product', anchor=tk.W, width=200, stretch=True)
        self.details_tree.column('quantity', anchor=tk.CENTER, width=40, stretch=False)
        self.details_tree.column('price', anchor=tk.E, width=80, stretch=False)
        self.details_tree.column('subtotal', anchor=tk.E, width=90, stretch=False)

        self.details_tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.details_tree.yview)
        self.details_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Populate Treeview ---
        self._populate_details(purchase_data)

        # --- Close Button ---
        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, pady=(5, 10))
        close_button = ttk.Button(button_frame, text="Close", command=self.destroy)
        close_button.pack()

        # Bind Escape key to close
        self.bind('<Escape>', lambda event=None: self.destroy())

        # Wait for the window to be closed
        self.wait_window(self)

    def _populate_details(self, purchase_data):
        """Populates the treeview with the provided purchase data."""
        for i in self.details_tree.get_children():
            self.details_tree.delete(i)

        if not purchase_data:
            self.details_tree.insert("", tk.END, values=("No purchases found in this period", "", "", "", ""))
            return

        for item in purchase_data:
            timestamp_str, product_name, qty, price, subtotal = item
            try:
                # Format timestamp nicely
                dt_obj = datetime.datetime.fromisoformat(timestamp_str)
                display_ts = dt_obj.strftime('%Y-%m-%d %H:%M') # Shorter format for this view
            except (ValueError, TypeError):
                display_ts = timestamp_str # Fallback

            price_display = f"{gui_utils.CURRENCY_SYMBOL}{price:.2f}"
            subtotal_display = f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"

            self.details_tree.insert("", tk.END, values=(display_ts, product_name, qty, price_display, subtotal_display))

