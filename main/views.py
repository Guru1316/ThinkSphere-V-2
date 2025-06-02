from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404
from .models import User, Subsphere, Post, Comment, Vote
from .forms import (
    RegisterForm, LoginForm, SubsphereForm,
    PostForm, CommentForm, ProfileForm
)
from django.core.files.storage import default_storage
from django.db.models import Q
from mongoengine import DoesNotExist
from django.http import HttpResponseRedirect
from django.urls import reverse
from mongoengine.queryset.visitor import Q

# Custom 404 function for MongoDB
def get_object_or_404(model, **kwargs):
    obj = model.objects(**kwargs).first()
    if not obj:
        raise Http404
    return obj

# --- AUTH VIEWS ---
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            if User.objects(email=form.cleaned_data['email']).first():
                messages.error(request, "Email already registered")
            else:
                user = User(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email']
                )
                user.set_password(form.cleaned_data['password'])
                user.save()
                messages.success(request, "Registration successful! Please log in.")
                return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

def login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = User.objects(email=form.cleaned_data['email']).first()
            if user and user.check_password(form.cleaned_data['password']):
                request.session['user_id'] = str(user.id)
                request.session['username'] = user.username
                return redirect('home')
            else:
                messages.error(request, "Invalid email or password")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout(request):
    request.session.flush()
    return redirect('login')

# --- HOME & PROFILE ---

def home(request):
    username = request.session.get('username')
    try:
        subspheres = Subsphere.objects.all()
        recent_posts = Post.objects().order_by('-created_at')[:10]
    except Exception as e:
        messages.error(request, f"Database error: {str(e)}")
        subspheres = []
        recent_posts = []
    
    return render(request, 'home.html', {
        'username': username,
        'subspheres': subspheres,
        'recent_posts': recent_posts
    })

def profile(request, username):
    try:
        user = User.objects.get(username=username)
        posts = Post.objects(created_by=user).order_by('-created_at')
        
        if request.session.get('user_id') == str(user.id):
            if request.method == "POST":
                form = ProfileForm(request.POST, request.FILES)
                if form.is_valid():
                    user.username = form.cleaned_data['username']
                    user.email = form.cleaned_data['email']
                    
                    if 'profile_image' in request.FILES:
                        profile_image = request.FILES['profile_image']
                        filename = default_storage.save(profile_image.name, profile_image)
                        user.profile_image = filename
                    
                    user.save()
                    messages.success(request, "Profile updated!")
                    return redirect('profile', username=user.username)
            else:
                form = ProfileForm(initial={
                    'username': user.username,
                    'email': user.email
                })
        else:
            form = None

        return render(request, 'profile.html', {
            'profile_user': user,
            'posts': posts,
            'joined_subspheres': user.joined_subspheres,
            'form': form
        })
    except DoesNotExist:
        messages.error(request, "User not found")
        return redirect('home')

# --- SUBSPHERE VIEWS ---

