import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
import datetime
import os # Keep os import for checking icon file
import sqlite3 # Import needed for sqlite3.Error in SalesHistoryWindow

# --- External Libraries ---
from dateutil.relativedelta import relativedelta, MO, SU
try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None

# --- Import Database Operations ---
# Assume db_operations.py is in the same directory
import db_operations

# --- Constants Defined Here ---
# --- !!! Updated Icon Filename !!! ---
ICON_FILENAME = "ocean.ico" # Using the requested icon name


# --- Helper Function to Center Windows ---
def center_window(window, width=None, height=None):
    """Centers a tkinter window on the screen."""
    window.update_idletasks()
    w = width if width else window.winfo_reqwidth()
    h = height if height else window.winfo_reqheight()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    window.geometry(f'{w}x{h}+{x}+{y}')

# --- Helper Function to Set Icon ---
def set_window_icon(window):
    """Sets the window icon, handling potential errors."""
    if os.path.exists(ICON_FILENAME):
        try:
            window.iconbitmap(ICON_FILENAME)
            # print(f"Icon '{ICON_FILENAME}' set for {window.title()}.") # Optional debug print
        except tk.TclError as e:
            print(f"Error setting icon '{ICON_FILENAME}' for {window.title()}: {e}.")
        except Exception as e:
             print(f"An unexpected error occurred while setting icon for {window.title()}: {e}")
    else:
         print(f"Warning: Icon file '{ICON_FILENAME}' not found for {window.title()}.")


# --- Customer Selection Dialog Class ---
class CustomerSelectionDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Select or Enter Customer")
        set_window_icon(self) # Set icon for this dialog

        dialog_width = 350
        dialog_height = 150
        self.result = None
        self.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        req_width = self.winfo_reqwidth()
        req_height = self.winfo_reqheight()
        x = parent_x + (parent_width // 2) - (req_width // 2)
        y = parent_y + (parent_height // 2) - (req_height // 2)
        self.geometry(f'+{x}+{y}')
        self.transient(parent)
        self.grab_set()
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text="Select existing or enter new customer:").grid(row=0, column=0, pady=(10, 5), padx=10, sticky='w')
        # Fetch names using the imported function
        self.customer_names_list = db_operations.fetch_distinct_customer_names()
        self.customer_var = tk.StringVar()
        self.customer_combobox = ttk.Combobox(self, textvariable=self.customer_var, values=self.customer_names_list)
        self.customer_combobox.grid(row=1, column=0, pady=5, padx=10, sticky='ew')
        self.customer_combobox.focus_set()
        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, pady=10)
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
            # Case-insensitive check against the fetched list
            for existing_name in self.customer_names_list:
                if selected_name.lower() == existing_name.lower():
                    is_new = False
                    break
            if is_new and selected_name != 'N/A':
                print(f"Adding new customer from selection dialog: {selected_name}")
                # Add to DB using imported function
                if not db_operations.add_customer_to_db(selected_name, None, None):
                    print(f"Warning: Could not add new customer '{selected_name}' via selection dialog.")
                    pass
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()


