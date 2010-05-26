// Utility function, to call a function with the given scope
function bind(scope, fn) {
    return function() {
	return fn.apply(scope, arguments);
    };
}

// An EventPainter object is used to keep track of each of two
// columns of event labels. An EventPainter tracks a filtered
// subset of an event log, with the current previous and next
// Y positions.
function EventPainter(params) {
    this._init(params);
}

// We don't draw a label unless there is this much separation
// above and below to adjacent events
var LABEL_SPACE = 10;

EventPainter.prototype = {
    _init: function(params) {
	this.log = params.log;

	this.getPos = params.getPos;
	this.predicate = params.predicate;
	this.paintLine = params.paintLine;
	this.paintLabel = params.paintLabel;

	this.i = null;
	this.nextI = -1;
	this.pos = null;
	this.lastPos = null;
	this.lastLabelPos = null;
	this.nextPos = null;

	this.advance();
	this.advance();
    },

    advance: function() {
	if (this.nextI == null)
	    return;

	this.lastPos = this.pos;
	this.i = this.nextI;
	this.pos = this.nextPos;

	this.nextI += 1;
	while (this.nextI < this.log.length) {
	    var e = this.log[this.nextI];
	    if (this.predicate(e)) {
		this.nextPos = this.getPos(e[0]);
		return;
	    }

	    this.nextI += 1;
	}

	this.nextI = null;
	this.nextPos = null;
    },

    paint: function() {
	var label;
	if ((this.lastPos == null || this.pos - this.lastPos > LABEL_SPACE) &&
	    (this.nextPos == null || this.nextPos - this.pos > LABEL_SPACE)) {
	    label = this.log[this.i][1];
	} else {
	    if (this.lastLabelPos == null || this.pos - this.lastLabelPos > LABEL_SPACE)
		label = '<...>';
	    else
		label = null;
	}

	if (label != null) {
	    this.paintLabel(this.pos, label);
	    this.lastLabelPos = this.pos;
	}

	this.paintLine(this.pos);
    }
};

// An EventRun object holds information about one of the runs of data in
// an uploaded report

function EventRun(log, events) {
    this._init(log, events);
}

EventRun.prototype = {
    _init: function(log, events) {
	this.log = log;
	this.events = events;
	this.prepared = false;

	this.statistics = null;
	this.statTimes = null;
	this.start = null;
	this.range = null;
    },

    // The prepare step does precomputation work from the raw data we got as JSON
    //
    // - We munge times in the log to be float seconds since start of the run
    //   rather than 64-bit microseconds since the epoch
    // - We collect statistics times and values
    // - We determine the [start,end] range of times
    //
    prepare: function() {
	var name;
	var event;

	if (this.prepared)
	    return;

	this.prepared = true;

	this.statistics = {};
	this.statTimes = [];

	for (name in this.events) {
	    event = this.events[name];
	    if (event.statistic) {
		this.statistics[event.name] = {
		    minValue: null,
		    maxValue: null,
		    currentValue: null,
		    values: []
		};
	    }
	}

	var i;
	var time;
	var start = null;

	for (i = 0; i < this.log.length; i++) {
	    var e = this.log[i];

	    if (start == null) {
		start = e[0];
		e[0] = time = 0;
	    } else {
		e[0] = time = (e[0] - start) / 1000000;
	    }

	    name = e[1];

	    var statistic = this.statistics[name];
	    if (statistic !== undefined) {
		var value = e[2];
		if (statistic.currentValue == null) {
		    statistic.minValue = statistic.maxValue = value;
		} else {
		    statistic.minValue = Math.min(statistic.minValue, value);
		    statistic.maxValue = Math.max(statistic.maxValue, value);
		}
		statistic.currentValue = value;
	    }

	    // perf.statisticsCollected is stored every time we collect
	    // statistics, but repeated values are omitted, so store
	    // *all* values into the arrays we are collecting
	    if (event.name == 'perf.statisticsCollected') {
		this.statTimes.push(time);
		for (name in this.statistics) {
		    statistic = this.statistics[name];
		    statistic.values.push(event.currentValue);
		}
	    }

	    if (event.name == 'glx.swapComplete') {
		// the argument is a time in microseconds since epoch
		e[2] = (e[2] - start) / 1000000;
	    }
	}

	this.range = time;
    }
};

