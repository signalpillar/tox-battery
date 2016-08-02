"""
Track changes in requirements.txt to recreate venv if needed.

The mechanism is the following:

- Detect envs that will be used in this run and process each separately.
- Find requirements files declared in `deps` parameter.
- Check whether requirements file has changed from previous run.
  This check is done by comparing current version of requirements file
  with previously saved version of the file.
  Previous version file is saved in the file with the path:
      `<toxwordir>/<original-req-file-name>.<venv-name>.previous

.. note::

    It is not possible to save .previous file in the env specific directory
    (``.tox/<venv>``) as it will be wiped on recreation and for the first
    creation procedure.
"""

# std
import filecmp
import os
import shutil

# 3rd-party
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

    is_enabled_env = lambda env: env.envname in config.envlist
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
        fname = '{0}.{0}.previous'.format(
            fname.replace('/', '-'), config.envname)
        return os.path.join(tox_dir, fname)

    requirement_files = map(parse_requirements_fname, deps)
    return any(
        is_changed(reqfile, build_fpath_for_previous_version(reqfile))
        for reqfile in requirement_files
        if reqfile and os.path.isfile(reqfile)
    )


def is_changed(fpath, prev_version_fpath):
    """Check requirements file is updated relatively to prev. version of the file.

    :param str fpath: Path to the requirements file.
    :param str prev_version_fpath: Path to the prev. version requirements file.
    :rtype: bool
    :raise ValueError: Requirements file doesn't exist.
    """
    if not (fpath and os.path.isfile(fpath)):
        raise ValueError(
            "Requirements file {0!r} doesn't exist.".format(fpath))

    prev_version_exists = os.path.isfile(prev_version_fpath)
    changed = False

    if prev_version_exists:
        changed = not are_equal_requirement_files(fpath, prev_version_fpath)

    if changed or not prev_version_exists:
        dirname = os.path.dirname(prev_version_fpath)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        shutil.copy(fpath, prev_version_fpath)
    return changed


def are_equal_requirement_files(fpath1, fpath2):
    return filecmp.cmp(fpath1, fpath2)


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


def content_of(fpath):
    with open(fpath) as fd:
        return fd.read()
