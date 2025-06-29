import tkinter as tk
import ctypes
import os
import struct
import math
import pymem
import json
from tkinter import ttk
from PIL import Image, ImageTk
from memhack import read_game_memory

# Load config file
with open("config.json", "r") as file:
    config = json.load(file)

# Load data from config
PRODUCTS_DATA = config["products"]
ISLAND_GROUPS = config["island_groups"]
PLAYER_SETTINGS = config["player_settings"]

# Use loaded data
class Products:
    DATA = PRODUCTS_DATA
    NAMES = list(DATA.keys())

class IslandGroups:
    GROUPS = ISLAND_GROUPS

    @classmethod
    def get_group(cls, market_name):
        for group, islands in cls.GROUPS.items():
            if market_name in islands:
                return group
        return None

# =============================================================================
# Core Classes
# =============================================================================

class Product:
    """Represents a product and its pricing/supply calculations."""
    def __init__(self, name, supply_address, pm, limit):
        self.name = name
        self.supply_address = supply_address
        self.pm = pm
        self.limit = limit
        self.volume, self.weight, self.raw_price = Products.DATA[name]
        self.update_product()

    def update_product(self, conversion_rate=311):
        self.supply = read_game_memory(self.pm, self.supply_address, 'float')
        self.amnt = max(0, math.floor(self.supply - self.limit + 1))
        self.base_price = self.raw_price * conversion_rate
        self.sell_price = self.calc_sell_price(self.supply)
        self.buy_price = math.ceil(self.sell_price * 1.023)
        
    def calc_sell_price(self, supply):
        V = self.base_price
        coeff = 0.38 if supply > 0.5 else -1.68
        price = (coeff * V / 10000) * (supply ** 2) - (abs(coeff) * V / 50) * supply + V
        return math.ceil(price)

    def calculate_buy_mult(self, quantity):
        total = sum(math.ceil(self.calc_sell_price(self.supply - i) * 1.023)
                    for i in range(quantity))
        return total

    def calculate_sell_mult(self, quantity):
        total = sum(math.ceil(self.calc_sell_price(self.supply + i))
                    for i in range(quantity))
        return total

    def max_quantity(self, player, quantity_type="principal"):
        if quantity_type == "mass":
            return math.floor(player.mass_limit / self.weight)
        elif quantity_type == "volume":
            return math.floor(player.volume_limit / self.volume)
        elif quantity_type == "principal":
            i, total_cost = 0, 0
            while i < self.amnt:
                cost = math.ceil(self.calc_sell_price(self.supply - i) * 1.023)
                total_cost += cost
                if total_cost > player.principal:
                    break
                i += 1
            return i

    def max_quantity_mass(self, player):
        return self.max_quantity(player, "mass")

    def max_quantity_volume(self, player):
        return self.max_quantity(player, "volume")

    def max_quantity_principal(self, player):
        return self.max_quantity(player, "principal")

class Market:
    """Represents a market in the game."""
    def __init__(self, pm, base):
        self.pm = pm
        self.base = base
        self.name = self._get_market_name()
        self.index = read_game_memory(pm, pm.read_longlong(base + 0x38) + 0x58, 'int')
        self.limit = read_game_memory(pm, base + 0x4C, 'float')
        self.products = self._init_products()

    def _get_market_name(self):
        try:
            addr_ptr = self.pm.read_longlong(self.base + 0x38)
            addr = self.pm.read_longlong(addr_ptr + 0x18)
            length = struct.unpack("<I", self.pm.read_bytes(addr + 0x10, 4))[0]
            raw = self.pm.read_bytes(addr + 0x14, length * 2)
            return raw[::2][:length].decode('utf-8', errors='ignore')
        except Exception:
            return "Unknown Market"

    def _init_products(self):
        base_addr = self.pm.read_longlong(self.base + 0x20) + 0x24
        return [Product(name, base_addr + i * 4, self.pm, self.limit)
                for i, name in enumerate(Products.NAMES)]

    def update_products(self, conversion_rate):
        for product in self.products:
            product.update_product(conversion_rate)

class Player:
    def __init__(self):
        self.principal = PLAYER_SETTINGS["principal"]
        self.conversion_rate = PLAYER_SETTINGS["conversion_rate"]
        self.mass_limit = PLAYER_SETTINGS["mass_limit"]
        self.volume_limit = PLAYER_SETTINGS["volume_limit"]
        self.min_profit = PLAYER_SETTINGS["min_profit"]

    def update(self, principal, conversion_rate, mass_limit, volume_limit, min_profit):
        self.principal = principal
        self.conversion_rate = conversion_rate
        self.mass_limit = mass_limit
        self.volume_limit = volume_limit
        self.min_profit = min_profit

    def __repr__(self):
        # Print float values without decimals
        return (f"Player:\n Principal: {self.principal:.0f}\n Currency: {self.conversion_rate}\n "
                f"Mass: {self.mass_limit:.0f}\n Volume: {self.volume_limit:.0f}")

