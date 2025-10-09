# AUR Submission Guide for Tamil Assistant

This guide walks you through submitting the Tamil Assistant to the Arch User Repository (AUR), following the [AUR submission guidelines](https://wiki.archlinux.org/title/AUR_submission_guidelines).

## 📋 Pre-Submission Checklist

### ✅ Package Compliance
- [x] **Unique Package**: Tamil Assistant doesn't exist in official repos or AUR
- [x] **Useful Package**: Educational tool for Tamil language learning
- [x] **Architecture Support**: Supports `x86_64` architecture (`arch=('any')`)
- [x] **License Compliance**: Includes 0BSD LICENSE file and REUSE.toml
- [x] **Maintainer Info**: Proper maintainer comment in PKGBUILD
- [x] **Python Package Structure**: Proper site-packages installation

### ✅ Required Files
- [x] `PKGBUILD` - Package build script
- [x] `.SRCINFO` - Package metadata
- [x] `LICENSE` - 0BSD license file
- [x] `REUSE.toml` - License compliance metadata
- [x] `tamil-assistant-postinstall.sh` - Post-installation setup script

## 🚀 Submission Steps

### 1. Create AUR Account
1. Visit [AUR website](https://aur.archlinux.org/)
2. Register for an account
3. Verify your email address

### 2. Set Up SSH Authentication
```bash
# Generate SSH key pair for AUR
ssh-keygen -f ~/.ssh/aur -t ed25519 -C "your-email@example.com"

# IMPORTANT: Add the PUBLIC key to your AUR account
# 1. Copy the content of ~/.ssh/aur.pub
cat ~/.ssh/aur.pub

# 2. Go to https://aur.archlinux.org/account/
# 3. Paste the public key content into "SSH Public Key" field
# 4. Save your profile

# Configure SSH client for aur.archlinux.org host

# For Bash/Zsh:
cat >> ~/.ssh/config << EOF
Host aur.archlinux.org
    IdentityFile ~/.ssh/aur
    User aur
EOF

# For Fish shell:
echo "Host aur.archlinux.org
    IdentityFile ~/.ssh/aur
    User aur" >> ~/.ssh/config

# Test SSH connection to AUR
ssh -T aur@aur.archlinux.org
# Should return: "Hi username! You've successfully authenticated with the key ..."
```

### 3. Test Package Build
```bash
# Test the package build locally
makepkg -s --noconfirm

# Test installation in a clean environment
makepkg -i --noconfirm
```

### 4. Create AUR Repository
```bash
# Clone the AUR repository (will be empty initially)
git clone ssh://aur@aur.archlinux.org/tamil-assistant.git
cd tamil-assistant

# Copy package files from your project
cp /home/radnus/Projects/tamil-assistant/PKGBUILD .
cp /home/radnus/Projects/tamil-assistant/.SRCINFO .
cp /home/radnus/Projects/tamil-assistant/LICENSE .
cp /home/radnus/Projects/tamil-assistant/tamil-assistant.install .
cp /home/radnus/Projects/tamil-assistant/tamil-assistant-postinstall.sh .
cp /home/radnus/Projects/tamil-assistant/tamil-assistant.desktop .
cp /home/radnus/Projects/tamil-assistant/readme.md .

# Add and commit files
git add .
git commit -m "Initial package submission"
git push origin master
```

### 5. Verify AUR Submission
```bash
# Check if package appears on AUR
# Visit: https://aur.archlinux.org/packages/tamil-assistant

# Test installation from AUR
yay -S tamil-assistant
# or
paru -S tamil-assistant
```

### 6. Update Package (Future Releases)
```bash
# When you have a new version:

# 1. Update PKGBUILD in your main project
# Edit PKGBUILD: change pkgver=1.0.0 to pkgver=1.0.1
# Update .SRCINFO: makepkg --printsrcinfo > .SRCINFO

# 2. Update AUR repository
cd ~/tamil-assistant  # Your AUR repo
git pull origin master

# 3. Copy updated files
cp /home/radnus/Projects/tamil-assistant/PKGBUILD .
cp /home/radnus/Projects/tamil-assistant/.SRCINFO .

# 4. Commit and push
git add PKGBUILD .SRCINFO
git commit -m "Update to v1.0.1"
git push origin master
```

## 📋 **Complete Step-by-Step Submission Process**

### **Step 1: Prepare Your Package**
```bash
# Ensure all files are ready
cd /home/radnus/Projects/tamil-assistant

# Update PKGBUILD version if needed
# Edit PKGBUILD: pkgver=1.0.1

# Generate .SRCINFO
makepkg --printsrcinfo > .SRCINFO

# Test build
makepkg -s --noconfirm
```

### **Step 2: Create AUR Repository**
```bash
# Clone empty AUR repository
git clone ssh://aur@aur.archlinux.org/tamil-assistant.git
cd tamil-assistant

# Copy all required files
cp /home/radnus/Projects/tamil-assistant/PKGBUILD .
cp /home/radnus/Projects/tamil-assistant/.SRCINFO .
cp /home/radnus/Projects/tamil-assistant/LICENSE .
cp /home/radnus/Projects/tamil-assistant/tamil-assistant.install .
cp /home/radnus/Projects/tamil-assistant/tamil-assistant-postinstall.sh .
cp /home/radnus/Projects/tamil-assistant/tamil-assistant.desktop .
cp /home/radnus/Projects/tamil-assistant/readme.md .
cp /home/radnus/Projects/tamil-assistant/REUSE.toml .
```

### **Step 3: Submit to AUR**
```bash
# Add all files
git add .

# Commit with descriptive message
git commit -m "Initial package submission for Tamil Assistant v1.0.1

- AI-powered Tamil language learning companion
- i3 window manager integration
- Configurable prompts and comprehensive logging
- AUR package ready"

# Push to AUR
git push origin master
```

### **Step 4: Verify Submission**
```bash
# Check AUR website
# Visit: https://aur.archlinux.org/packages/tamil-assistant

# Test installation
yay -S tamil-assistant
# or
paru -S tamil-assistant
```

### **Step 5: Test Installation**
```bash
# Install the package
sudo pacman -S tamil-assistant

# Verify installation
which tamil-assistant
ls -la /usr/bin/tamil-assistant*

# Set up user configuration (IMPORTANT!)
tamil-assistant --setup

# Test the application
tamil-assistant --help
```

## 🔄 **Updating Your Package**

When you release a new version:

### **Method 1: Manual Update**
```bash
# 1. Update main project
cd /home/radnus/Projects/tamil-assistant
# Edit PKGBUILD: pkgver=1.0.2
makepkg --printsrcinfo > .SRCINFO

# 2. Update AUR
cd ~/tamil-assistant
git pull origin master
cp /home/radnus/Projects/tamil-assistant/PKGBUILD .
cp /home/radnus/Projects/tamil-assistant/.SRCINFO .
git add PKGBUILD .SRCINFO
git commit -m "Update to v1.0.2"
git push origin master
```

### **Method 2: Automated Update (Future)**
The GitHub Actions workflow can be configured to automatically update AUR when you create releases.

## 📦 Package Structure

### Files Included
```
tamil-assistant/
├── PKGBUILD                    # Package build script
├── .SRCINFO                   # Package metadata
├── LICENSE                     # 0BSD license
├── REUSE.toml                  # License compliance
├── tamil-assistant.install     # Package install hooks
├── tamil-assistant-postinstall.sh  # Post-install script
└── (source files will be downloaded from GitHub)
```

### Installation Paths
- **Executable**: `/usr/bin/tamil-assistant`
- **Python Modules**: `/usr/lib/python3.11/site-packages/tamil_assistant/`
- **Configuration Template**: `/etc/tamil-assistant/config.ini.example`
- **User Configuration**: `~/.config/tamil-assistant/config.ini` (created on first run)
- **Desktop File**: `/usr/share/applications/tamil-assistant.desktop`
- **Documentation**: `/usr/share/doc/tamil-assistant/`
- **Launcher**: `/usr/bin/tamil-assistant-launcher`
- **Prompt Templates**: `/usr/share/tamil-assistant/prompts/`

## 🔧 Post-Submission Maintenance

### Regular Updates
1. **Monitor Upstream**: Check for new releases
2. **Update PKGBUILD**: Bump `pkgver` and `pkgrel` as needed
3. **Regenerate .SRCINFO**: Run `makepkg --printsrcinfo > .SRCINFO`
4. **Test Build**: Ensure package builds successfully
5. **Commit Changes**: Push updates to AUR

### User Support
1. **Monitor Comments**: Respond to user feedback
2. **Address Issues**: Fix reported bugs promptly
3. **Update Documentation**: Improve README and guides

## 📋 Package Dependencies

### Required Dependencies
- `python>=3.8` - Python runtime
- `python-requests>=2.31.0` - HTTP requests
- `python-pillow>=10.0.0` - Image processing
- `python-pdf2image>=1.16.0` - PDF to image conversion
- `python-dbus>=1.3.2` - D-Bus communication
- `python-gobject>=3.42.0` - GTK3 bindings
- `okular` - PDF viewer
- `i3-wm` - Window manager
- `poppler` - PDF rendering
- `gtk3` - GUI toolkit

### Optional Dependencies
- `rofi` - Application launcher integration
- `dmenu` - Alternative application launcher

## 🎯 Key Features Highlighted

1. **Educational Focus**: Designed for Tamil language learning
2. **i3 Integration**: Seamless window manager integration
3. **Okular Integration**: D-Bus communication with PDF viewer
4. **AI-Powered**: Google Gemini API for contextual translations
5. **Comprehensive Logging**: Session tracking and analytics
6. **Interactive Learning**: Clickable Wikipedia links
7. **Poem Analysis**: Special handling for Tamil poetry

## ⚠️ Important Notes

1. **API Key Required**: Users must configure Google Gemini API key
2. **i3 Configuration**: Manual i3 config setup required
3. **Okular Dependency**: Requires Okular for PDF viewing
4. **Architecture**: Python package supports all architectures (`arch=('any')`)
5. **User Setup**: After installation, users must run `tamil-assistant --setup` to create user configuration files

## 🔗 Related Documentation

- [AUR Submission Guidelines](https://wiki.archlinux.org/title/AUR_submission_guidelines)
- [Arch Package Guidelines](https://wiki.archlinux.org/title/Arch_package_guidelines)
- [Python Package Guidelines](https://wiki.archlinux.org/title/Python_package_guidelines)
- [VCS Package Guidelines](https://wiki.archlinux.org/title/VCS_package_guidelines)

---

**Ready for AUR submission!** 🎉

Follow the steps above to submit Tamil Assistant to the Arch User Repository and make it available to the Arch Linux community.
