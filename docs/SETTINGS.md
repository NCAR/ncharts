# ncharts Settings

Django settings are defined in `datavis/settings`.

Default values are defined in `default.py`, and then may be overridden by environment-specific settings files, such as `production.py` and `override.py`, which are described below.

## Production

To run in production mode, set `DJANGO_SETTINGS_MODULE` to `datavis.settings.production`. Production mode disables debug logging and configures allowed hosts. **When ncharts is exposed to the internet at large, it should be run in production mode.**

```sh
export DJANGO_SETTINGS_MODULE=datavis.settings.production
```

## Override (optional)

Settings can be overridden via an optional override file, `datavis/settings/override.py`. `override.py` is `.gitignore`d, so you can make environment-specific changes to settings without modifying files that are tracked in version control.

For example, production `ADMINS` for `datavis.eol.ucar.edu` are defined in `datavis/settings/override.datavis.eol.ucar.edu.py`. A symbolic link can made from this file to `override.py`

```sh
cd datavis/settings
ln -s override.datavis.eol.ucar.edu.py override.py
```

Note that `override.py` is `import`ed at the **end** of `default.py` and `production.py`, so any settings that are **derived** from values defined within those respective files will need to be redefined in `override.py`.

For example, `CACHES` is based on `VAR_RUN_DIR` in `production.py`. If `VAR_RUN_DIR` is overridden in `override.py`, then `CACHES` will need to be assigned again in `override.py` if `CACHES` is to be based on the overridden value of `VAR_RUN_DIR`.
