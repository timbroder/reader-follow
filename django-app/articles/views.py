from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.core import serializers
from django.utils import simplejson 
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import get_object_or_404, render_to_response as r2r
from django.template import RequestContext, Context
from django.utils.encoding import smart_unicode
from django.views.decorators.cache import cache_page
import datetime
import settings
import time
from models import *
from django.views.decorators.csrf import csrf_exempt
from social_auth.models import UserSocialAuth
#from pprint import pprint
from gdata.contacts import service, client
from follow import utils
from follow.models import Follow
from django.shortcuts import redirect
import json 

debug = getattr(settings, 'DEBUG', None)

#def dump(obj):
#    '''return a printable representation of an object for debugging'''
#    newobj=obj
#    if '__dict__' in dir(obj):
#        newobj=obj.__dict__
#        if ' object at ' in str(obj) and not newobj.has_key('__type__'):
#            newobj['__type__']=str(obj)
#        for attr in newobj:
#            newobj[attr]=dump(newobj[attr])
#    return newobj

def invalid_post(data):
    invalid = ''
    tests = ['url', 'body', 'published_on', 'title']
    
    for test in tests:
        if test not in data:
            invalid = "%s %s," % (invalid, test)
        
    if invalid != '':
        return "Error: missing" + invalid.strip(',')
    return None

def convert_publish_date(in_string):
    return datetime.datetime.now()
    in_string = in_string.split(" (")[0]
    in_format = "%b %d, %Y" # %I:%M %p"
    out_format = "%b %d, %Y %I:%M %p"
    in_converted = time.strptime(in_string,in_format)
    out_converted = time.strftime("%Y-%m-%d %H:%M", in_converted)
    return out_converted

#{
#    "url": "http: //www.google.com",
#    "body": "mybody",
#    "published_on": "Nov 1, 2011 2:24 PM",
#    "title": "my_title",
#    "auth": "021cf1a61bd8a2e1b1bc108932110340"
#}
@csrf_exempt
def post(request):
    #if request.method != 'POST':
    #    return HttpResponseNotFound('<h1>expecting post</h1>')
    #data = simplejson.loads(request.raw_post_data)
    data = request.GET
    is_invalid = invalid_post(data)
    if is_invalid:
        return HttpResponse("0")
        
    try:
        article = Article.objects.get(url = data['url'])
    except Article.DoesNotExist:
        published_on = convert_publish_date(data['published_on'])
        article = Article(url = data['url'], 
                          body = data['body'], 
                          published_on = published_on, 
                          title = data['title']
                          )
        article.save()
      
    try:
        profile = UserProfile.objects.get(auth_key=data['auth'])
    except:
        return HttpResponse('bad auth key')

    try:
        shared = Shared.objects.get(article=article,
                        userprofile=profile
                        )
        #already shared
        return HttpResponse('already shared')
    except Exception as e:
        shared = Shared(article=article,
                        userprofile=profile,
                        shared_on=datetime.datetime.now()
                        )
        shared.save()
    return HttpResponse("shared: %s" % article.title)
    
    
def get(request, article_id):
    article = get_object_or_404(Article, id = article_id)
    data = serializers.serialize("json", [article, ])
    return HttpResponse(data)

def print_contacts(contacts):
    for contact in contacts:
        print contact

def get_contacts(user):
    auth = UserSocialAuth.objects.get(user=user)
    gd_client = service.ContactsService()
    gd_client.debug = 'true'
    gd_client.SetAuthSubToken(auth.extra_data['access_token'])
    #feed = gd_client.GetContactsFeed()
    #for i, entry in enumerate(feed.entry):
    #    print '\n%s %s' % (i+1, entry)
    
    #uri = "%s?updated-min=2007-03-16T00:00:00&max-results=500&orderby=lastmodified&sortorder=descending" % gd_client.GetFeedUri()
    contacts = []
    entries = []
    uri = "%s?updated-min=2007-03-16T00:00:00&max-results=500&q=gmail.com" % gd_client.GetFeedUri()
    feed = gd_client.GetContactsFeed(uri)
    next_link = feed.GetNextLink()
    entries.extend(feed.entry)
    
    while next_link:
        feed = gd_client.GetContactsFeed(uri=next_link.href)
        entries.extend(feed.entry)
        next_link = feed.GetNextLink()
    for entry in entries:
        for email in entry.email:
            if email.primary and email.address and entry.title:
                #if 'gmail.com' in email.address:
                contact = GoogleContact(entry.title.text, email.address)
                contacts.append(contact)    
        #print 'Updated on %s' % contact.updated.text
    contacts = sorted(contacts, key=lambda k: k.name) 
    
    return contacts

def contacts(request):
    user = request.user
    if not user.is_authenticated():
        return r2r('login.html', {})
    else:
        if request.session.get('google_contacts_cached'):
            contacts = request.session.get('google_contacts_cached')
        else:
            contacts = get_contacts(user)
            request.session['google_contacts_cached'] = contacts
            
        contact_emails = [contact.email for contact in contacts]
        
        signed_up = User.objects.filter(userprofile__is_signed_up = True, userprofile__social_auth__uid__in = contact_emails)
        signed_up_emails = [usr.email for usr in signed_up]
        
        following = Follow.objects.filter(user=user)
        for f in Follow.objects.all():
            print f.target
        following_emails = [usr.target.email for usr in following]

        return r2r('index.html', { 'contacts': contacts,
                                   'signed_up_emails': signed_up_emails,
                                   'following_emails': following_emails,
                                   'user': user })
    
def home(request):
    return contacts(request)

#make current user follow
def follow(request, email):
    user = request.user
    
    following, created = User.objects.get_or_create(email=email)
    if created:
        following.username = email
        following.save()
    
    utils.follow(user, following)
        
    return redirect('/')

def unfollow(request, email):
    user = request.user
    
    following, created = User.objects.get_or_create(email=email)
    if created:
        following.username = email
        following.save()
    
    try:
        utils.unfollow(user, following)
    except:
        pass
        
    return redirect('/')
    
    
    