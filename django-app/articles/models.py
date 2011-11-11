from django.db import models

# Create your models here.
class Article(models.Model):
    title = models.CharField(max_length=255, unique=True)
    url = models.URLField()
    body = models.TextField()
    published_on = models.DateTimeField()
    
    def __unicode__(self):
        return self.url