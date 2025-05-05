import sqlite3
import os
import datetime
from tkinter import messagebox # Keep messagebox import here for DB errors shown directly
import logging # Assuming logging is used elsewhere

# --- Constants ---
CURRENCY_SYMBOL = "₱"
DATABASE_FILENAME = "pos_system.db" # database file

# --- Default Product Data (Used if DB is empty initially) ---
# Ensure key products used in UI/logic exist here if DB is new
DEFAULT_PRODUCTS = {
    "Sample Prod": 75.00,
    "Sample Prod 1": 35.00,
    "Sample Prod 2": 60.00,
    "Very Long Product Name Example": 100.00, # Example for testing layout
    "Refill (20)": 20.00,
    "Refill (25)": 25.00,
    "Custom Sale": 0.00, # Placeholder, price usually overridden
    "Container": 200.00,
    "Ice Cubes (1kg)": 20.00, # Add other products as needed
}

# --- Database Helper Functions (SQLite) ---

def initialize_db():
    """Creates the database file and tables if they don't exist."""
    db_exists = os.path.exists(DATABASE_FILENAME)
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;") # Enable foreign keys

        # Products Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Products (
                ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
                ProductName TEXT NOT NULL UNIQUE,
                Price REAL NOT NULL CHECK (Price >= 0)
            )
        ''')
        # Sales Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Sales (
                SaleID INTEGER PRIMARY KEY AUTOINCREMENT,
                SaleTimestamp TEXT NOT NULL,
                TotalAmount REAL NOT NULL CHECK (TotalAmount >= 0),
                CustomerName TEXT DEFAULT 'N/A'
            )
        ''')
        # Add CustomerName column to Sales if missing (backward compatibility)
        cursor.execute("PRAGMA table_info(Sales)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'CustomerName' not in columns:
            logging.info("Adding CustomerName column to Sales table...")
            cursor.execute("ALTER TABLE Sales ADD COLUMN CustomerName TEXT DEFAULT 'N/A'")
            logging.info("CustomerName column added.")

        # SaleItems Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS SaleItems (
                SaleItemID INTEGER PRIMARY KEY AUTOINCREMENT,
                SaleID INTEGER NOT NULL,
                ProductName TEXT NOT NULL,
                Quantity INTEGER NOT NULL CHECK (Quantity > 0),
                PriceAtSale REAL NOT NULL,
                Subtotal REAL NOT NULL,
                FOREIGN KEY (SaleID) REFERENCES Sales (SaleID) ON DELETE CASCADE
            )
        ''')
        # Customers Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Customers (
                CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
                CustomerName TEXT NOT NULL UNIQUE COLLATE NOCASE,
                ContactNumber TEXT,
                Address TEXT,
                DateAdded TEXT DEFAULT CURRENT_TIMESTAMP -- Added DateAdded column
            )
        ''')
        # Add ContactNumber, Address, and DateAdded columns if they don't exist (backward compatibility)
        cursor.execute("PRAGMA table_info(Customers)")
        customer_columns = [info[1] for info in cursor.fetchall()]
        if 'ContactNumber' not in customer_columns:
            logging.info("Adding ContactNumber column to Customers table...")
            cursor.execute("ALTER TABLE Customers ADD COLUMN ContactNumber TEXT")
            logging.info("ContactNumber column added.")
        if 'Address' not in customer_columns:
            logging.info("Adding Address column to Customers table...")
            cursor.execute("ALTER TABLE Customers ADD COLUMN Address TEXT")
            logging.info("Address column added.")
        # --- Add DateAdded column if missing ---
        if 'DateAdded' not in customer_columns:
            logging.info("Adding DateAdded column to Customers table...")
            try:
                # Add column with default for new rows, existing rows get NULL initially
                cursor.execute("ALTER TABLE Customers ADD COLUMN DateAdded TEXT DEFAULT CURRENT_TIMESTAMP")
                logging.info("DateAdded column added.")
            except sqlite3.Error as e:
                logging.error(f"Error adding DateAdded column: {e}")


        # Populate Products if DB was just created or Products table is empty
        populate_defaults = False
        if not db_exists:
             logging.info(f"Database '{DATABASE_FILENAME}' not found. Creating tables and populating Products with defaults.")
             populate_defaults = True
        else:
             cursor.execute("SELECT COUNT(*) FROM Products")
             count = cursor.fetchone()[0]
             if count == 0:
                 logging.info(f"Database '{DATABASE_FILENAME}' found but Products table is empty. Populating with defaults.")
                 populate_defaults = True
             else:
                 logging.info(f"Database '{DATABASE_FILENAME}' and tables found with existing products.")

        if populate_defaults:
            try:
                # Use INSERT OR IGNORE to avoid errors if a default product somehow exists
                default_items = list(DEFAULT_PRODUCTS.items())
                cursor.executemany("INSERT OR IGNORE INTO Products (ProductName, Price) VALUES (?, ?)", default_items)
                conn.commit()
                logging.info("Default products inserted (or ignored if existing).")
            except sqlite3.Error as e:
                logging.exception("Error inserting default products.") # Log traceback
                conn.rollback()

        conn.commit() # Commit any schema changes
    except sqlite3.Error as e:
        logging.exception("Database initialization error.") # Log traceback
        messagebox.showerror("Database Error", f"Could not initialize database.\nError: {e}")
        raise # Re-raise the exception after logging and showing message
    finally:
        if conn:
            conn.close()

