from django.core.cache.utils import make_template_fragment_key
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from PIL import Image
from posts.models import Post, Group, User, Comment
import tempfile
import time


TEST_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}


@override_settings(CACHES=TEST_CACHE)
class PostsTest(TestCase):
    def setUp(self):
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.user = User.objects.create_user(
            username='ivan1337',
            email='ivan1337@ya.ru',
            password='13371337')
        self.group = Group.objects.create(
            slug="Testid",
            title="Test Group",
            description="Test spec")
        self.authorized_client.force_login(self.user)
        self.text = 'TestTestTest!'
        self.edit_text = 'EditTestEdit'
        self.image = self._create_img()
        self.notImg = self._create_file()

    def _create_img(self):
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            image = Image.new('RGB', (200, 200), 'white')
            image.save(f, 'PNG')
        return open(f.name, mode='rb')

    def _create_file(self):
        file = SimpleUploadedFile('filename.txt', b'hello world', 'text/plain')
        return file

    def check_post(self, text, post_id):
        response_index = self.authorized_client.get(reverse('index'))
        self.assertContains(response_index, text)
        response_profile = self.authorized_client.get(
            reverse('profile', kwargs={'username': self.user.username}))
        self.assertContains(response_profile, text)
        response_post = self.authorized_client.get(reverse('post', kwargs={
            'username': self.user.username,
            'post_id': post_id}))
        self.assertContains(response_post, text)
        responce_group_post = self.authorized_client.get(
            reverse('group_posts', kwargs={'slug': self.group.slug}))
        self.assertContains(response_post, text)

    def test_client_page(self):
        response = self.client.get(
            reverse('profile', kwargs={'username': self.user.username}))
        self.assertEqual(response.status_code, 200)

    def test_add_post_authenticated(self):
        response = self.authorized_client.post(
            reverse('new_post'),
            data={'text': self.text, 'group': self.group.id},
            follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)
        post = Post.objects.all().first()
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.text, self.text)

    def test_add_post_deauthenticated(self):
        response = self.client.post(
            reverse('new_post'),
            data={'text': self.text, 'group': self.group.id},
            follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 0)
        self.url = reverse('new_post')
        self.login_target = reverse('login') + '?next=' + self.url
        response = self.client.get(self.url)
        self.assertRedirects(response, self.login_target)

    def test_published_index(self):
        self.post = Post.objects.create(
            text=self.text, author=self.user, group=self.group)
        post_id = int(self.post.id)
        text = self.text
        self.check_post(text, post_id)

    def test_post_edit(self):
        self.post = Post.objects.create(
            text=self.text, author=self.user, group=self.group)
        post_id = self.post.id
        response = self.authorized_client.post(reverse('post_edit', kwargs={
                                               'username': self.user.username,
                                               'post_id': post_id}),
                                               {'text': {self.edit_text}})
        text = self.edit_text
        self.check_post(text, post_id)

    def test_404(self):
        response = self.client.get("/random_page/", follow=True)
        self.assertEqual(response.status_code, 404)

    def test_upload_img(self):
        post = Post.objects.create(
            text=self.text, author=self.user, group=self.group)
        response = self.authorized_client.post(reverse('post_edit', kwargs={
                                               'username': self.user.username,
                                               'post_id': post.id}),
                                               {'text': self.edit_text,
                                                'image': self.image})
        text = '<img'
        post_id = post.id
        self.check_post(text, post_id)

    def test_upload_noimg(self):
        post = Post.objects.create(
            text=self.text, author=self.user, group=self.group)
        response = self.authorized_client.post(reverse('post_edit', kwargs={
                                               'username': self.user.username,
                                               'post_id': post.id}),
                                               {'text': {self.edit_text},
                                                'image': self.notImg})
        self.assertTrue(response.context['form'].has_error('image'))


class TestCache(TestCase):
    def setUp(self):
        self.key = make_template_fragment_key('index_page', [1])

    def test_cache(self):
        self.client.get(reverse('index'))
        self.assertTrue(cache.get(self.key))
        cache.clear()
        self.assertFalse(cache.get(self.key))


class TestFollowing(TestCase):
    def setUp(self):
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.user_1 = User.objects.create_user(
            username='ivan1337',
            email='ivan1337@ya.ru',
            password='13371337')
        self.user_2 = User.objects.create_user(
            username='oleg1337',
            email='oleg1337@ya.ru',
            password='13371337')

    def test_follow(self):
        self.authorized_client.force_login(self.user_1)
        response = self.authorized_client.get(
            reverse('profile', kwargs={'username': self.user_2.username}))
        button_subscribe = 'Подписаться'
        self.assertContains(response, button_subscribe)
        response = self.authorized_client.get(
            reverse('profile_follow', kwargs={'username': self.user_2.username}))
        author_profile = reverse(
            'profile', kwargs={'username': self.user_2.username})
        self.assertRedirects(response, author_profile)
        response = self.authorized_client.get(
            reverse('profile', kwargs={'username': self.user_2.username}))
        button_unsubscribe = 'Отписаться'
        self.assertContains(response, button_unsubscribe)
        response = self.authorized_client.get(
            reverse('profile_unfollow', kwargs={'username': self.user_2.username}))
        author_profile = reverse(
            'profile', kwargs={'username': self.user_2.username})
        self.assertRedirects(response, author_profile)

    def test_follow_lent(self):
        self.post = Post.objects.create(
            text='Test_text', author=self.user_2)
        self.authorized_client.force_login(self.user_1)
        self.authorized_client.get(
            reverse('profile_follow', kwargs={'username': self.user_2.username}))
        response = self.authorized_client.get(reverse('user_following'))
        self.assertContains(response, self.post.text)
        self.authorized_client.get(
            reverse('profile_unfollow', kwargs={'username': self.user_2.username}))
        response = self.authorized_client.get(reverse('user_following'))
        self.assertNotContains(response, self.post.text)


class TestComment(TestCase):
    def setUp(self):
        self.authorized_client = Client()
        self.unauthorized_client = Client()
        self.user_1 = User.objects.create_user(
            username='ivan1337',
            email='ivan1337@ya.ru',
            password='13371337')
        self.user_2 = User.objects.create_user(
            username='oleg1337',
            email='oleg1337@ya.ru',
            password='13371337')
        self.post_user2 = Post.objects.create(
            text='test_text', author=self.user_2)
        self.post_id = self.post_user2.id
        self.test_text = 'text_comment'

    def test_comment_auth(self):
        comment_url = reverse('add_comment', kwargs={'username': self.user_2,
                                                     'post_id': self.post_id})
        self.authorized_client.force_login(self.user_1)
        self.authorized_client.post(comment_url, {'text': self.test_text})
        response = self.authorized_client.get(reverse('post', kwargs={
            'username': self.user_2.username,
            'post_id': self.post_id}))
        self.assertEqual(1, Comment.objects.filter(
            text=self.test_text).count())
        self.assertContains(response, self.test_text)





    def test_comment_deauth(self):
        comment_url = reverse('add_comment', kwargs={'username': self.user_2,
                                                     'post_id': self.post_id})
        self.authorized_client.post(comment_url, {'text': self.test_text})
        response = self.authorized_client.get(reverse('post', kwargs={
            'username': self.user_2.username,
            'post_id': self.post_id}))
        self.assertEqual(0, Comment.objects.filter(
            text=self.test_text).count())