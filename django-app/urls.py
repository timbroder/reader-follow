from django.conf.urls.defaults import patterns, include, url
import settings
from django.contrib import admin
admin.autodiscover()

from articles import views as articles
from articles import feeds

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    (r'^comments/', include('django.contrib.comments.urls')),
    
    (r'^follow/(?P<email>.+)/$', articles.follow),
    (r'^unfollow/(?P<email>.+)/$', articles.unfollow),
    (r'^shared/(?P<email>.+)/$', feeds.UsersSharedFeed()),
    (r'^feed/(?P<email>.+)/(?P<auth_key>.+)/$', feeds.FollowingFeed()),
    
    (r'^post/$', articles.post),
    (r'^share/$', articles.share),
    (r'^comment/on/(?P<article_id>.+)/$', articles.comment_on),
    (r'^comment/$', articles.comment),
    (r'^comments/$', articles.comments),
    (r'^get/(?P<article_id>\d+)/$', articles.get),
    url(r'', include('social_auth.urls')),
    url('^', include('follow.urls')),
    (r'^$', articles.home),
)

print settings.MEDIA_ROOT

urlpatterns = urlpatterns + patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT }),
    )