def fetch_products_from_db():
    """Fetches all products from the SQLite database."""
    products = {}
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("SELECT ProductName, Price FROM Products ORDER BY ProductName")
        rows = cursor.fetchall()
        for row in rows:
            products[row[0]] = float(row[1])
        logging.debug(f"Fetched {len(products)} products from DB.")
    except sqlite3.Error as e:
        logging.exception("Error fetching products from DB.")
        messagebox.showerror("Database Error", f"Could not fetch products.\nError: {e}")
    finally:
        if conn:
            conn.close()
    return products

def insert_product_to_db(name, price):
    """Inserts a new product into the SQLite database."""
    conn = None
    success = False
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Products (ProductName, Price) VALUES (?, ?)", (name, price))
        conn.commit()
        success = True
        logging.info(f"Inserted product '{name}' with price {price:.2f} into DB.")
    except sqlite3.IntegrityError:
        # This happens if UNIQUE constraint fails (product name exists)
        conn.rollback()
        logging.warning(f"Attempted to insert duplicate product: '{name}'.")
        messagebox.showwarning("Product Exists", f"Product '{name}' already exists in the database.")
    except sqlite3.Error as e:
        conn.rollback()
        logging.exception(f"Error inserting product '{name}' into DB.")
        messagebox.showerror("Database Error", f"Could not add product '{name}'.\nError: {e}")
    finally:
        if conn:
            conn.close()
    return success

def delete_product_from_db(product_name):
    """Deletes a product from the SQLite database by name."""
    conn = None
    success = False
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Products WHERE ProductName = ?", (product_name,))
        conn.commit()
        if cursor.rowcount > 0:
            success = True
            logging.info(f"Deleted product '{product_name}' from database.")
        else:
            logging.warning(f"Product '{product_name}' not found in database for deletion.")
            messagebox.showwarning("Not Found", f"Product '{product_name}' was not found in the database.")
    except sqlite3.Error as e:
        conn.rollback()
        logging.exception(f"Error deleting product '{product_name}' from DB.")
        messagebox.showerror("Database Error", f"Could not delete product '{product_name}'.\nError: {e}")
    finally:
        if conn:
            conn.close()
    return success

