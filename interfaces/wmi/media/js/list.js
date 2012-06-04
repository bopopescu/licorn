/*
* Licorn list
* Copyright (C) 2011 Robin Lucbernet <robinlucbernet@gmail.com>
* Licensed under the terms of the GNU GPL version 2
*/

order_pic=[];
order_pic['asc'] = '<img src="/media/images/12x12/sort_asc.png" alt="asc order image">';
order_pic['desc'] = '<img src="/media/images/12x12/sort_desc.png" alt="desc order image">';

// time before the hover views appear
var list_hover_timeout_value = 250;

// holds the global setTimeout() result for the subcontent.
var hover_timeout = null;

function init_list_events(list_name, main_column, search_columns, identifier) {

	// initialize the list
	sort_items_list(list_name, 'asc', main_column, identifier);

	// search bar
	$('#'+list_name+'_list').find('#search_box').keyup(function(event) {
		search(list_name, $('#'+list_name+'_list').find('#search_box').val(), search_columns, identifier);
	});

	// header item click : sort
	$('#'+list_name+'_list').find(".list_header_item").click(function() {
		if (!$(this).hasClass('not_sortable')) {
			item_sort = $(this).attr("id");
			sort_way = $(this).attr("value");

			if (sort_way == 'desc') {
				new_sort = 'asc';
			}
			else {
				new_sort = 'desc';
			}

			$(this).attr("value", new_sort);

			// sort icons
			$('#'+list_name+'_list').find(".item_header_sort").html('');
			$(this).find(".item_header_sort").html(order_pic[sort_way]);

			sort_items_list(list_name, new_sort, item_sort);
		}
	});

	// init massive select
	$('#'+list_name+'_massive_delete').click(function() {
		items=[]
		$('#'+list_name+'_list').find(".row").each(function() {
			if ($(this).find('.'+list_name+'_checkbox').is(':checked') == true) {
				items.push($(this).find('.'+list_name+'_'+main_column).text());
			}
		});

		html = '<ul>'
		$.each(items, function(k, item) {
			html += '<li>'+item+'</li>';
		});
		html += '</ul>';
		delete_title = gettext("Massive removal");

		if (html == '<ul></ul>') {
			delete_content = gettext("Please select at least one account.");
			delete_dialog = new dialog(delete_title, delete_content);
		}
		else {
			delete_content = gettext("Are you sure you want to remove these account(s):");
			delete_content += html;
			delete_content += "<input type='checkbox' id='massive_delete_no_archive'/> <label for='massive_delete_no_archive'>" + gettext("Definitely remove account data (no archiving)") + "</label>";
			delete_dialog = new dialog(delete_title,delete_content,
				true, function() {
						items=[]
						$('#'+list_name+'_list').find(".row").each(function() {
							if ($(this).find('.'+list_name+'_checkbox').is(':checked') == true) {
								items.push($(this).find('.'+list_name+'_'+identifier).text());
								clear_sub_content_with_id($(this).find('.'+list_name+'_'+identifier).text())
							}
						});

						// check if 'no_archive' checkbox is checked
						//	the result will be interpretated in the core (python code):
						//	with python, empty strings are False, others strings are True
						if ($("#massive_delete_no_archive").attr('checked')) {
							no_archive = 'True';
						}
						else {
							no_archive = '';
						}
						page_url = "/"+list_name+"/massive/delete/" + $.URLEncode(items.join(',')) + "/" + no_archive;




						$.get(page_url);
					});
		}
		delete_dialog.show();
	});

	$('#'+list_name+'_massive_skel').click(function() {
		users=[]
		$('#'+list_name+'_list').find(".row").each(function() {
			if ($(this).find('.users_checkbox').is(':checked') == true) {
				users.push($(this).find('.users_login').text());
			}
		});

		users_selected_html = '<ul>'
		$.each(users, function(k, user) {
			users_selected_html += '<li>'+user+'</li>';
		});
		users_selected_html += '</ul>';
		skel_dialog_title = gettext("Massive skeleton reapplying");

		if (users_selected_html == '<ul></ul>') {
			skel_dialog_content =  gettext("Please select at least one user account.");
			skel_dialog = new dialog(skel_dialog_title,	skel_dialog_content);
			skel_dialog.show();
		}
		else {
			skel_dialog_content = gettext("Are you sure you want to reapply their skeleton to these user account(s):");
			skel_dialog_content += users_selected_html;
			$.get('/users/message/massive_skel/', function(html) {
				skel_dialog_content += html;
				skel_dialog = new dialog(skel_dialog_title,	skel_dialog_content,
					true, function() {
						users=[]
						$('#users_list').find(".row").each(function() {
							if ($(this).find('.users_checkbox').is(':checked') == true) {
								users.push($(this).find('.users_uidNumber').text());
							}
						});
						skel = $("#id_skel_to_apply").attr('value').toString();
						page_url = "/users/massive/skel/" + $.URLEncode(users.join(',')) + '/' + $.URLEncode(skel)
						$.get(page_url);
					});
				skel_dialog.show();
			});
		}
	});

	$('#'+list_name+'_massive_permissiveness').click(function() {
		groups=[]
		$('#'+list_name+'_list').find(".row").each(function() {
			if ($(this).find('.groups_checkbox').is(':checked') == true) {
				groups.push($(this).find('.groups_name').text());
			}
		});

		groups_selected_html = '<ul>'
		$.each(groups, function(k, g) {
			groups_selected_html += '<li>'+g+'</li>';
		});
		groups_selected_html += '</ul>';
		perm_dialog_title = gettext("Massive group premissiveness");

		if (groups_selected_html == '<ul></ul>') {
			perm_dialog_content =  gettext("Please select at least one group.");
			perm_dialog = new dialog(perm_dialog_title,	perm_dialog_content);
			perm_dialog.show();
		}
		else {
			perm_dialog_content = gettext("Are you sure you want to toggle permissiveness of group(s):");
			perm_dialog_content += groups_selected_html;

			perm_dialog = new dialog(perm_dialog_title,	perm_dialog_content,
				true, function() {
					groups=[]
					$('#'+list_name+'_list').find(".row").each(function() {
						if ($(this).find('.groups_checkbox').is(':checked') == true) {
							groups.push($(this).find('.groups_gidNumber').text());
						}
					});
					page_url = "/groups/massive/permissiveness/" + $.URLEncode(groups.join(','));
					$.get(page_url);
				});
			perm_dialog.show();

		}
	});

	$('#'+list_name+'_massive_select').click(function() {
		if ($(this).attr('checked') == 'checked') {
			checked = true;
		} else {
			checked = false;
		}
		$('#'+list_name+'_list').find('.'+list_name+'_checkbox').each( function() {
			if (! $(this).is(':disabled') && $(this).is(':visible')) {
				$(this).attr('checked', checked);
			}
		});
	});
}

