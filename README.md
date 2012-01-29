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
 - Twitter-like convections (@ (mention), # (tag))
 - Some extensions to the twitter conventions
   (!@ (immediate notify), ## (channel), @##channel:line (reply to line),
    @# (notify tag watchers), )
 - Add in a +1/like infrastructure
 - XMPP integration (digests/notifications)
 - IRC integration (single channel)
 - forking model
 - NLP to determine whether a user would want to know about this update
 - NLP to determine topic name
 - Voting system for topic changes, merges(?)
 - Possibly access control
 - Possibly organization separation
 - Learn tornado and redis

TODO
================================================================================
 - Get Redis running
 - Get Python+Redis working
 - Get Tornado running
 - Get Tornado+Redis running (simple updates)
 - Get AJAX-y Tornado+Redis running
 - Get real time chat
 - Start going down the list

CONCERNS
================================================================================
 - Grove.io?
   - Still based on IRC
   - Does not seem to have tiered notifications
   - No NLP fanciness
   - No forking model
   - Not voting system
   - Won't learn Tornado unless I build APPNAME