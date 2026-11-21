#!/usr/bin/env python3
"""
On-disk cache of Gemini results, so a page or word is only paid for once.

One JSON file per (PDF content, page, model, prompt):
    ~/.cache/tamil-assistant/pages/<pdf-hash>_p<page>_<model>_<prompt-hash>.json
holding the page's word list plus any word details fetched later.

The PDF is identified by its file name and size, so the PDF itself is never
read here. Changing the model or editing the page prompt starts a fresh
cache entry instead of showing stale answers.
"""

import hashlib
import json
import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from tamil_assistant.gemini_client import TamilWord

logger = logging.getLogger('ResultCache')


def _short_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:10]


class ResultCache:
    def __init__(self, cache_dir=None):
        base = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
        self.dir = Path(cache_dir) if cache_dir else base / 'tamil-assistant' / 'pages'

    def pdf_id(self, pdf_path):
        """Identify a PDF by file name + size (one stat call; the file is not read).
        Moving the file keeps its cache; a different file with the same name
        would also need the exact same byte size to collide."""
        size = os.stat(pdf_path).st_size
        return _short_hash(f"{os.path.basename(pdf_path)}:{size}")

    def page_key(self, pdf_path, page, model, page_prompt):
        safe_model = re.sub(r'[^A-Za-z0-9._-]', '_', model)
        return f"{self.pdf_id(pdf_path)}_p{page}_{safe_model}_{_short_hash(page_prompt)}"

    def _path(self, key):
        return self.dir / f"{key}.json"

    def _read(self, key):
        try:
            with open(self._path(key), encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as e:
            logger.warning(f"Ignoring unreadable cache file {key}: {e}")
            return None

    def _write(self, key, data):
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            # Write to a temp file then rename, so a crash never leaves half a file
            fd, tmp = tempfile.mkstemp(dir=self.dir, suffix='.tmp')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self._path(key))
        except OSError as e:
            logger.warning(f"Could not write cache file {key}: {e}")

    def get_page(self, key):
        """Cached word list for a page, or None"""
        data = self._read(key)
        if not data or 'words' not in data:
            return None
        words = [TamilWord.from_dict(d) for d in data['words']]
        # Words looked up after the page was cached
        for w in words:
            detail = data.get('details', {}).get(w.tamil_word)
            if detail:
                w.merge_detail(TamilWord.from_dict(detail))
        return words

    def put_page(self, key, words, file_name=None, page=None):
        data = self._read(key) or {}
        data.update({
            'file': file_name,
            'page': page,
            'created': data.get('created') or datetime.now().isoformat(timespec='seconds'),
            'words': [w.to_dict() for w in words],
        })
        data.setdefault('details', {})
        self._write(key, data)

    def get_detail(self, key, tamil_word):
        """Cached detail for one word on this page, or None.
        (Details stay valid when the detail prompt is edited; the prompt hash
        is stored only so it is visible which prompt produced them.)"""
        data = self._read(key)
        if not data:
            return None
        d = data.get('details', {}).get(tamil_word)
        return TamilWord.from_dict(d) if d else None

    def put_detail(self, key, word, detail_prompt):
        data = self._read(key) or {'details': {}}
        d = word.to_dict()
        d['prompt'] = _short_hash(detail_prompt)
        data.setdefault('details', {})[word.tamil_word] = d
        self._write(key, data)
