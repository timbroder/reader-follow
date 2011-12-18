from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.core import serializers
from django.utils import simplejson 
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import get_object_or_404, render_to_response as r2r
from django.template import RequestContext, Context, loader
from django.utils.encoding import smart_unicode
from django.views.decorators.cache import cache_page
import datetime
import settings
import time
from models import *
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from social_auth.models import UserSocialAuth
from gdata.contacts import service, client
from gdata.docs import data
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
import urllib, urllib2
from django.core.context_processors import csrf
from django.utils.html import escape
import logging
from django.contrib import messages

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
    except Exception as e:
        logging.error('bad auth key', exc_info=True, extra={'request': request, 'exception': e})
        return NottyResponse('bad auth key')

    if not share_article(article, profile):
        return NottyResponse("already shared") 
    else:
        return NottyResponse("shared: %s" % article.title)

def get_entry_data(request, url, auth_key, sha=None):
    get_id_url = "https://www.google.com/reader/api/0/search/items/ids?q=%s" % url
    get_entry_url = "https://www.google.com/reader/api/0/stream/items/contents?freshness=false&client=reader-follow&i=%s"
    find_feed_url = "https://www.google.com/reader/api/0/feed-finder?q=%s" % url
    get_feed_url = "http://www.google.com/reader/atom/feed/%s?n=200"
    if sha:
        spinner_off = " jQuery('.spinner-%s').css({'opacity':'0'});" % sha
    else:
        spinner_off = ''
    
    try:
        article = Article.objects.get(url=url)
        return article
    except:
        article = Article()
    
    try:
        profile = UserProfile.objects.get(auth_key=auth_key)
        auth = UserSocialAuth.objects.get(user=profile.user)
    except Exception as e:
        logging.error('there seems to be an error with your auth key or account', exc_info=True, extra={'request': request, 'exception': e})
        return NottyResponse("there seems to be an error with your auth key or account", spinner_off)

    gd_client = service.ContactsService()
    gd_client.debug = 'true'
    gd_client.SetAuthSubToken(auth.extra_data['access_token'])

    try:
        search = gd_client.Get(get_id_url)
    except Exception as e:
        try:
            if True: #'Token invalid' in e.args[0]['reason'] or True:
                logging.info("refreshing token - %s" % profile.user.username, exc_info=True, extra={'request': request, 'exception': e })
                auth = refresh_token(auth)
                gd_client.SetAuthSubToken(auth.extra_data['access_token'])
                search = gd_client.Get(get_id_url)
        except Exception as ee:
            logging.error("token refresh - %s" % profile.user.username, exc_info=True, extra={'request': request, 'exception': ee})
            return NottyResponse("auth problems. admin notified, will fix soon!", spinner_off) 
    
    
    try:
        if debug:
            print "TRY SEARCH1 %s" % get_id_url
        soup = Soup(search.__str__())
        
        entry_id = soup.findAll('number')[0].text
        get_entry_url_full = get_entry_url % entry_id
    except:
        try:
            if debug:
                print "TRY SEARCH2a %s" % find_feed_url
            find = gd_client.Get(find_feed_url)
            soup = Soup(find.__str__())
            links = soup.findAll('ns0:link')
            for link in links:
                if link['rel'] != 'self':
                    found = False
                    get_feed_url = get_feed_url % link['href']
                    
                    if debug:
                        print "TRY SEARCH2b %s" % get_feed_url
                    
                    
                    #print get_feed_url % link['href']
                    #print rss.__str__()
                    continuation = ''
                    found = False
                    for i in range (1,10):
                        if found:
                            break
                        rss = gd_client.Get("%s%s" % (get_feed_url,  continuation))
                        entries = Soup(rss.__str__())
                        try:
                            continuation =  "&c=%s" % entries.findAll('ns2:continuation')[0].contents[0]
                        except:
                            continuation = ''
                            break

                        for entry in entries.findAll('ns0:id', { 'ns2:original-id': True }):
                            if url in entry['ns2:original-id']:
                                found = True
                                get_entry_url_full = get_entry_url % entry.contents[0]
                                break
                    else:
                        if not found:
                            logging.error("article search - %s" % profile.user.username, exc_info=True, extra={'request': request })
                            return NottyResponse("there was an error finding this in reader. admin notified, will fix soon!", spinner_off)
        except Exception as e:
            if debug:
                print 'Error on search'
            logging.error("article search - %s" % profile.user.username, exc_info=True, extra={'request': request, 'exception': e})
            return NottyResponse("there was an error finding this in reader. admin notified, will fix soon!", spinner_off) 
    
    try:
        if debug:
            print "GET ARTICLE %s" % get_entry_url_full
            
        entry = gd_client.Get(get_entry_url_full, converter=str)
    except Exception as e:
        try:
            if True: #'Token invalid' in e.args[0]['reason'] or True:
                logging.info("refreshing token - %s" % profile.user.username, exc_info=True, extra={'request': request, 'exception': e })
                auth = refresh_token(auth)
                gd_client.SetAuthSubToken(auth.extra_data['access_token'])
                search = gd_client.Get(get_id_url)
        except Exception as ee:
            logging.error("token refresh - %s" % profile.user.username, exc_info=True, extra={'request': request, 'exception': ee})
            return NottyResponse("auth problems. admin notified, will fix soon!", spinner_off) 
        
            
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
        if debug:
            print "TRYING BODY1"
        article.body = item['summary']['content'].encode("utf-8")
    except Exception as e:
        if debug:
            print e
        try: 
            if debug:
                print "TRYING BODY2"
            article.body = item['content']['content'].encode("utf-8")
        except Exception as e:
            if debug:
                print e
                print "FAILED BODY"
            
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
        
    spinner_off = " jQuery('.spinner-%s').css({'opacity':'0'});" % data['sha']
      
    try:
        profile = UserProfile.objects.get(auth_key=data['auth'])
    except:
        logging.error("bad auth key", exc_info=True, extra={'request': request })
        return NottyResponse('bad auth key', spinner_off)

    try:
        article = get_entry_data(request, data['url'], data['auth'], data['sha'])
    except Article.DoesNotExist as e:
        logging.error("share article - %s" % profile.user.username, exc_info=True, extra={'request': request, 'exception': e})
        return NottyResponse("not shared yet, fix this", spinner_off)
    
    if isinstance(article, NottyResponse):
        logging.error("share article - %s" % profile.user.username, exc_info=True, extra={'request': request })
        return article

    if not share_article(article, profile):
        return NottyResponse("already shared", spinner_off)
    else:
        return NottyResponse("shared: %s" % article.title, spinner_off)
    
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

