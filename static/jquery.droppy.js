/*
 * Droppy 0.1.2
 * (c) 2008 Jason Frame (jason@onehackoranother.com)
 * Ruined 2009 by Andrew Badr (andrewbadr@gmail.com)
 */

// Use string property access for compilation export
$['Menu'] = function(title, menu, opt_speed) {
	// `title` is $'d object of what should activate the menu
	// `menu` is the node w/the menu listed
	var speed = (opt_speed === undefined) ? 250 : opt_speed;
	
	function hideNow() {
		menu.slideUp(speed);
		title.removeClass('hover');
	}
	
    function hide() {
      $.data(menu, 'cancelHide', false);
      setTimeout(function() {
        if (!$.data(menu, 'cancelHide')) {
			hideNow();
        }
      }, 500);
    }
  
    function show() {
      $.data(menu, 'cancelHide', true);
      menu.slideDown(speed);
	  title.addClass('hover');
    }
 
	function initLi() {
		$(this).hover(
		  function() { $(this).addClass('hover'); $('> a', this).addClass('hover'); },
		  function() { $(this).removeClass('hover'); $('> a', this).removeClass('hover'); }
		);
	}
	
	title.hover(show, hide);
	menu.hover(show, hide);
	menu.find('li').each(initLi);
	menu.css('top', title.offset().top + title.outerHeight());
	$('li:not(:first)').css('borderTop', '1px solid #ccc')
	title.show();
	
	var pub = {};
	pub.addEntry = function(liContents) {
		// Takes a dom node to put inside the new LI
		menu.append('<li></li>');
		var newItem = menu.find('li:last');
		newItem.append(liContents);
		newItem.css('borderTop', '1px solid #ccc');
		initLi.call(newItem);
	};
	pub.close = hideNow;
	
	return pub;
};
