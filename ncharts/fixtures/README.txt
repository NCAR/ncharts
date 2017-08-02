
Note that the json parser is more picky than python, the last entry in a dictionary or list should NOT be followed by a comma.

Adding a platform
    Edit platform.json, and copy/paste the lines of an existing platform.

Adding a project
    Edit projects.json, and copy/paste the json lines from an existing project to add your new project.

    The primary key, "pk", for a project is its name, which should be unique to each.

    For a name of local timezone for the project, look at the directories in /usr/share/zoneinfo, for example "Europe/Lisbon".
    Check that the timezone is listed in timezones.json. If not, add it.

    Once you've added a project, then in platforms.json, add that project to every platform which will provide
    datasets to ncharts for that project.

Adding a dataset

1. determine a new, unique primary key, aka 'pk'.  To see the existing primary keys for datasets, do:

        fgrep pk datasets

   To see a sorted listing of the current primary keys:

        fgrep -h '"pk"' dataset* | cut -d: -f 2 | sort -u -n

   Choose a primary key that is not listed.

2. If you're adding a dataset for a new project, copy an existing datasets_XXXXX.json to a new file.
    If you keep the prefix "datasets" on the file, then it's easier to check the primary keys for datasets,
    as above.

3. A dataset in a datasets_XXXXX.json file has two sections, both with the same "pk".

   The first section will be:
        "model": "ncharts.dataset",
   and will have fields generic to a dataset, such as its associated project, platforms,
   start and end time, location, a short name, and a long name. For a project that is currently
   running you can enter an end_time in the future.

   Under "fields", the "variables" entry is typically empty. This is only used for the weather
   station datasets, to add meta-data, such as units, and long_name to the variables, since
   this information is not found in the NetCDF files.

   The second section will be:
        "model": "ncharts.filedataset",
   and that section is where one specifies the "directory" and "filenames" under the "fields" entry.
   The "filenames" element typically contains strftime format descriptors, such as %Y, %m, %d, %H, etc
   for matching the files in the dataset.

   For datasets served by a database, currently the GV-LRT and C130-LRT, the second section will be
   for a "model": "ncharts.dbdataset", and have fields, such as "dbname", "user", "host", and "table".
   For these datasets, one specifies an end_time in the future, typically Dec 31 of the current year.


Uploading changes to the ncharts database

    After making a change to a json file, go to the top ncharts directory, and run
        ./load_db.sh
    You'll need the value of the EOL_DATAVIS_SECRET_KEY environment variable to run
    the above on a production server.

Deleting a project, platform, or datasets
    Use the admin URL for ncharts from within the EOL firewall to delete a
    one or more of the above from the ncharts django database.
    
