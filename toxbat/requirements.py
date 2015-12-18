"""
Track changes in requirements.txt to recreate venv if needed.

The mechanism is the following:

- Detect envs that will be used in this run and process each separately.
- Find requirements files declared in `deps` parameter.
- Check whether requirements file has changed from previous run.
  This is check is done by comparing current version of requirements file
  with previously saved version of the file.
  Previous version file is saved in the file with the path:
      `<toxwordir>/<original-req-file-name>.<venv-name>.previous

.. note::

    It is not possible to save .previous file in the env specifiec directory
    (``.tox/<venv>``) as it will be wiped on recreation and for this first
    creation procedure.
"""

# std
import os
import shutil

# 3rd-party
import pkg_resources
from tox import hookimpl


@hookimpl
def tox_configure(config):
    """
    @param tox.config.Config config: Configuration object to observe.
    @rtype: tox.config.Config
    """
    return _ensure_envs_recreated_on_requirements_update(config)


@hookimpl
def tox_addoption(parser):
    # add option to describe strategy how toreload updated requirements
    pass


def _ensure_envs_recreated_on_requirements_update(config):
    user_asked_to_recreate = config.option.recreate
    if user_asked_to_recreate:
        return config

    is_enabled_env = lambda (env_name, env): env_name in config.envlist
    for env_name, env in filter(is_enabled_env, config.envconfigs.items()):
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
        fname = '{}.{}.previous'.format(
            fname.replace('/', '-'), config.envname)
        return os.path.join(tox_dir, fname)

    requirement_files = map(parse_requirements_fname, deps)
    return any(
        is_changed(reqfile, build_fpath_for_previous_version(reqfile))
        for reqfile in requirement_files
        if os.path.isfile(reqfile)
    )


def is_changed(fpath, prev_version_fpath):
    """Check requirements file is updated relatively to prev. version of the file.

    :param str fpath: Path to the requirements file.
    :param str prev_version_fpath: Path to the prev. version requirements file.
    :rtype: bool
    :raise ValueError: Requirements file doesn't exist.
    """
    if not (fpath and os.path.isfile(fpath)):
        raise ValueError("Requirements file {!r} doesn't exist.".format(fpath))

    prev_version_exists = os.path.isfile(prev_version_fpath)
    changed = False

    if prev_version_exists:
        current_reqs = parse_requirements(content_of(fpath))
        previous_reqs = parse_requirements(content_of(prev_version_fpath))
        changed = current_reqs != previous_reqs

    if changed or not prev_version_exists:
        shutil.copy(fpath, prev_version_fpath)
    return changed


def parse_requirements(file_content):
    """
    :param str file_content: Content of the requirements file
    :rtype: list[pkg_resources.Requirements]
    """
    return list(pkg_resources.parse_requirements(file_content))


def parse_requirements_fname(dep_name):
    """Parse requirements file path from dependency declaration (-r<filepath>).

    >>> parse_requirements_fname('pep8')
    None
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
