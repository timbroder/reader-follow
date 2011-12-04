// ==UserScript==
// @name           Reader Sharing
// @namespace      http://www.timbroder.com
// @description    Bringing Following and Sharing back to Google Reader
// @include        http://www.google.com/reader/view/*
// @include        https://www.google.com/reader/view/*
// @require        http://cdnjs.cloudflare.com/ajax/libs/jquery/1.7/jquery.min.js
// @version        2.0
// ==/UserScript==

function main() {
	if (navigator.userAgent.toLowerCase().indexOf('chrome') > -1) {
	    GM_getValue = function (key,def) {
	        return localStorage[key] || def;
	    };
	    
	    GM_setValue = function (key,value) {
	        localStorage[key] = value;
	        return localStorage[key];
	    };
	    
	    GM_deleteValue = function (key) {
	        return delete localStorage[key];
	    };
	}
	
	var Loader = function() {
		if(typeof unsafeWindow !== 'undefined') {
			this.body = unsafeWindow.document.body;
		} else {
			this.body = document.body;
		}
	};
	
	Loader.prototype = {
		addScript: function(url, clazz) {
			var script = document.createElement('script');
			script.type = 'text/javascript';
			script.src = url;
			
			if (clazz !== null ) {
				script.className = clazz;
			}
			
			this.body.appendChild(script);
		}
	};
	
	var Article = function(key, factory, loader, $article) {
		this.key = key;
		this.ui = factory;
		this.loader = loader;
		
		this.init($article);
	};
	
	Article.prototype = {
		init: function($article) {
			var self = this;
			this.endpoint = 'http://readersharing.net/';
			this.$container = $article;
			this.$container.addClass('reader-shareable');
			this.$action_bar = this.$container.parents('.card-common').find('.card-actions');
			this.$title = this.$container.find('.entry-title a');
			this.href = this.$title.attr('href');
			this.body = this.$container.find('.entry-body').html();
			this.published_on = this.$container.find('.entry-date').text();
			
			this.sha = SHA1(this.href);
			this.$comments_area = this.ui.get_comments_area(this.$container);
			
			this.display_comments();
			this.init_share_button();
			this.init_comment_button();
			
			if (this.key === '' || this.key === null || this.key === 'undefined') {
				this.show_modal(false);
				return;
			}
			
			this.$container.parents('.card-common').addClass(this.sha);
		},
		
		init_share_button: function() {
			var self = this;
			this.$share_button = this.ui.get_bar_button('Sharing.net');
			this.$share_button.insertAfter(this.$action_bar.find(".star"));
			this.$share_button.parent().addClass('reader-shareable');
			
			this.$share_button.on('click', function(){
				self.share();
			});
		},
		
		init_comment_button: function() {
			var self = this;
			//this.comments.add_button($action, $share_button);
			//this.comments.show_comments($action);
			
			this.$comment_button = this.ui.get_bar_button('Comment');
		
			this.$comment_button.on('click', function(){
				self.add_comment();
			});
		
			this.$comment_button.insertAfter(this.$share_button);
		
			//this.display_comments($action);*/
		},
		
		share: function() {
			var self = this,
				json = this.get_json_href();
			delete json.sha;
		
			/*GM_xmlhttpRequest({
				url: this.post_url + '?' + $.param(json),// + '?callback=?',
				data : json,
				method: "GET",
				onload: function (responseObject){
					var data = responseObject.responseText;
					var tmpFunc = new Function(data);
					tmpFunc(); 
				},
				onerror: function () {}
			});*/
			var url = this.endpoint + 'share/?' + $.param(json);
			this.loader.addScript(url, this.sha);
		},
		
		add_comment: function() {
			var self = this;
			if (this.$comments_area.find('.add_comment').size() === 0) {
				var $add_button = this.ui.get_add_comment();	
				$add_button.find('.submit').on('click', function(event){
					event.preventDefault();
					$(this).after(self.ui.get_spinner(self.sha));
					var json = self.get_json_href();
					
					json.comment = $(this).parents('.add_comment').find('textarea').val();
					var url = self.endpoint + 'comment/?' + $.param(json);
					self.loader.addScript(url, this.sha);
				});
				this.$comments_area.append($add_button);
			}
		},
		
		display_comments: function() {
			var json = this.get_json_href();
			var url = this.endpoint + 'comments/?' + $.param(json);
			this.loader.addScript(url, this.sha);
		},
		
		get_json_data: function() {
			var json = {
					'url': this.href,
					'body': this.body,
					'published_on': this.published_on,
					'title': this.$title.text(),
					'auth': this.key,
					'sha': this.sha
					//'callback': myFunction
			};
			
			return json;
		},
		
		get_json_href: function() {
			var json = {
					'url': this.href,
					'sha': this.sha,
					'auth': this.key
			};
			
			return json;
		},
		
		destroy: function() {
			$('script .' + this.sha).remove();
		}
	};
	
	var ReaderUI = function(base_url) {
		this.base_url = base_url;
		this.key = GM_getValue("greader_key");
	};
	
	ReaderUI.prototype = {
		get_bar_button: function(text) {
			return $('<span class="item-link link reader-sharing"><span class="link unselectable">' + text + '</span></span>').clone();
		},
		
		get_comment_area: function() {
			return $('<div class="card-comments"><div class="entry-comments"></div></div>').clone();
		},
		
		get_add_comment: function() {
			var html = '<div class="add_comment">' + 
					   '<div>' +
					   '<textarea rows="2" cols="40">' +
					   '</textarea>' +
					   '  </div>' +
					   '  <div>' +
					   '    <input class="submit" type="submit" value="Add Comment" />' +
					   '  </div>' +
					   '</div>';
			return $(html).clone();
		},
		
		get_spinner: function(sha) {
			var html = '<img src="' + this.base_url + 'media/images/loader.gif" class="spinner-' + sha + '"/>';
			return $(html).clone();
		},
		
		get_comments_area: function($elm) {
			var $comments_area = $elm.parents('.card').find('.entry-comments');
			
			//just in case gogle rips it out
			if ($comments_area.size() < 1) {
				$comments_area = this.ui.get_comment_area();
				$elm.parents('.card').find('.card-actions').before($comments_area);
			}
			/*else {
				$comments_area.html('alaready there');
			}*/
			
			return $comments_area;
		}
	};
	
	var ReaderSharing = function(base_url) {
		var self = this;
		this.key = GM_getValue("greader_key");
		self.base_url = base_url;
		this.settingsShown = false;
		this.check_ui_load();
		this.articles = [];
		
		/** may need something for clicking to new feeds but scrolling tends to take care of it
		$('#viewer-container').livequery(function() {
		});**/

		this.show_modal(false);
		this.loader = new Loader();
		this.ui = new ReaderUI(base_url);
		
		$('#viewer-entries-container').scroll(function() {
			self.update_ui();
		});
	};

	ReaderSharing.prototype = {
		show_modal: function(force) {
			if (this.key === '' || this.key === null || this.key === 'undefined' || force) {
				var key = prompt('Please enter your auth key', this.key);
				if (key !== null && key !== '') {
					this.key = key;
					GM_setValue("greader_key", key);
				}
				
			}
		},
		
		bind_menu: function() {
			if (!this.settingsShown) {
				var self = this,
					$controls = $('#viewer-top-controls'),
					$button = $('<a href="#">Reader Sharing Settings</a>');
				
				$button.on('click', function(){
					self.show_modal(true);
				});
				$button.appendTo($controls);
				self.settingsShown = true;
			}
		},
		
		check_ui_load: function() {
			var self = this;
			setTimeout(function () {
				if($('#entries .entry').length === 0) {
					if (!self.settingsShown) {
						if($('#no-entries-msg').length !== 0) {
							self.bind_menu();
						}
					}
					self.check_ui_load();
				}
				else{
					self.bind_menu();
					self.update_ui();
				}
			}, 100);
		},
		
		update_ui: function () {
			var self = this;
			$('.entry-container:not(.reader-shareable)').each(function () {
				//self.add_button($(this));
				self.articles.push(new Article(self.key, self.ui, self.loader, $(this)));
			});
		}

	};

	$(function(){
		new ReaderSharing('http://readersharing.net/');
	});
	
	function SHA1(a){function e(a){a=a.replace(/\r\n/g,"\n");var b="";for(var c=0;c<a.length;c++){var d=a.charCodeAt(c);d<128?b+=String.fromCharCode(d):d>127&&d<2048?(b+=String.fromCharCode(d>>6|192),b+=String.fromCharCode(d&63|128)):(b+=String.fromCharCode(d>>12|224),b+=String.fromCharCode(d>>6&63|128),b+=String.fromCharCode(d&63|128))}return b}function d(a){var b="",c,d;for(c=7;c>=0;c--)d=a>>>c*4&15,b+=d.toString(16);return b}function c(a){var b="",c,d,e;for(c=0;c<=6;c+=2)d=a>>>c*4+4&15,e=a>>>c*4&15,b+=d.toString(16)+e.toString(16);return b}function b(a,b){var c=a<<b|a>>>32-b;return c}var f,g,h,i=Array(80),j=1732584193,k=4023233417,l=2562383102,m=271733878,n=3285377520,o,p,q,r,s,t;a=e(a);var u=a.length,v=[];for(g=0;g<u-3;g+=4)h=a.charCodeAt(g)<<24|a.charCodeAt(g+1)<<16|a.charCodeAt(g+2)<<8|a.charCodeAt(g+3),v.push(h);switch(u%4){case 0:g=2147483648;break;case 1:g=a.charCodeAt(u-1)<<24|8388608;break;case 2:g=a.charCodeAt(u-2)<<24|a.charCodeAt(u-1)<<16|32768;break;case 3:g=a.charCodeAt(u-3)<<24|a.charCodeAt(u-2)<<16|a.charCodeAt(u-1)<<8|128}v.push(g);while(v.length%16!=14)v.push(0);v.push(u>>>29),v.push(u<<3&4294967295);for(f=0;f<v.length;f+=16){for(g=0;g<16;g++)i[g]=v[f+g];for(g=16;g<=79;g++)i[g]=b(i[g-3]^i[g-8]^i[g-14]^i[g-16],1);o=j,p=k,q=l,r=m,s=n;for(g=0;g<=19;g++)t=b(o,5)+(p&q|~p&r)+s+i[g]+1518500249&4294967295,s=r,r=q,q=b(p,30),p=o,o=t;for(g=20;g<=39;g++)t=b(o,5)+(p^q^r)+s+i[g]+1859775393&4294967295,s=r,r=q,q=b(p,30),p=o,o=t;for(g=40;g<=59;g++)t=b(o,5)+(p&q|p&r|q&r)+s+i[g]+2400959708&4294967295,s=r,r=q,q=b(p,30),p=o,o=t;for(g=60;g<=79;g++)t=b(o,5)+(p^q^r)+s+i[g]+3395469782&4294967295,s=r,r=q,q=b(p,30),p=o,o=t;j=j+o&4294967295,k=k+p&4294967295,l=l+q&4294967295,m=m+r&4294967295,n=n+s&4294967295}var t=d(j)+d(k)+d(l)+d(m)+d(n);return t.toLowerCase()}
}

