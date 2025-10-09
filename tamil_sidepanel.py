#!/usr/bin/env python3
"""
Tamil Learning Assistant - i3 Scratchpad Panel
Integrates with Okular and Google Gemini
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango
import sys
import signal
import logging
import os
import argparse
import shutil
from datetime import datetime
from pathlib import Path

from config_manager import get_config
from okular_interface import OkularInterface
from gemini_client import GeminiClient, TamilWord

class TamilSidePanel(Gtk.Window):
    def __init__(self):
        super().__init__(title="Tamil Assistant")

        # Setup logging
        self.setup_logging()

        # Load configuration
        try:
            self.config = get_config()
            self.logger.info("Configuration loaded successfully")
            self.logger.info(f"Config summary: {self.config}")
        except Exception as e:
            self.logger.error(f"Configuration error: {e}")
            self.show_error_dialog(
                "Configuration Error",
                str(e)
            )
            sys.exit(1)

        # Initialize interfaces
        self.okular = OkularInterface()
        self.gemini = GeminiClient()  # Now reads from config automatically

        # State
        self.current_words = []
        self.current_page_image = None
        self.current_file_name = None
        self.current_page_number = None

        # Setup window
        self.setup_window()
        self.setup_ui()
        self.setup_styling()

    def setup_logging(self):
        """Setup logging with datetime-based file splitting"""
        # Create logs directory if it doesn't exist
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Create session-specific log file
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"tamil_assistant_{session_timestamp}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)  # Also log to console
            ]
        )
        
        self.logger = logging.getLogger('TamilAssistant')
        self.logger.info(f"Logging started - Session: {session_timestamp}")
        self.logger.info(f"Log file: {log_file}")

    def show_error_dialog(self, title, message):
        """Show error dialog"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def setup_window(self):
        """Configure window properties"""
        self.set_default_size(
            self.config.get_window_width(),
            self.config.get_window_height()
        )
        # Use NORMAL type hint to avoid conflicts with other applications
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.set_keep_above(False)
        self.stick()  # Follow across workspaces
        self.set_skip_taskbar_hint(True)
        
        # Set a unique window class to avoid conflicts
        self.set_wmclass("tamil-assistant", "TamilAssistant")

        # Handle close button
        self.connect("delete-event", self.on_close)

    def setup_ui(self):
        """Build the user interface"""
        # Main vertical box
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)

        # Header
        header = Gtk.Label()
        header.set_markup("<big><b>🇮🇳 Tamil Assistant</b></big>")
        header.set_halign(Gtk.Align.CENTER)
        vbox.pack_start(header, False, False, 0)

        # Info label
        info = Gtk.Label()
        info.set_markup("<small>Powered by Google Gemini</small>")
        info.set_halign(Gtk.Align.CENTER)
        vbox.pack_start(info, False, False, 0)

        # Context label (file name and page)
        self.context_label = Gtk.Label()
        self.context_label.set_markup("<small><i>No document loaded</i></small>")
        self.context_label.set_halign(Gtk.Align.CENTER)
        self.context_label.set_margin_top(5)
        vbox.pack_start(self.context_label, False, False, 0)

        vbox.pack_start(Gtk.Separator(), False, False, 5)

        # Button box
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.analyze_btn = Gtk.Button(label="📄 Analyze Page")
        self.analyze_btn.set_tooltip_text("Analyze current page in Okular")
        self.lookup_btn = Gtk.Button(label="🔍 Lookup Selected")
        self.lookup_btn.set_tooltip_text("Lookup selected text (select in Okular first)")

        btn_box.pack_start(self.analyze_btn, True, True, 0)
        btn_box.pack_start(self.lookup_btn, True, True, 0)
        vbox.pack_start(btn_box, False, False, 0)

        # Status label with spinner
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.spinner = Gtk.Spinner()
        self.status = Gtk.Label(label="Ready")
        self.status.set_halign(Gtk.Align.START)
        status_box.pack_start(self.spinner, False, False, 0)
        status_box.pack_start(self.status, True, True, 0)
        vbox.pack_start(status_box, False, False, 0)

        vbox.pack_start(Gtk.Separator(), False, False, 5)

        # Word list (scrollable)
        list_label = Gtk.Label()
        list_label.set_markup("<b>Words Found:</b>")
        list_label.set_halign(Gtk.Align.START)
        vbox.pack_start(list_label, False, False, 0)

        scrolled_list = Gtk.ScrolledWindow()
        scrolled_list.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_list.set_min_content_height(300)

        self.word_listbox = Gtk.ListBox()
        self.word_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scrolled_list.add(self.word_listbox)

        vbox.pack_start(scrolled_list, True, True, 0)

        # Detail view
        detail_label = Gtk.Label()
        detail_label.set_markup("<b>Details:</b>")
        detail_label.set_halign(Gtk.Align.START)
        vbox.pack_start(detail_label, False, False, 0)

        detail_frame = Gtk.Frame()
        detail_scrolled = Gtk.ScrolledWindow()
        detail_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        detail_scrolled.set_min_content_height(200)

        self.detail_view = Gtk.Label()
        self.detail_view.set_line_wrap(True)
        self.detail_view.set_line_wrap_mode(Pango.WrapMode.WORD)
        self.detail_view.set_halign(Gtk.Align.START)
        self.detail_view.set_valign(Gtk.Align.START)
        self.detail_view.set_margin_start(10)
        self.detail_view.set_margin_end(10)
        self.detail_view.set_margin_top(10)
        self.detail_view.set_margin_bottom(10)
        self.detail_view.set_selectable(True)  # Allow text selection

        detail_scrolled.add(self.detail_view)
        detail_frame.add(detail_scrolled)
        vbox.pack_start(detail_frame, False, True, 0)

        self.add(vbox)

        # Connect signals
        self.analyze_btn.connect("clicked", self.on_analyze_clicked)
        self.lookup_btn.connect("clicked", self.on_lookup_clicked)
        self.word_listbox.connect("row-selected", self.on_word_selected)
        self.detail_view.connect("activate-link", self._on_detail_activate_link)

    def setup_styling(self):
        """Apply CSS styling"""
        font_size = self.config.get_font_size()
        tamil_font = self.config.get_tamil_font()

        css = f"""
        window {{
            background-color: #f5f5f5;
        }}

        label {{
            font-size: {font_size}pt;
        }}

        .tamil {{
            font-family: '{tamil_font}';
            font-size: {font_size + 3}pt;
        }}

        button {{
            padding: 8px;
        }}

        list row {{
            padding: 8px;
        }}

        list row:selected {{
            background-color: #4CAF50;
        }}
        """

        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode())

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def set_status(self, message, is_loading=False):
        """Update status label"""
        self.status.set_text(message)
        if is_loading:
            self.spinner.start()
        else:
            self.spinner.stop()

    def on_analyze_clicked(self, button):
        """Analyze current page in Okular"""
        self.set_status("Getting current page...", True)
        self.analyze_btn.set_sensitive(False)

        # Run in background thread
        GLib.idle_add(self._do_analyze)

    def _do_analyze(self):
        """Background task: analyze page"""
        try:
            # Get current page from Okular
            page_num = self.okular.get_current_page()
            pdf_path = self.okular.get_current_document()
            
            # Extract file name for logging and display
            self.current_file_name = os.path.basename(pdf_path)
            self.current_page_number = page_num  # Convert to 1-indexed for display
            
            self.logger.info(f"Starting page analysis - File: {self.current_file_name}, Page: {self.current_page_number}")
            self.logger.info(f"Full PDF path: {pdf_path}")

            self.set_status(f"Rendering page {self.current_page_number}...", True)

            # Render page to image
            self.current_page_image = self.okular.render_page_to_image(pdf_path, page_num)
            self.logger.info("Page rendered to image successfully")

            self.set_status("Analyzing with Gemini...", True)

            # Send to Gemini and log token usage
            words, tokens_sent, tokens_received = self.gemini.analyze_page(self.current_page_image)
            
            self.logger.info(f"Gemini analysis complete - Tokens sent: {tokens_sent}, Tokens received: {tokens_received}")
            self.logger.info(f"Found {len(words)} Tamil words on page {self.current_page_number}")

            self.current_words = words

            # Update UI
            GLib.idle_add(self._update_word_list, words)
            GLib.idle_add(self._update_context_display)

            self.set_status(f"✅ Found {len(words)} words")

        except Exception as e:
            self.logger.error(f"Analysis error: {e}")
            self.set_status(f"❌ Error: {str(e)}")
        finally:
            self.analyze_btn.set_sensitive(True)

        return False  # Don't repeat

    def _update_word_list(self, words):
        """Update word list in UI"""
        # Clear existing
        for child in self.word_listbox.get_children():
            self.word_listbox.remove(child)

        # Separate regular words from poem summary
        regular_words = []
        poem_summary = None
        
        for word in words:
            if word.tamil_word == "POEM_SUMMARY":
                poem_summary = word
            else:
                regular_words.append(word)

        # Add regular words first
        for word in regular_words:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            box.set_margin_start(5)
            box.set_margin_end(5)
            box.set_margin_top(3)
            box.set_margin_bottom(3)

            # Tamil word
            tamil_label = Gtk.Label()
            tamil_label.set_markup(f"<span font_family='{self.config.get_tamil_font()}' size='large'><b>{word.tamil_word}</b></span>")
            tamil_label.set_halign(Gtk.Align.START)

            # Literal translation
            literal_label = Gtk.Label()
            literal_label.set_markup(f"<small>{word.literal_translation}</small>")
            literal_label.set_halign(Gtk.Align.START)
            literal_label.set_line_wrap(True)

            box.pack_start(tamil_label, False, False, 0)
            box.pack_start(literal_label, False, False, 0)

            row.add(box)
            row.word_data = word  # Store word data

            self.word_listbox.add(row)

        # Add poem summary if present
        if poem_summary:
            # Add separator
            separator = Gtk.Separator()
            self.word_listbox.add(separator)
            
            # Add poem summary with special styling
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            box.set_margin_start(8)
            box.set_margin_end(8)
            box.set_margin_top(8)
            box.set_margin_bottom(8)

            # Poem summary title
            title_label = Gtk.Label()
            title_label.set_markup("<b>📖 Page Summary</b>")
            title_label.set_halign(Gtk.Align.START)

            # Poem summary content
            summary_label = Gtk.Label()
            summary_label.set_markup(f"<small>{poem_summary.contextual_meaning}</small>")
            summary_label.set_halign(Gtk.Align.START)
            summary_label.set_line_wrap(True)
            summary_label.set_selectable(True)

            box.pack_start(title_label, False, False, 0)
            box.pack_start(summary_label, False, False, 0)

            row.add(box)
            row.word_data = poem_summary  # Store word data

            self.word_listbox.add(row)

        self.word_listbox.show_all()
        return False

    def _update_context_display(self):
        """Update the context display with file name and page number"""
        if self.current_file_name and self.current_page_number:
            context_text = f"📄 {self.current_file_name} - Page {self.current_page_number}"
            self.context_label.set_markup(f"<small><i>{context_text}</i></small>")
        else:
            self.context_label.set_markup("<small><i>No document loaded</i></small>")
        return False

    def on_lookup_clicked(self, button):
        """Lookup selected text"""
        self.set_status("Getting selected text...", True)
        self.lookup_btn.set_sensitive(False)

        GLib.idle_add(self._do_lookup)

    def _do_lookup(self):
        """Background task: lookup word"""
        try:
            # Get selected text
            selected_text = self.okular.get_selected_text()

            if not selected_text:
                self.logger.warning("No text selected in Okular for lookup")
                self.set_status("⚠️ No text selected in Okular")
                self.lookup_btn.set_sensitive(True)
                return False

            self.logger.info(f"Starting word lookup - Selected text: '{selected_text}'")
            self.set_status(f"Looking up: {selected_text}", True)

            # Get context if we don't have current page image
            if not self.current_page_image:
                page_num = self.okular.get_current_page()
                pdf_path = self.okular.get_current_document()
                self.current_page_image = self.okular.render_page_to_image(pdf_path, page_num)
                self.logger.info("Rendered page image for lookup context")

            # Send to Gemini and log token usage
            word, tokens_sent, tokens_received = self.gemini.lookup_word(selected_text, self.current_page_image)
            
            self.logger.info(f"Word lookup complete - Tokens sent: {tokens_sent}, Tokens received: {tokens_received}")

            if word:
                self.logger.info(f"Found word: {word.tamil_word} - {word.literal_translation}")
                GLib.idle_add(self._show_word_detail, word)
                self.set_status("✅ Lookup complete")
            else:
                self.logger.warning(f"No results found for: {selected_text}")
                self.set_status("❌ No results")

        except Exception as e:
            self.logger.error(f"Lookup error: {e}")
            self.set_status(f"❌ Error: {str(e)}")
        finally:
            self.lookup_btn.set_sensitive(True)

        return False

    def on_word_selected(self, listbox, row):
        """Word selected from list"""
        if row and hasattr(row, 'word_data'):
            self._show_word_detail(row.word_data)

    def _show_word_detail(self, word):
        """Display word details"""
        tamil_font = self.config.get_tamil_font()
        
        # Make URLs clickable
        contextual_meaning = self._make_urls_clickable(word.contextual_meaning)
        
        # Debug logging
        self.logger.info(f"Showing word detail for: {word.tamil_word}")
        self.logger.info(f"Original contextual meaning: {word.contextual_meaning}")
        self.logger.info(f"Processed contextual meaning: {contextual_meaning}")

        detail_html = f"""<span font_family='{tamil_font}' size='xx-large'><b>{word.tamil_word}</b></span>

<b>Literal Translation:</b>
<span foreground='#e74c3c'>{word.literal_translation}</span>

<b>Contextual Meaning:</b>
<span foreground='#3498db'>{contextual_meaning}</span>

<b>Sentence Context:</b>
<span style='italic' foreground='#7f8c8d'>{word.sentence_context}</span>"""

        self.detail_view.set_markup(detail_html)
        return False
    
    def _make_urls_clickable(self, text):
        """Convert URLs in text to clickable HTML links"""
        import re
        
        if not text:
            return text
        
        # Pattern to match Wikipedia URLs (excluding trailing punctuation)
        url_pattern = r'(https://en\.wikipedia\.org/wiki/[^\s<>".!?,:;]+)'
        
        def replace_url(match):
            url = match.group(1)
            # Make it a simple clickable link with proper formatting
            return f'<a href="{url}">{url}</a>'
        
        try:
            return re.sub(url_pattern, replace_url, text)
        except Exception as e:
            self.logger.error(f"Error processing URLs: {e}")
            return text
    
    def _open_url(self, url):
        """Open URL in default browser"""
        import webbrowser
        try:
            webbrowser.open(url)
            self.logger.info(f"Opened URL: {url}")
        except Exception as e:
            self.logger.error(f"Failed to open URL {url}: {e}")
            self.set_status(f"❌ Failed to open URL")
    
    def _on_detail_activate_link(self, label, uri):
        """Handle link clicks in detail view"""
        if uri:
            self._open_url(uri)
        return True

    def on_close(self, widget, event):
        """Handle window close - hide instead of quit"""
        self.hide()
        return True  # Prevent actual close

