// See gregfranko.com/blog/jquery-best-practices
//
// IIFE: Immediately Invoked Function Expression
(function(main_iife_function) {
        main_iife_function(window.jQuery, window, document);
    }(function($,window,document) {
        var unique = function(arr) {
            return arr.filter(function(value, index, array) {
                return array.indexOf(value) === index;
            });
        };
        $(function() {

            // hide/show the time_length_val input depending on the time_length_choice
            cval = $("#id_time_length_choice").val();
            console.log("time_length_val ready, choice val=", cval);
            if (cval === '' || cval === '0') {
                console.log("time_length_val show");
                $( "#id_time_length_val" ).show();
            }
            else {
                console.log("time_length_val hide");
                $( "#id_time_length_val" ).hide();
            }

            // console.log("time is " + (typeof time == "undefined"))

            // var ncharts = $("div[id^='time-series']").length
            // console.log("ncharts=",ncharts)

            console.log("DOM is ready!");

            $("div[id^='time-series']").each(function(index) {

                var vnames =  $( this ).data("variables");
                var vunits =  $( this ).data("units");
                var long_names =  $( this ).data("long_names");
                if (long_names.length == 0) {
                    long_names = vnames;
                }
                console.log("time-series, time.length=",time.length);
                console.log("vnames=",vnames,", vunits=",vunits);

                // series and yAxis are arrays of dictionaries
                var yAxis = [];
                
                var unique_units = unique(vunits);
                console.log("unique_units=",unique_units);
                var opposite = false;
                for (var unit of unique_units) {
                    console.log("unit=",unit);
                    ya = {
                        opposite: opposite,
                        title: {
                            text: unit,
                        },
                    };
                    yAxis.push(ya);
                    opposite = !opposite;
                }

                var series = [];
                for (var iv = 0; iv < vnames.length; iv++ ) {
                    var vname = vnames[iv];
                    var vunit = vunits[iv];
                    var long_name = long_names[iv];
                    var vseries = {};
                    var vdata = [];
                    for (var i = 0; i < time.length; i++) {
                        // var d = new Date((time0 + time[i])*1000);
                        // d += d.utcOffset
                        vdata.push([(time0 + time[i])*1000, data[vname][i]]);
                    }
                    vseries['data'] = vdata;
                    if (unique_units.length > 1) {
                        vseries['name'] = vname + '(' + vunit + ')';
                    }
                    else {
                        vseries['name'] = vname;
                    }
                    vseries['yAxis'] = unique_units.indexOf(vunit);
                    vseries['tooltip'] = {
                        // valueSuffix: long_name,
                        pointFormat: '<span style="color:{series.color}">\u25CF</span> ' + long_name + ',{series.name}: <b>{point.y}</b><br/>',
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
                        startOnTick: false,
                        endOnTick: false,
                        title: {
                            text: 'time'
                        },
                    },
                    yAxis: yAxis,
                    series: series,
                    legend: {
                        enabled: true,
                        rtl: false,
                    },
                });
            });

            $("div[id^='heatmap']").each(function(index) {

                var vnames =  $( this ).data("variables");
                var vunits =  $( this ).data("units");
                var long_names = $( this ).data("long_names");

                console.log("heatmap, vnames=",vnames,
                        ",time.length=",time.length,
                        ",dim2.length=",dim2['data'].length);

                if (long_names.length == 0) {
                    long_names = vnames;
                }

                // var vname =  $( this ).data("variable");
                // var units =  $( this ).data("units");
                // var long_name =  $( this ).data("long_name");
                // var dim2_name =  $( this ).data("dim2_name");
                var dim2_name = dim2['name'];
                var dim2_units = dim2['units'];

                for (var iv = 0; iv < vnames.length; iv++) {
                    vname = vnames[iv];
                    long_name = long_names[iv];
                    units = vunits[iv];

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
                    console.log("heatmap, chart_data.length=",chart_data.length,
                            ", chart_data[0].length=",chart_data[0].length);
                    console.log("heatmap, minval=",minval,", maxval=",maxval);

                    console.log("heatmap, colsize=", (maxtime - mintime) / 20);
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

                    for (var i = 0; i < chart_data.length && i < 10; i++) {
                        for (var j = 0; j < chart_data[i].length; j++) {
                            console.log("chart_data[",i,"]=",
                                chart_data[i][0],",",chart_data[i][1],",",chart_data[i][2]);
                        }
                    }

                    $( this ).highcharts({
                        chart: {
                            type: 'heatmap',
                            marginTop: 40,
                            marginBottom: 40,
                            zoomType: 'x',
                            panning: true,
                            panKey: 'shift',
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
                                text: 'time'
                            },
                            /*
                            tickPixelInterval: (maxtime - mintime) / 100,
                            ordinal: false,
                            */
                        },
                        yAxis: {
                            title: {
                                text: dim2_name + '(' + dim2_units + ')'
                            },
                            min: mindim2,
                            max: maxdim2,
                            tickWidth: 2,
                            /*
                            ordinal: false,
                            */
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
                                pointFormat: 'time:{point.x:%H:%M},' + dim2_name + ':{point.y},' + vname + ':{point.value}'
                            }
                        }],
                    });
                }
            });
            $("div[id^='hc-time-series']").each(function(index) {

                var vname =  $( this ).data("variable");
                var units =  $( this ).data("units");
                var long_name =  $( this ).data("long_name");
                if (long_name.length == 0) {
                    long_name = vname;
                }

                console.log("time-series, time.length=",time.length,
                        ",data.length=",data.length);

                var chart_data = [];
                for (var i = 0; i < time.length; i++) {
                    // var d = new Date((time0 + time[i])*1000);
                    // d += d.utcOffset
                    chart_data.push([(time0 + time[i])*1000, data[vname][i]]);
                } 

                $( this ).highcharts({
                    chart: {
                        type: 'line',
                        zoomType: 'x',
                        panning: true,
                        panKey: 'shift',
                        marginLeft: 100,
                    },
                    title: {
                        text: long_name
                    },
                    xAxis: {
                        type: 'datetime',
                        dateTimeLabelFormats: {
                            millisecond: '%H:%M:%S.%L',
                            second: '%H:%M:%S',
                            minute: '%H:%M',
                            hour: '%H:%M',
                            day: '%e. %b',
                            month: '%b \'%y',
                            year: '%Y'
                        },
                        title: {
                            text: 'time'
                        },
                    },
                    yAxis: {
                        title: {
                            text: vname + '(' + units + ')'
                        },
                    },
                    series:[{
                        data: chart_data
                    }],
                });
            });
            $("#id_time_length_choice").change(function() {
                console.log("time_length_choice change, val=",$(this).val());
                if ($(this).val() == '0' || $(this).val() == '') {
                    $("#id_time_length_val").show();
                }
                else {
                    $("#id_time_length_val").hide();
                }
            });
        });
    })
);

