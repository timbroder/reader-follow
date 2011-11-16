from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in

from django.dispatch import receiver
from django.contrib.auth.models import User
from articles.models import UserProfile
import random, string
from social_auth.models import UserSocialAuth

def random_md5like_hash():
    available_chars= string.hexdigits[:16]
    return ''.join(
        random.choice(available_chars)
        for dummy in xrange(32))

@receiver(post_save, sender=User)
def gen_auth_key(sender, instance, created, **kwargs):
    user=instance
    
    if created:
        UserProfile.objects.create(user=user)
      
    profile = user.get_profile()
    if not profile:
        profile = UserProfile()
    
    if not profile.auth_key:
        new_key = random_md5like_hash()

        while UserProfile.objects.filter(auth_key=new_key).count() > 0:
            new_key = random_md5like_hash()
        profile.auth_key = new_key
    
    profile.assoc_social()
    
    profile.save()
    

    
#@receiver(post_save, sender=UserSocialAuth)
#def assoc_social(sender, instance, created, **kwargs):
#    print 'social'
        
@receiver(user_logged_in)
def set_signed_up(sender, user, request, **kwargs):
    profile = user.get_profile()
    if not profile.is_signed_up:
        profile.is_signed_up = True
        profile.save()
        
