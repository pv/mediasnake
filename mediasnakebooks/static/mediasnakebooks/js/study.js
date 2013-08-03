var study = (function() {
    var words;
    var known;
    var language;
    var dict_url;
    var external_dict_url;
    var word_url;
    var words_url;

    var init = function(new_language, new_token_url, new_dict_url, new_external_dict_url, new_word_url, new_words_url) {
	if (!new_language) {
	    location.reload();
	    return;
	}

	language = new_language;
	dict_url = new_dict_url;
	external_dict_url = new_external_dict_url;
	word_url = new_word_url;
	words_url = new_words_url;

	$.get(new_token_url, function (data) {
	    $("#ebook-text").html(data["html"]);

	    $.post(words_url, { "words": data["words"] }, function (data) { 
		words = data['words'];
		known = data['known'];
		updateWordKnowledge();
	    });
	});
    };

    var dictLookup = function(word, callback) {
	$.get(dict_url.replace('@WORD@', word), callback);
    }

    var updateWordKnowledge = function() {
	$("#ebook-text span").each(function () {
	    var w = $(this).attr('data-src');
	    if (w) {
		$(this).removeClass("known-0 known-1 known-2 known-3 known-4 known-5");
		$(this).addClass("word known-" + known[words.indexOf(w)]);
	    }
	});

	$("#ebook-text span.word").click(function() {
	    var word = $(this).attr('data-src');
	    var entry = this;

	    if (!word) {
		return;
	    }

	    popupWordModal(word);
	});
    };

    var popupWordModal = function(word) {
	$("#modal-word-header").text(word);
	html = "<div class=\"controls\">";
	html = html + "<a class=\"btn btn-known-5\" onclick=\"study.adjust('" + escape(word) + "', 5);\">[Unk]</a> ";
	html = html + "<a class=\"btn btn-known-4\" onclick=\"study.adjust('" + escape(word) + "', 4);\">[4]</a> ";
	html = html + "<a class=\"btn btn-known-3\" onclick=\"study.adjust('" + escape(word) + "', 3);\">[3]</a> ";
	html = html + "<a class=\"btn btn-known-2\" onclick=\"study.adjust('" + escape(word) + "', 2);\">[2]</a> ";
	html = html + "<a class=\"btn btn-known-1\" onclick=\"study.adjust('" + escape(word) + "', 1);\">[1]</a> ";
	html = html + "<a class=\"btn btn-known-0\" onclick=\"study.adjust('" + escape(word) + "', 0);\">[Ign]</a> ";
	html = html + "</div>";

	if (external_dict_url) {
	    var url;
	    url = external_dict_url.replace('@WORD@', word).replace('@word@', word);
	    html = html + "<div><a class=\"btn btn-link pull-right\" target=\"_blank\" href=\"" + url + "\">External dictionary</a><div>";
	}

	html = html + "<pre id=\"modal-word-dictionary\"></pre>";
	$("#modal-word-body").html(html);

	dictLookup(word, function(data) {
	    if (!data['error']) {
		$("#modal-word-dictionary").text(data["text"]);
	    }
	    else {
		$("#modal-word-dictionary").text("Dictionary lookup failed: " + data["text"]);
	    }
	});

	$("#modal-word").modal();
    }

    var adjust = function (word, level) {
	var entry = this;
	word = unescape(word);
	$.post(word_url.replace('@WORD@', word),  { "level": level }, function(data) {
	    if (data["word"]) {
		var w = data["word"];
		var level = data["level"];
		var selector = ".word[data-src=\"" + w + "\"]";
		known[words.indexOf(w)] = level;
		$(selector).removeClass("known-0 known-1 known-2 known-3 known-4 known-5");
		$(selector).addClass("word known-" + known[words.indexOf(w)]);
	    }
	});
	$("#modal-word").modal("hide");
    }

    $.ajaxSetup({ 
	beforeSend: function(xhr, settings) {
	    function getCookie(name) {
		var cookieValue = null;
		if (document.cookie && document.cookie != '') {
                    var cookies = document.cookie.split(';');
                    for (var i = 0; i < cookies.length; i++) {
			var cookie = jQuery.trim(cookies[i]);
			// Does this cookie string begin with the name we want?
			if (cookie.substring(0, name.length + 1) == (name + '=')) {
			    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
			    break;
			}
		    }
		}
		return cookieValue;
            }
            if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
		// Only send the token to relative URLs i.e. locally.
		xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
            }
	} 
    });

    return { init: init, adjust: adjust };
})();
