from django import template

register = template.Library()

GRADIENTS = [
    ('linear-gradient(135deg, #667eea 0%, #764ba2 100%)', '#e0c3fc'),
    ('linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', '#fecfef'),
    ('linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', '#d6f5ff'),
    ('linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', '#d4ffe8'),
    ('linear-gradient(135deg, #fa709a 0%, #fee140 100%)', '#fff4cc'),
    ('linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)', '#f5e6ff'),
    ('linear-gradient(135deg, #fccb90 0%, #d57eeb 100%)', '#faedff'),
    ('linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)', '#eef4ff'),
]


@register.filter(name='book_gradient')
def book_gradient(title):
    if not title:
        return GRADIENTS[0]
    hash_val = 0
    for ch in str(title):
        hash_val = ord(ch) + ((hash_val << 5) - hash_val)
    return GRADIENTS[abs(hash_val) % len(GRADIENTS)]
