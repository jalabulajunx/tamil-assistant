#!/usr/bin/env python3
"""
Google Gemini REST API client for Tamil text analysis.

Two calls:
- analyze_page(): one call per page, returns a compact word list
  (word, short meaning, romanization, pronunciation). Kept short because
  output tokens are what cost money.
- lookup_word(): one call per word the user opens, returns the full detail
  (context, sentence, grammar, pronunciation, sound notes).
"""

import requests
import base64
import json
import io
import html
import logging
from PIL import Image
from tamil_assistant.config_manager import get_config

# Entries in the page list that are not words
SPECIAL_ENTRIES = ("POEM_SUMMARY", "PICTURE_NOTE")


class TamilWord:
    FIELDS = ("tamil_word", "literal_translation", "contextual_meaning",
              "sentence_context", "grammar_notes", "romanization",
              "pronunciation", "sound_notes")

    def __init__(self, tamil_word, literal="", contextual="", sentence="",
                 grammar_notes="", romanization="", pronunciation="",
                 sound_notes="", has_detail=False):
        self.tamil_word = tamil_word
        self.literal_translation = literal
        self.contextual_meaning = contextual
        self.sentence_context = sentence
        self.grammar_notes = grammar_notes
        self.romanization = romanization
        self.pronunciation = pronunciation
        self.sound_notes = sound_notes
        self.has_detail = has_detail

    @property
    def is_special(self):
        return self.tamil_word in SPECIAL_ENTRIES

    def merge_detail(self, other):
        """Fill in fields from a detail lookup, keeping list values the detail lacks"""
        for f in self.FIELDS[1:]:
            value = getattr(other, f, "")
            if value:
                setattr(self, f, value)
        self.has_detail = True

    def to_dict(self):
        d = {f: getattr(self, f) for f in self.FIELDS}
        d["has_detail"] = self.has_detail
        return d

    @classmethod
    def from_dict(cls, d):
        """Build from our own cache format or from either Gemini response format"""
        w = cls(
            tamil_word=d.get("tamil_word") or d.get("w", ""),
            literal=d.get("literal_translation") or d.get("en", ""),
            contextual=d.get("contextual_meaning", ""),
            sentence=d.get("sentence_context", ""),
            grammar_notes=d.get("grammar_notes", ""),
            romanization=d.get("romanization") or d.get("rom", ""),
            pronunciation=d.get("pronunciation") or d.get("say", ""),
            sound_notes=d.get("sound_notes", ""),
            has_detail=bool(d.get("has_detail", False)),
        )
        # Special entries carry their text in the meaning field
        if w.is_special and not w.contextual_meaning:
            w.contextual_meaning = w.literal_translation
        return w

    def __repr__(self):
        return f"TamilWord({self.tamil_word}: {self.literal_translation})"