def update_product_in_db(original_name, new_name, new_price):
    """Updates a product's name and price in the database."""
    conn = None
    success = False
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE Products SET ProductName = ?, Price = ? WHERE ProductName = ?",
                       (new_name, new_price, original_name))
        conn.commit()
        if cursor.rowcount > 0:
            success = True
            logging.info(f"Updated product '{original_name}' to '{new_name}', Price: {new_price:.2f}")
        else:
            # This might happen if the product was deleted between selection and update attempt
            logging.warning(f"Product '{original_name}' not found in database for update.")
            messagebox.showwarning("Not Found", f"Product '{original_name}' was not found in the database.")
    except sqlite3.IntegrityError:
        # This happens if the new_name violates the UNIQUE constraint
        conn.rollback()
        logging.warning(f"Update error for '{original_name}': Name '{new_name}' likely already exists.")
        messagebox.showerror("Update Error", f"Could not rename to '{new_name}'.\nA product with that name already exists.")
    except sqlite3.Error as e:
        conn.rollback()
        logging.exception(f"Error updating product '{original_name}' in DB.")
        messagebox.showerror("Database Error", f"Could not update product '{original_name}'.\nError: {e}")
    finally:
        if conn:
            conn.close()
    return success

# --- DB Functions for Sales ---
def save_sale_record(timestamp, total_amount, customer_name):
    """Saves a sale header record and returns the new SaleID."""
    conn = None
    sale_id = None
    timestamp_str = timestamp.isoformat()
    customer_name_to_save = customer_name if customer_name else 'N/A'
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Sales (SaleTimestamp, TotalAmount, CustomerName) VALUES (?, ?, ?)",
                       (timestamp_str, total_amount, customer_name_to_save))
        sale_id = cursor.lastrowid
        conn.commit()
        logging.info(f"Saved sale record ID: {sale_id} for Customer: '{customer_name_to_save}', Total: {total_amount:.2f}")
    except sqlite3.Error as e:
        if conn: conn.rollback()
        logging.exception("Error saving sale record header.")
        messagebox.showerror("Database Error", f"Could not save sale record.\nError: {e}")
    finally:
        if conn: conn.close()
    return sale_id

