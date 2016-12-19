# std
import os
import subprocess
import textwrap

# local
from toxbat import requirements

# 3rd-party
import pytest


def test_is_changed_fails_on_missing_req_file():
    with pytest.raises(ValueError):
        requirements.is_changed('nonexisting/requirements.txt', 'nonexisting/requirements.txt')


def test_venv_recreated_with_simple_changes_in_file(tmpdir):
    """ Environment is recreated on any file change.
    We don't understand semantics of the requirements file,
    so even simple line swapping trigger environment recreation.
    """
    # given
    tmpdir = tmpdir.strpath
    path = lambda *args: os.path.join(tmpdir, *args)
    update_file(
        path('tox.ini'),
        textwrap.dedent('''
        [tox]
        skipsdist=True

        [testenv:python]
        deps = -rreq1/requirements.txt
        commands = {posargs}
    '''))
    update_file(
        path('req1/requirements.txt'),
        textwrap.dedent('''
        pytest-xdist==1.13.0
        pep8
    '''))
    run('tox -e python -- python -V'.split(), tmpdir)
    marker_fpath = path('.tox/python/marker.file')
    update_file(marker_fpath, '')

    # excercise
    # change order of dependencies
    update_file(
        path('req1/requirements.txt'),
        textwrap.dedent('''
        pep8
        pytest-xdist==1.13.0
    '''))
    run('tox -e python -- python -V'.split(), tmpdir)

    # verify
    assert not os.path.isfile(marker_fpath)
    # assert True


def test_venv_notrecreated_without_requirements_file_update(tmpdir):
    """Ensure recreation doesn't occur when requirement files
    are not updated.

    To ensure that venv is not recreated on second tox run we
    create a marker file before in the venv folder. If venv is not
    recreated, directory is not removed and maker file stays in it.

    """
    # given
    tmpdir = tmpdir.strpath
    path = lambda *args: os.path.join(tmpdir, *args)
    update_file(
        path('tox.ini'),
        textwrap.dedent('''
        [tox]
        skipsdist=True

        [testenv:python]
        deps = -rreq1/requirements.txt
        commands = {posargs}
    '''))
    update_file(
        path('req1/requirements.txt'),
        textwrap.dedent('''
        pytest-xdist==1.13.0
        pep8
    '''))
    run('tox -e python -- python -V'.split(), tmpdir)
    marker_fpath = path('.tox/python/marker.file')
    update_file(marker_fpath, '')

    # excercise
    # nothing chnaged in the file
    run('tox -e python -- python -V'.split(), tmpdir)

    # verify that marker file exists as we didn't recreate environment
    assert os.path.isfile(marker_fpath)


def test_venv_recreated_on_requirements_file_update(tmpdir):
    """Ensure environment recreated on requirements file changed."""
    # given
    tmpdir = tmpdir.strpath
    path = lambda *args: os.path.join(tmpdir, *args)
    update_file(
        path('tox.ini'),
        textwrap.dedent('''
        [tox]
        skipsdist=True

        [testenv]
        deps = -rreq1/requirements.txt
        commands = {posargs}
    '''))
    update_file(path('req1/requirements.txt'), 'pytest-xdist==1.13.0\n')

    # excercise
    run('tox -- python -V'.split(), tmpdir)
    assert_package_intalled(tmpdir, package='pytest-xdist', version='1.13')
    update_file(path('req1/requirements.txt'), 'pytest-xdist==1.13.1\n')
    run('tox -- python -V'.split(), tmpdir)

    # verify
    assert_package_intalled(tmpdir, package='pytest-xdist', version='1.13.1')


def test_venv_recreated_on_nested_requirements_file_update(tmpdir):
    """Ensures a change in nested requirements recreates the venvs."""
    # given
    tmpdir = tmpdir.strpath
    path = lambda *args: os.path.join(tmpdir, *args)
    update_file(
        path('tox.ini'),
        textwrap.dedent('''
        [tox]
        skipsdist=True

        [testenv]
        deps = -rreq1/requirements.txt
        commands = {posargs}
    '''))
    update_file(path('req1/requirements.txt'), '-r requirements/base.txt\n')
    update_file(path('req1/requirements/base.txt'), 'pytest-xdist==1.13.0\n')

    # excercise
    run('tox -- python -V'.split(), tmpdir)
    assert_package_intalled(tmpdir, package='pytest-xdist', version='1.13')
    update_file(path('req1/requirements/base.txt'), 'pytest-xdist==1.13.1\n')
    run('tox -- python -V'.split(), tmpdir)

    # verify
    assert_package_intalled(tmpdir, package='pytest-xdist', version='1.13.1')


def test_venv_not_recreated_when_nested_requirements_file_do_not_change(tmpdir):
    """Ensures the venvs do not get recreated when nothing changes in the nested rquirements files."""
    # given
    tmpdir = tmpdir.strpath
    path = lambda *args: os.path.join(tmpdir, *args)
    update_file(
        path('tox.ini'),
        textwrap.dedent('''
        [tox]
        skipsdist=True

        [testenv]
        deps = -rreq1/requirements.txt
        commands = {posargs}
    '''))
    update_file(path('req1/requirements.txt'), '-r requirements/base.txt\n')
    update_file(path('req1/requirements/base.txt'), 'pytest-xdist==1.13.1\n')

    # excercise
    run('tox -- python -V'.split(), tmpdir)
    assert_package_intalled(tmpdir, package='pytest-xdist', version='1.13')
    update_file(path('req1/requirements/base.txt'), 'pytest-xdist==1.13.1\n')
    run('tox -- python -V'.split(), tmpdir)

    # verify
    assert_package_intalled(tmpdir, package='pytest-xdist', version='1.13.1')


def assert_package_intalled(toxini_dir, package, version):
    _, output, _ = run('tox -- pip freeze'.split(), toxini_dir, capture_output=True)
    expected_line = "{0}=={1}".format(package, version)
    assert expected_line in output


def run(cmd, working_dir, ok_return_codes=(0, ), capture_output=False):
    p = subprocess.Popen(
        cmd,
        cwd=working_dir,
        stdout=capture_output and subprocess.PIPE or None,
        stderr=capture_output and subprocess.PIPE or None)
    (stdout, stderr) = p.communicate()
    if not capture_output:
        stdout, stderr = '', ''

    if p.returncode not in ok_return_codes:
        raise Exception("Failed to execute {0!r} with return code {1}:\n {2}"
                        .format(cmd, p.returncode, stdout + stderr))
    return p.returncode, str(stdout), str(stderr)


def update_file(fpath, content):
    fdir = os.path.dirname(fpath)
    if fdir and not os.path.isdir(fdir):
        os.makedirs(fdir)
    with open(fpath, 'w') as fd:
        fd.write(content)
