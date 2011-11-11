from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Article(models.Model):
    title = models.CharField(max_length=255, unique=True)
    url = models.URLField()
    body = models.TextField()
    published_on = models.DateTimeField()
    users = models.ManyToManyField(User)
    
    def __unicode__(self):
        return self.url