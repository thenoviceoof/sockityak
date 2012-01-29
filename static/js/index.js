// index.js
////////////////////////////////////////////////////////////////////////////////

$("#new_channel").click(function(){
    var name = prompt("Name of the new channel?");
    window.open("/channel/"+name, "_blank");
});