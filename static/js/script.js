// script.js
// for testing
////////////////////////////////////////////////////////////////////////////////

(function($){
    // utilities
    function padZeroes(num, pad) {
        num = ''+num; // convert to string
        while(num.length < pad) {
            num = "0" + num;
        }
        return num;
    }

    function timestamp(time) {
        var d = new Date(time);
        return $.map([d.getHours(),d.getMinutes(),d.getSeconds()],
                     function(elem, ind){
                         return padZeroes(elem, 2);
                     }).join(":");
    }

    // backbone list rendering
    var Line = Backbone.Model.extend({
        defaults: {
            line: 0,
            user: "anon",
            mess: "",
            time: 0
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
            var timeStamp = $("<span>").addClass("timestamp")
                .text(timestamp(item.get("time")));
            var lineNum = $("<span>").addClass("line-number")
                .text(padZeroes(item.get("line"), 5));
            var userName = $("<span>").addClass("username")
                .text(item.get("user"));
            var message = $("<span>").addClass("message")
                .text(item.get("mess"));
            var li = $("<li>").html(timeStamp).append(lineNum)
                .append(userName).append(message);
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

            // new message
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
