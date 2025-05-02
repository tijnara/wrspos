import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

# Import necessary modules
import db_operations
import gui_utils # Import the utils module

# --- Customer List Window Class ---
class CustomerListWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manage Customers")
        gui_utils.set_window_icon(self) # Use helper function

        win_width = 650
        win_height = 600
        self.geometry(f"{win_width}x{win_height}")
        self.minsize(500, 400)

        gui_utils.center_window(self, win_width, win_height) # Use helper function
        self.transient(parent)
        self.grab_set()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1) # Allow Treeview to expand
        self.rowconfigure(0, weight=0) # Form frame fixed height
        self.rowconfigure(2, weight=0) # Buttons fixed height

        # --- Add/Edit Customer Form Frame ---
        form_frame = ttk.LabelFrame(self, text="Customer Details", padding="10")
        form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
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


        # --- Customer List Frame (Using Treeview) ---
        list_frame = ttk.LabelFrame(self, text="Existing Customers", padding="10")
        list_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        # --- Updated columns: Added 'seq_no', removed 'cust_id' display ---
        customer_columns = ('seq_no', 'name', 'contact', 'address') # Removed cust_id
        self.customer_tree = ttk.Treeview(list_frame, columns=customer_columns, show="headings", selectmode="browse")

        # --- Updated headings ---
        self.customer_tree.heading('seq_no', text='Cust #') # Changed heading
        self.customer_tree.heading('name', text='Name')
        self.customer_tree.heading('contact', text='Contact Number')
        self.customer_tree.heading('address', text='Address')

        # --- Updated column properties ---
        self.customer_tree.column('seq_no', anchor=tk.W, width=50, stretch=False) # Changed width
        self.customer_tree.column('name', anchor=tk.W, width=150, stretch=True)
        self.customer_tree.column('contact', anchor=tk.W, width=100, stretch=False)
        self.customer_tree.column('address', anchor=tk.W, width=250, stretch=True)

        self.customer_tree.grid(row=0, column=0, sticky="nsew")

        # Add scrollbar
        customer_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.customer_tree.yview)
        self.customer_tree.configure(yscrollcommand=customer_scrollbar.set)
        customer_scrollbar.grid(row=0, column=1, sticky="ns")

        # Bind selection event
        self.customer_tree.bind("<<TreeviewSelect>>", self.on_customer_select)

        # --- Bottom Buttons (Delete, Close) ---
        bottom_button_frame = ttk.Frame(self)
        bottom_button_frame.grid(row=2, column=0, pady=10)

        self.delete_button = ttk.Button(bottom_button_frame, text="Delete Selected", command=self.delete_selected_customer)
        self.delete_button.pack(side=tk.LEFT, padx=10)

        close_button = ttk.Button(bottom_button_frame, text="Close", command=self.destroy)
        close_button.pack(side=tk.LEFT, padx=10)

        # --- Initialize ---
        self.selected_customer_id = None # Still track the actual DB ID internally
        self.populate_customer_list()
        self.clear_form()

    def clear_form(self):
        """Clears the entry fields and selection."""
        self.selected_customer_id = None
        self.name_var.set("")
        self.contact_var.set("")
        self.address_var.set("")
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
            # --- Adjust indices to skip seq_no ---
            self.name_var.set(values[1])
            self.contact_var.set(values[2] if values[2] else "")
            self.address_var.set(values[3] if values[3] else "")
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

        # --- Check for existing name (case-insensitive) ---
        all_customers_data = db_operations.fetch_all_customers() # Fetch ID and Name
        name_lower = name.lower()
        is_duplicate = False
        for cust_id, cust_name, _, _ in all_customers_data:
            if cust_name.lower() == name_lower:
                # If we are updating, allow saving if the duplicate name belongs to the currently selected customer
                if self.selected_customer_id is not None and cust_id == self.selected_customer_id:
                    continue # It's the same customer, allow update
                else:
                    is_duplicate = True # Found a duplicate name belonging to a different customer
                    break

        if is_duplicate:
            messagebox.showwarning("Duplicate Name", f"A customer named '{name}' already exists.", parent=self)
            return
        # --- End Check ---

        if self.selected_customer_id is not None:
            # Update existing customer
            print(f"Updating customer ID: {self.selected_customer_id}")
            if db_operations.update_customer_in_db(self.selected_customer_id, name, contact, address):
                messagebox.showinfo("Success", f"Customer '{name}' updated successfully.", parent=self)
                self.populate_customer_list()
                self.clear_form()
            else:
                # Error message shown by db function (or handled above)
                pass
        else:
            # Add new customer
            print(f"Adding new customer: {name}")
            if db_operations.add_customer_to_db(name, contact, address):
                messagebox.showinfo("Success", f"Customer '{name}' added successfully.", parent=self)
                self.populate_customer_list()
                self.clear_form()
            else:
                # Error message shown by db function (or handled above)
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
        # --- Calculate total number for reverse numbering ---
        total_customers = len(all_customers)
        seq_counter = 0
        for customer_data in all_customers:
            seq_counter += 1
            # --- Calculate reverse number ---
            display_seq_no = total_customers - seq_counter + 1
            cust_id, name, contact, address = customer_data
            display_contact = contact if contact is not None else ""
            display_address = address if address is not None else ""
            # --- Insert display_seq_no as the first value ---
            self.customer_tree.insert("", tk.END, iid=cust_id, values=(display_seq_no, name, display_contact, display_address))

