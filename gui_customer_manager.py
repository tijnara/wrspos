import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog # Added for file dialogs
import csv # Added for CSV export
import datetime # Added for timestamp formatting
import logging # Added logging

# Import necessary modules
import db_operations
import gui_utils # Import the utils module

# --- Customer List Window Class ---
class CustomerListWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent # Store parent reference
        self.title("Manage Customers")
        gui_utils.set_window_icon(self) # Use helper function

        win_width = 750 # Increased width
        win_height = 750 # Increased height
        self.geometry(f"{win_width}x{win_height}")
        self.minsize(600, 550) # Increased min size

        gui_utils.center_window(self, win_width, win_height) # Use helper function
        self.transient(parent)
        self.grab_set()

        # --- Configure Grid Layout ---
        self.columnconfigure(0, weight=1) # Allow main content column to expand
        # Row weights: Form, Search, Customer List, History, Buttons
        self.rowconfigure(0, weight=0) # Form frame fixed height
        self.rowconfigure(1, weight=0) # Search frame fixed height
        self.rowconfigure(2, weight=1) # Customer List Treeview frame (expandable)
        self.rowconfigure(3, weight=1) # Purchase History Treeview frame (expandable)
        self.rowconfigure(4, weight=0) # Buttons fixed height

        # --- Add/Edit Customer Form Frame (Row 0) ---
        self._setup_form_frame()

        # --- Search Frame (Row 1) ---
        self._setup_search_frame()

        # --- Customer List Frame (Row 2) ---
        self._setup_customer_list_tree()

        # --- NEW: Purchase History Frame (Row 3) ---
        self._setup_purchase_history_tree()

        # --- Bottom Buttons (Row 4) ---
        self._setup_bottom_buttons()

        # --- Initialize ---
        self.selected_customer_id = None # Track the actual DB ID internally
        self.populate_customer_list() # Initial population (no search term)
        self.clear_form() # Clears form and history

        # --- Bind Escape key ---
        self.bind('<Escape>', lambda event=None: self.destroy())

    # --- UI Setup Methods ---

    def _setup_form_frame(self):
        """Sets up the Add/Edit customer form."""
        form_frame = ttk.LabelFrame(self, text="Customer Details", padding="10")
        form_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        form_frame.columnconfigure(1, weight=1) # Allow entry fields to expand

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

    def _setup_search_frame(self):
        """Sets up the customer search area."""
        search_frame = ttk.Frame(self, padding=(10, 0, 10, 5))
        search_frame.grid(row=1, column=0, sticky="ew")
        search_frame.columnconfigure(1, weight=1) # Allow search entry to expand

        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.search_entry.bind("<Return>", self.filter_customer_list) # Bind Enter key

        search_button = ttk.Button(search_frame, text="Search", command=self.filter_customer_list)
        search_button.grid(row=0, column=2, padx=(5, 0))

    def _setup_customer_list_tree(self):
        """Sets up the treeview for displaying the customer list."""
        list_frame = ttk.LabelFrame(self, text="Existing Customers", padding="10")
        list_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.customer_columns = ('seq_no', 'name', 'contact', 'address') # Store for export
        self.customer_tree = ttk.Treeview(list_frame, columns=self.customer_columns, show="headings", selectmode="browse")

        self.customer_tree.heading('seq_no', text='Cust #')
        self.customer_tree.heading('name', text='Name')
        self.customer_tree.heading('contact', text='Contact Number')
        self.customer_tree.heading('address', text='Address')

        self.customer_tree.column('seq_no', anchor=tk.W, width=50, stretch=False)
        self.customer_tree.column('name', anchor=tk.W, width=150, stretch=True)
        self.customer_tree.column('contact', anchor=tk.W, width=100, stretch=False)
        self.customer_tree.column('address', anchor=tk.W, width=250, stretch=True)

        self.customer_tree.grid(row=0, column=0, sticky="nsew")

        customer_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.customer_tree.yview)
        self.customer_tree.configure(yscrollcommand=customer_scrollbar.set)
        customer_scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind selection event
        self.customer_tree.bind("<<TreeviewSelect>>", self.on_customer_select)

    def _setup_purchase_history_tree(self):
        """Sets up the treeview for displaying customer purchase history."""
        history_frame = ttk.LabelFrame(self, text="Purchase History for Selected Customer", padding="10")
        history_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        history_frame.rowconfigure(0, weight=1)
        history_frame.columnconfigure(0, weight=1)

        self.history_columns = ('hist_timestamp', 'hist_product', 'hist_quantity', 'hist_price', 'hist_subtotal')
        self.purchase_history_tree = ttk.Treeview(history_frame, columns=self.history_columns, show="headings", selectmode="none") # No selection needed here

        # Define headings
        self.purchase_history_tree.heading('hist_timestamp', text='Date/Time')
        self.purchase_history_tree.heading('hist_product', text='Product Name')
        self.purchase_history_tree.heading('hist_quantity', text='Qty')
        self.purchase_history_tree.heading('hist_price', text='Price')
        self.purchase_history_tree.heading('hist_subtotal', text='Subtotal')

        # Define column properties
        self.purchase_history_tree.column('hist_timestamp', anchor=tk.W, width=140, stretch=False)
        self.purchase_history_tree.column('hist_product', anchor=tk.W, width=200, stretch=True)
        self.purchase_history_tree.column('hist_quantity', anchor=tk.CENTER, width=40, stretch=False)
        self.purchase_history_tree.column('hist_price', anchor=tk.E, width=80, stretch=False)
        self.purchase_history_tree.column('hist_subtotal', anchor=tk.E, width=90, stretch=False)

        self.purchase_history_tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        history_scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.purchase_history_tree.yview)
        self.purchase_history_tree.configure(yscrollcommand=history_scrollbar.set)
        history_scrollbar.grid(row=0, column=1, sticky="ns")

    def _setup_bottom_buttons(self):
        """Sets up the main action buttons at the bottom."""
        bottom_button_frame = ttk.Frame(self)
        bottom_button_frame.grid(row=4, column=0, pady=10) # Now row 4

        export_button = ttk.Button(bottom_button_frame, text="Export Customers", command=self.export_customers_to_csv)
        export_button.pack(side=tk.LEFT, padx=10)

        self.delete_button = ttk.Button(bottom_button_frame, text="Delete Selected", command=self.delete_selected_customer)
        self.delete_button.pack(side=tk.LEFT, padx=10)

        close_button = ttk.Button(bottom_button_frame, text="Close", command=self.destroy)
        close_button.pack(side=tk.LEFT, padx=10)

    # --- Logic Methods ---

    def filter_customer_list(self, event=None):
        """Filters the customer list based on the search entry."""
        search_term = self.search_var.get()
        logging.debug(f"Filtering customer list with term: '{search_term}'")
        self.populate_customer_list(search_term)
        self.clear_form() # Clear form and history when searching

    def clear_form(self):
        """Clears the entry fields, selection, and purchase history."""
        logging.debug("Clearing customer form and history.")
        self.selected_customer_id = None
        self.name_var.set("")
        self.contact_var.set("")
        self.address_var.set("")
        # self.search_var.set("") # Keep search term when clearing form after save/delete
        selection = self.customer_tree.selection()
        if selection:
            self.customer_tree.selection_remove(selection)

        # Clear the purchase history tree
        for i in self.purchase_history_tree.get_children():
            self.purchase_history_tree.delete(i)

        self.name_entry.focus_set()

    def on_customer_select(self, event=None):
        """Populates form fields and purchase history when a customer is selected."""
        selected_item_iid = self.customer_tree.focus()
        if not selected_item_iid:
            self._populate_purchase_history([]) # Clear history if no selection
            return

        item_data = self.customer_tree.item(selected_item_iid)
        values = item_data['values']

        if values:
            try:
                self.selected_customer_id = int(selected_item_iid) # The iid *is* the CustomerID
                customer_name = values[1] # Get name from the selected row values

                # Populate form fields
                self.name_var.set(customer_name)
                self.contact_var.set(values[2] if values[2] else "")
                self.address_var.set(values[3] if values[3] else "")

                # Fetch and display purchase history
                logging.info(f"Fetching purchase history for customer: '{customer_name}' (ID: {self.selected_customer_id})")
                history_data = db_operations.fetch_all_customer_purchase_details(customer_name)
                self._populate_purchase_history(history_data)

            except (ValueError, IndexError) as e:
                 logging.error(f"Error processing customer selection: {e}. IID: {selected_item_iid}, Values: {values}")
                 self.clear_form() # Clear everything on error
                 self._populate_purchase_history([])
        else:
             logging.warning(f"No values found for selected customer item: {selected_item_iid}")
             self.clear_form()
             self._populate_purchase_history([])

    def _populate_purchase_history(self, history_data):
        """Clears and populates the purchase history treeview."""
        logging.debug(f"Populating purchase history tree with {len(history_data)} items.")
        # Clear existing items
        for i in self.purchase_history_tree.get_children():
            self.purchase_history_tree.delete(i)

        if not history_data:
            self.purchase_history_tree.insert("", tk.END, values=("No purchase history found", "", "", "", ""))
            return

        # Populate with new data
        for item in history_data:
            timestamp_str, product_name, qty, price, subtotal = item
            try:
                # Format timestamp nicely
                dt_obj = datetime.datetime.fromisoformat(timestamp_str)
                display_ts = dt_obj.strftime('%Y-%m-%d %H:%M') # Shorter format
            except (ValueError, TypeError):
                display_ts = timestamp_str # Fallback

            price_display = f"{gui_utils.CURRENCY_SYMBOL}{price:.2f}"
            subtotal_display = f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"

            self.purchase_history_tree.insert("", tk.END, values=(display_ts, product_name, qty, price_display, subtotal_display))
        logging.debug("Purchase history tree populated.")


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

        # Check for existing name (case-insensitive) before saving
        all_customers_data = db_operations.fetch_all_customers()
        name_lower = name.lower()
        is_duplicate = False
        for cust_id, cust_name, _, _ in all_customers_data:
            if cust_name.lower() == name_lower:
                # Allow saving if it's the currently selected customer being updated
                if self.selected_customer_id is not None and cust_id == self.selected_customer_id:
                    continue
                else:
                    is_duplicate = True
                    break

        if is_duplicate:
            logging.warning(f"Save/Update failed: Duplicate customer name '{name}'.")
            messagebox.showwarning("Duplicate Name", f"A customer named '{name}' already exists.", parent=self)
            return

        # Proceed with update or add
        if self.selected_customer_id is not None:
            # Update existing customer
            logging.info(f"Attempting to update customer ID: {self.selected_customer_id} to Name: '{name}'")
            if db_operations.update_customer_in_db(self.selected_customer_id, name, contact, address):
                messagebox.showinfo("Success", f"Customer '{name}' updated successfully.", parent=self)
                self.filter_customer_list() # Refresh list with current filter
                self.clear_form() # Clear form fields & history
            # else: db_operations shows error message
        else:
            # Add new customer
            logging.info(f"Attempting to add new customer: '{name}'")
            if db_operations.add_customer_to_db(name, contact, address):
                messagebox.showinfo("Success", f"Customer '{name}' added successfully.", parent=self)
                self.filter_customer_list() # Refresh list with current filter
                self.clear_form() # Clear form fields & history
            # else: db_operations shows error message

    def delete_selected_customer(self):
        """Deletes the customer currently selected in the Treeview."""
        if self.selected_customer_id is None:
             messagebox.showwarning("No Selection", "Please select a customer from the list to delete.", parent=self)
             return

        customer_name = self.name_var.get() # Get name from form for confirmation message
        logging.warning(f"Confirmation requested for deleting customer '{customer_name}' (ID: {self.selected_customer_id}).")
        confirmed = messagebox.askyesno("Confirm Deletion",
                                        f"Are you sure you want to permanently delete customer '{customer_name}' (ID: {self.selected_customer_id})?\n"
                                        "This cannot be undone.", parent=self)
        if not confirmed:
            logging.info("Customer deletion cancelled.")
            return

        logging.warning(f"Attempting deletion of customer ID: {self.selected_customer_id}")
        if db_operations.delete_customer_from_db(self.selected_customer_id):
            messagebox.showinfo("Success", f"Customer '{customer_name}' deleted.", parent=self)
            self.filter_customer_list() # Refresh list with current filter
            self.clear_form() # Clear form fields & history
        # else: db_operations shows error message


    def populate_customer_list(self, search_term=""):
        """Fetches and displays the list of customers, optionally filtering."""
        logging.debug(f"Populating customer list (Search: '{search_term}').")
        for i in self.customer_tree.get_children():
            self.customer_tree.delete(i)

        all_customers = db_operations.fetch_all_customers() # Sorted newest first by DB query
        filtered_customers = []

        if search_term:
            term_lower = search_term.lower()
            for cust_id, name, contact, address in all_customers:
                contact_str = contact if contact else ""
                address_str = address if address else ""
                if (term_lower in name.lower() or
                    term_lower in contact_str.lower() or
                    term_lower in address_str.lower()):
                    filtered_customers.append((cust_id, name, contact, address))
        else:
            filtered_customers = all_customers

        # Populate the treeview with filtered results (newest first display)
        seq_counter = 0
        for customer_data in filtered_customers:
            seq_counter += 1
            cust_id, name, contact, address = customer_data
            display_contact = contact if contact is not None else ""
            display_address = address if address is not None else ""
            # Insert seq_counter, use cust_id as the item identifier (iid)
            self.customer_tree.insert("", tk.END, iid=cust_id, values=(seq_counter, name, display_contact, display_address))
        logging.debug(f"Customer list populated with {len(filtered_customers)} items.")

    def export_customers_to_csv(self):
        """Exports the currently displayed customer list to a CSV file."""
        logging.info("Exporting customer list to CSV.")
        if not self.customer_tree.get_children():
            messagebox.showwarning("No Data", "There are no customers to export.", parent=self)
            return

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Customer List As",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path:
            logging.info("Customer export cancelled.")
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                headers = [self.customer_tree.heading(col)['text'] for col in self.customer_columns]
                writer.writerow(headers)
                # Iterate in display order
                for item_id in self.customer_tree.get_children():
                    row_values = self.customer_tree.item(item_id)['values']
                    writer.writerow(row_values)

            logging.info(f"Customer list exported successfully to {file_path}")
            messagebox.showinfo("Export Successful", f"Customer list exported successfully to:\n{file_path}", parent=self)
        except Exception as e:
            logging.exception(f"Error exporting customer list to CSV: {file_path}")
            messagebox.showerror("Export Failed", f"Could not export customer list.\nError: {e}", parent=self)