# --- Sales History Window Class ---
class SalesHistoryWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Sales History & Summary")
        set_window_icon(self) # Set icon for this window

        win_width = 850
        win_height = 750
        self.geometry(f"{win_width}x{win_height}")
        self.minsize(700, 600)
        center_window(self, win_width, win_height)
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=0)
        self.rowconfigure(4, weight=0)
        ttk.Label(self, text="Sales List", font=("Arial", 14, "bold")).grid(row=0, column=0, pady=10, padx=10, sticky="w")
        ttk.Label(self, text="Receipt Details", font=("Arial", 14, "bold")).grid(row=0, column=1, pady=10, padx=10, sticky="w")
        list_frame = ttk.Frame(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        sales_columns_display = ("sale_num", "timestamp", "customer", "total")
        self.sales_tree = ttk.Treeview(list_frame, columns=sales_columns_display, show="headings", selectmode="browse")
        self.sales_tree.heading("sale_num", text="Sales #")
        self.sales_tree.heading("timestamp", text="Timestamp")
        self.sales_tree.heading("customer", text="Customer")
        self.sales_tree.heading("total", text="Total")
        self.sales_tree.column("sale_num", anchor=tk.W, width=60, stretch=False)
        self.sales_tree.column("timestamp", anchor=tk.W, width=150, stretch=False)
        self.sales_tree.column("customer", anchor=tk.W, width=120, stretch=True)
        self.sales_tree.column("total", anchor=tk.E, width=80, stretch=False)
        self.sales_tree.grid(row=0, column=0, sticky="nsew")
        sales_list_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.sales_tree.yview)
        self.sales_tree.configure(yscrollcommand=sales_list_scrollbar.set)
        sales_list_scrollbar.grid(row=0, column=1, sticky="ns")
        self.sales_tree.bind("<<TreeviewSelect>>", self.on_sale_select)
        text_frame = ttk.Frame(self)
        text_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=5)
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        self.receipt_text = tk.Text(text_frame, wrap="word", state="disabled", height=10, width=40, font=("Courier New", 9))
        self.receipt_text.grid(row=0, column=0, sticky="nsew")
        receipt_text_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.receipt_text.yview)
        self.receipt_text.configure(yscrollcommand=receipt_text_scrollbar.set)
        receipt_text_scrollbar.grid(row=0, column=1, sticky="ns")
        summary_frame = ttk.LabelFrame(self, text="Default Summaries", padding="5")
        summary_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        summary_frame.columnconfigure(1, weight=1)
        ttk.Label(summary_frame, text="This Week (Mon-Sun):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.week_total_label = ttk.Label(summary_frame, text=f"{db_operations.CURRENCY_SYMBOL}0.00", font=("Arial", 10, "bold"))
        self.week_total_label.grid(row=0, column=1, sticky="e", padx=5, pady=2)
        ttk.Label(summary_frame, text="This Month:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.month_total_label = ttk.Label(summary_frame, text=f"{db_operations.CURRENCY_SYMBOL}0.00", font=("Arial", 10, "bold"))
        self.month_total_label.grid(row=1, column=1, sticky="e", padx=5, pady=2)
        custom_summary_frame = ttk.LabelFrame(self, text="Custom Date Range Summary", padding="10")
        custom_summary_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 10))
        custom_summary_frame.columnconfigure(1, weight=0)
        custom_summary_frame.columnconfigure(3, weight=0)
        custom_summary_frame.columnconfigure(4, weight=0)
        custom_summary_frame.columnconfigure(5, weight=1)
        ttk.Label(custom_summary_frame, text="Start Date:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky='w')
        self.start_date_entry = DateEntry(custom_summary_frame, width=12, background='darkblue',
                                          foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.start_date_entry.grid(row=0, column=1, padx=(0, 10), pady=5)
        ttk.Label(custom_summary_frame, text="End Date:").grid(row=0, column=2, padx=(10, 5), pady=5, sticky='w')
        self.end_date_entry = DateEntry(custom_summary_frame, width=12, background='darkblue',
                                        foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.end_date_entry.grid(row=0, column=3, padx=(0, 10), pady=5)
        self.end_date_entry.set_date(datetime.date.today())
        view_range_button = ttk.Button(custom_summary_frame, text="View Detailed Summary", command=self.update_custom_summary)
        view_range_button.grid(row=0, column=4, padx=(10, 5), pady=5, sticky='e')

        # Custom Summary Treeview Frame
        custom_summary_tree_frame = ttk.LabelFrame(self, text="Custom Date Range Details", padding="5")
        custom_summary_tree_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=10, pady=5) # Row 4
        custom_summary_tree_frame.rowconfigure(0, weight=1)
        custom_summary_tree_frame.columnconfigure(0, weight=1)

        summary_columns = ('product', 'total_qty', 'total_revenue')
        self.custom_summary_tree = ttk.Treeview(custom_summary_tree_frame, columns=summary_columns, show="headings", selectmode="none")
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

        # Custom Range Grand Total Label
        self.custom_range_grand_total_label = ttk.Label(self, text=f"Selected Range Total: {db_operations.CURRENCY_SYMBOL}0.00", font=("Arial", 10, "bold"))
        self.custom_range_grand_total_label.grid(row=5, column=0, columnspan=2, sticky="e", padx=10, pady=(0,5)) # Row 5

        # Action Buttons Frame
        action_button_frame = ttk.Frame(self)
        action_button_frame.grid(row=6, column=0, columnspan=2, pady=10) # Row 6
        delete_button = ttk.Button(action_button_frame, text="Delete Selected Sale", command=self.delete_selected_sale)
        delete_button.pack(side=tk.LEFT, padx=10)
        close_button = ttk.Button(action_button_frame, text="Close", command=self.destroy)
        close_button.pack(side=tk.LEFT, padx=10)

        self.populate_sales_list()
        self.update_default_summaries()

    def populate_sales_list(self):
        """Fetches sales and populates the sales Treeview."""
        for i in self.sales_tree.get_children():
            self.sales_tree.delete(i)
        sales_data = db_operations.fetch_sales_list_from_db()
        if sales_data:
            for sale in sales_data:
                sale_id, timestamp_str, total_amount, customer_name = sale
                try:
                    timestamp_obj = datetime.datetime.fromisoformat(timestamp_str)
                    display_ts = timestamp_obj.strftime('%Y-%m-%d %H:%M:%S')
                except (TypeError, ValueError):
                    display_ts = timestamp_str
                total_display = f"{db_operations.CURRENCY_SYMBOL}{total_amount:.2f}"
                self.sales_tree.insert("", tk.END, values=(sale_id, display_ts, customer_name, total_display), iid=sale_id)
        else:
            pass
        self.update_receipt_display("")

    def update_default_summaries(self):
        """Calculates and displays weekly and monthly sales totals."""
        today = datetime.date.today()
        start_of_week = today + relativedelta(weekday=MO(-1))
        end_of_week = start_of_week + relativedelta(days=6)
        start_of_month = today.replace(day=1)
        end_of_month = today.replace(day=1) + relativedelta(months=+1) - datetime.timedelta(days=1)
        start_week_dt_str = datetime.datetime.combine(start_of_week, datetime.time.min).isoformat()
        end_week_dt_str = (datetime.datetime.combine(end_of_week, datetime.time.min) + datetime.timedelta(days=1)).isoformat()
        start_month_dt_str = datetime.datetime.combine(start_of_month, datetime.time.min).isoformat()
        end_month_dt_str = (datetime.datetime.combine(end_of_month, datetime.time.min) + datetime.timedelta(days=1)).isoformat()
        weekly_total = db_operations.fetch_sales_summary(start_week_dt_str, end_week_dt_str)
        monthly_total = db_operations.fetch_sales_summary(start_month_dt_str, end_month_dt_str)
        self.week_total_label.config(text=f"{db_operations.CURRENCY_SYMBOL}{weekly_total:.2f}")
        self.month_total_label.config(text=f"{db_operations.CURRENCY_SYMBOL}{monthly_total:.2f}")

    def update_custom_summary(self):
        """Calculates and displays detailed product summary for the selected date range."""
        try:
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date()
            if start_date > end_date:
                messagebox.showwarning("Invalid Range", "Start date cannot be after end date.", parent=self)
                return

            start_date_dt_str = datetime.datetime.combine(start_date, datetime.time.min).isoformat()
            end_date_dt_str = (datetime.datetime.combine(end_date, datetime.time.min) + datetime.timedelta(days=1)).isoformat()

            # Fetch detailed summary data
            summary_data = db_operations.fetch_product_summary_by_date_range(start_date_dt_str, end_date_dt_str)

            # Clear previous summary details
            for i in self.custom_summary_tree.get_children():
                self.custom_summary_tree.delete(i)

            grand_total = 0.0
            if summary_data:
                for item_summary in summary_data:
                    name, total_qty, total_revenue = item_summary
                    revenue_display = f"{db_operations.CURRENCY_SYMBOL}{total_revenue:.2f}"
                    self.custom_summary_tree.insert("", tk.END, values=(name, total_qty, revenue_display))
                    grand_total += total_revenue
            else:
                 self.custom_summary_tree.insert("", tk.END, values=("No sales in this period", "", ""))

            # Update the grand total label for the custom range
            self.custom_range_grand_total_label.config(text=f"Selected Range Total: {db_operations.CURRENCY_SYMBOL}{grand_total:.2f}")

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
            conn = sqlite3.connect(db_operations.DATABASE_FILENAME) # Need sqlite3 here
            cursor = conn.cursor()
            cursor.execute("SELECT SaleTimestamp, CustomerName, TotalAmount FROM Sales WHERE SaleID = ?", (sale_id,))
            sale_data = cursor.fetchone()
            conn.close()
            if not sale_data: raise ValueError("Sale ID not found in database.")
            timestamp_str = sale_data[0]
            customer_name = sale_data[1]
            total_amount = sale_data[2]
            total_display = f"{db_operations.CURRENCY_SYMBOL}{total_amount:.2f}"
            items = db_operations.fetch_sale_items_from_db(sale_id)
            receipt = self.generate_detailed_receipt(sale_id, timestamp_str, customer_name, total_display, items)
            self.update_receipt_display(receipt)
        except (IndexError, ValueError, TypeError, sqlite3.Error) as e: # Catch sqlite3.Error
            print(f"Error processing sale selection: {e}")
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
                confirm_msg = f"Are you sure you want to permanently delete Sale # {sale_id_to_delete} ({values[1]})?"
            except tk.TclError:
                confirm_msg = f"Are you sure you want to permanently delete Sale # {sale_id_to_delete}?"

            confirmed = messagebox.askyesno("Confirm Deletion", confirm_msg, parent=self)
            if confirmed:
                if db_operations.delete_sale_from_db(sale_id_to_delete):
                    messagebox.showinfo("Success", f"Sale # {sale_id_to_delete} deleted successfully.", parent=self)
                    self.populate_sales_list()
                    self.update_default_summaries()
                    self.update_custom_summary()
                else:
                    messagebox.showerror("Error", f"Failed to delete Sale # {sale_id_to_delete}.", parent=self)
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
        receipt += f"Sale ID: {sale_id}\n"
        try:
            timestamp_obj = datetime.datetime.fromisoformat(timestamp_str)
            receipt += f"Date: {timestamp_obj.strftime('%Y-%m-%d %H:%M:%S')}\n"
        except (TypeError, ValueError):
            receipt += f"Date: {timestamp_str}\n"
        receipt += f"Customer: {customer_name}\n"
        receipt += "--------------------------------------\n"
        receipt += "{:<18} {:>3} {:>7} {:>8}\n".format("Item", "Qty", "Price", "Subtotal")
        receipt += "--------------------------------------\n"
        if items:
            for item_details in items:
                name, qty, price, subtotal = item_details
                price_str = f"{db_operations.CURRENCY_SYMBOL}{price:.2f}"
                subtotal_str = f"{db_operations.CURRENCY_SYMBOL}{subtotal:.2f}"
                receipt += "{:<18} {:>3d} {:>7} {:>8}\n".format(name[:18], qty, price_str, subtotal_str)
        else:
            receipt += " (No item details found)\n"
        receipt += "======================================\n"
        receipt += "{:<29} {:>8}\n".format("TOTAL:", total_display)
        receipt += "--------------------------------------\n"
        receipt += "        Thank you!\n"
        return receipt


# --- Updated Customer List Window Class ---
class CustomerListWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manage Customers")
        set_window_icon(self) # Set icon for this window

        win_width = 650
        win_height = 600
        self.geometry(f"{win_width}x{win_height}")
        self.minsize(500, 400)

        center_window(self, win_width, win_height)
        self.transient(parent)
        self.grab_set()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1) # Allow Treeview to expand
        self.rowconfigure(0, weight=0)
        self.rowconfigure(2, weight=0) # Buttons row

        # --- Add/Edit Customer Form Frame ---
        form_frame = ttk.LabelFrame(self, text="Customer Details", padding="10")
        form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        form_frame.columnconfigure(1, weight=1)

        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(form_frame, width=40, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form_frame, text="Contact #:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.contact_var = tk.StringVar()
        self.contact_entry = ttk.Entry(form_frame, width=40, textvariable=self.contact_var)
        self.contact_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form_frame, text="Address:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.address_var = tk.StringVar()
        self.address_entry = ttk.Entry(form_frame, width=40, textvariable=self.address_var)
        self.address_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        form_button_frame = ttk.Frame(form_frame)
        form_button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 5))

        self.save_button = ttk.Button(form_button_frame, text="Save / Update", command=self.save_or_update_customer)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(form_button_frame, text="Clear Form", command=self.clear_form)
        self.clear_button.pack(side=tk.LEFT, padx=5)


        # --- Customer List Frame (Using Treeview) ---
        list_frame = ttk.LabelFrame(self, text="Existing Customers", padding="10")
        list_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        # Define columns for the Treeview
        customer_columns = ('name', 'contact', 'address')
        self.customer_tree = ttk.Treeview(list_frame, columns=customer_columns, show="headings", selectmode="browse") # Changed selectmode

        # Define headings
        self.customer_tree.heading('name', text='Name')
        self.customer_tree.heading('contact', text='Contact Number')
        self.customer_tree.heading('address', text='Address')

        # Define column properties
        self.customer_tree.column('name', anchor=tk.W, width=150, stretch=True)
        self.customer_tree.column('contact', anchor=tk.W, width=100, stretch=False)
        self.customer_tree.column('address', anchor=tk.W, width=250, stretch=True)

        self.customer_tree.grid(row=0, column=0, sticky="nsew")

        # Add scrollbar
        customer_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.customer_tree.yview)
        self.customer_tree.configure(yscrollcommand=customer_scrollbar.set)
        customer_scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind selection event
        self.customer_tree.bind("<<TreeviewSelect>>", self.on_customer_select) # Bind event

        # --- Bottom Buttons (Delete, Close) ---
        bottom_button_frame = ttk.Frame(self)
        bottom_button_frame.grid(row=2, column=0, pady=10)

        self.delete_button = ttk.Button(bottom_button_frame, text="Delete Selected", command=self.delete_selected_customer)
        self.delete_button.pack(side=tk.LEFT, padx=10)

        close_button = ttk.Button(bottom_button_frame, text="Close", command=self.destroy)
        close_button.pack(side=tk.LEFT, padx=10)

        # --- Initialize ---
        self.selected_customer_id = None # Track selected customer ID
        self.populate_customer_list()
        self.clear_form() # Start with empty fields

    def clear_form(self):
        """Clears the entry fields and selection."""
        self.selected_customer_id = None
        self.name_var.set("")
        self.contact_var.set("")
        self.address_var.set("")
        # Deselect item in treeview
        selection = self.customer_tree.selection()
        if selection:
            self.customer_tree.selection_remove(selection)
        self.name_entry.focus_set()

    def on_customer_select(self, event=None):
        """Populates form fields when a customer is selected in the Treeview."""
        selected_item_iid = self.customer_tree.focus()
        if not selected_item_iid:
            return
        item_data = self.customer_tree.item(selected_item_iid)
        values = item_data['values']
        if values:
            # The iid *is* the CustomerID we stored when populating
            self.selected_customer_id = int(selected_item_iid)
            self.name_var.set(values[0])
            self.contact_var.set(values[1] if values[1] else "")
            self.address_var.set(values[2] if values[2] else "")
        else:
             self.clear_form()

    def save_or_update_customer(self):
        """Adds a new customer or updates the selected existing customer."""
        name = self.name_var.get().strip()
        contact = self.contact_var.get().strip()
        address = self.address_var.get().strip()

        if not name:
            messagebox.showwarning("Missing Name", "Customer Name cannot be empty.", parent=self)
            return
        if name == 'N/A':
             messagebox.showwarning("Invalid Name", "Cannot use 'N/A' as a customer name.", parent=self)
             return

        if self.selected_customer_id is not None:
            # Update existing customer
            print(f"Updating customer ID: {self.selected_customer_id}")
            if db_operations.update_customer_in_db(self.selected_customer_id, name, contact, address):
                messagebox.showinfo("Success", f"Customer '{name}' updated successfully.", parent=self)
                self.populate_customer_list() # Refresh list
                self.clear_form() # Clear form after update
            else:
                # Error message shown by db function
                pass
        else:
            # Add new customer
            print(f"Adding new customer: {name}")
            if db_operations.add_customer_to_db(name, contact, address):
                messagebox.showinfo("Success", f"Customer '{name}' added successfully.", parent=self)
                self.populate_customer_list() # Refresh list
                self.clear_form() # Clear form after add
            else:
                # Error message shown by db function
                pass

    def delete_selected_customer(self):
        """Deletes the customer currently selected in the Treeview."""
        if self.selected_customer_id is None:
             messagebox.showwarning("No Selection", "Please select a customer from the list to delete.", parent=self)
             return
        customer_name = self.name_var.get()
        confirmed = messagebox.askyesno("Confirm Deletion",
                                        f"Are you sure you want to permanently delete customer '{customer_name}' (ID: {self.selected_customer_id})?\n"
                                        "This cannot be undone.", parent=self)
        if not confirmed:
            return
        if db_operations.delete_customer_from_db(self.selected_customer_id):
            messagebox.showinfo("Success", f"Customer '{customer_name}' deleted.", parent=self)
            self.populate_customer_list()
            self.clear_form()
        else:
             messagebox.showerror("Error", f"Failed to delete customer '{customer_name}'.", parent=self)


    def populate_customer_list(self):
        """Fetches and displays the list of customers in the Treeview."""
        for i in self.customer_tree.get_children():
            self.customer_tree.delete(i)
        all_customers = db_operations.fetch_all_customers()
        for customer_data in all_customers:
            cust_id, name, contact, address = customer_data
            display_contact = contact if contact is not None else ""
            display_address = address if address is not None else ""
            # Use CustomerID as the item identifier (iid)
            self.customer_tree.insert("", tk.END, iid=cust_id, values=(name, display_contact, display_address))


