from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.core import serializers
from django.utils import simplejson 
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import get_object_or_404, render_to_response
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
from django.contrib.auth import authenticate, login, logout
import re, string
from django.core.mail import EmailMultiAlternatives
from view_cache_utils import cache_page_with_prefix
from django.utils.hashcompat import md5_constructor
import httplib
from django.db import IntegrityError
from django.views.generic.base import TemplateView
from classes import *

class SharingDebug:
    def __init__(self, *args, **kwargs):
        self.debug_enabled = False
        self.full_debug_enabled = False
        self.get_debug()
    
    def get_debug(self):
        self.debug_enabled = getattr(settings, 'DEBUG', False)
        self.full_debug_enabled = getattr(settings, 'DEBUG', False)
        
    def debug(self, str):
        if self.debug_enabled:
            print str
    
    def full_debug(self, str, obj=None):
        if obj == None:
            return self.debug(str)
        if self.debug_enabled:
            print str
            print obj
            
class Invalids:    
    def test_invalids(self, data, tests):
        invalid = ''
        for test in tests:
            if test not in data:
                invalid = "%s %s," % (invalid, test)
            
        if invalid != '':
            return "Error: missing" + invalid.strip(',')
        return None

class Token(SharingDebug):
    def refresh_token(self, auth):
        self.debug("REFRESH TOKEN")
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
    
class Contacts(SharingDebug, Token):
    def print_contacts(self, contacts):
        for contact in contacts:
            self.debug("Contacts.print_contacts :: %s" % contact)
            
    def get_contacts(self, user):
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
                auth = self.refresh_token(auth)
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
                    if self.check_email(email.address):
                        contact = GoogleContact(entry.title.text, email.address)
                        contacts.append(contact)    
            #self.debug("Contacts.get_contacts :: 'Updated on %s'") % contact.updated.text
        contacts = sorted(contacts, key=lambda k: k.name) 
        
        return contacts

    def check_email(self, email):
        nope = ['facebook.com', 'aol.com']
        for no in nope:
            if no in email:
                return False
        
        return True

    def contacts(self, request):
        user = request.user
        if not user.is_authenticated():
            return render_to_response('login.html', {})
        else:
            if request.session.get('google_contacts_cached'):
                contacts = request.session.get('google_contacts_cached')
            else:
                contacts = self.get_contacts(user)
                request.session['google_contacts_cached'] = contacts
                
            contact_emails = [contact.email for contact in contacts]
            
            signed_up = User.objects.filter(userprofile__is_signed_up = True, userprofile__social_auth__uid__in = contact_emails)
            signed_up_emails = [usr.email for usr in signed_up]
            
            following = Follow.objects.filter(user=user)
    
            following_emails = [usr.target.email for usr in following]
    
            return render_to_response('index.html', { 'contacts': contacts,
                                       'signed_up_emails': signed_up_emails,
                                       'following_emails': following_emails,
                                       'user': user,
                                       #'messages': messages
                                    }, context_instance=RequestContext(request))
            
