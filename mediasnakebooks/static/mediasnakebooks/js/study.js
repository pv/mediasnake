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

	$("#ebook-text").addClass("big-text");

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
	    var context = $(this).parent().html();
	    var word = $(this).attr('data-src');
	    var entry = this;

	    if (!word) {
		return true;
	    }

	    popupWordModal(word, context);
	    return true;
	});
    };

    var popupWordModal = function(word, context) {
	var level, note, j;

	base_word = word.replace(/\[.*\]/, "");
	$("#modal-word-header").text(base_word);
	$("#modal-word-word").attr("value", word);
	$("#modal-word-context").attr("value", context);

	j = words.indexOf(word);
    
	// Load word from external dictionary
	if (external_dict_url) {
	    var url, base_word;
	    base_word = word.replace(/\[.*\]/, "");
	    url = external_dict_url.replace('@WORD@', base_word).replace('@word@', base_word);
	    $("#modal-word-external-dict").attr('href', url);
	    $("#modal-word-external-dict").removeClass('hide');
	}
	else {
	    $("#modal-word-external-dict").addClass('hide');
	}

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

	// Load notes
	note = notes[j];
	if (!note) {
	    note = "";
	}
	$("#modal-word-notes").val(note);

	// Update buttons
	level = known[j];
	$("#modal-word-known-group .btn").removeClass("btn-known-0 btn-known-1 btn-known-2 btn-known-3 btn-known-4 btn-known-5");
	$("#modal-word-known").addClass("btn-known-" + getNextLevel(level, 1));
	$("#modal-word-unknown").addClass("btn-known-" + getNextLevel(level, 0));
	$("#modal-word-ignore").addClass("btn-known-" + getNextLevel(level, -1));

	// Show dialog
	$("#modal-word-buttons").show();
	$("#modal-word-answer").hide();
	$("#modal-word").modal();
    }

    var getNextLevel = function(level, isKnown) {
	if (isKnown == 1) {
	    if (level > 1) {
		level = level - 1;
	    }
	    else if (level == 1) {
		// Noop
	    }
	    else {
		level = 4;
	    }
	}
	else if (isKnown == -1) {
	    level = 0;
	}
	else {
	    if (level < 4 && level >= 1) {
		level = level + 1;
	    }
	    else if (level == 4) {
		// Noop
	    }
	    else {
		level = 4;
	    }
	}
	return level;
    }

    var markKnown = function(isKnown, doClose) {
	var j, word;

	word = $("#modal-word-word").attr("value");
	j = words.indexOf(word)
	level = getNextLevel(known[j], isKnown);
	known[j] = level;

	save();

	if (isKnown == 0) {
	    $("#modal-word-buttons").hide();
	    $("#modal-word-unknown2").hide();
	    $("#modal-word-known2").show();
	    $("#modal-word-answer").show();
	}
	else if (isKnown == 1) {
	    $("#modal-word-buttons").hide();
	    $("#modal-word-unknown2").show();
	    $("#modal-word-known2").hide();
	    $("#modal-word-answer").show();
	}
	else {
	    $("#modal-word").modal("hide");
	}
	if (doClose) {
	    $("#modal-word").modal("hide");
	}
    }

    var save = function () {
	var word, level, note, data, j;

	word = $("#modal-word-word").attr("value");
	context = $("#modal-word-context").attr("value");
	note = $("#modal-word-notes").val();
	j = words.indexOf(word);
	level = known[j];

	data = { "known": level, "notes": note, "context": context };

	$.post(word_url.replace('@WORD@', word), data, function(data) {
	    if (!data["error"]) {
		var selector = ".word[data-src=\"" + word + "\"]";
		var j = words.indexOf(word);
		notes[j] = note;
		$(selector).removeClass("known-0 known-1 known-2 known-3 known-4 known-5");
		$(selector).addClass("word known-" + known[j]);
	    }
	});
    }

    var saveAndHide = function() {
	save();
	$("#modal-word").modal("hide");
    }

    return { init: init, markKnown: markKnown, saveAndHide: saveAndHide };
})();
