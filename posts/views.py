from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.cache import cache_page
from .models import *
from .forms import PostForm, CommentForm


def pagination(request, post_list):
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return paginator, page


def index(request):
    post_list = Post.objects.all()
    paginator, page = pagination(request, post_list)
    return render(
        request,
        'index.html',
        {'page': page, 'paginator': paginator})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = Post.objects.filter(group=group)
    paginator, page = pagination(request, post_list)
    return render(request, "group.html",
                  {'group': group, 'page': page, 'paginator': paginator})


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.order_by('-pub_date').all()
    paginator, page = pagination(request, post_list)
    following_count = author.following.all().count()
    follower_count = author.follower.all().count()
    status_following = None
    if request.user.is_authenticated:
        status_following = author.following.filter(user=request.user)
    return render(request, 'profile.html',
                  {'author': author, 'username': username,
                   'page': page, 'paginator': paginator,
                   'status_following': status_following, 
                   'following_count': following_count,
                   'follower_count': follower_count})


def post_view(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, pk=post_id)
    count = Post.objects.filter(author=post.author).count
    comments = Comment.objects.filter(post=post)
    form = CommentForm()
    return render(request, "post_view.html",
                  {'count': count, 'username': username, 'comments': comments,
                   'post': post, 'author': post.author, 'form': form})


@login_required
def new_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST or None, files=request.FILES or None)
        if form.is_valid():
            my_post = form.save(commit=False)
            my_post.author = request.user
            my_post.save()
            return redirect('index')
    form = PostForm()
    return render(request, 'new_post.html', {'form': form})


def post_edit(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, pk=post_id)
    if request.user != post.author:
        return redirect('post', username=username, post_id=post_id)
    form = PostForm(request.POST or None, files=request.FILES or None,
                    instance=post)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('post', username=username, post_id=post_id)
    return render(request, "new_post.html",
                  {'form': form, 'post': post})


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect('post', username=post.author.username, post_id=post_id)
    form = CommentForm()
    return render(request, 'post_view.html', {'post': post, 'form': form})


@login_required
def user_following(request):
    authors = request.user.follower.all().values("author")
    post_list = Post.objects.filter(author__in=authors)
    paginator, page = pagination(request, post_list)
    return render(request, "follow.html",
                  {'page': page,
                   'paginator': paginator})


@login_required
def profile_follow(request, username):
    profile_to_follow = get_object_or_404(User, username=username)
    if request.user != profile_to_follow:
        Follow.objects.get_or_create(
            user=request.user, author=profile_to_follow)
    return redirect("profile", username=username)


@login_required
def profile_unfollow(request, username):
    profile_to_unfollow = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user).filter(
        author=profile_to_unfollow).delete()
    return redirect("profile", username=username)
