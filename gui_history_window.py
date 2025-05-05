# Import necessary libraries
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import os
import sqlite3 # Keep for error catching if needed
import csv # Added for CSV export

# --- External Libraries ---
from dateutil.relativedelta import relativedelta, MO, SU
try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None

# --- Import Project Modules ---
# Ensure all these .py files are in the SAME directory as main.py
import db_operations
import gui_utils # Import the new utils module

# --- Sales History Window Class ---
class SalesHistoryWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent # Store parent reference if needed
        self.title("Sales History & Summary")
        gui_utils.set_window_icon(self) # Use helper function

        win_width = 850
        win_height = 750 # May need adjustment for new labels
        self.geometry(f"{win_width}x{win_height}")
        self.minsize(700, 650) # Increased min height slightly
        gui_utils.center_window(self, win_width, win_height) # Use helper function
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1) # Sales list row
        self.rowconfigure(2, weight=0) # Filter row
        self.rowconfigure(3, weight=0) # Default summary row
        self.rowconfigure(4, weight=0) # Custom date entry row
        self.rowconfigure(5, weight=1) # Custom summary tree row
        self.rowconfigure(6, weight=0) # Custom total row
        self.rowconfigure(7, weight=0) # Buttons row

        # --- Widgets ---
        ttk.Label(self, text="Sales List", font=("Arial", 14, "bold")).grid(row=0, column=0, pady=10, padx=10, sticky="w")
        ttk.Label(self, text="Receipt Details", font=("Arial", 14, "bold")).grid(row=0, column=1, pady=10, padx=10, sticky="w")

        # Sales List Treeview
        list_frame = ttk.Frame(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.sales_columns_display = ("sale_num", "receipt_no", "timestamp", "customer", "total") # Store for export headers
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

        # Receipt Details Text Area
        text_frame = ttk.Frame(self)
        text_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=5)
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        self.receipt_text = tk.Text(text_frame, wrap="word", state="disabled", height=10, width=40, font=("Courier New", 9), relief="sunken", borderwidth=1)
        self.receipt_text.grid(row=0, column=0, sticky="nsew")
        receipt_text_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.receipt_text.yview)
        self.receipt_text.configure(yscrollcommand=receipt_text_scrollbar.set)
        receipt_text_scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Filter Frame (New Row 2) ---
        filter_frame = ttk.Frame(self, padding="5")
        filter_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(5,0))
        filter_frame.columnconfigure(1, weight=1) # Allow combobox to expand
        ttk.Label(filter_frame, text="Filter by Customer:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        # Populate customer list for filter
        customer_list = ["All Customers"] + sorted([c for c in db_operations.fetch_distinct_customer_names() if c != 'N/A']) #
        self.filter_customer_var = tk.StringVar(value="All Customers")
        self.filter_customer_combo = ttk.Combobox(filter_frame, textvariable=self.filter_customer_var, values=customer_list, state="readonly", width=30)
        self.filter_customer_combo.grid(row=0, column=1, padx=5, sticky="ew")
        # Add a button to apply filters
        filter_button = ttk.Button(filter_frame, text="Apply Filter", command=self.apply_filters)
        filter_button.grid(row=0, column=2, padx=(10, 0))


        # Default Summaries (Now Row 3)
        summary_frame = ttk.LabelFrame(self, text="Default Summaries", padding="5")
        summary_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        summary_frame.columnconfigure(1, weight=1) # Make right column expand

        # ***MODIFIED***: Create StringVars for dynamic date labels
        self.week_label_var = tk.StringVar(value="This Week:")
        self.month_label_var = tk.StringVar(value="This Month:")

        # ***MODIFIED***: Use StringVars for the labels
        ttk.Label(summary_frame, textvariable=self.week_label_var).grid(row=0, column=0, sticky="w", padx=5, pady=1)
        self.week_total_label = ttk.Label(summary_frame, text=f"Total: {gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 10)) #
        self.week_total_label.grid(row=0, column=1, sticky="e", padx=5, pady=1)
        self.week_items_label = ttk.Label(summary_frame, text="Items: 0", font=("Arial", 10))
        self.week_items_label.grid(row=1, column=0, sticky="w", padx=5, pady=1)
        self.week_avg_label = ttk.Label(summary_frame, text=f"Avg Sale: {gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 10)) #
        self.week_avg_label.grid(row=1, column=1, sticky="e", padx=5, pady=1)

        ttk.Label(summary_frame, textvariable=self.month_label_var).grid(row=2, column=0, sticky="w", padx=5, pady=(5,1))
        self.month_total_label = ttk.Label(summary_frame, text=f"Total: {gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 10)) #
        self.month_total_label.grid(row=2, column=1, sticky="e", padx=5, pady=(5,1))
        self.month_items_label = ttk.Label(summary_frame, text="Items: 0", font=("Arial", 10))
        self.month_items_label.grid(row=3, column=0, sticky="w", padx=5, pady=1)
        self.month_avg_label = ttk.Label(summary_frame, text=f"Avg Sale: {gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 10)) #
        self.month_avg_label.grid(row=3, column=1, sticky="e", padx=5, pady=1)


        # Custom Date Range Selection (Now Row 4)
        custom_entry_frame = ttk.LabelFrame(self, text="Custom Date Range", padding="10")
        custom_entry_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 0))
        custom_entry_frame.columnconfigure(1, weight=0)
        custom_entry_frame.columnconfigure(3, weight=0)
        custom_entry_frame.columnconfigure(4, weight=1)
        ttk.Label(custom_entry_frame, text="Start Date:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky='w')
        # DateEntry styling might be limited or require specific tkcalendar knowledge
        self.start_date_entry = DateEntry(custom_entry_frame, width=12, background='darkblue',
                                          foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.start_date_entry.grid(row=0, column=1, padx=(0, 10), pady=5)
        ttk.Label(custom_entry_frame, text="End Date:").grid(row=0, column=2, padx=(10, 5), pady=5, sticky='w')
        self.end_date_entry = DateEntry(custom_entry_frame, width=12, background='darkblue',
                                        foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.end_date_entry.grid(row=0, column=3, padx=(0, 10), pady=5)
        self.end_date_entry.set_date(datetime.date.today())
        view_range_button = ttk.Button(custom_entry_frame, text="View Detailed Summary", command=self.update_custom_summary)
        view_range_button.grid(row=0, column=4, padx=(10, 5), pady=5, sticky='e')

        # Custom Date Range Details Treeview (Now Row 5)
        custom_summary_tree_frame = ttk.LabelFrame(self, text="Custom Date Range Details", padding="5")
        custom_summary_tree_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        custom_summary_tree_frame.rowconfigure(0, weight=1)
        custom_summary_tree_frame.columnconfigure(0, weight=1)
        self.summary_columns = ('product', 'total_qty', 'total_revenue') # Store for export
        self.custom_summary_tree = ttk.Treeview(custom_summary_tree_frame, columns=self.summary_columns, show="headings", selectmode="browse") # Changed selectmode
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
        # --- Bind double-click event ---
        self.custom_summary_tree.bind("<Double-Button-1>", self.on_summary_item_select)

        # Custom Range Grand Total Label and Export Button (Now Row 6)
        custom_total_frame = ttk.Frame(self)
        custom_total_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=(0,5))
        custom_total_frame.columnconfigure(0, weight=1) # Make space for labels
        self.custom_range_items_label = ttk.Label(custom_total_frame, text="Items: 0", font=("Arial", 10))
        self.custom_range_items_label.grid(row=0, column=0, sticky="w", padx=5)
        self.custom_range_avg_label = ttk.Label(custom_total_frame, text=f"Avg Sale: {gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 10)) #
        self.custom_range_avg_label.grid(row=1, column=0, sticky="w", padx=5)
        self.custom_range_grand_total_label = ttk.Label(custom_total_frame, text=f"Total: {gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 10, "bold")) #
        self.custom_range_grand_total_label.grid(row=0, column=1, sticky="e", padx=(10,0)) # Total on right
        export_summary_button = ttk.Button(custom_total_frame, text="Export Summary", command=self.export_summary_to_csv)
        export_summary_button.grid(row=1, column=1, sticky="e", padx=(10, 0), pady=(2,0)) # Export below total


        # Action Buttons (Now Row 7)
        action_button_frame = ttk.Frame(self)
        action_button_frame.grid(row=7, column=0, columnspan=2, pady=10)
        export_sales_button = ttk.Button(action_button_frame, text="Export Sales List", command=self.export_sales_to_csv)
        export_sales_button.pack(side=tk.LEFT, padx=10)
        delete_button = ttk.Button(action_button_frame, text="Delete Selected Sale", command=self.delete_selected_sale)
        delete_button.pack(side=tk.LEFT, padx=10)
        close_button = ttk.Button(action_button_frame, text="Close", command=self.destroy)
        close_button.pack(side=tk.LEFT, padx=10)

        # Initial data population
        self.apply_filters() # Apply default filters on load

        # --- Bind Escape key ---
        self.bind('<Escape>', lambda event=None: self.destroy())


    def apply_filters(self):
        """Applies the selected customer filter and refreshes the views."""
        self.populate_sales_list()
        self.update_default_summaries()
        self.update_custom_summary() # Also update custom summary based on filter

    def populate_sales_list(self):
        """Fetches sales based on filter and populates the sales Treeview."""
        selected_customer = self.filter_customer_var.get()
        for i in self.sales_tree.get_children():
            self.sales_tree.delete(i)
        # Fetch based on selected customer
        sales_data = db_operations.fetch_sales_list_from_db(customer_name=selected_customer) #
        if sales_data:
            receipt_counter = 0
            # Display newest first by inserting at index 0
            for i, sale in enumerate(sales_data):
                receipt_counter += 1 # Increment for each sale
                sale_id, timestamp_str, total_amount, customer_name_db = sale
                try:
                    timestamp_obj = datetime.datetime.fromisoformat(timestamp_str)
                    display_ts = timestamp_obj.strftime('%a %Y-%m-%d %H:%M:%S') # Include day
                except (TypeError, ValueError):
                    display_ts = timestamp_str # Fallback to original string if format is wrong
                total_display = f"{gui_utils.CURRENCY_SYMBOL}{total_amount:.2f}" #
                # Insert at the beginning (index 0) to show newest first
                self.sales_tree.insert("", 0, values=(sale_id, receipt_counter, display_ts, customer_name_db, total_display), iid=sale_id)
        else:
            pass # No sales data found
        self.update_receipt_display("") # Clear receipt display

    def update_default_summaries(self):
        """Calculates and displays weekly and monthly sales totals based on filter."""
        selected_customer = self.filter_customer_var.get()
        today = datetime.date.today()

        # Calculate week dates (Monday to Sunday)
        start_of_week = today + relativedelta(weekday=MO(-1))
        end_of_week = start_of_week + relativedelta(days=6)

        # Calculate month dates
        start_of_month = today.replace(day=1)
        # End of month is start of next month minus one day
        end_of_month = (today.replace(day=1) + relativedelta(months=+1)) - datetime.timedelta(days=1)

        # Format dates for database query (ISO format) and display
        date_format_display = "%Y-%m-%d" # Format for display
        start_week_dt_str = datetime.datetime.combine(start_of_week, datetime.time.min).isoformat()
        # End date for query needs to be start of the *next* day
        end_week_dt_str = (datetime.datetime.combine(end_of_week, datetime.time.min) + datetime.timedelta(days=1)).isoformat()
        start_month_dt_str = datetime.datetime.combine(start_of_month, datetime.time.min).isoformat()
        end_month_dt_str = (datetime.datetime.combine(end_of_month, datetime.time.min) + datetime.timedelta(days=1)).isoformat()

        # ***MODIFIED***: Format date ranges for labels
        week_range_str = f"{start_of_week.strftime(date_format_display)} to {end_of_week.strftime(date_format_display)}"
        month_range_str = f"{start_of_month.strftime(date_format_display)} to {end_of_month.strftime(date_format_display)}"

        # Fetch stats for the week
        week_revenue, week_items, week_sales_count = db_operations.fetch_sales_stats(start_week_dt_str, end_week_dt_str, customer_name=selected_customer) #
        week_avg = week_revenue / week_sales_count if week_sales_count > 0 else 0.0

        # ***MODIFIED***: Update labels with dates and stats
        self.week_label_var.set(f"This Week ({week_range_str}):")
        self.week_total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{week_revenue:.2f}") #
        self.week_items_label.config(text=f"Items: {week_items}")
        self.week_avg_label.config(text=f"Avg Sale: {gui_utils.CURRENCY_SYMBOL}{week_avg:.2f}") #

        # Fetch stats for the month
        month_revenue, month_items, month_sales_count = db_operations.fetch_sales_stats(start_month_dt_str, end_month_dt_str, customer_name=selected_customer) #
        month_avg = month_revenue / month_sales_count if month_sales_count > 0 else 0.0

        # ***MODIFIED***: Update labels with dates and stats
        self.month_label_var.set(f"This Month ({month_range_str}):")
        self.month_total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{month_revenue:.2f}") #
        self.month_items_label.config(text=f"Items: {month_items}")
        self.month_avg_label.config(text=f"Avg Sale: {gui_utils.CURRENCY_SYMBOL}{month_avg:.2f}") #


    def update_custom_summary(self):
        """Calculates and displays detailed product summary for the selected date range and customer."""
        selected_customer = self.filter_customer_var.get()
        try:
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date()
            if start_date > end_date:
                messagebox.showwarning("Invalid Range", "Start date cannot be after end date.", parent=self)
                return

            start_date_dt_str = datetime.datetime.combine(start_date, datetime.time.min).isoformat()
            # End date for query needs to be start of the *next* day
            end_date_dt_str = (datetime.datetime.combine(end_date, datetime.time.min) + datetime.timedelta(days=1)).isoformat()

            # Fetch product summary
            summary_data = db_operations.fetch_product_summary_by_date_range(start_date_dt_str, end_date_dt_str, customer_name=selected_customer) #

            for i in self.custom_summary_tree.get_children():
                self.custom_summary_tree.delete(i)

            if summary_data:
                # Add alternating row tags if needed (similar to sale_tree, requires tags='evenrow'/'oddrow')
                for i, item_summary in enumerate(summary_data):
                    name, total_qty, total_revenue = item_summary
                    revenue_display = f"{gui_utils.CURRENCY_SYMBOL}{total_revenue:.2f}" #
                    self.custom_summary_tree.insert("", tk.END, values=(name, total_qty, revenue_display))
            else:
                 # Optionally add a placeholder if no data
                 self.custom_summary_tree.insert("", tk.END, values=("No sales in this period", "", ""))

            # Fetch overall stats for the custom range
            custom_revenue, custom_items, custom_sales_count = db_operations.fetch_sales_stats(start_date_dt_str, end_date_dt_str, customer_name=selected_customer) #
            custom_avg = custom_revenue / custom_sales_count if custom_sales_count > 0 else 0.0

            self.custom_range_grand_total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{custom_revenue:.2f}") #
            self.custom_range_items_label.config(text=f"Items: {custom_items}")
            self.custom_range_avg_label.config(text=f"Avg Sale: {gui_utils.CURRENCY_SYMBOL}{custom_avg:.2f}") #


        except Exception as e:
             messagebox.showerror("Error", f"Could not calculate custom summary: {e}", parent=self)


    def on_sale_select(self, event=None):
        """Handles selection change in the sales Treeview to display receipt."""
        selected_item_id = self.sales_tree.focus()
        if not selected_item_id:
            self.update_receipt_display("Select a sale from the list to view details.")
            return
        try:
            sale_id = int(selected_item_id) # The iid is the sale_id
            item_data = self.sales_tree.item(selected_item_id, 'values')
            if not item_data or len(item_data) < 5: # Now expecting 5 values
                 raise ValueError("Could not retrieve sale details from list.")

            # Fetch details directly from DB to ensure accuracy
            conn = sqlite3.connect(db_operations.DATABASE_FILENAME) #
            cursor = conn.cursor()
            cursor.execute("SELECT SaleTimestamp, CustomerName, TotalAmount FROM Sales WHERE SaleID = ?", (sale_id,))
            sale_data_db = cursor.fetchone()
            conn.close()
            if not sale_data_db: raise ValueError("Sale ID not found in database.")

            timestamp_str = sale_data_db[0]
            customer_name = sale_data_db[1]
            total_amount = sale_data_db[2]
            total_display = f"{gui_utils.CURRENCY_SYMBOL}{total_amount:.2f}" #

            items = db_operations.fetch_sale_items_from_db(sale_id) #
            receipt = self.generate_detailed_receipt(sale_id, timestamp_str, customer_name, total_display, items)
            self.update_receipt_display(receipt)
        except (IndexError, ValueError, TypeError, sqlite3.Error) as e:
            print(f"Error processing sale selection: {e}")
            self.update_receipt_display("Error retrieving sale details.")


    def delete_selected_sale(self):
        """Deletes the sale selected in the Treeview."""
        selected_item_id = self.sales_tree.focus()
        if not selected_item_id:
            messagebox.showwarning("No Selection", "Please select a sale from the list to delete.", parent=self)
            return
        try:
            sale_id_to_delete = int(selected_item_id) # The iid is the SaleID
            try:
                # Get details from the selected row for confirmation message
                values = self.sales_tree.item(selected_item_id, 'values')
                confirm_msg = f"Are you sure you want to permanently delete Sales # {sale_id_to_delete} ({values[2]})?" # Index 2 is timestamp now
            except (tk.TclError, IndexError):
                 # Fallback if getting item fails
                confirm_msg = f"Are you sure you want to permanently delete Sales # {sale_id_to_delete}?"

            confirmed = messagebox.askyesno("Confirm Deletion", confirm_msg, parent=self)
            if confirmed:
                if db_operations.delete_sale_from_db(sale_id_to_delete): #
                    messagebox.showinfo("Success", f"Sales # {sale_id_to_delete} deleted successfully.", parent=self)
                    self.apply_filters() # Refresh lists after delete
                else:
                    # db_operations likely showed an error, but show one here too
                    messagebox.showerror("Error", f"Failed to delete Sales # {sale_id_to_delete}.", parent=self)
        except (ValueError, IndexError, TypeError) as e:
             messagebox.showerror("Error", f"Could not determine selected sale ID: {e}", parent=self)


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
                price_str = f"{gui_utils.CURRENCY_SYMBOL}{price:.2f}" #
                subtotal_str = f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}" #
                # Truncate name if too long
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
        if not self.sales_tree.get_children():
            messagebox.showwarning("No Data", "There is no sales data to export.", parent=self)
            return

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Sales History As",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path: return # User cancelled

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Get headers from treeview columns
                headers = [self.sales_tree.heading(col)['text'] for col in self.sales_columns_display]
                writer.writerow(headers)
                # Iterate in display order (newest first as inserted)
                for item_id in self.sales_tree.get_children():
                    row_values = self.sales_tree.item(item_id)['values']
                    writer.writerow(row_values)

            messagebox.showinfo("Export Successful", f"Sales history exported successfully to:\n{file_path}", parent=self)
            print(f"Sales history exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export sales history.\nError: {e}", parent=self)
            print(f"Error exporting sales history: {e}")

    def export_summary_to_csv(self):
        """Exports the currently displayed custom summary data to a CSV file."""
        if not self.custom_summary_tree.get_children():
            messagebox.showwarning("No Data", "There is no summary data to export.", parent=self)
            return
        # Check if only the 'No sales' placeholder is present
        first_item_values = self.custom_summary_tree.item(self.custom_summary_tree.get_children()[0])['values']
        if first_item_values and first_item_values[0] == "No sales in this period":
             messagebox.showwarning("No Data", "There is no summary data to export.", parent=self)
             return

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Product Summary As",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path: return # User cancelled

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                headers = [self.custom_summary_tree.heading(col)['text'] for col in self.summary_columns]
                writer.writerow(headers)
                # Iterate through items in the summary tree
                for item_id in self.custom_summary_tree.get_children():
                    row_values = self.custom_summary_tree.item(item_id)['values']
                    writer.writerow(row_values)

            messagebox.showinfo("Export Successful", f"Product summary exported successfully to:\n{file_path}", parent=self)
            print(f"Product summary exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export product summary.\nError: {e}", parent=self)
            print(f"Error exporting product summary: {e}")

    def on_summary_item_select(self, event=None):
        """Displays details of the selected item in the custom summary treeview."""
        selected_item_id = self.custom_summary_tree.focus()
        if not selected_item_id:
            return # No item selected

        item_values = self.custom_summary_tree.item(selected_item_id)['values']

        # Check if it's the 'No sales' placeholder
        if not item_values or item_values[0] == "No sales in this period":
            return

        try:
            product_name = item_values[0]
            total_qty = item_values[1]
            total_revenue_str = item_values[2]
            message = (
                f"Product: {product_name}\n"
                f"Total Quantity Sold: {total_qty}\n"
                f"Total Revenue: {total_revenue_str}"
            )
            # Show details in a simple messagebox
            messagebox.showinfo("Product Summary Detail", message, parent=self)
        except IndexError:
            messagebox.showerror("Error", "Could not retrieve details for the selected summary item.", parent=self)

# # Note: The __main__ block below is for isolated testing and might need adjustments
# # depending on how db_operations and gui_utils are structured if run standalone.
# # It's generally best to run the application via main.py.
# if __name__ == '__main__':
#     root = tk.Tk()
#     # Dummy db_operations and gui_utils might be needed here for testing
#     # (As shown in the previous attempt's output)
#     # ... (dummy class definitions would go here) ...

#     if DateEntry is None:
#        print("tkcalendar not installed, date entry widgets will be disabled.")

#     # Initialize dummy db if needed
#     # ...

#     app = SalesHistoryWindow(root)
#     root.mainloop()