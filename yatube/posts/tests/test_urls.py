from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from posts.models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='slava')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{PostModelTest.group.slug}/': 'posts/group_list.html',
            f'/profile/{PostModelTest.user.username}/': 'posts/profile.html',
            f'/posts/{PostModelTest.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{PostModelTest.post.id}/edit/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, 200)

    def test_url_accessible_to_any_user(self):
        """Страницы доступны любому пользователю."""
        templates_url_names = [
            '/',
            f'/group/{PostModelTest.group.slug}/',
            f'/profile/{PostModelTest.user.username}/',
            f'/posts/{PostModelTest.post.id}/',
        ]
        for url in templates_url_names:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_url_accessible_to_authorized_user(self):
        """Страница '/create/'  доступна авторизованному пользователю,
        и страница '/posts/1/edit/' доступна автору."""
        templates = ['/create/', '/posts/1/edit/']
        for template in templates:
            with self.subTest(template=template):
                response = self.authorized_client.get(template)
                self.assertEqual(response.status_code, 200)

    def test_url_accessible_to_author(self):
        """Страница '/posts/1/edit/' доступна автору поста."""
        response = self.authorized_client.get('/posts/1/edit/')
        self.assertEqual(response.status_code, 200)

    def test_redirect_guest_to_login(self):
        """Пользователь перенаправлен на страницу авторизации"""
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_unexisting_page(self):
        """Недоступность несуществующей страницы проекта."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, 404)
