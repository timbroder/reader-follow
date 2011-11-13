from django.db import models
from django.contrib.auth.models import User
from social_auth.models import UserSocialAuth
from follow import utils

# Create your models here.
class Article(models.Model):
    title = models.CharField(max_length=255, unique=True)
    url = models.URLField()
    body = models.TextField()
    published_on = models.DateTimeField()
    users = models.ManyToManyField(User)
    
    def __unicode__(self):
        return self.url
    
class UserProfile(models.Model):
    user = models.OneToOneField(User)
    auth_key = models.CharField(max_length=64, unique=True)
    is_signed_up = models.BooleanField(default=False)
    social_auth = models.ForeignKey('social_auth.UserSocialAuth', blank=True, null=True)
    
    def __unicode__(self):
        return self.user.username
    
    def assoc_social(self):
        try:
            social = UserSocialAuth.objects.get(uid=self.user.email)
            self.social_auth = social
        except:
            self.social_auth = None
        self.save()
    
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
    
utils.register(User)    

import signals