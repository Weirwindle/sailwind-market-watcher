"""Launch the Sailwind Market Watcher desktop application."""

import ctypes
import math
import tkinter as tk
from queue import Empty, Queue
from threading import Thread
from time import perf_counter
from tkinter import ttk

import pymem
from PIL import Image, ImageTk

from market import Market, generate_trade_routes, scan_market_addresses
from settings import APP_DIR, PLAYER_SETTINGS_PATH, Player, save_player_settings

START_GROUPS_OPTION = "Selected start groups"


def configure_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    background = "#0e1724"
    panel = "#172437"
    field = "#101c2d"
    border = "#30435a"
    text_color = "#edf4fc"
    muted = "#aabdd2"
    accent = "#79e1cf"
    root.configure(background=background)
    root.option_add("*TCombobox*Listbox.background", field)
    root.option_add("*TCombobox*Listbox.foreground", text_color)
    root.option_add("*TCombobox*Listbox.selectBackground", "#28566a")
    root.option_add("*TCombobox*Listbox.selectForeground", text_color)
    root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))

    style.configure(".", background=panel, foreground=text_color, font=("Segoe UI", 10))
    style.configure("Page.TFrame", background=background)
    style.configure("TNotebook", background=background, borderwidth=0)
    style.configure("TNotebook.Tab", background="#21334a", padding=(14, 7))
    style.map(
        "TNotebook.Tab",
        background=[("selected", panel)],
        foreground=[("selected", accent)],
    )
    style.configure(
        "TLabelframe", bordercolor=border, lightcolor=border, darkcolor=border
    )
    style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
    style.configure("Muted.TLabel", foreground=muted)
    style.configure("Tooltip.TLabel", background="#263b52")
    style.configure(
        "TButton",
        background="#263b52",
        bordercolor=border,
        lightcolor="#263b52",
        darkcolor="#263b52",
        padding=(12, 6),
    )
    style.map(
        "TButton",
        background=[("pressed", "#304d66"), ("active", "#34526b")],
        bordercolor=[("focus", accent)],
        foreground=[("disabled", muted)],
    )
    style.configure(
        "Accent.TButton",
        background=accent,
        foreground="#102631",
        lightcolor=accent,
        darkcolor=accent,
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Accent.TButton",
        background=[
            ("disabled", "#263b52"),
            ("pressed", "#55bcae"),
            ("active", "#a2eddf"),
        ],
        foreground=[("disabled", muted)],
    )
    for input_style in ("TEntry", "TCombobox"):
        style.configure(
            input_style,
            fieldbackground=field,
            insertcolor=text_color,
            bordercolor=border,
            lightcolor=field,
            darkcolor=field,
            arrowcolor=text_color,
            padding=(7, 4),
        )
        style.map(
            input_style,
            fieldbackground=[("readonly", field), ("disabled", panel)],
            foreground=[("disabled", muted)],
            bordercolor=[("focus", accent)],
        )
    style.configure(
        "TCheckbutton",
        indicatorbackground=field,
        indicatorforeground="#102631",
        indicatorcolor=field,
        indicatormargin=(0, 0, 5, 0),
        padding=(2, 3),
    )
    style.map(
        "TCheckbutton",
        indicatorbackground=[("selected", accent)],
        indicatorcolor=[("selected", accent)],
        background=[("active", "#263b52")],
    )
    style.configure(
        "Treeview",
        background=field,
        fieldbackground=field,
        bordercolor=border,
        lightcolor=field,
        darkcolor=field,
        rowheight=30,
    )
    style.map(
        "Treeview",
        background=[("selected", "#28566a")],
        foreground=[("selected", "#ffffff")],
    )
    style.configure(
        "Treeview.Heading",
        font=("Segoe UI", 10, "bold"),
        background="#21334a",
        bordercolor=border,
        lightcolor="#21334a",
        darkcolor="#21334a",
        padding=(7, 8),
    )
    style.map("Treeview.Heading", background=[("active", "#34526b")])
    style.configure(
        "Vertical.TScrollbar",
        background="#34526b",
        troughcolor=field,
        bordercolor=field,
        lightcolor="#34526b",
        darkcolor="#34526b",
        arrowcolor=text_color,
    )