def setup_user_config():
    """Set up user configuration files"""
    print("🔧 Setting up Tamil Assistant for current user...")
    
    # Get user home directory
    user_home = Path.home()
    user_config_dir = user_home / ".config" / "tamil-assistant"
    user_prompts_dir = user_config_dir / "prompts"
    user_log_dir = user_home / ".local" / "share" / "tamil-assistant" / "logs"
    
    # Create directories
    user_config_dir.mkdir(parents=True, exist_ok=True)
    user_prompts_dir.mkdir(parents=True, exist_ok=True)
    user_log_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy default config if it doesn't exist
    config_file = user_config_dir / "config.ini"
    if not config_file.exists():
        print("📝 Creating user configuration...")
        shutil.copy("/etc/tamil-assistant/config.ini.example", config_file)
        print(f"✅ Configuration created at {config_file}")
        print("⚠️  Please edit this file and add your Google Gemini API key!")
        print("   Get your API key from: https://aistudio.google.com/apikey")
    else:
        print(f"ℹ️  User configuration already exists at {config_file}")
    
    # Copy prompt templates if they don't exist
    if not any(user_prompts_dir.iterdir()):
        print("📝 Creating user prompt templates...")
        shutil.copytree("/usr/share/tamil-assistant/prompts", user_prompts_dir, dirs_exist_ok=True)
        print(f"✅ Prompt templates created at {user_prompts_dir}")
        print("ℹ️  You can customize these prompts for your specific needs")
    else:
        print(f"ℹ️  User prompt templates already exist at {user_prompts_dir}")
    
    print(f"📁 Logs directory created at {user_log_dir}")
    
    # Check i3 config
    i3_config = user_home / ".config" / "i3" / "config"
    if i3_config.exists():
        print("🔍 Checking i3 configuration...")
        with open(i3_config, 'r') as f:
            content = f.read()
            if "tamil-assistant" in content:
                print("ℹ️  Tamil Assistant bindings already exist in i3 config")
            else:
                print("⚠️  Tamil Assistant bindings not found in i3 config")
                print("📋 Add these lines to your ~/.config/i3/config:")
                print("")
                print("# Tamil Assistant")
                print("bindsym $mod+y exec tamil-assistant-launcher")
                print("for_window [class=\"TamilAssistant\"] move scratchpad")
                print("for_window [class=\"TamilAssistant\"] resize set 400 900")
                print("for_window [class=\"TamilAssistant\"] floating enable")
                print("for_window [class=\"TamilAssistant\"] move position 1520 0")
                print("")
                print("Then reload i3 with: i3-msg reload")
    else:
        print(f"⚠️  i3 config not found at {i3_config}")
        print("📋 Create ~/.config/i3/config and add the Tamil Assistant bindings")
    
    print("")
    print("🎉 Tamil Assistant setup complete!")
    print("")
    print("📖 Next steps:")
    print(f"1. Edit {config_file} and add your Google Gemini API key")
    print("2. Add the i3 bindings to your ~/.config/i3/config (see above)")
    print("3. Reload i3: i3-msg reload")
    print("4. Launch Tamil Assistant with Mod+Y")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Tamil Learning Assistant')
    parser.add_argument('--setup', action='store_true', 
                       help='Set up user configuration files')
    args = parser.parse_args()
    
    if args.setup:
        setup_user_config()
        return
    
    # Allow Ctrl+C to quit
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = TamilSidePanel()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()

    Gtk.main()

if __name__ == '__main__':
    main()
