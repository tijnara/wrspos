import tkinter as tk
from tkinter import ttk
import logging
from dateutil.relativedelta import relativedelta, MO, SU
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- Constants ---
DATE_FORMAT_DISPLAY = "%Y-%m-%d"

class SalesHistoryCharts(tk.Toplevel):
    def __init__(self, parent, db_operations):
        super().__init__(parent)
        self.parent = parent
        self.db_operations = db_operations
        self.title("Sales Charts")
        self.geometry("800x600")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.weekly_tab = ttk.Frame(self.notebook)
        self.monthly_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.weekly_tab, text="Weekly Sales")
        self.notebook.add(self.monthly_tab, text="Monthly Sales")

        self._setup_weekly_chart()
        self._setup_monthly_chart()

        self.update_charts()

    def _setup_weekly_chart(self):
        """Sets up the weekly sales bar chart."""
        self.weekly_fig, self.weekly_ax = plt.subplots(figsize=(8, 4), dpi=100)
        self.weekly_ax.set_xlabel("Week Start Date")
        self.weekly_ax.set_ylabel("Sales")
        self.weekly_ax.set_title("Weekly Sales")
        self.weekly_ax.grid(True)

        self.weekly_canvas = FigureCanvasTkAgg(
            self.weekly_fig, master=self.weekly_tab)
        self.weekly_canvas.draw()
        self.weekly_canvas.get_tk_widget().pack(
            side=tk.TOP, fill=tk.BOTH, expand=1)

    def _setup_monthly_chart(self):
        """Sets up the monthly sales bar chart."""
        self.monthly_fig, self.monthly_ax = plt.subplots(figsize=(8, 4), dpi=100)
        self.monthly_ax.set_xlabel("Month")
        self.monthly_ax.set_ylabel("Sales")
        self.monthly_ax.set_title("Monthly Sales")
        self.monthly_ax.grid(True)

        self.monthly_canvas = FigureCanvasTkAgg(
            self.monthly_fig, master=self.monthly_tab)
        self.monthly_canvas.draw()
        self.monthly_canvas.get_tk_widget().pack(
            side=tk.TOP, fill=tk.BOTH, expand=1)

    def update_charts(self):
        """Updates both weekly and monthly charts with data from the database."""
        self.update_weekly_chart()
        self.update_monthly_chart()

    def update_weekly_chart(self):
        """Updates the weekly sales bar chart with data from the database."""
        logging.debug("Updating weekly sales chart.")
        today = datetime.date.today()
        weekly_sales = {}
        for i in range(5):  # Get the last 5 weeks
            start_of_week = today + relativedelta(weekday=MO(-i))
            end_of_week = start_of_week + relativedelta(days=6)
            start_week_str = datetime.datetime.combine(
                start_of_week, datetime.time.min).isoformat()
            end_week_str = (datetime.datetime.combine(
                end_of_week, datetime.time.min) + datetime.timedelta(days=1)).isoformat()
            weekly_revenue, _, _ = self.db_operations.fetch_sales_stats(
                start_week_str, end_week_str)
            weekly_sales[start_of_week.strftime(
                DATE_FORMAT_DISPLAY)] = weekly_revenue

        dates = list(weekly_sales.keys())
        sales_values = list(weekly_sales.values())

        self.weekly_ax.clear()
        self.weekly_ax.bar(dates, sales_values)
        self.weekly_ax.set_xlabel("Week Start Date")
        self.weekly_ax.set_ylabel("Sales")
        self.weekly_ax.set_title("Weekly Sales")
        self.weekly_ax.grid(True)
        self.weekly_fig.autofmt_xdate()
        self.weekly_canvas.draw()
        logging.debug("Weekly sales chart updated.")

    def update_monthly_chart(self):
        """Updates the monthly sales bar chart with data from the database."""
        logging.debug("Updating monthly sales chart.")
        today = datetime.date.today()
        monthly_sales = {}
        for i in range(6):  # Get the last 6 months
            first_day_of_month = today + relativedelta(months=-i, day=1)
            last_day_of_month = today + \
                relativedelta(months=-i, day=31)  # Not precise, but good enough for most months
            start_month_str = datetime.datetime.combine(
                first_day_of_month, datetime.time.min).isoformat()
            end_month_str = (datetime.datetime.combine(
                last_day_of_month, datetime.time.min) + datetime.timedelta(days=1)).isoformat()
            monthly_revenue, _, _ = self.db_operations.fetch_sales_stats(
                start_month_str, end_month_str)
            monthly_sales[first_day_of_month.strftime(
                "%Y-%m")] = monthly_revenue  # Use year-month as label

        months = list(monthly_sales.keys())
        sales_values = list(monthly_sales.values())

        self.monthly_ax.clear()
        self.monthly_ax.bar(months, sales_values)
        self.monthly_ax.set_xlabel("Month")
        self.monthly_ax.set_ylabel("Sales")
        self.monthly_ax.set_title("Monthly Sales")
        self.monthly_ax.grid(True)
        self.monthly_fig.autofmt_xdate()
        self.monthly_canvas.draw()
        logging.debug("Monthly sales chart updated.")

