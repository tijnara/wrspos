# SEASIDE Water Refilling Station - POS System

A simple Point of Sale (POS) system built with Python and Tkinter for managing sales, products, and customers, specifically tailored for the SEASIDE Water Refilling Station.

## Features

* **Product Management:**
    * Add new products with names and prices.
    * Edit existing product names and prices.
    * Remove products permanently.
    * Product data is stored persistently in an SQLite database (`pos_system.db`).
* **Customer Management:**
    * Add new customers with name, contact number, and address.
    * Update existing customer details.
    * Delete customers.
    * Customer data is stored persistently in the SQLite database.
* **Sales Processing:**
    * Add standard products to the current sale with a click.
    * Add products with a custom price and quantity via a dedicated dialog.
    * Decrease the quantity of an item in the current sale.
    * Remove items completely from the current sale.
    * Clear the entire current sale.
    * Finalize sales, prompting for customer selection (from existing list or new entry).
* **Sales History & Reporting:**
    * Record all finalized sales (timestamp, total amount, customer name) and items sold in the database.
    * View a list of all past sales transactions.
    * View detailed receipts for selected past sales.
    * Delete past sale records.
    * View sales summaries for the current week and current month.
    * View a detailed product sales summary (total quantity, total revenue per product) for a custom date range using calendar pickers.
* **User Interface:**
    * Graphical User Interface (GUI) built using Python's standard `tkinter` library and `ttk` themed widgets.
    * Separate windows for managing customers and viewing sales history.
    * Dialogs for adding/editing products, selecting customers, and adding custom items.
    * Attempts to center windows on the screen.
    * Custom application icon (`oceans.ico`).

## File Structure

* `main.py`: The main entry point to run the application. Handles dependency checks and starts the GUI.
* `gui_classes.py`: Contains the Tkinter classes for the main application window (`POSApp`) and all associated dialogs/windows (`CustomerSelectionDialog`, `SalesHistoryWindow`, `CustomerListWindow`, `CustomPriceDialog`). Also includes helper functions like `center_window` and `set_window_icon`.
* `db_operations.py`: Contains all functions for interacting with the SQLite database (initialization, fetching, inserting, updating, deleting data for products, sales, items, and customers).
* `pos_system.db`: The SQLite database file where all application data is stored. This file is created automatically if it doesn't exist when `main.py` is run.
* `oceans.ico`: The icon file used for the application windows. (Ensure this file is present in the same directory).

## Setup and Installation

1.  **Python:** Ensure you have Python 3 installed on your system.
2.  **Dependencies:** Install the required external libraries using pip. Open your terminal or command prompt and run:
    ```bash
    pip install python-dateutil tkcalendar
    ```
3.  **Icon File:** Make sure the icon file named `oceans.ico` is placed in the same directory as the Python scripts (`main.py`, `gui_classes.py`, `db_operations.py`).
4.  **Database:** The `pos_system.db` file will be created automatically in the same directory when you run the application for the first time. If you encounter database errors (like missing columns), deleting the existing `pos_system.db` file and restarting the application will recreate it with the latest structure.

## Running the Application

1.  Open your terminal or command prompt.
2.  Navigate (`cd`) to the directory containing the three Python files (`main.py`, `gui_classes.py`, `db_operations.py`) and the `oceans.ico` file.
3.  Run the main script using:
    ```bash
    python main.py
    ```

## How to Use

* **Adding Items to Sale:** Click the buttons for standard products in the "Add to Sale" section. Use the "Custom Price Item" button to select a product and specify a different price and quantity.
* **Managing Current Sale:**
    * Select an item in the "Current Sale" list.
    * Click "- Qty" to decrease its quantity by one (removes if quantity becomes zero).
    * Click "Remove Item" to remove all quantities of the selected item.
    * Click "Clear Sale" to empty the current sale list.
* **Finalizing Sale:** Click "Finalize Sale". A dialog will appear to select or enter a customer name. Click "OK" to save the sale, view the receipt pop-up, and clear the current sale.
* **Managing Products:**
    * Use the "Manage Products" section to view the list of products.
    * Click "Add New Product" to add a new item via dialog boxes.
    * Select a product from the list and click "Edit Product" to modify its name/price.
    * Select a product from the list and click "Remove Product" to delete it permanently (requires confirmation).
* **Managing Customers:**
    * Click "Manage Customers" to open the customer window.
    * View existing customers in the table.
    * Enter details in the "Customer Details" section and click "Add Customer" to save a new one.
    * Click on a customer in the table to load their details into the fields above for viewing or editing. Click "Save / Update" to save changes.
    * Select a customer in the table and click "Delete Selected" to remove them (requires confirmation).
* **Viewing Sales History:**
    * Click "View History" to open the history window.
    * See recent sales, weekly/monthly summaries.
    * Use the date pickers and "View Detailed Summary" button to see product breakdowns for specific periods.
    * Select a sale from the list to view its detailed receipt.
    * Select a sale and click "Delete Selected Sale" to remove it permanently (requires confirmation).

