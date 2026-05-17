import os
import sys
import locale
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class TerminalCompat:
    SYMBOL_MAP: Dict[str, str] = {
        '✅': '[OK]',
        '❌': '[ERR]',
        '⚠️': '[WARN]',
        '📚': '[BOOK]',
        '🕷️': '[CRAWL]',
        '🔍': '[SEARCH]',
        '🔒': '[LOCK]',
        '⚡': '[FAST]',
        '📦': '[PKG]',
        '🔧': '[CONF]',
        '💾': '[DB]',
        '📡': '[NET]',
        '🔑': '[KEY]',
        '🛡️': '[SEC]',
        '📊': '[STAT]',
        '🔄': '[SYNC]',
        '⏳': '[WAIT]',
        '🚀': '[START]',
        '🛑': '[STOP]',
        '📋': '[LIST]',
    }

    def __init__(self):
        self.encoding = self._detect_encoding()
        self.supports_utf8 = self.encoding.lower() in ('utf-8', 'utf8')
        self.is_container = self._detect_container()
        self.is_ci = self._detect_ci()
        self.supports_emoji = self._check_emoji_support()

    def _detect_encoding(self) -> str:
        try:
            enc = sys.stdout.encoding
            if enc:
                return enc.lower()
        except Exception:
            pass

        try:
            enc = locale.getpreferredencoding()
            if enc:
                return enc.lower()
        except Exception:
            pass

        try:
            enc = os.environ.get('LANG', '').split('.')[-1]
            if enc:
                return enc.lower()
        except Exception:
            pass

        return 'ascii'

    def _check_emoji_support(self) -> bool:
        if not self.supports_utf8:
            return False

        if self.is_container or self.is_ci:
            return False

        if sys.platform == 'win32':
            try:
                version = sys.getwindowsversion()
                if version.major < 10:
                    return False
            except Exception:
                return False

        try:
            test_str = '✅'
            test_str.encode(self.encoding)
            return True
        except (UnicodeEncodeError, UnicodeDecodeError):
            return False

    def _detect_container(self) -> bool:
        indicators = [
            '/.dockerenv',
            '/run/.containerenv',
        ]
        for path in indicators:
            if os.path.exists(path):
                return True

        try:
            if os.path.exists('/proc/1/cgroup'):
                with open('/proc/1/cgroup', 'r') as f:
                    content = f.read().lower()
                    if 'docker' in content or 'kubepods' in content or 'containerd' in content:
                        return True
        except Exception:
            pass

        return bool(os.environ.get('KUBERNETES_SERVICE_HOST'))

    def _detect_ci(self) -> bool:
        ci_vars = [
            'CI', 'JENKINS_URL', 'GITLAB_CI', 'GITHUB_ACTIONS',
            'TRAVIS', 'CIRCLECI', 'TF_BUILD',
        ]
        return any(os.environ.get(v) for v in ci_vars)

    def sym(self, emoji: str) -> str:
        if self.supports_emoji:
            return emoji
        return self.SYMBOL_MAP.get(emoji, emoji)

    def safe_print(self, message: str):
        try:
            if self.supports_utf8:
                print(message)
            else:
                safe_msg = self._sanitize(message)
                print(safe_msg)
        except UnicodeEncodeError:
            safe_msg = self._sanitize(message)
            print(safe_msg)

    def _sanitize(self, text: str) -> str:
        result = text
        for emoji, replacement in self.SYMBOL_MAP.items():
            result = result.replace(emoji, replacement)
        try:
            result.encode(self.encoding, errors='replace')
        except Exception:
            result = result.encode('ascii', errors='replace').decode('ascii')
        return result

    def format_status(self, passed: bool) -> str:
        return self.sym('✅' if passed else '❌')

    def format_warning(self) -> str:
        return self.sym('⚠️')

    def format_header(self, title: str) -> str:
        return f"\n{'=' * 50}\n  {self.sym('🚀')} {title}\n{'=' * 50}"


terminal_compat = TerminalCompat()