class Entry(Token, Invalids):
    def share_article(self, article, profile):
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
        
    def get_entry_data(self, request, url, auth_key, sha=None):
        get_id_url = "https://www.google.com/reader/api/0/search/items/ids?q=%s" % url
        get_entry_url = "https://www.google.com/reader/api/0/stream/items/contents?freshness=false&client=reader-follow&i=%s"
        find_feed_url = "https://www.google.com/reader/api/0/feed-finder?q=%s" % url
        get_feed_url = "http://www.google.com/reader/atom/feed/%s?n=100"
        get_entry_url_full = ""
        if sha:
            spinner_off = " jQuery('.spinner-%s').css({'opacity':'0'});" % sha
        else:
            spinner_off = ''
        
        self.debug("Entry.get_entry_data :: trying to get url: %s" % url)
            
        try:
            article = Article.objects.get(lookup_url=url)
            self.debug('Entry.get_entry_data :: got article')
                
            return article, None
        except:
            self.debug('Entry.get_entry_data :: didn\'t get article')
            article = Article()
            article.lookup_url = url
        
        try:
            profile = UserProfile.objects.get(auth_key=auth_key)
            auth = UserSocialAuth.objects.get(user=profile.user)
        except Exception as e:
            logging.error('there seems to be an error with your auth key or account', exc_info=True, extra={'request': request, 'exception': e})
            return NottyResponse("There seems to be an error with your auth key or account", spinner_off), None
    
        gd_client = service.ContactsService()
        gd_client.debug = 'true'
        gd_client.SetAuthSubToken(auth.extra_data['access_token'])
    
        try:
            search = gd_client.Get(get_id_url)
        except Exception as e:
            try:
                if True: #'Token invalid' in e.args[0]['reason'] or True:
                    logging.info("refreshing token - %s" % profile.user.username, exc_info=True, extra={'request': request, 'exception': e })
                    auth = self.refresh_token(auth)
                    gd_client.SetAuthSubToken(auth.extra_data['access_token'])
                    search = gd_client.Get(get_id_url)
            except Exception as ee:
                logging.error("token refresh1 - %s" % profile.user.username, exc_info=True, extra={'request': request, 'exception': ee})
                return NottyResponse("Auth problems. admin notified, will fix soon!", spinner_off), None
        
        
        try:
            self.debug("Entry.get_entry_data :: TRY SEARCH1 %s" % get_id_url)
            soup = Soup(search.__str__())
            
            entry_id = soup.findAll('number')[0].text
            get_entry_url_full = get_entry_url % entry_id
        except:
            try:
                found = False
                self.debug("Entry.get_entry_data :: TRY SEARCH2a %s" % find_feed_url)
                find = gd_client.Get(find_feed_url)
                soup = Soup(find.__str__())
                
                self.full_debug("Entry.get_entry_data :: Soup", soup)
                    
                links = soup.findAll('ns0:link')
                for link in links:
                    if link['rel'] == 'self':
                        continue
                    found = False
                    get_feed_url = get_feed_url % link['href']
                    
                    self.debug("Entry.get_entry_data :: TRY SEARCH2b %s" % get_feed_url)

                    continuation = ''
                    found = False
                    dammit = 0
                    for i in range (1,2):
                        if found:
                            break
                        rss = gd_client.Get("%s%s" % (get_feed_url,  continuation))
                        #self.full_debug("Entry.get_entry_data :: rss", rss)
                        entries = Soup(rss.__str__())
                        try:
                            continuation =  "&c=%s" % entries.findAll('ns2:continuation')[0].contents[0]
                        except:
                            continuation = ''
                          #  break
                        #self.full_debug("Entry.get_entry_data :: entries", entries)
                        #continue
                        #for entry in entries.findAll('ns0:id', { 'ns2:original-id': True }):
                         #   self.full_debug("Entry.get_entry_data :: entry", entry)
                            #if url in entry['ns2:original-id']:
                        #        found = True
                        #        get_entry_url_full = get_entry_url % entry.contents[0]
                        #            break
                        #self.full_debug("Entry.get_entry_data :: entries.prettify", entries.prettify())
                        self.debug("Entry.get_entry_data :: url %s" % url)
                        if "feedproxy.google.com" in url:
                            self.debub('Entry.get_entry_data :: feed proxy')
                            request = urllib2.Request(url)
                            opener = urllib2.build_opener()
                            f = opener.open(request)
                            url = f.url.split("?")[0]
                            self.debug("Entry.get_entry_data :: url %s" % url)
                        for entry in entries.findAll('ns0:link', recursive=True): #, {'ns2:crawl-timestamp-msec': True}): #, { 'ns2:original-id': True }):
                            #self.debug('Entry.get_entry_data :: entry')
                            
                            #pass
                            if url in entry['href']:
                                self.debug("Entry.get_entry_data :: url %s" % url)
                                self.debug("Entry.get_entry_data :: 'in href?")
                                self.full_debug("Entry.get_entry_data :: entry.prettify()", entry.prettify())
                                self.debug("\n\n\n")
                                self.full_debug("Entry.get_entry_data :: entry.previousSibling.prettify()", entry.previousSibling.prettify())
                                self.debug("\n\n\n")
                                    
                                try:
                                    self.debug("Entry.get_entry_data :: 'ns2'")
                                    self.debug("Entry.get_entry_data :: prevSib %s" % entry.previousSibling.find('ns0:id', { 'ns2:original-id': True }).contents[0])
                                    
                                    get_entry_url_full = get_entry_url % entry.previousSibling.find('ns0:id', { 'ns2:original-id': True }).contents[0]
                                    found = True
                                except:
                                    self.debug("Entry.get_entry_data :: 'ns1'")
                                    self.debug("Entry.get_entry_data :: prevSib %s" % entry.previousSibling.find('ns0:id', { 'ns1:original-id': True }).contents[0])
                                    
                                    get_entry_url_full = get_entry_url % entry.previousSibling.find('ns0:id', { 'ns1:original-id': True }).contents[0]
                                    found = True
                                
                                break
                                #found = True
                               # self.debug("Entry.get_entry_data :: %s" % entry['href'])
                                #self.debug(entry.find('ns0:id'))
                            #self.debug(entry.prettify())
                            #self.debug(entry.text)
                            dammit = dammit + 1
                           # if dammit > 8:
                                
                                #break
                        #         self.debug('YAY')
                        #        self.debug(entry.find('ns0:id'))
                                #found = True
                                 #get_entry_url_full = get_entry_url % entry.find('ns0:id')
                        #        break
                           # self.debug(entry.findAll('ns0:link'))
                           # self.debug(entry.findAll('ns1:link'))
                           # self.debug(entry.findAll('ns2:link'))
                            #if url in entry['ns2:original-id']:
                            #    found = True
                            #    get_entry_url_full = get_entry_url % entry.contents[0]
                               # break
                        self.debug("Entry.get_entry_data :: ANOTHER LOOP")
                        #for entry in entries.findAll('entry'):
                         #   self.full_debug("", entry)
                else:
                    if not found:
                        article.title = url
                        article.published_on = datetime.datetime.now()
                        article.url = url
                        article.save()
                        logging.error("article search - %s" % profile.user.username, exc_info=True, extra={'request': request })
                        return NottyResponse("There was an error finding this in Google Reader\'s Database. We've shared the url so your friends can see it. The Admin has been notified", spinner_off), article
            except Exception as e:
                self.debug("Entry.get_entry_data :: 'Error on search'")
    
                article.title = url
                article.published_on = datetime.datetime.now()
                article.url = url
                article.save()
                logging.error("article search - %s" % profile.user.username, exc_info=True, extra={'request': request, 'exception': e})
                return NottyResponse("There was an error finding this in Google Reader\'s Database. We've shared the url so your friends can see it. The Admin has been notified", spinner_off), article
        
        try:
            self.debug("Entry.get_entry_data :: GET ARTICLE %s" % get_entry_url_full)
                
            entry = gd_client.Get(get_entry_url_full, converter=str)
        except Exception as e:
            self.debug("Entry.get_entry_data :: TOKEN REFRESH2")
            try:
                if True: #'Token invalid' in e.args[0]['reason'] or True:
                    logging.info("refreshing token - %s" % profile.user.username, exc_info=True, extra={'request': request, 'exception': e })
                    auth = self.refresh_token(auth)
                    gd_client.SetAuthSubToken(auth.extra_data['access_token'])
                    entry = gd_client.Get(get_entry_url_full, converter=str)
            except Exception as ee:
                self.full_debug("Entry.get_entry_data :: ", ee)
                logging.error("token refresh3 - %s" % profile.user.username, exc_info=True, extra={'request': request, 'exception': ee})
                return NottyResponse("Auth problems. admin notified, will fix soon!", spinner_off), None
            
        self.debug("Entry.get_entry_data :: %s" % get_entry_url_full)            
        json = simplejson.loads(entry.__str__())
    
        try:
            article.domain = json['alternate'][0]['href']
        except:
            #self.debug("Entry.get_entry_data :: error on href)
            pass
        
        item = json['items'][0]
        try:
            article.google_id = item['id']
        except:
            #self.debug("Entry.get_entry_data :: error on item id)
            pass
        
        #shitty
        try:
            self.debug("Entry.get_entry_data :: TRYING BODY1")
            article.body = item['summary']['content'].encode("utf-8")
        except Exception as e:
            self.full_debug("Entry.get_entry_data :: ", e)
            try: 
                self.debug("Entry.get_entry_data :: TRYING BODY2")
                article.body = item['content']['content'].encode("utf-8")
            except Exception as e:
                if debug:
                    self.full_debug("Entry.get_entry_data :: ", e) 
                    self.debug("Entry.get_entry_data :: FAILED BODY")
                pass
            
        try:
            article.title = item['title']
            article.published_on = datetime.datetime.fromtimestamp(int(item['published'])).strftime('%Y-%m-%d %H:%M:%S')
            article.url = url
            try:
                article.save()
            except IntegrityError:
                article = Article.objects.get(url=article.url)
            return article, None
        except Exception:
            raise
            if debug:
                self.full_debug("Entry.get_entry_data :: 'catastrophic error'", Exception)
            return None, None
        
