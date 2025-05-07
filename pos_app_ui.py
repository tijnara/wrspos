import tkinter as tk
from tkinter import ttk
import logging
import gui_utils # Needed for CURRENCY_SYMBOL and new color constants

# --- UI Class ---
class POSAppUI:
    """
    Handles the creation and layout of the main POS application's UI elements.
    Does not contain application logic, only widget definitions and placement.
    """
    def __init__(self, root, style):
        """
        Initializes the UI components.

        Args:
            root: The main tkinter root window.
            style: The ttk.Style object configured for the application.
        """
        logging.debug("Initializing POSAppUI...")
        self.root = root
        self.style = style

        self.status_var = tk.StringVar()
        self.customer_display_var = tk.StringVar()
        self.latest_customer_name_var = tk.StringVar()
        self.product_listbox = None
        self.sale_tree = None
        self.total_label = None
        self.product_canvas = None
        self.scrollable_frame = None
        self.first_product_button = None

        self._setup_frames()
        self._setup_status_bar()
        self._setup_product_panel()
        self._setup_sale_panel()
        logging.debug("POSAppUI Initialization complete.")

    def _setup_frames(self):
        logging.debug("Setting up main frames.")
        self.product_frame = ttk.Frame(self.root, padding="5", style='App.TFrame')
        self.sale_frame = ttk.Frame(self.root, padding="5", style='App.TFrame')
        self.product_frame.grid(row=0, column=0, sticky="nsew")
        self.sale_frame.grid(row=0, column=1, sticky="nsew")

        self.product_frame.columnconfigure(0, weight=1)
        self.product_frame.columnconfigure(1, weight=0)
        self.product_frame.rowconfigure(0, weight=0)
        self.product_frame.rowconfigure(1, weight=1)
        self.product_frame.rowconfigure(2, weight=0)
        self.product_frame.rowconfigure(3, weight=1)
        self.product_frame.rowconfigure(4, weight=0)

        self.sale_frame.columnconfigure(0, weight=1)
        self.sale_frame.columnconfigure(1, weight=0)
        self.sale_frame.rowconfigure(0, weight=0)
        self.sale_frame.rowconfigure(1, weight=1)
        self.sale_frame.rowconfigure(2, weight=0)
        self.sale_frame.rowconfigure(3, weight=0)
        self.sale_frame.rowconfigure(4, weight=0)
        self.sale_frame.rowconfigure(5, weight=0)

    def _setup_status_bar(self):
        logging.debug("Setting up status bar.")
        # The style for this label will be changed dynamically by POSAppLogic
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2), style='Status.TLabel') # Default style
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky='ew')

    def _setup_product_panel(self):
        logging.debug("Setting up product panel.")
        ttk.Label(self.product_frame, text="Add to Sale", font=("Arial", 12, "bold"), style='Header.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 2), sticky='w')
        self.product_canvas = tk.Canvas(self.product_frame, bg=self.style.lookup('App.TFrame', 'background'), highlightthickness=0)
        product_scrollbar = ttk.Scrollbar(self.product_frame, orient="vertical", command=self.product_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.product_canvas, style='App.TFrame')
        self.product_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="scrollable_frame")
        self.product_canvas.configure(yscrollcommand=product_scrollbar.set)
        self.product_canvas.grid(row=1, column=0, sticky="nsew")
        product_scrollbar.grid(row=1, column=1, sticky="ns")

        ttk.Separator(self.product_frame, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky='ew', pady=10)
        ttk.Label(self.product_frame, text="Manage Products", font=("Arial", 12, "bold"), style='Header.TLabel').grid(row=2, column=0, columnspan=2, pady=(5, 2), sticky='w')

        self.product_list_frame = ttk.Frame(self.product_frame, style='App.TFrame')
        self.product_list_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=2)
        self.product_list_frame.rowconfigure(0, weight=1)
        self.product_list_frame.columnconfigure(0, weight=1)

        # Use defined selection colors for tk.Listbox
        self.product_listbox = tk.Listbox(
            self.product_list_frame,
            exportselection=False,
            bg="#FFFFFF", # Standard background
            fg="#000000", # Standard foreground
            selectbackground=gui_utils.LISTBOX_SELECT_BG, # Use constant
            selectforeground=gui_utils.LISTBOX_SELECT_FG, # Use constant
            borderwidth=1,
            relief="sunken"
        )
        product_list_scrollbar = ttk.Scrollbar(self.product_list_frame, orient="vertical", command=self.product_listbox.yview)
        self.product_listbox.configure(yscrollcommand=product_list_scrollbar.set)
        self.product_listbox.grid(row=0, column=0, sticky="nsew")
        product_list_scrollbar.grid(row=0, column=1, sticky="ns")

        product_mgmt_button_frame = ttk.Frame(self.product_frame, style='App.TFrame')
        product_mgmt_button_frame.grid(row=4, column=0, columnspan=2, pady=5, sticky='w')
        self.add_product_button = ttk.Button(product_mgmt_button_frame, text="Add New Product", style='Action.TButton')
        self.edit_product_button = ttk.Button(product_mgmt_button_frame, text="Edit Product", style='Action.TButton')
        self.remove_product_button = ttk.Button(product_mgmt_button_frame, text="Remove Product", style='Action.TButton')
        self.view_customers_button = ttk.Button(product_mgmt_button_frame, text="Manage Customers", style='Action.TButton')
        self.add_product_button.pack(side=tk.LEFT, padx=2)
        self.edit_product_button.pack(side=tk.LEFT, padx=2)
        self.remove_product_button.pack(side=tk.LEFT, padx=2)
        self.view_customers_button.pack(side=tk.LEFT, padx=2)

    def _setup_sale_panel(self):
        logging.debug("Setting up sale panel.")
        ttk.Label(self.sale_frame, text="Current Sale", font=("Arial", 14, "bold"), style='Header.TLabel').grid(row=0, column=0, columnspan=2, pady=5, sticky='w')

        columns = ("item", "quantity", "price", "subtotal")
        self.sale_tree = ttk.Treeview(self.sale_frame, columns=columns, show="headings", selectmode="browse", style="Custom.Treeview")
        self.sale_tree.heading("item", text="Item")
        self.sale_tree.heading("quantity", text="Qty")
        self.sale_tree.heading("price", text="Price")
        self.sale_tree.heading("subtotal", text="Subtotal")
        self.sale_tree.column("item", anchor=tk.W, width=150, stretch=True)
        self.sale_tree.column("quantity", anchor=tk.CENTER, width=40, stretch=False)
        self.sale_tree.column("price", anchor=tk.E, width=80, stretch=False)
        self.sale_tree.column("subtotal", anchor=tk.E, width=90, stretch=False)
        sale_scrollbar = ttk.Scrollbar(self.sale_frame, orient="vertical", command=self.sale_tree.yview)
        self.sale_tree.configure(yscrollcommand=sale_scrollbar.set)
        self.sale_tree.grid(row=1, column=0, sticky="nsew", padx=(5,0), pady=2)
        sale_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0,5), pady=2)

        customer_frame = ttk.Frame(self.sale_frame, style='App.TFrame')
        customer_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=(5,0))
        customer_frame.columnconfigure(1, weight=1)
        self.select_customer_button = ttk.Button(customer_frame, text="Select Customer (Ctrl+C)", style='Action.TButton')
        self.customer_display_label = ttk.Label(customer_frame, textvariable=self.customer_display_var, anchor=tk.W, style='TLabel')
        self.select_customer_button.grid(row=0, column=0, padx=(0, 5))
        self.customer_display_label.grid(row=0, column=1, sticky='ew')

        latest_customer_frame = ttk.Frame(self.sale_frame, style='App.TFrame')
        latest_customer_frame.grid(row=3, column=0, columnspan=2, sticky='ew', padx=5, pady=(0, 5))
        latest_customer_frame.columnconfigure(0, weight=1)
        self.latest_customer_label = ttk.Label(latest_customer_frame, textvariable=self.latest_customer_name_var, anchor=tk.W, style='TLabel', font=('Arial', 9))
        self.latest_customer_label.grid(row=0, column=0, sticky='ew', padx=(5,0))

        finalize_total_frame = ttk.Frame(self.sale_frame, style='App.TFrame')
        finalize_total_frame.grid(row=4, column=0, columnspan=2, pady=(2,5), sticky="ew")
        finalize_total_frame.columnconfigure(0, weight=1)
        finalize_total_frame.columnconfigure(1, weight=0)
        finalize_total_frame.columnconfigure(2, weight=0)
        self.finalize_button = ttk.Button(finalize_total_frame, text="Finalize Sale (Ctrl+F)", style='Finalize.TButton')
        self.total_label = ttk.Label(finalize_total_frame, text=f"{gui_utils.CURRENCY_SYMBOL}0.00", font=("Arial", 14, "bold"), style='Total.TLabel')
        self.finalize_button.grid(row=0, column=1, padx=(5, 10), sticky="e")
        self.total_label.grid(row=0, column=2, padx=(0, 5), sticky="e")

        other_sale_actions_frame = ttk.Frame(self.sale_frame, style='App.TFrame')
        other_sale_actions_frame.grid(row=5, column=0, columnspan=2, pady=(0, 5), sticky="e")
        self.history_button = ttk.Button(other_sale_actions_frame, text="View History (Ctrl+H)", style='Action.TButton')
        self.clear_button = ttk.Button(other_sale_actions_frame, text="Clear Sale", style='Action.TButton')
        self.remove_item_button = ttk.Button(other_sale_actions_frame, text="Remove Item", style='Action.TButton')
        self.decrease_qty_button = ttk.Button(other_sale_actions_frame, text="- Qty", style='Action.TButton')
        self.history_button.pack(side=tk.RIGHT, padx=2)
        self.clear_button.pack(side=tk.RIGHT, padx=2)
        self.remove_item_button.pack(side=tk.RIGHT, padx=2)
        self.decrease_qty_button.pack(side=tk.RIGHT, padx=2)