# =============================================================================
# Helper Functions
# =============================================================================

def find_markets(pm, status_label, root, markets, update_chart_button):
    """
    Scan memory for market addresses using a specified pattern.
    Updates the GUI status label with results.
    """
    status_label.config(text="🔍 Scanning for Markets...")
    root.update_idletasks()
    print('🔍 Scanning for Markets...')
    PATTERN = rb"..\x00\x00\x80\x3F\x00\x00.\x42.\x00\x00\x00\x6F\x12\x83\x3A\x00\x00\x80\x3F"
    markets.clear()
    markets.extend([Market(pm, addr - 0x4E) for addr in pm.pattern_scan_all(PATTERN, return_multiple=True)])
    
    if len(markets) != 27:
        print(f'⚠️ Found {len(markets)} markets. Exiting...')
        status_label.config(text="⚠️ Error: Market scan failed")
        return []
    
    print(f'✅ Found {len(markets)} markets.')
    status_label.config(text=f"✅ Found {len(markets)} markets.")
    for market in markets:
        print(f"{hex(market.base)}  {market.index:02} {market.name}")
    update_chart()
    return markets

def calculate_trade_metrics(start_market, end_market, product, player):
    start_product = next((p for p in start_market.products if p.name == product.name), None)
    end_product = next((p for p in end_market.products if p.name == product.name), None)
    if not start_product or not end_product:
        return None
    max_qty = min(
        start_product.max_quantity(player, "principal"),
        start_product.max_quantity(player, "mass"),
        start_product.max_quantity(player, "volume"),
        math.floor((abs(start_product.supply - end_product.supply) / 2))
    )
    if max_qty == 0:
        return None
    total_buy_price = start_product.calculate_buy_mult(max_qty)
    total_sell_price = end_product.calculate_sell_mult(max_qty)
    profit = total_sell_price - total_buy_price
    profit_per_pound = profit / (start_product.weight * max_qty) if start_product.weight else 0
    profit_per_item = profit / max_qty if max_qty else 0
    return {
        "Start Market": start_market.name,
        "End Market": end_market.name,
        "Product": product.name,
        "Qnty": f"{max_qty}/{start_product.amnt}",
        "$_Buy": total_buy_price,
        "$_Sell": total_sell_price,
        "$Profit": profit,
        "$/Pound": round(profit_per_pound, 1),
        "$/Item": round(profit_per_item, 1)
    }

def generate_trade_routes(start_groups, end_groups, player, markets):
    trade_routes = []
    start_markets = [m for m in markets if IslandGroups.get_group(m.name) in start_groups]
    end_markets = [m for m in markets if IslandGroups.get_group(m.name) in end_groups]
    for start_market in start_markets:
        for end_market in end_markets:
            if start_market != end_market:
                for product in start_market.products:
                    metrics = calculate_trade_metrics(start_market, end_market, product, player)
                    if metrics and metrics["$Profit"] > player.min_profit:
                        trade_routes.append(metrics)
    return trade_routes

# =============================================================================
# GUI Helper Functions
# =============================================================================

def update_values():
    try:
        player.update(**{key: float(var.get()) for key, var in {
            "principal": player_principal_var, "conversion_rate": conversion_rate_var,
            "mass_limit": weight_limit_var, "volume_limit": volume_limit_var, "min_profit": min_profit_var
        }.items()})
        print("Updated", player)
    except ValueError:
        print("Invalid input! Please enter numeric values.")

def update_chart():
    start_groups = [f"{name} (Group {idx+1})" for idx, name in enumerate(island_names)
                    if start_group_vars[name].get() == 1]
    end_groups = [f"{name} (Group {idx+1})" for idx, name in enumerate(island_names)
                  if end_group_vars[name].get() == 1]

    for market in markets:
        market.update_products(player.conversion_rate)

    # Generate, sort, and insert trade routes into the treeview
    trade_routes = sorted(generate_trade_routes(start_groups, end_groups, player, markets), 
                          key=lambda x: (x["Start Market"], -x["$Profit"]))
    
    tree.delete(*tree.get_children())
    for route in trade_routes:
        tree.insert("", "end", values=[route[k] for k in ["Start Market", "End Market", "Product", 
                                                         "Qnty", "$_Buy", "$_Sell", "$Profit", "$/Pound", "$/Item"]])

def update_loop():
    update_chart()
    root.after(5000, update_loop)