def main():
    def find_markets():
        results = Queue()
        started_at = perf_counter()
        start_button.state(["disabled"])
        status_label.config(text="Scanning for markets…")

        def scan():
            try:
                scan_result = scan_market_addresses(pm.process_handle)
                addresses = scan_result.addresses
                print(
                    f"Scan timing: region queries {scan_result.region_query_seconds:.2f}s, "
                    f"memory reads {scan_result.memory_read_seconds:.2f}s, "
                    f"signature matching {scan_result.signature_match_seconds:.2f}s."
                )
                if len(addresses) != 32:
                    raise ValueError(f"Found {len(addresses)} markets, expected 32.")
                load_started_at = perf_counter()
                scanned_markets = [Market(pm, address - 0x4E) for address in addresses]
                print(f"Market loading took {perf_counter() - load_started_at:.2f}s.")
                results.put(scanned_markets)
            except Exception as error:
                results.put(error)

        def finish_scan():
            try:
                result = results.get_nowait()
            except Empty:
                root.after(100, finish_scan)
                return

            start_button.state(["!disabled"])
            if isinstance(result, Exception):
                print(f"Market scan failed: {result}")
                status_label.config(
                    text=f"Market scan failed. {result}"
                    if isinstance(result, ValueError)
                    else "Market scan failed. See the console for details."
                )
                return

            markets[:] = result
            summary = f"Found {len(markets)} markets in {perf_counter() - started_at:.1f} seconds."
            status_label.config(text=summary)
            print(summary)
            for market in markets:
                print(f"{hex(market.base)}  {market.index:02} {market.name}")
            port_names = sorted(
                {market.name for market in markets if market.name != "Unknown Market"}
            )
            origin_port_picker.configure(
                values=[START_GROUPS_OPTION, *port_names], state="readonly"
            )
            if origin_port_var.get() not in port_names:
                origin_port_var.set(START_GROUPS_OPTION)
            update_chart()

        Thread(target=scan, daemon=True).start()
        root.after(100, finish_scan)

    def update_values():
        try:
            settings = {key: float(var.get()) for key, var in player_vars.items()}
            if not all(map(math.isfinite, settings.values())):
                raise ValueError
        except ValueError:
            player_status.config(text="Enter a number in each field.")
            return

        player.update(**settings)
        try:
            save_player_settings(PLAYER_SETTINGS_PATH, settings)
        except OSError as error:
            player_status.config(text="Applied for this session only.")
            print(f"Could not save player settings: {error}")
        else:
            player_status.config(text="Player inputs saved.")
        update_chart()

    def update_chart():
        if not markets:
            return

        start_groups = [
            f"{name} (Group {idx + 1})"
            for idx, name in enumerate(island_names)
            if start_group_vars[name].get() == 1
        ]
        end_groups = [
            f"{name} (Group {idx + 1})"
            for idx, name in enumerate(island_names)
            if end_group_vars[name].get() == 1
        ]

        for market in markets:
            market.update_products(player.conversion_rate)

        origin_port = origin_port_var.get()
        update_port_market(
            next((market for market in markets if market.name == origin_port), None)
        )
        if origin_port == START_GROUPS_OPTION:
            origin_port = None
        trade_routes = generate_trade_routes(
            start_groups, end_groups, player, markets, origin_port
        )

        sort_routes(trade_routes)

        tree.delete(*tree.get_children())
        for row, route in enumerate(trade_routes):
            tree.insert(
                "",
                "end",
                tags=("alternate",) if row % 2 else (),
                values=[
                    route[k]
                    for k in [
                        "Start Market",
                        "End Market",
                        "Product",
                        "Qnty",
                        "$_Buy",
                        "$_Sell",
                        "$Profit",
                        "$/Pound",
                        "$/Item",
                    ]
                ],
            )

        update_column_headers()

    def update_port_market(market):
        port_tree.delete(*port_tree.get_children())
        if market is None:
            port_caption.config(text="Select a departure port to view its market.")
            return

        port_caption.config(text=market.name)
        for row, product in enumerate(
            sorted(market.products, key=lambda product: product.name)
        ):
            port_tree.insert(
                "",
                "end",
                tags=("alternate",) if row % 2 else (),
                values=(
                    product.name,
                    product.amnt,
                    product.buy_price if product.amnt > 0 else "—",
                    product.sell_price,
                ),
            )

    def update_loop():
        update_chart()
        root.after(5000, update_loop)

    def on_mouse_wheel(event, tree):
        if event.delta > 0:  # Scroll up
            tree.yview_scroll(-5, "units")
        else:  # Scroll down
            tree.yview_scroll(5, "units")

    def create_tooltip(widget, text):
        """Show fixed help or look up help for the area under the pointer."""
        window = None
        visible_text = None

        def hide_tip(_event=None):
            nonlocal window, visible_text
            if window is not None:
                window.destroy()
                window = None
            visible_text = None

        def show_tip(event):
            nonlocal window, visible_text
            message = text(event) if callable(text) else text
            if message == visible_text:
                return
            hide_tip()
            if message is None:
                return
            visible_text = message
            window = tk.Toplevel(widget)
            window.wm_overrideredirect(True)
            ttk.Label(
                window, text=message, style="Tooltip.TLabel", padding=8, wraplength=300
            ).pack()
            window.update_idletasks()
            x = min(
                event.x_root + 16, widget.winfo_screenwidth() - window.winfo_reqwidth()
            )
            y = event.y_root + 20
            if y + window.winfo_reqheight() > widget.winfo_screenheight():
                y = event.y_root - window.winfo_reqheight() - 8
            window.wm_geometry(f"{x:+d}{y:+d}")

        widget.bind("<Enter>", show_tip, add="+")
        widget.bind("<Leave>", hide_tip, add="+")
        if callable(text):
            widget.bind("<Motion>", show_tip, add="+")

    def add_heading_tooltips(table, help_by_column):
        def heading_help(event):
            if table.identify_region(event.x, event.y) != "heading":
                return None
            column = table.column(table.identify_column(event.x), "id")
            return help_by_column.get(column)

        create_tooltip(table, heading_help)

    def create_group_checkboxes(parent, names, default_func, label_text, tooltip):
        """Creates a labeled group of checkboxes with default values."""
        label = ttk.Label(parent, text=label_text, style="Muted.TLabel")
        label.grid(row=0, column=0, columnspan=2, sticky="w", padx=3, pady=(0, 6))
        create_tooltip(label, tooltip)
        vars_dict = {name: tk.IntVar(value=default_func(name)) for name in names}
        half = (len(names) + 1) // 2
        for idx, (name, var) in enumerate(vars_dict.items()):
            ttk.Checkbutton(parent, text=name, variable=var, command=update_chart).grid(
                row=(idx % half) + 1, column=idx // half, sticky="w", padx=10, pady=2
            )
        return vars_dict

    print("=== Island Market Scanner ===")

    try:
        process_name = "Sailwind.exe"
        pm = pymem.Pymem(process_name)
    except pymem.exception.ProcessNotFound:
        print(
            f"Error: {process_name} is not running. Please start the game and try again."
        )
        return 1

    # Set AppUserModelID for taskbar icon on Windows
    myappid = "mycompany.myproduct.subproduct.version"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    root = tk.Tk()
    root.title("Sailwind Market Scanner")
    root.geometry("1050x680")
    root.minsize(890, 460)

    icon = Image.open(APP_DIR / "boat.ico")
    icon = ImageTk.PhotoImage(icon)
    root.iconphoto(True, icon)

    configure_theme(root)

    root.grid_rowconfigure(2, weight=1)
    root.grid_columnconfigure(0, weight=1)

    button_frame = ttk.Frame(root, padding=(14, 10))
    button_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 0))

    player = Player()
    print(player)
    markets = []
    start_button = ttk.Button(
        button_frame,
        text="Scan For Markets",
        style="Accent.TButton",
        command=find_markets,
    )
    start_button.grid(row=0, column=0, sticky="w", padx=(0, 6))
    create_tooltip(start_button, "Read market data from your running Sailwind game.")

    status_label = ttk.Label(
        button_frame, text="Scan to load market data.", style="Muted.TLabel"
    )
    status_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(7, 0))

    ttk.Label(button_frame, text="Departure port").grid(row=0, column=1, padx=(12, 4))
    origin_port_var = tk.StringVar(value=START_GROUPS_OPTION)
    origin_port_picker = ttk.Combobox(
        button_frame, textvariable=origin_port_var, width=24, state="disabled"
    )
    origin_port_picker.grid(row=0, column=2, sticky="w")
    origin_port_picker.bind("<<ComboboxSelected>>", lambda event: update_chart())
    create_tooltip(
        origin_port_picker,
        "Choose a port for Port Market and departures. Selected start groups restores regional browsing.",
    )

    top_frame = ttk.Frame(root, style="Page.TFrame")
    top_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=12)
    top_frame.columnconfigure(1, weight=1)

    player_frame = ttk.LabelFrame(top_frame, text="Player inputs", padding=(12, 8))
    player_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

    player_fields = (
        ("principal", "Player Principal:", "Available money in the selected currency."),
        (
            "conversion_rate",
            "Conversion Rate:",
            "Use the in-game exchange rate.\nLions ~34, Dragons ~330, Crowns ~82.",
        ),
        (
            "mass_limit",
            "Weight Limit:",
            "Maximum cargo weight.\nDhow ~1000, sanbuq ~4000.",
        ),
        (
            "volume_limit",
            "Volume Limit:",
            "Maximum cargo volume.\nDhow ~40, sanbuq ~120.",
        ),
        ("min_profit", "Min Profit:", "Only show trades above this profit."),
    )
    player_vars = {}
    for row, (key, label, tooltip) in enumerate(player_fields):
        variable = tk.StringVar(value=getattr(player, key))
        player_vars[key] = variable
        field_label = ttk.Label(player_frame, text=label)
        field_label.grid(row=row, column=0, sticky="w", pady=2)
        create_tooltip(field_label, tooltip)
        entry = ttk.Entry(player_frame, textvariable=variable, width=15)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        create_tooltip(entry, tooltip)

    update_button = ttk.Button(
        player_frame, text="Update Values", command=update_values
    )
    update_button.grid(row=5, column=0, columnspan=2, pady=(6, 2))
    create_tooltip(
        update_button,
        "Apply your inputs to trade estimates and save them for the next launch.",
    )
    player_status = ttk.Label(player_frame, text="", style="Muted.TLabel")
    player_status.grid(row=6, column=0, columnspan=2, sticky="w")

    player_frame.columnconfigure(1, weight=1)

    group_frame = ttk.LabelFrame(top_frame, text="Island groups", padding=(12, 8))
    group_frame.grid(row=0, column=1, sticky="nsew")
    group_frame.columnconfigure((0, 1), weight=1, uniform="group")

    start_group_frame = ttk.Frame(group_frame, padding=(0, 4))
    start_group_frame.grid(row=0, column=0, sticky="nw")
    end_group_frame = ttk.Frame(group_frame, padding=(0, 4))
    end_group_frame.grid(row=0, column=1, sticky="nw")

    island_names = [
        "Al'Ankh",
        "Aestrin",
        "Chronos",
        "Happy Bay",
        "Emerald Arch",
        "Fire Fish Lagoon",
    ]

    # For start groups, only "Al'Ankh" is enabled by default.
    start_group_vars = create_group_checkboxes(
        start_group_frame,
        island_names,
        default_func=lambda name: 1 if name == "Al'Ankh" else 0,
        label_text="Start Groups:",
        tooltip="Choose departure regions while Departure port is set to Selected start groups.",
    )

    # For end groups, all checkboxes are enabled by default.
    end_group_vars = create_group_checkboxes(
        end_group_frame,
        island_names,
        default_func=lambda name: 1,
        label_text="End Groups:",
        tooltip="Choose which regions can appear as destinations in Trade Routes.",
    )

    tabs = ttk.Notebook(root)
    tabs.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
    table_frame = ttk.Frame(tabs, style="Page.TFrame")
    port_frame = ttk.Frame(tabs, padding=(8, 8, 8, 0))
    tabs.add(table_frame, text="Trade Routes")
    tabs.add(port_frame, text="Port Market")

    def tab_help(event):
        try:
            tab = tabs.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return None
        return {
            0: "Compare estimated profit for one product at a time across ports.",
            1: "See stock and estimated one-crate prices at the selected departure port.",
        }.get(tab)

    create_tooltip(tabs, tab_help)

    port_caption = ttk.Label(port_frame, text="Scan and select a departure port.")
    port_caption.grid(row=0, column=0, sticky="w", pady=(0, 8))
    port_columns = ("Product", "Stock", "Est. Buy / Crate", "Est. Sell / Crate")
    port_tree = ttk.Treeview(port_frame, columns=port_columns, show="headings")
    add_heading_tooltips(
        port_tree,
        {
            "Product": "The commodity listed at the selected port.",
            "Stock": "Estimated number of crates available to buy at this port.",
            "Est. Buy / Crate": "Estimated cost of the next crate. A dash means there is no stock to buy.",
            "Est. Sell / Crate": "Estimated amount the port pays for one crate you already own.",
        },
    )
    port_tree.tag_configure("alternate", background="#142238")
    for column in port_columns:
        port_tree.heading(column, text=column)
        port_tree.column(
            column, width=150, anchor="w" if column == "Product" else "center"
        )
    port_tree.grid(row=1, column=0, sticky="nsew")
    port_scrollbar = ttk.Scrollbar(
        port_frame, orient="vertical", command=port_tree.yview
    )
    port_scrollbar.grid(row=1, column=1, sticky="ns")
    port_tree.configure(yscrollcommand=port_scrollbar.set)
    port_tree.bind("<MouseWheel>", lambda event: on_mouse_wheel(event, port_tree))
    port_frame.columnconfigure(0, weight=1)
    port_frame.rowconfigure(1, weight=1)

    columns = (
        "From",
        "To",
        "Product",
        "Qnty",
        "$Buy",
        "$Sell",
        "$Profit",
        "$/Pound",
        "$/Item",
    )
    tree = ttk.Treeview(table_frame, columns=columns, show="headings")
    add_heading_tooltips(
        tree,
        {
            "From": "Port where you buy the cargo. Click to sort by departure port.",
            "To": "Port where you sell the cargo. Click to sort by destination.",
            "Product": "The commodity traded on this route.",
            "Qnty": "Planned crates / estimated crates available at the departure port.",
            "$Buy": "Estimated total purchase cost for the planned crates.",
            "$Sell": "Estimated total sale revenue for the planned crates.",
            "$Profit": "Estimated sale revenue minus purchase cost. Click to sort.",
            "$/Pound": "Estimated profit per pound of cargo. Click to sort.",
            "$/Item": "Estimated profit per crate. Click to sort.",
        },
    )
    tree.tag_configure("alternate", background="#142238")

    sort_columns = {"From": "Start Market", "To": "End Market"}
    primary_sortable = ("From", "To")
    secondary_sortable = ("$Profit", "$/Pound", "$/Item")
    sort_state = {
        "primary_col": "From",
        "primary_reverse": False,
        "secondary_col": "$Profit",
        "secondary_reverse": True,
    }

    def treeview_sort_column(column):
        if column in primary_sortable:
            priority = "primary"
        elif column in secondary_sortable:
            priority = "secondary"
        else:
            return

        column_key = f"{priority}_col"
        reverse_key = f"{priority}_reverse"
        if sort_state[column_key] == column:
            sort_state[reverse_key] = not sort_state[reverse_key]
        else:
            sort_state[column_key] = column
            sort_state[reverse_key] = priority == "secondary"
        update_chart()

    def sort_routes(routes):
        # Stable sorts keep the profit metric ordered within each port.
        secondary = sort_state["secondary_col"]
        primary = sort_columns[sort_state["primary_col"]]
        routes.sort(
            key=lambda route: route[secondary], reverse=sort_state["secondary_reverse"]
        )
        routes.sort(
            key=lambda route: route[primary], reverse=sort_state["primary_reverse"]
        )

    def update_column_headers():
        """Update Treeview headers with arrow indicators for primary/secondary sorts."""
        for col in columns:
            arrow = ""
            if col == sort_state["primary_col"]:
                arrow = " ▲" if sort_state["primary_reverse"] else " ▼"
            elif col == sort_state["secondary_col"]:
                arrow = " ⮟" if sort_state["secondary_reverse"] else " ⮝"
            tree.heading(
                col, text=col + arrow, command=lambda c=col: treeview_sort_column(c)
            )

    column_widths = {
        "From": 155,
        "To": 155,
        "Product": 105,
        "Qnty": 65,
        "$Buy": 75,
        "$Sell": 75,
        "$Profit": 80,
        "$/Pound": 85,
        "$/Item": 75,
    }

    for col in columns:
        tree.column(
            col,
            width=column_widths[col],
            minwidth=55 if col.startswith("$") else 65,
            anchor="w" if col in ("From", "To", "Product") else "center",
        )

    tree.grid(row=0, column=0, sticky="nsew")

    table_frame.grid_columnconfigure(0, weight=1)
    table_frame.grid_rowconfigure(0, weight=1)

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky="ns")
    tree.bind("<MouseWheel>", lambda event: on_mouse_wheel(event, tree))

    update_column_headers()
    root.after(2000, update_loop)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
