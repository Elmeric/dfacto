# User's Guide

How-to's and Recipes...

---

## How To install Dfacto?

### Python Version

We recommend using the latest version of Python. Dfacto
supports Python 3.7.2 and newer.

### Dependencies

These libraries will be installed automatically when installing Dfacto.


- ...

### Install Dfacto in a virtual environment

Use a virtual environment to manage the dependencies for your project. You may use the
standard `python venv` module or your preferred packages manager such as `poetry`.

=== "Python venv"

    Create an environment:
    ``` shell
    $ mkdir myproject
    $ cd myproject
    $ python3 -m venv venv
    ```

    TIP: On Windows, you may have to replace the `python3` command by `py -3`, depending
    on your Python installation.

    Activate the environment:
    ``` shell
    $ source venv/bin/activate
    ```
    or, on Windows:
    ``` shell
    $ venv/Scripts/activate.bat
    ```

    Install Trio-Engineio:
    ``` shell
    $ pip install trio_engineio
    ```

=== "Poetry"

    Setup a new project:
    ``` shell
    $ poetry new --src myproject
    ```

    Add a dependency to Trio-Engineio and install it:
    ``` shell
    $ poetry add trio_engineio
    $ poetry install
    ```

    Activate the project environment created by Poetry:
    ``` shell
    $ source {path_to_venv}/bin/activate
    ```
    or, on Windows:
    ``` shell
    $ {path_to_venv}/Scripts/activate.bat
    ```

    TIP: You can retrieve the {path_to_venv} created by Poetry with:
    ``` shell
    $ poetry env info --path
    ```


