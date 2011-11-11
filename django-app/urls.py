from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from articles import views as articles

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    
    (r'^post/$', articles.post),
    (r'^get/(?P<article_id>\d+)/$', articles.get),
)
