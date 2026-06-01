#!/usr/bin/env bash
# Mega Clock Deployment Script for rodep-lore

set -e

echo "🚀 Starting Mega Clock deployment..."

# 1. Install Dependencies
echo "📦 Installing system dependencies..."
sudo apt update || echo "⚠️ Warning: apt update had some issues, but continuing..."
sudo apt install -y python3-pyqt5 fonts-manrope fonts-inter fonts-montserrat

# 2. Setup GNOME Desktop Entry
echo "🖥️ Setting up GNOME Desktop entry..."
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/mega-clock.desktop" <<EOF
[Desktop Entry]
Name=Mega Clock
Comment=A high-fashion massive digital clock
Exec=python3 $HOME/rodep-lore/scripts/clock/fashion_clock.py
Icon=preferences-system-time
Terminal=false
Type=Application
Categories=Utility;Clock;
Keywords=Clock;Time;Big;Fashion;
StartupNotify=true
EOF

chmod +x "$DESKTOP_DIR/mega-clock.desktop"
update-desktop-database "$DESKTOP_DIR"

# 3. Setup Systemd User Service
echo "⚙️ Configuring systemd user service..."
SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_DIR"

cat > "$SYSTEMD_DIR/mega-clock.service" <<EOF
[Unit]
Description=Mega Clock Service
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $HOME/rodep-lore/scripts/clock/fashion_clock.py
Restart=always
RestartSec=5
Environment=DISPLAY=:0
Environment=WAYLAND_DISPLAY=wayland-0
Environment=XDG_RUNTIME_DIR=/run/user/$(id -u)

[Install]
WantedBy=default.target
EOF

# 4. Enable and Start
echo "🔄 Initializing service..."
systemctl --user daemon-reload
systemctl --user enable mega-clock.service
systemctl --user restart mega-clock.service

echo "✅ Mega Clock deployment complete!"
echo "💡 You can now find 'Mega Clock' in your GNOME apps or move it to your secondary monitor with Super+Shift+Right."
