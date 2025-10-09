# Maintainer: radnus <radnus@gmail.com>
pkgname=tamil-assistant
pkgver=1.0.0
pkgrel=1
pkgdesc="AI-powered Tamil language learning companion for i3 window manager"
arch=('any')
url="https://github.com/jalabulajunx/tamil-assistant"
license=('MIT')
depends=(
    'python>=3.8'
    'python-requests>=2.31.0'
    'python-pillow>=10.0.0'
    'python-pdf2image>=1.16.0'
    'python-dbus>=1.3.2'
    'python-gobject>=3.42.0'
    'okular'
    'i3-wm'
    'poppler'
    'gtk3'
)
makedepends=('git')
optdepends=(
    'rofi: For application launcher integration'
    'dmenu: Alternative application launcher'
)
source=("$pkgname-$pkgver.tar.gz::https://github.com/jalabulajunx/tamil-assistant/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')  # Replace with actual checksum when uploading
install=tamil-assistant.install

package() {
    cd "$pkgname-$pkgver"
    
    # Install main executable
    install -Dm755 tamil_sidepanel.py "$pkgdir/usr/bin/tamil-assistant"
    
    # Install Python modules as a proper package
    install -dm755 "$pkgdir/usr/lib/python3.11/site-packages/tamil_assistant"
    install -Dm644 gemini_client.py "$pkgdir/usr/lib/python3.11/site-packages/tamil_assistant/"
    install -Dm644 okular_interface.py "$pkgdir/usr/lib/python3.11/site-packages/tamil_assistant/"
    install -Dm644 config_manager.py "$pkgdir/usr/lib/python3.11/site-packages/tamil_assistant/"
    
    # Create __init__.py for proper Python package
    touch "$pkgdir/usr/lib/python3.11/site-packages/tamil_assistant/__init__.py"
    
    # Install configuration template
    install -Dm644 config.ini.example "$pkgdir/etc/tamil-assistant/config.ini.example"
    
    # Install desktop file
    install -Dm644 tamil-assistant.desktop "$pkgdir/usr/share/applications/tamil-assistant.desktop"
    
    # Install documentation
    install -Dm644 readme.md "$pkgdir/usr/share/doc/tamil-assistant/README.md"
    
    # Install launcher script
    install -Dm755 launch_tamil.sh "$pkgdir/usr/bin/tamil-assistant-launcher"
    
    # Install package files
    install -Dm644 requirements.txt "$pkgdir/usr/share/tamil-assistant/requirements.txt"
    
    # Install prompt templates
    install -dm755 "$pkgdir/usr/share/tamil-assistant/prompts"
    install -Dm644 prompts/page_analysis.txt "$pkgdir/usr/share/tamil-assistant/prompts/"
    install -Dm644 prompts/word_lookup.txt "$pkgdir/usr/share/tamil-assistant/prompts/"
    
    # Create logs directory
    install -dm755 "$pkgdir/var/log/tamil-assistant"
    
    # Install post-install script
    install -Dm755 tamil-assistant-postinstall.sh "$pkgdir/usr/share/tamil-assistant/postinstall.sh"
}
