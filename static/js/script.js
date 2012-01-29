// script.js
// for testing
////////////////////////////////////////////////////////////////////////////////

// creates a wrapper for a websocket
function make_websock(loc) {
    var self = {};
    self.loc = loc;
    self.open = function() {
	// lengthen timeout
	if(!self.timeout) {
	    self.timeout = 0;
	}
	self.timeout += 1;
	var ws = new WebSocket(self.loc);
	console.log("Websocket opened");

	// send
	self.send = function(mess) {
	    ws.send(mess);
	};

	// message back
	ws.onmessage = function(evt) {
	    $("#stuff").append($("<li>").text(evt.data));
	};

	// try reconnecting
	ws.onclose = function() {
	    // retry connecting timeouts: grow quadratically
	    console.log(self.loc);
	    var secs = 1000*Math.pow(self.timeout,2);
	    console.log("Trying to reconnect in " + secs/1000 + " seconds");
	    setTimeout(self.open, secs);
	};
    };
    
    self.open();
    return self;
}

var ws_url = "ws://"+window.location.host+"/websocket/"+channel;
var sock = make_websock(ws_url);
// var ws = new WebSocket("ws://"+window.location.host+"/websocket/"+channel);

$("#post").focus();

// send a message
$("#form").submit(function(evt){
    sock.send($("#post").val());
    $("#post").val("");
    evt.preventDefault();
    return false;
});