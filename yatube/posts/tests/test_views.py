import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Comment, Group, Post, Follow

User = get_user_model()
NUMBER_OF_POSTS = 13
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='slava')
        cls.follower = User.objects.create_user(username='follower')
        cls.non_follower = User.objects.create_user(username='non_follower')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.image = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.image,
            content_type='image/gif'
        )
        post_list = []
        for i in range(NUMBER_OF_POSTS):
            post = Post(
                text=f'Тестовый пост-{i}',
                author=cls.user,
                group=cls.group,
                image=cls.uploaded
            )
            post_list.append(post)
        Post.objects.bulk_create(post_list)
        cls.posts = Post.objects.all()
        cls.form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.follower_client = Client()
        self.follower_client.force_login(self.follower)
        self.non_follower_client = Client()
        self.non_follower_client.force_login(self.non_follower)

    def test_pages_uses_correct_template(self):
        """Во view-функциях используются правильные html-шаблоны"""
        templates_url_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': PostModelTest.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': PostModelTest.user}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={
                    'post_id': PostModelTest.posts[1].id
                }
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={
                    'post_id': PostModelTest.posts[1].id
                }
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_url_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_pages_show_correct_context(self):
        """Cловарь contex соответствует ожиданиям на страницах:
        'posts:index', 'posts:group_list' и 'posts:profile'"""
        templates_url_names = [
            reverse('posts:index'),
            reverse(
                'posts:group_list', kwargs={'slug': PostModelTest.group.slug}
            ),
            reverse(
                'posts:profile', kwargs={'username': PostModelTest.user}
            ),
        ]
        for reverse_name in templates_url_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                first_object = response.context['page_obj'][0]
                self.assertEqual(response.status_code, 200)
                self.assertIn('page_obj', response.context)
                self.assertEqual(
                    first_object.text,
                    PostModelTest.posts[0].text
                )
                self.assertEqual(
                    first_object.author.username,
                    self.user.username
                )
                self.assertEqual(
                    first_object.group.title,
                    PostModelTest.group.title
                )
                self.assertEqual(
                    first_object.image,
                    PostModelTest.posts[0].image
                )

    def test_post_detail_show_correct_context(self):
        """Cловарь contex соответствует ожиданиям на странице 'post_detail'"""
        response = self.client.get(reverse(
            'posts:post_detail',
            args={PostModelTest.posts[1].id}
        ))
        first_object = response.context['full_post']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(first_object.text, PostModelTest.posts[1].text)
        self.assertEqual(
            first_object.author.username,
            PostModelTest.user.username
        )
        self.assertEqual(first_object.group.title, PostModelTest.group.title)
        self.assertEqual(
            first_object.image,
            PostModelTest.posts[1].image
        )

    def test_post_create_show_correct_context(self):
        """Cловарь contex соответствует ожиданиям на странице 'post_create'"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form = response.context['form']
        self.assertIsInstance(form, PostForm)
        self.assertEqual(response.status_code, 200)
        for field_name, field_type in self.form_fields.items():
            with self.subTest(field_name=field_name):
                self.assertIsInstance(form.fields[field_name], field_type)

    def test_post_edit_show_correct_context(self):
        """Cловарь contex соответствует ожиданиям на странице 'post_edit'"""
        response = self.authorized_client.get(reverse(
            'posts:post_edit',
            args=[PostModelTest.posts[1].id]
        ))
        form = response.context['form']
        self.assertIsInstance(form, PostForm)
        self.assertEqual(form.instance, PostModelTest.posts[1])
        self.assertEqual(response.status_code, 200)
        for field_name, field_type in self.form_fields.items():
            with self.subTest(field_name=field_name):
                self.assertIsInstance(form.fields[field_name], field_type)

    def test_paginator(self):
        """Paginator показывает правильное кол-во постов на страницах
        'posts:index', 'posts:group_list' и 'posts:profile'"""
        templates_url_names = [
            (reverse('posts:index'), 10),
            (reverse('posts:index') + '?page=2', 3),
            (reverse(
                'posts:group_list', kwargs={'slug': PostModelTest.group.slug}
            ), 10),
            (reverse(
                'posts:group_list', kwargs={'slug': PostModelTest.group.slug}
            ) + '?page=2', 3),
            (reverse('posts:profile', args={PostModelTest.user}), 10),
            (reverse(
                'posts:profile',
                args={PostModelTest.user}
            ) + '?page=2', 3),
        ]

        for reverse_name, expected_num_posts in templates_url_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(
                    response.context['page_obj']
                ), expected_num_posts)

    def test_post_appears_on_pages(self):
        """Пост отображается на страницах 'index', 'group_list' и 'profile'"""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertContains(response, PostModelTest.posts[1].text)
        response = self.authorized_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': PostModelTest.group.slug}
        ))
        self.assertContains(response, PostModelTest.posts[1].text)
        response = self.authorized_client.get(reverse(
            'posts:profile',
            kwargs={'username': PostModelTest.user.username}
        ))
        self.assertContains(response, PostModelTest.posts[1].text)

    def test_post_does_not_appear_on_wrong_group_page(self):
        """Пост не отображается в неправильной группе"""
        group2 = Group.objects.create(
            title='Неправильная группа',
            slug='wrong_slug',
            description='Описание неправильной группы',
        )
        response = self.authorized_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': group2.slug}
        ))
        self.assertNotContains(response, PostModelTest.posts[1].text)

    def test_unauthorized_client_cant_write_comment(self):
        """Неавторизованный пользователь не может оставить комментарий"""
        comments_count = Comment.objects.filter(
            post_id=PostModelTest.posts[2].id
        ).count()
        self.guest_client.post(
            reverse('posts:add_comment', args=[PostModelTest.posts[2].id]),
            data={'text': 'Новый комментарий'}
        )
        self.assertEqual(
            Comment.objects.filter(post_id=PostModelTest.posts[2].id).count(),
            comments_count)

    def test_comment_show_on_post_page(self):
        """Комментарий выводится на странице поста."""
        self.authorized_client.post(
            reverse('posts:add_comment', args=[PostModelTest.posts[2].id]),
            data={'text': 'Новый комментарий'}
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail', args=[PostModelTest.posts[2].id])
        )
        self.assertEqual(response.context.get('comments')[0].text,
                         'Новый комментарий')

    def test_cache_index_page(self):
        """Кеширование работает верно."""
        test_post = Post.objects.create(
            text='Этот пост будет удален',
            author=PostModelTest.user,
            group=PostModelTest.group
        )
        check_content = self.guest_client.get(reverse('posts:index')).content
        test_post.delete()
        cached_content = self.guest_client.get(reverse('posts:index')).content
        self.assertEqual(check_content, cached_content)
        cache.clear()
        cleared_cache = self.guest_client.get(reverse('posts:index')).content
        self.assertNotEqual(cached_content, cleared_cache)

    def test_authorized_client_can_follow_author(self):
        """Авторизованный пользователь может подписаться на автора"""
        response = self.follower_client.post(
            reverse('posts:profile_follow', args=[PostModelTest.user.username])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Follow.objects.filter(
            user=self.follower.id,
            author=self.user.id).exists())

    def test_authorized_client_can_unfollow_author(self):
        """Авторизованный пользователь может отписаться от автора"""
        response = self.follower_client.post(
            reverse('posts:profile_unfollow',
                    args=[PostModelTest.user.username])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Follow.objects.filter(
            user=PostModelTest.follower.id,
            author=PostModelTest.user.id).exists())

    def test_post_appears_in_followers_feed(self):
        """Новый пост появляется на странице подписчика
        и не появляется в ленте неподписанного пользователя"""
        Follow.objects.create(user=PostModelTest.follower,
                              author=PostModelTest.user)
        new_post = Post.objects.create(
            text='Новый пост для подписчика',
            author=PostModelTest.user,
            group=PostModelTest.group
        )
        response = self.follower_client.get(reverse('posts:follow_index'))
        self.assertContains(response, new_post.text)
        response = self.non_follower_client.get(reverse('posts:follow_index'))
        self.assertNotContains(response, new_post.text)
