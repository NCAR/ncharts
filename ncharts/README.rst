=====
ncharts
=====

Charting Django app, developed at NCAR.

Detailed documentation is in the "docs" directory.

Quick start
-----------

1. Add "ncharts" to your INSTALLED_APPS setting like this::

      INSTALLED_APPS = (
          ...
          'ncharts',
      )

2. Include the polls URLconf in your project urls.py like this::

      url(r'^ncharts', include('ncharts.urls')),

3. Run `python manage.py syncdb` to create the polls models.

4. Start the development server and visit http://127.0.0.1:8000/admin/.

5. Visit http://127.0.0.1:8000/ncharts
