{% load cache %} {% autoescape on %} {% cache 86400 comments article.id %}
var html = '{% for comment in comment_list %}<p>{{ comment.user.username }} <em>({{ comment.submit_date }})</em></p><p>{{ comment.comment }}</p>{% endfor %}';
var $expanded = jQuery('.{{ sha }}').find('.entry-comments');
if ($expanded.size() > 0) {
	$expanded.html(html);
}
else {
	jQuery('.read-{{ sha }}').find('.card-comments').html(html);
}
{% endcache %}
{% endautoescape %}