from django.conf.urls.defaults import patterns, include, url
import settings
from django.contrib import admin
admin.autodiscover()

from articles import views as articles

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    
    (r'^follow/(?P<email>.+)/$', articles.follow),
    (r'^unfollow/(?P<email>.+)/$', articles.unfollow),
    
    (r'^post/$', articles.post),
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