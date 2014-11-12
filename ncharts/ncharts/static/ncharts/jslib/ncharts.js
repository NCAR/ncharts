// See gregfranko.com/blog/jquery-best-practices
//
// IIFE: Immediately Invoked Function Expression
(
    function(main_iife_function) {
        main_iife_function(window.jQuery, window, document);
    }(function($,window,document) {
        $(function() {
            // the DOM is ready!
            console.log("DOM is ready!");
            // user selects 3 variables. Need to create 3 <div>s
            // for block in html can do that.
            // How to put multiple traces on a plot (temp and dp)?
            //  all with same units
            // this code can then determine the number of <div>s,
            // for each div, the column numbers in the data matrix, and
            // the variable names and long names, units
            // attach the variable name(s) to the <div>
            // map the variable name to the column(s) of data
            // client side determines whether to combine vars into one plot
            // server side just ships data, indexed by variable name (station #)
            //
            // could do .highcharts().  what to do on ajax call back of new data?
            //      destroy() and makeChart()
            // make charts global

            // $("#time-series").append("<p>hi from time-series</p>");
            //

            // $("#timex-series").html(data)

            // $("#timex-series").html("<p>" + chart_data[0].length +"</p>")

            console.log("time is " + (typeof time == "undefined"))

            var chart_title = 'zippie';

            var ncharts = $("div[id^='time-series']").length
            console.log("ncharts=",ncharts)

            // $("#time-series").highcharts({

            $("div[id^='time-series']").each(function(index) {
                console.log("im here, index=",index);
                console.log("this=",$( this ).text() );
                console.log(index + ": " + $( this ).data("variable"));

                var vname =  $( this ).data("variable");
                var units =  $( this ).data("units");
                var long_name =  $( this ).data("long_name");
                if (long_name.length == 0) {
                    long_name = vname;
                }

                // console.log("im here, vname=",vname);

                var chart_data = [];
                for (var i = 0; i < time.length; i++) {
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
        });
    }
));