//needed for chrome
function addJQuery(callback) {
  var script = document.createElement("script");
  script.setAttribute("src", "http://readersharing.net/media/js/notty.with.js");
  script.addEventListener('load', function() {
	  if (navigator.userAgent.toLowerCase().indexOf('chrome') > -1) {
		  var script = document.createElement("script");
		  script.textContent = "(" + callback.toString() + ")();";
		  document.body.appendChild(script);
	  }
	  else {
		  main();
	  }
  }, false);
  document.body.appendChild(script);
}

// load jQuery and execute the main function
//if (navigator.userAgent.toLowerCase().indexOf('chrome') > -1) {
	addJQuery(main);
//}
//else if (typeof jQuery !== 'undefined') {
//	addJQuery();
//}

var style = "#nottys{position:fixed;top:20px;right:20px;width:280px;z-index:999}" +
"#nottys .notty{margin-bottom:20px;color:#FFF;text-shadow:#000 0 1px 2px;font:normal 12px/17px Helvetica;border:1px solid rgba(0,0,0,0.7);background:0 transparent), 0 rgba(0,0,0,0.4));-webkit-border-radius:6px;-moz-border-radius:6px;border-radius:6px;-webkit-box-shadow:rgba(0,0,0,0.8) 0 2px 13px rgba(0,0,0,0.6) 0 -3px 13px rgba(255,255,255,0.5) 0 1px 0 inset;-moz-box-shadow:rgba(0,0,0,0.8) 0 2px 13px rgba(0,0,0,0.6) 0 -3px 13px rgba(255,255,255,0.5) 0 1px 0 inset;box-shadow:rgba(0,0,0,0.8) 0 2px 13px rgba(0,0,0,0.6) 0 -3px 13px rgba(255,255,255,0.5) 0 1px 0 inset;position:relative;cursor:default;-webkit-user-select:none;-moz-user-select:none;overflow:hidden;_overflow:visible;_zoom:1;padding:10px;background:black}" +
".pop{-webkit-animation-duration:.5s;-webkit-animation-iteration-count:1;-webkit-animation-name:pop;-webkit-animation-timing-function:ease-in}" +
".remove{-webkit-animation-iteration-count:1;-webkit-animation-timing-function:ease-in-out;-webkit-animation-duration:.3s;-webkit-animation-name:remove}" +
"#nottys .notty.click{cursor:pointer}" +
"#nottys .notty .hide{position:absolute;font-weight:700;line-height:20px;height:20px;right:0;top:0;background:0;-webkit-border-top-right-radius:6px;-webkit-border-bottom-left-radius:6px;-moz-border-radius-bottomleft:6px;-moz-border-radius-topright:6px;-webkit-box-shadow:rgba(255,255,255,0.5) 0 -1px 0 inset, rgba(255,255,255,0.5) 0 1px 0 inset, #000 0 5px 6px;-moz-box-shadow:rgba(255,255,255,0.5) 0 -1px 0 inset, rgba(255,255,255,0.5) 0 1px 0 inset, #000 0 5px 6px;box-shadow:rgba(255,255,255,0.5) 0 -1px 0 inset, rgba(255,255,255,0.5) 0 1px 0 inset, #000 0 5px 6px;border-left:1px solid rgba(255,255,255,0.5);cursor:pointer;display:none;padding:5px 15px}" +
"#nottys .notty .hide:hover{background:0 #fff);color:#000;text-shadow:none}" +
"#nottys .notty .right,#nottys .notty .left{width:79%;height:100%;float:left}" +
"#nottys .notty .time{font-size:9px;position:relative}" +
"#nottys .notty .right .time{margin-left:19px}" +
"#nottys .notty .left{width:20%}" +
"#nottys .notty .right .inner{padding-left:19px}" +
"#nottys .notty .left .img:after{content:'';background:0 transparent);width:1px;height:50px;position:absolute;right:-10px}" +
"#nottys .notty .left .img{width:100%;background-size:auto 100%;height:50px;border-radius:6px;-webkit-box-shadow:rgba(255,255,255,0.9) 0 1px 0 inset, rgba(0,0,0,0.5) 0 1px 6px;-moz-box-shadow:rgba(255,255,255,0.9) 0 1px 0 inset, rgba(0,0,0,0.5) 0 1px 6px;box-shadow:rgba(255,255,255,0.9) 0 1px 0 inset, rgba(0,0,0,0.5) 0 1px 6px;border:1px solid rgba(0,0,0,0.55);position:relative}" +
"#nottys .notty:after{content:'.';visibility:hidden;display:block;clear:both;height:0;font-size:0}" +
"#nottys .notty h2{font-size:14px;text-shadow:#000 0 2px 4px;color:#fff;margin:0 0 5px}" +
"80%{-webkit-transform:scale(1.05);opacity:1}" +
"to{-webkit-transform:scale(1)}" +
"100%{right:-223px;opacity:0}";
GM_addStyle(style);

