// ==UserScript==
// @name           Reader Sharing
// @namespace      http://www.timbroder.com
// @description    Bringing Following and Sharing back to Google Reader
// @include        http://www.google.com/reader/view/*
// @include        https://www.google.com/reader/view/*
// @require        http://cdnjs.cloudflare.com/ajax/libs/jquery/1.7/jquery.min.js
// ==/UserScript==

var ReaderSharing = function() {
	var self = this;
	this.key = GM_getValue("key");
	self.post_url = 'http://localhost:8000/post/';
	
	this.buttons_check();
	
	$('#viewer-entries-container').scroll(function() {
		self.add_buttons();
	});
	
	/** may need something for clicking to new feeds but scrolling tends to take care of it
	$('#viewer-container').livequery(function() {
		console.log('live?');
	});**/
	
	//settings

	this.show_modal(false);
};

ReaderSharing.prototype = {
		
	show_modal: function(force) {
		if (this.key === '' || this.key === null || this.key === 'undefined' || force) {
			var key = prompt('Please enter your auth key', this.key);
			if (key !== null && key !== '') {
				this.key = key;
				GM_setValue("key", key);
			}
			
		}
	},
	
	bind_menu: function() {
		var self = this,
			$controls = $('#viewer-top-controls'),
			$button = $('<a href="#">Reader Sharing Settings</a>');
		
		$button.on('click', function(){
			self.show_modal(true);
		});
		$button.appendTo($controls);
	},
	
	buttons_check: function() {
		var self = this;
		setTimeout(function () {
			if($('#entries .entry').length === 0) {
				self.buttons_check();
			}
			else{
				self.bind_menu();
				self.add_buttons();
			}
		}, 100);
	},
	
	add_buttons: function () {
		var self = this;
		$('.entry-actions:not(.reader-shareable)').each(function () {
			self.add_button($(this));
		});
	},
	
	add_button: function($action) {
		var self = this,
			$share_button = $('<span class="item-link link reader-sharing"><span class="link unselectable">Share!</span></span>');
		$share_button.on('click', function(){
			self.post($(this));
		});
		$share_button.insertAfter($action.find(".star"));
		$share_button.parent().addClass('reader-shareable');
	},
	
	post: function($elm) {
		var self = this,
			$data = $elm.parents('.card').find('.entry-container');
		var $title = $data.find('.entry-title a');
		if (this.key === '' || this.key === null || this.key === 'undefined') {
			this.show_modal(false);
			return;
		}
		var json = {
				'url': $title.attr('href'),	
				'body': $data.find('.entry-body').html(),
				'published_on': $data.find('.entry-date').text(),
				'title': $title.text(),
				'auth': this.key
		};
		
		var req = $.ajax({
			  url: this.post_url + '?callback=?',
			  data : json
			});
	}
};

function showStatus(rsp) {
	$.notty({
        content : rsp.responseText,
        timeout: 3000
     });
}

$(function(){
	new ReaderSharing();
});

//Author: Ryan Greenberg (ryan@ischool.berkeley.edu)
//Date: September 3, 2009
//Version: $Id: gm_jq_xhr.js 240 2009-11-03 17:38:40Z ryan $

//This allows jQuery to make cross-domain XHR by providing
//a wrapper for GM_xmlhttpRequest. The difference between
//XMLHttpRequest and GM_xmlhttpRequest is that the Greasemonkey
//version fires immediately when passed options, whereas the standard
//XHR does not run until .send() is called. In order to allow jQuery
//to use the Greasemonkey version, we create a wrapper object, GM_XHR,
//that stores any parameters jQuery passes it and then creates GM_xmlhttprequest
//when jQuery calls GM_XHR.send().

//Wrapper function
function GM_XHR() {
 this.type = null;
 this.url = null;
 this.async = null;
 this.username = null;
 this.password = null;
 this.status = null;
 this.headers = {};
 this.readyState = null;
 this.success = null;
 
 this.open = function(type, url, async, username, password) {
     this.type = type ? type : null;
     this.url = url ? url : null;
     this.async = async ? async : null;
     this.username = username ? username : null;
     this.password = password ? password : null;
     this.readyState = 1;
 };
 
 this.setRequestHeader = function(name, value) {
     this.headers[name] = value;
 };
     
 this.abort = function() {
     this.readyState = 0;
 };
 
 this.getResponseHeader = function(name) {
     return this.headers[name];
 };
 
 this.send = function(data) {
     this.data = data;
     var that = this;
     GM_xmlhttpRequest({
         method: this.type,
         url: this.url,
         headers: this.headers,
         data: this.data,
         success: this.success,
         onload: function(rsp) {
             // Populate wrapper object with all data returned from GM_XMLHttpRequest
             for (k in rsp) {
                 that[k] = rsp[k];
             }
             showStatus(rsp);
         },
         onerror: function(rsp) {
             for (k in rsp) {
                 that[k] = rsp[k];
             }
         },
         onreadystatechange: function(rsp) {
             for (k in rsp) {
                 that[k] = rsp[k];
             }
         }
     });
 };
};

//Tell jQuery to use the GM_XHR object instead of the standard browser XHR
$.ajaxSetup({
 xhr: function(){return new GM_XHR;}
});


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