def add_comment(request, article, profile, c):
    variables = [article.id,] 
    hash = md5_constructor(u':'.join([urlquote(var) for var in variables]))
    cache_key = 'template.cache.%s.%s' % ('comments', hash.hexdigest())
    cache.delete(cache_key)
    cache_key = 'template.cache.%s.%s' % ('commenton', hash.hexdigest())
    cache.delete(cache_key)
    
    comment = Comment();
    comment.ip_address = request.META.get("REMOTE_ADDR", None)
    comment.user = profile.user
    comment.comment = c
    comment.content_type = ContentType.objects.get(app_label="articles", model="article")
    comment.object_pk = article.id
    comment.site = Site.objects.get(id=1)
    comment.save()
    
    return comment
    
def commenets_email(request, article, comments, by, when):
    if waffle.flag_is_active(request, 'commentemail'):
        users = []
        for comment in comments:
            if comment.user not in users and comment.user != request.user:
                users.append(comment.user)
        emails = [user.email for user in users]
            
        msg = """
        %s
        %s commented on an article in Google Reader
        
        %s
        
        Continue the conversation: http://readersharing.net/comment/on/%s/
       
        (%s)
        """
        
        subject = "Comment: %s"
        
        send_mail(subject % article.title, 
                  msg % (article.title, by.username, comment.comment, article.id, when), 
                  'follow@readersharing.net',
                  emails, 
                  fail_silently=False)

@login_required(login_url='/login/google-oauth2/')
@csrf_protect
def comment_on(request, article_id):
    profile = request.user.userprofile
    article = get_object_or_404(Article, id=article_id)
    data = { 'sha': None }
    c = get_comments(article, data)
    c.update(csrf(request))
    
    if request.method == 'POST':
        comment = request.POST['comment']
        comment = add_comment(request, article, profile, comment)
        
        commenets_email(request, article, c['comment_list'], request.user, comment.submit_date)

    return r2r('add_comment.html', c)
    
    
