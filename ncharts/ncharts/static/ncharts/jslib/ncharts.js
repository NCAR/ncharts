// See gregfranko.com/blog/jquery-best-practices
//
// IIFE: Immediately Invoked Function Expression
(function(main_iife_function) {
        main_iife_function(window.jQuery, window, document);
    }(function($,window,document) {
        
        // Put local variables and functions into this namespace
        local_ns = {}

        local_ns.debug_level = 0;

        local_ns.find_x_ge = function(arr,val) {
            var index = null;
            arr.some(function(e1,i) {
                return e1['x'] >= val ? (( index = i), true) : false;
            });
            return index;
        }

        local_ns.unique = function(arr) {
            return arr.filter(function(value, index, array) {
                return array.indexOf(value) === index;
            });
        };

        local_ns.setPlotTimezone = function(val) {
            // console.log("calling Highcharts.setOptions,val",val);
            local_ns.plotTimezone = val;
            local_ns.zone = moment.tz.zone(val);
            Highcharts.setOptions({
                global: {
                    getTimezoneOffset: function(timestamp) {
                        var timezoneOffset =
                            -moment.tz(timestamp,local_ns.plotTimezone).utcOffset();
                        // console.log("timezoneOffset=",timezoneOffset);
                        return timezoneOffset;
                    },
                    // Documentation on this seems wrong. With the current
                    // logic here, we must set this to true.
                    useUTC: true,
                }
            });
        };
        local_ns.format_time = function(val, format) {
            format = typeof format !== "undefined" ? format : 'YYYY-MM-DD HH:mm:ss ZZ';
            var mom = moment(val).tz(local_ns.pickerTimezone);
            // format it, and set it on the picker
            return mom.format(format);
        }

        local_ns.update_start_time = function(start_time) {
            var dstr = local_ns.format_time(start_time,'YYYY-MM-DD HH:mm');
            // console.log("updating start_time, dstr=",dstr);
            $("input#id_start_time").val(dstr);
	    local_ns.update_sounding_boxes(start_time);
        }

        local_ns.update_sounding_boxes = function(start_time) {

	    try {
		console.log("update_ sounding_boxes, soundings.length=",soundings.length);
		if (soundings.length > 0) {
		    $("#sounding-checkbox").empty();
		    
	    	    for (var is = 0; is < soundings.length; is++) {
			var sname = soundings[is][0];
			var stime = soundings[is][1] * 1000;	// milliseconds
			
			if (stime >= start_time && stime < start_time + local_ns.time_length) {
			    $("<input data-mini='true' name='soundings' type='checkbox' />")
				.attr("id", "id_soundings_" + is)
				.attr("value", sname)
				.appendTo("#sounding-checkbox");
			    var $label = $("<label>").text(sname).attr({for:"id_soundings_" + is});
			    $("#sounding-checkbox").append($label);
			}
		    }
		}
	    }
	    catch (err) {
		return;
	    }
	}

        local_ns.get_start_time = function() {
            var dstr = $("input#id_start_time").val();;
            return moment.tz(dstr,'YYYY-MM-DD HH:mm',local_ns.pickerTimezone);
        }

        // set the value of local_ns.time_length in units of milliseconds
        local_ns.update_time_length = function(time_length,time_length_units) {
            /*
            console.log("update_time_length, len=",time_length,", units=",
                    time_length_units);
            */
            switch(time_length_units) {
            case "day":
                time_length *= 24;
            case "hour":
                time_length *= 60;
            case "minute":
                time_length *= 60;
            case "second":
                time_length *= 1000;    // milliseconds
                break;
            }
            local_ns.time_length = time_length;

            if (local_ns.track_real_time) {
                local_ns.update_start_time(Date.now() - local_ns.time_length);
            }
	    local_ns.update_sounding_boxes(local_ns.get_start_time())
        }

        // Add support for %Z time formatter
        Highcharts.dateFormats = {
            Z: function (timestamp) {
                // console.log("zone.abbr=",local_ns.zone.abbr(timestamp));
                return local_ns.zone.abbr(timestamp);
            }
        };

        local_ns.do_ajax = function() {
            // console.log("do_ajax");
            $.ajax({
                url: ajaxurl,
                timeout: 30 * 1000,
                // No data is sent to the server. In the ajax url is a numeric id which
                // is used to map to the user's selection.
                dataType: "json",   // type of data back from server

                error: function(jqXHR, error_type, errorThrown) {
                    /*
                     * From http://api.jquery.com/jquery.ajax/:
                     * Possible values for the second argument (besides null) are
                     * "timeout", "error", "abort", and "parsererror".
                     * When an HTTP error occurs, errorThrown receives the textual
                     * portion of the HTTP status, such as "Not Found" or "Internal Server Error." 
                     */
                    console.log("ajax error_type=",error_type);
                    console.log("ajax errorThrown=",errorThrown);
                    // schedule again
                    setTimeout(local_ns.do_ajax,local_ns.ajaxTimeout);
                },
                success: function(indata) {

                    // console.log("ajax success!, now=",new Date(),",
                    // itime0=",itime0);
                    var first_time = null;  // first plotted time

                    $("div[id^='time-series']").each(function(index) {

                        // update time series plots from ajax data
                        var chart = $( this ).highcharts();

                        for (var iv = 0; iv < chart.series.length; iv++ ) {
                            var series = chart.series[iv];
                            var vname = series.name;

                            if (vname == 'Navigator') continue;

                            if (!(vname in indata)) {
                                continue;
                            }

                            if (series.data.length > 0) {
                                first_time = series.data[0]['x'];
                            }

                            var itimes = $.parseJSON(indata[vname]['time'])

                            if (itimes.length == 0) {
                                continue;
                            }

                            // shouldn't often happen in this ajax function
                            if (series.data.length == 0 && local_ns.debug_level) {
                                console.log("ajax, iv=",iv,", vname=",vname,
                                    ", series.data.length=",series.data.length);
                            }

                            // console.log("first_time=",local_ns.format_time(first_time));

                            var itime0 = indata[vname]['time0'];
                            var vdata = $.parseJSON(indata[vname]['data']);

                            var ix = 0;
                            var tx;
                            for (var idata = 0; idata < itimes.length; idata++) {
                                var redraw = (idata == itimes.length - 1 ? true : false);
                                tx = (itime0 + itimes[idata]) * 1000;
                                var dx = vdata[idata];

                                // var dl = series.data.length; 
                                for ( ; ix < series.data.length; ix++) {
                                    try {
                                        if (series.data[ix]['x'] >= tx) break;
                                    }
                                    catch(err) {
                                        console.log("error ",err," in looping over chart times, ",
                                            "var=",vname,
                                            ", data time=",
                                            local_ns.format_time(tx),
                                            ", ix=", ix, ", len=",
                                            series.data.length);
                                    }
                                }

                                // later time than all in chart, add with possible shift
                                if (ix == series.data.length) {
                                    var shift = (first_time &&
                                        (tx > first_time + local_ns.time_length)) ? true : false;

                                    // With StockChart, saw this exception frequently:
                                    // "TypeError: Cannot read property 'x' of undefined"
                                    series.addPoint([tx,dx],redraw,shift);
                                    if (shift) {
                                        try {
                                            first_time = series.data[0]['x'];
                                        }
                                        catch(err) {
                                            var first_time_str = "null";
                                            if (first_time) {
                                                first_time_str = local_ns.format_time(first_time);
                                            }
                                            console.log("error ",err," in accessing first chart time, ",
                                                "var=",vname,", iv=", iv,
                                                ", tx=",
                                                local_ns.format_time(tx),
                                                ", first_time=", first_time_str,
                                                ", idata=",idata,", ix=", ix, ", len=",
                                                series.data.length);
                                        }
                                        if (ix) ix--;
                                    }
                                }
                                else {
                                    var ctx = series.data[ix]['x'];
                                    if (ctx == tx) {    // same time, replace it
                                        series.data[ix].update(dx,redraw);
                                    }
                                    else {
                                        // shift=false, adding in middle
                                        if (local_ns.debug_level > 1) {
                                            console.log("var=",vname,
                                                " insert time, tx=",
                                                local_ns.format_time(tx),
                                                ", ctx=",
                                                local_ns.format_time(ctx),
                                                ", ix=", ix, ", len=",
                                                series.data.length); 
                                        }
                                        series.addPoint([tx,dx],redraw,false);
                                    }
                                }
                            }

                            var npts = 0
                            while ((l = series.data.length) > 1 &&
                                series.data[l-1]['x'] >
                                    series.data[0]['x'] + local_ns.time_length) {
                                series.removePoint(0,true);
                                first_time = series.data[0]['x'];
                                npts++;
                            }
                            if (npts && local_ns.debug_level) {
                                console.log("var=",vname," removed ",npts," points, time_length=",
                                        local_ns.time_length);
                            }
                            if (local_ns.debug_level) {
                                console.log("time-series ajax function done, var= ",vname,
                                    ", itimes.length=",itimes.length,
                                    ", first_time=", local_ns.format_time(first_time),
                                    ", chart.series[",iv,"].data.length=", series.data.length)
                            }
                        }
                        // charts of multiple variables sometimes take a while to redraw
                        // if (chart.series.length > 1) chart.redraw();
                    });

                    $("div[id^='heatmap']").each(function(index) {

                        // update heatmap plots from ajax data
                        var chart = $( this ).highcharts();

                        var t0 = new Date();
                        var t1;
                        for (var iv = 0; iv < chart.series.length; iv++ ) {
                            var series = chart.series[iv];
                            var vname = series.name;
                            // console.log("vname=",vname)

                            if (series.data.length > 0) {
                                first_time = series.data[0]['x'];
                            }

                            if (!(vname in indata)) {
                                continue;
                            }
                            var itimes = $.parseJSON(indata[vname]['time'])

                            if (itimes.length == 0) {
                                continue;
                            }

                            var itime0 = indata[vname]['time0']
                            var vdata = $.parseJSON(indata[vname]['data'])
                            var dim2 = $.parseJSON(indata[vname]['dim2'])

                            if (local_ns.debug_level > 1) {
                                t0 = new Date();
                                console.log("heatmap ",t0,", vname=",vname,", adding ",itimes.length,
                                        " points, dim2.length=",dim2.length)
                            }

                            var ix = 0;
                            var tx;

                            // redraw == true results in very slow performance on heatmaps.
                            // Instead we wait and do a chart.redraw() when all points have
                            // been updated.
                            var redraw = false;

                            for (var idata = 0; idata < itimes.length; idata++) {
                                // redraw = (idata == itimes.length - 1 ? true : false);

                                tx = (itime0 + itimes[idata]) * 1000;

                                for ( ; ix < series.data.length; ix++) {
                                    if (series.data[ix]['x'] >= tx) break;
                                }

                                // later time than all in chart, add with possible shift
                                if (ix == series.data.length) {
                                    // shift=true is also slow on a heatmap. Disable it.
                                    var shift = (false && first_time &&
                                        (tx > first_time + local_ns.time_length)) ? true : false;
                                    for (var j = 0; j < dim2.length; j++) {
                                        dx = vdata[idata][j];
                                        // console.log("heatmap addPoint, idata=",idata,
                                        //         ", iv=",iv,", j=",j," length=",series.data.length);
                                        series.addPoint(
                                            [tx,dim2[j],dx], redraw,shift);
                                    }
                                    if (shift || !first_time) {
                                        first_time = series.data[0]['x'];
                                        ix -= dim2.length;
                                    }
                                }
                                else {
                                    var ctx = series.data[ix]['x'];
                                    if (ctx == tx) {    // same time, replace it
                                        for (var j = 0; j < dim2.length; j++) {
                                            dx = vdata[idata][j];
                                            series.data[ix+j].update([tx,dim2[j],dx],redraw);
                                        }
                                    }
                                    else {
                                        // shift=false, adding in middle
                                        for (var j = 0; j < dim2.length; j++) {
                                            dx = vdata[idata][j];
                                            // console.log("heatmap addPoint, idata=",idata,
                                            //         ", iv=",iv,", j=",j," length=",series.data.length);
                                            series.addPoint(
                                                [tx,dim2[j],dx], redraw,false);
                                        }
                                        if (ctx > tx && ix == 0) {
                                            first_time = series.data[0]['x'];
                                        }
                                    }
                                }
                            }
                            if (local_ns.debug_level > 1) {
                                t1 = new Date();
                                console.log("added ", itimes.length, " points, elapsed time=",(t1 - t0)/1000," seconds");
                                t0 = t1;
                            }
                            // remove points
                            var npts = 0;
                            while ((l = series.data.length) > 1 &&
                                series.data[l-1]['x'] >
                                    series.data[0]['x'] + local_ns.time_length) {
                                series.removePoint(0,redraw);
                                first_time = series.data[0]['x'];
                                npts++;
                            }
                            if (local_ns.debug_level > 1) {
                                t1 = new Date();
                                console.log("removed ", npts, " points, elapsed time=",(t1 - t0)/1000," seconds");
                                t0 = t1;
                            }
                            if (local_ns.debug_level) {
                                console.log("heatmap ajax function done, var= ",vname,
                                    ", itimes.length=",itimes.length,
                                    ", first_time=", local_ns.format_time(first_time),
                                    ", chart.series[",iv,"].data.length=", series.data.length)
                            }
                        }
                        chart.redraw();
                        if (local_ns.debug_level > 1) {
                            t1 = new Date();
                            console.log("chart redraw, elapsed time=",(t1 - t0)/1000," seconds");
                            t0 = t1;
                        }
                    });

                    // update the start time on the datetimepicker from
                    // first time in chart (milliseconds)
                    if (first_time) {
                        local_ns.update_start_time(first_time);
                    }

                    // schedule again
                    setTimeout(local_ns.do_ajax,local_ns.ajaxTimeout);
                }
            });
        }

        $(function() {
            console.log("DOM is ready!");

            // When doc is ready, grab the selected time zone
            var tzelem = $("select#id_timezone");
            var tz = tzelem.val();
            local_ns.pickerTimezone = tz;
            local_ns.setPlotTimezone(tz);

            local_ns.long_name_dict = {};

            // console.log("select#id_timezone tz=",tz)

            $("select#id_timezone").change(function() {
                // When user changes the timezone, adjust the time
                // in the datetimepicker so that it is the
                // same moment in time as with the previous timezone.
                //
                // Unfortunately datetimepicker time formats
                // are different than moment time formats:
                // datetimepicker:  "yyyy-mm-dd hh:ii"
                // moment:          "YYYY-MM-DD HH:mm"
                // The moment format is hard-coded here, and so
                // if the datetimepicker format is changed in
                // django/python, it must be changed here.
                //
                // Also couldn't find out how to get the current
                // datetimepicker format.
                //
                // To avoid formatting times one would get/set
                // from datetimepicker using javascript Date objects.
                // However, a javascript Date is either in the
                // browser's time zone or UTC. I believe there would
                // always be a problem right around the time of
                // daylight savings switches, if Date is used.

                // Note that we don't change the value of
                // the timezone in local_ns, since that must match
                // what is plotted.

                var picker = $("input#id_start_time");
                var dstr = picker.val();

                // console.log("picker.val()=",dstr);

                // parse time using current timezone
                var mom = moment.tz(dstr,'YYYY-MM-DD HH:mm',local_ns.pickerTimezone);

                // get the new timezone
                var new_tz = $(this).val();

                // save previous value, but don't
                local_ns.pickerTimezone = new_tz;

                // adjust time for new timezone
                mom = mom.tz(new_tz);

                // format it, and set it on the picker
                dstr = mom.format('YYYY-MM-DD HH:mm');
                picker.val(dstr);
            });

            $("#id_variables_clear").change(function() {
                // console.log("id_variables_clear change, val=",$(this).prop("checked"));
                if ($(this).prop("checked")) {
                    $('#variable-checkbox :checked').prop('checked',false);
                    $(this).prop('checked',false);
                }
            });

            $("#id_variables_all").change(function() {
                // console.log("id_variables_all change, val=",$(this).prop("checked"));
                if ($(this).prop("checked")) {
                    $('#variable-checkbox :not(:checked)').prop('checked',true);
                    $(this).prop('checked',false);
                }
            });

	    $("#id_soundings_clear").change(function() {
                if ($(this).prop("checked")) {
                    $('#sounding-checkbox :checked').prop('checked',false);
                    $(this).prop('checked',false);
                }
            });

            $("#id_soundings_all").change(function() {
                if ($(this).prop("checked")) {
                    $('#sounding-checkbox :not(:checked)').prop('checked',true);
                    $(this).prop('checked',false);
                }
            });

            // set the time_length
            local_ns.update_time_length(
                $("input#id_time_length_0").val(),
                 $("select#id_time_length_units").val());

            /* If the user wants to track real time with ajax. */
            local_ns.track_real_time = $("input#id_track_real_time").prop("checked");

            $("input#id_start_time").change(function() {
	    	var start_time = local_ns.get_start_time();
		local_ns.update_sounding_boxes(start_time);
            });

            $("input#id_track_real_time").change(function() {
                local_ns.track_real_time = $(this).prop("checked");
                if (local_ns.track_real_time) {
                    local_ns.update_start_time(Date.now() - local_ns.time_length);
                }
            });

            // time_length text widget
            $("input#id_time_length_0").change(function() {
                var time_length = $(this).val();
                var time_length_units = $("select#id_time_length_units").val();
                local_ns.update_time_length(time_length,time_length_units);
            });

            // time_length select widget
            $("select#id_time_length_1").change(function() {
                var time_length = $(this).val();
                var time_length_units = $("select#id_time_length_units").val();
                $("input#id_time_length_0").val(time_length);
                local_ns.update_time_length(time_length,time_length_units);
            });

            // time_length units select widget
            $("select#id_time_length_units").change(function() {
                var time_length_units = $(this).val();
                var time_length = $("input#id_time_length_0").val();
                local_ns.update_time_length(time_length,time_length_units);
            });

            // console.log("track_real_time=",local_ns.track_real_time);
            // Everything below here depends on plot_times and plot_data
            // being passed.
            if (window.plot_times === undefined) return

            if (local_ns.track_real_time) {
                // mean delta-t of data
                local_ns.ajaxTimeout = 10 * 1000;   // 10 seconds
                if ('' in plot_times && plot_times[''].length > 1) {
                    // set ajax update period to 1/2 the data deltat
                    local_ns.ajaxTimeout =
                        Math.max(
                            local_ns.ajaxTimeout,
                            Math.ceil((plot_times[''][plot_times[''].length-1] - plot_times[''][0]) /
                                (plot_times[''].length - 1) * 1000 / 2)
                        );
                }
                if (local_ns.debug_level > 2) {
                    // update more frequently for debugging
                    local_ns.ajaxTimeout = 10 * 1000;
                }

                // start AJAX
                setTimeout(local_ns.do_ajax,local_ns.ajaxTimeout);

                if (local_ns.debug_level) {
                    console.log("ajaxTimeout=",local_ns.ajaxTimeout);
                }
            }

            var first_time = null;

            $("div[id^='time-series']").each(function(index) {

                // console.log("time-series");

                // series name
                var sname =  $( this ).data("series");
                var vnames =  $( this ).data("variables");
                var vunits =  $( this ).data("units");
                var long_names =  $( this ).data("long_names");

                // console.log("time-series, plot_times[''].length=",plot_times[''].length);
                // console.log("vnames=",vnames,", vunits=",vunits);

                // A yAxis for each unique unit
                var yAxis = [];
                
                // One plot for all variable with the same units.
                // This has already been organized by python, so
                // unique_units will have length 1 here.
                var unique_units = local_ns.unique(vunits);

                // create a yAxis
                for (var unit of unique_units) {
                    ya = {
                        title: {
                            text: unit,
                        },
                        opposite: false,
                        // docs seem to indicate that the default for
                        // ordinal is true, but the default seems to be
                        // false. We'll set it to false to make sure
                        ordinal: false,
                    };
                    yAxis.push(ya);
                }

                /*
                 * array of objects, one for each input variable,
                 * with these keys:
                 *  name: variable name and units
                 *  data: 2 column array, containing time, data values
                 *  yAxis: index of the yaxis to use
                 *  tooltip: how to display points.
                 */
                var series = [];

                var ptitle;
                if (vnames.length > 1) {
                    ptitle = vnames[0] + ", " + vnames[1] + "...";
                }
                else {
                    ptitle = vnames[0];
                }
                for (var iv = 0; iv < vnames.length; iv++ ) {
                    var vname = vnames[iv];
                    var vunit = vunits[iv];
                    if (long_names.length > iv) {
                        local_ns.long_name_dict[vname] = long_names[iv];
                    }
                    else {
                        local_ns.long_name_dict[vname] = '';
                    }
                    var vseries = {};
                    var vdata = [];
                    for (var idata = 0; idata < plot_times[sname].length; idata++) {
                        vdata.push([(plot_time0[sname] + plot_times[sname][idata])*1000,
                                plot_data[sname][vname][idata]]);
                    }
                    if (plot_times[sname].length) {
                        first_time = (plot_time0[sname] + plot_times[sname][0]) * 1000;
                    }

                    vseries['data'] = vdata;
                    vseries['name'] = vname;
                    /*
                    vseries['tooltip'] = {
                        valuePrefix: long_names[iv] + ':',
                    },
                    */

                    // which axis does this one belong to? Will always be 0
                    vseries['yAxis'] = unique_units.indexOf(vunit);
                    series.push(vseries);
                    if (local_ns.debug_level > 1) {
                        console.log("initial, vname=",vname,", series[",iv,"].length=",
                                series[iv].data.length);
                    }
                } 

                /*
                 * A StockChart seems to have bugs. The data array chart.series[i].data
                 * does not seem to be dependably accessible from ajax code.
                 * chart.series[i].data.length was often 0. 
                 * So instead of highcharts('StockChart',{}) just do highcharts({}).
                 * All the same functionality seems to be there
                 */
                $( this ).highcharts({
                    chart: {
                        type: 'line',
                        // zoomType: 'x',
                        // panning: true,
                        // panKey: 'shift',
                        spacingLeft: 20,
                        spacingRight: 20,
                        // marginLeft: 20,
                        // marginRight: 20,
                        // marginTop: 40,
                        // marginBottom: 80,
                    },
                    plotOptions: {
                        series: {
                            dataGrouping: {
                                dateTimeLabelFormats: {
                                   millisecond:
                ['%Y-%m-%d %H:%M:%S.%L %Z', '%Y-%m-%d %H:%M:%S.%L', '-%H:%M:%S.%L %Z'],
                                   second:
                ['%Y-%m-%d %H:%M:%S %Z', '%Y-%m-%d %H:%M:%S', '-%H:%M:%S %Z'],
                                   minute:
                ['%Y-%m-%d %H:%M %Z', '%Y-%m-%d %H:%M', '-%H:%M %Z'],
                                   hour:
                ['%Y-%m-%d %H:%M %Z', '%Y-%m-%d %H:%M', '-%H:%M %Z'],
                                   day:
                ['%Y-%m-%d %Z', '%Y-%m-%d', '-%m-%d %Z'],
                                   week:
                ['Week from %Y-%m-%d', '%Y-%m-%d', '-%Y-%m-%d'],
                                   month:
                ['%Y-%m', '%Y-%m', '-%Y-%m'],
                                   year: ['%Y', '%Y', '-%Y']
                ['%Y', '%Y', '-%Y'],
                                }
                            },
                            gapSize: 2,
                        },
                    },
                    xAxis: {
                        type: 'datetime',
                        // opted not to add %Z to these formats.
                        // The timezone is in the xAxis label, and in
                        // the tooltip popups.
                        dateTimeLabelFormats: {
                            millisecond: '%H:%M:%S.%L',
                            second: '%H:%M:%S',
                            minute: '%H:%M',
                            hour: '%H:%M',
                            day: '%Y<br/>%m-%d',
                            month: '%Y<br/>%m',
                            year: '%Y'
                        },
                        startOnTick: false,
                        endOnTick: false,
                        title: {
                            text: "time (" + local_ns.plotTimezone + ")"
                        },
                        ordinal: false,
                    },
                    yAxis: yAxis,
                    series: series,
                    legend: {
                        enabled: true,
                        margin: 0,
                    },
                    rangeSelector: {
                        enabled: false,
                    },
                    scrollbar: {
                        enabled: false,
                    },
                    tooltip: {
                        shared: true,       // show all points in the tooltip
                        /* define a formatter function to prefix the long_name
                         * to the variable name in the tooltip. Adding a
                         * tooltip.valuePrefix to the series almost works,
                         * but it is placed before the value, in bold.
                         * Tried using point.series.symbol, but it is a string,
                         * such as "circle"
                         */
                        formatter: function() {
                            s = '<span style="font-size: 10px"><b>' + Highcharts.dateFormat('%Y-%m-%d %H:%M:%S.%L %Z',this.x) + '</b></span><br/>';
                            $.each(this.points, function(i, point) {
                                s += '<span style="color:' + point.series.color + '">\u25CF</span>' + local_ns.long_name_dict[point.series.name] + ',' + point.series.name + ': <b>' + point.y + '</b><br/>';
                            });
                            return s;
                        },
                        // If no formatter, use these settings.
                        /*
                        headerFormat: '<span style="font-size: 10px"><b>{point.key}</b></span><br/>',
                        pointFormat: '<span style="color:{series.color}">\u25CF</span> ' + ',{series.name}: <b>{point.y}</b><br/>',
                        xDateFormat: '%Y-%m-%d %H:%M:%S.%L %Z',
                        valueDecimals: 6,
                        */
                    },
                    navigator: {
                        height: 25,
                        margin: 5,
                        enabled: true,
                        // adaptToUpdatedData: true,

                    },
                    title: {
                        text: ptitle,
                    }
                });
            });

            $("div[id^='heatmap']").each(function(index) {

                // one plot per variable, vnames will have length of 1

                var sname =  $( this ).data("series");
                var vnames =  $( this ).data("variables");
                var vunits =  $( this ).data("units");
                var long_names = $( this ).data("long_names");

                // console.log("vnames=",vnames);
                for (var iv = 0; iv < vnames.length; iv++) {
                    var vname = vnames[iv];
                    // console.log("vname=", vname);
                    if (long_names.length > iv) {
                        long_name = long_names[iv];
                    } else {
                        long_name = vname;
                    }
                    var units = vunits[iv];

                    var minval = Number.POSITIVE_INFINITY;
                    var maxval = Number.NEGATIVE_INFINITY;

                    var mintime = (plot_time0[sname] + plot_times[sname][0]) * 1000;
                    var maxtime = (plot_time0[sname] + plot_times[sname][plot_times[sname].length-1]) * 1000;
                    var dim2_name = plot_dim2[sname][vname]['name'];
                    var dim2_units = plot_dim2[sname][vname]['units'];

                    var mindim2 = plot_dim2[sname][vname]['data'][0];
                    var maxdim2 = plot_dim2[sname][vname]['data'][plot_dim2[sname][vname]['data'].length-1];

                    var chart_data = [];
                    for (var i = 0; i < plot_times[sname].length; i++) {
                        var tx = (plot_time0[sname] + plot_times[sname][i]) * 1000;
                        for (var j = 0; j < plot_dim2[sname][vname]['data'].length; j++) {
                            dx = plot_data[sname][vname][i][j];
                            if (dx !== null) {
                                minval = Math.min(minval,dx);
                                maxval = Math.max(maxval,dx);
                            }
                            chart_data.push([tx, plot_dim2[sname][vname]['data'][j],dx]);
                        }
                    } 
                    if (plot_times[sname].length) {
                        first_time = (plot_time0[sname] + plot_times[sname][0]) * 1000;
                    }

                    // var colsize = 3600 * 1000;
                    var colsize = (maxtime - mintime) / (plot_times[sname].length - 1);
                    var rowsize = (maxdim2 - mindim2) / (plot_dim2[sname].length - 1);

                    $( this ).highcharts({
                        chart: {
                            type: 'heatmap',
                            marginTop: 40,
                            marginBottom: 60,
                            zoomType: 'x',
                            panning: true,
                            panKey: 'shift',
                            plotOptions: {
                                series: {
                                    dataGrouping: {
                                        dateTimeLabelFormats: {
                                           millisecond:
                        ['%Y-%m-%d %H:%M:%S.%L %Z', '%Y-%m-%d %H:%M:%S.%L', '-%H:%M:%S.%L %Z'],
                                           second:
                        ['%Y-%m-%d %H:%M:%S %Z', '%Y-%m-%d %H:%M:%S', '-%H:%M:%S %Z'],
                                           minute:
                        ['%Y-%m-%d %H:%M %Z', '%Y-%m-%d %H:%M', '-%H:%M %Z'],
                                           hour:
                        ['%Y-%m-%d %H:%M %Z', '%Y-%m-%d %H:%M', '-%H:%M %Z'],
                                           day:
                        ['%Y-%m-%d %Z', '%Y-%m-%d', '-%m-%d %Z'],
                                           week:
                        ['Week from %Y-%m-%d', '%Y-%m-%d', '-%Y-%m-%d'],
                                           month:
                        ['%Y-%m', '%Y-%m', '-%Y-%m'],
                                           year: ['%Y', '%Y', '-%Y']
                        ['%Y', '%Y', '-%Y'],
                                        }
                                    }
                                }
                            },
                        },
                        title: {
                            text: long_name + '(' + units + ')'
                        },
                        xAxis: {
                            type: 'datetime',
                            dateTimeLabelFormats: {
                                millisecond: '%H:%M:%S.%L',
                                second: '%H:%M:%S',
                                minute: '%H:%M',
                                hour: '%H:%M',
                                day: '%Y<br/>%m-%d',
                                month: '%Y<br/>%m',
                                year: '%Y'
                            },
                            /*
                            min: mintime,
                            max: maxtime,
                            */
                            title: {
                                margin: 0,
                                text: "time (" + local_ns.plotTimezone + ")",
                            },
                            ordinal: false,
                        },
                        yAxis: {
                            title: {
                                text: dim2_name + '(' + dim2_units + ')'
                            },
                            min: mindim2,
                            max: maxdim2,
                            tickWidth: 2,
                        },
                        colorAxis: {
                            stops: [
                                [0, '#3060cf'],
                                [0.5, '#fffbbc'],
                                [0.9, '#c4463a']
                            ],
                            min: minval,
                            max: maxval,
                            reversed: false,
                            // minColor: '#FFFFFF',
                            // maxColor: Highcharts.getOptions().colors[0]
                        },
                        legend: {
                            title: vname,
                            align: 'right',
                            layout: 'vertical',
                            margin: 15,
                            verticalAlign: 'bottom'
                        },
                        tooltip: {
                            enabled: true,
                            /*
                            headerFormat: vname + "<br/>",
                            */
                            headerFormat: '',
                            pointFormat:
                                vname + '={point.value}, ' + dim2_name +
                                '={point.y}, {point.x:%Y-%m-%d %H:%M:%S.%L %Z}',
                            // xDateFormat: '%Y-%m-%d %H:%M:%S.%L %Z',
                        },
                        series:[{
                            name: vname,
                            data: chart_data,
                            colsize: colsize,
                            rowsize: rowsize,
                        }],
                    });
                }
            });

            $("div[id^='sounding-profile']").each(function(index) {
                var sname =  $( this ).data("series");
		var vnames =  $( this ).data("variables");
		var vunits =  $( this ).data("units");
                var long_names =  $( this ).data("long_names");
                if (long_names.length == 0) {
                    long_names = vnames;
                }

		var series = [];
		var axis = [];
		var ptitle = "";

                if (vnames.length > 1) {
		    for (var i = 0; i < vnames.length; i++) {
			if (i == vnames.length - 1) {
			    ptitle += vnames[i];
			} 
			else {
			    ptitle += (vnames[i] + ", "); 
			}
		    }
                }
                else {
                    ptitle = vnames[0];
                }

		ptitle = sname + ": "  + ptitle;

                var altname = 'alt';
                // the altitude array
                var altitudes = plot_data[sname][altname];

		var data_length = altitudes.length;
		var skip;
		if (data_length < 100) {
		    skip = 1;
		}
		else {
		    skip = Math.round(data_length/100);
		}


                var alt_increasing = true;  // are altitudes increasing?
                if (data_length > 1) {
                    // check first and last
                    alt_increasing = altitudes[data_length-1] > altitudes[0];
                }

                var alt_check_func;
                var last_val_init;
                if (alt_increasing) {
                    last_val_init = -Number.MAX_VALUE;
                    alt_ok = function(x,xlast) {
                        return x > xlast;
                    }
                } else {
                    last_val_init = Number.MAX_VALUE;
                    alt_ok = function(x,xlast) {
                        return x < xlast;
                    }
                }

		for (var iv = 0; iv < vnames.length; iv++) {
		    var vname = vnames[iv];
                    if (vname == altname) continue;
		    var vunit = vunits[iv];
                    var vseries = {};
		    var vaxis = {};
                    var vdata = [];
                    var last_val = last_val_init;
		    for (var idata = 0; idata < data_length; idata+=skip) {
                        var x = altitudes[idata];
                        if (alt_ok(x,last_val) {
                            var y = plot_data[sname][vname][idata];
			    vdata.push(x,y)
			}
                        last_val = x;
		    }

		    vaxis['title'] = {text: vname + " (" + vunit + ")",
				    style: {"color": "black", "fontSize": "20px"}}; 
		    vaxis['lineWidth'] = 1;
		    vaxis['minorGridLineDashStyle'] = 'longdash';
		    vaxis['minorTickInterval'] = 'auto';
		    vaxis['minorTickWidth'] = 0;

		    if (iv % 2 == 0) {
			vaxis['opposite'] = false;
		    }
		    else {
			vaxis['opposite'] = true;
		    }
		    vseries['data'] = vdata;
                    vseries['name'] = vname;
		    vseries['yAxis'] = iv;

                    series.push(vseries);
		    axis.push(vaxis);
		    if (local_ns.debug_level > 0) {
                        console.log("initial, vname=",vname,", series[",iv,"].length=",
                                series[iv].data.length);
                    }
		}

		$(this).highcharts({
		    chart: {
			showAxes: true,
		//	height: 1000,
			inverted: true,
			type: 'line',
		    },
		    xAxis: {
			reversed: false,
			endOnTick: true,
                        title: {
                            text: "Altitude (m)",
			    style: {"color": "black", "fontSize": "20px"},
                        },
                    },
		    yAxis: axis,
		    legend: {
                        enabled: true,
                        margin: 0,
                    },
                    rangeSelector: {
                        enabled: false,
                    },
                    scrollbar: {
                        enabled: false,
                    },
                    series: series,
                    title: {
			margin: 10,
                        text: ptitle,
			style: {"color": "black", "fontSize": "25px", "fontWeight": "bold", "text-decoration": "underline"},
                    },
		});
            });
            if (first_time) {
                local_ns.update_start_time(first_time);
            } 
        });     // end of DOM-is-ready function
    })
);

