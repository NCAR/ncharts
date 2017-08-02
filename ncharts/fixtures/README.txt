
Note that the json parser is more picky than python, the last entry in a dictionary or list should NOT be followed by a comma.

Adding a platform
    Edit platform.json.

Adding a project
    Edit projects.json, and copy paste the json lines for an existing project.

    The primary key, "pk", for a project is its name, which should be unique to each.


    For a name of local time zone for the project, look at the directories in /usr/share/zoneinfo, for example "Europe/Lisbon".
    Check that the timezone is listed in timezones.json. If not, add it.

    Once you've added a project, then in platforms.json, add that project to every platform which will provide
    datasets to ncharts for that project.

Adding a dataset

1. determine a new, unique primary key, aka 'pk'.  To see the existing primary keys for datasets, do:

        fgrep pk datasets

   To see a sorted listing of the current primary keys:

        fgrep -h pk dataset* | cut -d: -f 2 | sort -u -n

   Choose a primary key that is not listed.

2. If your adding a dataset for a new project, copy an existing datasets_XXXXX.json to a new file.
    If you keep the prefix "datasets" on the file, then it's easier to check the primary keys for datasets,
    as above.

3. A dataset in a datasets_XXXXX.json file has two sections, both with the same "pk".

   The first section will be:
        "model": "ncharts.dataset",
   and will have fields generic to a dataset, such as its associated project, platforms,
   start and end time, location, a short name, and a long name. For a project that is currently
   running you can enter an end_time in the future.

   The second section will be:
        "model": "ncharts.filedataset",
   and that section is where one specifies the "directory" and "filenames" under the "fields" entry.
   The "filenames" element typically contains strftime format descriptors, such as %Y, %m, %d, %H, etc
   for matching the files in the dataset.

   For datasets served by a database, currently the GV-LRT and C130-LRT, the second section will be
   for a "model": "ncharts.dbdataset", and have fields, such as "dbname", "user", "host", and "table".
   For these datasets, one specifies an end_time in the future, typically Dec 31 of the current year.