function sort_items_list(list_name, sort_way, item_sort) {

	// keep a trace of the current sorted column
	$('#'+list_name+'_list').find('.current_sort').removeClass('current_sort');
	$("#"+ list_name +"_list").find('.header_' + item_sort).addClass('current_sort');

	//console.log('sorting on '+ item_sort +', '+ sort_way);

	// get a sorted list
	users_list_return = my_sort(list_name, sort_way, [item_sort]);

	hidden = 0;
	$.each(users_list_return, function(key, obj) {
		if ($(this).is(':hidden')) { hidden += 1; }
	});


	// 75ms * number of visible elements seems fine, because a human expects
	// 75ms * number of visible elements seems fine, because a human expects
	// a list to be sorted faster if there are fewer elements.
	effect_duration = 75 * (users_list_return.length - hidden);

	// but we need to floor and ceil the values, else it can be
	// too long or too fast to see the effect.
	if (effect_duration == 0)
		effect_duration = 100;

	if (effect_duration > 750)
		effect_duration = 750;

	final_width = $('#'+ list_name +'_list_header').width();

	css_classes = Array({
			'del_classes' : list_name + '_row_odd row_odd odd',
			'add_classes' : list_name + '_row_even row_even even'
		}, {
			'add_classes' : list_name + '_row_odd row_odd odd',
			'del_classes' : list_name + '_row_even row_even even'
		})
	cpt=0;

	$.each(users_list_return, function(key, obj) {
		the_div = $("#"+ list_name +"_list").find('#'+obj.id).filter('.'+list_name+'_row');

		final_position   = cpt*51+'px';
		current_position = the_div.css('margin-top');

		if (final_position == current_position) {
			the_div.css({ 'z-index': 5000 });
		} else {
			the_div.css({ 'z-index': key });
		}
		the_div.stop(true, true).animate({ 'margin-top': final_position },
						effect_duration * Math.random(),
						'swing').width(final_width);

		if(! the_div.is(':hidden')) {
			the_div.find('.odd_even_typed').each(function() {
				classes = css_classes[cpt%2];
				$(this).removeClass(classes.del_classes);
				$(this).addClass(classes.add_classes);
			});
			cpt +=1;
		}
	});
}

