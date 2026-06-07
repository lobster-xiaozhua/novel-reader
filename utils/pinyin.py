"""汉字转拼音工具 - 轻量级实现"""
import logging

logger = logging.getLogger(__name__)

# 常用汉字拼音映射（覆盖高频汉字）
_PINYIN_DATA = {}

def _init_pinyin():
    """初始化拼音映射表 - 从 pypinyin 或内置数据加载"""
    global _PINYIN_DATA
    if _PINYIN_DATA:
        return True
    
    try:
        # 尝试使用 pypinyin 库
        from pypinyin import lazy_pinyin, Style
        _PINYIN_DATA = {
            '_converter': lambda text: ''.join(lazy_pinyin(text, style=Style.NORMAL)),
            '_converter_initial': lambda text: ''.join([p[0] for p in lazy_pinyin(text, style=Style.NORMAL) if p]),
        }
        logger.info('[Pinyin] 使用 pypinyin 库')
        return True
    except ImportError:
        pass
    
    # 降级方案：使用最小内置映射
    _PINYIN_DATA = {
        '_converter': _fallback_converter,
        '_converter_initial': _fallback_initial_converter,
    }
    logger.info('[Pinyin] 使用降级方案（无 pypinyin）')
    return False


def _fallback_converter(text: str) -> str:
    """降级拼音转换 - 仅处理简单映射"""
    return text.lower()


def _fallback_initial_converter(text: str) -> str:
    """降级首字母转换"""
    return text[0].lower() if text else ''


def to_pinyin(text: str) -> str:
    """将文本转换为拼音（全拼）"""
    if not _init_pinyin():
        return text.lower()
    return _PINYIN_DATA['_converter'](text)


def to_pinyin_initial(text: str) -> str:
    """将文本转换为拼音首字母"""
    if not _init_pinyin():
        return text[0].lower() if text else ''
    return _PINYIN_DATA['_converter_initial'](text)


def expand_search_query(text: str) -> list[str]:
    """扩展搜索查询 - 返回原文、拼音、首字母等多个搜索词"""
    if not text:
        return []
    
    results = [text.lower()]
    pinyin = to_pinyin(text)
    if pinyin != text.lower():
        results.append(pinyin)
    
    initials = to_pinyin_initial(text)
    if initials and len(text) > 1:
        results.append(initials)
    
    return list(set(results))
