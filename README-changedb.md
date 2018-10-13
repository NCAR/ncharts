# Switching ncharts database from sqlite to postgres

1. Setup postgres server
   See `README-devel.md`.

2. Check django database configuration

  To dump the existing sqlite database, the database in `datavis/settings/default.py` and `datavis/settings/production.py` should be sqlite:

  ```sh
  DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(VAR_LIB_DIR, 'db.sqlite3'),
        'OPTIONS': {'timeout': 20,},
    }
  }
```

3. Save clientstate fields from existing sqlite database

  ```sh
  python3 manage.py dumpdata --indent 2 sessions.session ncharts.variabletimes \
      ncharts.clientstate_data_times ncharts.clientstate > /tmp/datadump.json
```

4. Switch django database configuration

  In `datavis/settings/default.py`, and `datavis/settings/production.py`, set DATABASES to postgresql:

  ```sh
  DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ncharts',
        'CONN_MAX_AGE': 10,
    }
  }
```

5. Create and initialize the postgres database

   Follow instructions in `README-devel.md` or `README-prod.md`.

6. Restore clientstate fields

  ```sh
python3 manage.py loaddata /tmp/datadump.json
```

7. Restart ncharts
