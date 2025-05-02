import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog # Added for file dialogs
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
import db_operations
import gui_utils # Import the new utils module

# --- Sales History Window Class ---
class SalesHistoryWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Sales History & Summary")
        gui_utils.set_window_icon(self) # Use helper function

        win_width = 850
        win_height = 750
        self.geometry(f"{win_width}x{win_height}")
        self.minsize(700, 600)
        gui_utils.center_window(self, win_width, win_height) # Use helper function
        self.columnconfigure(0, weight=2) # Give more weight to the left side (sales list)
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
        # --- Adjusted Column Widths ---
        self.sales_tree.column("sale_num", anchor=tk.W, width=60, stretch=False)
        self.sales_tree.column("receipt_no", anchor=tk.W, width=70, stretch=False) # Slightly smaller
        self.sales_tree.column("timestamp", anchor=tk.W, width=160, stretch=False) # Reduced width
        self.sales_tree.column("customer", anchor=tk.W, width=100, stretch=True) # Allow stretch, but start smaller
        self.sales_tree.column("total", anchor=tk.E, width=70, stretch=False) # Slightly smaller
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
        self.receipt_text = tk.Text(text_frame, wrap="word", state="disabled", height=10, width=40, font=("Courier New", 9))
        self.receipt_text.grid(row=0, column=0, sticky="nsew")
        receipt_text_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.receipt_text.yview)
        self.receipt_text.configure(yscrollcommand=receipt_text_scrollbar.set)
        receipt_text_scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Filter Frame (Row 2) ---
        filter_frame = ttk.Frame(self, padding="5")
        filter_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(5,0))
        filter_frame.columnconfigure(1, weight=1) # Allow combobox to expand
        ttk.Label(filter_frame, text="Filter by Customer:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        # Populate customer list for filter
        customer_list = ["All Customers"] + sorted([c for c in db_operations.fetch_distinct_customer_names() if c != 'N/A'])
        self.filter_customer_var = tk.StringVar(value="All Customers")
        self.filter_customer_combo = ttk.Combobox(filter_frame, textvariable=self.filter_customer_var, values=customer_list, state="readonly", width=30)
        self.filter_customer_combo.grid(row=0, column=1, padx=5, sticky="ew")
        # Add a button to apply filters
        filter_button = ttk.Button(filter_frame, text="Apply Filter", command=self.apply_filters)
        filter_button.grid(row=0, column=2, padx=(10, 0))


        # Default Summaries (Now Row 3)
        summary_frame = ttk.LabelFrame(self, text="Default Summaries", padding="5")
        summary_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        summary_frame.columnconfigure(1, weight=1)
        ttk.Label(summary_frame, text="This Week (Mon-Sun):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.week_total_label = ttk.Label(summary_frame, text=f"{gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 10, "bold"))
        self.week_total_label.grid(row=0, column=1, sticky="e", padx=5, pady=2)
        ttk.Label(summary_frame, text="This Month:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.month_total_label = ttk.Label(summary_frame, text=f"{gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 10, "bold"))
        self.month_total_label.grid(row=1, column=1, sticky="e", padx=5, pady=2)

        # Custom Date Range Selection (Now Row 4)
        custom_entry_frame = ttk.LabelFrame(self, text="Custom Date Range", padding="10")
        custom_entry_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 0))
        custom_entry_frame.columnconfigure(1, weight=0)
        custom_entry_frame.columnconfigure(3, weight=0)
        custom_entry_frame.columnconfigure(4, weight=1)
        ttk.Label(custom_entry_frame, text="Start Date:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky='w')
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
        self.custom_summary_tree = ttk.Treeview(custom_summary_tree_frame, columns=self.summary_columns, show="headings", selectmode="none")
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

        # Custom Range Grand Total Label and Export Button (Now Row 6)
        custom_total_frame = ttk.Frame(self)
        custom_total_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=(0,5))
        custom_total_frame.columnconfigure(0, weight=1) # Make space for label
        self.custom_range_grand_total_label = ttk.Label(custom_total_frame, text=f"Selected Range Total: {gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 10, "bold"))
        self.custom_range_grand_total_label.grid(row=0, column=0, sticky="e")
        export_summary_button = ttk.Button(custom_total_frame, text="Export Summary", command=self.export_summary_to_csv)
        export_summary_button.grid(row=0, column=1, sticky="e", padx=(10, 0))

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
        sales_data = db_operations.fetch_sales_list_from_db(customer_name=selected_customer)
        if sales_data:
            receipt_counter = 0
            for sale in sales_data:
                receipt_counter += 1 # Increment for each sale
                sale_id, timestamp_str, total_amount, customer_name_db = sale
                try:
                    timestamp_obj = datetime.datetime.fromisoformat(timestamp_str)
                    display_ts = timestamp_obj.strftime('%a %Y-%m-%d %H:%M:%S') # Include day
                except (TypeError, ValueError):
                    display_ts = timestamp_str
                total_display = f"{gui_utils.CURRENCY_SYMBOL}{total_amount:.2f}"
                # --- Insert values in the new order (sale_id first, then receipt_counter) ---
                self.sales_tree.insert("", 0, values=(sale_id, receipt_counter, display_ts, customer_name_db, total_display), iid=sale_id)
        else:
            pass
        self.update_receipt_display("")

    def update_default_summaries(self):
        """Calculates and displays weekly and monthly sales totals based on filter."""
        selected_customer = self.filter_customer_var.get()
        today = datetime.date.today()
        start_of_week = today + relativedelta(weekday=MO(-1))
        end_of_week = start_of_week + relativedelta(days=6)
        start_of_month = today.replace(day=1)
        end_of_month = today.replace(day=1) + relativedelta(months=+1) - datetime.timedelta(days=1)
        start_week_dt_str = datetime.datetime.combine(start_of_week, datetime.time.min).isoformat()
        end_week_dt_str = (datetime.datetime.combine(end_of_week, datetime.time.min) + datetime.timedelta(days=1)).isoformat()
        start_month_dt_str = datetime.datetime.combine(start_of_month, datetime.time.min).isoformat()
        end_month_dt_str = (datetime.datetime.combine(end_of_month, datetime.time.min) + datetime.timedelta(days=1)).isoformat()
        # Pass customer filter to summary functions
        weekly_total = db_operations.fetch_sales_summary(start_week_dt_str, end_week_dt_str, customer_name=selected_customer)
        monthly_total = db_operations.fetch_sales_summary(start_month_dt_str, end_month_dt_str, customer_name=selected_customer)
        self.week_total_label.config(text=f"{gui_utils.CURRENCY_SYMBOL}{weekly_total:.2f}")
        self.month_total_label.config(text=f"{gui_utils.CURRENCY_SYMBOL}{monthly_total:.2f}")

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
            end_date_dt_str = (datetime.datetime.combine(end_date, datetime.time.min) + datetime.timedelta(days=1)).isoformat()

            # Pass customer filter to product summary function
            summary_data = db_operations.fetch_product_summary_by_date_range(start_date_dt_str, end_date_dt_str, customer_name=selected_customer)

            for i in self.custom_summary_tree.get_children():
                self.custom_summary_tree.delete(i)

            grand_total = 0.0
            if summary_data:
                for item_summary in summary_data:
                    name, total_qty, total_revenue = item_summary
                    revenue_display = f"{gui_utils.CURRENCY_SYMBOL}{total_revenue:.2f}"
                    self.custom_summary_tree.insert("", tk.END, values=(name, total_qty, revenue_display))
                    grand_total += total_revenue
            else:
                 self.custom_summary_tree.insert("", tk.END, values=("No sales in this period", "", ""))

            self.custom_range_grand_total_label.config(text=f"Selected Range Total: {gui_utils.CURRENCY_SYMBOL}{grand_total:.2f}")

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

            conn = sqlite3.connect(db_operations.DATABASE_FILENAME)
            cursor = conn.cursor()
            cursor.execute("SELECT SaleTimestamp, CustomerName, TotalAmount FROM Sales WHERE SaleID = ?", (sale_id,))
            sale_data_db = cursor.fetchone()
            conn.close()
            if not sale_data_db: raise ValueError("Sale ID not found in database.")

            timestamp_str = sale_data_db[0]
            customer_name = sale_data_db[1]
            total_amount = sale_data_db[2]
            total_display = f"{gui_utils.CURRENCY_SYMBOL}{total_amount:.2f}"

            items = db_operations.fetch_sale_items_from_db(sale_id)
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
                values = self.sales_tree.item(selected_item_id, 'values')
                # --- Update confirmation message to use Sales # ---
                confirm_msg = f"Are you sure you want to permanently delete Sales # {sale_id_to_delete} ({values[2]})?" # Index 2 is timestamp now
            except (tk.TclError, IndexError):
                confirm_msg = f"Are you sure you want to permanently delete Sales # {sale_id_to_delete}?"

            confirmed = messagebox.askyesno("Confirm Deletion", confirm_msg, parent=self)
            if confirmed:
                if db_operations.delete_sale_from_db(sale_id_to_delete):
                    messagebox.showinfo("Success", f"Sales # {sale_id_to_delete} deleted successfully.", parent=self)
                    self.populate_sales_list()
                    self.update_default_summaries()
                    self.update_custom_summary()
                else:
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
        receipt += f"Sales #: {sale_id}\n" # Changed label back
        try:
            timestamp_obj = datetime.datetime.fromisoformat(timestamp_str)
            receipt += f"Date: {timestamp_obj.strftime('%a %Y-%m-%d %H:%M:%S')}\n" # Include day
        except (TypeError, ValueError):
            receipt += f"Date: {timestamp_str}\n"
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
        if not self.sales_tree.get_children():
            messagebox.showwarning("No Data", "There is no sales data to export.", parent=self)
            return

        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Sales History As",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path: # User cancelled
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Write header row using the Treeview column headings
                headers = [self.sales_tree.heading(col)['text'] for col in self.sales_columns_display]
                writer.writerow(headers)

                # Write data rows (iterate in display order - newest first)
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
        # Check if the first row indicates no sales
        first_item_values = self.custom_summary_tree.item(self.custom_summary_tree.get_children()[0])['values']
        if first_item_values and first_item_values[0] == "No sales in this period":
             messagebox.showwarning("No Data", "There is no summary data to export.", parent=self)
             return

        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Product Summary As",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path: # User cancelled
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Write header row using the Treeview column headings
                headers = [self.custom_summary_tree.heading(col)['text'] for col in self.summary_columns]
                writer.writerow(headers)

                # Write data rows
                for item_id in self.custom_summary_tree.get_children():
                    row_values = self.custom_summary_tree.item(item_id)['values']
                    writer.writerow(row_values)

            messagebox.showinfo("Export Successful", f"Product summary exported successfully to:\n{file_path}", parent=self)
            print(f"Product summary exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export product summary.\nError: {e}", parent=self)
            print(f"Error exporting product summary: {e}")

