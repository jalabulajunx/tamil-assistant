#!/bin/bash

echo "==================================="
echo "Tamil Assistant Setup"
echo "==================================="
echo ""

# Check if config.ini exists
if [ ! -f "config.ini" ]; then
    echo "⚠️  config.ini not found!"
    echo ""

    if [ -f "config.ini.example" ]; then
        echo "Creating config.ini from example..."
        cp config.ini.example config.ini
        echo "✓ Created config.ini"
    else
        echo "Creating config.ini..."
        cat > config.ini << 'EOF'
[gemini]
api_key =
model = gemini-2.0-flash-exp

[ui]
window_width = 400
window_height = 900
font_tamil = Noto Sans Tamil
font_size = 11

[okular]
dbus_service_pattern = org.kde.okular-*
dbus_path = /okular
EOF
        echo "✓ Created config.ini"
    fi

    echo ""
    echo "📝 Please edit config.ini and add your Gemini API key"
    echo "   Get your key from: https://aistudio.google.com/apikey"
    echo ""
    read -p "Press Enter to open config.ini in nano..."
    nano config.ini
fi

# Check if API key is set
if grep -q "^api_key = $" config.ini || grep -q "^api_key = YOUR_" config.ini; then
    echo ""
    echo "⚠️  API key not set in config.ini"
    echo ""
    read -p "Enter your Gemini API key: " api_key

    if [ -n "$api_key" ]; then
        sed -i "s/^api_key = .*/api_key = $api_key/" config.ini
        echo "✓ API key saved to config.ini"
    fi
fi

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install --user -r requirements.txt

# Install system packages
echo ""
echo "Checking system dependencies..."
packages="python-gobject gtk3 poppler python-cairo xclip"
for pkg in $packages; do
    if ! pacman -Q $pkg &> /dev/null; then
        echo "Installing $pkg..."
        sudo pacman -S --noconfirm $pkg
    fi
done

# Make scripts executable
chmod +x *.py

echo ""
echo "==================================="
echo "✅ Setup Complete!"
echo "==================================="
echo ""
echo "Configuration file: $(pwd)/config.ini"
echo ""
echo "Next steps:"
echo "1. Test the configuration:"
echo "   python3 test_gemini.py"
echo ""
echo "2. Add i3 config (see README.md)"
echo ""
echo "3. Reload i3: Mod+Shift+R"
echo ""
echo "4. Press Mod+T to toggle Tamil Assistant"
echo ""
