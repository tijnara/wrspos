import sqlite3
import os
import datetime
from tkinter import messagebox # Keep messagebox import here for DB errors shown directly

# --- Constants ---
CURRENCY_SYMBOL = "₱"
DATABASE_FILENAME = "pos_system.db" # database file

# --- Default Product Data (Used if DB is empty initially) ---
DEFAULT_PRODUCTS = {
    "Sample Prod": 75.00,
    "Sample Prod 1": 35.00,
    "Sample Prod 2": 60.00,
    "Very Long Product Name Example": 100.00, # Example for testing layout
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
            print("Adding CustomerName column to Sales table...")
            cursor.execute("ALTER TABLE Sales ADD COLUMN CustomerName TEXT DEFAULT 'N/A'")
            print("CustomerName column added.")

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
            print("Adding ContactNumber column to Customers table...")
            cursor.execute("ALTER TABLE Customers ADD COLUMN ContactNumber TEXT")
            print("ContactNumber column added.")
        if 'Address' not in customer_columns:
            print("Adding Address column to Customers table...")
            cursor.execute("ALTER TABLE Customers ADD COLUMN Address TEXT")
            print("Address column added.")
        # --- Add DateAdded column if missing ---
        if 'DateAdded' not in customer_columns:
            print("Adding DateAdded column to Customers table...")
            try:
                # Add column with default for new rows, existing rows get NULL initially
                cursor.execute("ALTER TABLE Customers ADD COLUMN DateAdded TEXT DEFAULT CURRENT_TIMESTAMP")
                # Optionally, update existing NULL rows to a specific date/time or now
                # cursor.execute("UPDATE Customers SET DateAdded = ? WHERE DateAdded IS NULL", (datetime.datetime.now().isoformat(),))
                print("DateAdded column added.")
            except sqlite3.Error as e:
                print(f"Error adding DateAdded column: {e}")


        # Populate Products if DB was just created
        if not db_exists:
             print(f"Database '{DATABASE_FILENAME}' not found. Creating tables and populating Products with defaults.")
             try:
                 cursor.execute("SELECT COUNT(*) FROM Products")
                 count = cursor.fetchone()[0]
                 if count == 0:
                     default_items = list(DEFAULT_PRODUCTS.items())
                     cursor.executemany("INSERT INTO Products (ProductName, Price) VALUES (?, ?)", default_items)
                     conn.commit()
                     print("Default products inserted.")
                 else:
                      print("Products table already had data.")
             except sqlite3.Error as e:
                 print(f"Error inserting default products: {e}")
                 conn.rollback()
        else:
             cursor.execute("SELECT COUNT(*) FROM Products")
             count = cursor.fetchone()[0]
             if count == 0:
                 print(f"Database '{DATABASE_FILENAME}' found but Products table is empty. Populating with defaults.")
                 try:
                     default_items = list(DEFAULT_PRODUCTS.items())
                     cursor.executemany("INSERT INTO Products (ProductName, Price) VALUES (?, ?)", default_items)
                     conn.commit()
                     print("Default products inserted.")
                 except sqlite3.Error as e:
                     print(f"Error inserting default products into existing empty table: {e}")
                     conn.rollback()
             else:
                 print(f"Database '{DATABASE_FILENAME}' and tables found.")
        conn.commit()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Could not initialize database.\nError: {e}")
        print(f"Database initialization error: {e}")
        raise
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
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Could not fetch products.\nError: {e}")
        print(f"Error fetching products: {e}")
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
    except sqlite3.IntegrityError:
        conn.rollback()
        messagebox.showwarning("Product Exists", f"Product '{name}' already exists in the database.")
        print(f"Attempted to insert duplicate product: {name}")
    except sqlite3.Error as e:
        conn.rollback()
        messagebox.showerror("Database Error", f"Could not add product '{name}'.\nError: {e}")
        print(f"Error inserting product {name}: {e}")
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
            print(f"Deleted product '{product_name}' from database.")
        else:
            print(f"Product '{product_name}' not found in database for deletion.")
            messagebox.showwarning("Not Found", f"Product '{product_name}' was not found in the database.")
    except sqlite3.Error as e:
        conn.rollback()
        messagebox.showerror("Database Error", f"Could not delete product '{product_name}'.\nError: {e}")
        print(f"Error deleting product {product_name}: {e}")
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
            print(f"Updated product '{original_name}' to '{new_name}', Price: {new_price:.2f}")
        else:
            print(f"Product '{original_name}' not found in database for update.")
            messagebox.showwarning("Not Found", f"Product '{original_name}' was not found in the database.")
    except sqlite3.IntegrityError:
        conn.rollback()
        messagebox.showerror("Update Error", f"Could not rename to '{new_name}'.\nA product with that name already exists.")
        print(f"Error updating product: Name '{new_name}' likely already exists.")
    except sqlite3.Error as e:
        conn.rollback()
        messagebox.showerror("Database Error", f"Could not update product '{original_name}'.\nError: {e}")
        print(f"Error updating product {original_name}: {e}")
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
        print(f"Saved sale record with ID: {sale_id} for Customer: {customer_name_to_save}")
    except sqlite3.Error as e:
        if conn: conn.rollback()
        messagebox.showerror("Database Error", f"Could not save sale record.\nError: {e}")
        print(f"Error saving sale record: {e}")
    finally:
        if conn: conn.close()
    return sale_id

def save_sale_items_records(sale_id, sale_details):
    """Saves the items for a given sale."""
    conn = None
    items_to_insert = []
    for name, details in sale_details.items():
        price = details['price']
        quantity = details['quantity']
        subtotal = price * quantity
        items_to_insert.append((sale_id, name, quantity, price, subtotal))
    if not items_to_insert: return False
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT INTO SaleItems (SaleID, ProductName, Quantity, PriceAtSale, Subtotal)
            VALUES (?, ?, ?, ?, ?)
        ''', items_to_insert)
        conn.commit()
        print(f"Saved {len(items_to_insert)} items for SaleID: {sale_id}")
        return True
    except sqlite3.Error as e:
        if conn: conn.rollback()
        messagebox.showerror("Database Error", f"Could not save sale items for SaleID {sale_id}.\nError: {e}")
        print(f"Error saving sale items for SaleID {sale_id}: {e}")
        return False
    finally:
        if conn: conn.close()

def fetch_sales_list_from_db(customer_name=None):
    """Fetches basic info for all sales, ordered oldest first.
       Optionally filters by customer name."""
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
        query += " ORDER BY SaleTimestamp ASC" # Keep oldest first for numbering
        cursor.execute(query, params)
        sales_list = cursor.fetchall()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Could not fetch sales list.\nError: {e}")
        print(f"Error fetching sales list: {e}")
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
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Could not fetch items for Sale ID {sale_id}.\nError: {e}")
        print(f"Error fetching items for Sale ID {sale_id}: {e}")
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
            ORDER BY CustomerName COLLATE NOCASE
        """)
        names = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error fetching customer names: {e}")
    finally:
        if conn: conn.close()
    return names

def fetch_all_customers():
    """Fetches all customer details (ID, name, contact, address), ordered newest first."""
    conn = None
    customers = []
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        # --- Changed ORDER BY to DateAdded DESC ---
        cursor.execute("""
            SELECT CustomerID, CustomerName, ContactNumber, Address
            FROM Customers
            WHERE CustomerName != 'N/A'
            ORDER BY DateAdded DESC
        """)
        customers = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching all customers: {e}")
        messagebox.showerror("Database Error", f"Could not fetch customer list.\nError: {e}")
    finally:
        if conn: conn.close()
    return customers


def add_customer_to_db(name, contact=None, address=None):
    """Adds a new customer to the Customers table if they don't exist.
       DateAdded will use the default CURRENT_TIMESTAMP."""
    if not name or name == 'N/A':
        print("Cannot add empty or 'N/A' customer name.")
        return False
    conn = None
    success = False
    try:
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        # DateAdded uses default, no need to specify here
        cursor.execute("INSERT OR IGNORE INTO Customers (CustomerName, ContactNumber, Address) VALUES (?, ?, ?)",
                       (name, contact, address))
        conn.commit()
        if cursor.rowcount >= 0:
            success = True
            print(f"Customer '{name}' ensured in database.")
        else:
             print(f"Failed to ensure customer '{name}' in database.")
    except sqlite3.Error as e:
        if conn: conn.rollback()
        messagebox.showerror("Database Error", f"Could not add customer '{name}'.\nError: {e}", parent=None)
        print(f"Error adding customer {name}: {e}")
    finally:
        if conn: conn.close()
    return success

def update_customer_in_db(customer_id, name, contact, address):
    """Updates details for an existing customer."""
    conn = None
    success = False
    if not name:
        print("Customer name cannot be empty for update.")
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
            print(f"Updated customer ID {customer_id} to Name: {name}")
        else:
            print(f"Customer ID {customer_id} not found for update.")
    except sqlite3.IntegrityError:
        if conn: conn.rollback()
        messagebox.showerror("Update Error", f"Could not update customer.\nAnother customer with the name '{name}' might already exist.", parent=None)
        print(f"Error updating customer ID {customer_id}: Name '{name}' likely already exists.")
    except sqlite3.Error as e:
        if conn: conn.rollback()
        messagebox.showerror("Database Error", f"Could not update customer ID {customer_id}.\nError: {e}", parent=None)
        print(f"Error updating customer ID {customer_id}: {e}")
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
            print(f"Deleted customer ID {customer_id} from database.")
        else:
            print(f"Customer ID {customer_id} not found for deletion.")
    except sqlite3.Error as e:
        if conn: conn.rollback()
        messagebox.showerror("Database Error", f"Could not delete customer ID {customer_id}.\nError: {e}", parent=None)
        print(f"Error deleting customer ID {customer_id}: {e}")
    finally:
        if conn: conn.close()
    return success


def fetch_sales_stats(start_dt_str, end_dt_exclusive_str, customer_name=None):
    """
    Fetches total revenue, total items sold, and number of sales within a date range.
    Optionally filters by customer name.
    Expects ISO format strings like 'YYYY-MM-DDTHH:MM:SS'.
    Returns a tuple: (total_revenue, total_items, num_sales)
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
        params_sales = [start_dt_str, end_dt_exclusive_str]
        params_items = [start_dt_str, end_dt_exclusive_str]

        customer_filter_sql = ""
        if customer_name and customer_name != "All Customers":
            customer_filter_sql = " AND CustomerName = ?"
            params_sales.append(customer_name)
            params_items.append(customer_name)

        query_sales = f"SELECT COALESCE(SUM(TotalAmount), 0), COUNT(SaleID) {base_sales_query} {customer_filter_sql}"
        cursor.execute(query_sales, params_sales)
        result_sales = cursor.fetchone()
        if result_sales:
            total_revenue = result_sales[0] if result_sales[0] is not None else 0.0
            num_sales = result_sales[1] if result_sales[1] is not None else 0

        query_items = f"SELECT COALESCE(SUM(Quantity), 0) {base_items_query} {customer_filter_sql}"
        cursor.execute(query_items, params_items)
        result_items = cursor.fetchone()
        if result_items:
            total_items = result_items[0] if result_items[0] is not None else 0

    except sqlite3.Error as e:
        print(f"Error fetching sales stats ({start_dt_str} to {end_dt_exclusive_str}, Customer: {customer_name}): {e}")
        return (0.0, 0, 0)
    finally:
        if conn: conn.close()

    return (total_revenue, total_items, num_sales)


def fetch_sales_summary(start_dt_str, end_dt_exclusive_str, customer_name=None):
    """
    Fetches the sum of TotalAmount for sales within a date range.
    Optionally filters by customer name.
    Expects ISO format strings like 'YYYY-MM-DDTHH:MM:SS'.
    """
    total_revenue, _, _ = fetch_sales_stats(start_dt_str, end_dt_exclusive_str, customer_name)
    return total_revenue


def fetch_product_summary_by_date_range(start_dt_str, end_dt_exclusive_str, customer_name=None):
    """
    Fetches aggregated product sales (total quantity, total revenue) within a date range.
    Optionally filters by customer name.
    Expects ISO format strings like 'YYYY-MM-DDTHH:MM:SS'.
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
    except sqlite3.Error as e:
        print(f"Error fetching product summary ({start_dt_str} to {end_dt_exclusive_str}, Customer: {customer_name}): {e}")
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
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("DELETE FROM Sales WHERE SaleID = ?", (sale_id,))
        conn.commit()
        if cursor.rowcount > 0:
            success = True
            print(f"Deleted Sale ID {sale_id} and its items from database.")
        else:
            print(f"Sale ID {sale_id} not found in database for deletion.")
    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"Error deleting Sale ID {sale_id}: {e}")
    finally:
        if conn: conn.close()
    return success
