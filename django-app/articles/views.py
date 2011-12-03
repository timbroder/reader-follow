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
from gdata.contacts import service, client
import gdata
from follow import utils
from follow.models import Follow
from django.shortcuts import redirect
import json 
import waffle
from django.core.mail import send_mail
from django.contrib.comments import Comment
from django.contrib.contenttypes.models import ContentType
from django.utils.hashcompat import md5_constructor
from django.utils.http import urlquote
from django.core.cache import cache
from BeautifulSoup import BeautifulSoup as Soup
from urllib2 import Request, urlopen
import urllib
from django.template import loader, Context

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

def dump(obj):
  '''return a printable representation of an object for debugging'''
  newobj=obj
  if '__dict__' in dir(obj):
    newobj=obj.__dict__
    if ' object at ' in str(obj) and not newobj.has_key('__type__'):
      newobj['__type__']=str(obj)
    for attr in newobj:
      newobj[attr]=dump(newobj[attr])
  return newobj

def test_invalids(data, tests):
    invalid = ''
    for test in tests:
        if test not in data:
            invalid = "%s %s," % (invalid, test)
        
    if invalid != '':
        return "Error: missing" + invalid.strip(',')
    return None

def invalid_post(data):
    tests = ['url', 'body', 'published_on', 'title']
    return test_invalids(data, tests)

def invalid_share(data):
    tests = ['url', 'auth']
    return test_invalids(data, tests)
    
def invalid_comment(data):
    tests = ['url', 'auth', 'comment']
    return test_invalids(data, tests)

def invalid_comments(data):
    tests = ['url', 'sha']
    return test_invalids(data, tests)

def convert_publish_date(in_string):
    return datetime.datetime.now()
    in_string = in_string.split(" (")[0]
    in_format = "%b %d, %Y" # %I:%M %p"
    out_format = "%b %d, %Y %I:%M %p"
    in_converted = time.strptime(in_string,in_format)
    out_converted = time.strftime("%Y-%m-%d %H:%M", in_converted)
    return out_converted

def share_article(article, profile):
    try:
        shared = Shared.objects.get(article=article,
                        userprofile=profile
                        )
        #already shared
        return False
        #return JsonpResponse("alert('already shared');")
    except Exception as e:
        shared = Shared(article=article,
                        userprofile=profile,
                        shared_on=datetime.datetime.now()
                        )
        shared.save()
        return True
#{
#    "url": "http: //www.google.com",
#    "body": "mybody",
#    "published_on": "Nov 1, 2011 2:24 PM",
#    "title": "my_title",
#    "auth": "021cf1a61bd8a2e1b1bc108932110340"
#}
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
        return NottyResponse('bad auth key')

    if not share_article(article, profile):
        return NottyResponse("already shared") 
    else:
        return NottyResponse("shared: %s" % article.title)

def get_entry_data(request, url):
    get_id_url = "https://www.google.com/reader/api/0/search/items/ids?q=%s" % url
    get_entry_url = "https://www.google.com/reader/api/0/stream/items/contents?freshness=false&client=reader-follow&i=%s"
    try:
        article = Article.objects.get(url=url)
        return article
    except:
        article = Article()
    
    auth = UserSocialAuth.objects.get(user=User.objects.get(id=10))
    gd_client = service.ContactsService()
    gd_client.debug = 'true'
    gd_client.SetAuthSubToken(auth.extra_data['access_token'])

    search = gd_client.Get(get_id_url)
    soup = Soup(search.__str__())
    entry_id = soup.findAll('number')[0].text
    get_entry_url = get_entry_url % entry_id
    entry = gd_client.Get(get_entry_url, converter=str) 
    json = simplejson.loads(entry.__str__())

    try:
        article.domain = json['alternate'][0]['href']
    except:
        #print 'error on href'
        pass
    
    item = json['items'][0]
    try:
        article.google_id = item['id']
    except:
        #print 'error on item id'
        pass
    
    #shitty
    try:
        article.body = item['summary']['content']
    except:
        try: 
            article.body = item['content']['content']
        except:
            pass
        
    try:
        article.title = item['title']
        article.published_on = datetime.datetime.fromtimestamp(int(item['published'])).strftime('%Y-%m-%d %H:%M:%S')
        article.url = url
        article.save()
        return article
    except Exception:
        raise
        #print 'catastrophic error'
        #print Exception
        return None
    

def share(request):
    #if request.method != 'POST':
    #    return HttpResponseNotFound('<h1>expecting post</h1>')
    #data = simplejson.loads(request.raw_post_data)
    data = request.GET
    is_invalid = invalid_share(data)
    article = None
    if is_invalid:
        return HttpResponse("0")
        
    try:
        article = get_entry_data(request, data['url'])
    except Article.DoesNotExist:
        return NottyResponse("not shared yet, fix this")
      
    try:
        profile = UserProfile.objects.get(auth_key=data['auth'])
    except:
        return NottyResponse('bad auth key')

    if not share_article(article, profile):
        return NottyResponse("already shared") 
    else:
        return NottyResponse("shared: %s" % article.title)
    
    return HttpResponse("1")

def get_comments(article, data):

    
    articleType = ContentType.objects.get(app_label="articles", model="article")
    comments = Comment.objects.select_related('user').filter(content_type=articleType, object_pk=article.id, is_removed=False)
    
    return { 'article': article, 'comment_list': comments, 'sha': data['sha'] }

