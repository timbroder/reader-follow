from django.contrib.syndication.views import Feed, FeedDoesNotExist
from models import *
from django.shortcuts import get_object_or_404

class UsersSharedFeed(Feed):
    def get_object(self, request, email):
        return get_object_or_404(UserProfile, user__email=email)
    
    def title(self, obj):
        return "%s's shared items" % obj.user.username

    def link(self, obj):
        return obj.get_absolute_url()
    
    def description(self, obj):
        return "Shared on Google Reader"

    def items(self, obj):
        return obj.articles.all()[:30]
    
