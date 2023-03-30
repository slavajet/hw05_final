from django.forms import ModelForm

from .models import Comment, Post


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'text': ('Текст'),
            'group': ('Группа'),
            'image': ('Картинка'),
        }
        help_texts = {
            'text': 'Здесь можно написать свой великолепный пост',
            'group': 'Если нет подходящей группы, оставьте поле пустым',
            'image': 'Можете прикрепить изображение',
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
    labels = {'text': ('Текст')}
    help_texts = {'text': 'Здесь можно написать свой великолепный комментарий'}