class ShareCache(SharingDebug):
    def cache_map(request):
        key = md5_constructor("comment_cache_%s-%s" % (request.get_full_path(), request.user.id)).hexdigest()
        self.debug(key)
        return key
    
class Subscribe(SharingDebug):
    def reader_subscribe(self, request, email):
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
            if debug:
                self.debug("Subscribe.reader_subscribe :: dead on token")
                self.debug("Subscribe.reader_subscribe :: %s " % e.code)
                self.debug("Subscribe.reader_subscribe :: %s " % e.hdrs)
                self.debug("Subscribe.reader_subscribe :: %s " % e.read())
        
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
            if debug:
                self.debug("Subscribe.reader_subscribe :: BAD BAD add")
                self.debug("Subscribe.reader_subscribe :: %s" % e.code)
                self.debug("Subscribe.reader_subscribe :: %s" % e.hdrs)
                self.debug("Subscribe.reader_subscribe :: %s" % e.read())
        resp_str = "%s" % response.read()
        json = simplejson.loads(resp_str)
        if json['numResults'] == 0 or json['numResults'] == '0':
            messages.success(request, "Reader has not been able to crawl %s's feed, please try again later." % email)
        else:
            messages.success(request, "Successfully added %s's shared feed to reader" % email)
        
        return None