var study = (function() {
    var words;
    var known;
    var language;

    var init = function(token_url, language) {
	if (!language) {
	    location.reload();
	    return;
	}

	language = language;

	$.get(token_url.replace("@language@", language), function (data) {
	    $("#ebook-text").html(data["html"]);
	    words = data['words'];
	    known = data['known'];
	    updateWordKnowledge();
	});
    };

    var updateWordKnowledge = function() {
	$("#ebook-text span").each(function () {
	    var w = $(this).attr('data-src');
	    $(this).removeClass("known-0 known-1 known-2 known-3 known-4 known-5");
	    $(this).addClass("known-" + known[words.indexOf(w)]);
	});
    };

    return { init: init };
})();
