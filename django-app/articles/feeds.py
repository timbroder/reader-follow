from django.contrib.syndication.views import Feed, FeedDoesNotExist
from models import *
from django.shortcuts import get_object_or_404
from follow import utils
from follow.models import Follow

class ArticleFeed(Feed):
    def item_title(self, item):
        return item.title
    
    def item_link(self, item):
        return item.url
    
    def item_description(self, item):
        return item.body

class UsersSharedFeed(ArticleFeed):
    def get_object(self, request, email):
        return get_object_or_404(UserProfile, user__email=email)
    
    def title(self, obj):
        return "%s's shared items" % obj.user.username

    def link(self, obj):
        return obj.get_absolute_url()
    
    def description(self, obj):
        return "Shared on Google Reader"
    
    def items(self, obj):
        return obj.articles.all()[:100]
    
class FollowingFeed(ArticleFeed):
    def get_object(self, request, email, auth_key):
        return get_object_or_404(UserProfile, auth_key=auth_key, user__email=email)
    
    def title(self, obj):
        return "Following on Google Reader (by %s)" % obj.user.username

    def link(self, obj):
        return obj.get_agg_share_url()
    
    def description(self, obj):
        return "Following on Google Reader"
    
    def item_title(self, item):
        return item.article.title
    
    def item_link(self, item):
        return item.article.url
    
    def item_description(self, item):
        return item.article.body
    
    def item_pubdate(self, item):
        item.shared_on
        
    def items(self, obj):
        following = Follow.objects.filter(user=obj)
        following = [user.target.get_profile() for user in following]
        shared = Shared.objects.filter(userprofile__in=following).order_by('-shared_on')[:100]
        return shared