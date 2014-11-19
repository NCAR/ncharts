// See gregfranko.com/blog/jquery-best-practices
//
// IIFE: Immediately Invoked Function Expression
(
    function(main_iife_function) {
        main_iife_function(window.jQuery, window, document);
    }(function($,window,document) {
        $(function() {
            // console.log("DOM is ready!");

            // console.log("time is " + (typeof time == "undefined"))

            // var ncharts = $("div[id^='time-series']").length
            // console.log("ncharts=",ncharts)

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

            $("div[id^='time-series']").each(function(index) {

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

                $( this ).highcharts('StockChart',{
                    chart: {
                        type: 'line',
                        // zoomType: 'x',
                        // panning: true,
                        // panKey: 'shift',
                    },
                    title: {
                        text: long_name
                    },
                    series:[{
                        name: 'data',
                        data: chart_data
                    }],
                });
            });

            $("div[id^='heatmap']").each(function(index) {

                var vname =  $( this ).data("variable");
                var units =  $( this ).data("units");
                var long_name =  $( this ).data("long_name");
                var dim2_name =  $( this ).data("dim2_name");

                if (long_name.length == 0) {
                    long_name = vname;
                }

                console.log("heatmap, vname=",vname,
                        ",time.length=",time.length,
                        ",dim2.length=",dim2.length,
                        ",data[vname].length=",data[vname].length);

                minval = Number.POSITIVE_INFINITY;
                maxval = Number.NEGATIVE_INFINITY;

                var datetime = true;

                if (datetime) {
                    mintime = time0 + time[0] * 1000;
                    maxtime = time0 + time[time.length-1] * 1000;
                }
                else {
                    // mintime = time[0] * 1000;
                    // maxtime = time[time.length-1] * 1000;
                    mintime = time[0];
                    maxtime = time[time.length-1];
                }

                mindim2 = dim2[0];
                maxdim2 = dim2[dim2.length-1];

                var chart_data = [];
                for (var i = 0; i < time.length; i++) {
                    if (datetime) {
                        var tx = time0 + time[i] * 1000;
                    }
                    else {
                        // var tx = time[i] * 1000;
                        var tx = time[i];
                    }
                    for (var j = 0; j < dim2.length; j++) {
                        dx = data[vname][i][j];
                        if (dx !== null) {
                            minval = Math.min(minval,dx);
                            maxval = Math.max(maxval,dx);
                        }
                        chart_data.push([tx, dim2[j],dx]);
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
                        marginBottom: 40
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
                            day: '%e. %b',
                            month: '%b \'%y',
                            year: '%Y'
                        },
                        /*
                        */
                        min: mintime,
                        max: maxtime,
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
                            text: dim2_name
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
            });
        });
    }
));

