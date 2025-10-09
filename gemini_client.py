#!/usr/bin/env python3
"""
Google Gemini REST API client for Tamil text analysis
Uses direct HTTP requests - based on working portfolio implementation
"""

import requests
import base64
import json
import io
import html
import logging
from PIL import Image
from tamil_assistant.config_manager import get_config

class TamilWord:
    def __init__(self, tamil_word, literal, contextual, sentence):
        self.tamil_word = tamil_word
        self.literal_translation = literal
        self.contextual_meaning = contextual
        self.sentence_context = sentence

    def __repr__(self):
        return f"TamilWord({self.tamil_word}: {self.literal_translation})"

class GeminiClient:
    def __init__(self, api_key=None, model=None):
        """
        Initialize Gemini client
        If api_key/model not provided, reads from config
        """
        if api_key is None or model is None:
            config = get_config()
            self.api_key = api_key or config.get_gemini_api_key()
            self.model = model or config.get_gemini_model()
        else:
            self.api_key = api_key
            self.model = model

        # Use consistent timeout like the working implementation
        self.timeout = 60
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        
        # Setup logging
        self.logger = logging.getLogger('GeminiClient')

        print(f"✓ Gemini client initialized with model: {self.model}")

    def _image_to_base64(self, image):
        """Convert PIL Image to base64 string"""
        buffer = io.BytesIO()
        # Convert to RGB if needed (remove alpha channel)
        if image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = rgb_image

        image.save(buffer, format='JPEG', quality=85)
        image_bytes = buffer.getvalue()
        return base64.b64encode(image_bytes).decode('utf-8')

    def _decode_html_entities(self, text: str) -> str:
        """Decode HTML entities in text - copied from working implementation"""
        try:
            return html.unescape(text)
        except Exception as e:
            print(f"Warning: Error decoding HTML entities: {e}")
            return text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')

    def analyze_page(self, image):
        """Analyze entire page for Tamil words"""
        config = get_config()
        prompt = config.get_page_analysis_prompt()

        try:
            # Build payload matching working implementation structure
            base64_image = self._image_to_base64(image)

            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{
                        "text": prompt
                    }, {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64_image
                        }
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 8192,
                }
            }

            # Make request
            headers = {"Content-Type": "application/json"}
            url = f"{self.api_url}?key={self.api_key}"

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            # Check status code first
            if response.status_code != 200:
                error_text = response.text[:200] if response.text else "No error details"
                raise Exception(f"Gemini API error: {response.status_code} - {error_text}")

            response.raise_for_status()

            # Parse response using working implementation's approach
            response_data = response.json()

            if 'candidates' not in response_data or not response_data['candidates']:
                raise Exception("No candidates in Gemini response")

            candidate = response_data['candidates'][0]
            if 'content' not in candidate:
                raise Exception("No content in Gemini response")

            if 'parts' not in candidate['content']:
                raise Exception("No parts in Gemini response content")

            # Extract text from all parts
            full_response = ""
            for part in candidate['content']['parts']:
                if 'text' in part:
                    full_response += part['text']

            if not full_response.strip():
                raise Exception("Empty response from Gemini")

            # Decode HTML entities
            decoded_response = self._decode_html_entities(full_response.strip())

            # Extract token usage if available
            tokens_sent = 0
            tokens_received = 0
            if 'usageMetadata' in response_data:
                usage = response_data['usageMetadata']
                tokens_sent = usage.get('promptTokenCount', 0)
                tokens_received = usage.get('candidatesTokenCount', 0)
                self.logger.info(f"Token usage - Sent: {tokens_sent}, Received: {tokens_received}")

            words = self._parse_response(decoded_response)
            return words, tokens_sent, tokens_received

        except requests.exceptions.Timeout:
            raise Exception(f"Request timed out after {self.timeout}s. Check your internet connection.")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Connection error: {e}. Check your internet connection.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Gemini API request failed: {e}")
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")

    def lookup_word(self, text, context_image):
        """Lookup specific word with context"""
        config = get_config()
        prompt_template = config.get_word_lookup_prompt()
        prompt = prompt_template.format(word=text)

        try:
            # Build payload
            base64_image = self._image_to_base64(context_image)

            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{
                        "text": prompt
                    }, {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64_image
                        }
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 4096,
                }
            }

            # Make request
            headers = {"Content-Type": "application/json"}
            url = f"{self.api_url}?key={self.api_key}"

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code != 200:
                error_text = response.text[:200] if response.text else "No error details"
                raise Exception(f"Gemini API error: {response.status_code} - {error_text}")

            response.raise_for_status()

            # Parse response
            response_data = response.json()

            if 'candidates' not in response_data or not response_data['candidates']:
                raise Exception("No candidates in Gemini response")

            candidate = response_data['candidates'][0]
            if 'content' not in candidate or 'parts' not in candidate['content']:
                raise Exception("Invalid response structure")

            # Extract text
            full_response = ""
            for part in candidate['content']['parts']:
                if 'text' in part:
                    full_response += part['text']

            if not full_response.strip():
                raise Exception("Empty response from Gemini")

            # Decode HTML entities
            decoded_response = self._decode_html_entities(full_response.strip())

            # Extract token usage if available
            tokens_sent = 0
            tokens_received = 0
            if 'usageMetadata' in response_data:
                usage = response_data['usageMetadata']
                tokens_sent = usage.get('promptTokenCount', 0)
                tokens_received = usage.get('candidatesTokenCount', 0)
                self.logger.info(f"Token usage - Sent: {tokens_sent}, Received: {tokens_received}")

            words = self._parse_response(decoded_response)
            word = words[0] if words else None
            return word, tokens_sent, tokens_received

        except requests.exceptions.Timeout:
            raise Exception(f"Request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
        except Exception as e:
            raise Exception(f"Error: {e}")

    def _parse_response(self, text):
        """Parse Gemini response to TamilWord objects"""
        # Clean markdown if present
        text = text.strip()

        # Remove markdown code blocks
        if text.startswith("```json"):
            text = text.split("```json")[1].split("```")[0].strip()
        elif text.startswith("```"):
            text = text.split("```")[1].split("```")[0].strip()

        # Sometimes Gemini adds explanation text, try to extract JSON
        # Look for [ or { to find JSON start
        json_start = -1
        for i, char in enumerate(text):
            if char in '[{':
                json_start = i
                break

        if json_start > 0:
            text = text[json_start:]

        # Find JSON end
        json_end = -1
        for i in range(len(text) - 1, -1, -1):
            if text[i] in ']}':
                json_end = i + 1
                break

        if json_end > 0:
            text = text[:json_end]

        try:
            data = json.loads(text)

            # Handle both array and single object
            if isinstance(data, list):
                words = data
            elif isinstance(data, dict):
                words = [data]
            else:
                raise ValueError("Unexpected response format")

            # Convert to TamilWord objects
            result = []
            for word_data in words:
                word = TamilWord(
                    tamil_word=word_data.get('tamil_word', ''),
                    literal=word_data.get('literal_translation', ''),
                    contextual=word_data.get('contextual_meaning', ''),
                    sentence=word_data.get('sentence_context', '')
                )
                result.append(word)

            return result

        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            try:
                # Attempt to fix incomplete JSON
                fixed_text = self._fix_incomplete_json(text)
                data = json.loads(fixed_text)
                
                # Handle both array and single object
                if isinstance(data, list):
                    words = data
                elif isinstance(data, dict):
                    words = [data]
                else:
                    raise ValueError("Unexpected response format")

                # Convert to TamilWord objects
                result = []
                for word_data in words:
                    word = TamilWord(
                        tamil_word=word_data.get('tamil_word', ''),
                        literal=word_data.get('literal_translation', ''),
                        contextual=word_data.get('contextual_meaning', ''),
                        sentence=word_data.get('sentence_context', '')
                    )
                    result.append(word)

                return result
                
            except Exception:
                self.logger.error(f"Failed to parse JSON. Response was:\n{text[:500]}")
                raise Exception(f"Failed to parse JSON: {e}\nResponse preview: {text[:200]}")

    def _fix_incomplete_json(self, text):
        """Attempt to fix common JSON issues"""
        # Remove incomplete last entry by finding the last complete object
        text = text.strip()
        
        # If it doesn't end with ], try to fix it
        if not text.endswith(']'):
            # Find the last complete object
            last_complete_bracket = text.rfind(']')
            if last_complete_bracket > 0:
                # Extract only the complete part
                text = text[:last_complete_bracket + 1]
            else:
                # If no complete bracket found, try to close the last incomplete object
                # Find the last complete closing brace
                last_complete_brace = text.rfind('}')
                if last_complete_brace > 0:
                    # Add closing bracket
                    text = text[:last_complete_brace + 1] + ']'
        
        return text

    def test_connection(self):
        """Test API connection with simple request - matching working implementation"""
        try:
            # Build payload exactly like working implementation
            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": "Say 'API is working!' in one sentence."}]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 50,
                }
            }

            headers = {"Content-Type": "application/json"}
            url = f"{self.api_url}?key={self.api_key}"

            print(f"   Testing connection to: {url.split('?')[0]}")
            print(f"   Model: {self.model}")
            print(f"   Timeout: {self.timeout}s")

            # Use same timeout as working implementation
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout  # 30 seconds like working code
            )

            print(f"   Status code: {response.status_code}")

            # Check status code first (like working implementation)
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', response.text)
                except:
                    error_msg = response.text[:200]
                return False, f"HTTP {response.status_code}: {error_msg}"

            response.raise_for_status()
            response_data = response.json()

            # Parse response using working implementation's approach
            if 'candidates' not in response_data or not response_data['candidates']:
                return False, "No candidates in response"

            candidate = response_data['candidates'][0]
            if 'content' not in candidate:
                return False, "No content in response"

            if 'parts' not in candidate['content']:
                return False, "No parts in response content"

            # Extract text
            full_response = ""
            for part in candidate['content']['parts']:
                if 'text' in part:
                    full_response += part['text']

            if not full_response.strip():
                return False, "Empty response text"

            # Decode HTML entities
            decoded_response = self._decode_html_entities(full_response.strip())

            return True, decoded_response

        except requests.exceptions.Timeout:
            return False, f"Timeout after {self.timeout}s - check your internet connection"
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection error: {e}"
        except requests.exceptions.HTTPError as e:
            return False, f"HTTP error: {e}"
        except Exception as e:
            return False, f"Error: {str(e)}"
