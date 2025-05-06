import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog  # Added for file dialogs
import datetime
import os
import sqlite3  # Keep for error catching if needed
import csv  # Added for CSV export
import logging  # Import logging for chart window

# --- External Libraries ---
from dateutil.relativedelta import relativedelta, MO, SU

try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None

# --- Import Project Modules ---
import db_operations
import gui_utils  # Import the new utils module

# --- Import the new charts window ---
try:
    from gui_charts import SalesHistoryCharts
except ImportError:
    SalesHistoryCharts = None  # Handle case where file might be missing
    logging.warning("gui_charts.py not found. Sales Graph feature will be disabled.")  # Use logging


# --- Sales History Window Class ---
class SalesHistoryWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent  # Store parent reference if needed
        self.title("Sales History & Summary")
        gui_utils.set_window_icon(self)  # Use helper function

        # --- Chart window reference ---
        self.chart_window = None
        self.todays_items_window = None  # Reference for today's items window
        self.todays_items_tree = None  # Treeview for today's items

        win_width = 850
        win_height = 700
        self.geometry(f"{win_width}x{win_height}")
        self.minsize(700, 500)
        gui_utils.center_window(self, win_width, win_height)
        self.columnconfigure(0, weight=2)  # Sales list column
        self.columnconfigure(1, weight=1)  # Receipt details column

        # Row configurations
        self.rowconfigure(0, weight=0)  # Header labels
        self.rowconfigure(1, weight=1)  # Sales list and Receipt details
        self.rowconfigure(2, weight=0)  # Today's summary
        self.rowconfigure(3, weight=0)  # Default summaries (Week)
        self.rowconfigure(4, weight=0)  # Custom date entry
        self.rowconfigure(5, weight=1)  # Custom summary tree
        self.rowconfigure(6, weight=0)  # Custom total and export
        self.rowconfigure(7, weight=0)  # Main action buttons

        # --- Widgets ---
        ttk.Label(self, text="Sales List", font=("Arial", 14, "bold")).grid(row=0, column=0, pady=10, padx=10,
                                                                            sticky="w")
        ttk.Label(self, text="Receipt Details", font=("Arial", 14, "bold")).grid(row=0, column=1, pady=10, padx=10,
                                                                                 sticky="w")

        # Sales List Treeview (Row 1, Column 0)
        list_frame = ttk.Frame(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.sales_columns_display = ("sale_num", "receipt_no", "timestamp", "customer", "total")
        self.sales_tree = ttk.Treeview(list_frame, columns=self.sales_columns_display, show="headings",
                                       selectmode="browse")
        self.sales_tree.heading("sale_num", text="Sales #")
        self.sales_tree.heading("receipt_no", text="Receipt No.")
        self.sales_tree.heading("timestamp", text="Timestamp")
        self.sales_tree.heading("customer", text="Customer")
        self.sales_tree.heading("total", text="Total")
        self.sales_tree.column("sale_num", anchor=tk.W, width=60, stretch=False)
        self.sales_tree.column("receipt_no", anchor=tk.W, width=80, stretch=False)
        self.sales_tree.column("timestamp", anchor=tk.W, width=160, stretch=False)
        self.sales_tree.column("customer", anchor=tk.W, width=100, stretch=True)
        self.sales_tree.column("total", anchor=tk.E, width=70, stretch=False)
        self.sales_tree.grid(row=0, column=0, sticky="nsew")
        sales_list_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.sales_tree.yview)
        self.sales_tree.configure(yscrollcommand=sales_list_scrollbar.set)
        sales_list_scrollbar.grid(row=0, column=1, sticky="ns")
        self.sales_tree.bind("<<TreeviewSelect>>", self.on_sale_select)

        # Receipt Details Text Area (Row 1, Column 1)
        text_frame = ttk.Frame(self)
        text_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=5)
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        self.receipt_text = tk.Text(text_frame, wrap="word", state="disabled", height=10, width=40,
                                    font=("Courier New", 9), relief="sunken", borderwidth=1)
        self.receipt_text.grid(row=0, column=0, sticky="nsew")
        receipt_text_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.receipt_text.yview)
        self.receipt_text.configure(yscrollcommand=receipt_text_scrollbar.set)
        receipt_text_scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Today's Sales Summary (Row 2) ---
        today_frame = ttk.LabelFrame(self, text="Today's Sales", padding="5")
        today_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        today_frame.columnconfigure(1, weight=1)  # Allow label to expand
        self.today_total_label = ttk.Label(today_frame, text=f"Total: {gui_utils.CURRENCY_SYMBOL}0.00",
                                           font=("Arial", 10, "bold"))
        self.today_total_label.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        # Corrected: Button text and command name
        self.view_todays_items_button = ttk.Button(today_frame, text="View Today's Item Sales",
                                                   command=self.view_todays_items)
        self.view_todays_items_button.grid(row=0, column=1, sticky="e", padx=5, pady=2)

        # Default Summaries (Row 3 - Simplified Further)
        summary_frame = ttk.LabelFrame(self, text="Default Summaries", padding="5")
        summary_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 5))
        summary_frame.columnconfigure(1, weight=1)
        self.week_label_var = tk.StringVar(value="This Week (Mon-Sun):")
        ttk.Label(summary_frame, textvariable=self.week_label_var).grid(row=0, column=0, sticky="w", padx=5, pady=1)
        self.week_total_label = ttk.Label(summary_frame, text=f"Total: {gui_utils.CURRENCY_SYMBOL}0.00",
                                          font=("Arial", 10))
        self.week_total_label.grid(row=0, column=1, sticky="e", padx=5, pady=1)

        # Custom Date Range Selection (Row 4)
        custom_entry_frame = ttk.LabelFrame(self, text="Custom Date Range", padding="10")
        custom_entry_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 0))
        custom_entry_frame.columnconfigure(1, weight=0)  # Start Date Entry
        custom_entry_frame.columnconfigure(3, weight=0)  # End Date Entry
        custom_entry_frame.columnconfigure(4, weight=1)  # View Button (to push it right)

        if DateEntry:
            ttk.Label(custom_entry_frame, text="Start Date:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky='w')
            self.start_date_entry = DateEntry(custom_entry_frame, width=12, background='darkblue',
                                              foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
            self.start_date_entry.grid(row=0, column=1, padx=(0, 10), pady=5)
            ttk.Label(custom_entry_frame, text="End Date:").grid(row=0, column=2, padx=(10, 5), pady=5, sticky='w')
            self.end_date_entry = DateEntry(custom_entry_frame, width=12, background='darkblue',
                                            foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
            self.end_date_entry.grid(row=0, column=3, padx=(0, 10), pady=5)
            self.end_date_entry.set_date(datetime.date.today())  # Default end date to today
        else:
            # Fallback if tkcalendar is not available
            ttk.Label(custom_entry_frame, text="Start (YYYY-MM-DD):").grid(row=0, column=0, padx=(0, 5), pady=5,
                                                                           sticky='w')
            self.start_date_str_var = tk.StringVar()
            self.start_date_entry = ttk.Entry(custom_entry_frame, textvariable=self.start_date_str_var, width=12)
            self.start_date_entry.grid(row=0, column=1, padx=(0, 10), pady=5)

            ttk.Label(custom_entry_frame, text="End (YYYY-MM-DD):").grid(row=0, column=2, padx=(10, 5), pady=5,
                                                                         sticky='w')
            self.end_date_str_var = tk.StringVar(value=datetime.date.today().strftime('%Y-%m-%d'))
            self.end_date_entry = ttk.Entry(custom_entry_frame, textvariable=self.end_date_str_var, width=12)
            self.end_date_entry.grid(row=0, column=3, padx=(0, 10), pady=5)
            logging.warning("tkcalendar not found. Using basic Entry widgets for date input.")

        view_range_button = ttk.Button(custom_entry_frame, text="View Detailed Summary",
                                       command=self.update_custom_summary)
        view_range_button.grid(row=0, column=4, padx=(10, 5), pady=5, sticky='e')

        # Custom Date Range Details Treeview (Row 5)
        custom_summary_tree_frame = ttk.LabelFrame(self, text="Custom Date Range Details", padding="5")
        custom_summary_tree_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        custom_summary_tree_frame.rowconfigure(0, weight=1)
        custom_summary_tree_frame.columnconfigure(0, weight=1)
        self.summary_columns = ('product', 'total_qty', 'total_revenue')
        self.custom_summary_tree = ttk.Treeview(custom_summary_tree_frame, columns=self.summary_columns,
                                                show="headings", selectmode="browse")
        self.custom_summary_tree.heading('product', text='Product')
        self.custom_summary_tree.heading('total_qty', text='Total Qty Sold')
        self.custom_summary_tree.heading('total_revenue', text='Total Revenue')
        self.custom_summary_tree.column('product', anchor=tk.W, width=200, stretch=True)
        self.custom_summary_tree.column('total_qty', anchor=tk.CENTER, width=100, stretch=False)
        self.custom_summary_tree.column('total_revenue', anchor=tk.E, width=120, stretch=False)
        self.custom_summary_tree.grid(row=0, column=0, sticky='nsew')
        summary_scrollbar = ttk.Scrollbar(custom_summary_tree_frame, orient="vertical",
                                          command=self.custom_summary_tree.yview)
        self.custom_summary_tree.configure(yscrollcommand=summary_scrollbar.set)
        summary_scrollbar.grid(row=0, column=1, sticky='ns')
        self.custom_summary_tree.bind("<Double-Button-1>", self.on_summary_item_select)

        # Custom Range Grand Total Label and Export Button (Row 6)
        custom_total_frame = ttk.Frame(self)
        custom_total_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 5))
        custom_total_frame.columnconfigure(0, weight=1)
        self.custom_range_items_label = ttk.Label(custom_total_frame, text="Items: 0", font=("Arial", 10))
        self.custom_range_items_label.grid(row=0, column=0, sticky="w", padx=5)
        self.custom_range_avg_label = ttk.Label(custom_total_frame, text=f"Avg Sale: {gui_utils.CURRENCY_SYMBOL}0.00",
                                                font=("Arial", 10))
        self.custom_range_avg_label.grid(row=1, column=0, sticky="w", padx=5)
        self.custom_range_grand_total_label = ttk.Label(custom_total_frame,
                                                        text=f"Total: {gui_utils.CURRENCY_SYMBOL}0.00",
                                                        font=("Arial", 10, "bold"))
        self.custom_range_grand_total_label.grid(row=0, column=1, sticky="e", padx=(10, 0))
        export_summary_button = ttk.Button(custom_total_frame, text="Export Summary",
                                           command=self.export_summary_to_csv)
        export_summary_button.grid(row=1, column=1, sticky="e", padx=(10, 0), pady=(2, 0))

        # Action Buttons (Row 7)
        action_button_frame = ttk.Frame(self)
        action_button_frame.grid(row=7, column=0, columnspan=2, pady=10)
        graph_button = ttk.Button(action_button_frame, text="Sales Graph", command=self.open_sales_chart)
        graph_button.pack(side=tk.LEFT, padx=10)
        export_sales_button = ttk.Button(action_button_frame, text="Export Sales List",
                                         command=self.export_sales_to_csv)
        export_sales_button.pack(side=tk.LEFT, padx=10)
        delete_button = ttk.Button(action_button_frame, text="Delete Selected Sale", command=self.delete_selected_sale)
        delete_button.pack(side=tk.LEFT, padx=10)
        close_button = ttk.Button(action_button_frame, text="Close", command=self.destroy)
        close_button.pack(side=tk.LEFT, padx=10)

        # Initial data population
        self.populate_sales_list()
        self.update_default_summaries()
        self.update_todays_summary()
        self.update_custom_summary()

        self.bind('<Escape>', lambda event=None: self.destroy())

    def populate_sales_list(self):
        """Fetches sales and populates the sales Treeview."""
        for i in self.sales_tree.get_children():
            self.sales_tree.delete(i)
        sales_data = db_operations.fetch_sales_list_from_db()
        if sales_data:
            receipt_counter = 0
            for i, sale in enumerate(sales_data):
                receipt_counter += 1
                sale_id, timestamp_str, total_amount, customer_name_db = sale
                try:
                    timestamp_obj = datetime.datetime.fromisoformat(timestamp_str)
                    display_ts = timestamp_obj.strftime('%a %Y-%m-%d %H:%M:%S')
                except (TypeError, ValueError):
                    display_ts = timestamp_str
                total_display = f"{gui_utils.CURRENCY_SYMBOL}{total_amount:.2f}"
                self.sales_tree.insert("", 0,
                                       values=(sale_id, receipt_counter, display_ts, customer_name_db, total_display),
                                       iid=sale_id)
        else:
            pass  # No sales data, tree remains empty
        self.update_receipt_display("")  # Clear receipt display

    def update_todays_summary(self):
        """Calculates and displays today's sales total."""
        today = datetime.date.today()
        start_today_dt_str = datetime.datetime.combine(today, datetime.time.min).isoformat()
        # For end of day, make it exclusive: start of next day
        end_today_dt_str = (
            datetime.datetime.combine(today + datetime.timedelta(days=1), datetime.time.min)).isoformat()

        today_revenue, _, _ = db_operations.fetch_sales_stats(start_today_dt_str, end_today_dt_str)
        self.today_total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{today_revenue:.2f}")

    def update_default_summaries(self):
        """Calculates and displays weekly sales totals."""
        today = datetime.date.today()
        start_of_week = today + relativedelta(weekday=MO(-1))  # Monday of the current week
        end_of_week = start_of_week + relativedelta(days=6)  # Sunday of the current week

        start_week_dt_str = datetime.datetime.combine(start_of_week, datetime.time.min).isoformat()
        # For end of week, make it exclusive: start of the day AFTER Sunday
        end_week_dt_str = (
            datetime.datetime.combine(end_of_week + datetime.timedelta(days=1), datetime.time.min)).isoformat()

        week_revenue, _, week_sales_count = db_operations.fetch_sales_stats(start_week_dt_str, end_week_dt_str)

        start_date_fmt = start_of_week.strftime("%b %d")
        end_date_fmt = end_of_week.strftime("%b %d")
        week_label_text = f"This Week (Mon-Sun) {start_date_fmt} - {end_date_fmt}:"
        self.week_label_var.set(week_label_text)

        self.week_total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{week_revenue:.2f}")

    def update_custom_summary(self):
        """Calculates and displays detailed product summary for the selected date range."""
        try:
            if DateEntry:  # Using tkcalendar
                start_date = self.start_date_entry.get_date()
                end_date = self.end_date_entry.get_date()
            else:  # Using ttk.Entry, need to parse
                start_date_str = self.start_date_str_var.get()
                end_date_str = self.end_date_str_var.get()
                if not start_date_str or not end_date_str:  # Basic check
                    messagebox.showwarning("Missing Date", "Please enter both start and end dates.", parent=self)
                    return
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()

            if start_date > end_date:
                messagebox.showwarning("Invalid Range", "Start date cannot be after end date.", parent=self)
                return

            start_date_dt_str = datetime.datetime.combine(start_date, datetime.time.min).isoformat()
            # For end date, make it exclusive: start of the day AFTER the selected end_date
            end_date_dt_str = (
                datetime.datetime.combine(end_date + datetime.timedelta(days=1), datetime.time.min)).isoformat()

            summary_data = db_operations.fetch_product_summary_by_date_range(start_date_dt_str, end_date_dt_str)

            for i in self.custom_summary_tree.get_children():
                self.custom_summary_tree.delete(i)

            if summary_data:
                for i, item_summary in enumerate(summary_data):
                    name, total_qty, total_revenue = item_summary
                    revenue_display = f"{gui_utils.CURRENCY_SYMBOL}{total_revenue:.2f}"
                    self.custom_summary_tree.insert("", tk.END, values=(name, total_qty, revenue_display))
            else:
                self.custom_summary_tree.insert("", tk.END, values=("No sales in this period", "", ""))

            custom_revenue, custom_items, custom_sales_count = db_operations.fetch_sales_stats(start_date_dt_str,
                                                                                               end_date_dt_str)
            custom_avg = custom_revenue / custom_sales_count if custom_sales_count > 0 else 0.0

            self.custom_range_grand_total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{custom_revenue:.2f}")
            self.custom_range_items_label.config(text=f"Items: {custom_items}")
            self.custom_range_avg_label.config(text=f"Avg Sale: {gui_utils.CURRENCY_SYMBOL}{custom_avg:.2f}")

        except ValueError as ve:  # Catch parsing errors for manual entry
            messagebox.showerror("Invalid Date Format", f"Please enter dates in YYYY-MM-DD format.\nError: {ve}",
                                 parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Could not calculate custom summary: {e}", parent=self)

    def on_sale_select(self, event=None):
        """Handles selection change in the sales Treeview to display receipt."""
        selected_item_id = self.sales_tree.focus()
        if not selected_item_id:
            self.update_receipt_display("Select a sale from the list to view details.")
            return
        try:
            sale_id = int(selected_item_id)
            item_data = self.sales_tree.item(selected_item_id, 'values')
            if not item_data or len(item_data) < 5:
                raise ValueError("Could not retrieve sale details from list.")

            # Fetch full sale details from DB to ensure accuracy
            # This part was previously doing a direct sqlite3 call, which is not ideal.
            # Assuming db_operations has a function like fetch_one_sale(sale_id)
            # For now, we'll use existing functions, but this could be optimized.

            # We need SaleTimestamp, CustomerName, TotalAmount for the header
            # And then SaleItems for the body.
            # Let's get the header info from the selected tree row first.
            # item_data[0] is sale_id (Sales #), item_data[1] is receipt_no,
            # item_data[2] is timestamp_str, item_data[3] is customer_name, item_data[4] is total_display

            timestamp_str_from_tree = item_data[2]  # This is already formatted for display
            customer_name_from_tree = item_data[3]
            total_display_from_tree = item_data[4]

            # For items, we must fetch from DB
            items = db_operations.fetch_sale_items_from_db(sale_id)

            # Regenerate receipt using the potentially more accurate timestamp from DB if needed,
            # but for now, using tree data for header is simpler.
            # The timestamp from tree is already formatted. We might want raw for fromisoformat.
            # Let's assume the tree's timestamp is sufficient for display in receipt header.
            # If raw timestamp is needed, an additional DB call or passing it in sales_list_from_db would be required.

            receipt = self.generate_detailed_receipt(sale_id, timestamp_str_from_tree, customer_name_from_tree,
                                                     total_display_from_tree, items)
            self.update_receipt_display(receipt)
        except (IndexError, ValueError, TypeError) as e:  # Removed sqlite3.Error as direct calls are avoided
            logging.error(f"Error processing sale selection: {e}")
            self.update_receipt_display("Error retrieving sale details.")

    def delete_selected_sale(self):
        """Deletes the sale selected in the Treeview."""
        selected_item_id = self.sales_tree.focus()
        if not selected_item_id:
            messagebox.showwarning("No Selection", "Please select a sale from the list to delete.", parent=self)
            return
        try:
            sale_id_to_delete = int(selected_item_id)
            try:
                values = self.sales_tree.item(selected_item_id, 'values')
                confirm_msg = f"Are you sure you want to permanently delete Sales # {sale_id_to_delete} ({values[2]})?"
            except (tk.TclError, IndexError):
                confirm_msg = f"Are you sure you want to permanently delete Sales # {sale_id_to_delete}?"

            confirmed = messagebox.askyesno("Confirm Deletion", confirm_msg, parent=self)
            if confirmed:
                if db_operations.delete_sale_from_db(sale_id_to_delete):
                    messagebox.showinfo("Success", f"Sales # {sale_id_to_delete} deleted successfully.", parent=self)
                    self.populate_sales_list()
                    self.update_default_summaries()
                    self.update_todays_summary()
                    self.update_custom_summary()
                else:
                    # db_operations.delete_sale_from_db does not show messagebox on its own for this one
                    messagebox.showerror("Error", f"Failed to delete Sales # {sale_id_to_delete}. Check logs.",
                                         parent=self)
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
        # timestamp_str is already formatted from the tree view
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
        # total_display is already formatted from the tree view
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

        if not file_path: return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                headers = [self.sales_tree.heading(col)['text'] for col in self.sales_columns_display]
                writer.writerow(headers)
                for item_id in self.sales_tree.get_children():
                    row_values = self.sales_tree.item(item_id)['values']
                    writer.writerow(row_values)

            messagebox.showinfo("Export Successful", f"Sales history exported successfully to:\n{file_path}",
                                parent=self)
            logging.info(f"Sales history exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export sales history.\nError: {e}", parent=self)
            logging.exception(f"Error exporting sales history: {e}")

    def export_summary_to_csv(self):
        """Exports the currently displayed custom summary data to a CSV file."""
        if not self.custom_summary_tree.get_children():
            messagebox.showwarning("No Data", "There is no summary data to export.", parent=self)
            return
        # Check if the only item is the placeholder
        first_item_id = self.custom_summary_tree.get_children()[0]
        first_item_values = self.custom_summary_tree.item(first_item_id)['values']
        if first_item_values and first_item_values[0] == "No sales in this period":
            messagebox.showwarning("No Data", "There is no summary data to export.", parent=self)
            return

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Product Summary As",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path: return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                headers = [self.custom_summary_tree.heading(col)['text'] for col in self.summary_columns]
                writer.writerow(headers)
                for item_id in self.custom_summary_tree.get_children():
                    row_values = self.custom_summary_tree.item(item_id)['values']
                    writer.writerow(row_values)

            messagebox.showinfo("Export Successful", f"Product summary exported successfully to:\n{file_path}",
                                parent=self)
            logging.info(f"Product summary exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export product summary.\nError: {e}", parent=self)
            logging.exception(f"Error exporting product summary: {e}")

    def on_summary_item_select(self, event=None):
        """Displays details of the selected item in the custom summary treeview."""
        selected_item_id = self.custom_summary_tree.focus()
        if not selected_item_id:
            return

        item_values = self.custom_summary_tree.item(selected_item_id)['values']

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
            messagebox.showinfo("Product Summary Detail", message, parent=self)
        except IndexError:
            messagebox.showerror("Error", "Could not retrieve details for the selected summary item.", parent=self)

    def open_sales_chart(self):
        """Opens the sales chart window."""
        if SalesHistoryCharts is None:
            messagebox.showerror("Error",
                                 "Chart library components not found.\nPlease ensure gui_charts.py is present and matplotlib is installed.",
                                 parent=self)
            return

        if self.chart_window is None or not tk.Toplevel.winfo_exists(self.chart_window):
            self.chart_window = SalesHistoryCharts(self, db_operations)
            self.chart_window.grab_set()
        else:
            self.chart_window.deiconify()
            self.chart_window.lift()
            self.chart_window.focus_set()
            try:
                self.chart_window.update_charts()
            except Exception as e:
                logging.error(f"Failed to update charts: {e}")
                messagebox.showerror("Chart Error", f"Failed to update charts:\n{e}",
                                     parent=self.chart_window if self.chart_window and tk.Toplevel.winfo_exists(
                                         self.chart_window) else self)

    def view_todays_items(self):
        """Fetches and displays items sold today in a new window. Corrected version."""
        logging.info("Showing today's individual item sales summary.")
        today_str = datetime.date.today().strftime('%Y-%m-%d')

        # This is the corrected function call
        items_data = db_operations.fetch_sales_items_for_date(today_str)

        if self.todays_items_window is None or not tk.Toplevel.winfo_exists(self.todays_items_window):
            self.todays_items_window = tk.Toplevel(self)
            self.todays_items_window.title(f"Items Sold Today ({today_str})")
            gui_utils.set_window_icon(self.todays_items_window)
            self.todays_items_window.geometry("500x400")
            gui_utils.center_window(self.todays_items_window, 500, 400)  # Center with explicit size
            self.todays_items_window.transient(self)
            self.todays_items_window.protocol("WM_DELETE_WINDOW", self._close_todays_items_window)

            tree_frame = ttk.Frame(self.todays_items_window)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            cols = ('product', 'qty', 'revenue')
            # Store tree as instance variable
            self.todays_items_tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
            self.todays_items_tree.heading('product', text='Product Name')
            self.todays_items_tree.heading('qty', text='Total Qty Sold')
            self.todays_items_tree.heading('revenue', text='Total Revenue')
            self.todays_items_tree.column('product', anchor=tk.W, stretch=True)
            self.todays_items_tree.column('qty', anchor=tk.CENTER, width=100, stretch=False)
            self.todays_items_tree.column('revenue', anchor=tk.E, width=120, stretch=False)

            scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.todays_items_tree.yview)
            self.todays_items_tree.configure(yscrollcommand=scrollbar.set)

            self.todays_items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            self.todays_items_window.deiconify()
            self.todays_items_window.lift()
            self.todays_items_window.focus_set()

        # Clear existing items in the tree (important for refresh)
        if self.todays_items_tree:  # Ensure tree exists
            for i in self.todays_items_tree.get_children():
                self.todays_items_tree.delete(i)

            # Populate Treeview with fresh data
            if items_data:
                for item in items_data:
                    name, qty, revenue = item
                    revenue_str = f"{gui_utils.CURRENCY_SYMBOL}{revenue:.2f}"
                    self.todays_items_tree.insert('', tk.END, values=(name, qty, revenue_str))
            else:
                self.todays_items_tree.insert('', tk.END, values=("No items sold today.", "", ""))

        self.todays_items_window.grab_set()

    def _close_todays_items_window(self):
        """Handles closing the 'Today's Items' window."""
        if self.todays_items_window:
            self.todays_items_window.grab_release()
            self.todays_items_window.destroy()
            self.todays_items_window = None
            self.todays_items_tree = None  # Clear tree reference as well
