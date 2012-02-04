// index.js
////////////////////////////////////////////////////////////////////////////////

$("#new-channel").click(function(){
    var name = prompt("Name of the new channel?");
    window.open("/newchannel/"+name, "_blank");
});