#!/usr/bin/env python3
"""
Configuration manager for Tamil Assistant
Reads and validates configuration from config.ini
"""

import os
import configparser
from pathlib import Path

class Config:
    def __init__(self, config_path=None):
        """Initialize configuration"""
        self.config = configparser.ConfigParser()

        # Determine config file path
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Default: look in script directory
            script_dir = Path(__file__).parent
            self.config_path = script_dir / 'config.ini'

        # Load configuration
        self.load()

        # Validate
        self.validate()

    def load(self):
        """Load configuration from file"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                f"Please create config.ini in the same directory as the scripts.\n"
                f"See config.ini.example for template."
            )

        self.config.read(self.config_path)
        print(f"✓ Configuration loaded from: {self.config_path}")

    def validate(self):
        """Validate required configuration"""
        errors = []

        # Check Gemini section
        if not self.config.has_section('gemini'):
            errors.append("Missing [gemini] section in config.ini")
        else:
            # Check API key
            api_key = self.get_gemini_api_key()
            if not api_key or api_key == '' or api_key.startswith('your-'):
                errors.append(
                    "Gemini API key not set in config.ini\n"
                    "Get your key from: https://aistudio.google.com/apikey\n"
                    "Then set it in config.ini under [gemini] section:\n"
                    "  api_key = YOUR_KEY_HERE"
                )

            # Check model
            if not self.config.has_option('gemini', 'model'):
                errors.append("Missing 'model' in [gemini] section")

        # Check UI section (optional but warn)
        if not self.config.has_section('ui'):
            print("⚠️  Warning: Missing [ui] section, using defaults")

        # Raise errors if any
        if errors:
            error_msg = "Configuration errors:\n\n" + "\n\n".join(f"• {e}" for e in errors)
            raise ValueError(error_msg)

        print("✓ Configuration validated successfully")

    # Gemini Configuration
    def get_gemini_api_key(self):
        """Get Gemini API key"""
        # Try environment variable first
        env_key = os.getenv('GEMINI_API_KEY')
        if env_key:
            return env_key

        # Then try config file
        return self.config.get('gemini', 'api_key', fallback='')

    def get_gemini_model(self):
        """Get Gemini model name"""
        return self.config.get('gemini', 'model', fallback='gemini-2.0-flash-exp')

    # UI Configuration
    def get_window_width(self):
        """Get window width"""
        return self.config.getint('ui', 'window_width', fallback=400)

    def get_window_height(self):
        """Get window height"""
        return self.config.getint('ui', 'window_height', fallback=900)

    def get_tamil_font(self):
        """Get Tamil font name"""
        return self.config.get('ui', 'font_tamil', fallback='Noto Sans Tamil')

    def get_font_size(self):
        """Get font size"""
        return self.config.getint('ui', 'font_size', fallback=11)

    # Okular Configuration
    def get_okular_service_pattern(self):
        """Get Okular D-Bus service pattern"""
        return self.config.get('okular', 'dbus_service_pattern', fallback='org.kde.okular-*')

    def get_okular_path(self):
        """Get Okular D-Bus path"""
        return self.config.get('okular', 'dbus_path', fallback='/okular')

    # Prompt Configuration
    def get_page_analysis_prompt(self):
        """Get page analysis prompt"""
        prompt_file = self.config.get('prompts', 'page_analysis_prompt_file', fallback='prompts/page_analysis.txt')
        return self._load_prompt_file(prompt_file)

    def get_word_lookup_prompt(self):
        """Get word lookup prompt template"""
        prompt_file = self.config.get('prompts', 'word_lookup_prompt_file', fallback='prompts/word_lookup.txt')
        return self._load_prompt_file(prompt_file)

    def _load_prompt_file(self, prompt_file):
        """Load prompt from file"""
        try:
            # Try relative to config file directory first
            prompt_path = self.config_path.parent / prompt_file
            if prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            
            # Try relative to script directory
            script_dir = Path(__file__).parent
            prompt_path = script_dir / prompt_file
            if prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            
            # Fall back to defaults
            if 'page_analysis' in prompt_file:
                return self._get_default_page_prompt()
            else:
                return self._get_default_word_prompt()
                
        except Exception as e:
            print(f"Warning: Could not load prompt file {prompt_file}: {e}")
            # Fall back to defaults
            if 'page_analysis' in prompt_file:
                return self._get_default_page_prompt()
            else:
                return self._get_default_word_prompt()

    def _get_default_page_prompt(self):
        """Default page analysis prompt if not in config"""
        return """Analyze this Tamil language learning page. For EVERY Tamil word visible:

Context:
1. Person using this is an Indian-origin Canadian.
2. Has limited Tamil knowledge
3. Is being taught by his grandmom from Indian
4. Student is 10 years old - very proficient in English and is learning French at school
5. Proficiency in English is equal to that of 14 year old. Reads a ton of novels.
6. His Tamil textbook is based on Tamil Nadu (India) textbook for 1st grade
7. The page (image) extracts are from that textbook

Extract and provide:
1. Tamil word (in Tamil script)
2. Literal/dictionary translation to English
3. Contextual meaning based on usage in the sentence
4. The sentence/phrase where it appears
5. There may be handwritten words instead of printed words. Try to identify the words and provide the contextual meaning.

Exception:
1. Sometimes the page will be only of pictures with no words (or very few words). 
Try your best to gather clues and as much information relayed by just the picture (s) and provide a hypothetical narration.

Return ONLY a JSON array with this exact structure:
[
  {
    "tamil_word": "தமிழ்",
    "literal_translation": "Tamil",
    "contextual_meaning": "refers to Tamil language in this context",
    "sentence_context": "the full sentence where this word appears"
  }
]

CRITICAL RULES:
- Include ALL Tamil words on the page
- Be precise with contextual meanings
- Try to see a pattern for the entire page. Such as it contains a poem or a song.
- If this page contains a poem or song, add a special entry at the END of the JSON array:
  {
    "tamil_word": "POEM_SUMMARY",
    "literal_translation": "Poem Summary",
    "contextual_meaning": "Complete summary of the poem including theme, message, cultural significance, and overall meaning explained for a 10-year-old with advanced English reading skills",
    "sentence_context": "Full text of the poem in Tamil"
  }
- For famous Tamil personalities, poets, scholars, divine entities, orators, or historical figures mentioned, add Wikipedia links in contextual_meaning like: "Famous Tamil poet. Learn more: https://en.wikipedia.org/wiki/[Name]"
- Add grammar notes in contextual_meaning if relevant
- Add poem summary explaining the entire meaning of the poem
- Return ONLY the JSON array
- Do NOT wrap in markdown code blocks
- Do NOT add any text before or after the JSON
- Start directly with [ and end with ]"""

    def _get_default_word_prompt(self):
        """Default word lookup prompt if not in config"""
        return """In this Tamil text image, focus on the word or phrase: "{word}"

Provide detailed analysis:
1. Literal/dictionary meaning
2. Contextual meaning in this specific sentence
3. Grammar notes (verb form, case, tense, etc.)
4. The full sentence where it appears
5. If this refers to a famous (or not) Tamil personality, poet, scholar, authors, divine entity, orator, historical figure, or names of a person, include Wikipedia link

Return ONLY a JSON object with this exact structure:
{
  "tamil_word": "{word}",
  "literal_translation": "...",
  "contextual_meaning": "...",
  "sentence_context": "...",
  "grammar_notes": "..."
}

CRITICAL RULES:
- For identified Tamil personalities, names, authors, poets, scholars, divine entities, orators, or historical figures, add Wikipedia links in contextual_meaning like: "Famous Tamil poet. Learn more: https://en.wikipedia.org/wiki/[Name]"
- Return ONLY the JSON object
- Do NOT wrap in markdown code blocks
- Do NOT add any text before or after
- Start directly with { and end with }"""

    def __str__(self):
        """String representation of config"""
        api_key = self.get_gemini_api_key()
        masked_key = f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 14 else "***"

        return f"""Tamil Assistant Configuration:
  Config file: {self.config_path}

  Gemini:
    API Key: {masked_key}
    Model: {self.get_gemini_model()}

  UI:
    Window: {self.get_window_width()}x{self.get_window_height()}
    Tamil Font: {self.get_tamil_font()}
    Font Size: {self.get_font_size()}pt

  Okular:
    Service: {self.get_okular_service_pattern()}
    Path: {self.get_okular_path()}
"""

# Singleton instance
_config_instance = None

def get_config(config_path=None):
    """Get or create config instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance
