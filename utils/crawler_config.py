"""爬虫站点配置模块。

定义站点配置数据结构和默认值，
提供基于域名匹配的配置查找功能。
支持自定义选择器、请求延迟、UA 池、代理等参数。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class SiteConfig:
    """站点爬虫配置数据类。

    封装单个目标网站的抓取规则和网络请求参数，
    包括 CSS 选择器、反爬策略、请求配置等。
    """
    name: str  # 站点名称标识
    domain: str  # 站点域名
    chapter_list_selectors: List[str] = field(default_factory=lambda: [
        "div[class*='list']",  # 章节列表容器常见 class
        "div[class*='chapter']",
        "dl",
        "ul",
        "ol"
    ])
    content_selectors: List[str] = field(default_factory=lambda: [
        "#content",  # 正文内容常见 ID/class
        "#bookContent",
        ".content",
        ".chapter-content",
        ".read-content"
    ])
    title_selector: Optional[str] = None  # 书名 CSS 选择器
    author_selector: Optional[str] = None  # 作者 CSS 选择器
    description_selector: Optional[str] = None  # 简介 CSS 选择器
    link_selector: str = "a[href]"  # 章节链接标签选择器
    skip_keywords: List[str] = field(default_factory=lambda: [
        "首页", "末页", "上一页", "下一页", "返回", "目录", "顶部", "底部"
    ])
    request_delay: float = 0.5  # 请求间隔（秒）
    user_agents: List[str] = field(default_factory=lambda: [])  # 站点专属 UA 池
    cookies: Dict[str, str] = field(default_factory=dict)  # 请求携带的 Cookie
    use_proxy: bool = False  # 是否启用代理
    proxy_url: Optional[str] = None  # 代理服务器地址
    retry_delay: float = 2.0  # 重试基础延迟（秒）
    max_retries: int = 3  # 最大重试次数


# 全局 User-Agent 池，覆盖 Chrome、Firefox、Safari、Edge 及移动端
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

# 默认配置：domain 为 "*" 表示匹配所有未单独配置的站点
DEFAULT_CONFIG = SiteConfig(name="default", domain="*", user_agents=UA_POOL)

# 已适配站点配置字典，键为域名，值为对应的 SiteConfig
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
    """根据 URL 域名匹配对应的站点配置。

    遍历已配置站点列表，若域名包含匹配项则返回对应配置，
    否则返回默认配置。

    Args:
        url: 完整的 URL 字符串。

    Returns:
        SiteConfig: 匹配的站点配置或默认配置。
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc
    for site_domain, config in SITE_CONFIGS.items():
        if site_domain in domain:
            return config
    return DEFAULT_CONFIG
