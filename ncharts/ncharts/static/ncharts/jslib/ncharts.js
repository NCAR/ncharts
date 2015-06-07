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

        // Add support for %Z time formatter
        Highcharts.dateFormats = {
            Z: function (timestamp) {
                // console.log("zone.abbr=",local_ns.zone.abbr(timestamp));
                return local_ns.zone.abbr(timestamp);
            }
        };

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
                    for (var i = 0; i < time.length; i++) {
                        vdata.push([(time0 + time[i])*1000, data[vname][i]]);
                    }
                    vseries['data'] = vdata;
                    vseries['name'] = vname;

                    // which axis does this one belong to? Will always be 1
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
                for (var iv = 0; iv < vnames.length; iv++) {
                    // console.log("vnames[iv]=", vnames[iv])
                }

                // console.log("vnames=",vnames);
                for (var iv = 0; iv < vnames.length; iv++) {
                    var vname = vnames[iv];
                    // console.log("vname=", vname);
                    long_name = vmeta[vname]['long_name'];
                    units = vmeta[vname]['units'];

                    minval = Number.POSITIVE_INFINITY;
                    maxval = Number.NEGATIVE_INFINITY;

                    var datetime = true;

                    if (datetime) {
                        mintime = (time0 + time[0]) * 1000;
                        maxtime = (time0 + time[time.length-1]) * 1000;
                    }
                    else {
                        // mintime = time[0] * 1000;
                        // maxtime = time[time.length-1] * 1000;
                        mintime = time[0];
                        maxtime = time[time.length-1];
                    }

                    mindim2 = dim2['data'][0];
                    maxdim2 = dim2['data'][dim2['data'].length-1];

                    var chart_data = [];
                    for (var i = 0; i < time.length; i++) {
                        if (datetime) {
                            var tx = (time0 + time[i]) * 1000;
                        }
                        else {
                            // var tx = time[i] * 1000;
                            var tx = time[i];
                        }
                        for (var j = 0; j < dim2['data'].length; j++) {
                            dx = data[vname][i][j];
                            if (dx !== null) {
                                minval = Math.min(minval,dx);
                                maxval = Math.max(maxval,dx);
                            }
                            chart_data.push([tx, dim2['data'][j],dx]);
                        }
                    } 
                    /*
                    console.log("heatmap, chart_data.length=",chart_data.length,
                            ", chart_data[0].length=",chart_data[0].length);
                    console.log("heatmap, minval=",minval,", maxval=",maxval);

                    console.log("heatmap, colsize=", (maxtime - mintime) / 20);
                    */
                    // var colsize = 3600 * 1000;
                    var colsize = (maxtime - mintime) / (time.length - 1);
                    var rowsize = (maxdim2 - mindim2) / (dim2.length - 1);

                    /*
                    for (var i = 0; i < chart_data.length; i++) {
                        if (chart_data[i][2] === null) {
                            chart_data[i][2] = minval;
                        }
                    }
                    */

                    /*
                    for (var i = 0; i < chart_data.length && i < 10; i++) {
                        for (var j = 0; j < chart_data[i].length; j++) {
                            console.log("chart_data[",i,"]=",
                                chart_data[i][0],",",chart_data[i][1],",",chart_data[i][2]);
                        }
                    }
                    */

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
            /*
            $("#id_time_length_choice").change(function() {
                console.log("time_length_choice change, val=",$(this).val());
                if ($(this).val() == '0' || $(this).val() == '') {
                    $("#id_time_length_val").show();
                }
                else {
                    $("#id_time_length_val").hide();
                }
            });
            */
        });
    })
);

