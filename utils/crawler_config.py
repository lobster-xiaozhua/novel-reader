from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class SiteConfig:
    name: str
    domain: str
    chapter_list_selectors: List[str] = field(default_factory=lambda: [
        "div[class*='list']",
        "div[class*='chapter']",
        "dl",
        "ul",
        "ol"
    ])
    content_selectors: List[str] = field(default_factory=lambda: [
        "#content",
        "#bookContent",
        ".content",
        ".chapter-content",
        ".read-content"
    ])
    title_selector: Optional[str] = None
    author_selector: Optional[str] = None
    description_selector: Optional[str] = None
    link_selector: str = "a[href]"
    skip_keywords: List[str] = field(default_factory=lambda: [
        "首页", "末页", "上一页", "下一页", "返回", "目录", "顶部", "底部"
    ])
    request_delay: float = 0.5
    user_agents: List[str] = field(default_factory=lambda: [])
    cookies: Dict[str, str] = field(default_factory=dict)
    use_proxy: bool = False
    proxy_url: Optional[str] = None
    retry_delay: float = 2.0
    max_retries: int = 3


UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/105.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]

DEFAULT_CONFIG = SiteConfig(name="default", domain="*", user_agents=UA_POOL)

SITE_CONFIGS: Dict[str, SiteConfig] = {
    "example.com": SiteConfig(
        name="Example Novel Site",
        domain="example.com",
        chapter_list_selectors=["#chapter-list", ".chapter-list"],
        content_selectors=["#novel-content"],
        title_selector="h1.title",
        author_selector=".author-name",
        description_selector=".description",
        user_agents=UA_POOL,
    ),
}


def get_config_for_url(url: str) -> SiteConfig:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc
    for site_domain, config in SITE_CONFIGS.items():
        if site_domain in domain:
            return config
    return DEFAULT_CONFIG
