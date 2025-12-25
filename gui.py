import os, sys
import time
import json
import threading
import pygame
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from mutagen import File as MutagenFile

# --------- Pygame init for audio ----------
pygame.mixer.init()

AUDIO_EXTENSIONS = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')
CONFIG_FILE = "music_player_config.json"

def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(relative)


class MusicPlayerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ABs Music Player")
        self.root.geometry("1100x680")
        self.root.minsize(900, 600)
        try:
            self.root.iconbitmap(resource_path("assets/icon.ico"))
        except:
            pass

        # State
        self.songs = []
        self.current_index = None
        self.is_paused = False
        self.is_muted = False
        self.current_length = 0
        self.play_start_time = None
        self.auto_next_enabled = True
        self.manual_stop = False
        self.last_folder = None
        self.loading_in_progress = False

        # UI setup
        self._setup_style()
        self._build_ui()

        # Load previous session
        self._load_config()

        # Start updating progress bar
        self._schedule_progress_update()

        # Save config on close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ---------- Configuration Persistence ----------

    def _load_config(self):
        """Load previous folder and playback position from config file"""
        if not os.path.exists(CONFIG_FILE):
            return

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            folder = config.get('last_folder')
            last_index = config.get('last_index', 0)
            volume = config.get('volume', 70)

            if folder and os.path.exists(folder):
                self.last_folder = folder
                self.volume_scale.set(volume)
                pygame.mixer.music.set_volume(volume / 100.0)
                
                # Load songs in background
                self._load_songs_threaded(folder, last_index)
        except Exception as e:
            print(f"Error loading config: {e}")

    def _save_config(self):
        """Save current folder and playback position to config file"""
        config = {
            'last_folder': self.last_folder,
            'last_index': self.current_index if self.current_index is not None else 0,
            'volume': int(self.volume_scale.get())
        }
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _on_closing(self):
        """Handle window close event"""
        self._save_config()
        pygame.mixer.music.stop()
        self.root.destroy()

    # ---------- UI & Style ----------

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Modern color palette
        bg_main = "#0a0e1a"      # Deep navy
        bg_card = "#151b2e"      # Card background
        bg_hover = "#1f2937"     # Hover state
        accent = "#8b5cf6"       # Purple
        accent_light = "#a78bfa" # Light purple
        text_primary = "#f3f4f6"
        text_secondary = "#9ca3af"
        border = "#2d3748"

        self.bg_main = bg_main
        self.bg_card = bg_card
        self.accent = accent
        self.text_primary = text_primary
        self.text_secondary = text_secondary

        self.root.configure(bg=bg_main)

        # Frame styles
        style.configure("TFrame", background=bg_main)
        style.configure("Card.TFrame", background=bg_card, relief="flat")
        
        # Label styles
        style.configure("TLabel", 
                       background=bg_main, 
                       foreground=text_primary,
                       font=("Segoe UI", 10))
        style.configure("Card.TLabel", 
                       background=bg_card, 
                       foreground=text_primary)
        style.configure("Heading.TLabel", 
                       font=("Segoe UI", 24, "bold"),
                       foreground=text_primary)
        style.configure("SubHeading.TLabel", 
                       font=("Segoe UI", 12),
                       foreground=text_secondary)
        style.configure("PlayingTitle.TLabel",
                       font=("Segoe UI", 16, "bold"),
                       foreground=accent_light)

        # Button styles with modern look
        style.configure("Accent.TButton",
                        font=("Segoe UI", 10, "bold"),
                        borderwidth=0,
                        relief="flat",
                        padding=(12, 8))
        style.map("Accent.TButton",
                  background=[("active", accent_light), ("!active", accent)],
                  foreground=[("active", "#ffffff"), ("!active", "#ffffff")])

        style.configure("Control.TButton",
                        font=("Segoe UI", 11),
                        borderwidth=0,
                        relief="flat",
                        padding=(10, 6))
        style.map("Control.TButton",
                  background=[("active", bg_hover), ("!active", bg_card)],
                  foreground=[("active", accent_light), ("!active", text_primary)])

        # Treeview (playlist) with modern styling
        style.configure("Playlist.Treeview",
                        background=bg_card,
                        foreground=text_primary,
                        fieldbackground=bg_card,
                        rowheight=32,
                        bordercolor=border,
                        borderwidth=1,
                        relief="flat")
        style.configure("Playlist.Treeview.Heading",
                        background=bg_card,
                        foreground=text_secondary,
                        borderwidth=0,
                        relief="flat",
                        font=("Segoe UI", 10, "bold"))
        style.map("Playlist.Treeview",
                  background=[('selected', accent)],
                  foreground=[('selected', '#ffffff')])
        style.map("Playlist.Treeview.Heading",
                  background=[("active", bg_hover)])

        # Scale (slider) styling
        style.configure("TScale",
                       background=bg_card,
                       troughcolor=bg_hover,
                       borderwidth=0,
                       relief="flat")

    def _build_ui(self):
        # Main container with padding
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Top bar with gradient effect simulation
        top_frame = ttk.Frame(container)
        top_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 20))

        # Title section
        title_container = ttk.Frame(top_frame)
        title_container.pack(side=tk.LEFT)

        title_label = ttk.Label(
            title_container,
            text="🎵 ABs Music Player",
            style="Heading.TLabel"
        )
        title_label.pack(side=tk.TOP, anchor="w")

        subtitle_label = ttk.Label(
            title_container,
            text="Your personal music sanctuary",
            style="SubHeading.TLabel"
        )
        subtitle_label.pack(side=tk.TOP, anchor="w")

        # Choose folder button
        choose_btn = ttk.Button(
            top_frame,
            text="📂  Choose Folder",
            style="Accent.TButton",
            command=self.choose_folder
        )
        choose_btn.pack(side=tk.RIGHT, pady=10)

        # Main content area
        main_frame = ttk.Frame(container)
        main_frame.pack(fill=tk.BOTH, expand=True)

        main_frame.columnconfigure(0, weight=2, minsize=350)
        main_frame.columnconfigure(1, weight=3)
        main_frame.rowconfigure(0, weight=1)

        # -------- LEFT: Playlist Card --------
        playlist_card = self._create_card(main_frame, "")
        playlist_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # Playlist header
        playlist_header = ttk.Frame(playlist_card, style="Card.TFrame")
        playlist_header.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(20, 10))

        ttk.Label(
            playlist_header,
            text="📋 Playlist",
            style="Card.TLabel",
            font=("Segoe UI", 14, "bold")
        ).pack(side=tk.LEFT)

        self.song_count_label = ttk.Label(
            playlist_header,
            text="0 songs",
            style="Card.TLabel",
            font=("Segoe UI", 9),
            foreground=self.text_secondary
        )
        self.song_count_label.pack(side=tk.RIGHT)

        # Treeview for playlist
        tree_frame = ttk.Frame(playlist_card, style="Card.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        columns = ("#", "Title", "Duration")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="Playlist.Treeview",
            selectmode="browse"
        )
        
        self.tree.heading("#", text="#")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Duration", text="⏱")

        self.tree.column("#", width=50, anchor="center", stretch=False)
        self.tree.column("Title", width=250, anchor="w")
        self.tree.column("Duration", width=80, anchor="center", stretch=False)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        # Scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # -------- RIGHT: Player Card --------
        player_card = self._create_card(main_frame, "")
        player_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        player_card.rowconfigure(0, weight=1)
        player_card.rowconfigure(1, weight=0)
        player_card.rowconfigure(2, weight=0)
        player_card.rowconfigure(3, weight=0)

        # Now Playing Section
        now_playing_section = ttk.Frame(player_card, style="Card.TFrame")
        now_playing_section.grid(row=0, column=0, sticky="nsew", padx=25, pady=(25, 10))

        # Album art placeholder (visual element)
        album_frame = tk.Frame(
            now_playing_section,
            bg="#1f2937",
            width=180,
            height=180,
            relief="flat",
            borderwidth=0
        )
        album_frame.pack(pady=(0, 20))
        album_frame.pack_propagate(False)

        album_icon = ttk.Label(
            album_frame,
            text="🎵",
            font=("Segoe UI", 72),
            background="#1f2937",
            foreground=self.accent
        )
        album_icon.place(relx=0.5, rely=0.5, anchor="center")

        # Song title
        self.now_playing_label = ttk.Label(
            now_playing_section,
            text="No song playing",
            style="PlayingTitle.TLabel",
            wraplength=450
        )
        self.now_playing_label.pack(pady=(0, 8))

        # Song details grid
        details_grid = ttk.Frame(now_playing_section, style="Card.TFrame")
        details_grid.pack(pady=(10, 0))

        detail_style = {"style": "Card.TLabel", "font": ("Segoe UI", 9)}
        label_style = {"style": "Card.TLabel", "font": ("Segoe UI", 9, "bold"), 
                      "foreground": self.text_secondary}

        ttk.Label(details_grid, text="File:", **label_style).grid(row=0, column=0, sticky="nw", padx=(0, 10))
        
        # Scrollable text widget for file path
        file_frame = ttk.Frame(details_grid, style="Card.TFrame")
        file_frame.grid(row=0, column=1, sticky="ew")
        details_grid.columnconfigure(1, weight=1)
        
        self.file_text = tk.Text(
            file_frame,
            height=2,
            wrap=tk.WORD,
            bg=self.bg_card,
            fg=self.text_primary,
            font=("Segoe UI", 9),
            relief="flat",
            borderwidth=0,
            padx=5,
            pady=2
        )
        self.file_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_text.insert("1.0", "—")
        self.file_text.config(state=tk.DISABLED)
        
        file_scroll = ttk.Scrollbar(file_frame, orient="vertical", command=self.file_text.yview)
        self.file_text.configure(yscrollcommand=file_scroll.set)
        file_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(details_grid, text="Duration:", **label_style).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(6, 0))
        self.duration_value = ttk.Label(details_grid, text="—", **detail_style)
        self.duration_value.grid(row=1, column=1, sticky="w", pady=(6, 0))

        ttk.Label(details_grid, text="Track:", **label_style).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=(6, 0))
        self.index_value = ttk.Label(details_grid, text="—", **detail_style)
        self.index_value.grid(row=2, column=1, sticky="w", pady=(6, 0))

        # Progress section
        progress_section = ttk.Frame(player_card, style="Card.TFrame")
        progress_section.grid(row=1, column=0, sticky="ew", padx=25, pady=(15, 10))

        self.time_label = ttk.Label(
            progress_section,
            text="00:00 / 00:00",
            style="Card.TLabel",
            font=("Segoe UI", 11, "bold"),
            foreground=self.accent
        )
        self.time_label.pack(side=tk.TOP, anchor="w", pady=(0, 8))

        self.progress_scale = ttk.Scale(
            progress_section,
            from_=0,
            to=100,
            orient="horizontal",
            style="TScale",
            command=self._on_progress_drag
        )
        self.progress_scale.pack(fill=tk.X)
        self.progress_scale.bind("<ButtonRelease-1>", self._on_progress_click)

        # Control buttons section
        controls_section = ttk.Frame(player_card, style="Card.TFrame")
        controls_section.grid(row=2, column=0, sticky="ew", padx=25, pady=(15, 10))

        controls_section.columnconfigure(0, weight=1)
        controls_section.columnconfigure(1, weight=1)
        controls_section.columnconfigure(2, weight=1)
        controls_section.columnconfigure(3, weight=1)

        btn_config = {"style": "Control.TButton", "width": 10}

        self.prev_btn = ttk.Button(
            controls_section,
            text="⏮  Prev",
            command=self.play_previous,
            **btn_config
        )
        self.prev_btn.grid(row=0, column=0, padx=3, pady=4, sticky="ew")

        self.play_pause_btn = ttk.Button(
            controls_section,
            text="▶  Play",
            command=self.play_pause,
            **btn_config
        )
        self.play_pause_btn.grid(row=0, column=1, padx=3, pady=4, sticky="ew")

        self.next_btn = ttk.Button(
            controls_section,
            text="Next  ⏭",
            command=self.play_next,
            **btn_config
        )
        self.next_btn.grid(row=0, column=2, padx=3, pady=4, sticky="ew")

        self.stop_btn = ttk.Button(
            controls_section,
            text="⏹  Stop",
            command=self.stop,
            **btn_config
        )
        self.stop_btn.grid(row=0, column=3, padx=3, pady=4, sticky="ew")

        # Volume and mute section
        volume_section = ttk.Frame(player_card, style="Card.TFrame")
        volume_section.grid(row=3, column=0, sticky="ew", padx=25, pady=(10, 25))

        volume_section.columnconfigure(1, weight=1)

        self.mute_btn = ttk.Button(
            volume_section,
            text="🔊",
            command=self.toggle_mute,
            style="Control.TButton",
            width=4
        )
        self.mute_btn.grid(row=0, column=0, padx=(0, 10))

        volume_label = ttk.Label(
            volume_section,
            text="Volume",
            style="Card.TLabel",
            font=("Segoe UI", 9, "bold"),
            foreground=self.text_secondary
        )
        volume_label.grid(row=0, column=1, sticky="w")

        self.volume_scale = ttk.Scale(
            volume_section,
            from_=0,
            to=100,
            orient="horizontal",
            command=self.on_volume_change,
            style="TScale"
        )
        self.volume_scale.grid(row=0, column=2, sticky="ew", padx=(10, 0))
        self.volume_scale.set(70)
        pygame.mixer.music.set_volume(0.7)

    def _create_card(self, parent, title):
        """Helper to create modern card-style frames"""
        card = tk.Frame(
            parent,
            bg=self.bg_card,
            relief="flat",
            borderwidth=0
        )
        return card

    # ---------- Song loading (optimized with threading) ----------

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        
        self.last_folder = folder
        self._load_songs_threaded(folder, 0)

    def _load_songs_threaded(self, folder_path, start_index=0):
        """Load songs in a background thread to prevent UI freezing"""
        if self.loading_in_progress:
            return
        
        self.loading_in_progress = True
        self.now_playing_label.config(text="Loading songs...")
        
        def load_task():
            try:
                self._load_songs_from_folder(folder_path, start_index)
            finally:
                self.loading_in_progress = False
        
        thread = threading.Thread(target=load_task, daemon=True)
        thread.start()

    def _load_songs_from_folder(self, folder_path, start_index=0):
        """Fast song loading using mutagen for metadata"""
        self.songs.clear()
        
        # Clear tree in main thread
        self.root.after(0, lambda: [self.tree.delete(item) for item in self.tree.get_children()])

        files = sorted(
            f for f in os.listdir(folder_path)
            if f.lower().endswith(AUDIO_EXTENSIONS)
        )

        if not files:
            self.root.after(0, lambda: messagebox.showinfo("No songs", "No audio files found in this folder."))
            return

        for idx, filename in enumerate(files, start=1):
            full_path = os.path.join(folder_path, filename)
            title = os.path.splitext(filename)[0]
            length_seconds = self._get_audio_length_fast(full_path)

            song_data = {
                "path": full_path,
                "title": title,
                "length": length_seconds
            }
            self.songs.append(song_data)

            # Insert into tree in main thread
            duration_str = self._format_time(length_seconds) if length_seconds else "—"
            self.root.after(0, lambda i=idx, t=title, d=duration_str: 
                           self.tree.insert("", "end", values=(i, t, d)))

        # Update song count
        count_text = f"{len(files)} song{'s' if len(files) != 1 else ''}"
        self.root.after(0, lambda: self.song_count_label.config(text=count_text))

        # Select the starting song
        def select_song():
            tree_items = self.tree.get_children()
            if tree_items and 0 <= start_index < len(tree_items):
                self.tree.selection_set(tree_items[start_index])
                self.tree.focus(tree_items[start_index])
                self.tree.see(tree_items[start_index])
                self.current_index = start_index
                self._update_details_panel()
            self.now_playing_label.config(text="No song playing")
        
        self.root.after(0, select_song)

    def _get_audio_length_fast(self, path):
        """Fast audio length detection using mutagen (metadata based)"""
        try:
            audio = MutagenFile(path)
            if audio is not None and audio.info is not None:
                return audio.info.length
        except:
            pass
        
        # Fallback to pygame
        try:
            snd = pygame.mixer.Sound(path)
            return snd.get_length()
        except:
            return 0

    # ---------- Playback logic ----------

    def on_tree_select(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        values = self.tree.item(item_id, "values")
        index = int(values[0]) - 1
        self.current_index = index
        self._update_details_panel()

    def on_tree_double_click(self, event=None):
        self.play_selected_song()

    def play_selected_song(self):
        if self.current_index is None and self.songs:
            self.current_index = 0
        if self.current_index is not None:
            self._play_song_at_index(self.current_index)

    def _play_song_at_index(self, index):
        if not self.songs:
            return

        index = index % len(self.songs)
        self.current_index = index
        song = self.songs[index]
        try:
            pygame.mixer.music.load(song["path"])
            pygame.mixer.music.play()
            self.is_paused = False
            self.play_pause_btn.config(text="⏸  Pause")

            self.current_length = song["length"] or 0
            self.play_start_time = time.time()

            self._update_details_panel(now_playing=True)

            tree_items = self.tree.get_children()
            if 0 <= index < len(tree_items):
                self.tree.selection_set(tree_items[index])
                self.tree.focus(tree_items[index])
                self.tree.see(tree_items[index])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play song:\n{song['title']}\n\n{e}")

    def play_pause(self):
        if not self.songs:
            return

        if pygame.mixer.music.get_busy() and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.play_pause_btn.config(text="▶  Resume")
        else:
            if self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.play_pause_btn.config(text="⏸  Pause")
            else:
                self.play_selected_song()

    def play_next(self):
        if not self.songs:
            return
        if self.current_index is None:
            self.current_index = 0
        else:
            self.current_index = (self.current_index + 1) % len(self.songs)
        self._play_song_at_index(self.current_index)

    def play_previous(self):
        if not self.songs:
            return
        if self.current_index is None:
            self.current_index = 0
        else:
            self.current_index = (self.current_index - 1) % len(self.songs)
        self._play_song_at_index(self.current_index)

    def stop(self):
        self.manual_stop = True
        pygame.mixer.music.stop()
        self.is_paused = False
        self.play_pause_btn.config(text="▶  Play")

        self.progress_scale.set(0)
        self.time_label.config(text="00:00 / 00:00")

    def toggle_mute(self):
        if self.is_muted:
            vol = self.volume_scale.get() / 100.0
            pygame.mixer.music.set_volume(vol)
            self.is_muted = False
            self.mute_btn.config(text="🔊")
        else:
            pygame.mixer.music.set_volume(0.0)
            self.is_muted = True
            self.mute_btn.config(text="🔇")

    def on_volume_change(self, value):
        if not self.is_muted:
            vol = float(value) / 100.0
            pygame.mixer.music.set_volume(vol)

    # ---------- Progress bar seeking ----------

    def _on_progress_drag(self, value):
        """Handle dragging the progress bar"""
        pass  # Just visual update during drag

    def _on_progress_click(self, event):
        """Handle clicking or releasing on progress bar to seek"""
        if not self.songs or self.current_index is None:
            return
        
        if self.current_length <= 0:
            return
        
        # Get the position value (0-100)
        position_percent = self.progress_scale.get()
        
        # Calculate target time in seconds
        target_time = (position_percent / 100.0) * self.current_length
        
        # Seek to position
        self._seek_to_position(target_time)

    def _seek_to_position(self, target_seconds):
        """Seek to a specific position in the current song"""
        if not self.songs or self.current_index is None:
            return
        
        song = self.songs[self.current_index]
        
        try:
            # Stop current playback
            was_playing = pygame.mixer.music.get_busy() and not self.is_paused
            pygame.mixer.music.stop()
            
            # Reload and play from position
            pygame.mixer.music.load(song["path"])
            pygame.mixer.music.play(start=target_seconds)
            
            # Restore paused state if it was paused
            if not was_playing and self.is_paused:
                pygame.mixer.music.pause()
            else:
                self.is_paused = False
                self.play_pause_btn.config(text="⏸  Pause")
            
            # Reset start time for accurate position tracking
            self.play_start_time = time.time()
            
        except Exception as e:
            print(f"Seek error: {e}")

    # ---------- UI helpers ----------

    def _update_details_panel(self, now_playing=False):
        if self.current_index is None or not self.songs:
            return
        song = self.songs[self.current_index]
        title = song["title"]
        path = song["path"]
        length = song["length"] or 0

        if now_playing:
            self.now_playing_label.config(text=title)
        else:
            self.now_playing_label.config(text=title)

        # Update file path in text widget
        self.file_text.config(state=tk.NORMAL)
        self.file_text.delete("1.0", tk.END)
        self.file_text.insert("1.0", path)
        self.file_text.config(state=tk.DISABLED)
        
        self.duration_value.config(text=self._format_time(length) if length else "—")
        self.index_value.config(text=str(self.current_index + 1))

    def _format_time(self, seconds):
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    # ---------- Progress bar update & auto-next ----------

    def _schedule_progress_update(self):
        self._update_progress()
        self.root.after(500, self._schedule_progress_update)

    def _update_progress(self):
        if not self.songs or self.current_index is None:
            return

        if not self.is_paused and not pygame.mixer.music.get_busy():
            if self.manual_stop:
                self.manual_stop = False
                return

            if self.play_start_time and (time.time() - self.play_start_time) > 1.0:
                if self.auto_next_enabled:
                    self.play_next()
            return

        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            pos_ms = 0

        current_sec = pos_ms // 1000
        total_sec = int(self.current_length)

        if total_sec > 0:
            progress = (current_sec / total_sec) * 100
            self.progress_scale.set(progress)
            self.time_label.config(
                text=f"{self._format_time(current_sec)} / {self._format_time(total_sec)}"
            )
        else:
            self.progress_scale.set(0)
            self.time_label.config(
                text=f"{self._format_time(current_sec)} / 00:00"
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicPlayerGUI(root)
    root.mainloop()