def comment(request):
    data = request.GET
    is_invalid = invalid_comment(data)
    if is_invalid:
        return HttpResponse("0")
    
    remove_spinner = " jQuery('.spinner-%s').remove();" % data['sha']
    
    try:
        article = get_entry_data(request, data['url'], data['auth'], data['sha'])
    except Article.DoesNotExist as e:
        logging.error("comment, unshared article", exc_info=True, extra={'request': request, 'exception': e})
        return NottyResponse("not shared yet, fix this", remove_spinner)

    if isinstance(article, NottyResponse):
        logging.error("comment", exc_info=True, extra={'request': request })
        return article
    
    if not Article:
        logging.error("comment, no article", exc_info=True, extra={'request': request })
        return NottyResponse("there was an error", remove_spinner)
        
    try:
        profile = UserProfile.objects.get(auth_key=data['auth'])
    except Exception as e:
        logging.info("bad auth key", exc_info=True, extra={'request': request, 'exception': e})
        return NottyResponse('bad auth key', remove_spinner)
    
    share_article(article, profile)
    comment = add_comment(request, article, profile, data['comment'])
    
    #show updated comments
    comments = get_comments(article, data)
    tmpl = loader.get_template('comments.js')
    rendered = tmpl.render(Context(comments)) + remove_spinner
    
    commenets_email(request, article, comments['comment_list'], request.user, comment.submit_date)
    
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
    if debug:
        print "REFRESH TOKEN"
    token = gdata.gauth.OAuth2Token(client_id = getattr(settings, 'GOOGLE_OAUTH2_CLIENT_ID'),
                                     client_secret = getattr(settings, 'GOOGLE_OAUTH2_CLIENT_SECRET'),
                                     scope = ' '.join(getattr(settings, 'GOOGLE_OAUTH_EXTRA_SCOPE', [])),
                                     user_agent = 'ReaderSharing.net', 
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
    uri = "%s?updated-min=2007-03-16T00:00:00&max-results=500&orderby=lastmodified&sortorder=descending" % client.GetFeedUri()
    contacts = []
    entries = []
    #uri = "%s?updated-min=2007-03-16T00:00:00&max-results=500&q=gmail.com" % gd_client.GetFeedUri()

    try:
        feed = client.GetContactsFeed(uri)
    except Exception as e:
        if 'Token invalid' in e.args[0]['reason'] or True:
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
        request.session.set_expiry(1680)
        if request.session.get('google_contacts_cached'):
            contacts = request.session.get('google_contacts_cached')
        else:
            contacts = get_contacts(user)
            request.session['google_contacts_cached'] = contacts
            
        contact_emails = [contact.email for contact in contacts]
        
        signed_up = User.objects.filter(userprofile__is_signed_up = True, userprofile__social_auth__uid__in = contact_emails)
        signed_up_emails = [usr.email for usr in signed_up]
        
        following = Follow.objects.filter(user=user)

        following_emails = [usr.target.email for usr in following]

        return r2r('index.html', { 'contacts': contacts,
                                   'signed_up_emails': signed_up_emails,
                                   'following_emails': following_emails,
                                   'user': user,
                                   #'messages': messages
                                }, context_instance=RequestContext(request))
    
def home(request):
    #logging.info('test', exc_info=True, extra={'request': request,})
    return contacts(request)

def reader_subscribe(request, email):
#quickadd_url = "https://www.google.com/reader/api/0/subscription/edit?ck=%s&client=scroll" % time.time()
    quickadd_url = "http://www.google.com/reader/api/0/subscription/quickadd?client=sscroll"
    auth = UserSocialAuth.objects.get(user=request.user)
    T = auth.extra_data['access_token']
    #T = "//0Jp3Tb13-1PQa0QqkRprMA"
    
    token_url = "https://www.google.com/reader/api/0/token?ck=%s&client=sscroll" % time.time()
    req = urllib2.Request(token_url)
    req.add_header('Authorization', 'Bearer %s' % T)
    
    try:
        response = urllib2.urlopen(req)
    except Exception as e:
        print 'dead on token'
        print e.code
        print e.hdrs
        print e.read()
    
    the_page = response.read()
    action_token = "%s" % the_page
    
    data = urllib.urlencode({
                            #'s': 'feed/http://readersharing.net/shared/timothy.broder@gmail.com/', 
                            # 'token': T,  
                            # 'T': T,  
                             #'ac': 'subscribe',
                             #'a': "user/-/label/sharetest", 
                             #'t': 'test'
                             
                             'quickadd':  "http://readersharing.net/shared/%s/" % email, 
                             'T': action_token, 
                             #'ac': 'subscribe',
    
                            })
    req = urllib2.Request(quickadd_url, data)
    req.add_header('Authorization', 'Bearer %s' % T)
    
    try:
        response = urllib2.urlopen(req)
    except Exception as e:
        print "BAD BAD add"
        print e.code
        print e.hdrs
        print e.read()
    resp_str = "%s" % response.read()
    json = simplejson.loads(resp_str)
    if json['numResults'] == 0 or json['numResults'] == '0':
        messages.success(request, "Reader has not been able to crawl %s's feed, please try again later." % email)
    else:
        messages.success(request, "Successfully added %s's shared feed to reader" % email)
    
    return None

#make current user follow
@login_required(login_url='/login/google-oauth2/')
def follow(request, email):
    
    
    user = request.user
    
    following, created = User.objects.get_or_create(email=email)
    if created:
        following.username = email
        following.save()
    
    utils.follow(user, following)
    
    
    subscribed = reader_subscribe(request, email)
    if isinstance(subscribed, HttpResponse):
        return subscribed
    else:
        #notify
        pass
    
    
    
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

@login_required(login_url='/login/google-oauth2/')
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


@login_required(login_url='/login/google-oauth2/')
def followall(request):
    following = Follow.objects.filter(user = request.user)
    for usr in following:
        email = usr.target.email
        reader_subscribe(request, email)
    
    return redirect('/')
    
    
