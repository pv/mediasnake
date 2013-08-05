var bookmark = (function() {
    var bookmark_url;

    var init = function(new_bookmark_url) {
	bookmark_url = new_bookmark_url;
	focusBookmark();
	reinit();
    }

    var reinit = function () {
	$("#ebook-text p").click(function () {
	    updateBookmark($(this).attr("data-line"));
	    return true;
	});
    };

    var focusBookmark = function () {
	$.get(bookmark_url, function (data) {
	    if (!data["error"]) {
		var element = $("#ebook-text p[data-line=" + data["paragraph"] + "]");
		$("html, body").scrollTop(element.offset().top);
		updateBookmark(data["paragraph"]);
	    }
	});
    };

    var updateBookmark = function (paragraph) {
	$.post(bookmark_url, { "paragraph": paragraph });
    };

    return { init: init, reinit: reinit };
})();
