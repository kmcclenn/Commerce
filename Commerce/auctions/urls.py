from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("new", views.new_listing, name="new_listing"),
    path("listings/<str:listing_id>", views.listing, name="listing"),
    path("watchlist/<str:listing_id>", views.add_to_watchlist, name="add_to_watchlist"),
    path("bid/<str:listing_id>", views.bid, name="bid"),
    path("watchlist", views.view_watchlist, name="view_watchlist"),
    path("comment/<str:listing_id>", views.comment, name="comment"),
    path("close_listing/<str:listing_id>", views.close_listing, name="close_listing"),
    path("categories", views.categories, name="categories"),
    path("categories/<str:category_name>", views.specific_category, name="specific_category")
]
