Sockityak
================================================================================
Trying out README driven development.
================================================================================

A replacement for IRC, meant for ADI consumption

APPNAME = Sockityak; subject to changes

STORIES
================================================================================

1.) Bob is a normal college student at Columbia, who is also
interested in computer science (this makes him highly abnormal, but
nevermind). He wants to talk about some programming things once in a
while, but the main avenue for connecting the ADI executive board
(e-board) is through IRC, which no one is on, or the committee
list-serv, which isn't an informal conversation thing. When APPNAME
comes out, he tries it out: after finding the general chat
conversation not to his fancy, he tries to talk about something else:
this thread of conversation is forked, and eventually some ADI members
find his thread after getting notifications of his new channel, and
they have a nice real-time conversation.

2.) John is an ADI e-board member: he doesn't know what the community
members want, so he asks them on APPNAME. Since APPNAME has become a
hangout for the Columbia tech community, he gets responses within a
day (a reasonable amount of time!) and even strikes up an hour of
furious debate. He gets the feedback from the people that care most,
especially outside of the e-board.

3.) Nathan is bored, and wants to talk. He logs on to APPNAME, and
makes a meme-thread. Everyone has fun posting silly pictures of each
other, and many lols are had.

GOALS
================================================================================
 - Provide a highly asynchronous chat
 - Interval digests
 - Tiered notifications
 - Twitter-like conventions (@ (mention), # (tag))
 - Some extensions to the twitter conventions
   (!@ (immediate notify), ## (channel), @##channel:line (reply to line),
    @# (notify tag watchers), )
 - Autocomplete EVERYTHING
 - Add in a +1/like infrastructure
 - XMPP integration (digests/notifications)
 - smart digests (new tags, @, highly voted treated specially,
   both new topics and watched topics)
 - IRC integration (single channel)
 - rate-limiting
 - ban-hammer: channel and org-wide
 - forking model
 - NLP to determine whether a user would want to know about this update
 - NLP to determine topic name
 - Voting system for topic changes, merges(?)
 - Ensure University association for chat
 - Possibly access control (users against orgs/threads)
 - Possibly organization separation
 - Learn tornado and redis and mongodb

TODO
================================================================================
 - X Get Redis running
 - X Get Python+Redis working (apt-get install python-redis)
 - X Get Tornado running (pip install tornado, ubuntu current is 1.2)
 - X Get Tornado+Redis running (simple updates)
 - X Get AJAX-y Tornado+Redis running
 - X Get real time chat
 - X Add channels
 - X switch to json format in chat data
   - define an extensible json schema
 - X Add auth (google oauth, or facebook oauth. or both)
   - X remake redis sessions
 - Switch to mongodb (except sessions, pubsub)
 - Probably clean up the styles right about here
   - front page
   - channel list
   - \ channel
   - settings
 - who's in the room list? / past participants
 - Add title-page notification
   - Add audio notifications
   - easy mute?
 - Add email notifications
   - add "watch" mechanism
   - once per message, if you're not already connected
   - digest (hourly)
   - digest (daily, weekly, hourly)
 - Parse out @ and #
   - get XMPP working
   - !@ - direct notification (marked digest, email, XMPP, text)
   - lots of if-this-then-that functionality

USING
================================================================================
 - Tornado
 - Redis
 - MongoDB
 - websockets
 - jQuery
 - backbone.js

CONCERNS
================================================================================
 - Grove.io?
   - Still based on IRC
   - Does not seem to have tiered notifications
   - No NLP fanciness
   - No forking model
   - Not voting system
   - Won't learn Tornado unless I build APPNAME
