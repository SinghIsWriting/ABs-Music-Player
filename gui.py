import os, sys
import time
import pygame
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# --------- Pygame init for audio ----------
pygame.mixer.init()

AUDIO_EXTENSIONS = ('.mp3', '.wav', '.ogg')

def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(relative)


class MusicPlayerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ABs Music Player")
        self.root.geometry("950x580")
        self.root.minsize(800, 500)
        self.root.iconbitmap(resource_path("assets/icon.ico"))

        # State
        self.songs = []              # list of dicts: {path, title, length}
        self.current_index = None
        self.is_paused = False
        self.is_muted = False
        self.current_length = 0
        self.play_start_time = None  # for detecting "just started"
        self.auto_next_enabled = True
        self.manual_stop = False

        # UI setup
        self._setup_style()
        self._build_ui()

        # Start updating progress bar
        self._schedule_progress_update()

    # ---------- UI & Style ----------

    def _setup_style(self):
        style = ttk.Style()
        # Use a theme that supports styling (on Windows 'vista', on others 'clam')
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg_main = "#111827"   # dark slate
        bg_card = "#1f2937"   # slightly lighter
        accent = "#6366f1"    # indigo
        text_light = "#e5e7eb"

        self.bg_main = bg_main
        self.bg_card = bg_card
        self.accent = accent
        self.text_light = text_light

        self.root.configure(bg=bg_main)

        style.configure("TFrame", background=bg_main)
        style.configure("Card.TFrame", background=bg_card)
        style.configure("TLabel", background=bg_main, foreground=text_light)
        style.configure("Card.TLabel", background=bg_card, foreground=text_light)
        style.configure("Heading.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("SubHeading.TLabel", font=("Segoe UI", 11))

        style.configure("Accent.TButton",
                        font=("Segoe UI", 11, "bold"),
                        padding=6)
        style.map("Accent.TButton",
                  background=[("active", accent)],
                  foreground=[("active", "#ffffff")])

        # For Treeview (playlist)
        style.configure("Playlist.Treeview",
                        background=bg_card,
                        foreground=text_light,
                        fieldbackground=bg_card,
                        rowheight=26,
                        bordercolor=bg_card,
                        borderwidth=0)
        style.configure("Playlist.Treeview.Heading",
                        background=bg_card,
                        foreground=text_light,
                        font=("Segoe UI", 10, "bold"))
        style.map("Playlist.Treeview",
                  background=[('selected', accent)])

    def _build_ui(self):
        # Top bar
        top_frame = ttk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=16, pady=(12, 8))

        title_label = ttk.Label(
            top_frame,
            text="🎧 ABs Music Player",
            style="Heading.TLabel"
        )
        title_label.pack(side=tk.LEFT)

        choose_btn = ttk.Button(
            top_frame,
            text="📂 Choose Songs",
            style="Accent.TButton",
            command=self.choose_folder
        )
        choose_btn.pack(side=tk.RIGHT, padx=(8, 0))

        # Main area → left: playlist, right: details & controls
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        main_frame.columnconfigure(0, weight=2)
        main_frame.columnconfigure(1, weight=3)
        main_frame.rowconfigure(0, weight=1)

        # -------- Playlist (left) --------
        playlist_card = ttk.Frame(main_frame, style="Card.TFrame")
        playlist_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        header = ttk.Label(
            playlist_card,
            text="Playlist",
            style="Card.TLabel",
            font=("Segoe UI", 13, "bold")
        )
        header.pack(side=tk.TOP, anchor="w", padx=12, pady=(10, 4))

        # Treeview for playlist
        columns = ("#", "Title", "Duration")
        self.tree = ttk.Treeview(
            playlist_card,
            columns=columns,
            show="headings",
            style="Playlist.Treeview"
        )
        self.tree.heading("#", text="#")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Duration", text="Duration")

        self.tree.column("#", width=40, anchor="center")
        self.tree.column("Title", width=220, anchor="w")
        self.tree.column("Duration", width=80, anchor="center")

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        vsb = ttk.Scrollbar(playlist_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=(0, 10))
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 10))

        # -------- Details & controls (right) --------
        right_card = ttk.Frame(main_frame, style="Card.TFrame")
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        right_card.rowconfigure(0, weight=1)
        right_card.rowconfigure(1, weight=0)
        right_card.rowconfigure(2, weight=0)
        right_card.columnconfigure(0, weight=1)

        # Song details
        details_frame = ttk.Frame(right_card, style="Card.TFrame")
        details_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=(10, 4))

        details_frame.columnconfigure(1, weight=1)

        # "Now playing" label
        self.now_playing_label = ttk.Label(
            details_frame,
            text="Now Playing...",
            style="Card.TLabel",
            font=("Segoe UI", 14, "bold")
        )
        self.now_playing_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        # File path, duration, index
        ttk.Label(details_frame, text="File:", style="Card.TLabel").grid(row=1, column=0, sticky="w")
        self.file_value = ttk.Label(details_frame, text="—", style="Card.TLabel", wraplength=400)
        self.file_value.grid(row=1, column=1, sticky="w")

        ttk.Label(details_frame, text="Duration:", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.duration_value = ttk.Label(details_frame, text="—", style="Card.TLabel")
        self.duration_value.grid(row=2, column=1, sticky="w", pady=(4, 0))

        ttk.Label(details_frame, text="Track #:", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=(4, 0))
        self.index_value = ttk.Label(details_frame, text="—", style="Card.TLabel")
        self.index_value.grid(row=3, column=1, sticky="w", pady=(4, 0))

        # Progress bar & time
        progress_frame = ttk.Frame(right_card, style="Card.TFrame")
        progress_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 4))
        progress_frame.columnconfigure(0, weight=1)

        self.progress_scale = ttk.Scale(progress_frame, from_=0, to=100, orient="horizontal")
        self.progress_scale.grid(row=0, column=0, sticky="ew")

        self.time_label = ttk.Label(
            progress_frame,
            text="00:00 / 00:00",
            style="Card.TLabel",
            font=("Segoe UI", 9)
        )
        self.time_label.grid(row=1, column=0, sticky="e", pady=(2, 0))

        # Controls (bottom)
        controls_frame = ttk.Frame(right_card, style="Card.TFrame")
        controls_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))

        controls_frame.columnconfigure(0, weight=1)
        controls_frame.columnconfigure(1, weight=1)
        controls_frame.columnconfigure(2, weight=1)
        controls_frame.columnconfigure(3, weight=1)
        controls_frame.columnconfigure(4, weight=1)
        controls_frame.columnconfigure(5, weight=1)

        self.prev_btn = ttk.Button(
            controls_frame, text="⏮ Prev",
            style="Accent.TButton",
            command=self.play_previous
        )
        self.prev_btn.grid(row=0, column=0, padx=4, pady=6, sticky="ew")

        self.play_pause_btn = ttk.Button(
            controls_frame, text="▶ Play",
            style="Accent.TButton",
            command=self.play_pause
        )
        self.play_pause_btn.grid(row=0, column=1, padx=4, pady=6, sticky="ew")

        self.next_btn = ttk.Button(
            controls_frame, text="⏭ Next",
            style="Accent.TButton",
            command=self.play_next
        )
        self.next_btn.grid(row=0, column=2, padx=4, pady=6, sticky="ew")

        self.stop_btn = ttk.Button(
            controls_frame, text="⏹ Stop",
            style="Accent.TButton",
            command=self.stop
        )
        self.stop_btn.grid(row=0, column=3, padx=4, pady=6, sticky="ew")

        self.mute_btn = ttk.Button(
            controls_frame, text="🔊 Mute",
            style="Accent.TButton",
            command=self.toggle_mute
        )
        self.mute_btn.grid(row=0, column=4, padx=4, pady=6, sticky="ew")

        # Volume slider
        volume_frame = ttk.Frame(controls_frame, style="Card.TFrame")
        volume_frame.grid(row=0, column=5, padx=4, sticky="ew")
        ttk.Label(volume_frame, text="Vol", style="Card.TLabel").pack(anchor="w")
        self.volume_scale = ttk.Scale(
            volume_frame,
            from_=0,
            to=100,
            orient="horizontal",
            command=self.on_volume_change
        )
        self.volume_scale.pack(fill="x")
        self.volume_scale.set(70)
        pygame.mixer.music.set_volume(0.7)

    # ---------- Song loading ----------

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.load_songs_from_folder(folder)

    def load_songs_from_folder(self, folder_path):
        self.songs.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

        files = sorted(
            f for f in os.listdir(folder_path)
            if f.lower().endswith(AUDIO_EXTENSIONS)
        )

        if not files:
            messagebox.showinfo("No songs", "No audio files found in this folder.")
            return

        for idx, filename in enumerate(files, start=1):
            full_path = os.path.join(folder_path, filename)
            title = os.path.splitext(filename)[0]
            length_seconds = self._get_audio_length_safe(full_path)

            self.songs.append({
                "path": full_path,
                "title": title,
                "length": length_seconds
            })

            self.tree.insert(
                "",
                "end",
                values=(idx, title, self._format_time(length_seconds) if length_seconds else "—")
            )

        # Auto-select first song
        first = self.tree.get_children()[0]
        self.tree.selection_set(first)
        self.tree.focus(first)
        self.on_tree_select()

    def _get_audio_length_safe(self, path):
        """
        Try to get song length using pygame.mixer.Sound.
        If it fails (unsupported format, etc.), return 0.
        """
        try:
            snd = pygame.mixer.Sound(path)
            return snd.get_length()
        except Exception:
            return 0

    # ---------- Playback logic ----------

    def on_tree_select(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        values = self.tree.item(item_id, "values")
        index = int(values[0]) - 1  # first column is "#"
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
            self.play_pause_btn.config(text="⏸ Pause")

            self.current_length = song["length"] or 0
            self.play_start_time = time.time()

            # Update UI details
            self._update_details_panel(now_playing=True)

            # Visually select in playlist
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
            # Pause
            pygame.mixer.music.pause()
            self.is_paused = True
            self.play_pause_btn.config(text="▶ Resume")
        else:
            # Resume or start new song
            if self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.play_pause_btn.config(text="⏸ Pause")
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
        self.manual_stop = True  # prevent auto-next
        pygame.mixer.music.stop()
        self.is_paused = False
        self.play_pause_btn.config(text="▶ Play")

        self.progress_scale.set(0)
        self.time_label.config(text="00:00 / 00:00")

    def toggle_mute(self):
        if self.is_muted:
            # Unmute
            vol = self.volume_scale.get() / 100.0
            pygame.mixer.music.set_volume(vol)
            self.is_muted = False
            self.mute_btn.config(text="🔊 Mute")
        else:
            # Mute
            pygame.mixer.music.set_volume(0.0)
            self.is_muted = True
            self.mute_btn.config(text="🔇 Unmute")

    def on_volume_change(self, value):
        if not self.is_muted:
            vol = float(value) / 100.0
            pygame.mixer.music.set_volume(vol)

    # ---------- UI helpers ----------

    def _update_details_panel(self, now_playing=False):
        if self.current_index is None or not self.songs:
            return
        song = self.songs[self.current_index]
        title = song["title"]
        path = song["path"]
        length = song["length"] or 0

        if now_playing:
            self.now_playing_label.config(text=f"Now Playing: {title}")
        else:
            self.now_playing_label.config(text=f"Selected: {title}")

        self.file_value.config(text=path)
        self.duration_value.config(text=self._format_time(length) if length else "—")
        self.index_value.config(text=str(self.current_index + 1))

    def _format_time(self, seconds):
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    # ---------- Progress bar update & auto-next ----------

    def _schedule_progress_update(self):
        self._update_progress()
        # Call again every 500 ms
        self.root.after(500, self._schedule_progress_update)

    def _update_progress(self):
        if not self.songs or self.current_index is None:
            return

        # auto-next logic
        if not self.is_paused and not pygame.mixer.music.get_busy():
            if self.manual_stop:
                self.manual_stop = False  # reset block for next time
                return   # DO NOT auto-next

            if self.play_start_time and (time.time() - self.play_start_time) > 1.0:
                if self.auto_next_enabled:
                    self.play_next()
            return

        # Progress bar & time
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
            # Unknown total length
            self.progress_scale.set(0)
            self.time_label.config(
                text=f"{self._format_time(current_sec)} / 00:00"
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicPlayerGUI(root)
    root.mainloop()







# import os
# import time
# import pygame
# import customtkinter as ctk
# from tkinter import filedialog, messagebox

# # --------- Pygame init for audio ----------
# pygame.mixer.init()

# AUDIO_EXTENSIONS = ('.mp3', '.wav', '.ogg')


# class MusicPlayerApp(ctk.CTk):
#     def __init__(self):
#         super().__init__()

#         # -------- Window setup --------
#         ctk.set_appearance_mode("dark")          # "dark" / "light" / "system"
#         ctk.set_default_color_theme("blue")      # "blue", "green", "dark-blue"

#         self.title("🎧 Modern Music Player")
#         self.geometry("1000x600")
#         self.minsize(850, 500)

#         # -------- Player state --------
#         self.songs = []              # list of dicts: {path, title, length}
#         self.current_index = None
#         self.is_paused = False
#         self.is_muted = False
#         self.current_length = 0
#         self.play_start_time = None
#         self.auto_next_enabled = True
#         self.manual_stop = False     # so "Stop" doesn't auto-play next
#         self.song_buttons = []       # for highlighting selected song

#         # -------- Layout --------
#         self._build_ui()

#         # start progress updater
#         self._schedule_progress_update()

#     # ---------------- UI BUILDING ----------------

#     def _build_ui(self):
#         # Top Bar
#         top_frame = ctk.CTkFrame(self, fg_color="transparent")
#         top_frame.pack(side="top", fill="x", padx=20, pady=(15, 10))

#         title_label = ctk.CTkLabel(
#             top_frame,
#             text="Modern Music Player",
#             font=ctk.CTkFont(size=22, weight="bold")
#         )
#         title_label.pack(side="left")

#         choose_btn = ctk.CTkButton(
#             top_frame,
#             text="📂 Choose Folder",
#             command=self.choose_folder,
#             corner_radius=20
#         )
#         choose_btn.pack(side="right")

#         # Main content: left (playlist) and right (details+controls)
#         main_frame = ctk.CTkFrame(self, fg_color="transparent")
#         main_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

#         main_frame.grid_columnconfigure(0, weight=2)
#         main_frame.grid_columnconfigure(1, weight=3)
#         main_frame.grid_rowconfigure(0, weight=1)

#         # -------- Left: Playlist --------
#         playlist_card = ctk.CTkFrame(main_frame, corner_radius=20)
#         playlist_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

#         header = ctk.CTkLabel(
#             playlist_card,
#             text="Playlist",
#             font=ctk.CTkFont(size=16, weight="bold")
#         )
#         header.pack(anchor="w", padx=16, pady=(12, 4))

#         subtitle = ctk.CTkLabel(
#             playlist_card,
#             text="Select a song to play",
#             font=ctk.CTkFont(size=11)
#         )
#         subtitle.pack(anchor="w", padx=16, pady=(0, 8))

#         # Scrollable song list
#         self.playlist_frame = ctk.CTkScrollableFrame(
#             playlist_card,
#             corner_radius=16,
#             fg_color=("gray16", "gray90"),
#             label_text="Songs",
#         )
#         self.playlist_frame.pack(fill="both", expand=True, padx=12, pady=12)

#         # -------- Right: Details + Controls --------
#         right_card = ctk.CTkFrame(main_frame, corner_radius=20)
#         right_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

#         right_card.grid_rowconfigure(0, weight=2)
#         right_card.grid_rowconfigure(1, weight=1)
#         right_card.grid_rowconfigure(2, weight=1)
#         right_card.grid_columnconfigure(0, weight=1)

#         # --- Song details card ---
#         details_card = ctk.CTkFrame(right_card, corner_radius=20)
#         details_card.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 10))

#         details_card.grid_columnconfigure(1, weight=1)

#         self.now_playing_label = ctk.CTkLabel(
#             details_card,
#             text="Now Playing: —",
#             font=ctk.CTkFont(size=18, weight="bold")
#         )
#         self.now_playing_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 6))

#         # Info labels
#         ctk.CTkLabel(details_card, text="Track #:", anchor="w").grid(
#             row=1, column=0, sticky="w", padx=14, pady=(4, 0)
#         )
#         self.track_value = ctk.CTkLabel(details_card, text="—", anchor="w")
#         self.track_value.grid(row=1, column=1, sticky="w", padx=(0, 14), pady=(4, 0))

#         ctk.CTkLabel(details_card, text="Title:", anchor="w").grid(
#             row=2, column=0, sticky="w", padx=14, pady=(4, 0)
#         )
#         self.title_value = ctk.CTkLabel(details_card, text="—", anchor="w")
#         self.title_value.grid(row=2, column=1, sticky="w", padx=(0, 14), pady=(4, 0))

#         ctk.CTkLabel(details_card, text="Duration:", anchor="w").grid(
#             row=3, column=0, sticky="w", padx=14, pady=(4, 0)
#         )
#         self.duration_value = ctk.CTkLabel(details_card, text="—", anchor="w")
#         self.duration_value.grid(row=3, column=1, sticky="w", padx=(0, 14), pady=(4, 0))

#         ctk.CTkLabel(details_card, text="File:", anchor="w").grid(
#             row=4, column=0, sticky="nw", padx=14, pady=(6, 6)
#         )
#         self.path_value = ctk.CTkLabel(
#             details_card,
#             text="—",
#             anchor="nw",
#             justify="left",
#             wraplength=400
#         )
#         self.path_value.grid(row=4, column=1, sticky="w", padx=(0, 14), pady=(6, 10))

#         # --- Progress section ---
#         progress_card = ctk.CTkFrame(right_card, corner_radius=20)
#         progress_card.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))

#         ctk.CTkLabel(
#             progress_card,
#             text="Playback",
#             font=ctk.CTkFont(size=13, weight="bold")
#         ).pack(anchor="w", padx=14, pady=(10, 0))

#         self.progress_slider = ctk.CTkSlider(
#             progress_card,
#             from_=0,
#             to=100,
#             number_of_steps=100,
#             state="disabled"
#         )
#         self.progress_slider.pack(fill="x", padx=14, pady=(10, 4))

#         self.time_label = ctk.CTkLabel(
#             progress_card,
#             text="00:00 / 00:00",
#             font=ctk.CTkFont(size=11)
#         )
#         self.time_label.pack(anchor="e", padx=14, pady=(0, 10))

#         # --- Controls & volume ---
#         controls_card = ctk.CTkFrame(right_card, corner_radius=20)
#         controls_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))

#         for col in range(6):
#             controls_card.grid_columnconfigure(col, weight=1)

#         self.prev_btn = ctk.CTkButton(
#             controls_card, text="⏮", width=40, command=self.play_previous
#         )
#         self.prev_btn.grid(row=0, column=0, padx=6, pady=12, sticky="ew")

#         self.play_pause_btn = ctk.CTkButton(
#             controls_card, text="▶", width=40, command=self.play_pause
#         )
#         self.play_pause_btn.grid(row=0, column=1, padx=6, pady=12, sticky="ew")

#         self.next_btn = ctk.CTkButton(
#             controls_card, text="⏭", width=40, command=self.play_next
#         )
#         self.next_btn.grid(row=0, column=2, padx=6, pady=12, sticky="ew")

#         self.stop_btn = ctk.CTkButton(
#             controls_card, text="⏹", width=40, command=self.stop
#         )
#         self.stop_btn.grid(row=0, column=3, padx=6, pady=12, sticky="ew")

#         self.mute_btn = ctk.CTkButton(
#             controls_card, text="🔊", width=40, command=self.toggle_mute
#         )
#         self.mute_btn.grid(row=0, column=4, padx=6, pady=12, sticky="ew")

#         volume_frame = ctk.CTkFrame(controls_card, fg_color="transparent")
#         volume_frame.grid(row=0, column=5, padx=6, pady=12, sticky="ew")
#         ctk.CTkLabel(volume_frame, text="Vol").pack(anchor="w")
#         self.volume_slider = ctk.CTkSlider(
#             volume_frame,
#             from_=0,
#             to=100,
#             number_of_steps=100,
#             command=self.on_volume_change
#         )
#         self.volume_slider.pack(fill="x")
#         self.volume_slider.set(70)
#         pygame.mixer.music.set_volume(0.7)

#     # ---------------- SONG LOADING ----------------

#     def choose_folder(self):
#         folder = filedialog.askdirectory()
#         if not folder:
#             return
#         self.load_songs_from_folder(folder)

#     def load_songs_from_folder(self, folder_path):
#         # clear previous
#         self.songs.clear()

#         for widget in self.playlist_frame.winfo_children():
#             widget.destroy()

#         self.song_buttons.clear()
#         self.current_index = None
#         self.stop()

#         files = sorted(
#             f for f in os.listdir(folder_path)
#             if f.lower().endswith(AUDIO_EXTENSIONS)
#         )

#         if not files:
#             messagebox.showinfo("No songs", "No audio files found in this folder.")
#             return

#         for idx, filename in enumerate(files, start=1):
#             full_path = os.path.join(folder_path, filename)
#             title = os.path.splitext(filename)[0]
#             length_seconds = self._get_audio_length_safe(full_path)

#             self.songs.append({
#                 "path": full_path,
#                 "title": title,
#                 "length": length_seconds
#             })

#             # ------- Modern Playlist Row Layout -------
#             row_frame = ctk.CTkFrame(
#                 self.playlist_frame,
#                 fg_color="#1f1f1f",       # DARK ROW COLOR
#                 corner_radius=12
#             )
#             row_frame.pack(fill="x", padx=10, pady=6)

#             # clickable entire row
#             row_frame.bind("<Button-1>", lambda e, i=idx - 1: self.on_song_button_click(i))

#             # Song index
#             index_lbl = ctk.CTkLabel(
#                 row_frame,
#                 text=f"{idx:02d}",
#                 font=ctk.CTkFont(size=13, weight="bold"),
#                 text_color="white",
#                 width=35
#             )
#             index_lbl.pack(side="left", padx=(10, 6))
#             index_lbl.bind("<Button-1>", lambda e, i=idx - 1: self.on_song_button_click(i))

#             # Title
#             title_lbl = ctk.CTkLabel(
#                 row_frame,
#                 text=title,
#                 font=ctk.CTkFont(size=14),
#                 text_color="white",
#                 anchor="w"
#             )
#             title_lbl.pack(side="left", padx=10, fill="x", expand=True)
#             title_lbl.bind("<Button-1>", lambda e, i=idx - 1: self.on_song_button_click(i))

#             # Duration on right
#             duration_lbl = ctk.CTkLabel(
#                 row_frame,
#                 text=self._format_time(length_seconds) if length_seconds else "--:--",
#                 font=ctk.CTkFont(size=13),
#                 text_color="#bfbfbf"
#             )
#             duration_lbl.pack(side="right", padx=12)
#             duration_lbl.bind("<Button-1>", lambda e, i=idx - 1: self.on_song_button_click(i))

#             # Save row for highlighting
#             self.song_buttons.append(row_frame)

#         # auto-select first
#         if self.songs:
#             self.on_song_button_click(0)


#     def _get_audio_length_safe(self, path):
#         try:
#             snd = pygame.mixer.Sound(path)
#             return snd.get_length()
#         except Exception:
#             return 0

#     # ---------------- SELECTION & DETAILS ----------------

#     def on_song_button_click(self, index):
#         self.current_index = index
#         self._highlight_selected_button()
#         self._update_details_panel()

#     def _highlight_selected_button(self):
#         for i, frame in enumerate(self.song_buttons):
#             if i == self.current_index:
#                 frame.configure(fg_color="#006eff")   # selected row
#             else:
#                 frame.configure(fg_color="#1f1f1f")   # normal row

#     def _update_details_panel(self, now_playing=False):
#         if self.current_index is None or not self.songs:
#             return
#         song = self.songs[self.current_index]

#         title = song["title"]
#         path = song["path"]
#         length = song["length"] or 0

#         if now_playing:
#             self.now_playing_label.configure(text=f"Now Playing: {title}")
#         else:
#             self.now_playing_label.configure(text=f"Selected: {title}")

#         self.track_value.configure(text=str(self.current_index + 1))
#         self.title_value.configure(text=title)
#         self.duration_value.configure(
#             text=self._format_time(length) if length else "—"
#         )
#         self.path_value.configure(text=path)

#     @staticmethod
#     def _format_time(seconds):
#         seconds = int(seconds)
#         m, s = divmod(seconds, 60)
#         return f"{m:02d}:{s:02d}"

#     # ---------------- PLAYBACK LOGIC ----------------

#     def _play_song_at_index(self, index):
#         if not self.songs:
#             return
#         index = index % len(self.songs)
#         self.current_index = index
#         song = self.songs[index]

#         try:
#             pygame.mixer.music.load(song["path"])
#             pygame.mixer.music.play()
#             self.is_paused = False
#             self.manual_stop = False
#             self.play_pause_btn.configure(text="⏸")

#             self.current_length = song["length"] or 0
#             self.play_start_time = time.time()

#             self._highlight_selected_button()
#             self._update_details_panel(now_playing=True)
#         except Exception as e:
#             messagebox.showerror("Error", f"Failed to play:\n{song['title']}\n\n{e}")

#     def play_pause(self):
#         if not self.songs:
#             return

#         # if already playing and not paused → pause
#         if pygame.mixer.music.get_busy() and not self.is_paused:
#             pygame.mixer.music.pause()
#             self.is_paused = True
#             self.play_pause_btn.configure(text="▶")
#             return

#         # if paused → resume
#         if self.is_paused:
#             pygame.mixer.music.unpause()
#             self.is_paused = False
#             self.play_pause_btn.configure(text="⏸")
#             return

#         # if nothing is playing → play current or first
#         if self.current_index is None:
#             self.current_index = 0
#         self._play_song_at_index(self.current_index)

#     def play_next(self):
#         if not self.songs:
#             return
#         if self.current_index is None:
#             self.current_index = 0
#         else:
#             self.current_index = (self.current_index + 1) % len(self.songs)
#         self._play_song_at_index(self.current_index)

#     def play_previous(self):
#         if not self.songs:
#             return
#         if self.current_index is None:
#             self.current_index = 0
#         else:
#             self.current_index = (self.current_index - 1) % len(self.songs)
#         self._play_song_at_index(self.current_index)

#     def stop(self):
#         self.manual_stop = True
#         pygame.mixer.music.stop()
#         self.is_paused = False
#         self.play_pause_btn.configure(text="▶")
#         self.progress_slider.set(0)
#         self.time_label.configure(text="00:00 / 00:00")

#     def toggle_mute(self):
#         if self.is_muted:
#             vol = self.volume_slider.get() / 100.0
#             pygame.mixer.music.set_volume(vol)
#             self.is_muted = False
#             self.mute_btn.configure(text="🔊")
#         else:
#             pygame.mixer.music.set_volume(0.0)
#             self.is_muted = True
#             self.mute_btn.configure(text="🔇")

#     def on_volume_change(self, value):
#         if not self.is_muted:
#             vol = float(value) / 100.0
#             pygame.mixer.music.set_volume(vol)

#     # ---------------- PROGRESS & AUTO-NEXT ----------------

#     def _schedule_progress_update(self):
#         self._update_progress()
#         self.after(500, self._schedule_progress_update)

#     def _update_progress(self):
#         if not self.songs or self.current_index is None:
#             return

#         # Auto-next logic
#         if not self.is_paused and not pygame.mixer.music.get_busy():
#             if self.manual_stop:
#                 # manual stop: do nothing
#                 self.manual_stop = False
#                 return

#             if self.play_start_time and (time.time() - self.play_start_time) > 1.0:
#                 if self.auto_next_enabled:
#                     self.play_next()
#             return

#         # Progress bar and time
#         pos_ms = pygame.mixer.music.get_pos()
#         if pos_ms < 0:
#             pos_ms = 0
#         current_sec = pos_ms // 1000
#         total_sec = int(self.current_length)

#         if total_sec > 0:
#             progress = (current_sec / total_sec) * 100
#             self.progress_slider.set(progress)
#             self.time_label.configure(
#                 text=f"{self._format_time(current_sec)} / {self._format_time(total_sec)}"
#             )
#         else:
#             self.progress_slider.set(0)
#             self.time_label.configure(
#                 text=f"{self._format_time(current_sec)} / 00:00"
#             )


# if __name__ == "__main__":
#     app = MusicPlayerApp()
#     app.mainloop()

