import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
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
            group=cls.group
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

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """При отправке валидной формы, пост создается в базе данных"""
        post_count = Post.objects.count()
        post_data = {
            'text': 'Бла бла бла',
            'group': PostFormTest.post.group.pk,
            'image': PostFormTest.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=post_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': PostFormTest.user.username}
        ))
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                group=PostFormTest.post.group.pk,
                text='Бла бла бла',
                image='posts/small.gif'
            ).exists()
        )

    def test_post_edit(self):
        """При отправке валидной формы, пост менется в базе данных"""
        post_count = Post.objects.count()
        orignal_text = PostFormTest.post.text

        edit_data = {
            'text': 'Измененный текст поста',
            'group': PostFormTest.post.group.pk,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostFormTest.post.pk}
            ),
            data=edit_data)
        edit_text = edit_data['text']

        self.assertEqual(Post.objects.count(), post_count)

        self.assertRedirects(
            response, reverse(
                'posts:post_detail', kwargs={'post_id': PostFormTest.post.pk}))

        self.assertNotEqual(orignal_text, edit_text)

    def test_unauthorized_client_cant_create_post(self):
        """Неавторизованный пользователь не может создать пост"""
        post_count = Post.objects.count()
        post_data = {
            'text': 'Бла бла бла',
            'group': PostFormTest.post.group.pk,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=post_data,
            follow=True
        )
        self.assertRedirects(response, reverse('login')
                             + '?next=' + reverse('posts:post_create'))
        self.assertEqual(Post.objects.count(), post_count)
