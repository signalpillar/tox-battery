.. image:: https://travis-ci.org/signalpillar/tox-battery.svg
    :target: https://travis-ci.org/signalpillar/tox-battery


The project is an attempt to add to the `tox
<http://tox.readthedocs.org/en/latest/>`_ some missing out of the box functionality.

Basically it is just an extension for the tool that will be loaded automatically.

Features
--------

First `experimental feature <https://bitbucket.org/hpk42/tox/issues/149/virtualenv-is-not-recreated-when-deps>`_ is to recreate virtual environment on requirements file update.

Installation
------------

Thanks to entrypoints mechanism used by tox plugin system no additional configuration
is required except of the package installation.

::

    pip install tox-battery
