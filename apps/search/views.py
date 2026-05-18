from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from apps.books.models import Book


@login_required
def search(request):
    query = request.GET.get('q', '')
    results = []
    suggestions = []

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
        'page_obj': page_obj if query else None,
        'suggestions': suggestions,
    }
    return render(request, 'search/results.html', context)