/**
@name           Script Update Checker
@namespace      http://www.crappytools.net
@description    Code to add to any Greasemonkey script to let it check for updates.

//NOTES:
//Feel free to copy this into any script you write; that's what it's here for. A credit and/or URL back to here would be appreciated, though.
//I was careful to use as few variables as I could so it would be easy to paste right into an existing script. All the ones you need to set are at the very top.
//The target script needs to be uploaded to userscripts.org. The update checks will -not- increase the install count for the script there.
//This script is set up to check for updates to itself by default. It may be a good idea to leave it like this.
**/

var SUC_script_num = 118173; // Change this to the number given to the script by userscripts.org (check the address bar)
try{function updateCheck(forced){if ((forced) || (parseInt(GM_getValue('SUC_last_update', '0')) + 86400000 <= (new Date().getTime()))){try{GM_xmlhttpRequest({method: 'GET',url: 'http://userscripts.org/scripts/source/'+SUC_script_num+'.meta.js?'+new Date().getTime(),headers: {'Cache-Control': 'no-cache'},onload: function(resp){var local_version, remote_version, rt, script_name;rt=resp.responseText;GM_setValue('SUC_last_update', new Date().getTime()+'');remote_version=parseInt(/@uso:version\s*(.*?)\s*$/m.exec(rt)[1]);local_version=parseInt(GM_getValue('SUC_current_version', '-1'));if(local_version!=-1){script_name = (/@name\s*(.*?)\s*$/m.exec(rt))[1];GM_setValue('SUC_target_script_name', script_name);if (remote_version > local_version){if(confirm('There is an update available for the Greasemonkey script "'+script_name+'."\nWould you like to go to the install page now?')){GM_openInTab('http://userscripts.org/scripts/show/'+SUC_script_num);GM_setValue('SUC_current_version', remote_version);}}else if (forced)alert('No update is available for "'+script_name+'."');}else GM_setValue('SUC_current_version', remote_version+'');}});}catch (err){if (forced)alert('An error occurred while checking for updates:\n'+err);}}}GM_registerMenuCommand(GM_getValue('SUC_target_script_name', '???') + ' - Manual Update Check', function(){updateCheck(true);});updateCheck(false);}catch(err){}





