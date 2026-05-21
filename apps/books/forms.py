from django import forms
from .models import Book, Tag


class BookForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': '标签，用逗号分隔'}),
        help_text='多个标签用逗号分隔'
    )

    class Meta:
        model = Book
        fields = ['title', 'author', 'description', 'category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input', 'placeholder': '书名'}),
            'author': forms.TextInput(attrs={'class': 'input', 'placeholder': '作者'}),
            'description': forms.Textarea(attrs={'class': 'input', 'placeholder': '简介', 'rows': 3}),
            'category': forms.TextInput(attrs={'class': 'input', 'placeholder': '分类'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['tags_input'].initial = ','.join(self.instance.tags.values_list('name', flat=True))

    def save(self, commit=True):
        book = super().save(commit=commit)
        if commit:
            tags_input = self.cleaned_data.get('tags_input', '')
            if tags_input:
                tag_names = [t.strip() for t in tags_input.split(',') if t.strip()]
                for name in tag_names:
                    tag, _ = Tag.objects.get_or_create(name=name)
                    book.tags.add(tag)
            self._remove_stale_tags(book)
        return book

    def _remove_stale_tags(self, book):
        tags_input = self.cleaned_data.get('tags_input', '')
        current_names = set(t.strip() for t in tags_input.split(',') if t.strip())
        for tag in book.tags.all():
            if tag.name not in current_names:
                book.tags.remove(tag)


class MultiFileInput(forms.FileInput):
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        super().__init__(attrs={'accept': '.txt', **(attrs or {})})


class BatchImportForm(forms.Form):
    files = forms.FileField(widget=MultiFileInput())
