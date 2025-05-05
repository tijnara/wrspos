import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog # Added for file dialogs
import datetime
import os
import sqlite3 # Keep for error catching if needed
import csv # Added for CSV export
import logging # Added logging

# --- External Libraries ---
from dateutil.relativedelta import relativedelta, MO, SU
try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None
    logging.warning("tkcalendar not found, date entry disabled in history window.")

# --- Import Project Modules ---
import db_operations
import gui_utils # Import the new utils module
# --- REMOVED: Import of CustomerPurchaseDetailWindow ---
# from gui_customer_purchase_details import CustomerPurchaseDetailWindow

# --- Sales History Window Class ---
class SalesHistoryWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent # Store parent reference if needed
        self.title("Sales History & Summary")
        gui_utils.set_window_icon(self) # Use helper function

        # Check if DateEntry widget is available (needed for custom range)
        if DateEntry is None:
             messagebox.showerror("Missing Library",
                                  "Required library 'tkcalendar' is not installed.\n"
                                  "Custom date range selection will be disabled.\n"
                                  "Please install it using:\npip install tkcalendar",
                                  parent=self.parent)

        win_width = 850
        # Adjusted height back as Customer Summary section is removed
        win_height = 750
        self.geometry(f"{win_width}x{win_height}")
        self.minsize(700, 600) # Adjusted min height
        gui_utils.center_window(self, win_width, win_height) # Center the window

        # --- Configure Grid Layout ---
        self.columnconfigure(0, weight=2) # Sales List column
        self.columnconfigure(1, weight=1) # Receipt Details column
        self.rowconfigure(1, weight=1) # Sales list row
        self.rowconfigure(2, weight=0) # Filter row
        self.rowconfigure(3, weight=0) # Default summary row
        self.rowconfigure(4, weight=0) # Custom date entry row
        self.rowconfigure(5, weight=1) # Custom product summary tree row
        self.rowconfigure(6, weight=0) # Custom product total row
        # --- REMOVED Customer Summary Rows ---
        # self.rowconfigure(7, weight=1) # Customer summary tree row
        # self.rowconfigure(8, weight=0) # Customer summary export button row
        # --- Adjusted Action Buttons Row ---
        self.rowconfigure(7, weight=0) # Action Buttons row (was 9)


        # --- Widgets ---
        self._setup_labels()
        self._setup_sales_list_tree()
        self._setup_receipt_display()
        self._setup_filter_controls()
        self._setup_default_summaries()
        self._setup_custom_date_entry()
        self._setup_product_summary_tree()
        self._setup_product_summary_totals()
        # --- REMOVED Calls to setup customer summary ---
        # self._setup_customer_summary_tree()
        # self._setup_customer_summary_export()
        self._setup_action_buttons() # Adjusted row


        # Initial data population
        self.apply_filters() # Apply default filters on load

        # --- Bind Escape key ---
        self.bind('<Escape>', lambda event=None: self.destroy())

        # Make window modal after all setup
        self.transient(parent) # Keep on top of parent
        self.grab_set() # Direct input here


    # --- UI Setup Methods ---

    def _setup_labels(self):
        ttk.Label(self, text="Sales List", font=("Arial", 14, "bold")).grid(row=0, column=0, pady=10, padx=10, sticky="w")
        ttk.Label(self, text="Receipt Details", font=("Arial", 14, "bold")).grid(row=0, column=1, pady=10, padx=10, sticky="w")

    def _setup_sales_list_tree(self):
        list_frame = ttk.Frame(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.sales_columns_display = ("sale_num", "receipt_no", "timestamp", "customer", "total")
        self.sales_tree = ttk.Treeview(list_frame, columns=self.sales_columns_display, show="headings", selectmode="browse")
        self.sales_tree.heading("sale_num", text="Sales #")
        self.sales_tree.heading("receipt_no", text="Receipt No.")
        self.sales_tree.heading("timestamp", text="Timestamp")
        self.sales_tree.heading("customer", text="Customer")
        self.sales_tree.heading("total", text="Total")
        self.sales_tree.column("sale_num", anchor=tk.W, width=60, stretch=False)
        self.sales_tree.column("receipt_no", anchor=tk.W, width=80, stretch=False)
        self.sales_tree.column("timestamp", anchor=tk.W, width=190, stretch=False)
        self.sales_tree.column("customer", anchor=tk.W, width=120, stretch=True)
        self.sales_tree.column("total", anchor=tk.E, width=80, stretch=False)
        self.sales_tree.grid(row=0, column=0, sticky="nsew")
        sales_list_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.sales_tree.yview)
        self.sales_tree.configure(yscrollcommand=sales_list_scrollbar.set)
        sales_list_scrollbar.grid(row=0, column=1, sticky="ns")
        self.sales_tree.bind("<<TreeviewSelect>>", self.on_sale_select)

    def _setup_receipt_display(self):
        text_frame = ttk.Frame(self)
        text_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=5)
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        self.receipt_text = tk.Text(text_frame, wrap="word", state="disabled", height=10, width=40, font=("Courier New", 9), relief="sunken", borderwidth=1)
        self.receipt_text.grid(row=0, column=0, sticky="nsew")
        receipt_text_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.receipt_text.yview)
        self.receipt_text.configure(yscrollcommand=receipt_text_scrollbar.set)
        receipt_text_scrollbar.grid(row=0, column=1, sticky="ns")

    def _setup_filter_controls(self):
        filter_frame = ttk.Frame(self, padding="5")
        filter_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(5,0))
        filter_frame.columnconfigure(1, weight=1)
        ttk.Label(filter_frame, text="Filter by Customer:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        customer_list = ["All Customers"] + sorted([c for c in db_operations.fetch_distinct_customer_names() if c != 'N/A'])
        self.filter_customer_var = tk.StringVar(value="All Customers")
        self.filter_customer_combo = ttk.Combobox(filter_frame, textvariable=self.filter_customer_var, values=customer_list, state="readonly", width=30)
        self.filter_customer_combo.grid(row=0, column=1, padx=5, sticky="ew")
        filter_button = ttk.Button(filter_frame, text="Apply Filter", command=self.apply_filters)
        filter_button.grid(row=0, column=2, padx=(10, 0))

    def _setup_default_summaries(self):
        """Sets up the section for the default weekly summary, including item breakdown."""
        summary_frame = ttk.LabelFrame(self, text="Default Summary", padding="10")
        summary_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=(10, 5))
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.rowconfigure(0, weight=1)

        week_frame = ttk.Frame(summary_frame)
        week_frame.grid(row=0, column=0, sticky="nsew")
        week_frame.columnconfigure(0, weight=1)
        week_frame.rowconfigure(1, weight=1)

        self.week_label_var = tk.StringVar(value="This Week:")
        ttk.Label(week_frame, textvariable=self.week_label_var, font=("Arial", 11, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=(0,2))
        self.week_total_label = ttk.Label(week_frame, text=f"Total Sales: {gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 10))
        self.week_total_label.grid(row=0, column=1, sticky="e", padx=5, pady=(0,2))

        self.week_items_tree = ttk.Treeview(week_frame, columns=('product', 'qty'), show='headings', height=5)
        self.week_items_tree.heading('product', text='Product')
        self.week_items_tree.heading('qty', text='Qty Sold')
        self.week_items_tree.column('product', anchor=tk.W, width=250, stretch=True)
        self.week_items_tree.column('qty', anchor=tk.CENTER, width=60, stretch=False)
        week_scroll = ttk.Scrollbar(week_frame, orient="vertical", command=self.week_items_tree.yview)
        self.week_items_tree.configure(yscrollcommand=week_scroll.set)

        self.week_items_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=(2,0))
        week_scroll.grid(row=1, column=2, sticky="ns", pady=(2,0))

    def _setup_custom_date_entry(self):
        """Sets up the custom date range selection using DateEntry widgets."""
        custom_entry_frame = ttk.LabelFrame(self, text="Custom Date Range", padding="10")
        custom_entry_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 0))
        custom_entry_frame.columnconfigure(1, weight=0)
        custom_entry_frame.columnconfigure(3, weight=0)
        custom_entry_frame.columnconfigure(4, weight=1)

        ttk.Label(custom_entry_frame, text="Start Date:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky='w')
        if DateEntry:
            self.start_date_entry = DateEntry(custom_entry_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
            self.start_date_entry.grid(row=0, column=1, padx=(0, 10), pady=5)
        else:
            self.start_date_entry = ttk.Entry(custom_entry_frame, width=12, state='disabled')
            self.start_date_entry.grid(row=0, column=1, padx=(0, 10), pady=5)
            ttk.Label(custom_entry_frame, text="(tkcalendar needed)").grid(row=1, column=1)


        ttk.Label(custom_entry_frame, text="End Date:").grid(row=0, column=2, padx=(10, 5), pady=5, sticky='w')
        if DateEntry:
            self.end_date_entry = DateEntry(custom_entry_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
            self.end_date_entry.grid(row=0, column=3, padx=(0, 10), pady=5)
            self.end_date_entry.set_date(datetime.date.today())
        else:
            self.end_date_entry = ttk.Entry(custom_entry_frame, width=12, state='disabled')
            self.end_date_entry.grid(row=0, column=3, padx=(0, 10), pady=5)
            ttk.Label(custom_entry_frame, text="(tkcalendar needed)").grid(row=1, column=3)

        view_range_button_state = tk.NORMAL if DateEntry else tk.DISABLED
        view_range_button = ttk.Button(custom_entry_frame, text="View Detailed Summary",
                                       command=self.update_custom_summaries,
                                       state=view_range_button_state)
        view_range_button.grid(row=0, column=4, padx=(10, 5), pady=5, sticky='e')


    def _setup_product_summary_tree(self):
        custom_summary_tree_frame = ttk.LabelFrame(self, text="Product Summary (Custom Date Range)", padding="5")
        custom_summary_tree_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        custom_summary_tree_frame.rowconfigure(0, weight=1)
        custom_summary_tree_frame.columnconfigure(0, weight=1)
        self.summary_columns = ('product', 'total_qty', 'total_revenue')
        self.custom_summary_tree = ttk.Treeview(custom_summary_tree_frame, columns=self.summary_columns, show="headings", selectmode="browse")
        self.custom_summary_tree.heading('product', text='Product')
        self.custom_summary_tree.heading('total_qty', text='Total Qty Sold')
        self.custom_summary_tree.heading('total_revenue', text='Total Revenue')
        self.custom_summary_tree.column('product', anchor=tk.W, width=200, stretch=True)
        self.custom_summary_tree.column('total_qty', anchor=tk.CENTER, width=100, stretch=False)
        self.custom_summary_tree.column('total_revenue', anchor=tk.E, width=120, stretch=False)
        self.custom_summary_tree.grid(row=0, column=0, sticky='nsew')
        summary_scrollbar = ttk.Scrollbar(custom_summary_tree_frame, orient="vertical", command=self.custom_summary_tree.yview)
        self.custom_summary_tree.configure(yscrollcommand=summary_scrollbar.set)
        summary_scrollbar.grid(row=0, column=1, sticky='ns')
        self.custom_summary_tree.bind("<Double-Button-1>", self.on_summary_item_select)

    def _setup_product_summary_totals(self):
        custom_total_frame = ttk.Frame(self)
        custom_total_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=(0,5))
        custom_total_frame.columnconfigure(0, weight=1)
        custom_total_frame.columnconfigure(1, weight=1)

        self.custom_range_items_label = ttk.Label(custom_total_frame, text="Items: 0", font=("Arial", 10))
        self.custom_range_items_label.grid(row=0, column=0, sticky="w", padx=5)

        self.custom_range_grand_total_label = ttk.Label(custom_total_frame, text=f"Total: {gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 10, "bold"))
        self.custom_range_grand_total_label.grid(row=0, column=1, sticky="e", padx=(10,0))
        export_summary_button = ttk.Button(custom_total_frame, text="Export Product Summary", command=self.export_summary_to_csv)
        export_summary_button.grid(row=1, column=1, sticky="e", padx=(10, 0), pady=(2,0))

    # --- REMOVED: Customer Summary UI Setup ---
    # def _setup_customer_summary_tree(self): ...
    # def _setup_customer_summary_export(self): ...

    def _setup_action_buttons(self):
        # --- Adjusted Row ---
        action_button_frame = ttk.Frame(self)
        action_button_frame.grid(row=7, column=0, columnspan=2, pady=10) # Changed row to 7
        export_sales_button = ttk.Button(action_button_frame, text="Export Sales List", command=self.export_sales_to_csv)
        delete_button = ttk.Button(action_button_frame, text="Delete Selected Sale", command=self.delete_selected_sale)
        close_button = ttk.Button(action_button_frame, text="Close", command=self.destroy)
        export_sales_button.pack(side=tk.LEFT, padx=10)
        delete_button.pack(side=tk.LEFT, padx=10)
        close_button.pack(side=tk.LEFT, padx=10)

    # --- Logic Methods ---

    def apply_filters(self):
        """Applies the selected customer filter and refreshes the views."""
        logging.info(f"Applying filters. Selected customer: {self.filter_customer_var.get()}")
        self.populate_sales_list()
        self.update_default_summaries()
        self.update_custom_summaries()

    def populate_sales_list(self):
        """Fetches sales based on filter and populates the sales Treeview."""
        selected_customer = self.filter_customer_var.get()
        logging.debug(f"Populating sales list for customer: {selected_customer}")
        for i in self.sales_tree.get_children(): self.sales_tree.delete(i)
        sales_data = db_operations.fetch_sales_list_from_db(customer_name=selected_customer)
        if sales_data:
            receipt_counter = 0
            for sale in sales_data:
                receipt_counter += 1
                sale_id, timestamp_str, total_amount, customer_name_db = sale
                try: display_ts = datetime.datetime.fromisoformat(timestamp_str).strftime('%a %Y-%m-%d %H:%M:%S')
                except (TypeError, ValueError): display_ts = timestamp_str
                total_display = f"{gui_utils.CURRENCY_SYMBOL}{total_amount:.2f}"
                self.sales_tree.insert("", 0, values=(sale_id, receipt_counter, display_ts, customer_name_db, total_display), iid=sale_id)
        self.update_receipt_display("")

    def update_default_summaries(self):
        """Calculates and displays weekly sales total and item breakdown."""
        selected_customer = self.filter_customer_var.get() # Filter applies here
        logging.debug(f"Updating default summaries for customer: {selected_customer}")
        today = datetime.date.today()
        start_of_week = today + relativedelta(weekday=MO(-1))
        end_of_week = start_of_week + relativedelta(days=6)
        date_format_display = "%Y-%m-%d"
        start_week_dt_str = datetime.datetime.combine(start_of_week, datetime.time.min).isoformat()
        end_week_dt_str = (datetime.datetime.combine(end_of_week, datetime.time.min) + datetime.timedelta(days=1)).isoformat()
        week_range_str = f"{start_of_week.strftime(date_format_display)} to {end_of_week.strftime(date_format_display)}"

        week_revenue, _, _ = db_operations.fetch_sales_stats(start_week_dt_str, end_week_dt_str, customer_name=selected_customer)

        self.week_label_var.set(f"This Week ({week_range_str}):")
        self.week_total_label.config(text=f"Total Sales: {gui_utils.CURRENCY_SYMBOL}{week_revenue:.2f}")

        week_item_data = db_operations.fetch_product_summary_by_date_range(start_week_dt_str, end_week_dt_str, customer_name=selected_customer)
        self._populate_default_summary_tree(self.week_items_tree, week_item_data)

        logging.debug("Default summaries updated.")

    def _populate_default_summary_tree(self, treeview, item_data):
        """Clears and populates a default summary treeview (week or month)."""
        for i in treeview.get_children():
            treeview.delete(i)

        if item_data:
            for product_name, total_qty, _ in item_data: # Ignore total revenue here
                treeview.insert("", tk.END, values=(product_name, total_qty))
        else:
            treeview.insert("", tk.END, values=("No items sold", ""))


    def update_custom_summaries(self):
        """Updates the product custom summary based on date range from DateEntry."""
        if DateEntry is None:
            logging.warning("Attempted update_custom_summaries but DateEntry not available.")
            return

        logging.debug("Updating custom date range summaries...")
        try:
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date()

            if start_date is None or end_date is None:
                 messagebox.showwarning("Date Error", "Could not retrieve dates.", parent=self)
                 return
            if start_date > end_date:
                messagebox.showwarning("Invalid Range", "Start date cannot be after end date.", parent=self)
                return

            start_date_dt_str = datetime.datetime.combine(start_date, datetime.time.min).isoformat()
            end_date_dt_str = (datetime.datetime.combine(end_date, datetime.time.min) + datetime.timedelta(days=1)).isoformat()

            self._update_product_summary_display(start_date_dt_str, end_date_dt_str)
            # --- REMOVED Call to update customer summary ---
            # self._update_customer_summary_display(start_date_dt_str, end_date_dt_str)

        except Exception as e:
             logging.exception("Error calculating custom summaries.")
             messagebox.showerror("Error", f"Could not calculate custom summary: {e}", parent=self)

    def _update_product_summary_display(self, start_dt_str, end_dt_str):
        """Updates the product summary treeview for the given date range."""
        logging.debug(f"Updating product summary display for {start_dt_str} to {end_dt_str}")
        summary_data = db_operations.fetch_product_summary_by_date_range(start_dt_str, end_dt_str, customer_name=None)

        for i in self.custom_summary_tree.get_children(): self.custom_summary_tree.delete(i)

        if summary_data:
            for item_summary in summary_data:
                name, total_qty, total_revenue = item_summary
                revenue_display = f"{gui_utils.CURRENCY_SYMBOL}{total_revenue:.2f}"
                self.custom_summary_tree.insert("", tk.END, values=(name, total_qty, revenue_display))
        else:
             self.custom_summary_tree.insert("", tk.END, values=("No product sales in this period", "", ""))

        custom_revenue, custom_items, custom_sales_count = db_operations.fetch_sales_stats(start_dt_str, end_dt_str, customer_name=None)

        self.custom_range_grand_total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{custom_revenue:.2f}")
        self.custom_range_items_label.config(text=f"Items: {custom_items}")
        logging.debug("Product summary display updated.")

    # --- REMOVED: Customer Summary Update Logic ---
    # def _update_customer_summary_display(self, start_dt_str, end_dt_str): ...


    def on_sale_select(self, event=None):
        """Handles selection change in the sales Treeview to display receipt."""
        selected_item_id = self.sales_tree.focus()
        if not selected_item_id:
            self.update_receipt_display("Select a sale from the list to view details.")
            return
        try:
            sale_id = int(selected_item_id)
            logging.debug(f"Sale selected: ID={sale_id}")
            conn = sqlite3.connect(db_operations.DATABASE_FILENAME)
            cursor = conn.cursor()
            cursor.execute("SELECT SaleTimestamp, CustomerName, TotalAmount FROM Sales WHERE SaleID = ?", (sale_id,))
            sale_data_db = cursor.fetchone()
            conn.close()
            if not sale_data_db: raise ValueError("Sale ID not found in database.")

            timestamp_str, customer_name, total_amount = sale_data_db
            total_display = f"{gui_utils.CURRENCY_SYMBOL}{total_amount:.2f}"
            items = db_operations.fetch_sale_items_from_db(sale_id)
            receipt = self.generate_detailed_receipt(sale_id, timestamp_str, customer_name, total_display, items)
            self.update_receipt_display(receipt)
        except (ValueError, TypeError, sqlite3.Error) as e:
            logging.exception(f"Error processing sale selection for ID '{selected_item_id}'.")
            self.update_receipt_display("Error retrieving sale details.")


    def delete_selected_sale(self):
        """Deletes the sale selected in the Treeview."""
        selected_item_id = self.sales_tree.focus()
        if not selected_item_id:
            messagebox.showwarning("No Selection", "Please select a sale to delete.", parent=self)
            return
        try:
            sale_id_to_delete = int(selected_item_id)
            values = self.sales_tree.item(selected_item_id, 'values')
            confirm_msg = f"Delete Sales # {sale_id_to_delete} ({values[2]}) permanently?"
        except (ValueError, IndexError, tk.TclError):
            confirm_msg = f"Delete Sales # {selected_item_id} permanently?" # Fallback

        logging.warning(f"Confirmation requested for deleting Sale ID: {selected_item_id}")
        confirmed = messagebox.askyesno("Confirm Deletion", confirm_msg, parent=self)
        if confirmed:
            logging.warning(f"Attempting deletion of Sale ID: {sale_id_to_delete}")
            if db_operations.delete_sale_from_db(sale_id_to_delete):
                logging.info(f"Sale ID {sale_id_to_delete} deleted successfully.")
                messagebox.showinfo("Success", f"Sales # {sale_id_to_delete} deleted.", parent=self)
                self.apply_filters() # Refresh lists
            else:
                logging.error(f"Failed to delete Sale ID {sale_id_to_delete} via db_operations.")
                messagebox.showerror("Error", f"Failed to delete Sales # {sale_id_to_delete}.", parent=self)
        else:
            logging.info(f"Deletion of Sale ID {selected_item_id} cancelled by user.")


    def update_receipt_display(self, text_content):
        """Updates the content of the receipt Text widget."""
        self.receipt_text.config(state="normal")
        self.receipt_text.delete(1.0, tk.END)
        self.receipt_text.insert(tk.END, text_content)
        self.receipt_text.config(state="disabled")

    def generate_detailed_receipt(self, sale_id, timestamp_str, customer_name, total_display, items):
        """Generates receipt text from fetched data."""
        receipt = f"--- SEASIDE Water Refilling Station ---\n"
        receipt += f"Sales #: {sale_id}\n"
        try:
            timestamp_obj = datetime.datetime.fromisoformat(timestamp_str)
            receipt += f"Date: {timestamp_obj.strftime('%a %Y-%m-%d %H:%M:%S')}\n"
        except (TypeError, ValueError):
            receipt += f"Date: {timestamp_str}\n" # Fallback
        receipt += f"Customer: {customer_name}\n"
        receipt += "--------------------------------------\n"
        receipt += "{:<18} {:>3} {:>7} {:>8}\n".format("Item", "Qty", "Price", "Subtotal")
        receipt += "--------------------------------------\n"
        if items:
            for item_details in items:
                name, qty, price, subtotal = item_details
                price_str = f"{gui_utils.CURRENCY_SYMBOL}{price:.2f}"
                subtotal_str = f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"
                receipt += "{:<18} {:>3d} {:>7} {:>8}\n".format(name[:18], qty, price_str, subtotal_str)
        else:
            receipt += " (No item details found)\n"
        receipt += "======================================\n"
        receipt += "{:<29} {:>8}\n".format("TOTAL:", total_display)
        receipt += "--------------------------------------\n"
        receipt += "        Thank you!\n"
        return receipt

    def export_sales_to_csv(self):
        """Exports the currently displayed sales list to a CSV file."""
        logging.info("Exporting sales list to CSV.")
        if not self.sales_tree.get_children():
            messagebox.showwarning("No Data", "No sales data to export.", parent=self)
            return
        file_path = filedialog.asksaveasfilename(parent=self, title="Save Sales History As", defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not file_path: logging.info("Sales list export cancelled."); return
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                headers = [self.sales_tree.heading(col)['text'] for col in self.sales_columns_display]
                writer.writerow(headers)
                for item_id in self.sales_tree.get_children():
                    writer.writerow(self.sales_tree.item(item_id)['values'])
            logging.info(f"Sales list exported successfully to {file_path}")
            messagebox.showinfo("Export Successful", f"Sales history exported to:\n{file_path}", parent=self)
        except Exception as e:
            logging.exception(f"Error exporting sales list to CSV: {file_path}")
            messagebox.showerror("Export Failed", f"Could not export sales history.\nError: {e}", parent=self)

    def export_summary_to_csv(self):
        """Exports the currently displayed product summary data to a CSV file."""
        logging.info("Exporting product summary to CSV.")
        if not self.custom_summary_tree.get_children():
            messagebox.showwarning("No Data", "No product summary data to export.", parent=self)
            return
        first_item_values = self.custom_summary_tree.item(self.custom_summary_tree.get_children()[0])['values']
        if first_item_values and first_item_values[0] == "No product sales in this period":
             messagebox.showwarning("No Data", "No product summary data to export.", parent=self)
             return
        file_path = filedialog.asksaveasfilename(parent=self, title="Save Product Summary As", defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not file_path: logging.info("Product summary export cancelled."); return
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                headers = [self.custom_summary_tree.heading(col)['text'] for col in self.summary_columns]
                writer.writerow(headers)
                for item_id in self.custom_summary_tree.get_children():
                    writer.writerow(self.custom_summary_tree.item(item_id)['values'])
            logging.info(f"Product summary exported successfully to {file_path}")
            messagebox.showinfo("Export Successful", f"Product summary exported to:\n{file_path}", parent=self)
        except Exception as e:
            logging.exception(f"Error exporting product summary to CSV: {file_path}")
            messagebox.showerror("Export Failed", f"Could not export product summary.\nError: {e}", parent=self)

    # --- REMOVED: export_customer_summary_to_csv ---

    def on_summary_item_select(self, event=None):
        """Displays details of the selected item in the product summary treeview."""
        selected_item_id = self.custom_summary_tree.focus()
        if not selected_item_id: return
        item_values = self.custom_summary_tree.item(selected_item_id)['values']
        if not item_values or item_values[0] == "No product sales in this period": return
        try:
            product_name, total_qty, total_revenue_str = item_values
            message = (f"Product: {product_name}\n"
                       f"Total Quantity Sold: {total_qty}\n"
                       f"Total Revenue: {total_revenue_str}")
            logging.debug(f"Displaying product summary detail: {product_name}")
            messagebox.showinfo("Product Summary Detail", message, parent=self)
        except IndexError:
            logging.error("IndexError retrieving details for selected product summary item.")
            messagebox.showerror("Error", "Could not retrieve details for the selected summary item.", parent=self)

    # --- REMOVED: on_cust_summary_double_click ---

