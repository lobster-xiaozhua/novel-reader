# Elasticsearch index mappings with ik_max_word analyzer for Chinese text

BOOK_INDEX = 'novel_books'
CHAPTER_INDEX = 'novel_chapters'

COMMON_SETTINGS = {
    'analysis': {
        'analyzer': {
            'ik_smart_analyzer': {
                'type': 'custom',
                'tokenizer': 'ik_smart',
            },
        },
    },
}


def get_book_mapping():
    return {
        'settings': {
            'number_of_shards': 1,
            'number_of_replicas': 0,
            'analysis': {
                'analyzer': {
                    'ik_smart_analyzer': {
                        'type': 'custom',
                        'tokenizer': 'ik_smart',
                    },
                },
            },
        },
        'mappings': {
            'properties': {
                'id': {'type': 'integer'},
                'title': {
                    'type': 'text',
                    'analyzer': 'ik_max_word',
                    'search_analyzer': 'ik_smart',
                    'fields': {
                        'keyword': {'type': 'keyword'},
                        'pinyin': {'type': 'text', 'analyzer': 'ik_max_word'},
                    },
                },
                'author': {
                    'type': 'text',
                    'analyzer': 'ik_max_word',
                    'search_analyzer': 'ik_smart',
                    'fields': {
                        'keyword': {'type': 'keyword'},
                    },
                },
                'category': {
                    'type': 'keyword',
                },
                'description': {
                    'type': 'text',
                    'analyzer': 'ik_max_word',
                    'search_analyzer': 'ik_smart',
                },
                'tags': {
                    'type': 'keyword',
                },
                'total_chapters': {'type': 'integer'},
                'created_at': {'type': 'date'},
                'updated_at': {'type': 'date'},
            },
        },
    }


def get_chapter_mapping():
    return {
        'settings': {
            'number_of_shards': 2,
            'number_of_replicas': 0,
            'analysis': {
                'analyzer': {
                    'ik_smart_analyzer': {
                        'type': 'custom',
                        'tokenizer': 'ik_smart',
                    },
                },
            },
        },
        'mappings': {
            'properties': {
                'id': {'type': 'integer'},
                'book_id': {'type': 'integer'},
                'chapter_number': {'type': 'integer'},
                'title': {
                    'type': 'text',
                    'analyzer': 'ik_max_word',
                    'search_analyzer': 'ik_smart',
                    'fields': {
                        'keyword': {'type': 'keyword'},
                    },
                },
                'content': {
                    'type': 'text',
                    'analyzer': 'ik_max_word',
                    'search_analyzer': 'ik_smart',
                    'term_vector': 'with_positions_offsets',
                },
                'word_count': {'type': 'integer'},
                'created_at': {'type': 'date'},
            },
        },
    }
