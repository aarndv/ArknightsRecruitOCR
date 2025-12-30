import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import time
import threading
from datetime import datetime
from .scanner import ScreenScanner
from .calculator import RecruitCalculator
from .settings import SettingsManager, HOTKEY_OPTIONS

class OverlayApp:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.pool = self.fetcher.fetch_data()
        self.calculator = RecruitCalculator(self.pool)
        self.scanner = ScreenScanner()
        self.settings = SettingsManager()
        
        # Store tag positions and current recommendations
        self.tag_positions = {}  # tag_name -> (x1, y1, x2, y2)
        self.highlight_windows = []  # List of highlight overlay windows
        self.selected_combo = None  # Currently highlighted combo
        self.current_results = []  # Store current calculation results
        
        # Scan history (last 10 scans)
        self.scan_history = []
        self.max_history = 10
        
        # Mouse listener for mouse button hotkeys
        self.mouse_listener = None
        
        # Tooltip window
        self.tooltip = None

        # UI Config
        self.root = tk.Tk()
        
        # Auto-click feature (must be after root is created)
        self.auto_click_enabled = tk.BooleanVar(value=self.settings.get("features", "auto_click") or False)
        
        # Minimum rarity filter (default 3 = show all)
        self.min_rarity_filter = tk.IntVar(value=self.settings.get("features", "min_rarity") or 3)
        
        # Sound notification for high rarity
        self.sound_enabled = tk.BooleanVar(value=self.settings.get("features", "sound_notify") or False)
        
        self.root.title("Arknights Recruit Helper")
        self.root.attributes("-topmost", True) # Always on top
        self.root.geometry("380x520+50+50") 
        self.root.attributes("-alpha", 0.95) # Slightly less transparent
        self.root.configure(bg="#1a1a2e")
        
        # Remove default title bar for cleaner look (optional - comment out if issues)
        # self.root.overrideredirect(True)
        
        # Styling
        style = ttk.Style()
        style.theme_use('clam')
        
        # Treeview styling
        style.configure("Treeview", 
                        background="#16213e", 
                        foreground="#eee", 
                        fieldbackground="#16213e", 
                        rowheight=28,
                        font=('Segoe UI', 10))
        style.configure("Treeview.Heading", 
                        font=('Segoe UI', 10, 'bold'),
                        background="#0f3460",
                        foreground="#e94560")
        style.map("Treeview", 
                  background=[("selected", "#e94560")],
                  foreground=[("selected", "white")])
        
        self.setup_ui()
        self.setup_hotkeys()
        
        print(f"Overlay Started. Press '{self.settings.scan_hotkey}' to Scan, '{self.settings.clear_hotkey}' to Clear.")

    def setup_hotkeys(self):
        """Setup keyboard and mouse hotkeys based on settings"""
        # Clear existing hotkeys safely
        try:
            keyboard.unhook_all()
        except:
            pass
        
        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
            except:
                pass
            self.mouse_listener = None
        
        scan_key = self.settings.scan_hotkey
        clear_key = self.settings.clear_hotkey
        quick_key = self.settings.quick_hotkey
        
        # Setup keyboard hotkeys (non-mouse)
        if not scan_key.startswith("Mouse"):
            keyboard.add_hotkey(scan_key, lambda: self.root.after(0, self.perform_scan_sequence))
        
        if not clear_key.startswith("Mouse"):
            keyboard.add_hotkey(clear_key, lambda: self.root.after(0, self.clear_highlights))
        
        if not quick_key.startswith("Mouse"):
            keyboard.add_hotkey(quick_key, lambda: self.root.after(0, self.quick_scan))
        
        # Setup mouse button hotkeys if needed
        if scan_key.startswith("Mouse") or clear_key.startswith("Mouse") or quick_key.startswith("Mouse"):
            self._setup_mouse_listener(scan_key, clear_key, quick_key)
        
        # Update header label
        if hasattr(self, 'header_label'):
            self.header_label.config(text=f"[{scan_key}] Scan  •  [{quick_key}] Quick  •  [{clear_key}] Clear")
    
    def _setup_mouse_listener(self, scan_key, clear_key, quick_key):
        """Setup mouse button listener using pynput"""
        try:
            from pynput import mouse
            
            def on_click(x, y, button, pressed):
                if pressed:
                    button_name = None
                    if button == mouse.Button.x1:  # Mouse4 (back)
                        button_name = "Mouse4"
                    elif button == mouse.Button.x2:  # Mouse5 (forward)
                        button_name = "Mouse5"
                    
                    if button_name:
                        if button_name == scan_key:
                            self.root.after(0, self.perform_scan_sequence)
                        elif button_name == clear_key:
                            self.root.after(0, self.clear_highlights)
                        elif button_name == quick_key:
                            self.root.after(0, self.quick_scan)
            
            self.mouse_listener = mouse.Listener(on_click=on_click)
            self.mouse_listener.start()
        except ImportError:
            print("Warning: pynput not installed. Mouse button hotkeys won't work.")
            print("Install with: pip install pynput")

    def setup_ui(self):
        # Color scheme
        bg_dark = "#1a1a2e"
        bg_medium = "#16213e"
        accent = "#e94560"
        accent_hover = "#ff6b6b"
        text_light = "#eee"
        text_dim = "#888"
        
        # Main Container
        main_frame = tk.Frame(self.root, bg=bg_dark)
        main_frame.pack(fill="both", expand=True)

        # Header with logo/title
        header = tk.Frame(main_frame, bg=bg_dark)
        header.pack(fill="x", pady=(10, 5))
        
        title_label = tk.Label(header, text="⚔ ARKNIGHTS RECRUIT", 
                              fg=accent, bg=bg_dark, 
                              font=("Segoe UI", 14, "bold"))
        title_label.pack()
        
        self.header_label = tk.Label(header, 
                                     text=f"[{self.settings.scan_hotkey}] Scan  •  [{self.settings.quick_hotkey}] Quick  •  [{self.settings.clear_hotkey}] Clear", 
                                     fg=text_dim, bg=bg_dark, font=("Segoe UI", 9))
        self.header_label.pack(pady=(2, 0))
        
        # Separator
        sep = tk.Frame(main_frame, bg=accent, height=2)
        sep.pack(fill="x", padx=20, pady=5)
        
        # Button frame with modern styled buttons
        btn_frame = tk.Frame(main_frame, bg=bg_dark)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        # Create modern-looking buttons
        scan_btn = tk.Button(btn_frame, text="🔍 SCAN", command=self.perform_scan_sequence,
                            bg=accent, fg="white", activebackground=accent_hover, activeforeground="white",
                            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
                            width=8, pady=5)
        scan_btn.pack(side="left", padx=3)
        
        # Quick Scan button - scans and auto-clicks the best result
        quick_btn = tk.Button(btn_frame, text="⚡ QUICK", command=self.quick_scan,
                             bg="#FF9800", fg="white", activebackground="#FFB74D", activeforeground="white",
                             font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
                             width=8, pady=5)
        quick_btn.pack(side="left", padx=3)
        
        clear_btn = tk.Button(btn_frame, text="✕", command=self.clear_highlights,
                              bg=bg_medium, fg=text_light, activebackground="#2a4a7f", activeforeground="white",
                              font=("Segoe UI", 10), relief="flat", cursor="hand2",
                              width=3, pady=5)
        clear_btn.pack(side="left", padx=3)
        
        settings_btn = tk.Button(btn_frame, text="⚙", command=self.open_settings,
                                 bg=bg_medium, fg=text_light, activebackground="#2a4a7f", activeforeground="white",
                                 font=("Segoe UI", 12), relief="flat", cursor="hand2",
                                 width=3, pady=3)
        settings_btn.pack(side="right", padx=3)

        # Strategy Selection with modern radio buttons
        strat_frame = tk.Frame(main_frame, bg=bg_dark)
        strat_frame.pack(fill="x", padx=10, pady=5)
        
        self.strat_var = tk.StringVar(value="min")
        
        strat_label = tk.Label(strat_frame, text="Strategy:", fg=text_dim, bg=bg_dark, 
                               font=("Segoe UI", 9))
        strat_label.pack(side="left", padx=5)
        
        rb1 = tk.Radiobutton(strat_frame, text="🛡 Safe (Min★)", variable=self.strat_var, value="min", 
                             bg=bg_dark, fg="#4CAF50", selectcolor=bg_medium, 
                             activebackground=bg_dark, activeforeground="#4CAF50",
                             font=("Segoe UI", 9), cursor="hand2")
        rb2 = tk.Radiobutton(strat_frame, text="⚡ Risky (Max★)", variable=self.strat_var, value="max", 
                             bg=bg_dark, fg="#FF9800", selectcolor=bg_medium, 
                             activebackground=bg_dark, activeforeground="#FF9800",
                             font=("Segoe UI", 9), cursor="hand2")
        rb1.pack(side="left", padx=10)
        rb2.pack(side="left", padx=10)
        
        # Options row 1: Auto-click and sound
        options_frame1 = tk.Frame(main_frame, bg=bg_dark)
        options_frame1.pack(fill="x", padx=10, pady=2)
        
        auto_check = tk.Checkbutton(options_frame1, text="🖱 Auto-click", 
                                    variable=self.auto_click_enabled,
                                    command=self.on_auto_click_toggle,
                                    bg=bg_dark, fg="#00BCD4", selectcolor=bg_medium, 
                                    activebackground=bg_dark, activeforeground="#00BCD4",
                                    font=("Segoe UI", 9), cursor="hand2")
        auto_check.pack(side="left", padx=5)
        
        sound_check = tk.Checkbutton(options_frame1, text="🔔 Sound (4★+)", 
                                     variable=self.sound_enabled,
                                     command=self.on_sound_toggle,
                                     bg=bg_dark, fg="#9C27B0", selectcolor=bg_medium, 
                                     activebackground=bg_dark, activeforeground="#9C27B0",
                                     font=("Segoe UI", 9), cursor="hand2")
        sound_check.pack(side="left", padx=10)
        
        # Options row 2: Minimum rarity filter
        options_frame2 = tk.Frame(main_frame, bg=bg_dark)
        options_frame2.pack(fill="x", padx=10, pady=2)
        
        tk.Label(options_frame2, text="Min★ Filter:", fg=text_dim, bg=bg_dark,
                font=("Segoe UI", 9)).pack(side="left", padx=5)
        
        for r in [3, 4, 5]:
            color = "#eee" if r == 3 else ("#DDA0DD" if r == 4 else "#FFD700")
            rb = tk.Radiobutton(options_frame2, text=f"{r}★+", variable=self.min_rarity_filter, value=r,
                               bg=bg_dark, fg=color, selectcolor=bg_medium,
                               activebackground=bg_dark, activeforeground=color,
                               font=("Segoe UI", 9), cursor="hand2",
                               command=self.on_filter_change)
            rb.pack(side="left", padx=5)

        # Results section header
        results_header = tk.Frame(main_frame, bg=bg_dark)
        results_header.pack(fill="x", padx=10, pady=(10, 2))
        
        tk.Label(results_header, text="📋 RESULTS", fg=text_light, bg=bg_dark,
                font=("Segoe UI", 10, "bold")).pack(side="left")
        
        # Tag display
        self.tags_label = tk.Label(results_header, text="", fg=text_dim, bg=bg_dark,
                                   font=("Segoe UI", 9))
        self.tags_label.pack(side="right")

        # Results TreeView with scrollbar
        tree_frame = tk.Frame(main_frame, bg=bg_dark)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        cols = ("Tags", "Min", "Max")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10)
        self.tree.heading("Tags", text="Tag Combination")
        self.tree.heading("Min", text="Min★")
        self.tree.heading("Max", text="Max★")
        
        self.tree.column("Tags", width=200)
        self.tree.column("Min", width=60, anchor="center")
        self.tree.column("Max", width=60, anchor="center")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind hover event for operator tooltip
        self.tree.bind("<Motion>", self.on_tree_hover)
        self.tree.bind("<Leave>", self.hide_tooltip)
        
        # Bottom action bar
        bottom_frame = tk.Frame(main_frame, bg=bg_medium)
        bottom_frame.pack(fill="x", side="bottom")
        
        inner_bottom = tk.Frame(bottom_frame, bg=bg_medium)
        inner_bottom.pack(fill="x", padx=10, pady=8)
        
        copy_btn = tk.Button(inner_bottom, text="📋 Copy", command=self.copy_results,
                             bg=bg_dark, fg=text_light, activebackground="#2a4a7f",
                             font=("Segoe UI", 9), relief="flat", cursor="hand2", padx=10)
        copy_btn.pack(side="left", padx=2)
        
        history_btn = tk.Button(inner_bottom, text="📜 History", command=self.show_history,
                               bg=bg_dark, fg=text_light, activebackground="#2a4a7f",
                               font=("Segoe UI", 9), relief="flat", cursor="hand2", padx=10)
        history_btn.pack(side="left", padx=2)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready • Hover results for operators")
        status_label = tk.Label(inner_bottom, textvariable=self.status_var,
                               fg=text_dim, bg=bg_medium, font=("Segoe UI", 8))
        status_label.pack(side="right", padx=5)
    
    def on_auto_click_toggle(self):
        """Save auto-click preference"""
        self.settings.set(self.auto_click_enabled.get(), "features", "auto_click")
        print(f"Auto-click {'enabled' if self.auto_click_enabled.get() else 'disabled'}")
    
    def on_sound_toggle(self):
        """Save sound notification preference"""
        self.settings.set(self.sound_enabled.get(), "features", "sound_notify")
        print(f"Sound notification {'enabled' if self.sound_enabled.get() else 'disabled'}")
    
    def on_filter_change(self):
        """Save and apply rarity filter"""
        self.settings.set(self.min_rarity_filter.get(), "features", "min_rarity")
        # Re-apply filter to current results if we have tags
        if self.tag_positions:
            self.update_results(list(self.tag_positions.keys()))
    
    def play_notification_sound(self):
        """Play a notification sound for high rarity results"""
        try:
            import winsound
            # Play Windows asterisk sound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except:
            pass  # Silently fail on non-Windows or if no sound available
    
    def quick_scan(self):
        """Scan and automatically click the first/best result"""
        # Clear any existing highlights
        self.clear_highlights()
        
        # 1. Hide the overlay
        self.root.withdraw()
        self.root.update()
        time.sleep(0.15)
        
        # 2. Scan
        print("Quick scan...")
        try:
            img = self.scanner.capture_screen()
            tag_data, debug_boxes = self.scanner.scan_for_tags(img)
            self.tag_positions = tag_data
            tags = list(tag_data.keys())
        except Exception as e:
            print(f"Scan failed: {e}")
            tags = []
            self.tag_positions = {}
            self.root.deiconify()
            return
        
        if not tags:
            self.root.deiconify()
            self.status_var.set("No tags found")
            return
        
        # 3. Calculate results
        results = self.calculator.calculate(tags, sort_mode=self.strat_var.get())
        
        # Apply rarity filter
        min_rarity = self.min_rarity_filter.get()
        filtered_results = [r for r in results if r['min'] >= min_rarity]
        
        if not filtered_results:
            filtered_results = results  # Fallback to unfiltered if nothing passes
        
        if not filtered_results:
            self.root.deiconify()
            self.update_results(tags)
            self.status_var.set("No valid combos found")
            return
        
        # 4. Get the best result (first one after sorting)
        best_result = filtered_results[0]
        combo_tags = best_result['tags']
        
        # 5. Click the tags
        try:
            import pyautogui
            pyautogui.PAUSE = 0.1
            
            for tag in combo_tags:
                for stored_tag, bbox in self.tag_positions.items():
                    if stored_tag.lower() == tag.lower():
                        x1, y1, x2, y2 = bbox
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        print(f"Quick-clicking '{stored_tag}' at ({center_x}, {center_y})")
                        pyautogui.click(center_x, center_y)
                        time.sleep(0.12)
                        break
            
        except ImportError:
            print("Error: pyautogui not installed")
        except Exception as e:
            print(f"Quick scan click error: {e}")
        
        # 6. Show overlay and update results
        time.sleep(0.1)
        self.root.deiconify()
        self.update_results(tags)
        
        # Show what was clicked
        clicked_str = ", ".join(combo_tags)
        self.status_var.set(f"⚡ Quick: {clicked_str} ({best_result['min']}★-{best_result['max']}★)")
    
    def add_to_history(self, tags, results):
        """Add scan to history"""
        entry = {
            'timestamp': datetime.now(),
            'tags': tags.copy(),
            'results': results.copy() if results else [],
            'best_min': max([r['min'] for r in results]) if results else 0
        }
        self.scan_history.insert(0, entry)
        # Keep only last N entries
        if len(self.scan_history) > self.max_history:
            self.scan_history = self.scan_history[:self.max_history]
    
    def show_history(self):
        """Show scan history in a popup window"""
        bg_dark = "#1a1a2e"
        bg_medium = "#16213e"
        accent = "#e94560"
        text_light = "#eee"
        text_dim = "#888"
        
        if not self.scan_history:
            messagebox.showinfo("History", "No scan history yet!")
            return
        
        history_win = tk.Toplevel(self.root)
        history_win.title("Scan History")
        history_win.geometry("420x380")
        history_win.configure(bg=bg_dark)
        history_win.attributes("-topmost", True)
        
        tk.Label(history_win, text="📜 SCAN HISTORY", fg=accent, bg=bg_dark,
                font=("Segoe UI", 12, "bold")).pack(pady=10)
        
        # Create listbox for history
        list_frame = tk.Frame(history_win, bg=bg_dark)
        list_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        listbox = tk.Listbox(list_frame, bg=bg_medium, fg=text_light, 
                            selectbackground=accent, selectforeground="white",
                            font=("Segoe UI", 10), height=10, relief="flat",
                            highlightthickness=0)
        listbox.pack(fill="both", expand=True)
        
        for i, entry in enumerate(self.scan_history):
            time_str = entry['timestamp'].strftime("%H:%M:%S")
            tags_str = ", ".join(entry['tags'][:3]) + ("..." if len(entry['tags']) > 3 else "")
            best = entry['best_min']
            star_icon = "⭐" if best >= 4 else "  "
            listbox.insert(tk.END, f"  {time_str}  │  {star_icon}{best}★  │  {tags_str}")
        
        # Details frame
        detail_frame = tk.Frame(history_win, bg=bg_dark)
        detail_frame.pack(fill="x", padx=15, pady=5)
        
        detail_var = tk.StringVar(value="Select an entry to see details")
        detail_label = tk.Label(detail_frame, textvariable=detail_var, fg=text_dim, bg=bg_dark,
                               font=("Segoe UI", 9), wraplength=380, justify="left")
        detail_label.pack()
        
        def on_select(event):
            sel = listbox.curselection()
            if sel:
                entry = self.scan_history[sel[0]]
                tags_str = ", ".join(entry['tags'])
                results_str = ""
                for r in entry['results'][:5]:
                    results_str += f"  {', '.join(r['tags'])}: {r['min']}★-{r['max']}★\n"
                detail_var.set(f"Tags: {tags_str}\nTop combos:\n{results_str}")
        
        listbox.bind("<<ListboxSelect>>", on_select)
        
        # Load button
        def load_selected():
            sel = listbox.curselection()
            if sel:
                entry = self.scan_history[sel[0]]
                self.update_results(entry['tags'])
                history_win.destroy()
        
        tk.Button(history_win, text="↩ Load Selected", command=load_selected,
                 bg=accent, fg="white", font=("Segoe UI", 10, "bold"),
                 relief="flat", cursor="hand2", padx=20, pady=5).pack(pady=10)
    
    def copy_results(self):
        """Copy current results to clipboard"""
        if not self.current_results:
            self.status_var.set("Nothing to copy!")
            return
        
        lines = ["Arknights Recruitment Results", "=" * 30]
        lines.append(f"Tags: {', '.join(self.tag_positions.keys())}")
        lines.append("")
        
        for res in self.current_results:
            tag_str = ", ".join(res['tags'])
            ops = ", ".join([op['name'] for op in res['ops'][:5]])
            if len(res['ops']) > 5:
                ops += f" (+{len(res['ops']) - 5} more)"
            lines.append(f"{tag_str}: {res['min']}★-{res['max']}★")
            lines.append(f"  → {ops}")
        
        text = "\n".join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Results copied to clipboard!")
    
    def on_tree_hover(self, event):
        """Show operator tooltip when hovering over a row"""
        item = self.tree.identify_row(event.y)
        if not item:
            self.hide_tooltip()
            return
        
        values = self.tree.item(item)['values']
        if not values or values[0] in ["No Tags Found", "No Valid Combos"]:
            self.hide_tooltip()
            return
        
        tag_str = values[0]
        
        # Find matching result
        for res in self.current_results:
            if ", ".join(res['tags']) == tag_str:
                operators = res['ops']
                if operators:
                    self.show_tooltip(event, operators)
                return
        
        self.hide_tooltip()
    
    def show_tooltip(self, event, operators):
        """Show tooltip with operator names"""
        if self.tooltip:
            self.tooltip.destroy()
        
        # Build operator list with color-coded rarity
        op_lines = []
        for op in operators[:10]:
            rarity = op['rarity']
            name = op['name']
            if rarity >= 5:
                op_lines.append(f"  ⭐ {rarity}★ {name}")
            elif rarity >= 4:
                op_lines.append(f"  ✦ {rarity}★ {name}")
            else:
                op_lines.append(f"     {rarity}★ {name}")
        
        if len(operators) > 10:
            op_lines.append(f"  ... +{len(operators) - 10} more")
        
        op_text = "OPERATORS\n" + "\n".join(op_lines)
        
        # Create tooltip
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.attributes("-topmost", True)
        
        x = self.root.winfo_rootx() + event.x + 20
        y = self.root.winfo_rooty() + event.y + 10
        self.tooltip.geometry(f"+{x}+{y}")
        
        # Styled tooltip
        frame = tk.Frame(self.tooltip, bg="#0f3460", highlightbackground="#e94560", 
                        highlightthickness=1)
        frame.pack()
        
        label = tk.Label(frame, text=op_text, bg="#0f3460", fg="#eee",
                        font=("Segoe UI", 9), justify="left", padx=10, pady=8)
        label.pack()
    
    def hide_tooltip(self, event=None):
        """Hide the tooltip"""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def perform_scan_sequence(self):
        """
        Hides window, takes screenshot, shows window, processes data.
        """
        # Clear any existing highlights
        self.clear_highlights()
        
        # 1. Hide the overlay so it doesn't block the game
        self.root.withdraw()
        # Short pause to ensure OS redraws the screen without the window
        self.root.update()
        time.sleep(0.15) 

        # 2. Scan
        print("Snapshot taken...")
        try:
            img = self.scanner.capture_screen()
            tag_data, debug_boxes = self.scanner.scan_for_tags(img)
            # tag_data is now a dict: {tag_name: (x1, y1, x2, y2)}
            self.tag_positions = tag_data
            tags = list(tag_data.keys())
        except Exception as e:
            print(f"Scan failed: {e}")
            import traceback
            traceback.print_exc()
            tags = []
            self.tag_positions = {}
        
        # 3. Show window again
        self.root.deiconify()
        
        # 4. Process Results
        self.update_results(tags)

    def update_results(self, tags):
        # Clear previous results
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        if not tags:
            print("No tags found.")
            # Insert a placeholder row
            self.tree.insert("", "end", values=("No Tags Found", "-", "-"))
            self.tags_label.config(text="")
            self.status_var.set("No tags detected")
            return

        print(f"Processing Tags: {tags}")
        
        # Update tags display
        self.tags_label.config(text=" • ".join(tags[:3]) + ("..." if len(tags) > 3 else ""))
        
        # Calculate
        results = self.calculator.calculate(tags, sort_mode=self.strat_var.get())
        
        # Store all results for later use
        self.current_results = results
        
        # Apply rarity filter for display
        min_rarity = self.min_rarity_filter.get()
        filtered_results = [r for r in results if r['min'] >= min_rarity]
        
        # Add to history (with unfiltered results)
        self.add_to_history(tags, results)
        
        # Check for high rarity and play sound
        best_min = max([r['min'] for r in results]) if results else 0
        if self.sound_enabled.get() and best_min >= 4:
            self.play_notification_sound()
        
        if not filtered_results:
            if results:
                # Has results but all filtered out
                self.tree.insert("", "end", values=(f"No {min_rarity}★+ combos (lower filter)", "-", "-"))
                self.status_var.set(f"Found {len(tags)} tags, {len(results)} combos (filtered: 0)")
            else:
                self.tree.insert("", "end", values=("No Valid Combos", "-", "-"))
                self.status_var.set(f"Scanned {len(tags)} tags - no combos")
            return

        # Display
        self.root.title(f"Found: {len(tags)} Tags")
        filter_note = f" (showing {min_rarity}★+)" if min_rarity > 3 else ""
        self.status_var.set(f"Found {len(tags)} tags, {len(filtered_results)}/{len(results)} combos{filter_note}")
        
        for res in filtered_results:
            tag_str = ", ".join(res['tags'])
            min_r = res['min']
            max_r = res['max']
            
            # Color code based on rarity
            if min_r >= 5:
                tag_name = "gold"  # 5* guaranteed
            elif min_r >= 4:
                tag_name = "purple"  # 4* guaranteed
            else:
                tag_name = "normal"
            
            row_id = self.tree.insert("", "end", values=(tag_str, f"{min_r}*", f"{max_r}*"), tags=(tag_name,))
        
        # Configure tag colors
        self.tree.tag_configure("gold", foreground="#FFD700", font=('Segoe UI', 10, 'bold'))
        self.tree.tag_configure("purple", foreground="#DDA0DD")
        self.tree.tag_configure("normal", foreground="#eee")
        
        # Bind click event to show highlights
        self.tree.bind("<<TreeviewSelect>>", self.on_combo_select)
    
    def on_combo_select(self, event):
        """When user clicks a combo row, highlight those tags on screen"""
        self.clear_highlights()
        
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        tag_str = item['values'][0]
        
        if tag_str in ["No Tags Found", "No Valid Combos"]:
            return
        
        # Parse the tags from the combo string
        combo_tags = [t.strip() for t in tag_str.split(",")]
        
        # Collect positions for tags to click/highlight
        tags_to_process = []
        for tag in combo_tags:
            # Find the tag (case-insensitive)
            for stored_tag, bbox in self.tag_positions.items():
                if stored_tag.lower() == tag.lower():
                    tags_to_process.append((stored_tag, bbox))
                    break
        
        # If auto-click is enabled, click the tags
        if self.auto_click_enabled.get() and tags_to_process:
            self.auto_click_tags(tags_to_process)
        else:
            # Just highlight them
            for tag_name, bbox in tags_to_process:
                self.create_highlight(bbox, tag_name)
    
    def auto_click_tags(self, tags_to_process):
        """Automatically click on the specified tags"""
        try:
            import pyautogui
            pyautogui.PAUSE = 0.1  # Small delay between actions
            
            # Hide overlay temporarily so it doesn't interfere
            self.root.withdraw()
            self.root.update()
            time.sleep(0.1)
            
            for tag_name, bbox in tags_to_process:
                x1, y1, x2, y2 = bbox
                # Click in the center of the tag
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                print(f"Auto-clicking '{tag_name}' at ({center_x}, {center_y})")
                pyautogui.click(center_x, center_y)
                time.sleep(0.15)  # Wait a bit between clicks
            
            # Show overlay again
            time.sleep(0.1)
            self.root.deiconify()
            
            # Update status - no highlights for auto-click
            self.status_var.set(f"✓ Clicked {len(tags_to_process)} tags")
                
        except ImportError:
            print("Error: pyautogui not installed. Install with: pip install pyautogui")
            # Fall back to just highlighting
            for tag_name, bbox in tags_to_process:
                self.create_highlight(bbox, tag_name)
        except Exception as e:
            print(f"Auto-click error: {e}")
            self.root.deiconify()
            # Fall back to just highlighting
            for tag_name, bbox in tags_to_process:
                self.create_highlight(bbox, tag_name)
    
    def create_highlight(self, bbox, tag_name):
        """Create a colored border overlay on the screen at bbox position"""
        x1, y1, x2, y2 = bbox
        padding = 10
        border_width = 4
        
        # Create 4 separate border windows (top, bottom, left, right)
        # This allows clicking through the center
        borders = [
            # Top border
            (x1 - padding, y1 - padding, x2 - x1 + 2*padding, border_width),
            # Bottom border  
            (x1 - padding, y2 + padding - border_width, x2 - x1 + 2*padding, border_width),
            # Left border
            (x1 - padding, y1 - padding, border_width, y2 - y1 + 2*padding),
            # Right border
            (x2 + padding - border_width, y1 - padding, border_width, y2 - y1 + 2*padding),
        ]
        
        for (bx, by, bw, bh) in borders:
            border = tk.Toplevel(self.root)
            border.overrideredirect(True)
            border.attributes("-topmost", True)
            border.geometry(f"{bw}x{bh}+{bx}+{by}")
            border.configure(bg="#00FF00")
            
            # Make click-through on Windows
            self._make_click_through(border)
            
            self.highlight_windows.append(border)
    
    def _make_click_through(self, window):
        """Make a window click-through on Windows"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Need to update the window first
            window.update()
            
            # Get the window handle
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            
            # Get current extended style
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            
            styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        except Exception as e:
            pass  # Non-Windows or error
    
    def clear_highlights(self):
        """Remove all highlight overlay windows"""
        for hw in self.highlight_windows:
            try:
                hw.destroy()
            except:
                pass
        self.highlight_windows = []
    
    def open_settings(self):
        """Open the settings dialog"""
        SettingsDialog(self.root, self.settings, self.on_settings_saved)
    
    def on_settings_saved(self):
        """Called when settings are saved"""
        self.setup_hotkeys()
        print(f"Hotkeys updated: Scan={self.settings.scan_hotkey}, Clear={self.settings.clear_hotkey}")

    def run(self):
        self.root.mainloop()


class SettingsDialog:
    """Settings dialog for configuring hotkeys"""
    
    def __init__(self, parent, settings, on_save_callback=None):
        self.settings = settings
        self.on_save_callback = on_save_callback
        
        # Color scheme
        self.bg_dark = "#1a1a2e"
        self.bg_medium = "#16213e"
        self.accent = "#e94560"
        self.text_light = "#eee"
        self.text_dim = "#888"
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("380x380")
        self.dialog.configure(bg=self.bg_dark)
        self.dialog.attributes("-topmost", True)
        self.dialog.resizable(False, False)
        
        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_ui()
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
    
    def setup_ui(self):
        # Title
        title = tk.Label(self.dialog, text="⚙ SETTINGS", fg=self.accent, bg=self.bg_dark, 
                        font=("Segoe UI", 14, "bold"))
        title.pack(pady=15)
        
        # Hotkeys section
        hotkey_frame = tk.LabelFrame(self.dialog, text=" Hotkeys ", fg=self.text_light, bg=self.bg_dark,
                                     font=("Segoe UI", 10, "bold"))
        hotkey_frame.pack(fill="x", padx=20, pady=10)
        
        # Scan hotkey
        scan_frame = tk.Frame(hotkey_frame, bg=self.bg_dark)
        scan_frame.pack(fill="x", padx=10, pady=8)
        
        tk.Label(scan_frame, text="Scan Screen:", fg=self.text_light, bg=self.bg_dark, 
                width=14, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.scan_var = tk.StringVar(value=self.settings.scan_hotkey)
        scan_combo = ttk.Combobox(scan_frame, textvariable=self.scan_var, values=HOTKEY_OPTIONS, width=12)
        scan_combo.pack(side="left", padx=5)
        
        scan_capture_btn = tk.Button(scan_frame, text="⌨ Capture", command=lambda: self.capture_hotkey("scan"),
                                     bg=self.bg_medium, fg=self.text_light, relief="flat",
                                     font=("Segoe UI", 9), cursor="hand2")
        scan_capture_btn.pack(side="left", padx=5)
        
        # Clear hotkey
        clear_frame = tk.Frame(hotkey_frame, bg=self.bg_dark)
        clear_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(clear_frame, text="Clear:", fg=self.text_light, bg=self.bg_dark, 
                width=14, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.clear_var = tk.StringVar(value=self.settings.clear_hotkey)
        clear_combo = ttk.Combobox(clear_frame, textvariable=self.clear_var, values=HOTKEY_OPTIONS, width=12)
        clear_combo.pack(side="left", padx=5)
        
        clear_capture_btn = tk.Button(clear_frame, text="⌨ Capture", command=lambda: self.capture_hotkey("clear"),
                                      bg=self.bg_medium, fg=self.text_light, relief="flat",
                                      font=("Segoe UI", 9), cursor="hand2")
        clear_capture_btn.pack(side="left", padx=5)
        
        # Quick Scan hotkey
        quick_frame = tk.Frame(hotkey_frame, bg=self.bg_dark)
        quick_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(quick_frame, text="Quick Scan:", fg=self.text_light, bg=self.bg_dark, 
                width=14, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.quick_var = tk.StringVar(value=self.settings.quick_hotkey)
        quick_combo = ttk.Combobox(quick_frame, textvariable=self.quick_var, values=HOTKEY_OPTIONS, width=12)
        quick_combo.pack(side="left", padx=5)
        
        quick_capture_btn = tk.Button(quick_frame, text="⌨ Capture", command=lambda: self.capture_hotkey("quick"),
                                      bg=self.bg_medium, fg=self.text_light, relief="flat",
                                      font=("Segoe UI", 9), cursor="hand2")
        quick_capture_btn.pack(side="left", padx=5)
        
        # Info label
        info_label = tk.Label(self.dialog, 
                             text="💡 Mouse4/Mouse5 = Side buttons\n    Click 'Capture' then press any key",
                             fg=self.text_dim, bg=self.bg_dark, font=("Segoe UI", 9), justify="left")
        info_label.pack(pady=10)
        
        # Buttons
        btn_frame = tk.Frame(self.dialog, bg=self.bg_dark)
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        save_btn = tk.Button(btn_frame, text="✓ Save", command=self.save_settings,
                            bg=self.accent, fg="white", font=("Segoe UI", 10, "bold"),
                            relief="flat", cursor="hand2", width=12, pady=5)
        save_btn.pack(side="left", padx=10)
        
        cancel_btn = tk.Button(btn_frame, text="✕ Cancel", command=self.dialog.destroy,
                              bg=self.bg_medium, fg=self.text_light, font=("Segoe UI", 10),
                              relief="flat", cursor="hand2", width=12, pady=5)
        cancel_btn.pack(side="right", padx=10)
    
    def capture_hotkey(self, target):
        """Capture a key press or mouse button"""
        # Create capture dialog
        capture_win = tk.Toplevel(self.dialog)
        capture_win.title("Capture Key")
        capture_win.geometry("280x120")
        capture_win.configure(bg=self.bg_dark)
        capture_win.attributes("-topmost", True)
        capture_win.transient(self.dialog)
        capture_win.grab_set()
        
        tk.Label(capture_win, text="⌨", fg=self.accent, bg=self.bg_dark,
                font=("Segoe UI", 24)).pack(pady=(15, 5))
        label = tk.Label(capture_win, text="Press any key or mouse button...", 
                        fg=self.text_light, bg=self.bg_dark, font=("Segoe UI", 10))
        label.pack()
        
        captured_key = [None]
        
        def on_key(event):
            key = event.name.upper() if hasattr(event, 'name') else str(event)
            # Handle special keys
            if key in ['ESCAPE', 'ESC']:
                capture_win.destroy()
                return
            captured_key[0] = key
            capture_win.destroy()
        
        def on_mouse(x, y, button, pressed):
            if pressed:
                try:
                    from pynput.mouse import Button
                    if button == Button.x1:
                        captured_key[0] = "Mouse4"
                    elif button == Button.x2:
                        captured_key[0] = "Mouse5"
                    else:
                        return  # Ignore left/right/middle click
                    capture_win.destroy()
                    return False  # Stop listener
                except:
                    pass
        
        # Start keyboard listener
        keyboard.on_press(on_key)
        
        # Start mouse listener
        try:
            from pynput import mouse
            mouse_listener = mouse.Listener(on_click=on_mouse)
            mouse_listener.start()
        except:
            mouse_listener = None
        
        # Wait for capture window to close
        capture_win.wait_window()
        
        # Cleanup
        keyboard.unhook_all()
        if mouse_listener:
            mouse_listener.stop()
        
        # Set the captured key
        if captured_key[0]:
            if target == "scan":
                self.scan_var.set(captured_key[0])
            elif target == "clear":
                self.clear_var.set(captured_key[0])
            elif target == "quick":
                self.quick_var.set(captured_key[0])
    
    def save_settings(self):
        """Save settings and close dialog"""
        scan_key = self.scan_var.get()
        clear_key = self.clear_var.get()
        quick_key = self.quick_var.get()
        
        # Validate - all must be different
        keys = [scan_key, clear_key, quick_key]
        if len(keys) != len(set(keys)):
            messagebox.showerror("Error", "All hotkeys must be different!")
            return
        
        if not scan_key or not clear_key or not quick_key:
            messagebox.showerror("Error", "Please set all hotkeys!")
            return
        
        # Save
        self.settings.scan_hotkey = scan_key
        self.settings.clear_hotkey = clear_key
        self.settings.quick_hotkey = quick_key
        
        # Callback
        if self.on_save_callback:
            self.on_save_callback()
        
        self.dialog.destroy()