# Function to scroll 5 lines at a time
def on_mouse_wheel(event, tree):
    # Detect the direction of the scroll and move by 5 lines
    if event.delta > 0:  # Scroll up
        tree.yview_scroll(-5, "units")
    else:  # Scroll down
        tree.yview_scroll(5, "units")

def create_tooltip(widget, text):
    """Create a simple tooltip for a given widget."""
    # Define the tooltip style only once
    ttk.Style().configure('Tooltip.TLabel', background='#e0f3ff', foreground='#2c3e50', relief='solid', borderwidth=0, font=('Tahoma', 8))

    def show_tip(event):
        if hasattr(widget, "tooltip_window") and widget.tooltip_window.winfo_exists():
            return
        widget.tooltip_window = tk.Toplevel(widget)
        widget.tooltip_window.wm_overrideredirect(True)
        widget.tooltip_window.wm_geometry(f"+{event.x_root + 25}+{event.y_root - 5}")
        ttk.Label(widget.tooltip_window, text=text, style='Tooltip.TLabel', padding=3).pack()

    def hide_tip(event):
        if hasattr(widget, "tooltip_window"):
            widget.tooltip_window.destroy()
            del widget.tooltip_window

    widget.bind("<Enter>", show_tip)
    widget.bind("<Leave>", hide_tip)

def create_group_checkboxes(parent, names, default_func, label_text):
    """Creates a labeled group of checkboxes with default values."""
    ttk.Label(parent, text=label_text).grid(row=0, column=0, columnspan=2, sticky="w", padx=3, pady=3)
    vars_dict = {name: tk.IntVar(value=default_func(name)) for name in names}
    half = (len(names) + 1) // 2  
    for idx, (name, var) in enumerate(vars_dict.items()):
        ttk.Checkbutton(parent, text=name, variable=var, command=update_chart).grid(
            row=(idx % half) + 1, column=idx // half, sticky="w", padx=10, pady=2
        )
    return vars_dict

# =============================================================================
# Main GUI Setup Using Grid Layout
# =============================================================================

# Clear console and print header
os.system('cls' if os.name == 'nt' else 'clear')
print('=== Island Market Scanner ===')

# Hook to Sailwind.exe
try:
    process_name = 'Sailwind.exe'
    pm = pymem.Pymem(process_name)  # Try to attach to Sailwind.exe
except pymem.exception.ProcessNotFound:
    # If the game is not running, display an error and exit
    print(f"Error: {process_name} is not running. Please start the game and try again.")
    exit()

# Set AppUserModelID for taskbar icon on Windows
myappid = u'mycompany.myproduct.subproduct.version'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# Main GUI Window
root = tk.Tk()
root.title("Sailwind Market Scanner")
root.geometry("720x600")
root.minsize(720, 400)

# Load the icon image using PIL
icon = Image.open("boat.ico")
icon = ImageTk.PhotoImage(icon)
root.iconphoto(True, icon)

style = ttk.Style(root)
style.theme_use('clam')

# Configure grid rows on the root window:
root.grid_rowconfigure(0, weight=0)
root.grid_rowconfigure(1, weight=0)
root.grid_rowconfigure(2, weight=1)
root.grid_rowconfigure(3, weight=0)
root.grid_columnconfigure(0, weight=1)

# -------------------------------
# Row 0: Scan Button and Status Label
# -------------------------------
button_frame = ttk.Frame(root, padding="3")
button_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=3)

player = Player()
print(player)  # Print player information for debugging
markets = []
start_button = ttk.Button(button_frame, text="Scan For Markets", 
                          command=lambda: find_markets(pm, status_label, root, markets, update_chart_button))
start_button.grid(row=0, column=0, sticky="w", padx=(0, 10))

status_label = ttk.Label(button_frame, text="", font=("Arial", 10))
status_label.grid(row=0, column=1, sticky="w")

# ---------------------
# Row 1: Player Inputs
# ---------------------
top_frame = ttk.Frame(root, padding="8")
top_frame.grid(row=1, column=0, sticky="ew")

# Left: Player Inputs Frame
player_frame = ttk.LabelFrame(top_frame, text="Player Inputs", padding="8")
player_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

# Default values from player
player_principal_var = tk.StringVar(value=player.principal)
conversion_rate_var = tk.StringVar(value=player.conversion_rate)
weight_limit_var = tk.StringVar(value=player.mass_limit)
volume_limit_var = tk.StringVar(value=player.volume_limit)
min_profit_var = tk.StringVar(value=player.min_profit)

