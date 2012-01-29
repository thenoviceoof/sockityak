// script.js
// for testing
////////////////////////////////////////////////////////////////////////////////

// backbone list rendering
(function($){
    var Line = Backbone.Model.extend({
        defaults: {
            line: 0,
            user: "anon",
            mess: ""
        }
    });

    var Thread = Backbone.Collection.extend({
        model: Line
    });

    // view
    var ThreadView = Backbone.View.extend({
        el: $("#stuff"),
        initialize: function() {
            _.bindAll(this, 'render', 'appendItem');

            this.collection = new Thread();
            this.collection.bind('add', this.appendItem);

            this.render();
        },
        render: function() {
            var self = this;
            // in case collection is not empty
            _(this.collection.models).each(function(item){
                self.appendItem(item);
            }, this);
        },
        appendItem: function(item) {
            var lineNum = $("<b>").text(item.get("line"));
            var userName = $("<i>").text(item.get("user"));
            var message = $("<span>").text(item.get("mess"));
            var li = $("<li>").html(lineNum).append(userName).append(message);
            $(this.el).append(li);
        },
    });

    var thread = new ThreadView();

    for(var i in prepopulate_chat) {
	thread.appendItem(new Line(prepopulate_chat[i]));
    }

    // --------------------------------------------------
    // Web socket stuff

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
		thread.appendItem(new Line(JSON.parse(evt.data)));
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

    $("#post").focus();

    // send a message
    $("#form").submit(function(evt){
        sock.send($("#post").val());
        $("#post").val("");
        evt.preventDefault();
        return false;
    });

})(jQuery);
