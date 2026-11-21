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
import threading
from datetime import datetime
from pathlib import Path

from tamil_assistant.config_manager import get_config
from tamil_assistant.okular_interface import OkularInterface
from tamil_assistant.gemini_client import GeminiClient, TamilWord
from tamil_assistant.result_cache import ResultCache


def esc(text):
    """Escape model text for Pango markup"""
    return GLib.markup_escape_text(text or "")


SAY_IT_KEY = ("Say-it guide: aa ee oo = long vowels · CAPITALS T D N L = curl your "
              "tongue back · zh = ழ · R = rolled ற · th = soft t")

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
        self.cache = ResultCache()

        # State
        self.current_words = []
        self.current_page_image = None   # rendered lazily; None when the list came from cache
        self.current_pdf_path = None
        self.current_file_name = None
        self.current_page_number = None
        self.current_page_key = None     # cache key for the page being shown
        self.selected_word = None
        self._details_in_flight = set()

        # Setup window
        self.setup_window()
        self.setup_ui()
        self.setup_styling()

    def setup_logging(self):
        """Setup logging with datetime-based file splitting"""
        # Create logs directory in user's home directory if it doesn't exist
        log_dir = Path.home() / ".local" / "share" / "tamil-assistant" / "logs"
        
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Create session-specific log file
            session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"tamil_assistant_{session_timestamp}.log"
            
            # Configure logging with error handling
            handlers = [logging.StreamHandler(sys.stdout)]  # Always log to console
            
            try:
                # Try to add file handler
                file_handler = logging.FileHandler(log_file)
                handlers.append(file_handler)
            except PermissionError:
                # Fallback: try to create log file in /tmp if home directory fails
                try:
                    fallback_log = Path("/tmp") / f"tamil_assistant_{session_timestamp}.log"
                    file_handler = logging.FileHandler(fallback_log)
                    handlers.append(file_handler)
                except Exception:
                    # If all else fails, just use console logging
                    pass
            
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=handlers
            )
            
        except Exception as e:
            # If logging setup fails completely, use basic console logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler(sys.stdout)]
            )
            print(f"Warning: Could not set up file logging: {e}")
        
        self.logger = logging.getLogger('TamilAssistant')
        self.logger.info(f"Logging started - Session: {session_timestamp}")
        if 'log_file' in locals():
            self.logger.info(f"Log file: {log_file}")
        else:
            self.logger.info("Logging to console only")

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

        say_key = Gtk.Label()
        say_key.set_markup(f"<small><i>{esc(SAY_IT_KEY)}</i></small>")
        say_key.set_halign(Gtk.Align.START)
        say_key.set_line_wrap(True)
        say_key.set_xalign(0)
        vbox.pack_start(say_key, False, False, 0)

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
        """Update status label (main thread only; use _status from workers)"""
        self.status.set_text(message)
        if is_loading:
            self.spinner.start()
        else:
            self.spinner.stop()
        return False

    def _status(self, message, is_loading=False):
        """Thread-safe status update"""
        GLib.idle_add(self.set_status, message, is_loading)

    def _run_in_background(self, target, *args):
        """Run blocking work (rendering, Gemini calls) off the UI thread"""
        threading.Thread(target=target, args=args, daemon=True).start()

    def _page_image(self):
        """The current page image, rendering it (just this one page) if needed. Worker thread."""
        if self.current_page_image is None:
            self.current_page_image = self.okular.render_page_to_image(
                self.current_pdf_path, self.current_page_number)
            self.logger.info("Rendered page image")
        return self.current_page_image

    def _set_current_page(self, pdf_path, page_num):
        """Remember which page is shown; drop the old page image if it changed"""
        if (pdf_path, page_num) != (self.current_pdf_path, self.current_page_number):
            self.current_page_image = None
        self.current_pdf_path = pdf_path
        self.current_file_name = os.path.basename(pdf_path)
        self.current_page_number = page_num
        self.current_page_key = self.cache.page_key(
            pdf_path, page_num, self.gemini.model, self.config.get_page_analysis_prompt())

    def on_analyze_clicked(self, button):
        """Analyze current page in Okular"""
        self.set_status("Getting current page...", True)
        self.analyze_btn.set_sensitive(False)
        try:
            # D-Bus calls to Okular stay on the main thread
            page_num = self.okular.get_current_page()
            pdf_path = self.okular.get_current_document()
            self._set_current_page(pdf_path, page_num)
        except Exception as e:
            self.logger.error(f"Analysis error: {e}")
            self.set_status(f"❌ Error: {e}")
            self.analyze_btn.set_sensitive(True)
            return
        self._run_in_background(self._do_analyze)

    def _do_analyze(self):
        """Worker thread: word list for the current page, from cache or Gemini"""
        try:
            self.logger.info(f"Starting page analysis - File: {self.current_file_name}, Page: {self.current_page_number}")
            self.logger.info(f"Full PDF path: {self.current_pdf_path}")

            words = self.cache.get_page(self.current_page_key)
            if words is not None:
                self.logger.info(f"Page {self.current_page_number} loaded from cache ({len(words)} entries)")
                source = "saved"
            else:
                self._status(f"Rendering page {self.current_page_number}...", True)
                image = self._page_image()
                self._status("Analyzing with Gemini...", True)
                words, tokens_sent, tokens_received = self.gemini.analyze_page(image)
                self.logger.info(f"Gemini analysis complete - Tokens sent: {tokens_sent}, Tokens received (incl. thinking): {tokens_received}")
                self.cache.put_page(self.current_page_key, words,
                                    self.current_file_name, self.current_page_number)
                source = "new"

            self.current_words = words
            n_words = sum(1 for w in words if not w.is_special)
            self.logger.info(f"Found {n_words} Tamil words on page {self.current_page_number}")

            GLib.idle_add(self._update_word_list, words)
            GLib.idle_add(self._update_context_display)
            self._status(f"✅ {n_words} words" + (" (saved earlier, no cost)" if source == "saved" else ""))

        except Exception as e:
            self.logger.error(f"Analysis error: {e}")
            self._status(f"❌ Error: {e}")
        finally:
            GLib.idle_add(self.analyze_btn.set_sensitive, True)

    def _update_word_list(self, words):
        """Update word list in UI"""
        for child in self.word_listbox.get_children():
            self.word_listbox.remove(child)

        regular_words = [w for w in words if not w.is_special]
        special = [w for w in words if w.is_special]
        tamil_font = self.config.get_tamil_font()

        for word in regular_words:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            box.set_margin_start(5)
            box.set_margin_end(5)
            box.set_margin_top(3)
            box.set_margin_bottom(3)

            tamil_label = Gtk.Label()
            tamil_label.set_markup(f"<span font_family='{tamil_font}' size='large'><b>{esc(word.tamil_word)}</b></span>")
            tamil_label.set_halign(Gtk.Align.START)
            box.pack_start(tamil_label, False, False, 0)

            if word.pronunciation:
                say_label = Gtk.Label()
                say_label.set_markup(f"<span foreground='#8e44ad'>🗣 {esc(word.pronunciation)}</span>")
                say_label.set_halign(Gtk.Align.START)
                box.pack_start(say_label, False, False, 0)

            literal_label = Gtk.Label()
            literal_label.set_markup(f"<small>{esc(word.literal_translation)}</small>")
            literal_label.set_halign(Gtk.Align.START)
            literal_label.set_line_wrap(True)
            box.pack_start(literal_label, False, False, 0)

            row.add(box)
            row.word_data = word
            self.word_listbox.add(row)

        titles = {"POEM_SUMMARY": "📖 Poem Summary", "PICTURE_NOTE": "🖼 About the Pictures"}
        for entry in special:
            self.word_listbox.add(Gtk.Separator())
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            box.set_margin_start(8)
            box.set_margin_end(8)
            box.set_margin_top(8)
            box.set_margin_bottom(8)

            title_label = Gtk.Label()
            title_label.set_markup(f"<b>{titles.get(entry.tamil_word, 'Note')}</b>")
            title_label.set_halign(Gtk.Align.START)

            summary_label = Gtk.Label()
            summary_label.set_markup(f"<small>{esc(entry.contextual_meaning)}</small>")
            summary_label.set_halign(Gtk.Align.START)
            summary_label.set_line_wrap(True)
            summary_label.set_selectable(True)

            box.pack_start(title_label, False, False, 0)
            box.pack_start(summary_label, False, False, 0)
            row.add(box)
            row.word_data = entry
            self.word_listbox.add(row)

        self.word_listbox.show_all()
        return False

    def _update_context_display(self):
        """Update the context display with file name and page number"""
        if self.current_file_name and self.current_page_number:
            context_text = f"📄 {self.current_file_name} - Page {self.current_page_number}"
            self.context_label.set_markup(f"<small><i>{esc(context_text)}</i></small>")
        else:
            self.context_label.set_markup("<small><i>No document loaded</i></small>")
        return False

    def on_lookup_clicked(self, button):
        """Lookup text selected in Okular"""
        self.set_status("Getting selected text...", True)
        self.lookup_btn.set_sensitive(False)
        try:
            selected_text = self.okular.get_selected_text()
            if not selected_text:
                self.logger.warning("No text selected in Okular for lookup")
                self.set_status("⚠️ No text selected in Okular")
                self.lookup_btn.set_sensitive(True)
                return
            page_num = self.okular.get_current_page()
            pdf_path = self.okular.get_current_document()
            self._set_current_page(pdf_path, page_num)
        except Exception as e:
            self.logger.error(f"Lookup error: {e}")
            self.set_status(f"❌ Error: {e}")
            self.lookup_btn.set_sensitive(True)
            return

        self.logger.info(f"Starting word lookup - Selected text: '{selected_text}'")
        self.set_status(f"Looking up: {selected_text}", True)
        word = TamilWord(selected_text)
        self.selected_word = word
        self._show_word_detail(word)
        self._run_in_background(self._fetch_detail, word, True)

    def on_word_selected(self, listbox, row):
        """Word selected from list: show what we have, fetch details if missing"""
        if not (row and hasattr(row, 'word_data')):
            return
        word = row.word_data
        self.selected_word = word
        self._show_word_detail(word)
        if not word.is_special and not word.has_detail and word.tamil_word not in self._details_in_flight:
            self.set_status(f"Getting details for {word.tamil_word}...", True)
            self._run_in_background(self._fetch_detail, word, False)

    def _fetch_detail(self, word, from_selection):
        """Worker thread: fill in a word's details from cache or Gemini"""
        self._details_in_flight.add(word.tamil_word)
        try:
            detail = self.cache.get_detail(self.current_page_key, word.tamil_word)
            if detail:
                self.logger.info(f"Details for {word.tamil_word} loaded from cache")
            else:
                image = self._page_image()
                detail, tokens_sent, tokens_received = self.gemini.lookup_word(word.tamil_word, image)
                self.logger.info(f"Word lookup complete - Tokens sent: {tokens_sent}, Tokens received (incl. thinking): {tokens_received}")
                if not detail:
                    self._status(f"❌ No details for {word.tamil_word}")
                    return
                # Keep the key as the word we asked about, so the cache finds it again
                detail.tamil_word = word.tamil_word
                self.cache.put_detail(self.current_page_key, detail,
                                      self.config.get_word_lookup_prompt())
            word.merge_detail(detail)
            self.logger.info(f"Found word: {word.tamil_word} - {word.literal_translation}")
            if self.selected_word is word:
                GLib.idle_add(self._show_word_detail, word)
            self._status("✅ Details ready")
        except Exception as e:
            self.logger.error(f"Lookup error: {e}")
            self._status(f"❌ Error: {e}")
        finally:
            self._details_in_flight.discard(word.tamil_word)
            if from_selection:
                GLib.idle_add(self.lookup_btn.set_sensitive, True)

    def _show_word_detail(self, word):
        """Display word details"""
        tamil_font = self.config.get_tamil_font()

        if word.is_special:
            self.detail_view.set_markup(f"<span foreground='#3498db'>{esc(word.contextual_meaning)}</span>")
            return False

        self.logger.info(f"Showing word detail for: {word.tamil_word}")

        parts = [f"<span font_family='{tamil_font}' size='xx-large'><b>{esc(word.tamil_word)}</b></span>"]
        if word.pronunciation:
            parts.append(f"<b>Say it:</b>\n<span foreground='#8e44ad' size='large'>🗣 {esc(word.pronunciation)}</span>")
        if word.romanization:
            parts.append(f"<b>Romanized:</b>\n<span foreground='#7f8c8d'>{esc(word.romanization)}</span>")
        if word.sound_notes:
            parts.append(f"<b>Tricky Sounds:</b>\n<span foreground='#8e44ad'>{esc(word.sound_notes)}</span>")
        if word.literal_translation:
            parts.append(f"<b>Literal Translation:</b>\n<span foreground='#e74c3c'>{esc(word.literal_translation)}</span>")

        if word.has_detail:
            if word.contextual_meaning:
                contextual = self._make_urls_clickable(esc(word.contextual_meaning))
                parts.append(f"<b>Contextual Meaning:</b>\n<span foreground='#3498db'>{contextual}</span>")
            if word.grammar_notes:
                parts.append(f"<b>Grammar:</b>\n<span foreground='#27ae60'>{esc(word.grammar_notes)}</span>")
            if word.sentence_context:
                parts.append(f"<b>Sentence Context:</b>\n<span style='italic' foreground='#7f8c8d'>{esc(word.sentence_context)}</span>")
        else:
            parts.append("<i>Loading details…</i>")

        self.detail_view.set_markup("\n\n".join(parts))
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
            self.set_status("❌ Failed to open URL")
    
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
                print("   #####################################")
                print("   # Tamil Assistant configuration:    #")
                print("   #####################################")
                print("   # Configure window behavior for Tamil Assistant")
                print("   for_window [class=\"TamilAssistant\"] move scratchpad")
                print("   for_window [class=\"TamilAssistant\"] resize set 400 900")
                print("   for_window [class=\"TamilAssistant\"] floating enable")
                print("   for_window [class=\"TamilAssistant\"] move position 1520 0")
                print("")
                print("   # Position on right side when shown (adjust based on your screen resolution)")
                print("   # For 1920x1080: use 1520")
                print("   # For 2560x1440: use 2160")
                print("   # For 3840x2160: use 3440")
                print("   for_window [title=\"Tamil Assistant\"] move position 1520 0")
                print("")
                print("   # Keyboard shortcut: Mod+Y to execute script and show as floating panel")
                print("   bindsym $mod+y exec tamil-assistant-launcher")
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
