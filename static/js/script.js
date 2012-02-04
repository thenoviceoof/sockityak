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

    // backbone models
    var Line = Backbone.Model.extend({
        defaults: {
            line: 0,
            time: 0,
            user: "anon",
            message: ""
        }
    });

    var Thread = Backbone.Collection.extend({
        model: Line,
        // sort by timestamp
        comparator: function(line) { return line.get("line"); }
    });

    // instantiate this page's thread
    var thread = new Thread();
    // save the thread where we can get at it ???
    window.thread = thread;

    // backbone views
    var LineView = Backbone.View.extend({
        tagName: "li",
        template: _.template($("#line-template").html()),
        render: function() {
            $(this.el).html(this.template(this.model.toJSON()));
            this.setText();
            return this;
        },
        setText: function() {
            var time = timestamp(this.model.get('time'));
            var line = padZeroes(this.model.get('line'), 5);
            var user = this.model.get('user');
            var mess = this.model.get('message');
            this.$(".timestamp").text(time);
            this.$(".line-number").text(line);
            this.$(".username").text(user);
            this.$(".message").text(mess);
        }
    });

    var ThreadView = Backbone.View.extend({
        el: $("#chatroom"),
        initialize: function() {
            _.bindAll(this, 'render', 'append', 'addd');

            this.collection = thread;
            this.collection.bind('add', this.addd);

            this.render();
        },
        // right now, just kill all the chats, and rebuild everything
        // !!! this is very expensive, and bad
        render: function() {
            $("#chatroom li").remove();
            for(var i in this.collection.models) {
                this.append(this.collection.models[i]);
            }
        },
        append: function(line) {
            var view = new LineView({model: line});
            $("#chatroom").append(view.render().el);
        },
        // !!! this is a stupid name
        addd: function(line) {
            this.render();
        },
    });

    window.threadview = new ThreadView();

    // --------------------------------------------------
    // Web socket stuff

    // from: http://www.quirksmode.org/js/cookies.html
    function get_cookie(key) {
        var nameEQ = name + "=";
        var ca = document.cookie.split(';');
        for(var i=0;i < ca.length;i++) {
                var c = ca[i];
                while (c.charAt(0)==' ')
                    c = c.substring(1,c.length);
                if (c.indexOf(nameEQ) == 0)
                    return c.substring(nameEQ.length,c.length);
        }
        return null;
    }

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

            // authentication: with session cookie
            self.auth = function() {
                // get session cookie
                var session = get_cookie("session");
                var obj = {"type":"auth", "message":session};
                // send the whole rigamole
                ws.send(JSON.stringify(obj));
            };
            // send chat
            self.send = function(mess) {
                var obj = {"type": "message", "message": mess};
                ws.send(JSON.stringify(obj));
            };
            // get previous
            self.fetchOld = function() {
                var models = thread.models;
                var obj = {"type": "history"};
                if(models.length != 0) {
                    obj["message"] = models[0].get("line");
                }
                var j = JSON.stringify(obj)
                ws.send(j);
            };

            // new message
            ws.onmessage = function(evt) {
                var data = JSON.parse(evt.data);
                console.log(data);
                if(data["type"] == "error") {
                    console.log("ERROR");
                } else if(data["type"] == "auth") {
                    // auth okay, load up the initial messages
                    self.fetchOld();
                } else if(data["type"] == "message") {
                    thread.add(new Line(data["message"]));   
                } else if(data["type"] == "history") {
                    // turn the array of jsons into an array of Lines
                    var lines = $.map(data["message"], function(e, i){
                        return new Line(e);
                    });
                    thread.add(lines);   
                }
            };

            ws.onopen = function() {
                console.log("Websocket opened");
                // go authenticate first
                self.auth();
            };

            // try reconnecting
            ws.onclose = function() {
                // retry connecting timeouts: grow quadratically
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

    $("#load-past").click(function(e){
        console.log("mu");
        sock.fetchOld();
        e.preventDefault();
        return false;
    });

    $("#post").focus();

    // send a message
    $("#form").submit(function(evt){
        sock.send($("#post").val());
        $("#post").val("");
        evt.preventDefault();
        return false;
    });

})(jQuery);
