var study = (function() {
    var words;
    var known;
    var notes;
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
	if (new_external_dict_url == 'None') {
	    external_dict_url = "";
	}
	else {
	    external_dict_url = new_external_dict_url;
	}
	word_url = new_word_url;
	words_url = new_words_url;

	$.get(new_token_url, function (data) {
	    $("#ebook-text").html(data["html"]);
	    bookmark.reinit();

	    $.post(words_url, { "words": data["words"] }, function (data) { 
		words = data['words'];
		known = data['known'];
		notes = data['notes'];
		updateWordKnowledge();
	    });
	});
    };

    var dictLookup = function(word, callback) {
	base_word = word.replace(/\[.*\]/, "");
	$.get(dict_url.replace('@WORD@', base_word), callback);
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
		return true;
	    }

	    popupWordModal(word);
	    return true;
	});
    };

    var popupWordModal = function(word) {
	$("#modal-word-header").text(word);
	$("#modal-word-word").attr("value", word);

	if (external_dict_url) {
	    var url;
	    base_word = word.replace(/\[.*\]/, "");
	    url = external_dict_url.replace('@WORD@', base_word).replace('@word@', base_word);
	    $("#modal-word-external-dict").attr('href', url);
	    $("#modal-word-external-dict").removeClass('hide');
	}
	else {
	    $("#modal-word-external-dict").addClass('hide');
	}

	$(".modal-word-known").removeClass('active');
	level = known[words.indexOf(word)];
	$("#modal-word-known-" + level).addClass('active');

	note = notes[words.indexOf(word)];
	if (!note) {
	    note = "";
	}
	$("#modal-word-notes").val(note);

	$("#modal-word-dict").text("<Loading dictionary...>");

	dictLookup(word, function(data) {
	    base_word = $("#modal-word-word").attr("value").replace(/\[.*\]/, "");
	    if (data['word'] == base_word) {
		if (!data['error']) {
		    $("#modal-word-dict").text(data["text"]);
		}
		else {
		    $("#modal-word-dict").text("Dictionary lookup failed: " + data["text"]);
		}
	    }
	});

	$("#modal-word").modal();
    }

    var adjust = function () {
	var word, level, note, data;

	word = $("#modal-word-word").attr("value");
	note = $("#modal-word-notes").val();

	$("#modal-word .modal-word-known.active").each(function () {
	    level = $(this).attr("value");
	});

	data = { "known": level, "notes": note };

	$.post(word_url.replace('@WORD@', word), data, function(data) {
	    if (!data["error"]) {
		var selector = ".word[data-src=\"" + word + "\"]";
		var j = words.indexOf(word);
		known[j] = level;
		notes[j] = note;
		$(selector).removeClass("known-0 known-1 known-2 known-3 known-4 known-5");
		$(selector).addClass("word known-" + known[j]);
	    }
	});
	$("#modal-word").modal("hide");
    }

    return { init: init, adjust: adjust };
})();
