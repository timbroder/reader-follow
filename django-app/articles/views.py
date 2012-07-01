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
from django.utils.decorators import method_decorator

#debug = getattr(settings, 'DEBUG', None)

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

        
class DebugView(TemplateView, SharingDebug):
    def __init__(self, *args, **kwargs):
        super(DebugView, self).__init__(*args, **kwargs)
        self.get_debug()
        


#{
#    "url": "http: //www.google.com",
#    "body": "mybody",
#    "published_on": "Nov 1, 2011 2:24 PM",
#    "title": "my_title",
#    "auth": "021cf1a61bd8a2e1b1bc108932110340"
#}
class PostView(DebugView, Entry):
    def get(self, request):
        #if request.method != 'POST':
        #    return HttpResponseNotFound('<h1>expecting post</h1>')
        #data = simplejson.loads(request.raw_post_data)
        data = request.GET
        is_invalid = self.invalid_post(data)
        if is_invalid:
            return HttpResponse("0")
            
        try:
            article = Article.objects.get(url = data['url'])
        except Article.DoesNotExist:
            published_on = self.convert_publish_date(data['published_on'])
            article = Article(url = data['url'], 
                              body = data['body'], 
                              published_on = published_on, 
                              title = data['title']
                              )
            article.save()
          
        try:
            profile = UserProfile.objects.get(auth_key=data['auth'])
        except Exception as e:
            logout(request)
            logging.error('bad auth key', exc_info=True, extra={'request': request, 'exception': e})
            return NottyResponse('Bad auth key')
    
        if not self.share_article(article, profile):
            return NottyResponse("Already shared") 
        else:
            return NottyResponse("Shared: %s" % article.title)
        
    def convert_publish_date(self, in_string):
        return datetime.datetime.now()
        in_string = in_string.split(" (")[0]
        in_format = "%b %d, %Y" # %I:%M %p"
        out_format = "%b %d, %Y %I:%M %p"
        in_converted = time.strptime(in_string,in_format)
        out_converted = time.strftime("%Y-%m-%d %H:%M", in_converted)
        return out_converted
    
    def invalid_post(self, data):
        tests = ['url', 'body', 'published_on', 'title']
        return self.test_invalids(data, tests)

class ShareView(DebugView, Entry):
    def get(self, request):
        #if request.method != 'POST':
        #    return HttpResponseNotFound('<h1>expecting post</h1>')
        #data = simplejson.loads(request.raw_post_data)
        data = request.GET
        is_invalid = self.invalid_share(data)
        article = None
        if is_invalid:
            return HttpResponse("0")
            
        spinner_off = " jQuery('.spinner-%s').css({'opacity':'0'});" % data['sha']
          
        try:
            profile = UserProfile.objects.get(auth_key=data['auth'])
        except:
            logout(request)
            logging.error("bad auth key", exc_info=True, extra={'request': request })
            return NottyResponse('Bad auth key, please check readersharing.net', spinner_off)
    
        try:
            (article, backup) = self.get_entry_data(request, data['url'], data['auth'], data['sha'])
        except Article.DoesNotExist as e:
            logging.error("share article - %s" % profile.user.username, exc_info=True, extra={'request': request, 'exception': e})
            return NottyResponse("Not shared yet, fix this", spinner_off)
        
        if isinstance(article, NottyResponse):
            self.debug("ShareView.get :: %s" % backup)
            if backup is not None:
                if not self.share_article(backup, profile):
                    return NottyResponse("Already shared", spinner_off)
                else:
                    self.debug("ShareView.get :: returning artnot?")
                    self.debug("ShareView.get :: %s" % article.__class__)
                    return article
                    
            logging.error("share article - %s" % profile.user.username, exc_info=True, extra={'request': request })
            return article
    
        if not self.share_article(article, profile):
            return NottyResponse("Already shared", spinner_off)
        else:
            return NottyResponse("Shared: %s" % re.sub(r'\W+', ' ', article.title), spinner_off)
        
        return HttpResponse("1")
    

    def invalid_share(self, data):
        tests = ['url', 'auth']
        return self.test_invalids(data, tests)

