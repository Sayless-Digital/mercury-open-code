# Install Non-Flatpak VSCode on Zorin OS

## Method 1: Using Microsoft's Official Repository (Recommended)

1. **Import Microsoft's GPG key:**
```bash
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
sudo install -D -o root -g root -m 644 packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg
sudo sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
rm -f packages.microsoft.gpg
```

2. **Update package list and install:**
```bash
sudo apt update
sudo apt install code
```

3. **Launch VSCode:**
```bash
code
```

## Method 2: Download .deb Package Directly

1. **Download the .deb package:**
   Visit: https://code.visualstudio.com/Download
   Download the `.deb` package for Linux

2. **Install using dpkg:**
```bash
cd ~/Downloads
sudo dpkg -i code_*.deb
sudo apt-get install -f  # Fix any dependency issues
```

## After Installation

1. **Remove Flatpak version (optional):**
```bash
flatpak uninstall com.visualstudio.code
```

2. **Verify installation:**
```bash
which code
# Should show: /usr/bin/code (not in /app/bin)
```

3. **Test that npm works in terminal:**
```bash
code ~/Documents/Projects/Mercury\ Coder
# Open terminal in VSCode and test:
npm --version
```

## Benefits of Non-Flatpak Version
- Full access to system PATH (nvm, npm, etc.)
- Better integration with system tools
- No sandboxing issues
- Faster startup time