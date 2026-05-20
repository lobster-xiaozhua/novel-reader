from django.shortcuts import render
from django.core.paginator import Paginator
from haystack.query import SearchQuerySet
from apps.books.models import Book


def search(request):
    query = request.GET.get("q", "").strip()
    results = []
    suggestions = []
    page_obj = None
    total = 0

    if query:
        sqs = SearchQuerySet().models(Book).filter(content=query)
        total = sqs.count()

        paginator = Paginator(sqs, 12)
        page = request.GET.get("page", 1)
        page_obj = paginator.get_page(page)

        results = [result.object for result in page_obj.object_list]

    if len(query) >= 2:
        suggestions = Book.objects.filter(title__istartswith=query).values_list("title", flat=True)[:10]

    context = {
        "query": query,
        "results": results,
        "total": total,
        "page_obj": page_obj,
        "suggestions": suggestions,
    }
    return render(request, "search/results.html", context)
