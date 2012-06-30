from django.conf.urls.defaults import patterns, include, url
import settings
from django.contrib import admin
admin.autodiscover()

from articles import feeds
from articles.views import FollowAllView, SessionExpiresView, FollowView, UnfollowView, HomeView, PostView, ShareView
from articles.views import CommentOnView, CommentView, CommentsView, GetArticleView

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    (r'^comments/', include('django.contrib.comments.urls')),
    
    (r'^follow/all/$', FollowAllView.as_view()),
    (r'^accounts/expire/$', SessionExpiresView.as_view()),
    (r'^follow/(?P<email>.+)/$', FollowView.as_view()),
    (r'^unfollow/(?P<email>.+)/$', UnfollowView.as_view()),
    (r'^shared/(?P<email>.+)/$', feeds.UsersSharedFeed()),
    (r'^feed/(?P<email>.+)/(?P<auth_key>.+)/$', feeds.FollowingFeed()),
    
    (r'^post/$', PostView.as_view()),
    (r'^share/$', ShareView.as_view()),
    (r'^comment/on/(?P<article_id>.+)/$', CommentOnView.as_view()),
    (r'^comment/$', CommentView.as_view()),
    (r'^comments/$', CommentsView.as_view()),
    (r'^get/(?P<article_id>\d+)/$', GetArticleView.as_view()),
    url(r'', include('social_auth.urls')),
    url('^', include('follow.urls')),
    (r'^$', HomeView.as_view()),
)

print settings.MEDIA_ROOT

urlpatterns = urlpatterns + patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT }),
    )