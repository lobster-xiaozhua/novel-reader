from django.shortcuts import render
from django.contrib.auth.decorators import login_required
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

    if len(query) >= 2:
        suggestions = Book.objects.filter(
            title__istartswith=query
        ).values_list('title', flat=True)[:10]

    context = {
        'query': query,
        'results': results,
        'suggestions': suggestions,
    }
    return render(request, 'search/results.html', context)
