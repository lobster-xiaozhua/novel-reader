from django import forms
from .models import Book


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input', 'placeholder': '书名'}),
            'author': forms.TextInput(attrs={'class': 'input', 'placeholder': '作者'}),
            'description': forms.Textarea(attrs={'class': 'input', 'placeholder': '简介', 'rows': 3}),
        }
