BOOK_GRADIENTS = [
    ('#667eea', '#764ba2'),
    ('#f093fb', '#f5576c'),
    ('#4facfe', '#00f2fe'),
    ('#43e97b', '#38f9d7'),
    ('#fa709a', '#fee140'),
    ('#30cfd0', '#330867'),
    ('#a8edea', '#fed6e3'),
    ('#ff9a9e', '#fecfef'),
]


def get_book_gradient(book_id: int) -> tuple:
    return BOOK_GRADIENTS[book_id % len(BOOK_GRADIENTS)]
