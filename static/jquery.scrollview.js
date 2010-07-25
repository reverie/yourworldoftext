/**
    * ScrollView - jQuery plugin 0.1
    *
    * This plugin supplies contents view by grab and drag scroll.
    *
    * Copyright (c) 2009 Toshimitsu Takahashi
    * Modified 2009 by Andrew Badr
    *
    * Released under the MIT license.
    *
    */
    
// Edited to make global instead of a jquery extension, and require custom scroll callback
// it's a long story

function makeScrollable(container, scrollBy) {
    var active = true;
    container = $(container);
    var grabbing = "move";
    var isgrabbing = false;
    var xp, yp, grabbedNode;

    var startgrab = function(target){
        isgrabbing = true;
        // setting the style on grabbedNode instead of container is critical for performance :(
        grabbedNode = target; 
        grabbedNode.style.cursor = grabbing; 
    };
    
    var stopgrab = function(){
        isgrabbing = false;
        if (grabbedNode) {
            grabbedNode.style.cursor = '';
            grabbedNode = null;
        }
    };

    var scrollTo = function(dx, dy){
        scrollBy(dx, dy);                        
    };
 
    container.mousedown(function(e){
        if (active) {
            startgrab(e.target);
            xp = e.pageX;
            yp = e.pageY;
        }
    })
    .mousemove(function(e){
        if (!isgrabbing) return true;
        scrollTo(xp - e.pageX, yp - e.pageY);
        xp = e.pageX;
        yp = e.pageY;
    })
    .mouseup(stopgrab)
    .mouseleave(stopgrab);
   
    var pub = {};
    pub.stop = function() {
        active = false;
        stopgrab();
    };
    pub.start = function() {
        active=true;
    };
    return pub;
}
