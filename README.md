# Oxford Rivers
Oxford Rivers is a monitoring service for the river levels and flow around Oxford, with a view to providing information for the Oxford University rowing community.
The project is written in Python and Django, and is geared towards deployment using Docker and Gunicorn, with a MySQL database and data collection performed by a Celery worker, scheduler, and an Amazon SQS message broker.

A live deployment is currently running at [boards.other.fantasybumps.org.uk](https://boards.other.fantasybumps.org.uk).


## Running in development
Oxford Rivers has three requirements files:

  * `requirements.txt` -
  This is the main requirements file and contains all the dependencies needed for running tests or a development server.
  For simplicity, this file deliberately excludes the production-only dependencies of `mysqlclient`, `gunicorn`, and the SQS transport packages (`boto3` and `pycurl`),
  since these packages facilitate connections to external services which can be substituted out in development,
  e.g. for an SQLite database, or the `runserver` command.
  * `requirements_linting.txt` - This describes the requirements needed for running the Flake8 linting.
  * `requirements_dev.txt` - This describes the additional tooling needed for development, currently just `pre-commit`.

Automated quality control is performed through linting and testing.

 * Linting is performed with the `flake8` command, once the linting requirements have been installed.
 * Testing is performed with the build-in Django test runner, `python manage.py test`.

Both are performed by the GitHub Actions pipeline (`.github/workflows`), which also builds, & verifies the Docker image.
Pushing to the `deploy` branch will also publish the built image to Docker Hub.
Both checks are also run on every commit by [pre-commit](https://pre-commit.com/) hooks, which can be installed after installing the development requirements with:

    pip install -r requirements_dev.txt
    pre-commit install

Typing with MyPy may also be added in future (see the out-dated `trials/typing` branch), but previous integrations with Django and - in particular - Celery have been found lacking utility.

A database can be created and populated with the following set of commands:

    python manage.py migrate
    python manage.py loaddata flags
    python manage.py scrape_ea_boards
    python manage.py scrape_ourcs_flag_history
    python manage.py fetch_ourcs_flags

Unless configured otherwise in `core/settings.py:DATABASES`, an SQLite database called `database.sqlite3` will be created in the project root.
The latter three commands here are custom data collection commands provided by the project.

  * `scrape_ea_boards` retrieves the current EA boards from [their status page](http://riverconditions.environment-agency.gov.uk/).
  * `scrape_ourcs_flag_history` retrieves the history of the OURCs flag from [their flag information](https://ourcs.co.uk/information/flags/isis/) [pages](https://ourcs.co.uk/information/flags/godstow/).
  * `fetch_ourcs_flag` retrieves the current OURCs flag statuses from [their API](https://ourcs.co.uk/api/flags/status/isis/) [endpoints](https://ourcs.co.uk/api/flags/status/godstow/).

`scrape_ea_boards` and `fetch_ourcs_flag` should be run regularly to keep the data displayed up-to-date, but `scrape_ourcs_flag_history` only needs to be run once (and should be impotent thereafter).

Finally, the development server can be run on port 8000 with:

    python manage.py runserver [0.0.0.0:8000]

where adding the `0.0.0.0:8000` option allows external devices to also access the server (e.g. for mobile testing).

_While it is possible to run and test the Celery processes locally, a production-lite environment with locally-built Docker images is recommended to manage the necessary orchestration.
See below for more information._


## MCP server
The site also acts as an [MCP](https://modelcontextprotocol.io/) server at `/mcp`, built with `django-mcp-server`, so that Claude and other AI clients can read the river state directly rather than scraping the index page.
It is served by the same container as the rest of the site, is read-only, and (like the index page) needs no authentication.
To use it, add `https://<your domain>/mcp` as a remote custom connector in Claude.

It provides a single tool, `get_river_conditions`, which takes no arguments and returns the current OURCs flags, Jameson differentials (with bands, where defined), EA advisory boards and the transit permissions.
These are built from the same data and model properties as the index page (`flags.views.Index`), so the two cannot drift apart.
Every call reads the database afresh, so nothing is cached.
If no differentials are available, `differentials_available` is `false` and the list is empty, and clients should treat that as missing data rather than "nothing to report".

To try it locally, run the development server on port 8765 and use the project's `.mcp.json`, which points an MCP client such as Claude Code at it:

    python manage.py runserver 8765

The differentials come from the unmanaged `jameson.Differential` model, which reads a `flag` table (`time`, `reach`, and `flow` columns) from the `jameson` database.
Without access to Jameson's database, the table must be created by hand with some sample rows; otherwise the differentials will be reported as unavailable.
The tool's tests (`flags/tests/test_mcp.py`) make real JSON-RPC calls to `/mcp` and mock the Jameson lookup.


## Running in production
A Docker image of the project is available on [DockerHub](https://hub.docker.com/repository/docker/joehitchen/oxford-rivers) as `joehitchen/oxford-rivers` and this is the recommended deployment method, although others are possible.

By default this image will run a Gunicorn HTTP web server on port 8000.
The project is not arranged to support HTTPS connections directly, and should be placed behind a reverse proxy such as NGINX or Traefik.
To configure the web server, environment variables for the database should be set as indicated in `core/settings.py:DATABASES`.
Additionally, Django should be provided with a comma-separated list of the domain names it is running under in the `DJANGO_HOSTS` environment variables, and a long, random string of characters as `DJANGO_SECRET_KEY`.

Static files are collected in the `static` directory within the image, and from here can be shared in a volume for another container to serve or uploaded cloud service such as AWS S3 for hosting.
Django expects these files to be served under `/static/` by default, but this can be configured with the `STATIC_URL` environment variable.
This collection also includes the site's `favicon.ico` and `robots.txt` file, which should be served directly on the site's root, rather than the regular static URL.

To keep the data displayed up-to-date, regular retrievals from external sources must be performed.
This can be done by running the management commands on a regular basis - 
e.g. by scheduling a cron job on the server that calls the management commands using `docker run` or `docker exec` in some way - 
or by making use of the Celery framework provided.
The image contains all the connections necessary for a Celery worker and Celery Beat scheduler to operate, with Amazon SQS as a message broker between them.
The two Celery services should be pointed at it using the `CELERY_BROKER` environment variable (e.g. `sqs://`) and also be passed all the same environment variables as the web server.
Any further transport settings, such as the AWS region or a queue name prefix, can be provided as a JSON object in the `CELERY_BROKER_OPTIONS` environment variable, and AWS credentials are picked up from the usual environment variables or the host's IAM role.
The image does not contain the packages for other brokers, such as Redis, so these would need adding to the Dockerfile.
For testing the Celery services without a broker, `CELERY_BROKER=memory://` can be used, although tasks cannot then be passed between the processes.
Once configured, the Celery services can be run with the commands:

    Worker: celery --app=core worker --log-level=info
    Scheduler: celery --app=core beat --log-level=info

The scheduler will trigger an OURCs flag retrieval jobs every two minutes and an EA board scraping job every five minutes, which are then executed on the worker.