def create_subsphere(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Login required")
        return redirect('login')

    try:
        user = User.objects.get(id=user_id)
    except DoesNotExist:
        messages.error(request, "User not found")
        return redirect('login')

    if request.method == "POST":
        form = SubsphereForm(request.POST)
        if form.is_valid():
            subsphere = Subsphere(
                name=form.cleaned_data['name'],
                description=form.cleaned_data['description'],
                created_by=user
            )
            subsphere.save()
            
            # Add creator as first member
            subsphere.members.append(user)
            subsphere.save()
            
            # Add to user's joined subspheres
            user.joined_subspheres.append(subsphere)
            user.save()
            
            messages.success(request, "Subsphere created and joined!")
            return redirect('subsphere_detail', subsphere_id=str(subsphere.id))
    else:
        form = SubsphereForm()
    return render(request, 'create_subsphere.html', {'form': form})

def edit_subsphere(request, subsphere_id):
    user = User.objects(id=request.session.get('user_id')).first()
    subsphere = Subsphere.objects(id=subsphere_id).first()
    if not subsphere or subsphere.created_by != user:
        messages.error(request, "Not authorized or subsphere not found")
        return redirect('subsphere_list')

    if request.method == "POST":
        form = SubsphereForm(request.POST, instance=subsphere)
        if form.is_valid():
            subsphere.name = form.cleaned_data['name']
            subsphere.description = form.cleaned_data['description']
            subsphere.save()
            messages.success(request, "Subsphere updated!")
            return redirect('subsphere_detail', subsphere_id=subsphere_id)
    else:
        form = SubsphereForm(initial={
            'name': subsphere.name,
            'description': subsphere.description
        })
    return render(request, 'edit_subsphere.html', {'form': form, 'subsphere': subsphere})

def delete_subsphere(request, subsphere_id):
    user = User.objects(id=request.session.get('user_id')).first()
    subsphere = Subsphere.objects(id=subsphere_id).first()
    if subsphere and subsphere.created_by == user:
        for member in subsphere.members:
            if subsphere in member.joined_subspheres:
                member.joined_subspheres.remove(subsphere)
                member.save()
        subsphere.delete()
        messages.success(request, "Subsphere deleted!")
    else:
        messages.error(request, "Not authorized or subsphere not found")
    return redirect('subsphere_list')

def subsphere_list(request):
    subspheres = Subsphere.objects()
    return render(request, 'subsphere_list.html', {'subspheres': subspheres})

def subsphere_detail(request, subsphere_id):
    try:
        subsphere = Subsphere.objects.get(id=subsphere_id)
        posts = Post.objects(subsphere=subsphere).order_by('-created_at')
        
        user_id = request.session.get('user_id')
        is_member = False
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                is_member = user in subsphere.members
            except DoesNotExist:
                pass
                
        return render(request, 'subsphere_detail.html', {
            'subsphere': subsphere,
            'posts': posts,
            'is_member': is_member
        })
    except DoesNotExist:
        messages.error(request, "Subsphere not found")
        return redirect('subsphere_list')

def join_subsphere(request, subsphere_id):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Login required")
        return redirect('login')

    try:
        user = User.objects.get(id=user_id)
        subsphere = Subsphere.objects.get(id=subsphere_id)
        
        if user not in subsphere.members:
            subsphere.members.append(user)
            subsphere.save()
            
            if subsphere not in user.joined_subspheres:
                user.joined_subspheres.append(subsphere)
                user.save()
            
            messages.success(request, f"You joined {subsphere.name}")
        else:
            messages.info(request, f"You're already a member of {subsphere.name}")
            
        return redirect('subsphere_detail', subsphere_id=subsphere_id)
    except DoesNotExist:
        messages.error(request, "Subsphere or user not found")
        return redirect('subsphere_list')

def leave_subsphere(request, subsphere_id):
    user = User.objects(id=request.session.get('user_id')).first()
    subsphere = Subsphere.objects(id=subsphere_id).first()
    if user and subsphere and user in subsphere.members:
        subsphere.members.remove(user)
        subsphere.save()
        if subsphere in user.joined_subspheres:
            user.joined_subspheres.remove(subsphere)
            user.save()
        messages.success(request, f"You left {subsphere.name}")
    return redirect('subsphere_list')

# --- POST VIEWS ---

def create_post(request, subsphere_id):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Login required")
        return redirect('login')

    try:
        subsphere = Subsphere.objects.get(id=subsphere_id)
        user = User.objects.get(id=user_id)
        
        if user not in subsphere.members:
            messages.error(request, "You must join the subsphere first")
            return redirect('subsphere_detail', subsphere_id=subsphere_id)

        if request.method == "POST":
            form = PostForm(request.POST, request.FILES)
            if form.is_valid():
                post = Post(
                    title=form.cleaned_data['title'],
                    content=form.cleaned_data['content'],
                    created_by=user,
                    subsphere=subsphere
                )
                
                if 'image' in request.FILES:
                    image_file = request.FILES['image']
                    filename = default_storage.save(image_file.name, image_file)
                    post.image = filename
                
                post.save()
                messages.success(request, "Post created successfully!")
                return redirect('subsphere_detail', subsphere_id=subsphere_id)
        else:
            form = PostForm()
            
        return render(request, 'create_post.html', {
            'form': form,
            'subsphere': subsphere
        })
    except DoesNotExist:
        messages.error(request, "Subsphere not found")
        return redirect('subsphere_list')

def edit_post(request, post_id):
    post = Post.objects(id=post_id).first()
    user = User.objects(id=request.session.get('user_id')).first()
    if not post or post.created_by != user:
        messages.error(request, "Not authorized or post not found")
        return redirect('home')

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post.title = form.cleaned_data['title']
            post.content = form.cleaned_data['content']
            image_file = request.FILES.get('image')
            if image_file:
                image_filename = default_storage.save(image_file.name, image_file)
                post.image = image_filename
            post.save()
            messages.success(request, "Post updated!")
            return redirect('post_detail', post_id=post_id)
    else:
        form = PostForm(initial={
            'title': post.title,
            'content': post.content
        })
    return render(request, 'edit_post.html', {'form': form, 'post': post})

def delete_post(request, post_id):
    post = Post.objects(id=post_id).first()
    user = User.objects(id=request.session.get('user_id')).first()
    if post and post.created_by == user:
        post.delete()
        messages.success(request, "Post deleted!")
    else:
        messages.error(request, "Not authorized or post not found")
    return redirect('home')

def post_detail(request, post_id):
    post = Post.objects(id=post_id).first()
    if not post:
        messages.error(request, "Post not found")
        return redirect('home')
    
    # Get top-level comments (no parent)
    comments = Comment.objects(post=post, parent_comment=None).order_by('created_at')
    
    # For each comment, get its replies
    for comment in comments:
        comment.replies = Comment.objects(post=post, parent_comment=comment).order_by('created_at')
    
    user = User.objects(id=request.session.get('user_id')).first()
    
    # Check if user is a member of the subsphere
    is_member = False
    if user and post.subsphere:
        is_member = user in post.subsphere.members
    
    return render(request, 'post_detail.html', {
        'post': post,
        'comments': comments,
        'user': user,
        'is_member': is_member,
    })

# --- COMMENT VIEWS ---

def add_comment(request, post_id, parent_comment_id=None):
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            post = get_object_or_404(Post, id=post_id)
            user = get_object_or_404(User, id=request.session.get('user_id'))
            
            if parent_comment_id:
                parent_comment = get_object_or_404(Comment, id=parent_comment_id)
                comment = Comment.objects.create(
                    content=content,
                    created_by=user,
                    post=post,
                    parent_comment=parent_comment
                )
            else:
                comment = Comment.objects.create(
                    content=content,
                    created_by=user,
                    post=post
                )
            
            # Correct way to redirect with fragment identifier
            redirect_url = reverse('post_detail', kwargs={'post_id': post_id}) + f'#comment-{comment.id}'
            return HttpResponseRedirect(redirect_url)
    
    # Fallback redirect if something goes wrong
    return redirect('post_detail', post_id=post_id)

def edit_comment(request, comment_id):
    comment = Comment.objects(id=comment_id).first()
    user = User.objects(id=request.session.get('user_id')).first()
    if not comment or comment.created_by != user:
        messages.error(request, "Not authorized or comment not found")
        return redirect('home')

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment.content = form.cleaned_data['content']
            comment.save()
            messages.success(request, "Comment updated!")
            return redirect('post_detail', post_id=str(comment.post.id))
    else:
        form = CommentForm(initial={'content': comment.content})
    return render(request, 'edit_comment.html', {'form': form, 'comment': comment})

def delete_comment(request, comment_id):
    comment = Comment.objects(id=comment_id).first()
    user = User.objects(id=request.session.get('user_id')).first()
    
    if comment and comment.created_by == user:
        post_id = str(comment.post.id)
        comment.delete()
        messages.success(request, "Comment deleted!")
        return redirect('post_detail', post_id=post_id)
    else:
        messages.error(request, "Not authorized or comment not found")
        return redirect('home')

# --- VOTING VIEWS ---

def vote_post(request, post_id, vote_type):
    user = User.objects(id=request.session.get('user_id')).first()
    post = Post.objects(id=post_id).first()
    if not user or not post:
        messages.error(request, "Invalid request.")
        return redirect('home')

    existing_vote = Vote.objects(user=user, post=post).first()
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            existing_vote.delete()
            if vote_type == 'upvote':
                post.upvotes -= 1
            else:
                post.downvotes -= 1
        else:
            existing_vote.vote_type = vote_type
            existing_vote.save()
            if vote_type == 'upvote':
                post.upvotes += 1
                post.downvotes -= 1
            else:
                post.downvotes += 1
                post.upvotes -= 1
    else:
        Vote(user=user, post=post, vote_type=vote_type).save()
        if vote_type == 'upvote':
            post.upvotes += 1
        else:
            post.downvotes += 1
    post.save()
    return redirect('post_detail', post_id=post_id)

def vote_comment(request, comment_id, vote_type):
    comment = get_object_or_404(Comment, id=comment_id)
    user = get_object_or_404(User, id=request.session.get('user_id'))
    
    # Your existing voting logic here...
    
    # Correct way to redirect with fragment identifier
    redirect_url = reverse('post_detail', kwargs={'post_id': str(comment.post.id)}) + f'#comment-{comment.id}'
    return HttpResponseRedirect(redirect_url)

# --- SEARCH & FILTER ---

def search(request):
    query = request.GET.get('q', '').strip()
    posts = []
    users = []
    subspheres = []
    if query:
        posts = Post.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )
        users = User.objects.filter(username__icontains=query)
        subspheres = Subsphere.objects.filter(name__icontains=query)
    return render(request, 'search_results.html', {
        'query': query,
        'posts': posts,
        'users': users,
        'subspheres': subspheres,
    })

def filter_posts(request):
    keyword = request.GET.get('keyword', '')
    subsphere_id = request.GET.get('subsphere_id', '')
    author = request.GET.get('author', '')
    sort = request.GET.get('sort', 'newest')
    
    posts = Post.objects.all()
    
    # Apply filters
    if keyword:
        posts = posts.filter(Q(title__icontains=keyword) | Q(content__icontains=keyword))
    
    if subsphere_id:
        posts = posts.filter(subsphere=subsphere_id)
    
    if author and author != 'None':
        posts = posts.filter(author=author)
    
    # Apply sorting
    if sort == 'newest':
        posts = posts.order_by('-created_at')
    elif sort == 'oldest':
        posts = posts.order_by('created_at')
    elif sort == 'top':
        posts = posts.order_by('-votes')
    
    context = {
        'posts': posts,
        'keyword': keyword,
        'subsphere_id': subsphere_id,
        'author': author,
        'sort': sort,
    }
    
    return render(request, 'filter_posts.html', context)