def comments(request):
    data = request.GET
    is_invalid = invalid_comments(data)
    if is_invalid:
        return HttpResponse("0")
    try:
        article = Article.objects.get(url = data['url'])
    except Article.DoesNotExist:
        return HttpResponse("0")

    return r2r('comments.js', get_comments(article, data))
    
def comment(request):
    data = request.GET
    is_invalid = invalid_comment(data)
    if is_invalid:
        return HttpResponse("0")
    
    try:
        article = get_entry_data(request, data['url'])
    except Article.DoesNotExist:
        return NottyResponse("not shared yet, fix this")
    
    if not Article:
        return NottyResponse("there was an error")
        
    try:
        profile = UserProfile.objects.get(auth_key=data['auth'])
    except:
        return NottyResponse('bad auth key')
    
    share_article(article, profile)
    
    variables = [article.id,] 
    hash = md5_constructor(u':'.join([urlquote(var) for var in variables]))
    cache_key = 'template.cache.%s.%s' % ('comments', hash.hexdigest())
    cache.delete(cache_key)
    
    comment = Comment();
    comment.ip_address = request.META.get("REMOTE_ADDR", None)
    comment.user = profile.user
    comment.comment = data['comment']
    comment.content_type = ContentType.objects.get(app_label="articles", model="article")
    comment.object_pk = article.id
    comment.site = Site.objects.get(id=1)
    comment.save()
    
    #show updated comments
    comments = get_comments(article, data)
    tmpl = loader.get_template('comments.js')
    rendered = tmpl.render(Context(comments)) + " $('.spinner-%s').remove();" % data['sha']
    
    return NottyResponse("Comment Added", rendered)

def get(request, article_id):
    article = get_object_or_404(Article, id = article_id)
    data = serializers.serialize("json", [article, ])
    return HttpResponse(data)

def print_contacts(contacts):
    for contact in contacts:
        print contact

#lazy, make class based view
def check_email(email):
    nope = ['facebook.com', 'aol.com']
    for no in nope:
        if no in email:
            return False
    
    return True

def refresh_token(auth):
    token = gdata.gauth.OAuth2Token(client_id = getattr(settings, 'GOOGLE_OAUTH2_CLIENT_ID'),
                                     client_secret = getattr(settings, 'GOOGLE_OAUTH2_CLIENT_SECRET'),
                                     scope = ' '.join(getattr(settings, 'GOOGLE_OAUTH_EXTRA_SCOPE', [])),
                                     user_agent = 'reader-follow', 
                                     access_token = auth.extra_data['access_token'], 
                                     refresh_token = auth.extra_data['refresh_token'])
    body = urllib.urlencode({
                             'grant_type': 'refresh_token',
                             'client_id': token.client_id,
                             'client_secret': token.client_secret,
                             'refresh_token' : token.refresh_token
                             })
    headers = { 'user-agent': token.user_agent, }
    request = Request(token.token_uri, data=body, headers=headers)
    response = simplejson.loads(urlopen(request).read())
    auth.extra_data['access_token'] = response['access_token']
    auth.save()
    return auth

def get_contacts(user):
    auth = UserSocialAuth.objects.get(user=user)
    client = service.ContactsService()
    client.debug = 'true'
    
    client.SetAuthSubToken(auth.extra_data['access_token'])
    #uri = "%s?updated-min=2007-03-16T00:00:00&max-results=500&orderby=lastmodified&sortorder=descending" % gd_client.GetFeedUri()
    contacts = []
    entries = []
    #uri = "%s?updated-min=2007-03-16T00:00:00&max-results=500&q=gmail.com" % gd_client.GetFeedUri()

    try:
        feed = client.GetContactsFeed()
    except Exception as e:
        if 'Token invalid' in e.args[0]['reason']:
            auth = refresh_token(auth)
            client.SetAuthSubToken(auth.extra_data['access_token'])
            feed = client.GetContactsFeed()
            
    next_link = feed.GetNextLink()
    entries.extend(feed.entry)
    
    while next_link:
        feed = client.GetContactsFeed(uri=next_link.href)
        entries.extend(feed.entry)
        next_link = feed.GetNextLink()
    for entry in entries:
        for email in entry.email:
            if email.primary and email.address and entry.title:
                if check_email(email.address):
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
            #request.session['google_contacts_cached'] = contacts
            
        contact_emails = [contact.email for contact in contacts]
        
        signed_up = User.objects.filter(userprofile__is_signed_up = True, userprofile__social_auth__uid__in = contact_emails)
        signed_up_emails = [usr.email for usr in signed_up]
        
        following = Follow.objects.filter(user=user)

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
    
    if waffle.flag_is_active(request, 'followemail'):
        msg = """
        Remember when Google removed following and sharing from reader?  Do you want them back?
        It's easy! Check out http://readersharing.net
        
        %s is now following you on Google Reader
        
        Login to follow them back!
        """
        
        subject = "%s is now following you on Google Reader"
        send_mail(subject % user.username, 
                  msg % user.username, 
                  'follow@readersharing.net',
                  [following.email], 
                  fail_silently=False)
        
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
    
    
    