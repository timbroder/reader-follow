from django.db import models

# Create your models here.
class Article(models.Model):
    title = models.CharField(max_length=255)
    url = models.URLField()
    body = models.TextField()
    published_on = models.DateTimeField()