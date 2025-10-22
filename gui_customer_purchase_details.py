import tkinter as tk
from tkinter import ttk
import datetime

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
        self.rowconfigure(0, weight=0)  # Header label
        self.rowconfigure(1, weight=1)  # Treeview
        self.rowconfigure(2, weight=0)  # Close button

        # --- Header Label ---
        header_label = tk.Label(self, text=f"Purchase History for {customer_name}", font=gui_utils.HEADER_FONT)
        gui_utils.style_label(header_label)
        header_label.grid(row=0, column=0, pady=(10, 5))

        # --- Treeview for Purchase Details ---
        self.purchase_tree = ttk.Treeview(self, columns=("Date", "Product", "Qty", "Price", "Subtotal"), show="headings")
        self.purchase_tree.heading("Date", text="Date")
        self.purchase_tree.heading("Product", text="Product")
        self.purchase_tree.heading("Qty", text="Quantity")
        self.purchase_tree.heading("Price", text="Price")
        self.purchase_tree.heading("Subtotal", text="Subtotal")

        self.purchase_tree.column("Date", anchor=tk.W, width=120)
        self.purchase_tree.column("Product", anchor=tk.W, width=200)
        self.purchase_tree.column("Qty", anchor=tk.CENTER, width=60)
        self.purchase_tree.column("Price", anchor=tk.E, width=80)
        self.purchase_tree.column("Subtotal", anchor=tk.E, width=100)

        self.purchase_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # --- Scrollbar ---
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.purchase_tree.yview)
        self.purchase_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns")

        # --- Populate Treeview ---
        self._populate_purchase_data(purchase_data)

        # --- Close Button ---
        close_button = ttk.Button(self, text="Close", command=self.destroy)
        gui_utils.style_button(close_button)
        close_button.grid(row=2, column=0, pady=(5, 10))
        gui_utils.Tooltip(close_button, "Close the purchase details window.")

    def _populate_purchase_data(self, purchase_data):
        """Populates the treeview with the provided purchase data."""
        for i in self.purchase_tree.get_children():
            self.purchase_tree.delete(i)

        if not purchase_data:
            self.purchase_tree.insert("", tk.END, values=("No purchases found in this period", "", "", "", ""))
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

            self.purchase_tree.insert("", tk.END, values=(display_ts, product_name, qty, price_display, subtotal_display))
