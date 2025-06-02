from django.urls import path
from . import views

urlpatterns = [
    # User Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),

    # Home & Profile
    path('', views.home, name='home'),
    path('profile/<str:username>/', views.profile, name='profile'),

    # Subsphere routes
    path('subspheres/', views.subsphere_list, name='subsphere_list'),
    path('subspheres/create/', views.create_subsphere, name='create_subsphere'),
    path('subspheres/<str:subsphere_id>/', views.subsphere_detail, name='subsphere_detail'),
    path('subspheres/<str:subsphere_id>/edit/', views.edit_subsphere, name='edit_subsphere'),
    path('subspheres/<str:subsphere_id>/delete/', views.delete_subsphere, name='delete_subsphere'),
    path('subspheres/<str:subsphere_id>/join/', views.join_subsphere, name='join_subsphere'),
    path('subspheres/<str:subsphere_id>/leave/', views.leave_subsphere, name='leave_subsphere'),

    # Post routes
    path('subspheres/<str:subsphere_id>/posts/create/', views.create_post, name='create_post'),
    path('posts/<str:post_id>/', views.post_detail, name='post_detail'),
    path('posts/<str:post_id>/edit/', views.edit_post, name='edit_post'),
    path('posts/<str:post_id>/delete/', views.delete_post, name='delete_post'),

    # Comment routes
    path('posts/<str:post_id>/comment/', views.add_comment, name='add_comment'),
    path('posts/<str:post_id>/comment/<str:parent_comment_id>/', views.add_comment, name='add_reply'),
    path('comments/<str:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path('comments/<str:comment_id>/delete/', views.delete_comment, name='delete_comment'),

    # Voting routes
    path('posts/<str:post_id>/vote/<str:vote_type>/', views.vote_post, name='vote_post'),
    path('comments/<str:comment_id>/vote/<str:vote_type>/', views.vote_comment, name='vote_comment'),

    # Search & Filter
    path('search/', views.search, name='search'),
    path('filter/', views.filter_posts, name='filter_posts'),
]