// The LogViewer class adds event log behavior to the canvas
function LogViewer(canvas) {
    this._init(canvas);
}

LogViewer.prototype = {
    _init: function(canvas) {
	this.canvas = canvas;
	this.run = null;

	this.canvas.addEventListener('mousedown',
	                             bind(this, this._onMouseDown),
				     false);
	this.canvas.addEventListener('DOMMouseScroll',
	                             bind(this, this._onMouseScroll),
				     true);
    },

    // Load the given URL into the report log
    load: function(reportUrl) {
	var req = new XMLHttpRequest();
	req.open("GET", reportUrl);
	req.send();

	var me = this;
	req.onreadystatechange = function() {
	    me._onReadyStateChange(this);
	};

	var context = this.canvas.getContext('2d');

	this._showMessage("Loading...");
    },

    _onReadyStateChange: function(req) {
	if (req.readyState != 4) // DONE
	    return;

	if (req.status != 200) {
	    this._showMessage("Couldn't load log");
	    return;
	}

	try {
	    var report = JSON.parse(req.responseText);
	    var i;

	    var events = report['events'];
	    this.events = {};
	    for (i = 0; i < events.length; i++) {
		var event = events[i];
		this.events[event.name] = event;
	    }

	    var logs = report['logs'];
	    this.runs = [];
	    for (i = 0; i < logs.length; i++)
		this.runs.push(new EventRun(logs[i], events));
	} catch(e) {
	    this._showMessage("Malformed log");
	    return;
	}

	this.setRun(0);
    },

    _clampBounds: function() {
	if (this.zoomStart < 0) {
	    this.zoomEnd += - this.zoomStart;
	    this.zoomStart = 0;
	} else if (this.zoomEnd > this.run.range) {
	    this.zoomStart -= this.zoomEnd - this.run.range;
	    this.zoomEnd = this.run.range;
	}
    },

    // Zoom in by the specified zoom factor, centering the zoom
    // around the given y. If y is not given, then the center
    // of the canvas area is used.
    zoom: function(scale, y) {
	var range = this.zoomEnd - this.zoomStart;
	var height = this.canvas.height;
	if (y == null)
	    y = height / 2;

	var clickTime = this.zoomStart + range * y / height;

	var factor = 1 / scale;

	this.zoomStart = this.zoomStart * factor + clickTime * (1 - factor);
	this.zoomEnd = this.zoomEnd * factor + clickTime * (1 - factor);

	if (this.zoomEnd - this.zoomStart > this.run.range) {
	    this.zoomStart = 0;
	    this.zoomEnd = this.run.range;
	}

	this._clampBounds();
	this.redraw();
    },

    // Translate the coordinates from an event to be stage relative
    _eventCoords: function(e) {
	var x = e.clientX + window.scrollX;
	var y = e.clientY + window.scrollY;

	var el = this.canvas;
	do {
	    x -= el.offsetLeft;
	    y -= el.offsetTop;
	    el = el.offsetParent;
	} while (el);

	return {x: x, y: y};
    },

    _onMouseDown: function(e) {
	e.preventDefault();
	e.stopPropagation();

	if (e.button != 0)
	    return;

	var coords = this._eventCoords(e);
	var x = coords.x;
	var y = coords.y;

	this._inDrag = true;

	var mode;
	if (x >= this.zoomScrollX && x < this.zoomScrollX + this.zoomScrollWidth) {
	    if (y >= this.zoomScrollY && y < this.zoomScrollY + this.zoomScrollHeight) {
		mode = 'handle';
	    } else {
		mode = 'trough';
	    }
	} else {
	    mode = 'grab';
	}

	var me = this;
	var dragZoomStart = this.zoomStart;
	var zoomRange = (this.zoomEnd - this.zoomStart);

	function scroll(newStart) {
	    me.zoomStart = newStart;
	    me.zoomEnd = newStart + zoomRange;
	    me._clampBounds();
	    me.redraw();
	}

	var dragUpdate;

	switch (mode) {
	case 'handle':
	    dragUpdate = function(newY) {
		var delta = me.run.range * (newY - y) / me.canvas.height;
		scroll(dragZoomStart + delta);
	    };
	    break;
	case 'trough':
	    dragUpdate = function(newY) {
		var center = me.run.range * newY / me.canvas.height;
		scroll(center - zoomRange / 2);
	    };
	    dragUpdate(y); // Move immediately to click position
	    break;
	case 'grab':
	    dragUpdate = function(newY) {
		var delta = zoomRange * (newY - y) / me.canvas.height;
		scroll(dragZoomStart - delta);
	    };
	    break;
	}

	// We want to get mouse events even if the mouse leaves the
	// canvas. Using capturing phase events on the body didn't
	// work fully as expected, so create a div that covers
	// the entire window content and take events on that.
	//
	// The downside is that this breaks double-click handling -
	// the only fix I can think of for that is to handle double
	// clicks ourselves, looking at the event timestamp.
	// Which then means ignoring the system setting. When I
	// implemented it before, double click to zoom in wasn't
	// that useful anyways because there was no way to zoom out.

	var grabDiv = document.createElement("div");
	grabDiv.className = "grab";
	document.body.appendChild(grabDiv);

	function onMouseMove(e) {
	    e.stopPropagation();
	    dragUpdate(me._eventCoords(e).y);
	}

	function onMouseUp(e) {
	    e.stopPropagation();

	    if (e.button != 0)
		return;

	    dragUpdate(me._eventCoords(e).y);
	    grabDiv.removeEventListener('mousemove', onMouseMove, false);
	    grabDiv.removeEventListener('mouseup', onMouseUp, false);
	    document.body.removeChild(grabDiv);
	}

	grabDiv.addEventListener('mousemove', onMouseMove, false);
	grabDiv.addEventListener('mouseup', onMouseUp, false);
    },

    _onMouseScroll: function(e) {
	e.preventDefault();
	e.stopPropagation();
	this.zoom(Math.pow(1.5, - e.detail / 3),
	          this._eventCoords(e).y);
    },

    _showMessage: function(msg) {
	var context = this.canvas.getContext('2d');

	context.clearRect(0, 0, this.canvas.width, this.canvas.height);

	context.save();
	context.font = '50px sans-serif';
	context.textAlign = 'center';
	context.textBaseline = 'middle';
	context.fillStyle = "#888888";
	context.fillText(msg, this.canvas.width / 2, this.canvas.height / 2);
	context.restore();
    },

    redraw: function() {
	if (!this.run)
	    return;

	var context = this.canvas.getContext('2d');
	var width = this.canvas.width;
	var height = this.canvas.height;

	context.clearRect(0, 0, width, height);
	context.textBaseline = 'middle';

	// Layout and paint "scrollbar""

	this.zoomScrollX = 0;
	this.zoomScrollY = Math.round(height * this.zoomStart / this.run.range);
	this.zoomScrollWidth = 20;
	this.zoomScrollHeight = Math.round(height * (this.zoomEnd - this.zoomStart) / this.run.range);

	context.save();
	context.fillRect(20, 0, 1, height);
	context.fillRect(0, this.zoomScrollY - 1, 20, 1);
	context.fillRect(0, this.zoomScrollY + this.zoomScrollHeight, 20, 1);
	context.fillStyle = "#ff8844";
	context.fillRect(0, this.zoomScrollY, 20, this.zoomScrollHeight);
	context.restore();

	// Paint the entire set of ticks over the scrollbar for context

	var lastY = null;
	for (i = 0; i < this.run.log.length; i++) {
	    var e = this.run.log[i];
	    var y =  Math.floor(height * e[0] / this.run.range);
	    if (y != lastY) {
		context.fillRect(0, y, 20, 1);
		lastY = y;
	    }
	}

	// Paint the main part of the event log - the high-level script events
	// on the left, the remaining events on the right

	var me = this;
	function getY(t) {
	    return Math.floor(height * (t - me.zoomStart) / (me.zoomEnd - me.zoomStart));
	}

	var scriptPainter = new EventPainter({
	    log: this.run.log,
	    getPos: getY,
	    predicate: function(e) {
		return /^script\./.test(e[1]);
	    },
	    paintLine: function(pos) {
		context.save();
		context.fillStyle = '#0000ff';
		context.fillRect(width / 4, pos, width / 4, 1);
		context.restore();
		lastY = pos;
	    },
	    paintLabel: function(pos, label) {
		context.save();
		context.textAlign = 'right';
		context.fillStyle = '#0000ff';
		context.fillText(label, width / 4 - 5, pos);
		context.restore();
	    }
	});

	var detailPainter = new EventPainter({
	    log: this.run.log,
	    getPos: getY,
	    predicate: function(e) {
		return !/^script\./.test(e[1]);
	    },
	    paintLine: function(pos) {
		if (pos != lastY)
		    context.fillRect(width / 4, pos, width / 4, 1);

		lastY = pos;
	    },
	    paintLabel: function(pos, label) {
		context.fillText(label, 2 * width / 4 + 5, pos);
	    }
	});

	var i;

	// As we paint the event log, we note frame completion events
	// so we can try and show the vblank intervals
	var lastVblank = null;
	var prevVblank = null;

	lastY = null;
	for (i = 0; i < this.run.log.length; i++) {
	    var painter;
	    var vblankTime = null;
	    var e = this.run.log[i];

	    if (i == detailPainter.i) {
		if (detailPainter.pos >= height)
		    break;

		if (detailPainter.pos >= 0)
		    detailPainter.paint();

		detailPainter.advance();
	    }

	    if (i == scriptPainter.i) {
		if (scriptPainter.pos >= height)
		    break;

		if (scriptPainter.pos >= 0)
		    scriptPainter.paint();

		scriptPainter.advance();
	    }

	    var name = e[1];
	    if (name == 'glx.swapComplete' && e[2] != 0) {
		prevVblank = lastVblank;
		lastVblank = e[2];
	    }
	}

	var range = this.zoomEnd - this.zoomStart;

	if (prevVblank != null && lastVblank != null) {
	    // The interval between two swap completion events is some multiple
	    // of the vblank interval. The real interval is likely around 60H

	    var rawInterval = lastVblank - prevVblank;
	    var STANDARD_INTERVAL = 1 / 60;

	    var mult = Math.round(rawInterval / STANDARD_INTERVAL);
	    var interval = rawInterval / Math.max(mult, 1);

	    context.save();
	    context.fillStyle = "#ff8800";
	    context.textBaseline = 'middle';

	    if (interval > range / 20) {
		var vt = lastVblank + interval * Math.floor((this.zoomStart - lastVblank) / interval);
		while (vt <= this.zoomEnd) {
		    var y = getY(vt);
		    context.fillRect(3 * width / 4, y, width / 4, 1);
		    vt += interval;
		}
	    }
	    context.restore();
	}

	// Now draw a time scale

	var minTick = range / 10;
	var pow10 = Math.floor(Math.log(minTick) / Math.log(10));
	var tick10 = Math.pow(10, pow10);
	var tick;

	var digits = - pow10;

	if (tick10 >= minTick)
	    tick = tick10;
	else if (2 * tick10 >= minTick)
	    tick = 2 * tick10;
	else if (5 * tick10 >= minTick)
	    tick = 5 * tick10;
	else if (10 * tick10 >= minTick) {
	    tick = 10 * tick10;
	    digits -= 1;
	}

	var start = tick * Math.floor(this.zoomStart / tick);
	var count = Math.ceil(range / tick);

	context.save();
	context.fillStyle = "#444444";
	context.textBaseline = 'middle';
	for (i = 0; i < count; i++) {
	    var t = start + i * tick;
	    var y = getY(t);

	    var text = t.toFixed(digits);
	    var textWidth = context.measureText(text).width;

	    var x0 = 7 * width / 8 - textWidth / 2;
	    var x1 = 7 * width / 8 + textWidth / 2;

	    context.fillText(text, x0, y);
	    context.fillRect(3 * width / 4, y, x0 - (3 * width / 4) - 5, 1);
	    context.fillRect(x1 + 5, y, width - x1 + 5, 1);

	}
	context.restore();
    },

    setRun: function(runIndex) {
	this.run = this.runs[runIndex];

	this.run.prepare();
	this.zoomStart = 0;
	this.zoomEnd = this.run.range;
	this.redraw();
    }
};