class ShareComments(Invalids):
    def get_comments(self, article, data, flush_cache=False):
        user = UserProfile.objects.get(auth_key=data['auth']).user
        variables = ["comment_cache_%s-%s" % (article.id, user.id),]
        hash = md5_constructor(u':'.join([urlquote(var) for var in variables]))
        cache_key = variables #'template.cache.%s.%s' % ('commentson', hash.hexdigest())
        if flush_cache:
            cache.delete(cache_key)
        self.debug("ShareComments.get_comments :: get comments cache key %s" % cache_key)
        comments = cache.get(cache_key)
        if not comments:
            self.debug("ShareComments.get_comments :: user %s" % user)
            
            following = Follow.objects.filter(user=user)
            self.debug("ShareComments.get_comments :: following %s" % following)
            
            followed = Follow.objects.filter(target_user=user)
            self.debug("ShareComments.get_comments :: followed %s" % followed)
            
            users = [follow.target for follow in following]
            self.full_debug("ShareComments.get_comments :: users", users)
            
            users.extend([follow.user for follow in followed])
            users.append(user)
            self.full_debug("ShareComments.get_comments :: users2", users)
            #users = self.f5(users)
            articleType = ContentType.objects.get(app_label="articles", model="article")
            comments = Comment.objects.select_related('user').filter(user__in=users, content_type=articleType, object_pk=article.id, is_removed=False)
            self.full_debug("ShareComments.get_comments :: set comments cache key %s" % cache_key)
            cache.set(cache_key, comments, 86400)
            self.debug("ShareComments.get_comments :: not comments")
            self.debug("ShareComments.get_comments :: following %s" % following)
            self.debug("ShareComments.get_comments :: users %s" % users)
            self.debug("ShareComments.get_comments :: cache get by key %s" % cache.get(cache_key))
        else:
            self.debug("ShareComments.get_comments :: have comments")
        
        return { 'article': article, 'comment_list': comments, 'sha': data['sha'] }

    def add_comment(self, request, article, profile, c):
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
    
    def commenets_email(self, request, article, comments, by, when):
        if waffle.flag_is_active(request, 'commentemail'):
            users = []
            for comment in comments:
                if comment.user not in users and comment.user != request.user:
                    users.append(comment.user)
            emails = [user.email for user in users]
                
            html_msg = """
            <p><a href="%s">%s</a> commented on an article in Google Reader<br>
            <a href="http://readersharing.net/comment/on/%s/">%s</a></p>
            <p>Comment: %s</p>
            <p>Continue the conversation: <a href="http://readersharing.net/comment/on/%s/">http://readersharing.net/comment/on/%s/</a><br>
            Commented at: %s</p>
            """
            
            text_msg = """
            %s commented on an article in Google Reader
            Article: %s
            
            Comment: %s
            
            Continue the conversation: http://readersharing.net/comment/on/%s/
           
            Commented at: %s
            """
            
            subject = "Comment on: %s"
            
            #send_mail(subject % article.title, 
            #           #text_msg % (by.userprofile.get_absolute_url(), by.username, article.id, article.title, comment.comment, article.id, article.id, when.strftime('%a, %b %d %Y %H:%M')), 
            #          text_msg % (by.username, article.title, comment.comment, article.id, when.strftime('%a, %b %d %Y %H:%M')), 
            #          'follow@readersharing.net',
            #          emails, 
            #          fail_silently=False)
            
            msg = EmailMultiAlternatives(subject % article.title, 
                                         text_msg % (by.username, article.title, comment.comment, article.id, when.strftime('%a, %b %d %Y %H:%M')), 
                                         'Reader Sharing <readersharing@readersharing.net>',
                                         emails)
            self.debug("ShareComments.comments_email :: by %s" % by)
            
            html_msg = html_msg % (comment.user.userprofile.get_absolute_url(), by.username, article.id, article.title, comment.comment, article.id, article.id, when.strftime('%a, %b %d %Y %H:%M'))
            self.debug("ShareComments.comments_email :: html %s" % html_msg)
            msg.attach_alternative(html_msg, 
                                   "text/html")
            msg.send()
            
    def invalid_comment(self, data):
        tests = ['url', 'auth', 'comment']
        return self.test_invalids(data, tests)
    
    def invalid_comments(self, data):
        tests = ['url', 'sha']
        return self.test_invalids(data, tests)
    
    def f5(self, seq, idfun=None): 
       # order preserving
       if idfun is None:
           def idfun(x): return x
       seen = {}
       result = []
       for item in seq:
           marker = idfun(item)
           # in old Python versions:
           # if seen.has_key(marker)
           # but in new ones:
           if marker in seen: continue
           seen[marker] = 1
           result.append(item)
       return result

