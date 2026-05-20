from django.test import TestCase, Client
from django.urls import reverse
from apps.books.models import Book


class SearchViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.book1 = Book.objects.create(
            title='斗破苍穹',
            author='天蚕土豆',
            description='玄幻经典',
            folder_path='data/books/dpcc'
        )
        self.book2 = Book.objects.create(
            title='斗罗大陆',
            author='唐家三少',
            description='玄幻经典',
            folder_path='data/books/dldl'
        )
        self.book3 = Book.objects.create(
            title='凡人修仙传',
            author='忘语',
            description='修仙经典',
            folder_path='data/books/frxxz'
        )

    def test_search_view_get_empty(self):
        """测试搜索页面GET请求（无查询）"""
        response = self.client.get(reverse('search'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'search/results.html')
        self.assertEqual(len(response.context['results']), 0)
        self.assertEqual(response.context['total'], 0)

    def test_search_by_title(self):
        """测试按书名搜索"""
        response = self.client.get(reverse('search') + '?q=斗')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 2)
        results = list(response.context['results'])
        self.assertIn(self.book1, results)
        self.assertIn(self.book2, results)

    def test_search_by_author(self):
        """测试按作者搜索"""
        response = self.client.get(reverse('search') + '?q=天蚕')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 1)
        self.assertIn(self.book1, response.context['results'])

    def test_search_case_insensitive(self):
        """测试搜索不区分大小写（拉丁字母）"""
        Book.objects.create(title='Harry Potter', author='JK Rowling', folder_path='data/books/hp')
        response = self.client.get(reverse('search') + '?q=harry')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 1)
        response2 = self.client.get(reverse('search') + '?q=HARRY')
        self.assertEqual(response2.context['total'], 1)

    def test_search_with_whitespace(self):
        """测试搜索自动去除空白"""
        response = self.client.get(reverse('search') + '?q=  斗破  ')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['query'], '斗破')

    def test_search_pagination(self):
        """测试搜索结果分页"""
        for i in range(15):
            Book.objects.create(
                title=f'测试书籍{i}',
                folder_path=f'data/books/test{i}'
            )

        response = self.client.get(reverse('search') + '?q=测试&page=2')
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['page_obj'])

    def test_search_suggestions(self):
        """测试搜索建议（需2字以上查询）"""
        response = self.client.get(reverse('search') + '?q=斗破')
        self.assertEqual(response.status_code, 200)
        suggestions = list(response.context['suggestions'])
        self.assertTrue(len(suggestions) <= 10)
        self.assertIn('斗破苍穹', suggestions)

    def test_search_no_suggestions_for_short_query(self):
        """测试短查询不返回建议"""
        response = self.client.get(reverse('search') + '?q=斗')
        self.assertEqual(response.status_code, 200)
        suggestions = list(response.context['suggestions'])
        self.assertEqual(len(suggestions), 0)

    def test_search_empty_query(self):
        """测试空查询"""
        response = self.client.get(reverse('search') + '?q=')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 0)

    def test_search_no_results(self):
        """测试无结果搜索"""
        response = self.client.get(reverse('search') + '?q=不存在的书')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 0)
        self.assertEqual(len(response.context['results']), 0)

    def test_search_prefetch_related(self):
        """测试搜索预取章节数据"""
        from apps.chapters.models import Chapter
        Chapter.objects.create(
            book=self.book1,
            chapter_number=1,
            title='第一章',
            file_path='data/books/dpcc/ch1.txt'
        )

        response = self.client.get(reverse('search') + '?q=斗破')
        self.assertEqual(response.status_code, 200)

    def test_search_with_chapters_count(self):
        """测试搜索结果包含章节数"""
        from apps.chapters.models import Chapter
        Chapter.objects.create(
            book=self.book1,
            chapter_number=1,
            title='第一章',
            file_path='data/books/dpcc/ch1.txt'
        )
        Chapter.objects.create(
            book=self.book1,
            chapter_number=2,
            title='第二章',
            file_path='data/books/dpcc/ch2.txt'
        )

        response = self.client.get(reverse('search') + '?q=斗破')
        self.assertEqual(response.status_code, 200)
