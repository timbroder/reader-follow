{% load cache %} {% autoescape on %} {% cache 86400 comments article.id %}
var html = '{% for comment in comment_list %}<p>{{ comment.user.username }} <em>({{ comment.submit_date }})</em></p><p>{{ comment.comment }}</p>{% endfor %}';
$('.{{ sha }}').find('.entry-comments').html(html);
{% endcache %}
{% endautoescape %}