from django.db import models
from django.contrib.auth.models import User
from social_auth.models import UserSocialAuth
from follow import utils
import simplejson
from django.http import HttpResponse

# Create your models here.
class Article(models.Model):
    title = models.CharField(max_length=255)
    url = models.URLField(unique=True, max_length=255)
    
    #his really should join o a domain object, don't care atm
    domain = models.URLField(blank=True, null=True)
    google_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    body = models.TextField()
    published_on = models.DateTimeField()
    users = models.ManyToManyField(User)
    
    def __unicode__(self):
        return self.url
    
    def get_absolute_url(self):
        return self.url
    
class UserProfile(models.Model):
    user = models.OneToOneField(User)
    auth_key = models.CharField(max_length=64, unique=True)
    is_signed_up = models.BooleanField(default=False)
    social_auth = models.ForeignKey('social_auth.UserSocialAuth', blank=True, null=True)
    articles = models.ManyToManyField(Article, through='Shared')
    
    def __unicode__(self):
        return self.user.username
    
    def assoc_social(self):
        try:
            social = UserSocialAuth.objects.get(uid=self.user.email)
            self.social_auth = social
        except:
            self.social_auth = None
        self.save()
    
	def get_domain_url(self):
		site = Site.objects.get(id=settings.SITE_ID)
		return "http://%s/" % site.domain
    
    def get_absolute_url(self):
        return "%sshared/%s/" % (self.get_domain_url(), self.user.email)
    
    def get_agg_share_url(self):
        return "%sfeed/%s/%s/" % (self.get_domain_url(), self.user.email, self.auth_key)

class Shared(models.Model):
    article = models.ForeignKey(Article)
    userprofile = models.ForeignKey(UserProfile)
    shared_on = models.DateTimeField()
    
    class Meta:
        ordering = ["-shared_on"]
    
    def __unicode__(self):
        return "%s - %s" % (self.userprofile, self.article)
  
class GoogleContact:
    name = ''
    email = ''
    user_id = -1
    
    def __init__(self, name, email):
        try:
            self.name = name.lower()
        except:
            self.name = name
        if not self.name or self.name == '':
            self.name = 'N/A'
        self.email = email
    
    def __unicode__(self):
        return "%s <%s>" % (self.name, self.email)
    
    def __str__(self):
        return self.__unicode__()


class NottyResponse(HttpResponse):
    notty = "jQuery.notty({ content : '%s', timeout: 3000 });"
    def __init__(self, data, extra=None):
        data = self.notty % (data)
        if extra:
            data = "%s %s" % (data, extra)
        HttpResponse.__init__( self, data,
                               mimetype='application/json'
                               )

class JsonpResponse(HttpResponse):
    def __init__(self, data):
        json = simplejson.dumps(data)
        jsonp = "jQuery(%s)" % (json)
        HttpResponse.__init__( self, jsonp,
                               mimetype='application/json'
                               )
    
utils.register(User)    

import signals
import feeds