// script.js
// for testing
////////////////////////////////////////////////////////////////////////////////

var ws = new WebSocket("ws://"+window.location.host+"/websocket");

ws.onopen = function() {
    console.log("Websocket open");
};

// message back
ws.onmessage = function (evt) {
    $("#stuff").append($("<li>").text(evt.data));
};

// send a message
$("#form").submit(function(evt){
    ws.send($("#post").val());
    evt.preventDefault();
    return false;
});