class CommentsView(DebugView, ShareComments):
    def get(self, request):
        data = request.GET
        is_invalid = self.invalid_comments(data)
        if is_invalid:
            return HttpResponse("0")
        try:
            article = Article.objects.get(url = data['url'])
        except Article.DoesNotExist:
            return HttpResponse("0")
    
        return render_to_response('comments.js', self.get_comments(article, data))

class CommentOnView(DebugView, ShareComments):
    @method_decorator(login_required(login_url='/login/google-oauth2/'))
    @csrf_protect
    def get(self, request, article_id):
        profile = request.user.userprofile
        article = get_object_or_404(Article, id=article_id)
        data = { 'sha': None }
        c = self.get_comments(article, data)
        c.update(csrf(request))
        
        if request.method == 'POST':
            comment = request.POST['comment']
            comment = self.add_comment(request, article, profile, comment)
            
            self.commenets_email(request, article, c['comment_list'], request.user, comment.submit_date)
    
        return render_to_response('add_comment.html', c)
    
class CommentView(DebugView, ShareComments, Entry):  
    def get(self, request):
        data = request.GET
        is_invalid = self.invalid_comment(data)
        if is_invalid:
            return HttpResponse("0")
        
        remove_spinner = " jQuery('.spinner-%s').remove();" % data['sha']
        
        try:
            article, backup = self.get_entry_data(request, data['url'], data['auth'], data['sha'])
        except Article.DoesNotExist as e:
            logging.error("comment, unshared article", exc_info=True, extra={'request': request, 'exception': e})
            return NottyResponse("Not shared yet, fix this", remove_spinner)
    
        if isinstance(article, NottyResponse):
            logging.error("comment", exc_info=True, extra={'request': request })
            article = backup
            #return article
        
        if not Article:
            logging.error("comment, no article", exc_info=True, extra={'request': request })
            return NottyResponse("There was an error", remove_spinner)
            
        try:
            profile = UserProfile.objects.get(auth_key=data['auth'])
        except Exception as e:
            logging.info("bad auth key", exc_info=True, extra={'request': request, 'exception': e})
            return NottyResponse('Bad auth key, please check readersharing.net', remove_spinner)
        
        self.share_article(article, profile)
        comment = self.add_comment(request, article, profile, data['comment'])
        
        #show updated comments
        comments = self.get_comments(article, data, True)
        tmpl = loader.get_template('comments.js')
        rendered = tmpl.render(Context(comments)) + remove_spinner
        
        self.commenets_email(request, article, comments['comment_list'], request.user, comment.submit_date)
        
        return NottyResponse("Comment Added", rendered)

class GetArticleView(DebugView):
    def get(self, request, article_id):
        article = get_object_or_404(Article, id = article_id)
        data = serializers.serialize("json", [article, ])
        return HttpResponse(data)



class HomeView(TemplateView, Contacts):
    def get(self, request):
        #logging.info('test', exc_info=True, extra={'request': request,})
        return self.contacts(request)

class SessionExpiresView(DebugView):
    def get(self, request):
        self.debug("SessionExpiresView.get :: EXPIRE")
        request.session.set_expiry(900)
        return redirect('/')


#make current user follow
class FollowView(TemplateView, Subscribe):
    @method_decorator(login_required(login_url='/login/google-oauth2/'))
    def get(self, request, email):
        user = request.user
        
        following, created = User.objects.get_or_create(email=email)
        if created:
            following.username = email
            following.save()
        
        utils.follow(user, following)
        
        subscribed = self.reader_subscribe(request, email)
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
                      'Reader Sharing <readersharing@readersharing.net>',
                      [following.email], 
                      fail_silently=False)
        messages.success(request, "Followed %s" % email)    
        return redirect('/')

class UnfollowView(DebugView):
    @method_decorator(login_required(login_url='/login/google-oauth2/'))
    def get(self, request, email):
        user = request.user
        
        following, created = User.objects.get_or_create(email=email)
        if created:
            following.username = email
            following.save()
        
        try:
            utils.unfollow(user, following)
        except:
            pass
        
        messages.success(request, "Unfollowed %s" % email)    
        return redirect('/')

class FollowAllView(TemplateView, Subscribe):
    @method_decorator(login_required(login_url='/login/google-oauth2/'))
    def get(self, request):
 
        following = Follow.objects.filter(user=request.user)
        for usr in following:
            email = usr.target.email
            self.reader_subscribe(request, email)
        
        return redirect('/')
    
    
