from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from apps.books.models import Book


def search(request):
    query = request.GET.get('q', '')
    results = []
    suggestions = []
    page_obj = None

    if query:
        results = Book.objects.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        )
        paginator = Paginator(results, 12)
        page_obj = paginator.get_page(request.GET.get('page', 1))

    if len(query) >= 2:
        suggestions = Book.objects.filter(
            title__istartswith=query
        ).values_list('title', flat=True)[:10]

    context = {
        'query': query,
        'results': results if query else [],
        'total': len(results) if query else 0,
        'page_obj': page_obj,
        'suggestions': suggestions,
    }
    return render(request, 'search/results.html', context)
