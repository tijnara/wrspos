import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import csv
import datetime
import logging

import db_operations
import gui_utils


class CustomerListWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Manage Customers")
        gui_utils.set_window_icon(self)

        win_width = 750
        win_height = 750
        self.geometry(f"{win_width}x{win_height}")
        self.minsize(600, 550)

        self.resizable(True, True)

        gui_utils.center_window(self, win_width, win_height)
        self.transient(parent)
        self.grab_set()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=0)

        self._setup_form_frame()
        self._setup_search_frame()
        self._setup_customer_list_tree()  # Keyboard bindings will be added here
        self._setup_purchase_history_tree()
        self._setup_bottom_buttons()

        self.selected_customer_id = None
        self.populate_customer_list()
        self.clear_form()

        self.bind('<Escape>', lambda event=None: self.destroy())

    def _setup_form_frame(self):
        form_frame = ttk.LabelFrame(self, text="Customer Details", padding="10")
        form_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
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

    def _setup_search_frame(self):
        search_frame = ttk.Frame(self, padding=(10, 0, 10, 5))
        search_frame.grid(row=1, column=0, sticky="ew")
        search_frame.columnconfigure(1, weight=1)

        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.search_entry.bind("<Return>", self.filter_customer_list)

        search_button = ttk.Button(search_frame, text="Search", command=self.filter_customer_list)
        search_button.grid(row=0, column=2, padx=(5, 0))

    def _setup_customer_list_tree(self):
        list_frame = ttk.LabelFrame(self, text="Existing Customers", padding="10")
        list_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.customer_columns = ('seq_no', 'name', 'contact', 'address')
        self.customer_tree = ttk.Treeview(list_frame, columns=self.customer_columns, show="headings",
                                          selectmode="browse")

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

        # --- Keyboard Navigation Bindings for customer_tree ---
        self.customer_tree.bind("<<TreeviewSelect>>", self.on_customer_select)  # Existing selection binding
        self.customer_tree.bind("<Up>", self._handle_customer_tree_nav)
        self.customer_tree.bind("<Down>", self._handle_customer_tree_nav)
        self.customer_tree.bind("<Return>", self._handle_customer_tree_activate)
        self.customer_tree.bind("<space>", self._handle_customer_tree_activate)
        # Delete key for customer deletion (optional, as there's a button)
        self.customer_tree.bind("<Delete>", self._handle_customer_tree_delete)

    def _setup_purchase_history_tree(self):
        history_frame = ttk.LabelFrame(self, text="Purchase History for Selected Customer", padding="10")
        history_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        history_frame.rowconfigure(0, weight=1)
        history_frame.columnconfigure(0, weight=1)

        self.history_columns = ('hist_timestamp', 'hist_product', 'hist_quantity', 'hist_price', 'hist_subtotal')
        # Changed selectmode to "browse" to allow keyboard navigation if desired later, though no actions are bound yet.
        self.purchase_history_tree = ttk.Treeview(history_frame, columns=self.history_columns, show="headings",
                                                  selectmode="browse")

        self.purchase_history_tree.heading('hist_timestamp', text='Date/Time')
        self.purchase_history_tree.heading('hist_product', text='Product Name')
        self.purchase_history_tree.heading('hist_quantity', text='Qty')
        self.purchase_history_tree.heading('hist_price', text='Price')
        self.purchase_history_tree.heading('hist_subtotal', text='Subtotal')

        self.purchase_history_tree.column('hist_timestamp', anchor=tk.W, width=140, stretch=False)
        self.purchase_history_tree.column('hist_product', anchor=tk.W, width=200, stretch=True)
        self.purchase_history_tree.column('hist_quantity', anchor=tk.CENTER, width=40, stretch=False)
        self.purchase_history_tree.column('hist_price', anchor=tk.E, width=80, stretch=False)
        self.purchase_history_tree.column('hist_subtotal', anchor=tk.E, width=90, stretch=False)
        self.purchase_history_tree.grid(row=0, column=0, sticky="nsew")

        history_scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.purchase_history_tree.yview)
        self.purchase_history_tree.configure(yscrollcommand=history_scrollbar.set)
        history_scrollbar.grid(row=0, column=1, sticky="ns")

    def _setup_bottom_buttons(self):
        bottom_button_frame = ttk.Frame(self)
        bottom_button_frame.grid(row=4, column=0, pady=10)

        export_button = ttk.Button(bottom_button_frame, text="Export Customers", command=self.export_customers_to_csv)
        export_button.pack(side=tk.LEFT, padx=10)

        self.delete_button = ttk.Button(bottom_button_frame, text="Delete Selected",
                                        command=self.delete_selected_customer)
        self.delete_button.pack(side=tk.LEFT, padx=10)

        close_button = ttk.Button(bottom_button_frame, text="Close", command=self.destroy)
        close_button.pack(side=tk.LEFT, padx=10)

    # --- NEW Keyboard Navigation Handlers for customer_tree ---
    def _handle_customer_tree_nav(self, event):
        """Handles Up/Down arrow key navigation in the customer_tree."""
        tree = event.widget
        focused_item = tree.focus()  # Get current focused item (which is also the selected one in "browse" mode)

        if not focused_item:  # If nothing is focused/selected, select the first item
            children = tree.get_children()
            if children:
                tree.focus(children[0])
                tree.selection_set(children[0])
                # self.on_customer_select() # Trigger selection logic
        else:
            if event.keysym == "Up":
                prev_item = tree.prev(focused_item)
                if prev_item:
                    tree.focus(prev_item)
                    tree.selection_set(prev_item)
                    # self.on_customer_select() # Trigger selection logic
            elif event.keysym == "Down":
                next_item = tree.next(focused_item)
                if next_item:
                    tree.focus(next_item)
                    tree.selection_set(next_item)
                    # self.on_customer_select() # Trigger selection logic

        # Ensure the newly focused item is visible
        new_focus = tree.focus()
        if new_focus:
            tree.see(new_focus)
            # Manually call on_customer_select because TreeviewSelect event might not fire for programmatic focus/selection
            self.on_customer_select()

        return "break"  # Prevents default Tkinter handling for arrow keys in Treeview

    def _handle_customer_tree_activate(self, event):
        """Handles Return/Space key press on the customer_tree."""
        logging.debug(f"Customer tree activate event triggered by {event.keysym}")
        focused_item = self.customer_tree.focus()
        if focused_item:
            # Current behavior is that on_customer_select already populates the form.
            # We can enhance this by, for example, moving focus to the first form field.
            self.on_customer_select()  # Ensure data is populated
            if hasattr(self, 'name_entry'):
                self.name_entry.focus_set()  # Set focus to the name entry field
                self.name_entry.select_range(0, tk.END)
        return "break"

    def _handle_customer_tree_delete(self, event):
        """Handles Delete key press on the customer_tree."""
        logging.debug("Delete key pressed on customer tree.")
        focused_item = self.customer_tree.focus()
        if focused_item:
            # Ensure the form is populated with the customer to be deleted for confirmation message
            self.on_customer_select()
            self.delete_selected_customer()  # Call existing delete method
        return "break"

    # --- Existing Logic Methods (some might be slightly adjusted if needed) ---

    def filter_customer_list(self, event=None):
        search_term = self.search_var.get()
        logging.debug(f"Filtering customer list with term: '{search_term}'")
        self.populate_customer_list(search_term)
        self.clear_form()

    def clear_form(self):
        logging.debug("Clearing customer form and history.")
        self.selected_customer_id = None
        self.name_var.set("")
        self.contact_var.set("")
        self.address_var.set("")
        selection = self.customer_tree.selection()
        if selection:
            self.customer_tree.selection_remove(selection)  # Clear visual selection
            self.customer_tree.focus("")  # Remove focus from any item

        for i in self.purchase_history_tree.get_children():
            self.purchase_history_tree.delete(i)

        # Do not set focus here if it's called after an action that moves focus elsewhere
        # self.name_entry.focus_set()

    def on_customer_select(self, event=None):
        """Populates form fields and purchase history when a customer is selected."""
        # This method is now also called by keyboard navigation handlers
        selected_item_iid = self.customer_tree.focus()  # Use focus as it's set by nav handlers

        if not selected_item_iid:
            # If focus is lost or no item is focused, clear the form and history
            # This can happen if the list is empty or after a delete
            if not self.customer_tree.get_children():  # Check if tree is actually empty
                self.clear_form()
                self._populate_purchase_history([])
            return

        item_data = self.customer_tree.item(selected_item_iid)
        values = item_data.get('values')  # Use .get for safety

        if values and len(values) >= 4:  # Ensure values list is valid
            try:
                # The iid *is* the CustomerID if set correctly during population
                self.selected_customer_id = int(selected_item_iid)
                customer_name = values[1]

                self.name_var.set(customer_name)
                self.contact_var.set(values[2] if values[2] else "")
                self.address_var.set(values[3] if values[3] else "")

                logging.info(
                    f"Fetching purchase history for customer: '{customer_name}' (ID: {self.selected_customer_id})")
                history_data = db_operations.fetch_all_customer_purchase_details(customer_name)
                self._populate_purchase_history(history_data)

            except (ValueError, IndexError, TypeError) as e:  # Added TypeError
                logging.error(f"Error processing customer selection: {e}. IID: {selected_item_iid}, Values: {values}")
                # Clear form and history on error to avoid inconsistent state
                current_search = self.search_var.get()  # Preserve search term
                self.clear_form()
                self.search_var.set(current_search)  # Restore search term
                self._populate_purchase_history([])
        else:
            logging.warning(
                f"No valid values found for selected customer item: {selected_item_iid}. Item data: {item_data}")
            # Potentially clear form if selection is invalid
            # self.clear_form()
            # self._populate_purchase_history([])

    def _populate_purchase_history(self, history_data):
        logging.debug(f"Populating purchase history tree with {len(history_data)} items.")
        for i in self.purchase_history_tree.get_children():
            self.purchase_history_tree.delete(i)

        if not history_data:
            self.purchase_history_tree.insert("", tk.END, values=("No purchase history found", "", "", "", ""))
            return

        for item in history_data:
            timestamp_str, product_name, qty, price, subtotal = item
            try:
                dt_obj = datetime.datetime.fromisoformat(timestamp_str)
                display_ts = dt_obj.strftime('%Y-%m-%d %H:%M')
            except (ValueError, TypeError):
                display_ts = timestamp_str

            price_display = f"{gui_utils.CURRENCY_SYMBOL}{price:.2f}"
            subtotal_display = f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"
            self.purchase_history_tree.insert("", tk.END,
                                              values=(display_ts, product_name, qty, price_display, subtotal_display))
        logging.debug("Purchase history tree populated.")

    def save_or_update_customer(self):
        name = self.name_var.get().strip()
        contact = self.contact_var.get().strip()
        address = self.address_var.get().strip()

        if not name:
            messagebox.showwarning("Missing Name", "Customer Name cannot be empty.", parent=self)
            self.name_entry.focus_set()
            return
        if name == 'N/A':
            messagebox.showwarning("Invalid Name", "Cannot use 'N/A' as a customer name.", parent=self)
            self.name_entry.focus_set()
            return

        all_customers_data = db_operations.fetch_all_customers()
        name_lower = name.lower()
        is_duplicate = False
        for cust_id, cust_name, _, _ in all_customers_data:
            if cust_name.lower() == name_lower:
                if self.selected_customer_id is not None and cust_id == self.selected_customer_id:
                    continue
                else:
                    is_duplicate = True
                    break
        if is_duplicate:
            logging.warning(f"Save/Update failed: Duplicate customer name '{name}'.")
            messagebox.showwarning("Duplicate Name", f"A customer named '{name}' already exists.", parent=self)
            self.name_entry.focus_set()
            return

        current_search_term = self.search_var.get()  # Preserve search term

        if self.selected_customer_id is not None:
            logging.info(f"Attempting to update customer ID: {self.selected_customer_id} to Name: '{name}'")
            if db_operations.update_customer_in_db(self.selected_customer_id, name, contact, address):
                messagebox.showinfo("Success", f"Customer '{name}' updated successfully.", parent=self)
                self.populate_customer_list(current_search_term)
                self.clear_form()
                self.search_var.set(current_search_term)  # Restore search term
            # else: db_operations shows error message
        else:
            logging.info(f"Attempting to add new customer: '{name}'")
            if db_operations.add_customer_to_db(name, contact, address):
                messagebox.showinfo("Success", f"Customer '{name}' added successfully.", parent=self)
                self.populate_customer_list(current_search_term)
                self.clear_form()
                self.search_var.set(current_search_term)  # Restore search term
            # else: db_operations shows error message
        self.search_entry.focus_set()  # Return focus to search after action

    def delete_selected_customer(self):
        if self.selected_customer_id is None:
            messagebox.showwarning("No Selection", "Please select a customer from the list to delete.", parent=self)
            return

        customer_name_for_msg = self.name_var.get()  # Get name from form for confirmation
        if not customer_name_for_msg and self.customer_tree.focus():  # Fallback if form was cleared
            item_data = self.customer_tree.item(self.customer_tree.focus())
            values = item_data.get('values')
            if values and len(values) > 1:
                customer_name_for_msg = values[1]

        logging.warning(
            f"Confirmation requested for deleting customer '{customer_name_for_msg}' (ID: {self.selected_customer_id}).")
        confirmed = messagebox.askyesno("Confirm Deletion",
                                        f"Are you sure you want to permanently delete customer '{customer_name_for_msg}' (ID: {self.selected_customer_id})?\n"
                                        "This cannot be undone.", parent=self)
        if not confirmed:
            logging.info("Customer deletion cancelled.")
            return

        current_search_term = self.search_var.get()  # Preserve search term

        logging.warning(f"Attempting deletion of customer ID: {self.selected_customer_id}")
        if db_operations.delete_customer_from_db(self.selected_customer_id):
            messagebox.showinfo("Success", f"Customer '{customer_name_for_msg}' deleted.", parent=self)
            self.populate_customer_list(current_search_term)
            self.clear_form()
            self.search_var.set(current_search_term)  # Restore search term
        # else: db_operations shows error message
        self.search_entry.focus_set()  # Return focus to search after action

    def populate_customer_list(self, search_term=""):
        logging.debug(f"Populating customer list (Search: '{search_term}').")

        # Store current selection/focus to try and restore it
        current_focus_id = self.customer_tree.focus()

        for i in self.customer_tree.get_children():
            self.customer_tree.delete(i)

        all_customers = db_operations.fetch_all_customers()
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

        seq_counter = 0
        new_focus_candidate = None
        for customer_data in filtered_customers:
            seq_counter += 1
            cust_id, name, contact, address = customer_data
            display_contact = contact if contact is not None else ""
            display_address = address if address is not None else ""
            self.customer_tree.insert("", tk.END, iid=str(cust_id), values=(seq_counter, name, display_contact,
                                                                            display_address))  # Ensure iid is string
            if str(cust_id) == current_focus_id:
                new_focus_candidate = str(cust_id)

        if new_focus_candidate:
            self.customer_tree.focus(new_focus_candidate)
            self.customer_tree.selection_set(new_focus_candidate)
            self.customer_tree.see(new_focus_candidate)  # Ensure visible
        elif filtered_customers:  # If no old focus, but list is not empty, select first
            first_item_id = str(filtered_customers[0][0])
            self.customer_tree.focus(first_item_id)
            self.customer_tree.selection_set(first_item_id)
            self.customer_tree.see(first_item_id)
        else:  # List is empty
            self.clear_form()  # Clear form if list becomes empty
            self._populate_purchase_history([])

        logging.debug(f"Customer list populated with {len(filtered_customers)} items.")

    def export_customers_to_csv(self):
        logging.info("Exporting customer list to CSV.")
        if not self.customer_tree.get_children():
            messagebox.showwarning("No Data", "There are no customers to export.", parent=self)
            return

        file_path = filedialog.asksaveasfilename(
            parent=self, title="Save Customer List As", defaultextension=".csv",
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
                for item_id in self.customer_tree.get_children():
                    row_values = self.customer_tree.item(item_id)['values']
                    writer.writerow(row_values)
            logging.info(f"Customer list exported successfully to {file_path}")
            messagebox.showinfo("Export Successful", f"Customer list exported successfully to:\n{file_path}",
                                parent=self)
        except Exception as e:
            logging.exception(f"Error exporting customer list to CSV: {file_path}")
            messagebox.showerror("Export Failed", f"Could not export customer list.\nError: {e}", parent=self)