# Adjust the width of the text boxes
ttk.Label(player_frame, text="Player Principal:").grid(row=0, column=0, sticky="w", pady=3)
player_principal = ttk.Entry(player_frame, textvariable=player_principal_var, width=15)  # Narrower
player_principal.grid(row=0, column=1, sticky="ew", pady=3)

ttk.Label(player_frame, text="Conversion Rate:").grid(row=1, column=0, sticky="w", pady=3)
conversion_rate = ttk.Entry(player_frame, textvariable=conversion_rate_var, width=15)  # Narrower
conversion_rate.grid(row=1, column=1, sticky="ew", pady=3)

ttk.Label(player_frame, text="Weight Limit:").grid(row=2, column=0, sticky="w", pady=3)
weight_limit = ttk.Entry(player_frame, textvariable=weight_limit_var, width=15)  # Narrower
weight_limit.grid(row=2, column=1, sticky="ew", pady=3)

ttk.Label(player_frame, text="Volume Limit:").grid(row=3, column=0, sticky="w", pady=3)
volume_limit = ttk.Entry(player_frame, textvariable=volume_limit_var, width=15)  # Narrower
volume_limit.grid(row=3, column=1, sticky="ew", pady=3)

ttk.Label(player_frame, text="Min Profit:").grid(row=4, column=0, sticky="w", pady=3)
min_profit = ttk.Entry(player_frame, textvariable=min_profit_var, width=15)  # Narrower
min_profit.grid(row=4, column=1, sticky="ew", pady=3)

tooltips = {
    player_principal: "Player money in the currency used",
    conversion_rate: "Lions ~34.0\nDragons ~330\nCrowns ~82.0\nGet this info from currency exchange",
    weight_limit: "Max weight of supplies in rough seas\n ~1000 for dhow, ~4000 for sanbuq",
    volume_limit: "Max volume of supplies\n ~40 for dhow, ~120 for sanbuq\nRegular Crate=3, Barrel=4, Logs=20",
    min_profit: "Don't show trades that generate\n a profit less than this"
}

for widget, text in tooltips.items():
    create_tooltip(widget, text)

update_chart_button = ttk.Button(player_frame, text="Update Values", command=lambda: [update_values(), update_chart()])
update_chart_button.grid(row=5, column=0, columnspan=2, pady=(6, 2))

player_frame.columnconfigure(1, weight=1)


# --------------------------
# Row 1.5: Group Checkboxes
# --------------------------
group_frame = ttk.LabelFrame(top_frame, text="Select Groups", padding="5")
group_frame.grid(row=0, column=1, sticky="nsew")

# Create separate frames for Start and End Group Checkboxes
start_group_frame = ttk.Frame(group_frame, padding="5", relief="solid", borderwidth=2)
start_group_frame.grid(row=0, column=0, padx=5, pady=3)
end_group_frame = ttk.Frame(group_frame, padding="5", relief="solid", borderwidth=2)
end_group_frame.grid(row=0, column=1, padx=5, pady=3)

island_names = ["Al'Ankh", "Aestrin", "Chronos", "Happy Bay", "Emerald Arch", "Fire Fish Lagoon"]

# For start groups, only "Al'Ankh" is enabled by default.
start_group_vars = create_group_checkboxes(
    start_group_frame, island_names,
    default_func=lambda name: 1 if name == "Al'Ankh" else 0,
    label_text="Start Groups:"
)

# For end groups, all checkboxes are enabled by default.
end_group_vars = create_group_checkboxes(
    end_group_frame, island_names,
    default_func=lambda name: 1,
    label_text="End Groups:"
)

# -------------------------------
# Row 2: Trade Table (Chart)
# -------------------------------
table_frame = ttk.Frame(root, padding="8")
table_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=8)
root.grid_rowconfigure(2, weight=1)  # Allow table frame to expand

columns = ("From", "To", "Product", "Qnty", "$Buy", "$Sell", "$Profit", "$/Pound", "$/Item")
tree = ttk.Treeview(table_frame, columns=columns, show="headings")

# Set column widths
column_widths = {"From": 80, "To": 80, "Product": 60, "Qnty": 20, "$Buy": 20,
                "$Sell": 20, "$Profit": 30, "$/Pound": 30, "$/Item": 30
}

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=column_widths.get(col, 90), anchor="center")  # Default width if not in dict

tree.grid(row=0, column=0, sticky="nsew")

table_frame.grid_columnconfigure(0, weight=1)
table_frame.grid_rowconfigure(0, weight=1)

scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
tree.configure(yscroll=scrollbar.set)
scrollbar.grid(row=0, column=1, sticky="ns")
tree.bind("<MouseWheel>", lambda event: on_mouse_wheel(event, tree))

# Automatic chart update every second
root.after(5000, update_loop)

root.mainloop()