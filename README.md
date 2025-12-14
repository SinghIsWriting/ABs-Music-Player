# 🎧 **AB’s Music Player – Desktop Music Player**

A clean, modern, and lightweight music player built with **Python**, **CustomTkinter**, and **Pygame**.
This tool allows users to load music from a folder and play songs with an intuitive GUI, smooth controls, and a stylish dark theme.

---

## 🚀 **Features**

### 🎵 **Music Playback**

* Play, Pause, Resume songs
* Play Next / Previous
* Stop song completely (no auto-next)
* Mute / Unmute
* Adjustable volume slider

### 📂 **Playlist Viewer**

* Automatically fetches all songs from a selected folder
* Displays:

  * Track Number
  * Song Title
  * Duration
* Highlights currently selected song
* Scrollable, modern list view

### 📊 **Song Details Panel**

Shows detailed information such as:

* Now Playing Title
* Track Number
* Duration
* Full File Path
* Playback progress and time indicator

### 🎨 **Modern UI**

* Smooth dark-mode interface
* CustomTkinter-based polished widgets
* Rounded frames, hover effects, and clean layout

---

## 📦 **Download the Installer**

A ready-to-install Windows version is available:

👉 **[Download ABsMusicPlayer](installer/ABsMusicPlayer.exe)**
*(No Python required)*

---

## 🛠️ **Running From Source (For developers Developers)**

### **Clone repository**
```bash
git clone https://github.com/SinghIsWriting/ABs-Music-Player.git
cd ABs-Music-Player
```

### **Requirements**

Install dependencies:

```bash
pip install customtkinter pygame
```

### **Run the app**

```bash
python gui.py
```

---

## 📁 **Project Structure**

```
.
├── gui.py                 # Main Music Player source code
├── assets/
│   └── icon.ico           # Application icon
├── installer/
│   └── ABsMusicPlayer.exe # Pre-built Windows installer
└── README.md              # Project documentation
```

---

## 🧰 **How It Works**

1. Launch the app
2. Click **“Choose Folder”**
3. Select a folder containing `.mp3`, `.wav`, or `.ogg` files
4. Songs appear in the playlist
5. Select any song to play or use the buttons:

   * ▶ Play
   * ⏸ Pause
   * ⏭ Next
   * ⏮ Previous
   * ⏹ Stop
   * 🔊 Mute

Playback progress and song info updates automatically.

---

## 📘 **User Guide**

A complete user guide is included in the installer and accessible after installation.
It explains features, controls, examples, troubleshooting, and best practices.

If you want the User Guide added to the repo, I can create a `/docs` folder with PDF/HTML versions.

---

## 🧩 **Building the EXE (For Developers)**

We used **PyInstaller**:

**Install PyInstaller**
```bash
pip install pyinstaller
```
```bash
pyinstaller --noconsole --onefile --icon=assets/icon.ico gui.py --add-data "assets;assets"
```

Output EXE is then packaged into an installer using **Inno Setup**.

---

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -m 'Add some feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Open a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## **Contact Me**

For any inquiries or support, please reach out to:
- **Name**: Abhishek Singh
- **LinkedIn**: [My LinkedIn Profile](https://www.linkedin.com/in/abhishek-singh-bba2662a9)
- **Portfolio**: [Abhishek Singh](https://portfolio-abhishek-singh-nine.vercel.app/)

---

## ❤️ **Acknowledgements**

* **CustomTkinter** for modern GUI
* **Pygame** for audio playback
* **Python** for making desktop apps simple
* Designed & Developed by **Abhishek Singh (AB)**
