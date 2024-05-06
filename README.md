# Setting Up Blackhole

Start by installing the latest release of `Python 3.11`, available at https://www.python.org/downloads/.

Follow the instructions at https://python-poetry.org/docs/ in order to set up `poetry` on your machine. In a nutshell, this will involve installing `pipx`, followed by using pipx to install `poetry`.

Next, it's time to set up your virtual environment. Navigate to your `blackhole` repo directory in the command line. It's possible `poetry` may be able to find your `Python 3.11` install automatically due to there being multiple versions of Python installed on your machine. For that reason, it's simplest to provide `poetry` the absolute path to your install directory, like so:

>`env use C:\Users\{YOUR_USER_NAME}\AppData\Local\Programs\Python\Python311\python.exe`

Once poetry has created your virtual environment, enter:

> poetry install

This command will install all required dependencies to the virtual environment.

# Running Blackhole

To run `blackhole`, enter:

> poetry run start-blackhole

You should see the following: 

>INFO:     Started server process [532]
>
>INFO:     Waiting for application startup.
>
>INFO:     Application startup complete.
>
>INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

At this point `blackhole` is ready to receive API requests. While the server is runing, you may view the Swagger page for the app at: http://127.0.0.1:8000/docs