# --- New Custom Price Dialog Class ---
class CustomPriceDialog(tk.Toplevel):
    def __init__(self, parent, product_names):
        super().__init__(parent)
        self.parent = parent
        self.product_names = product_names
        self.title("Add Custom Price Item")
        set_window_icon(self) # Set icon for this dialog
        self.result = None
        dialog_width = 350
        dialog_height = 210
        self.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        req_width = self.winfo_reqwidth()
        req_height = self.winfo_reqheight()
        x = parent_x + (parent_width // 2) - (req_width // 2)
        y = parent_y + (parent_height // 2) - (req_height // 2)
        self.geometry(f'+{x}+{y}')
        self.transient(parent)
        self.grab_set()
        self.columnconfigure(1, weight=1)
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
             messagebox.showerror("Invalid Quantity", "Please enter a valid positive whole number for the quantity.", parent=self)
             return
        self.result = (product_name, custom_price, quantity)
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()


# --- Main Application Class ---
class POSApp:
    def __init__(self, root):
        """Initialize the POS Application."""
        self.root = root
        self.root.title("SEASIDE Water Refilling Station - POS")
        app_width = 850
        app_height = 750
        self.root.geometry(f"{app_width}x{app_height}")
        self.root.minsize(700, 600)

        # Use helper function to set icon for main window
        set_window_icon(self.root)

        center_window(self.root, app_width, app_height)

        db_operations.initialize_db()

        self.products = db_operations.fetch_products_from_db()
        self.current_sale = {}
        self.total_amount = 0.0
        self.history_window = None
        self.customer_list_window = None

        # --- Configure Main Layout ---
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=2)
        self.root.rowconfigure(0, weight=1)

        # --- Create Frames ---
        self.product_frame = ttk.Frame(root, padding="10")
        self.sale_frame = ttk.Frame(root, padding="10")
        self.product_frame.grid(row=0, column=0, sticky="nsew")
        self.sale_frame.grid(row=0, column=1, sticky="nsew")

        # Configure product frame grid rows/columns for resizing
        self.product_frame.columnconfigure(0, weight=1)
        self.product_frame.columnconfigure(1, weight=0)
        self.product_frame.rowconfigure(1, weight=1)
        self.product_frame.rowconfigure(2, weight=0)
        self.product_frame.rowconfigure(4, weight=1)
        self.product_frame.rowconfigure(3, weight=0)
        self.product_frame.rowconfigure(5, weight=0)

        # Configure sale frame grid rows/columns for resizing
        self.sale_frame.columnconfigure(0, weight=1)
        self.sale_frame.columnconfigure(1, weight=0)
        self.sale_frame.rowconfigure(1, weight=1)
        self.sale_frame.rowconfigure(0, weight=0)
        self.sale_frame.rowconfigure(2, weight=0)
        self.sale_frame.rowconfigure(3, weight=0)

        # --- Populate Product Frame (Sale Buttons) ---
        ttk.Label(self.product_frame, text="Add to Sale", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky='w')
        self.product_canvas = tk.Canvas(self.product_frame)
        product_scrollbar = ttk.Scrollbar(self.product_frame, orient="vertical", command=self.product_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.product_canvas)
        self.product_canvas.bind('<Configure>', lambda e: self.product_canvas.configure(scrollregion=self.product_canvas.bbox("all")))
        self.product_canvas_window = self.product_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.scrollable_frame.bind('<Configure>', self._configure_scrollable_frame)
        self.product_canvas.configure(yscrollcommand=product_scrollbar.set)
        self.product_canvas.grid(row=1, column=0, sticky="nsew")
        product_scrollbar.grid(row=1, column=1, sticky="ns")
        self.populate_product_buttons()

        # --- Product Management Section ---
        ttk.Separator(self.product_frame, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky='ew', pady=15)
        ttk.Label(self.product_frame, text="Manage Products", font=("Arial", 14, "bold")).grid(row=3, column=0, columnspan=2, pady=(10, 5), sticky='w')

        self.product_list_frame = ttk.Frame(self.product_frame)
        self.product_list_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=5)
        self.product_list_frame.rowconfigure(0, weight=1)
        self.product_list_frame.columnconfigure(0, weight=1)
        self.product_listbox = tk.Listbox(self.product_list_frame, exportselection=False)
        self.product_listbox.grid(row=0, column=0, sticky="nsew")
        product_list_scrollbar = ttk.Scrollbar(self.product_list_frame, orient="vertical", command=self.product_listbox.yview)
        self.product_listbox.configure(yscrollcommand=product_list_scrollbar.set)
        product_list_scrollbar.grid(row=0, column=1, sticky="ns")
        self.populate_product_management_list()

        product_mgmt_button_frame = ttk.Frame(self.product_frame)
        product_mgmt_button_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky='w')
        self.add_product_button = ttk.Button(product_mgmt_button_frame, text="Add New Product", command=self.prompt_new_item)
        self.add_product_button.pack(side=tk.LEFT, padx=5)
        self.edit_product_button = ttk.Button(product_mgmt_button_frame, text="Edit Product", command=self.prompt_edit_item)
        self.edit_product_button.pack(side=tk.LEFT, padx=5)
        self.remove_product_button = ttk.Button(product_mgmt_button_frame, text="Remove Product", command=self.remove_selected_product_permanently)
        self.remove_product_button.pack(side=tk.LEFT, padx=5)
        self.view_customers_button = ttk.Button(product_mgmt_button_frame, text="Manage Customers", command=self.view_customers)
        self.view_customers_button.pack(side=tk.LEFT, padx=5)


        # --- Populate Sale Frame ---
        ttk.Label(self.sale_frame, text="Current Sale", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10, sticky='w')
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
        self.sale_tree.grid(row=1, column=0, sticky="nsew", padx=(5,0), pady=5)
        sale_scrollbar = ttk.Scrollbar(self.sale_frame, orient="vertical", command=self.sale_tree.yview)
        self.sale_tree.configure(yscrollcommand=sale_scrollbar.set)
        sale_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0,5), pady=5)

        # --- Finalize Button and Total Label Frame (Row 2) ---
        finalize_total_frame = ttk.Frame(self.sale_frame)
        finalize_total_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        finalize_total_frame.columnconfigure(0, weight=1)
        finalize_total_frame.columnconfigure(1, weight=0)
        finalize_total_frame.columnconfigure(2, weight=0)

        self.finalize_button = ttk.Button(finalize_total_frame, text="Finalize Sale", command=self.finalize_sale)
        self.finalize_button.grid(row=0, column=1, padx=(5, 10), sticky="e")

        self.total_label = ttk.Label(finalize_total_frame, text=f"{db_operations.CURRENCY_SYMBOL}0.00", font=("Arial", 14, "bold"))
        self.total_label.grid(row=0, column=2, padx=(0, 5), sticky="e")


        # --- Other Sale Action Buttons Frame (Row 3) ---
        other_sale_actions_frame = ttk.Frame(self.sale_frame)
        other_sale_actions_frame.grid(row=3, column=0, columnspan=2, pady=(0, 10), sticky="e")

        self.history_button = ttk.Button(other_sale_actions_frame, text="View History", command=self.view_sales_history)
        self.history_button.pack(side=tk.RIGHT, padx=5)

        self.clear_button = ttk.Button(other_sale_actions_frame, text="Clear Sale", command=self.clear_sale)
        self.clear_button.pack(side=tk.RIGHT, padx=5)

        self.remove_item_button = ttk.Button(other_sale_actions_frame, text="Remove Item", command=self.remove_selected_item_from_sale)
        self.remove_item_button.pack(side=tk.RIGHT, padx=5)

        self.decrease_qty_button = ttk.Button(other_sale_actions_frame, text="- Qty", command=self.decrease_item_quantity)
        self.decrease_qty_button.pack(side=tk.RIGHT, padx=5)


        self.update_sale_display()

    # --- Helper for Scrollable Frame Resizing ---
    def _configure_scrollable_frame(self, event):
        """Reset the scroll region to encompass the inner frame"""
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
    def populate_product_buttons(self):
        """Clears and repopulates the product buttons for adding to sale."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        # --- Set max_cols to 4 ---
        max_cols = 4
        # Configure 4 columns in the scrollable frame to have equal weight
        for i in range(max_cols):
            self.scrollable_frame.columnconfigure(i, weight=1)

        row_num, col_num = 0, 0
        sorted_products = sorted(self.products.items())
        for name, price in sorted_products:
            btn_text = f"{name}\n({db_operations.CURRENCY_SYMBOL}{price:.2f})"
            btn = ttk.Button(
                self.scrollable_frame,
                text=btn_text,
                command=lambda n=name: self.add_item(n),
                # width=15 # Remove fixed width
            )
            btn.grid(row=row_num, column=col_num, padx=2, pady=2, sticky="ew") # Reduced padding slightly
            col_num += 1
            if col_num >= max_cols:
                col_num = 0
                row_num += 1
        # Add Custom Price Button below the grid
        custom_button = ttk.Button(self.scrollable_frame, text="Custom Price Item", command=self.prompt_custom_item)
        custom_button.grid(row=row_num + 1, column=0, columnspan=max_cols, pady=(10, 5), sticky='ew') # Adjusted padding

        self.scrollable_frame.update_idletasks()
        self.product_canvas.configure(scrollregion=self.product_canvas.bbox("all"))


    def populate_product_management_list(self):
        """Clears and repopulates the product management listbox."""
        self.product_listbox.delete(0, tk.END)
        sorted_products = sorted(self.products.items())
        for name, price in sorted_products:
            self.product_listbox.insert(tk.END, f"{name} ({db_operations.CURRENCY_SYMBOL}{price:.2f})")

    def _get_selected_product_details(self):
        """Helper method to get the name and price of the selected product in the listbox."""
        selection_indices = self.product_listbox.curselection()
        if not selection_indices:
            messagebox.showwarning("No Selection", "Please select a product from the 'Manage Products' list first.")
            return None, None
        selected_index = selection_indices[0]
        selected_text = self.product_listbox.get(selected_index)
        try:
            parts = selected_text.split(f' ({db_operations.CURRENCY_SYMBOL}')
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
        name = simpledialog.askstring("New Product", "Enter product name:")
        if not name: return
        if name in self.products:
             messagebox.showwarning("Product Exists", f"Product '{name}' already exists.")
             return
        price_str = simpledialog.askstring("New Product", f"Enter price for {name}:")
        if not price_str: return
        try:
            price = float(price_str)
            if price < 0: raise ValueError("Price cannot be negative.")
            if db_operations.insert_product_to_db(name, price):
                self.products[name] = price
                self.populate_product_buttons()
                self.populate_product_management_list()
                print(f"Added new product to DB and UI: {name} - {db_operations.CURRENCY_SYMBOL}{price:.2f}")
                messagebox.showinfo("Success", f"Product '{name}' added successfully.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Invalid price entered. Please enter a valid number.")

    def prompt_edit_item(self):
        """Gets selected product, prompts for new details, updates DB and UI."""
        original_name, original_price = self._get_selected_product_details()
        if original_name is None: return
        new_name = simpledialog.askstring("Edit Product", "Enter new product name:", initialvalue=original_name)
        if not new_name: return
        new_price_str = simpledialog.askstring("Edit Product", f"Enter new price for {new_name}:", initialvalue=f"{original_price:.2f}")
        if not new_price_str: return
        try:
            new_price = float(new_price_str)
            if new_price < 0: raise ValueError("Price cannot be negative.")
            if new_name != original_name and new_name in self.products:
                 messagebox.showerror("Edit Error", f"Cannot rename to '{new_name}'.\nA product with that name already exists.")
                 return
            if db_operations.update_product_in_db(original_name, new_name, new_price):
                if original_name in self.products:
                     del self.products[original_name]
                self.products[new_name] = new_price
                self.populate_product_buttons()
                self.populate_product_management_list()
                messagebox.showinfo("Success", f"Product '{original_name}' updated successfully.")
        except ValueError:
            messagebox.showerror("Invalid Input", "Invalid price entered. Please enter a valid number.")

    def remove_selected_product_permanently(self):
        """Gets selection from listbox, confirms, deletes from DB and updates UI."""
        product_name, _ = self._get_selected_product_details()
        if product_name is None: return
        confirmed = messagebox.askyesno("Confirm Permanent Deletion",
                                        f"Are you sure you want to permanently delete '{product_name}'?\n"
                                        "This cannot be undone.")
        if not confirmed: return
        if db_operations.delete_product_from_db(product_name):
            if product_name in self.products:
                 del self.products[product_name]
            self.populate_product_buttons()
            self.populate_product_management_list()
            messagebox.showinfo("Success", f"Product '{product_name}' permanently deleted.")

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
            price_str = f"{db_operations.CURRENCY_SYMBOL}{price:.2f}"
            subtotal_str = f"{db_operations.CURRENCY_SYMBOL}{subtotal:.2f}"
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

        self.total_label.config(text=f"Total: {db_operations.CURRENCY_SYMBOL}{self.total_amount:.2f}")

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
            price_str = f"{db_operations.CURRENCY_SYMBOL}{price:.2f}"
            subtotal_str = f"{db_operations.CURRENCY_SYMBOL}{subtotal:.2f}"
            receipt += "{:<18} {:>3d} {:>7} {:>8}\n".format(name[:18], qty, price_str, subtotal_str)
        receipt += "======================================\n"
        total_str = f"{db_operations.CURRENCY_SYMBOL}{self.total_amount:.2f}"
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
            self.history_window = SalesHistoryWindow(self.root)
            self.history_window.grab_set()
        else:
            self.history_window.deiconify()
            self.history_window.lift()
            self.history_window.focus_set()

    def view_customers(self):
        """Opens the customer management window."""
        if self.customer_list_window is None or not tk.Toplevel.winfo_exists(self.customer_list_window):
            self.customer_list_window = CustomerListWindow(self.root)
            self.customer_list_window.grab_set()
        else:
            self.customer_list_window.deiconify()
            self.customer_list_window.lift()
            self.customer_list_window.focus_set()
