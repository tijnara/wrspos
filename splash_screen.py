import tkinter as tk
from tkinter import ttk

class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Loading...")
        self.geometry("400x300")
        self.overrideredirect(True)  # Remove window decorations
        self.configure(bg="#4CAF50")

        # Center the splash screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (400 // 2)
        y = (screen_height // 2) - (300 // 2)
        self.geometry(f"400x300+{x}+{y}")

        # Add app name and logo
        tk.Label(self, text="Seaside POS", font=("Arial", 20, "bold"), bg="#4CAF50", fg="white").pack(pady=20)
        tk.Label(self, text="Loading, please wait...", font=("Arial", 12), bg="#4CAF50", fg="white").pack(pady=10)

        # Add a progress bar
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(pady=20, padx=50, fill="x")
        self.progress.start(10)

        self.after(3000, self.destroy)  # Close splash screen after 3 seconds

# Example usage
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    splash = SplashScreen(root)
    splash.mainloop()
    root.deiconify()  # Show the main window after splash screen
