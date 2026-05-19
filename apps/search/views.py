from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from apps.books.models import Book


def search(request):
    query = request.GET.get('q', '').strip()
    results = []
    suggestions = []
    page_obj = None
    total = 0

    if query:
        results = Book.objects.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        ).prefetch_related('chapters')
        total = results.count()
        paginator = Paginator(results, 12)
        page_obj = paginator.get_page(request.GET.get('page', 1))

    if len(query) >= 2:
        suggestions = Book.objects.filter(
            title__istartswith=query
        ).values_list('title', flat=True)[:10]

    context = {
        'query': query,
        'results': page_obj.object_list if page_obj else [],
        'total': total,
        'page_obj': page_obj,
        'suggestions': suggestions,
    }
    return render(request, 'search/results.html', context)
