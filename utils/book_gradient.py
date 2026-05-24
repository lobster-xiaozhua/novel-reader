"""书籍封面渐变色工具。

提供预定义的渐变色方案，根据书籍 ID 循环分配
美观的渐变色彩组合，用于书籍封面展示。
"""

# 预定义书籍封面渐变色方案列表
# 每个元素为 (起始色, 结束色) 的 HEX 颜色对
BOOK_GRADIENTS = [
    ('#667eea', '#764ba2'),  # 蓝紫渐变
    ('#f093fb', '#f5576c'),  # 粉玫红渐变
    ('#4facfe', '#00f2fe'),  # 天蓝青渐变
    ('#43e97b', '#38f9d7'),  # 绿薄荷渐变
    ('#fa709a', '#fee140'),  # 粉黄渐变
    ('#30cfd0', '#330867'),  # 青深蓝渐变
    ('#a8edea', '#fed6e3'),  # 浅蓝粉渐变
    ('#ff9a9e', '#fecfef'),  # 柔和粉渐变
]


def get_book_gradient(book_id: int) -> tuple:
    """根据书籍 ID 获取对应的渐变色方案。

    使用取模运算循环分配渐变色，确保同一书籍 ID
    始终返回相同的渐变色组合。

    Args:
        book_id: 书籍的唯一整数 ID。

    Returns:
        tuple: (起始色, 结束色) 两个 HEX 颜色字符串的元组。
    """
    return BOOK_GRADIENTS[book_id % len(BOOK_GRADIENTS)]
