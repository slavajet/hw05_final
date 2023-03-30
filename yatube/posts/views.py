from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from posts import constants

from .forms import CommentForm, PostForm
from .models import Group, Post, User, Follow
from .utils import paginate


@cache_page(constants.INDEX_CACHE, key_prefix='index_page')
def index(request):
    post_list = Post.objects.all()
    context = {
        'page_obj': paginate(request, post_list),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    context = {
        'group': group,
        'posts': post_list,
        'page_obj': paginate(request, post_list),
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = author.post_set.all()
    post_count = post_list.count()
    following = Follow.objects.filter(
        user=request.user, author=author).exists()
    context = {
        'author': author,
        'page_obj': paginate(request, post_list),
        'posts': post_list,
        'post_count': post_count,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    full_post = get_object_or_404(Post, id=post_id)
    author_posts = Post.objects.filter(author=full_post.author)
    post_count = author_posts.count()
    comments = full_post.comments.select_related('author')
    form = CommentForm()
    context = {
        'full_post': full_post,
        'post_count': post_count,
        'comments': comments,
        'form': form,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    if request.method != 'POST':
        form = PostForm()
        context = {'form': form}
        return render(request, 'posts/create_post.html', context)

    form = PostForm(request.POST, request.FILES)
    if not form.is_valid():
        context = {'form': form}
        return render(request, 'posts/create_post.html', context)

    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', post.author.username)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        'post': post,
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = Post.objects.get(id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    context = {
        'page_obj': paginate(request, post_list)
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user and not Follow.objects.filter(
            user=request.user, author=author).exists():
        Follow.objects.create(user=request.user, author=author)
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username)
