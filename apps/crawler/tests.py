import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import CrawlerTask


class CrawlerTaskModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.task = CrawlerTask.objects.create(
            user=self.user,
            url='http://example.com/book',
            status='pending'
        )

    def test_task_str(self):
        """测试任务模型字符串表示"""
        expected = f'{self.task.url} ({self.task.get_status_display()})'
        self.assertEqual(str(self.task), expected)

    def test_task_status_choices(self):
        """测试任务状态选项"""
        valid_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']
        for status in valid_statuses:
            self.task.status = status
            self.task.save()
            self.assertEqual(self.task.status, status)

    def test_task_default_status(self):
        """测试任务默认状态"""
        new_task = CrawlerTask.objects.create(
            user=self.user,
            url='http://example.com/new'
        )
        self.assertEqual(new_task.status, 'pending')

    def test_task_ordering(self):
        """测试任务排序"""
        task2 = CrawlerTask.objects.create(
            user=self.user,
            url='http://example.com/book2'
        )
        tasks = list(CrawlerTask.objects.all())
        self.assertEqual(tasks[0], task2)
        self.assertEqual(tasks[1], self.task)


class CrawlerViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        self.task = CrawlerTask.objects.create(
            user=self.user,
            url='http://example.com/book',
            status='pending'
        )

    def test_crawler_tasks_requires_login(self):
        """测试爬虫任务列表需要登录"""
        response = self.client.get(reverse('crawler_tasks'))
        self.assertEqual(response.status_code, 302)

    def test_crawler_tasks_view(self):
        """测试爬虫任务列表视图"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('crawler_tasks'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crawler/tasks.html')

    def test_crawler_tasks_only_show_own(self):
        """测试任务列表只显示自己的任务"""
        self.client.login(username='testuser', password='testpass123')
        CrawlerTask.objects.create(
            user=self.other_user,
            url='http://example.com/other'
        )

        response = self.client.get(reverse('crawler_tasks'))
        self.assertEqual(len(response.context['tasks']), 1)

    def test_create_task_requires_login(self):
        """测试创建任务需要登录"""
        response = self.client.post(reverse('create_task'), {
            'url': 'http://example.com/new'
        })
        self.assertEqual(response.status_code, 302)

    def test_create_task_requires_post(self):
        """测试创建任务只接受POST"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('create_task'))
        self.assertEqual(response.status_code, 405)

    def test_create_task_valid(self):
        """测试有效创建任务"""
        self.client.login(username='testuser', password='testpass123')

        with patch('apps.crawler.views.CrawlerEngine') as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine_class.return_value = mock_engine

            response = self.client.post(reverse('create_task'), {
                'url': 'http://example.com/new'
            })
            self.assertRedirects(response, reverse('crawler_tasks'))
            self.assertTrue(CrawlerTask.objects.filter(url='http://example.com/new').exists())

    def test_create_task_empty_url(self):
        """测试空URL创建任务失败"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('create_task'), {
            'url': ''
        })
        self.assertRedirects(response, reverse('crawler_tasks'))

    def test_create_task_whitespace_url(self):
        """测试空白字符URL被清理"""
        self.client.login(username='testuser', password='testpass123')

        with patch('apps.crawler.views.CrawlerEngine') as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine_class.return_value = mock_engine

            response = self.client.post(reverse('create_task'), {
                'url': '  http://example.com/new  '
            })
            self.assertRedirects(response, reverse('crawler_tasks'))
            task = CrawlerTask.objects.get(url='http://example.com/new')
            self.assertEqual(task.url, 'http://example.com/new')

    def test_task_detail_requires_login(self):
        """测试任务详情需要登录"""
        response = self.client.get(reverse('task_detail', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 302)

    def test_task_detail_view(self):
        """测试任务详情视图"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('task_detail', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['id'], self.task.id)
        self.assertEqual(data['status'], self.task.status)

    def test_task_detail_with_logs(self):
        """测试任务详情带日志"""
        self.client.login(username='testuser', password='testpass123')
        self.task.logs = json.dumps([{'time': 1234567890, 'msg': '测试日志'}])
        self.task.save()

        response = self.client.get(reverse('task_detail', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(len(data['logs']), 1)
        self.assertEqual(data['logs'][0]['msg'], '测试日志')

    def test_task_detail_invalid_logs(self):
        """测试任务详情处理无效日志"""
        self.client.login(username='testuser', password='testpass123')
        self.task.logs = 'invalid json'
        self.task.save()

        response = self.client.get(reverse('task_detail', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['logs'], [])

    def test_task_detail_not_found(self):
        """测试任务详情404"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('task_detail', kwargs={'pk': 99999}))
        self.assertEqual(response.status_code, 404)

    def test_task_detail_cannot_access_others(self):
        """测试无法访问他人任务"""
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(reverse('task_detail', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 404)

    def test_task_detail_response_structure(self):
        """测试任务详情响应结构"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('task_detail', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        expected_keys = ['id', 'status', 'total_chapters', 'downloaded_chapters', 'error_message', 'logs']
        for key in expected_keys:
            self.assertIn(key, data)
