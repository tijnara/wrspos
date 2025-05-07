import tkinter as tk
from tkinter import ttk
import logging
from dateutil.relativedelta import relativedelta, MO, SU
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import gui_utils  # For set_window_icon

# --- Constants ---
DATE_FORMAT_DISPLAY = "%Y-%m-%d"  # Example, adjust if needed


class SalesHistoryCharts(tk.Toplevel):
    def __init__(self, parent, db_operations):
        super().__init__(parent)
        self.parent = parent
        self.db_operations = db_operations
        self.title("Sales Charts")
        gui_utils.set_window_icon(self)  # Set icon

        # Initial size, can be resized by user
        self.geometry("800x600")
        self.minsize(600, 400)  # Set a minimum practical size

        # Make the window resizable
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()  # Make it modal
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        # Configure the main Toplevel window's grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self)
        # Use grid for the notebook and make it expand
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.weekly_tab = ttk.Frame(self.notebook)
        self.monthly_tab = ttk.Frame(self.notebook)

        # Configure tabs to expand their content
        self.weekly_tab.columnconfigure(0, weight=1)
        self.weekly_tab.rowconfigure(0, weight=1)
        self.monthly_tab.columnconfigure(0, weight=1)
        self.monthly_tab.rowconfigure(0, weight=1)

        self.notebook.add(self.weekly_tab, text="Weekly Sales")
        self.notebook.add(self.monthly_tab, text="Monthly Sales")

        self._setup_weekly_chart()
        self._setup_monthly_chart()

        self.update_charts()

    def _setup_weekly_chart(self):
        """Sets up the weekly sales bar chart."""
        # Figure and Axes
        self.weekly_fig, self.weekly_ax = plt.subplots(figsize=(7, 3.5), dpi=100)  # Adjusted figsize slightly
        self.weekly_ax.set_xlabel("Week Start Date")
        self.weekly_ax.set_ylabel("Sales")
        self.weekly_ax.set_title("Weekly Sales")
        self.weekly_ax.grid(True)
        self.weekly_fig.tight_layout()  # Helps with fitting labels, titles

        # Canvas to embed Matplotlib in Tkinter
        self.weekly_canvas = FigureCanvasTkAgg(self.weekly_fig, master=self.weekly_tab)
        self.weekly_canvas_widget = self.weekly_canvas.get_tk_widget()
        # Use grid for the canvas widget and make it expand
        self.weekly_canvas_widget.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.weekly_canvas.draw()

    def _setup_monthly_chart(self):
        """Sets up the monthly sales bar chart."""
        self.monthly_fig, self.monthly_ax = plt.subplots(figsize=(7, 3.5), dpi=100)  # Adjusted figsize
        self.monthly_ax.set_xlabel("Month")
        self.monthly_ax.set_ylabel("Sales")
        self.monthly_ax.set_title("Monthly Sales")
        self.monthly_ax.grid(True)
        self.monthly_fig.tight_layout()

        self.monthly_canvas = FigureCanvasTkAgg(self.monthly_fig, master=self.monthly_tab)
        self.monthly_canvas_widget = self.monthly_canvas.get_tk_widget()
        self.monthly_canvas_widget.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.monthly_canvas.draw()

    def update_charts(self):
        """Updates both weekly and monthly charts with data from the database."""
        self.update_weekly_chart()
        self.update_monthly_chart()
        # Redraw canvases after updating data
        if hasattr(self, 'weekly_canvas'): self.weekly_canvas.draw_idle()
        if hasattr(self, 'monthly_canvas'): self.monthly_canvas.draw_idle()

    def update_weekly_chart(self):
        """Updates the weekly sales bar chart with data from the database."""
        logging.debug("Updating weekly sales chart.")
        today = datetime.date.today()
        weekly_sales = {}
        # Fetch for the last 5 weeks including the current week
        for i in range(5):
            # MO(-i) means: current Monday if i=0, last Monday if i=1, etc.
            start_of_week = today + relativedelta(weekday=MO(-i))
            end_of_week = start_of_week + relativedelta(days=6)  # Sunday of that week

            start_week_str = datetime.datetime.combine(start_of_week, datetime.time.min).isoformat()
            # Exclusive end: start of the day AFTER end_of_week
            end_week_exclusive_str = (
                datetime.datetime.combine(end_of_week + datetime.timedelta(days=1), datetime.time.min)).isoformat()

            weekly_revenue, _, _ = self.db_operations.fetch_sales_stats(
                start_week_str, end_week_exclusive_str)
            weekly_sales[start_of_week.strftime(DATE_FORMAT_DISPLAY)] = weekly_revenue

        # Sort by date (keys) to ensure correct order on chart
        sorted_weekly_sales = dict(sorted(weekly_sales.items()))
        dates = list(sorted_weekly_sales.keys())
        sales_values = list(sorted_weekly_sales.values())

        self.weekly_ax.clear()  # Clear previous plot
        self.weekly_ax.bar(dates, sales_values)
        self.weekly_ax.set_xlabel("Week Start Date")
        self.weekly_ax.set_ylabel("Sales")
        self.weekly_ax.set_title("Weekly Sales")
        self.weekly_ax.grid(True)
        self.weekly_fig.autofmt_xdate(rotation=30, ha='right')  # Rotate x-axis labels for better readability
        self.weekly_fig.tight_layout()  # Adjust layout
        # self.weekly_canvas.draw_idle() # Moved to update_charts
        logging.debug("Weekly sales chart updated.")

    def update_monthly_chart(self):
        """Updates the monthly sales bar chart with data from the database."""
        logging.debug("Updating monthly sales chart.")
        today = datetime.date.today()
        monthly_sales = {}
        # Fetch for the last 6 months including the current month
        for i in range(6):
            # First day of the month, i months ago
            first_day_of_month = (today + relativedelta(months=-i)).replace(day=1)
            # Last day of that month
            next_month = (today + relativedelta(months=-i + 1)).replace(day=1)
            last_day_of_month = next_month - datetime.timedelta(days=1)

            start_month_str = datetime.datetime.combine(first_day_of_month, datetime.time.min).isoformat()
            # Exclusive end: start of the day AFTER last_day_of_month
            end_month_exclusive_str = (datetime.datetime.combine(last_day_of_month + datetime.timedelta(days=1),
                                                                 datetime.time.min)).isoformat()

            monthly_revenue, _, _ = self.db_operations.fetch_sales_stats(
                start_month_str, end_month_exclusive_str)
            monthly_sales[first_day_of_month.strftime("%Y-%m")] = monthly_revenue

        # Sort by month (keys)
        sorted_monthly_sales = dict(sorted(monthly_sales.items()))
        months = list(sorted_monthly_sales.keys())
        sales_values = list(sorted_monthly_sales.values())

        self.monthly_ax.clear()  # Clear previous plot
        self.monthly_ax.bar(months, sales_values)
        self.monthly_ax.set_xlabel("Month")
        self.monthly_ax.set_ylabel("Sales")
        self.monthly_ax.set_title("Monthly Sales")
        self.monthly_ax.grid(True)
        self.monthly_fig.autofmt_xdate(rotation=30, ha='right')  # Rotate x-axis labels
        self.monthly_fig.tight_layout()  # Adjust layout
        # self.monthly_canvas.draw_idle() # Moved to update_charts
        logging.debug("Monthly sales chart updated.")

    def destroy(self):
        """Clean up Matplotlib figures before destroying the window."""
        logging.debug("Destroying SalesHistoryCharts window and Matplotlib figures.")
        if hasattr(self, 'weekly_fig'):
            plt.close(self.weekly_fig)
        if hasattr(self, 'monthly_fig'):
            plt.close(self.monthly_fig)
        super().destroy()
