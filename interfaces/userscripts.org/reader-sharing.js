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
	self.post_url = 'http://localhost:8000/post/';
	
	this.buttons_check();
	
	$('#viewer-entries-container').scroll(function() {
		self.add_buttons();
	});
	
	/** may need something for clicking to new feeds but scrolling tends to take care of it
	$('#viewer-container').livequery(function() {
		console.log('live?');
	});**/
};

ReaderSharing.prototype = {
	buttons_check: function() {
		var self = this;
		setTimeout(function () {
			if($('#entries .entry').length === 0) {
				self.buttons_check();
			}
			else{
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

		var json = {
				'url': $title.attr('href'),	
				'body': $data.find('.entry-body').html(),
				'published_on': $data.find('.entry-date').text(),
				'title': $title.text(),
				'auth': '021cf1a61bd8a2e1b1bc108932110340'
		};
		
		var req = $.ajax({
			  url: this.post_url + '?callback=?',
			  data : json,
			});
	}
};

function showStatus(rsp) {
	console.log('back');
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
