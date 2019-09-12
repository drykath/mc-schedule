$(function () {
  // Grid view, show the requested tab
  if (window.location.hash && $('li.tab a[href="' + window.location.hash + '"]').length == 1) {
    $('li.tab a[href="' + window.location.hash + '"]').tab('show');
  }
  /* Disabled for now...
  $('li.tab a').click(function(e) {
    //window.location.hash = this.dataset.long.toLowerCase();
  });
  */
  $('[data-toggle="popover"]').popover().on('inserted.bs.popover', function () {
    var o = $(this);
    var p = $('#' + $(this).attr('aria-describedby'));
    fixPrefLinks(p, o, o);
  });
  fixPrefLinks($('div.panel-content'), null);
  if ($(window).width() < 400) {
    $('li.tab a').each(function() {
      var a = $(this);
      a.text(a.data('short'));
    });
  }
  $('body').on('click', function(e) {
    $('[data-toggle="popover"],[data-original-title]').each(function() {
      if (!$(this).is(e.target) && $(this).has(e.target).length === 0 && $('.popover').has(e.target).length === 0) {
        (($(this).popover('hide').data('bs.popover')||{}).inState||{}).click = false;
      }
    });
  });

  // Grid view browser display helper
  function reset_schedule_height() {
    var div;
    $('div.grid-item').each(function() {
      div = $(this);
      div.height(div.closest('td').height() - 4);
    });
  }
  reset_schedule_height();
  $('a[data-toggle="tab"]').on('shown.bs.tab', reset_schedule_height);

  $('table.gridschedule').floatThead({
    responsiveContainer: function($table) {
      return $table.closest('div.widetable');
    },
    top: 40
  });

  // Mouse horizontal grab-and-scroll for the grid schedule
  var mDown = false, mXPos = 0;
  $('table.gridschedule').mousedown(function(m) {
    mDown = true;
    mXPos = m.pageX;
  }).mouseup(function() {
    mDown = false;
  }).mousemove(function(m) {
    if (mDown === true) {
      $(this.parentElement).scrollLeft($(this.parentElement).scrollLeft() + (mXPos - m.pageX));
      mXPos = m.pageX;
    }
  });

  /* Scroll schedule to fill view, disabled for now...
  $('html,body').animate({
    scrollTop: ($('.nav-tabs').offset().top - 50) + 'px'
  }, 'fast');*/
  /* Affix needs some work
  var navtabs = $('#navtabs');
  navtabs.affix({
    offset: {
      top: function() {
        return navtabs[0].offsetTop - 50;
      }
    }
  });*/
});

function fixPrefLinks(p, o, initial=true) {
  // In case we need to override which link is shown
  switch (p.data('starred')) {
    case 'true':
    p.find('a.setpref[data-pref="star"]').hide();
    p.find('a.setpref[data-pref="unstar"]').show();
    break;
    case 'false':
    p.find('a.setpref[data-pref="star"]').show();
    p.find('a.setpref[data-pref="unstar"]').hide();
    break;
  }
  switch (p.data('hide')) {
    case 'true':
    p.find('a.setpref[data-pref="hide"]').hide();
    p.find('a.setpref[data-pref="unhide"]').show();
    break;
    case 'false':
    p.find('a.setpref[data-pref="hide"]').show();
    p.find('a.setpref[data-pref="unhide"]').hide();
    break;
  }
  if (initial) {
    p.find('a.setpref').click(function (e) {
      var picon = $('span.icon_' + $(this).data('panel'));
      var thislink = $(this);
      e.preventDefault();
      $.get($(this).attr('href'),
        function(data) {
          switch (thislink.data('pref')) {
            case 'star':
            picon.removeClass('glyphicon-remove').addClass('glyphicon-star');
            p.data('starred', 'true');
            p.data('hide', 'false');
            break;

            case 'unstar':
            picon.removeClass('glyphicon-star');
            p.data('starred', 'false');
            break;

            case 'hide':
            picon.removeClass('glyphicon-star').addClass('glyphicon-remove');
            p.data('hide', 'true');
            p.data('starred', 'false');
            break;

            case 'unhide':
            picon.removeClass('glyphicon-remove');
            p.data('hide', 'false');
            break;
          }
          fixPrefLinks(p, null, false);
        }
      );
    });
    p.find('button').click(function (e) {
      var form = $(p.find('form'));
      var picon = $('span.icon_' + form.data('panel'));
      e.preventDefault();
      $.post(form.attr('action'), form.serialize(), function () {
        picon.removeClass('glyphicon-remove glyphicon-star').addClass('glyphicon-ok');
        if (o) {
          o.popover('hide');
        }
      });
    });
  }
}

function copyIcsLink() {
  document.getElementById('ics-link').select();
  document.execCommand('copy');
}