function search(list_name, search_string, search_columns, identifier) {

	var len = search_string.length;
	if (len == 0)
		len = 0.86;

	effect_duration = 650 / len;

	search_string = no_accent(search_string.toLowerCase());

	// this is used when reorganizing the visuals.
	compt = 0;

	// go through all attributes of each item, and keep only items
	// whose attributes (one or more) match.
	$("#"+ list_name +"_list").find('.'+ list_name +'_row').each(function() {
		// OBJECT part of the search.
		match = false;
		the_div = $(this);

		$.each(search_columns, function(k, v) {
			if (no_accent(the_div.find("."+ list_name +"_" + v).text().toLowerCase()).search(search_string) != -1) {
				match = true;

				// break the $.each(), no need to search further in this item.
				return false;
			}
		});

		// VISUAL / HTML part of the search.

		if (compt % 2 != 0) {
			add_classes = [ 'users_row_odd', 'row_odd', 'odd' ];
			del_classes = [ 'users_row_even', 'row_even', 'even' ];
		} else {
			del_classes = [ 'users_row_odd', 'row_odd', 'odd' ];
			add_classes = [ 'users_row_even', 'row_even', 'even' ];
		}

		if (match) {
			if (the_div.is(':hidden')) {
				the_div.stop(true, true).fadeIn(effect_duration).animate({'margin-top': compt*51+'px' },
									effect_duration * Math.random(), 'swing');
			} else {
				the_div.stop(true, true).animate({'margin-top': compt*51+'px' }, effect_duration * Math.random(), 'swing');
			}
			compt += 1;

			the_div.find('.odd_even_typed').each(function() {
				for (i=0; i<del_classes.length; i++) {
					$(this).removeClass(del_classes[i]);
				}
				for (i=0; i<add_classes.length; i++) {
					$(this).addClass(add_classes[i]);
				}
			});
		}
		else {
			the_div.stop(true, true).fadeOut(effect_duration);
		}
	});
	sort_items_list($('#'+list_name+'_list').find('.current_sort').attr('value'),
		$('#'+list_name+'_list').find('.current_sort').attr('id'), identifier);

}

function my_sort(list_name, sort_way, sort_item) {

	items = $("#"+ list_name +"_list").find('.row')

	items.sort(function(a, b) {
		// run through each selector, and return first non-zero match

			var first = $(a).find("."+ list_name + "_" + sort_item).html().toLowerCase();
			var second = $(b).find("."+ list_name +"_" + sort_item).html().toLowerCase();

			var isNumeric = Number(first) && Number(second);
			if(isNumeric) {
				(sort_way == 'asc') ? diff=first-second : diff=second-first;

				if(diff != 0) {
					return diff;
				}
			}

			else if(first != second) {
				(sort_way == 'asc') ? r=(first<second) ? -1 : 1 : r=first>second ? -1 : 1;
				return r;
		}

		return 0;
	});

	return items;
}

