
# Adding NCharts Fixtures

## JSON inputs

The NCharts fixtures are specified as JSON dictionaries.  Note the json
parser is more picky than python, the last entry in a dictionary or list
should NOT be followed by a comma.

## Adding a platform

Edit `platform.json`, and copy/paste the lines of an existing platform.

## Adding a project

Edit `projects.json`, and copy/paste the json lines from an existing project to add your new project.

The project primary key, `pk`, is its name.  Each project primary key should be unique.

For a name of local timezone for the project, look at the directories in `/usr/share/zoneinfo`, for example `Europe/Lisbon`.
Check that the timezone is listed in `timezones.json`. If not, add it.

Once you've added a project, then in `platforms.json`, add that project to every platform which will provide
datasets to ncharts for that project.

## Adding a dataset

### Select a primary key

Determine a new, unique primary key or _pk_ for the dataset.  This command
prints a sorted listing of the current primary keys:

    fgrep -h '"pk"' datasets_* | cut -d: -f 2 | sort -u -n

Or the same command is available as the `printkeys` operation in the `load_db.sh` script:

    load_db.sh printkeys ncharts/fixtures/datasets*

Choose a primary key that is not listed.

### Create the datasets JSON file

If you're adding a dataset for a new project, copy an existing
`datasets_XXXXX.json` to a new file.  Keep the prefix "datasets" in the
filename.  That makes it easier to check the primary keys for datasets, as
above, but it is also required for the [`load_db.sh`](../../load_db.sh)
script to find and load the dataset file.

A dataset in a `datasets_XXXXX.json` file has two sections, both with the
same _pk_.  The first section will be:

    "model": "ncharts.dataset",

and will have fields generic to a dataset, such as its associated
project, platforms, start and end time, location, a short name, and a
long name. For a project that is currently running you can enter an
end_time in the future.

Under "fields", the "variables" entry is typically empty. This is only
used for the weather station datasets, to add meta-data, such as units,
and long_name to the variables, since this information is not found in
the NetCDF files.

The second section will be:

    "model": "ncharts.filedataset",

That section is where one specifies the _directory_ and _filenames_ under
the _fields_ entry.  The _filenames_ element typically contains strftime
format descriptors, such as %Y, %m, %d, %H, etc for matching the files in
the dataset.

For datasets served by a database, currently the GV-LRT and C130-LRT, the second section will be:

    "model": "ncharts.dbdataset"

It has fields such as "dbname", "user", "host", and "table".  For these
datasets, one specifies an `end_time` in the future, typically Dec 31 of
the current year.

## Uploading changes to the ncharts database

After making a change to a json file, go to the top ncharts directory, and run

    ./load_db.sh

## Updating production

The django production installation relies on a sqlite3 database in
`/var/lib/django`.  The database file is owned by `root` but kept
group-writable for the `apache` group.  That way anyone in the `apache`
group can modify the django database, instead of requiring `sudo`.

The environment variable `EOL_DATAVIS_SECRET_KEY` needs to be set to run the
above on a production server.  When `load_db.sh` is run on the production
server, that environment variable is set automatically by sourcing the
`key.sh` script.  The `key.sh` script parses the key from the systemd unit
file where it is set.

Normally, fixture changes should be committed (and tested, if possible)
somewhere else and pushed to github, then fetched on the production server.
Then the latest fixtures must be loaded into the django database.  Here are
the current steps:

    ssh <server>
    cd /var/django/ncharts
    git pull
    ./load_db.sh

The `load_db.sh` script by default loads the fixtures into the database.
That operation only requires `apache` group membership and not `sudo`.  If
the permissions ever need to be restored, the `load_db.sh` script can used
for that like so:

    ./load_db.sh fixperms

## Deleting a project, platform, or datasets

Use the admin URL for ncharts from within the EOL firewall to delete one or
more fixtures from the ncharts django database.  Since there are many `File
datasets`, all with similar names like `noqc_instrument`, you can look at
the link for each to identify the right dataset by the specific primary key
in the link.
