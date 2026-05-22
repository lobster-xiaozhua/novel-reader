from django.http import JsonResponse
from django.core.paginator import Paginator
from haystack.query import SearchQuerySet
from apps.books.models import Book


def search(request):
    query = request.GET.get('q', '').strip()
    results = []
    suggestions = []
    total = 0

    if query:
        sqs = SearchQuerySet().models(Book).filter(content=query)
        total = sqs.count()

        paginator = Paginator(sqs, 12)
        page = request.GET.get('page', 1)
        page_obj = paginator.get_page(page)

        results = [{'id': r.object.id, 'title': r.object.title, 'author': r.object.author, 'category': r.object.category} for r in page_obj.object_list]

    if len(query) >= 2:
        suggestions = list(Book.objects.filter(title__istartswith=query).values_list('title', flat=True)[:10])

    return JsonResponse({
        'query': query,
        'results': results,
        'total': total,
        'suggestions': suggestions,
    })
