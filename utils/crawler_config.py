import re
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
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ])


# 默认配置
DEFAULT_CONFIG = SiteConfig(name="default", domain="*")

# 预定义站点配置
SITE_CONFIGS: Dict[str, SiteConfig] = {
    "example.com": SiteConfig(
        name="Example Novel Site",
        domain="example.com",
        chapter_list_selectors=["#chapter-list", ".chapter-list"],
        content_selectors=["#novel-content"],
        title_selector="h1.title",
        author_selector=".author-name",
        description_selector=".description",
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
