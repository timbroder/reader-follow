// usage: log('inside coolFunc', this, arguments);
// paulirish.com/2009/log-a-lightweight-wrapper-for-consolelog/
window.log = function(){
  log.history = log.history || [];   // store logs to an array for reference
  log.history.push(arguments);
  if(this.console) {
      arguments.callee = arguments.callee.caller;
      console.log( Array.prototype.slice.call(arguments) );
  }
};
// make it safe to use console.log always
//(function(b){function c(){}for(var d="assert,count,debug,dir,dirxml,error,exception,group,groupCollapsed,groupEnd,info,log,markTimeline,profile,profileEnd,time,timeEnd,trace,warn".split(","),a;a=d.pop();)b[a]=b[a]||c})(window.console=window.console||{});
//paul's wasn't working so, http://code.google.com/p/fbug/source/browse/branches/firebug1.2/lite/firebugx.js?r=964
if(!window.console||!console.firebug){var names=["log","debug","info","warn","error","assert","dir","dirxml","group","groupEnd","time","timeEnd","count","trace","profile","profileEnd"];window.console={};for(var i=0;i<names.length;++i)window.console[names[i]]=function(){}}

// place any jQuery/helper plugins in here, instead of separate, slower script files.


/**
* pubsub!
* https://github.com/phiggins42/bloody-jquery-plugins/blob/master/pubsub.js
**/
(function(a){var b={};a.publish=function(c,e){b[c]&&a.each(b[c],function(){this.apply(a,e||[])})},a.subscribe=function(a,c){b[a]||(b[a]=[]),b[a].push(c);return[a,c]},a.unsubscribe=function(c){var e=c[0];b[e]&&a.each(b[e],function(a){this==c[1]&&b[e].splice(a,1)})}})(jQuery)