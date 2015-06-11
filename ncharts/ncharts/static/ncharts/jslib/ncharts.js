// See gregfranko.com/blog/jquery-best-practices
//
// IIFE: Immediately Invoked Function Expression
(function(main_iife_function) {
        main_iife_function(window.jQuery, window, document);
    }(function($,window,document) {
        
        // Put local variables and functions into this namespace
        local_ns = {}

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
        local_ns.update_start_time = function(val) {
            console.log("updating start_time, val=",val);
            var mom = moment(val).tz(local_ns.pickerTimezone);
            // format it, and set it on the picker
            var dstr = mom.format('YYYY-MM-DD HH:mm');
            console.log("updating start_time, dstr=",dstr);
            $("input#id_start_time").val(dstr);
        }

        // set the value of local_ns.time_length in units of milliseconds
        local_ns.update_time_length = function(time_length,time_length_units) {
            console.log("update_time_length, len=",time_length,", units=",
                    time_length_units);
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
                timeout: 10 * 1000,
                data: {
                    // send the last time of the current plot to server
                    last_time: local_ns.last_time,
                },
                dataType: "json",
                success: function(indata) {

                    var time0 = indata['time0']
                    var time = $.parseJSON(indata['time'])
                    var data = $.parseJSON(indata['data'])

                    // console.log("ajax success!, now=",new Date(),",time0=",time0);

                    if (time.length == 0) {
                        return;
                    }

                    $("div[id^='time-series']").each(function(index) {
                        var chart = $( this ).highcharts();
                        var vnames = $( this ).data("variables").sort();
                        if (vnames.length == 0) {
                            return
                        }
                        var idata;
                        // loop up to last point
                        for (idata = 0; idata < time.length - 1; idata++) {
                            var tx = (time0 + time[idata]) * 1000;
                            var start_time = tx;
                            if (chart.series[0].data.length) {
                                start_time = chart.series[0].data[0]['x'];
                            }
                            for (var iv = 0; iv < vnames.length; iv++ ) {
                                var vname = vnames[iv];
                                // console.log("first time=",chart.series[iv].data[0]);
                                var shift = false;
                                if (tx > start_time + local_ns.time_length) {
                                    shift = true;
                                }
                                // console.log("start_time=",new Date(start_time),",shift=",shift);
                                chart.series[iv].addPoint(
                                    [tx,data[vname][idata]], false, shift);
                            }
                        }
                        // for last point, update chart
                        var tx = (time0 + time[idata]) * 1000;
                        var start_time = tx;
                        if (chart.series[0].data.length) {
                            start_time = chart.series[0].data[0]['x'];
                        }
                        for (var iv = 0; iv < vnames.length; iv++ ) {
                            var vname = vnames[iv];
                            var shift = false;
                            if (tx > start_time + local_ns.time_length) {
                                shift = true;
                            }
                            // console.log("start_time=",new Date(start_time),",shift=",shift);
                            // for last point set redraw=true
                            chart.series[iv].addPoint(
                                [tx,data[vname][idata]], true, shift);
                        }

                        for (var iv = 0; iv < vnames.length; iv++ ) {
                            while (chart.series[iv].data.length &&
                                tx > chart.series[iv].data[0]['x'] + local_ns.time_length) {
                                chart.series[iv].removePoint(0,true);
                                // chart.series[iv].data[0].remove();
                            }
                        }
                        if (index == 0 && chart.series[0].data.length) {
                            local_ns.start_time = chart.series[0].data[0]['x'];
                        }
                    });

                    $("div[id^='heatmap']").each(function(index) {
                        var chart = $( this ).highcharts();
                        var vnames =  $( this ).data("variables");
                        if (vnames.length == 0) {
                            return
                        }
                        var idata;

                        var t0 =  new Date();
                        console.log("heatmap ",t0,", adding ",time.length,
                                " points, dim2['data'].length=",dim2['data'].length)

                        // loop up to last point
                        for (idata = 0; idata < time.length - 1; idata++) {
                            var tx = (time0 + time[idata]) * 1000;
                            var start_time = tx;
                            if (chart.series[0].data.length) {
                                start_time = chart.series[0].data[0]['x'];
                            }
                            for (var iv = 0; iv < vnames.length; iv++) {
                                var vname = vnames[iv];
                                var shift = false;
                                /*
                                if (tx > start_time + local_ns.time_length) {
                                    shift = true;
                                }
                                */
                                // console.log("start_time=",new Date(start_time),",shift=",shift);
                                for (var j = 0; j < dim2['data'].length; j++) {
                                    dx = data[vname][idata][j];
                                    // console.log("heatmap addPoint, idata=",idata,
                                    //         ", iv=",iv,", j=",j," length=",chart.series[iv].data.length);
                                    chart.series[iv].addPoint(
                                        [tx,dim2['data'][j],dx], false,shift);
                                }
                            }
                        }
                        var tx = (time0 + time[idata]) * 1000;
                        var start_time = tx;
                        if (chart.series[0].data.length) {
                            start_time = chart.series[0].data[0]['x'];
                        }
                        for (var iv = 0; iv < vnames.length; iv++ ) {
                            var vname = vnames[iv];
                            var shift = false;
                            /*
                            if (tx > start_time + local_ns.time_length) {
                                shift = true;
                            }
                            */
                            // console.log("start_time=",new Date(start_time),",shift=",shift);
                            // for last point set redraw=true
                            for (var j = 0; j < dim2['data'].length; j++) {
                                dx = data[vname][idata][j];
                                // console.log("heatmap last addPoint, idata=",idata,
                                //         ", iv=",iv,", j=",j," length=",chart.series[iv].data.length);
                                chart.series[iv].addPoint(
                                    [tx,dim2['data'][j],dx], false, shift);
                            }
                        }
                        var t1 =  new Date();
                        console.log("added ", idata+1, " points, elapsed time=",(t1 - t0)/1000," seconds");
                        t0 = t1;
                        var npts = 0;
                        for (var iv = 0; iv < vnames.length; iv++ ) {
                            while (chart.series[iv].data.length &&
                                tx > chart.series[iv].data[0]['x'] + local_ns.time_length) {
                                // console.log("series, remove Point, iv=",iv," length=",
                                //         chart.series[iv].data.length);
                                chart.series[iv].removePoint(0,false);
                                npts++;
                                // chart.series[iv].data[0].remove();
                            }
                        }
                        t1 =  new Date();
                        console.log("removed ", npts, " points, elapsed time=",(t1 - t0)/1000," seconds");
                        t0 = t1;
                        chart.redraw();
                        t1 =  new Date();
                        console.log("chart redraw, elapsed time=",(t1 - t0)/1000," seconds");
                        t0 = t1;

                        if (index == 0 && chart.series[0].data.length) {
                            local_ns.start_time = chart.series[0].data[0]['x'];
                        }
                    });

                    // update the start time on the datetimepicker from
                    // first time in chart (milliseconds)
                    local_ns.update_start_time(local_ns.start_time);

                    // last time, will be passed to servers in next ajax GET.
                    // Check for time.length>0 has been done above
                    local_ns.last_time = time0 + time[time.length-1];   // seconds
                    setTimeout(local_ns.do_ajax,local_ns.ajaxTimeout);
                }
            });
        }

        $(function() {
            // console.log("DOM is ready!");

            // When doc is ready, grab the selected time zone
            var tzelem = $("select#id_timezone");
            var tz = tzelem.val();
            local_ns.pickerTimezone = tz;
            local_ns.setPlotTimezone(tz);
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

            // set the time_length
            local_ns.update_time_length(
                $("input#id_time_length_0").val(),
                 $("select#id_time_length_units").val());

            /* If the user wants to track real time with ajax. */
            local_ns.track_real_time = $("input#id_track_real_time").prop("checked");
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
            // Everything below here depends on time and data
            // being passed.
            if (window.time === undefined) return


            // local_ns.last_time is passed to the server
            // by ajax 
            if (time.length > 0) {
                local_ns.last_time = time0 + time[time.length - 1];
            }
            else {
                local_ns.last_time = time0;
            }

            if (local_ns.track_real_time) {
                // mean delta-t of data
                local_ns.ajaxTimeout = 1000;
                if (time.length > 1) {
                    // set ajax update period to 1/2 the data deltat
                    local_ns.ajaxTimeout = Math.max(
                        local_ns.ajaxTimeout,
                        (time[time.length-1] - time[0]) / (time.length - 1) * 1000 / 2
                        );
                }
                setTimeout(local_ns.do_ajax,local_ns.ajaxTimeout);
            }

            $("div[id^='time-series']").each(function(index) {

                // console.log("time-series");

                var vnames =  $( this ).data("variables");
                var vunits =  $( this ).data("units");
                var long_names =  $( this ).data("long_names");
                if (long_names.length == 0) {
                    long_names = vnames;
                }

                var vmeta = {}
                for (var iv = 0; iv < vnames.length; iv++) {
                    // console.log("vnames[iv]=", vnames[iv])
                    vmeta[vnames[iv]] =
                        {long_name: long_names[iv], units: vunits[iv]};
                }
                delete vunits;
                delete long_name;

                vnames = vnames.sort()
                // console.log("time-series, time.length=",time.length);
                // console.log("vnames=",vnames,", vunits=",vunits);

                // A yAxis for each unique unit
                var yAxis = [];
                
                // One plot for all variable with the same units.
                // This has already been organized by python.
                // unique_units will have length 1 here.
                var unique_units = local_ns.unique(vunits).sort();

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
                 * array of objects, one for each input variable, with these keys:
                 *  name: variable name and units
                 *  data: 2 column array, containing time, data values
                 *  yAxis: index of the yaxis to use
                 *  tooltip: how to display points.
                 */
                var series = [];

                var ptitle;
                if (vnames.length > 1) {
                    ptitle = vnames[0] + "...";
                }
                else {
                    ptitle = vnames[0];
                }
                for (var iv = 0; iv < vnames.length; iv++ ) {
                    var vname = vnames[iv];
                    var vunit = vmeta[vname]['units']
                    var long_name = vmeta[vname]['long_name']
                    var vseries = {};
                    var vdata = [];
                    for (var idata = 0; idata < time.length; idata++) {
                        vdata.push([(time0 + time[idata])*1000, data[vname][idata]]);
                    }

                    vseries['data'] = vdata;
                    vseries['name'] = vname;

                    // which axis does this one belong to? Will always be 0
                    vseries['yAxis'] = unique_units.indexOf(vunit);
                    vseries['tooltip'] = {
                        // valueSuffix: long_name,
                        headerFormat: '<span style="font-size: 10px">{point.key}</span><br/>',
                        pointFormat: '<span style="color:{series.color}">\u25CF</span> ' + long_name + ',{series.name}: <b>{point.y}</b><br/>',
                        valueDecimals: 6,
                        xDateFormat: '%Y-%m-%d %H:%M:%S.%L %Z',
                    };
                    /* a checkbox allows one to "select" the series, but
                     * I'm not sure what that does. Clicking it doesn't
                     * make the series disappear. That is done by clicking
                     * on the name in the legend, which by default goes below
                     * the xaxis.
                     * Supposidly if you return anything other than false,
                     * the default action is to toggle the selected state
                     * of the series.
                        events: {
                            checkboxClick: function (event) {
                                alert('The checkbox is now ' + event.checked);
                                return false;
                            }
                        },
                     */
                    series.push(vseries);
                } 

                $( this ).highcharts('StockChart',{
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
                    navigator: {
                        height: 25,
                        margin: 5,
                    },
                    title: {
                        text: ptitle,
                    }
                });
            });

            $("div[id^='heatmap']").each(function(index) {

                // one plot per variable, vnames will have length of 1

                var vnames =  $( this ).data("variables");
                var vunits =  $( this ).data("units");
                var long_names = $( this ).data("long_names");

                /*
                console.log("heatmap, vnames.length=",vnames.length,
                        ",time.length=",time.length,
                        ",dim2.length=",dim2['data'].length);
                */

                if (long_names.length == 0) {
                    long_names = vnames;
                }

                // var vname =  $( this ).data("variable");
                // var units =  $( this ).data("units");
                // var long_name =  $( this ).data("long_name");
                // var dim2_name =  $( this ).data("dim2_name");
                var dim2_name = dim2['name'];
                var dim2_units = dim2['units'];

                // This is mostly unnecessary.
                // organize meta data by variable name,
                // then plot variables, sorted by name
                var vmeta = {}
                for (var iv = 0; iv < vnames.length; iv++) {
                    // console.log("vnames[iv]=", vnames[iv])
                    vmeta[vnames[iv]] =
                        {long_name: long_names[iv], units: vunits[iv]};
                }
                vnames = vnames.sort()
                // for (var iv = 0; iv < vnames.length; iv++) {
                    // console.log("vnames[iv]=", vnames[iv])
                // }

                // console.log("vnames=",vnames);
                for (var iv = 0; iv < vnames.length; iv++) {
                    var vname = vnames[iv];
                    // console.log("vname=", vname);
                    long_name = vmeta[vname]['long_name'];
                    units = vmeta[vname]['units'];

                    minval = Number.POSITIVE_INFINITY;
                    maxval = Number.NEGATIVE_INFINITY;


                    mintime = (time0 + time[0]) * 1000;
                    maxtime = (time0 + time[time.length-1]) * 1000;

                    mindim2 = dim2['data'][0];
                    maxdim2 = dim2['data'][dim2['data'].length-1];

                    var chart_data = [];
                    for (var i = 0; i < time.length; i++) {
                        var tx = (time0 + time[i]) * 1000;
                        for (var j = 0; j < dim2['data'].length; j++) {
                            dx = data[vname][i][j];
                            if (dx !== null) {
                                minval = Math.min(minval,dx);
                                maxval = Math.max(maxval,dx);
                            }
                            chart_data.push([tx, dim2['data'][j],dx]);
                        }
                    } 

                    // var colsize = 3600 * 1000;
                    var colsize = (maxtime - mintime) / (time.length - 1);
                    var rowsize = (maxdim2 - mindim2) / (dim2.length - 1);

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
                            // minColor: '#FFFFFF',
                            // maxColor: Highcharts.getOptions().colors[0]
                        },
                        legend: {
                            title: vname,
                            reversed: true,
                            align: 'right',
                            layout: 'vertical',
                            margin: 15,
                            verticalAlign: 'bottom'
                        },
                        series:[{
                            data: chart_data,
                            colsize: colsize,
                            rowsize: rowsize,
                            tooltip: {
                                enabled: true,
                                /*
                                headerFormat: vname + "<br/>",
                                */
                                headerFormat: '',
                                pointFormat: vname + '={point.value}, ' + dim2_name + '={point.y}, {point.x:%H:%M:%S %Z}',
                            }
                        }],
                    });
                }
            });
        });
    })
);