var style = "#nottys{position:fixed;top:20px;right:20px;width:280px;z-index:999}" +
"#nottys .notty{margin-bottom:20px;color:#FFF;text-shadow:#000 0 1px 2px;font:normal 12px/17px Helvetica;border:1px solid rgba(0,0,0,0.7);background:0 transparent), 0 rgba(0,0,0,0.4));-webkit-border-radius:6px;-moz-border-radius:6px;border-radius:6px;-webkit-box-shadow:rgba(0,0,0,0.8) 0 2px 13px rgba(0,0,0,0.6) 0 -3px 13px rgba(255,255,255,0.5) 0 1px 0 inset;-moz-box-shadow:rgba(0,0,0,0.8) 0 2px 13px rgba(0,0,0,0.6) 0 -3px 13px rgba(255,255,255,0.5) 0 1px 0 inset;box-shadow:rgba(0,0,0,0.8) 0 2px 13px rgba(0,0,0,0.6) 0 -3px 13px rgba(255,255,255,0.5) 0 1px 0 inset;position:relative;cursor:default;-webkit-user-select:none;-moz-user-select:none;overflow:hidden;_overflow:visible;_zoom:1;padding:10px}" +
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

//var SUC_script_num = 20145; // Change this to the number given to the script by userscripts.org (check the address bar)
//try{function updateCheck(forced){if ((forced) || (parseInt(GM_getValue('SUC_last_update', '0')) + 86400000 <= (new Date().getTime()))){try{GM_xmlhttpRequest({method: 'GET',url: 'http://userscripts.org/scripts/source/'+SUC_script_num+'.meta.js?'+new Date().getTime(),headers: {'Cache-Control': 'no-cache'},onload: function(resp){var local_version, remote_version, rt, script_name;rt=resp.responseText;GM_setValue('SUC_last_update', new Date().getTime()+'');remote_version=parseInt(/@uso:version\s*(.*?)\s*$/m.exec(rt)[1]);local_version=parseInt(GM_getValue('SUC_current_version', '-1'));if(local_version!=-1){script_name = (/@name\s*(.*?)\s*$/m.exec(rt))[1];GM_setValue('SUC_target_script_name', script_name);if (remote_version > local_version){if(confirm('There is an update available for the Greasemonkey script "'+script_name+'."\nWould you like to go to the install page now?')){GM_openInTab('http://userscripts.org/scripts/show/'+SUC_script_num);GM_setValue('SUC_current_version', remote_version);}}else if (forced)alert('No update is available for "'+script_name+'."');}else GM_setValue('SUC_current_version', remote_version+'');}});}catch (err){if (forced)alert('An error occurred while checking for updates:\n'+err);}}}GM_registerMenuCommand(GM_getValue('SUC_target_script_name', '???') + ' - Manual Update Check', function(){updateCheck(true);});updateCheck(false);}catch(err){}

/*!
 * jQuery Notty
 * http://www.userdot.net/#!/jquery
 *
 * Copyright 2011, UserDot www.userdot.net
 * Licensed under the GPL Version 3 license.
 * Version 1.0.0
 *
 */
(function(a){a.notty=function(b){function l(a){var b=[[2,"One second","1 second from now"],[60,"seconds",1],[120,"One minute","1 minute from now"],[3600,"minutes",60],[7200,"One hour","1 hour from now"],[86400,"hours",3600],[172800,"One day","tomorrow"],[604800,"days",86400],[1209600,"One week","next week"],[2419200,"weeks",604800],[4838400,"One month","next month"],[29030400,"months",2419200],[58060800,"One year","next year"],[290304e4,"years",29030400],[580608e4,"One century","next century"],[580608e5,"centuries",290304e4]],c=(new Date-a)/1e3,d="ago",e=1;c<0&&(c=Math.abs(c),d="from now",e=1);var f=0,g;while(g=b[f++])if(c<g[0])return typeof g[2]=="string"?g[e]:Math.floor(c/g[2])+" "+g[1];return a}var c,d,e,f,g,h,i;b=a.extend({title:undefined,content:undefined,timeout:0,img:undefined,showTime:!0,click:undefined},b),c=a("#nottys"),c.length||(c=a("<div>",{id:"nottys"}).appendTo(document.body)),d=a("<div>"),d.addClass("notty pop"),e=a("<div>",{click:function(){a(this).parent().removeClass("pop").addClass("remove").delay(300).queue(function(){a(this).clearQueue(),a(this).remove()})}}),e.addClass("hide"),e.html("Hide notification");if(b.img!=undefined){f=a("<div>",{style:"background: url('"+b.img+"')"}),f.addClass("img"),h=a("<div class='left'>"),g=a("<div class='right'>");if(b.title!=undefined)var j="<h2>"+b.title+"</h2>";else var j="";if(b.content!=undefined)var k=b.content;else var k="";i=a("<div>",{html:j+k}),i.addClass("inner"),i.appendTo(g),f.appendTo(h),h.appendTo(d),g.appendTo(d)}else{if(b.title!=undefined)var j="<h2>"+b.title+"</h2>";else var j="";if(b.content!=undefined)var k=b.content;else var k="";i=j+k,d.html(i)}e.appendTo(d);if(b.showTime!=!1){var m=Number(new Date);timeHTML=a("<div>",{html:"<strong>"+l(m)+"</strong> ago"}),timeHTML.addClass("time").attr("title",m),b.img!=undefined?timeHTML.appendTo(g):timeHTML.appendTo(d),setInterval(function(){a(".time").each(function(){var b=a(this).attr("title");a(this).html("<strong>"+l(b)+"</strong> ago")})},4e3)}d.hover(function(){e.show()},function(){e.hide()}),d.prependTo(c),d.show(),b.timeout&&setTimeout(function(){d.removeClass("pop").addClass("remove").delay(300).queue(function(){a(this).clearQueue(),a(this).remove()})},b.timeout),b.click!=undefined&&(d.addClass("click"),d.click(function(c){var d=a(c.target);d.is(".hide")||b.click.call(this)}));return this}})(jQuery)