def save_sale_items_records(sale_id, sale_details):
    """Saves the items for a given sale."""
    if not sale_id:
        logging.error("Attempted to save sale items with invalid SaleID.")
        return False
    conn = None
    items_to_insert = []
    for name, details in sale_details.items():
        try:
            price = details['price']
            quantity = details['quantity']
            subtotal = price * quantity
            items_to_insert.append((sale_id, name, quantity, price, subtotal))
        except KeyError as ke:
            logging.error(f"Missing key {ke} in sale_details for item '{name}' during save.")
            continue # Skip this item
        except Exception as ex:
            logging.exception(f"Unexpected error processing item '{name}' for saving.")
            continue # Skip this item

    if not items_to_insert:
        logging.warning(f"No valid items found to insert for SaleID: {sale_id}")
        return False

    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT INTO SaleItems (SaleID, ProductName, Quantity, PriceAtSale, Subtotal)
            VALUES (?, ?, ?, ?, ?)
        ''', items_to_insert)
        conn.commit()
        logging.info(f"Saved {len(items_to_insert)} items for SaleID: {sale_id}")
        return True
    except sqlite3.Error as e:
        if conn: conn.rollback()
        logging.exception(f"Error saving sale items for SaleID {sale_id}.")
        messagebox.showerror("Database Error", f"Could not save sale items for SaleID {sale_id}.\nError: {e}")
        return False
    finally:
        if conn: conn.close()

def fetch_sales_list_from_db(customer_name=None):
    """Fetches basic info for all sales, ordered oldest first. Optionally filters by customer name."""
    conn = None
    sales_list = []
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        query = "SELECT SaleID, SaleTimestamp, TotalAmount, CustomerName FROM Sales"
        params = []
        if customer_name and customer_name != "All Customers":
            query += " WHERE CustomerName = ?"
            params.append(customer_name)
        query += " ORDER BY SaleTimestamp ASC" # Keep oldest first
        cursor.execute(query, params)
        sales_list = cursor.fetchall()
        logging.debug(f"Fetched {len(sales_list)} sales records (Customer filter: {customer_name}).")
    except sqlite3.Error as e:
        logging.exception("Error fetching sales list from DB.")
        messagebox.showerror("Database Error", f"Could not fetch sales list.\nError: {e}")
    finally:
        if conn: conn.close()
    return sales_list

def fetch_sale_items_from_db(sale_id):
    """Fetches all items for a specific SaleID."""
    conn = None
    items_list = []
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ProductName, Quantity, PriceAtSale, Subtotal
            FROM SaleItems
            WHERE SaleID = ?
            ORDER BY ProductName
        """, (sale_id,))
        items_list = cursor.fetchall()
        logging.debug(f"Fetched {len(items_list)} items for SaleID {sale_id}.")
    except sqlite3.Error as e:
        logging.exception(f"Error fetching items for Sale ID {sale_id}.")
        messagebox.showerror("Database Error", f"Could not fetch items for Sale ID {sale_id}.\nError: {e}")
    finally:
        if conn: conn.close()
    return items_list

def fetch_distinct_customer_names():
    """Fetches distinct customer names from the Customers table."""
    conn = None
    names = []
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT CustomerName
            FROM Customers
            WHERE CustomerName IS NOT NULL AND CustomerName != '' AND CustomerName != 'N/A'
            ORDER BY CustomerName COLLATE NOCASE
        """)
        names = [row[0] for row in cursor.fetchall()]
        logging.debug(f"Fetched {len(names)} distinct customer names from Customers table.")
    except sqlite3.Error as e:
        logging.exception("Error fetching distinct customer names.")
    finally:
        if conn: conn.close()
    return names

def fetch_all_customers():
    """Fetches all customer details (ID, name, contact, address), ordered newest first by DateAdded."""
    conn = None
    customers = []
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT CustomerID, CustomerName, ContactNumber, Address
            FROM Customers
            WHERE CustomerName != 'N/A' -- Exclude the placeholder
            ORDER BY DateAdded DESC
        """)
        customers = cursor.fetchall()
        logging.debug(f"Fetched {len(customers)} customer records.")
    except sqlite3.Error as e:
        logging.exception("Error fetching all customers.")
        messagebox.showerror("Database Error", f"Could not fetch customer list.\nError: {e}")
    finally:
        if conn: conn.close()
    return customers


def add_customer_to_db(name, contact=None, address=None):
    """Adds a new customer to the Customers table if they don't exist (case-insensitive)."""
    if not name or name == 'N/A':
        logging.warning("Attempted to add empty or 'N/A' customer name.")
        return False
    conn = None
    success = False
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO Customers (CustomerName, ContactNumber, Address) VALUES (?, ?, ?)",
                       (name, contact, address))
        conn.commit()
        # Check if a row was actually inserted or ignored
        if cursor.lastrowid != 0 or cursor.changes() > 0:
            logging.info(f"Customer '{name}' added or already existed (ignored).")
            success = True
        else:
             # Check explicitly if it exists now (in case OR IGNORE didn't report change but name exists)
             cursor.execute("SELECT 1 FROM Customers WHERE CustomerName = ? COLLATE NOCASE", (name,))
             if cursor.fetchone():
                 logging.info(f"Customer '{name}' already existed (checked after OR IGNORE).")
                 success = True # It exists, so consider it a success
             else:
                 logging.error(f"Failed to ensure customer '{name}' in database for unknown reason (after OR IGNORE).")
    except sqlite3.Error as e:
        if conn: conn.rollback()
        logging.exception(f"Error adding customer '{name}'.")
        messagebox.showerror("Database Error", f"Could not add customer '{name}'.\nError: {e}", parent=None)
    finally:
        if conn: conn.close()
    return success

def update_customer_in_db(customer_id, name, contact, address):
    """Updates details for an existing customer."""
    conn = None
    success = False
    if not name:
        logging.warning("Customer update failed: Name cannot be empty.")
        return False
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Customers
            SET CustomerName = ?, ContactNumber = ?, Address = ?
            WHERE CustomerID = ?
        """, (name, contact, address, customer_id))
        conn.commit()
        if cursor.rowcount > 0:
            success = True
            logging.info(f"Updated customer ID {customer_id} to Name: '{name}'")
        else:
            logging.warning(f"Customer ID {customer_id} not found for update.")
    except sqlite3.IntegrityError:
        if conn: conn.rollback()
        logging.warning(f"Update error for customer ID {customer_id}: Name '{name}' likely already exists.")
        messagebox.showerror("Update Error", f"Could not update customer.\nAnother customer with the name '{name}' might already exist.", parent=None)
    except sqlite3.Error as e:
        if conn: conn.rollback()
        logging.exception(f"Error updating customer ID {customer_id}.")
        messagebox.showerror("Database Error", f"Could not update customer ID {customer_id}.\nError: {e}", parent=None)
    finally:
        if conn: conn.close()
    return success

def delete_customer_from_db(customer_id):
    """Deletes a customer from the Customers table."""
    conn = None
    success = False
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Customers WHERE CustomerID = ?", (customer_id,))
        conn.commit()
        if cursor.rowcount > 0:
            success = True
            logging.info(f"Deleted customer ID {customer_id} from database.")
        else:
            logging.warning(f"Customer ID {customer_id} not found for deletion.")
    except sqlite3.Error as e:
        if conn: conn.rollback()
        logging.exception(f"Error deleting customer ID {customer_id}.")
        messagebox.showerror("Database Error", f"Could not delete customer ID {customer_id}.\nError: {e}", parent=None)
    finally:
        if conn: conn.close()
    return success


def fetch_sales_stats(start_dt_str, end_dt_exclusive_str, customer_name=None):
    """
    Fetches total revenue, total items sold, and number of sales within a date range.
    Optionally filters by customer name ('All Customers' means no filter).
    Expects ISO format strings like 'YYYY-MM-DDTHH:MM:SS'.
    Returns a tuple: (total_revenue, total_items, num_sales) or (0.0, 0, 0) on error.
    """
    conn = None
    total_revenue = 0.0
    total_items = 0
    num_sales = 0
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        base_sales_query = "FROM Sales WHERE SaleTimestamp >= ? AND SaleTimestamp < ?"
        base_items_query = "FROM SaleItems JOIN Sales ON SaleItems.SaleID = Sales.SaleID WHERE Sales.SaleTimestamp >= ? AND Sales.SaleTimestamp < ?"
        params = [start_dt_str, end_dt_exclusive_str]

        customer_filter_sql = ""
        if customer_name and customer_name != "All Customers":
            customer_filter_sql = " AND CustomerName = ?"
            params.append(customer_name)

        query_sales = f"SELECT COALESCE(SUM(TotalAmount), 0), COUNT(SaleID) {base_sales_query} {customer_filter_sql}"
        cursor.execute(query_sales, params)
        result_sales = cursor.fetchone()
        if result_sales:
            total_revenue = result_sales[0] if result_sales[0] is not None else 0.0
            num_sales = result_sales[1] if result_sales[1] is not None else 0

        query_items = f"SELECT COALESCE(SUM(Quantity), 0) {base_items_query} {customer_filter_sql}"
        cursor.execute(query_items, params)
        result_items = cursor.fetchone()
        if result_items:
            total_items = result_items[0] if result_items[0] is not None else 0

        logging.debug(f"Fetched sales stats ({start_dt_str} to {end_dt_exclusive_str}, Customer: {customer_name}): Rev={total_revenue:.2f}, Items={total_items}, Sales={num_sales}")

    except sqlite3.Error as e:
        logging.exception(f"Error fetching sales stats ({start_dt_str} to {end_dt_exclusive_str}, Customer: {customer_name})")
        return (0.0, 0, 0)
    finally:
        if conn: conn.close()

    return (total_revenue, total_items, num_sales)


def fetch_sales_summary(start_dt_str, end_dt_exclusive_str, customer_name=None):
    """
    DEPRECATED: Use fetch_sales_stats instead.
    Fetches the sum of TotalAmount for sales within a date range.
    """
    logging.warning("fetch_sales_summary is deprecated. Use fetch_sales_stats.")
    total_revenue, _, _ = fetch_sales_stats(start_dt_str, end_dt_exclusive_str, customer_name)
    return total_revenue


def fetch_product_summary_by_date_range(start_dt_str, end_dt_exclusive_str, customer_name=None):
    """
    Fetches aggregated product sales (total quantity, total revenue) within a date range.
    Optionally filters by customer name ('All Customers' means no filter).
    """
    conn = None
    summary_data = []
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        query = """
            SELECT
                si.ProductName,
                SUM(si.Quantity) as TotalQuantity,
                SUM(si.Subtotal) as TotalRevenue
            FROM SaleItems si
            JOIN Sales s ON si.SaleID = s.SaleID
            WHERE s.SaleTimestamp >= ? AND s.SaleTimestamp < ?
        """
        params = [start_dt_str, end_dt_exclusive_str]
        if customer_name and customer_name != "All Customers":
            query += " AND s.CustomerName = ?"
            params.append(customer_name)

        query += """
            GROUP BY si.ProductName
            ORDER BY si.ProductName COLLATE NOCASE
        """
        cursor.execute(query, params)
        summary_data = cursor.fetchall()
        logging.debug(f"Fetched product summary ({start_dt_str} to {end_dt_exclusive_str}, Customer: {customer_name}). Found {len(summary_data)} products.")
    except sqlite3.Error as e:
        logging.exception(f"Error fetching product summary ({start_dt_str} to {end_dt_exclusive_str}, Customer: {customer_name})")
        messagebox.showerror("Database Error", f"Could not fetch product summary.\nError: {e}")
    finally:
        if conn: conn.close()
    return summary_data


def delete_sale_from_db(sale_id):
    """Deletes a sale and its associated items from the database."""
    conn = None
    success = False
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;") # Ensure cascade delete works
        cursor.execute("DELETE FROM Sales WHERE SaleID = ?", (sale_id,))
        conn.commit()
        if cursor.rowcount > 0:
            success = True
            logging.info(f"Deleted Sale ID {sale_id} and its items (via cascade) from database.")
        else:
            logging.warning(f"Sale ID {sale_id} not found in database for deletion.")
    except sqlite3.Error as e:
        if conn: conn.rollback()
        logging.exception(f"Error deleting Sale ID {sale_id}.")
        # Avoid showing messagebox here; let caller handle UI feedback
    finally:
        if conn: conn.close()
    return success

def fetch_sales_summary_by_customer(start_dt_str, end_dt_exclusive_str):
    """
    Fetches aggregated sales totals grouped by customer name within a date range.

    Args:
        start_dt_str: ISO format start timestamp (inclusive).
        end_dt_exclusive_str: ISO format end timestamp (exclusive).

    Returns:
        A list of tuples: [(CustomerName, TotalSalesAmount), ...],
        sorted by CustomerName (case-insensitive). Returns empty list on error.
    """
    conn = None
    summary_data = []
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        query = """
            SELECT
                CustomerName,
                SUM(TotalAmount) as TotalSales
            FROM Sales
            WHERE SaleTimestamp >= ? AND SaleTimestamp < ?
            GROUP BY CustomerName COLLATE NOCASE -- Group case-insensitively
            ORDER BY CustomerName COLLATE NOCASE -- Order case-insensitively
        """
        params = [start_dt_str, end_dt_exclusive_str]
        cursor.execute(query, params)
        summary_data = cursor.fetchall()
        logging.info(f"Fetched sales summary by customer for {start_dt_str} to {end_dt_exclusive_str}. Found {len(summary_data)} customers.")
    except sqlite3.Error as e:
        logging.exception(f"Error fetching sales summary by customer ({start_dt_str} to {end_dt_exclusive_str})")
    finally:
        if conn:
            conn.close()
    return summary_data

def fetch_customer_purchase_details_by_date(customer_name, start_dt_str, end_dt_exclusive_str):
    """
    Fetches detailed product purchases for a specific customer within a date range.

    Args:
        customer_name: The name of the customer.
        start_dt_str: ISO format start timestamp (inclusive).
        end_dt_exclusive_str: ISO format end timestamp (exclusive).

    Returns:
        A list of tuples: [(SaleTimestamp, ProductName, Quantity, PriceAtSale, Subtotal), ...],
        sorted by SaleTimestamp. Returns empty list on error.
    """
    conn = None
    purchase_details = []
    if not customer_name:
        logging.warning("Attempted to fetch purchase details with no customer name.")
        return purchase_details

    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        query = """
            SELECT
                s.SaleTimestamp,
                si.ProductName,
                si.Quantity,
                si.PriceAtSale,
                si.Subtotal
            FROM SaleItems si
            JOIN Sales s ON si.SaleID = s.SaleID
            WHERE s.CustomerName = ? COLLATE NOCASE -- Match customer case-insensitively
              AND s.SaleTimestamp >= ?
              AND s.SaleTimestamp < ?
            ORDER BY s.SaleTimestamp ASC -- Show oldest first for history
        """
        params = [customer_name, start_dt_str, end_dt_exclusive_str]
        cursor.execute(query, params)
        purchase_details = cursor.fetchall()
        logging.info(f"Fetched {len(purchase_details)} purchase detail items for customer '{customer_name}' between {start_dt_str} and {end_dt_exclusive_str}.")
    except sqlite3.Error as e:
        logging.exception(f"Error fetching purchase details for customer '{customer_name}'")
    finally:
        if conn:
            conn.close()
    return purchase_details


def fetch_all_customer_purchase_details(customer_name):
    """
    Fetches all detailed product purchases for a specific customer across all time.

    Args:
        customer_name: The name of the customer.

    Returns:
        A list of tuples: [(SaleTimestamp, ProductName, Quantity, PriceAtSale, Subtotal), ...],
        sorted by SaleTimestamp (oldest first). Returns empty list on error or if no customer name.
    """
    conn = None
    purchase_details = []
    if not customer_name:
        logging.warning("Attempted to fetch all purchase details with no customer name.")
        return purchase_details

    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        query = """
            SELECT
                s.SaleTimestamp,
                si.ProductName,
                si.Quantity,
                si.PriceAtSale,
                si.Subtotal
            FROM SaleItems si
            JOIN Sales s ON si.SaleID = s.SaleID
            WHERE s.CustomerName = ? COLLATE NOCASE -- Match customer case-insensitively
            ORDER BY s.SaleTimestamp ASC -- Show oldest first for history
        """
        params = [customer_name]
        cursor.execute(query, params)
        purchase_details = cursor.fetchall()
        logging.info(f"Fetched all ({len(purchase_details)}) purchase detail items for customer '{customer_name}'.")
    except sqlite3.Error as e:
        logging.exception(f"Error fetching all purchase details for customer '{customer_name}'")
        # Avoid showing messagebox here, let the calling GUI handle UI feedback
    finally:
        if conn:
            conn.close()
    return purchase_details

def fetch_latest_customer_name():
    """Fetches the CustomerName from the most recent sale record (excluding 'N/A')."""
    conn = None
    customer_name = None
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        # Order by SaleID DESC assuming higher ID means newer sale
        cursor.execute("""
            SELECT CustomerName
            FROM Sales
            WHERE CustomerName IS NOT NULL AND CustomerName != 'N/A'
            ORDER BY SaleID DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        if result:
            customer_name = result[0]
            logging.debug(f"Fetched latest used customer name: '{customer_name}'")
        else:
            logging.debug("No previous customer sales found (excluding N/A).")
    except sqlite3.Error as e:
        logging.exception("Error fetching latest customer name.")
    finally:
        if conn:
            conn.close()
    return customer_name