function select_row(list_name, id) {
	unselect_row();
	div = $('#'+list_name+'_list').find('.row').filter("#"+id);
	div.addClass('item_selected');
	div.children().addClass('bkg_selected');
	div.find('.'+list_name+'_content').children().addClass('bkg_selected');
	div.find(".item_menu").show();
}
function unselect_row() {
	$('.item_selected').removeClass('item_selected');
	$('.bkg_selected').removeClass('bkg_selected');
	$(".item_menu").hide();
}

function add_row(list_name, html, append_after) {
	//console.log('add_row ' + list_name + ' ' + html);

	list = $("#"+ list_name +"_list");

	//console.log(list);

	if (typeof(append_after) == 'undefined') {
		list.find('.list_items').append(html);

	} else {
		list.find(append_after).after(html);

	}

	if (list.hasClass('ajax-content-resizable')) {
		content_width = list.find('.list_header').width();
		list.find('.row').width(content_width);
	}

	if (list.hasClass('ajax-sortable')) {
		sort_items_list(list_name,
			list.find('.current_sort').attr('value'),
			list.find('.current_sort').attr('id'));
	}
}
function del_row(list_name, id) {
	list = $("#"+ list_name +"_list");

	list.find('#'+id).filter('.'+list_name+'_row').remove();

	if (list.hasClass('ajax-sortable')) {
		sort_items_list(list_name,
			list.find('.current_sort').attr('value'),
			list.find('.current_sort').attr('id'));
	}
}
function update_row_value(list_name, id, col_name, value, css_classes) {

	the_span = $("#"+ list_name +"_list")
				.find('#'+id)
				.filter('.'+list_name+'_row')
				.find('.'+list_name+'_'+col_name);

	the_span.html(value);

	if (typeof css_classes != 'undefined') {

		for (var i=0, l=css_classes.length; i<l; i++) {
			the_class = css_classes[i];

			if (the_class[0] == '+') {
				the_span.addClass(the_class.slice(1));
			} else {
				the_span.removeClass(the_class.slice(1));
			}
		}
	}
}
function change_locked_state(list_name, id, locked) {
	user_locked = $("#users_list").find('#'+id).filter('.users_row').find('.users_locked');

	user_locked.html(generate_locked_img('out', locked));

	if (locked) {
		user_locked.addClass('is_locked');
	} else {
		user_locked.removeClass('is_locked');
	}
}
function change_permissive_state(id, permissive) {
	g_perm = $("#groups_list").find('#'+id).filter('.groups_row').find('.groups_permissive');

	g_perm.html(generate_permissive_img('out', permissive));

	if (permissive) {
		g_perm.addClass('is_permissive');
	} else {
		g_perm.removeClass('is_permissive');
	}
}

relationships = [ 'no_membership', 'guest', 'member', 'resp' ]

function update_relationship(name, user_id, group_id, rel_id) {

	//console.log(name);
	//console.log(user_id);
	//console.log(group_id);
	//console.log(rel_id);
	//console.log(typeof(rel_id));

	if (typeof(rel_id) == "number") {
		new_rel = relationships[rel_id];
	} else {
		new_rel = rel_id
	}

	name = $('#click_item_id').text();

	if (name == 'user') {
		item_id = user_id
	} else {
		item_id = group_id
	}

	div = $('#sub_content').find('#'+item_id).filter('.click_item');

	popover = $('.popover_item').filter('#'+item_id).parent();

	hidden_input = div.find('input[name$="' + new_rel + '_' + name + 's"]');

	popover.children().show();
	popover.find('.rel_'+new_rel).hide();

	//console.log(1);

	div.attr('value', new_rel)
	div.find('.item_hidden_input').attr('value', ''); // erase old membership
	hidden_input.attr('value', item_id); // update new membership

	//console.log(2);

	div.find('.item_title')
		.removeClass('no_membership_bkg guest_bkg member_bkg resp_bkg')
		.addClass(new_rel+'_bkg');
}