class GeminiClient:
    def __init__(self, api_key=None, model=None):
        """
        Initialize Gemini client
        If api_key/model not provided, reads from config
        """
        config = get_config()
        self.api_key = api_key or config.get_gemini_api_key()
        self.model = model or config.get_gemini_model()
        self.timeout = config.get_request_timeout()
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        self.logger = logging.getLogger('GeminiClient')
        print(f"✓ Gemini client initialized with model: {self.model}")

    def _image_to_base64(self, image):
        """Convert PIL Image to base64 JPEG"""
        buffer = io.BytesIO()
        if image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = rgb_image
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        image.save(buffer, format='JPEG', quality=85)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def _generate(self, prompt, image=None, max_tokens=8192, json_output=True):
        """
        POST one generateContent request.
        Returns (text, tokens_sent, tokens_received). tokens_received includes
        thinking tokens, which are billed as output.
        """
        parts = [{"text": prompt}]
        if image is not None:
            parts.append({"inline_data": {"mime_type": "image/jpeg",
                                          "data": self._image_to_base64(image)}})
        generation_config = {"temperature": 0.2, "maxOutputTokens": max_tokens}
        if json_output:
            generation_config["responseMimeType"] = "application/json"

        payload = {"contents": [{"role": "user", "parts": parts}],
                   "generationConfig": generation_config}
        # Key goes in a header, not the URL, so it never appears in error messages or logs
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}

        try:
            response = requests.post(self.api_url, headers=headers, json=payload,
                                     timeout=self.timeout)
        except requests.exceptions.Timeout:
            raise Exception(f"Request timed out after {self.timeout}s. Check your internet connection.")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error. Check your internet connection.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Gemini API request failed: {type(e).__name__}")

        if response.status_code != 200:
            try:
                message = response.json().get('error', {}).get('message', '')
            except ValueError:
                message = response.text[:200]
            raise Exception(f"Gemini API error {response.status_code}: {message[:200]}")

        data = response.json()
        candidates = data.get('candidates') or []
        if not candidates:
            raise Exception("No candidates in Gemini response")
        candidate = candidates[0]
        text = "".join(p.get('text', '') for p in candidate.get('content', {}).get('parts', []))
        if not text.strip():
            reason = candidate.get('finishReason', 'unknown')
            raise Exception(f"Empty response from Gemini (finish reason: {reason})")

        usage = data.get('usageMetadata', {})
        tokens_sent = usage.get('promptTokenCount', 0)
        tokens_received = usage.get('candidatesTokenCount', 0) + usage.get('thoughtsTokenCount', 0)
        self.logger.info(
            f"Token usage - Sent: {tokens_sent}, Received: {usage.get('candidatesTokenCount', 0)} "
            f"+ thinking {usage.get('thoughtsTokenCount', 0)}, finish: {candidate.get('finishReason')}")

        return html.unescape(text.strip()), tokens_sent, tokens_received

    def analyze_page(self, image):
        """Compact word list for a page. Returns (words, tokens_sent, tokens_received)"""
        prompt = get_config().get_page_analysis_prompt()
        text, sent, received = self._generate(prompt, image, max_tokens=8192)
        return self._parse_response(text), sent, received

    def lookup_word(self, text, context_image):
        """Full detail for one word in the context of the page.
        Returns (word or None, tokens_sent, tokens_received)"""
        prompt = get_config().get_word_lookup_prompt().format(word=text)
        response, sent, received = self._generate(prompt, context_image, max_tokens=4096)
        words = self._parse_response(response)
        word = words[0] if words else None
        if word:
            word.has_detail = True
        return word, sent, received

    def _parse_response(self, text):
        """Parse a JSON array or object into TamilWord objects"""
        text = text.strip()

        # Remove markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        # Trim any text around the JSON
        starts = [i for i in (text.find('['), text.find('{')) if i >= 0]
        if starts:
            text = text[min(starts):]
        end = max(text.rfind(']'), text.rfind('}'))
        if end >= 0:
            text = text[:end + 1]

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            try:
                data = json.loads(self._fix_incomplete_json(text))
            except Exception:
                self.logger.error(f"Failed to parse JSON. Response was:\n{text[:500]}")
                raise Exception(f"Failed to parse JSON: {e}")

        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise Exception("Unexpected response format")

        return [TamilWord.from_dict(d) for d in data if isinstance(d, dict)]

    def _fix_incomplete_json(self, text):
        """Recover a truncated JSON array by dropping the incomplete last entry"""
        text = text.strip()
        if text.startswith('[') and not text.endswith(']'):
            last_brace = text.rfind('}')
            if last_brace > 0:
                text = text[:last_brace + 1] + ']'
        return text

    def test_connection(self):
        """Test API connection with a tiny request. Returns (ok, message)"""
        try:
            text, _, _ = self._generate("Say 'API is working!' in one sentence.",
                                        max_tokens=256, json_output=False)
            return True, text
        except Exception as e:
            return False, str(e)
