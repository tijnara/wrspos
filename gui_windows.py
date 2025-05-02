import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import filedialog # Added for file dialogs
import datetime
import os
import sqlite3 # Keep for error catching if needed
import shutil # Added for file copying

# --- External Libraries ---
from dateutil.relativedelta import relativedelta, MO, SU
try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None

# --- Import Project Modules ---
# Ensure all these .py files are in the SAME directory as main.py
import db_operations
import gui_utils
# Import dialogs
from gui_dialogs import PriceInputDialog, CustomerSelectionDialog, CustomPriceDialog
# Import other windows
from gui_customer_manager import CustomerListWindow
from gui_history_window import SalesHistoryWindow


# --- Main Application Class ---
class POSApp:
    def __init__(self, root):
        """Initialize the POS Application."""
        self.root = root
        self.root.title("SEASIDE Water Refilling Station - POS")
        app_width = 850
        app_height = 750
        # self.root.state('zoomed') # REMOVED: Don't start maximized
        self.root.geometry(f"{app_width}x{app_height}") # Set initial size
        self.root.minsize(700, 600) # Keep a reasonable minimum size

        # --- Prevent Resizing/Maximizing ---
        self.root.resizable(False, False)

        # Use helper function to set icon for main window
        gui_utils.set_window_icon(self.root)

        # Center the main window on startup
        gui_utils.center_window(self.root, app_width, app_height) # Centering is done here

        db_operations.initialize_db()

        self.products = self.load_products()
        self.current_sale = {}
        self.total_amount = 0.0
        self.history_window = None
        self.customer_list_window = None
        self.first_product_button = None # To store reference for F1 focus
        self.status_bar_job = None # To store the .after job ID
        self.current_customer_name = "N/A" # Track selected customer for the current sale

        # --- Apply Styles ---
        self.apply_styles() # Call method to configure styles

        # --- Create Menu Bar ---
        self.create_menu()

        # --- Configure Main Layout ---
        self.root.columnconfigure(0, weight=1) # Product frame
        self.root.columnconfigure(1, weight=1) # Sale frame
        self.root.rowconfigure(0, weight=1) # Main content row
        self.root.rowconfigure(1, weight=0) # Status bar row (fixed height)

        # --- Create Frames ---
        self.product_frame = ttk.Frame(root, padding="5", style='App.TFrame')
        self.sale_frame = ttk.Frame(root, padding="5", style='App.TFrame')
        self.product_frame.grid(row=0, column=0, sticky="nsew")
        self.sale_frame.grid(row=0, column=1, sticky="nsew")

        # --- Status Bar ---
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2), style='Status.TLabel')
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky='ew')
        self.show_status("Ready", duration=None) # Initial status

        # Configure product frame grid rows/columns for resizing
        self.product_frame.columnconfigure(0, weight=1) # Canvas/Scrollable area column
        self.product_frame.columnconfigure(1, weight=0) # Scrollbar column
        self.product_frame.rowconfigure(0, weight=0) # Label row
        self.product_frame.rowconfigure(1, weight=1) # Product button canvas row (expand vertically)
        # self.product_frame.rowconfigure(2, weight=0) # Custom button row (fixed height) - Handled by populate_product_buttons grid
        self.product_frame.rowconfigure(3, weight=0) # Separator/Label row (fixed height)
        self.product_frame.rowconfigure(4, weight=1) # Product management list area (expand vertically)
        self.product_frame.rowconfigure(5, weight=0) # Mgmt buttons row (fixed height)

        # Configure sale frame grid rows/columns for resizing
        self.sale_frame.columnconfigure(0, weight=1) # Treeview/Customer Label column
        self.sale_frame.columnconfigure(1, weight=0) # Scrollbar column
        self.sale_frame.rowconfigure(0, weight=0) # Header Label row
        self.sale_frame.rowconfigure(1, weight=1) # Sale Treeview row (expand vertically)
        self.sale_frame.rowconfigure(2, weight=0) # Customer Info row
        self.sale_frame.rowconfigure(3, weight=0) # Finalize/Total row
        self.sale_frame.rowconfigure(4, weight=0) # Action Buttons row

        # --- Populate Product Frame (Sale Buttons) ---
        ttk.Label(self.product_frame, text="Add to Sale", font=("Arial", 12, "bold"), style='Header.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 2), sticky='w')
        self.product_canvas = tk.Canvas(self.product_frame, bg=self.style.lookup('App.TFrame', 'background'), highlightthickness=0)
        product_scrollbar = ttk.Scrollbar(self.product_frame, orient="vertical", command=self.product_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.product_canvas, style='App.TFrame') # Apply style to inner frame
        self.product_canvas.bind('<Configure>', lambda e: self.product_canvas.configure(scrollregion=self.product_canvas.bbox("all")))
        self.product_canvas_window = self.product_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.scrollable_frame.bind('<Configure>', self._configure_scrollable_frame) # Re-bind configure to handle width
        self.product_canvas.configure(yscrollcommand=product_scrollbar.set)
        self.product_canvas.grid(row=1, column=0, sticky="nsew")
        product_scrollbar.grid(row=1, column=1, sticky="ns")
        self.populate_product_buttons() # Initial population

        # --- Product Management Section ---
        ttk.Separator(self.product_frame, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky='ew', pady=10)
        ttk.Label(self.product_frame, text="Manage Products", font=("Arial", 12, "bold"), style='Header.TLabel').grid(row=3, column=0, columnspan=2, pady=(5, 2), sticky='w')

        self.product_list_frame = ttk.Frame(self.product_frame, style='App.TFrame') # Style frame
        self.product_list_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=2)
        self.product_list_frame.rowconfigure(0, weight=1) # Make listbox expand vertically inside its frame
        self.product_list_frame.columnconfigure(0, weight=1) # Make listbox expand horizontally inside its frame
        self.product_listbox = tk.Listbox(self.product_list_frame, exportselection=False, bg="#FFFFFF", fg="#000000", selectbackground="#ABEBC6", selectforeground="#145A32", borderwidth=1, relief="sunken") # Adjusted select colors
        self.product_listbox.grid(row=0, column=0, sticky="nsew")
        product_list_scrollbar = ttk.Scrollbar(self.product_list_frame, orient="vertical", command=self.product_listbox.yview)
        self.product_listbox.configure(yscrollcommand=product_list_scrollbar.set)
        product_list_scrollbar.grid(row=0, column=1, sticky="ns")
        self.populate_product_management_list()

        product_mgmt_button_frame = ttk.Frame(self.product_frame, style='App.TFrame') # Style frame
        product_mgmt_button_frame.grid(row=5, column=0, columnspan=2, pady=5, sticky='w')
        self.add_product_button = ttk.Button(product_mgmt_button_frame, text="Add New Product", command=self.prompt_new_item, style='Action.TButton')
        self.add_product_button.pack(side=tk.LEFT, padx=2)
        self.edit_product_button = ttk.Button(product_mgmt_button_frame, text="Edit Product", command=self.prompt_edit_item, style='Action.TButton')
        self.edit_product_button.pack(side=tk.LEFT, padx=2)
        self.remove_product_button = ttk.Button(product_mgmt_button_frame, text="Remove Product", command=self.remove_selected_product_permanently, style='Action.TButton')
        self.remove_product_button.pack(side=tk.LEFT, padx=2)
        self.view_customers_button = ttk.Button(product_mgmt_button_frame, text="Manage Customers", command=self.view_customers, style='Action.TButton')
        self.view_customers_button.pack(side=tk.LEFT, padx=2)


        # --- Populate Sale Frame ---
        ttk.Label(self.sale_frame, text="Current Sale", font=("Arial", 14, "bold"), style='Header.TLabel').grid(row=0, column=0, columnspan=2, pady=5, sticky='w')
        columns = ("item", "quantity", "price", "subtotal")
        self.sale_tree = ttk.Treeview(self.sale_frame, columns=columns, show="headings", selectmode="browse", style="Custom.Treeview") # Apply Treeview style
        self.sale_tree.heading("item", text="Item")
        self.sale_tree.heading("quantity", text="Qty")
        self.sale_tree.heading("price", text="Price")
        self.sale_tree.heading("subtotal", text="Subtotal")
        self.sale_tree.column("item", anchor=tk.W, width=150, stretch=True)
        self.sale_tree.column("quantity", anchor=tk.CENTER, width=40, stretch=False)
        self.sale_tree.column("price", anchor=tk.E, width=80, stretch=False)
        self.sale_tree.column("subtotal", anchor=tk.E, width=90, stretch=False)
        self.sale_tree.grid(row=1, column=0, sticky="nsew", padx=(5,0), pady=2)
        sale_scrollbar = ttk.Scrollbar(self.sale_frame, orient="vertical", command=self.sale_tree.yview)
        self.sale_tree.configure(yscrollcommand=sale_scrollbar.set)
        sale_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0,5), pady=2)

        # --- Customer Selection Area (Row 2) ---
        customer_frame = ttk.Frame(self.sale_frame, style='App.TFrame')
        customer_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=(5,2))
        customer_frame.columnconfigure(1, weight=1) # Allow label to expand
        self.select_customer_button = ttk.Button(customer_frame, text="Select Customer (Ctrl+C)", command=self.select_customer_for_sale, style='Action.TButton')
        self.select_customer_button.grid(row=0, column=0, padx=(0, 5))
        self.customer_display_var = tk.StringVar(value=f"Customer: {self.current_customer_name}")
        self.customer_display_label = ttk.Label(customer_frame, textvariable=self.customer_display_var, anchor=tk.W, style='TLabel')
        self.customer_display_label.grid(row=0, column=1, sticky='ew')

        # --- Finalize Button and Total Label Frame (Row 3) ---
        finalize_total_frame = ttk.Frame(self.sale_frame, style='App.TFrame') # Style frame
        finalize_total_frame.grid(row=3, column=0, columnspan=2, pady=(2,5), sticky="ew") # Adjusted padding
        finalize_total_frame.columnconfigure(0, weight=1)
        finalize_total_frame.columnconfigure(1, weight=0)
        finalize_total_frame.columnconfigure(2, weight=0)

        self.finalize_button = ttk.Button(finalize_total_frame, text="Finalize Sale (Ctrl+F)", command=self.finalize_sale, style='Finalize.TButton') # Specific style
        self.finalize_button.grid(row=0, column=1, padx=(5, 10), sticky="e")

        self.total_label = ttk.Label(finalize_total_frame, text=f"{gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 14, "bold"), style='Total.TLabel') # Specific style
        self.total_label.grid(row=0, column=2, padx=(0, 5), sticky="e")


        # --- Other Sale Action Buttons Frame (Row 4) ---
        other_sale_actions_frame = ttk.Frame(self.sale_frame, style='App.TFrame') # Style frame
        other_sale_actions_frame.grid(row=4, column=0, columnspan=2, pady=(0, 5), sticky="e") # Adjusted padding

        self.history_button = ttk.Button(other_sale_actions_frame, text="View History (Ctrl+H)", command=self.view_sales_history, style='Action.TButton')
        self.history_button.pack(side=tk.RIGHT, padx=2)

        self.clear_button = ttk.Button(other_sale_actions_frame, text="Clear Sale", command=self.clear_sale, style='Action.TButton')
        self.clear_button.pack(side=tk.RIGHT, padx=2)

        self.remove_item_button = ttk.Button(other_sale_actions_frame, text="Remove Item", command=self.remove_selected_item_from_sale, style='Action.TButton')
        self.remove_item_button.pack(side=tk.RIGHT, padx=2)

        self.decrease_qty_button = ttk.Button(other_sale_actions_frame, text="- Qty", command=self.decrease_item_quantity, style='Action.TButton')
        self.decrease_qty_button.pack(side=tk.RIGHT, padx=2)


        self.update_sale_display()

        # --- Bind Keyboard Shortcuts ---
        self.bind_shortcuts()

    def apply_styles(self):
        """Configures ttk styles for the application."""
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            print("Warning: 'clam' theme not available, using default.")

        # --- Define Apple Green Theme Colors ---
        BG_COLOR = "#F0FFF0"       # Honeydew (very light green)
        BUTTON_BG = "#98FB98"      # PaleGreen
        BUTTON_FG = "#006400"      # DarkGreen
        BUTTON_ACTIVE = "#90EE90"  # LightGreen
        FINALIZE_BG = "#3CB371"    # MediumSeaGreen
        FINALIZE_ACTIVE = "#66CDAA" # MediumAquaMarine
        LABEL_FG = "#2F4F4F"       # DarkSlateGray
        HEADER_FG = "#1E8449"      # Darker Green
        TOTAL_FG = "#006400"       # DarkGreen
        TREE_HEADING_BG = "#D0F0C0" # Tea Green Light
        TREE_HEADING_FG = "#1E8449" # Darker Green
        TREE_ROW_BG_ODD = "#FFFFFF" # White
        TREE_ROW_BG_EVEN = "#F5FFFA" # MintCream
        STATUS_BG = "#98FB98"      # PaleGreen
        STATUS_FG = "#006400"      # DarkGreen
        SELECT_BG = "#90EE90"      # LightGreen (for selections)

        # --- Configure Styles ---
        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('App.TFrame', background=BG_COLOR)
        self.style.configure('TLabel', background=BG_COLOR, foreground=LABEL_FG, font=('Arial', 10))
        self.style.configure('Header.TLabel', background=BG_COLOR, foreground=HEADER_FG, font=('Arial', 12, 'bold'))
        self.style.configure('Total.TLabel', background=BG_COLOR, foreground=TOTAL_FG, font=('Arial', 14, 'bold'))
        self.style.configure('Status.TLabel', background=STATUS_BG, foreground=STATUS_FG, font=('Arial', 9))

        # Standard Button Style
        self.style.configure('TButton', background=BUTTON_BG, foreground=BUTTON_FG, font=('Arial', 9), padding=5, borderwidth=1, relief='raised')
        self.style.map('TButton', background=[('active', BUTTON_ACTIVE)])

        # Product Button Style
        self.style.configure('Product.TButton', font=('Arial', 10, 'bold'), padding=(5, 10))
        # Action Button Style
        self.style.configure('Action.TButton', padding=4, font=('Arial', 9))
        # Finalize Button Style
        self.style.configure('Finalize.TButton', background=FINALIZE_BG, foreground='white', font=('Arial', 10, 'bold'), padding=6)
        self.style.map('Finalize.TButton', background=[('active', FINALIZE_ACTIVE)])

        # Treeview Style
        self.style.configure("Custom.Treeview", rowheight=25, fieldbackground=TREE_ROW_BG_ODD, background=TREE_ROW_BG_ODD, foreground=LABEL_FG)
        self.style.map("Custom.Treeview", background=[('selected', SELECT_BG)]) # Highlight color
        self.style.configure("Custom.Treeview.Heading", background=TREE_HEADING_BG, foreground=TREE_HEADING_FG, font=('Arial', 10, 'bold'), relief="flat")
        self.style.map("Custom.Treeview.Heading", background=[('active', BUTTON_ACTIVE)])

        # Configure alternating row colors (requires tags)
        # This needs the actual treeview widget, so we do it after creation
        # self.sale_tree.tag_configure('oddrow', background=TREE_ROW_BG_ODD)
        # self.sale_tree.tag_configure('evenrow', background=TREE_ROW_BG_EVEN)

        # Other widgets
        self.style.configure('TEntry', fieldbackground='white', foreground='black')
        self.style.configure('TCombobox', fieldbackground='white', foreground='black')
        # Make scrollbar match button style
        self.style.configure('TScrollbar', background=BUTTON_BG, troughcolor=BG_COLOR, borderwidth=0)
        self.style.map('TScrollbar', background=[('active', BUTTON_ACTIVE)])
        self.style.configure('TLabelFrame', background=BG_COLOR, borderwidth=1, relief="groove")
        self.style.configure('TLabelFrame.Label', background=BG_COLOR, foreground=HEADER_FG, font=('Arial', 11, 'bold'))


    def show_status(self, message, duration=3000):
        """Displays a message in the status bar for a specified duration."""
        self.status_var.set(message)
        if self.status_bar_job:
            self.root.after_cancel(self.status_bar_job)
            self.status_bar_job = None
        if duration:
            self.status_bar_job = self.root.after(duration, self.clear_status)

    def clear_status(self):
        """Clears the status bar."""
        self.status_var.set("")
        self.status_bar_job = None

    def create_menu(self):
        """Creates the main menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Backup Database...", command=self.backup_database)
        file_menu.add_command(label="Restore Database...", command=self.restore_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

    def bind_shortcuts(self):
        """Binds keyboard shortcuts to application functions."""
        self.root.bind('<F1>', self.focus_first_product)
        self.root.bind('<Control-f>', lambda event=None: self.finalize_sale())
        self.root.bind('<Control-h>', lambda event=None: self.view_sales_history())
        self.root.bind('<Control-c>', lambda event=None: self.select_customer_for_sale())

    def focus_first_product(self, event=None):
        """Sets focus to the first product button."""
        if self.first_product_button and self.first_product_button.winfo_exists():
            self.first_product_button.focus_set()
            self.show_status("Focused first product button (F1)", 2000)
        else:
            self.show_status("No product buttons found to focus.", 2000)

    def backup_database(self):
        """Creates a backup copy of the database file."""
        source_db = db_operations.DATABASE_FILENAME
        if not os.path.exists(source_db):
            messagebox.showerror("Backup Error", f"Database file '{source_db}' not found.", parent=self.root)
            self.show_status(f"Backup failed: Database file '{source_db}' not found.", 5000)
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_filename = f"pos_backup_{timestamp}.db"

        backup_path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Database Backup As",
            initialfile=suggested_filename,
            defaultextension=".db",
            filetypes=[("Database files", "*.db"), ("All files", "*.*")]
        )

        if not backup_path:
            self.show_status("Backup cancelled.", 3000)
            return

        try:
            shutil.copy2(source_db, backup_path)
            self.show_status(f"Database backed up successfully to {os.path.basename(backup_path)}", 5000)
            print(f"Database backed up to {backup_path}")
        except Exception as e:
            messagebox.showerror("Backup Failed", f"Could not create backup.\nError: {e}", parent=self.root)
            self.show_status(f"Backup failed: {e}", 5000)
            print(f"Error during backup: {e}")

    def restore_database(self):
        """Restores the database from a backup file."""
        target_db = db_operations.DATABASE_FILENAME
        warning_msg = (
            "WARNING: Restoring a database will OVERWRITE the current data!\n\n"
            "This action cannot be undone.\n\n"
            "The application will close after restoring. You must restart it manually.\n\n"
            "Are you absolutely sure you want to proceed?"
        )
        if not messagebox.askyesno("Confirm Restore", warning_msg, icon='warning', parent=self.root):
            self.show_status("Restore cancelled.", 3000)
            return

        backup_path = filedialog.askopenfilename(
            parent=self.root,
            title="Select Database Backup to Restore",
            filetypes=[("Database files", "*.db"), ("All files", "*.*")]
        )

        if not backup_path:
            self.show_status("Restore cancelled.", 3000)
            return

        if not os.path.exists(backup_path):
            messagebox.showerror("Restore Error", "Selected backup file does not exist.", parent=self.root)
            self.show_status("Restore failed: Backup file not found.", 5000)
            return
        if not backup_path.lower().endswith(".db"):
             if not messagebox.askyesno("Confirm File Type", "The selected file doesn't have a .db extension. Are you sure it's a valid database backup?", icon='warning', parent=self.root):
                 self.show_status("Restore cancelled.", 3000)
                 return

        try:
            print("Attempting restore. Ensure all secondary windows (History, Customers) are closed.")
            shutil.copy2(backup_path, target_db)
            messagebox.showinfo("Restore Successful",
                                f"Database restored successfully from:\n{os.path.basename(backup_path)}\n\n"
                                "The application will now close. Please restart it.",
                                parent=self.root)
            print(f"Database restored from {backup_path}. Application closing.")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Restore Failed", f"Could not restore database.\nError: {e}", parent=self.root)
            self.show_status(f"Restore failed: {e}", 5000)
            print(f"Error during restore: {e}")

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
    def populate_product_buttons(self, available_width=None):
        """Clears and repopulates the product buttons with a fixed 4-column layout."""
        self.first_product_button = None # Reset reference
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # --- Define the desired order ---
        priority_order = ["Refill (20)", "Refill (25)"]
        ordered_products = []
        remaining_products = self.products.copy() # Create a copy to remove items from

        # Add priority items first if they exist
        for name in priority_order:
            if name in remaining_products:
                ordered_products.append((name, remaining_products[name]))
                del remaining_products[name] # Remove from remaining

        # Add the rest, sorted alphabetically
        ordered_products.extend(sorted(remaining_products.items()))

        # --- Grid layout logic ---
        max_cols = 4
        for i in range(max_cols):
            self.scrollable_frame.columnconfigure(i, weight=1)

        row_num, col_num = 0, 0
        # Use the ordered list
        for idx, (name, price) in enumerate(ordered_products):
            btn_text = f"{name}\n({gui_utils.CURRENCY_SYMBOL}{price:.2f})"
            # Apply the Product.TButton style
            btn = ttk.Button(
                self.scrollable_frame,
                text=btn_text,
                command=lambda n=name: self.add_item(n),
                style='Product.TButton'
            )
            btn.grid(row=row_num, column=col_num, padx=2, pady=2, sticky="ew")
            if idx == 0: # Still capture the *actual* first button for F1 focus
                self.first_product_button = btn

            col_num += 1
            if col_num >= max_cols:
                col_num = 0
                row_num += 1

        # Add Custom Price Button below the grid
        custom_button = ttk.Button(self.scrollable_frame, text="Custom Price Item", command=self.prompt_custom_item, style='Action.TButton')
        custom_button.grid(row=row_num + 1, column=0, columnspan=max_cols, pady=(10, 5), sticky='ew')

        self.scrollable_frame.update_idletasks()
        self.product_canvas.configure(scrollregion=self.product_canvas.bbox("all"))


    def populate_product_management_list(self):
        """Clears and repopulates the product management listbox."""
        self.product_listbox.delete(0, tk.END)
        sorted_products = sorted(self.products.items())
        for name, price in sorted_products:
            self.product_listbox.insert(tk.END, f"{name} ({gui_utils.CURRENCY_SYMBOL}{price:.2f})")

    def _get_selected_product_details(self):
        """Helper method to get the name and price of the selected product in the listbox."""
        selection_indices = self.product_listbox.curselection()
        if not selection_indices:
            messagebox.showwarning("No Selection", "Please select a product from the 'Manage Products' list first.", parent=self.root)
            return None, None
        selected_index = selection_indices[0]
        selected_text = self.product_listbox.get(selected_index)
        try:
            parts = selected_text.split(f' ({gui_utils.CURRENCY_SYMBOL}')
            product_name = parts[0]
            price_str = parts[1].rstrip(')')
            price = float(price_str)
            return product_name, price
        except Exception as e:
             messagebox.showerror("Error", f"Could not parse selected product details: {e}", parent=self.root)
             print(f"Error parsing listbox text '{selected_text}': {e}")
             return None, None

    def prompt_new_item(self):
        """Opens dialogs to get new product name and price, adds it to DB and UI."""
        name = simpledialog.askstring("New Product", "Enter product name:", parent=self.root)
        if not name: return
        if name in self.products:
             messagebox.showwarning("Product Exists", f"Product '{name}' already exists.", parent=self.root)
             return

        price_dialog = PriceInputDialog(self.root, "New Product Price", f"Enter price for {name}:")
        price = price_dialog.result

        if price is not None:
            try:
                if db_operations.insert_product_to_db(name, price):
                    self.products[name] = price
                    self.populate_product_buttons()
                    self.populate_product_management_list()
                    self.show_status(f"Product '{name}' added successfully.", 3000) # Status bar
            except Exception as e:
                 messagebox.showerror("Database Error", f"Could not save product to database.\n{e}", parent=self.root)
                 self.show_status(f"Failed to add product '{name}'.", 5000)


    def prompt_edit_item(self):
        """Gets selected product, prompts for new details, updates DB and UI."""
        original_name, original_price = self._get_selected_product_details()
        if original_name is None: return
        new_name = simpledialog.askstring("Edit Product", "Enter new product name:", initialvalue=original_name, parent=self.root)
        if not new_name: return

        price_dialog = PriceInputDialog(self.root, "Edit Product Price", f"Enter new price for {new_name}:", initialvalue=f"{original_price:.2f}")
        new_price = price_dialog.result

        if new_price is not None:
            try:
                if new_name != original_name and new_name in self.products:
                     messagebox.showerror("Edit Error", f"Cannot rename to '{new_name}'.\nA product with that name already exists.", parent=self.root)
                     return
                if db_operations.update_product_in_db(original_name, new_name, new_price):
                    if original_name in self.products:
                         del self.products[original_name]
                    self.products[new_name] = new_price
                    self.populate_product_buttons()
                    self.populate_product_management_list()
                    self.show_status(f"Product '{original_name}' updated successfully.", 3000) # Status bar
            except Exception as e:
                 messagebox.showerror("Database Error", f"Could not update product in database.\n{e}", parent=self.root)
                 self.show_status(f"Failed to update product '{original_name}'.", 5000)


    def remove_selected_product_permanently(self):
        """Gets selection from listbox, confirms, deletes from DB and updates UI."""
        product_name, _ = self._get_selected_product_details()
        if product_name is None: return
        confirmed = messagebox.askyesno("Confirm Permanent Deletion",
                                        f"Are you sure you want to permanently delete '{product_name}'?\n"
                                        "This cannot be undone.", parent=self.root)
        if not confirmed:
            self.show_status("Product deletion cancelled.", 2000)
            return
        if db_operations.delete_product_from_db(product_name):
            if product_name in self.products:
                 del self.products[product_name]
            self.populate_product_buttons()
            self.populate_product_management_list()
            self.show_status(f"Product '{product_name}' permanently deleted.", 3000) # Status bar
        else:
            # Error likely shown by db function, but add status too
            self.show_status(f"Failed to delete product '{product_name}'.", 5000)

    # --- Sale Handling Methods ---
    def add_item(self, name, override_price=None, quantity_to_add=1):
        """Adds an item to the current sale or increments its quantity."""
        if override_price is not None:
            current_price = override_price
            print(f"Using override price for {name}: {current_price}")
        elif name in self.products:
             current_price = self.products[name]
        else:
             messagebox.showerror("Error", f"Product '{name}' not found in product list.")
             self.show_status(f"Error: Product '{name}' not found.", 5000)
             return

        item_key = f"{name}__{current_price:.2f}" # Use name and price as key

        if item_key in self.current_sale:
             self.current_sale[item_key]['quantity'] += quantity_to_add
        else:
            self.current_sale[item_key] = {'name': name, 'price': current_price, 'quantity': quantity_to_add}

        self.show_status(f"Added {quantity_to_add} x {name}", 2000)
        self.update_sale_display()

    def prompt_custom_item(self):
        """Opens a dialog to select a product and enter a custom price and quantity."""
        dialog = CustomPriceDialog(self.root, list(self.products.keys()))
        result = dialog.result
        if result:
            product_name, custom_price, quantity = result
            if product_name and custom_price is not None and quantity is not None:
                self.add_item(product_name, override_price=custom_price, quantity_to_add=quantity)


    def decrease_item_quantity(self):
        """Decreases the quantity of the selected item in the sale tree."""
        selected_item_id = self.sale_tree.focus() # This is the item_key
        if not selected_item_id:
            messagebox.showwarning("No Selection", "Please select an item from the 'Current Sale' list to decrease quantity.")
            return

        if selected_item_id in self.current_sale:
            item_name = self.current_sale[selected_item_id]['name']
            current_quantity = self.current_sale[selected_item_id]['quantity']
            if current_quantity > 1:
                self.current_sale[selected_item_id]['quantity'] -= 1
                self.show_status(f"Decreased quantity for {item_name}.", 2000)
            else:
                del self.current_sale[selected_item_id]
                self.show_status(f"Removed {item_name} from sale.", 2000)
            self.update_sale_display(preserve_selection=selected_item_id if current_quantity > 1 else None)
        else:
             messagebox.showerror("Error", "Could not find the selected item in the current sale data.")
             self.show_status("Error: Could not decrease quantity.", 5000)


    def remove_selected_item_from_sale(self):
        """Removes the currently selected item from the sale tree (current sale only)."""
        selected_item_id = self.sale_tree.focus() # This is the item_key
        if not selected_item_id:
            messagebox.showwarning("No Selection", "Please select an item from the 'Current Sale' list to remove.")
            return

        if selected_item_id in self.current_sale:
            item_name = self.current_sale[selected_item_id]['name']
            confirmed = messagebox.askyesno("Confirm Remove Item", f"Are you sure you want to remove all '{item_name}' from the current sale?")
            if confirmed:
                del self.current_sale[selected_item_id]
                self.update_sale_display()
                self.show_status(f"Removed {item_name} from sale.", 3000)
            else:
                self.show_status("Item removal cancelled.", 2000)
        else:
             messagebox.showerror("Error", "Could not find the selected item in the current sale data.")
             self.show_status("Error: Could not remove item.", 5000)


    def update_sale_display(self, preserve_selection=None):
        """Updates the Treeview and total label, optionally preserving selection."""
        selected_id_to_preserve = preserve_selection

        # Configure Treeview tags (needs to be done after tree exists)
        self.sale_tree.tag_configure('oddrow', background="#FFFFFF") # White
        self.sale_tree.tag_configure('evenrow', background="#F5FFFA") # MintCream

        for i in self.sale_tree.get_children():
            self.sale_tree.delete(i)

        self.total_amount = 0.0
        sorted_sale_items = sorted(self.current_sale.items(), key=lambda item: item[1]['name'])
        new_selection_id = None

        # Add alternating row tags
        for i, (item_key, details) in enumerate(sorted_sale_items):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            name = details['name']
            price = details['price']
            quantity = details['quantity']
            subtotal = price * quantity
            price_str = f"{gui_utils.CURRENCY_SYMBOL}{price:.2f}"
            subtotal_str = f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"
            # Use item_key as the iid and apply tag
            item_id = self.sale_tree.insert("", tk.END, iid=item_key, values=(name, quantity, price_str, subtotal_str), tags=(tag,))

            if selected_id_to_preserve == item_key:
                new_selection_id = item_id

            self.total_amount += subtotal

        self.total_label.config(text=f"Total: {gui_utils.CURRENCY_SYMBOL}{self.total_amount:.2f}")

        if new_selection_id:
            print(f"Reselecting item ID: {new_selection_id}")
            self.sale_tree.focus(new_selection_id)
            self.sale_tree.selection_set(new_selection_id)
        else:
             self.sale_tree.focus('')
             self.sale_tree.selection_set('')


    def clear_sale(self):
        """Clears the current sale data and updates the display."""
        if not self.current_sale:
            self.show_status("Sale is already empty.", 2000)
            return
        confirmed = messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the current sale?")
        if confirmed:
            self.current_sale = {}
            self.current_customer_name = "N/A" # Reset customer
            self.customer_display_var.set(f"Customer: {self.current_customer_name}") # Update label
            self.update_sale_display()
            self.show_status("Sale cleared.", 3000)
        else:
            self.show_status("Clear sale cancelled.", 2000)

    def select_customer_for_sale(self):
        """Opens dialog to select customer for the current sale."""
        dialog = CustomerSelectionDialog(self.root)
        customer_name = dialog.result
        if customer_name is not None: # If user didn't cancel
            self.current_customer_name = customer_name
            self.customer_display_var.set(f"Customer: {self.current_customer_name}")
            self.show_status(f"Customer set to: {self.current_customer_name}", 3000)
        else:
            self.show_status("Customer selection cancelled.", 2000)


    def generate_receipt_text(self, sale_id, timestamp_obj, customer_name):
        """Generates a simple text receipt for the current sale."""
        receipt = f"--- SEASIDE Water Refilling Station ---\n"
        receipt += f"Sale ID: {sale_id}\n"
        receipt += f"Date: {timestamp_obj.strftime('%Y-%m-%d %H:%M:%S')}\n"
        receipt += f"Customer: {customer_name}\n"
        receipt += "--------------------------------------\n"
        receipt += "{:<18} {:>3} {:>7} {:>8}\n".format("Item", "Qty", "Price", "Subtotal")
        receipt += "--------------------------------------\n"
        for details in sorted(self.current_sale.values(), key=lambda item: item['name']):
            name = details['name']
            qty = details['quantity']
            price = details['price']
            subtotal = qty * price
            price_str = f"{gui_utils.CURRENCY_SYMBOL}{price:.2f}"
            subtotal_str = f"{gui_utils.CURRENCY_SYMBOL}{subtotal:.2f}"
            receipt += "{:<18} {:>3d} {:>7} {:>8}\n".format(name[:18], qty, price_str, subtotal_str)
        receipt += "======================================\n"
        total_str = f"{gui_utils.CURRENCY_SYMBOL}{self.total_amount:.2f}"
        receipt += "{:<29} {:>8}\n".format("TOTAL:", total_str)
        receipt += "--------------------------------------\n"
        receipt += "        Thank you!\n"
        return receipt

    def finalize_sale(self):
        """Checks for customer, records sale, generates receipt, clears sale."""
        if not self.current_sale:
             messagebox.showwarning("Empty Sale", "Cannot finalize an empty sale.")
             self.show_status("Cannot finalize an empty sale.", 3000)
             return

        if self.current_customer_name == "N/A":
            messagebox.showwarning("Customer Not Selected", "Please select a customer before finalizing the sale.", parent=self.root)
            self.show_status("Select a customer first.", 3000)
            return

        current_timestamp_obj = datetime.datetime.now()

        sale_items_for_db = {}
        for item_key, details in self.current_sale.items():
             sale_items_for_db[details['name']] = {'price': details['price'], 'quantity': details['quantity']}

        sale_id = db_operations.save_sale_record(current_timestamp_obj, self.total_amount, self.current_customer_name)
        if sale_id is None:
            self.show_status("Error saving sale record.", 5000)
            return

        items_saved = db_operations.save_sale_items_records(sale_id, sale_items_for_db)
        if not items_saved:
            self.show_status("Error saving sale items.", 5000)
            return

        receipt_text = self.generate_receipt_text(sale_id, current_timestamp_obj, self.current_customer_name)
        print("--- Receipt ---")
        print(receipt_text)
        print("---------------")
        messagebox.showinfo(f"Sale Finalized - ID: {sale_id}", receipt_text)

        self.current_sale = {}
        self.current_customer_name = "N/A"
        self.customer_display_var.set(f"Customer: {self.current_customer_name}")
        self.update_sale_display()
        self.show_status(f"Sale {sale_id} finalized and recorded.", 3000)


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
