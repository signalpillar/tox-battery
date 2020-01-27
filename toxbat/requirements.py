"""
Track changes in requirements.txt to recreate venv if needed.

The mechanism is the following:

- Detect envs that will be used in this run and process each separately.
- Find requirements files declared in `deps` parameter.
- Check whether requirements file has changed from previous run.
  This check is done by comparing SHA1 sum of the requirements parsed from the
  current version of the file and sum computed from previous run and saved in a
  special file. File with previous version is saved in the file with the path:
      `<toxwordir>/<original-req-file-name>.<venvpathSHA1>.previous

Name of the version file is composed from 2 parts:

* Original requirements file name, so we can distinguish it, if there are
  multiple requirement files.
* ``venvpathSHA1``. This part allows us ignore the fact in which testenv file
  is used but focus on venv. Previously instead of SHA1 name of testenv was
  used that works most of the time, but breaks behavior when user sets
  ``envdir``
  (`see <http://tox.readthedocs.io/en/latest/config.html#confval-envdir>`_).
  This is because tox-battery expected to find previous-version file for each
  testenv regardless whether they use same venv or not.

.. note::

    It is not possible to save .previous file in the env specific directory
    (``.tox/<venv>``) as it will be wiped on recreation and for the first
    creation procedure.
"""

import hashlib
import os

try:
    # pip >= 20
    from pip._internal.network.session import PipSession
    from pip._internal.req.req_file import parse_requirements
except ImportError:
    try:
        # pip < 10
        from pip.download import PipSession
        from pip.req import parse_requirements
    except ImportError:
        # It is quick hack to support pip 10 that has changed its internal
        # structure of the modules.
        from pip._internal.download import PipSession
        from pip._internal.req.req_file import parse_requirements

from tox import hookimpl


@hookimpl
def tox_configure(config):
    """
    :param tox.config.Config config: Configuration object to observe.
    :rtype: tox.config.Config
    """
    return _ensure_envs_recreated_on_requirements_update(config)


def _ensure_envs_recreated_on_requirements_update(config):
    user_asked_to_recreate = config.option.recreate
    if user_asked_to_recreate:
        return config

    def is_enabled_env(env):
        return env.envname in config.envlist

    for env in filter(is_enabled_env, config.envconfigs.values()):
        requires_recreation = are_requirements_changed(env)
        if not env.recreate and requires_recreation:
            env.recreate = True
    return config


def are_requirements_changed(config):
    """Check if any of the requirement files used by testenv is updated.

    :param tox.config.TestenvConfig config: Configuration object to observe.
    :rtype: bool
    """
    deps = (dep.name for dep in config.deps)

    def build_fpath_for_previous_version(fname):
        tox_dir = config.config.toxworkdir.strpath
        envdirkey = _str_to_sha1hex(str(config.envdir))
        fname = '{0}.{1}.previous'.format(fname.replace('/', '-'), envdirkey)
        return os.path.join(tox_dir, fname)

    requirement_files = map(parse_requirements_fname, deps)
    return any([
        is_changed(reqfile, build_fpath_for_previous_version(reqfile))
        for reqfile in requirement_files
        if reqfile and os.path.isfile(reqfile)])


def parse_pip_requirements(requirement_file_path):
    """
    Parses requirements using the pip API.

    :param str requirement_file_path: path of the requirement file to parse.
    :returns list: list of requirements
    """
    return sorted(
        str(r.req)
        for r in parse_requirements(requirement_file_path,
                                    session=PipSession())
        if r.req
    )


def is_changed(fpath, prev_version_fpath):
    """Check requirements file is updated relatively to prev. version of the file.

    :param str fpath: Path to the requirements file.
    :param str prev_version_fpath: Path to the prev. version requirements file.
    :rtype: bool
    :raise ValueError: Requirements file doesn't exist.
    """
    if not (fpath and os.path.isfile(fpath)):
        raise ValueError("Requirements file {0!r} doesn't exist.".format(fpath))

    # Compile the list of new requirements.
    new_requirements = parse_pip_requirements(fpath)

    # Hash them.
    new_requirements_hash = _str_to_sha1hex(str(new_requirements))

    # Read the hash of the previous requirements if any.
    previous_requirements_hash = 0
    if os.path.exists(prev_version_fpath):
        with open(prev_version_fpath) as fd:
            previous_requirements_hash = fd.read()

    # Create/Update the file with the hash of the new requirements.
    dirname = os.path.dirname(prev_version_fpath)
    # First time when running tox in the project .tox directory is missing.
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    with open(prev_version_fpath, 'w+') as fd:
        fd.write(new_requirements_hash)

    # Compare the hash of the new requirements with the hash of the previous
    # requirements.
    return previous_requirements_hash != new_requirements_hash


def parse_requirements_fname(dep_name):
    """Parse requirements file path from dependency declaration (-r<filepath>).

    >>> parse_requirements_fname('pep8')
    >>> parse_requirements_fname('-rrequirements.txt')
    'requirements.txt'

    :param dep_name: Name of the dependency
    :return: Requirements file path specified in the dependency declaration
        if specified otherwise None
    :rtype: str or None
    """
    req_option = '-r'
    if dep_name.startswith(req_option):
        return dep_name[len(req_option):]


def _str_to_sha1hex(v):
    """ Turn string into a SHA1 hex-digest.

    >>> _str_to_sha1hex('abc')
    'a9993e364706816aba3e25717850c26c9cd0d89d'
    """
    return hashlib.sha1(v.encode('utf-8')).hexdigest()
