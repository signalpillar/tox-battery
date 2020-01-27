# std
import glob
import os
import shlex
import subprocess
import textwrap

# local
from toxbat import requirements

# 3rd-party
import pytest


def test_is_changed_fails_on_missing_req_file():
    with pytest.raises(ValueError):
        requirements.is_changed('nonexisting/requirements.txt', 'nonexisting/requirements.txt')


@pytest.fixture(scope='function')
def in_project(tmpdir):
    """ Provide a function to calculate path in a temporary project.
    """
    def build_path(*args):
        return os.path.join(tmpdir.strpath, *args)
    yield build_path


@pytest.fixture(scope='function')
def cwd(in_project):
    """ Provide CWD path for the temporary project (root of the project).
    """
    yield in_project('.')


def test_venv_reused_for_different_testenvironments(in_project, cwd):
    """ Ensure venv reused by multiple test-environments without recreation.

    Declared test environments in tox.ini file can be run same virtual
    environment if they share same dependencies.

    In this test we need to check that environment (same) is not recreated each
    time because it is used by multiple test environments.

    In this test we have a 'test-requirements.txt' file that declares flake8
    and pytest and tox declares 2 test environments that reuse same
    dependencies.

    Normally tox creates a separate virtual environment for each test-env but
    in our case 'envdir' is set to fix the path and reuse environment::

        envdir = {toxworkdir}/env
    """
    # given
    update_file(
        in_project('tox.ini'),
        textwrap.dedent('''
        [tox]
        envlist = flake8, unit
        skipsdist = True

        [testenv]
        envdir = {toxworkdir}/env
        deps =
            -rrequirements-test.txt
        commands =
            pip --version
            flake8,test: flake8 --version
            unit,test: pytest --version
    '''))
    update_file(
        in_project('requirements-test.txt'),
        textwrap.dedent('''
        pytest
        flake8
    '''))

    # exercise
    _, stdout, stderr = run('tox', cwd, capture_output=True)
    print(stdout)

    # verify
    assert 'unit recreate:' not in stdout,\
        (
            "Found in command output that 'unit' test environment is "
            "recreated while it is expected to reuse existing "
            "'{toxworkdir}/env' virtual environment."
        )


def test_requirements_are_parsed(in_project, cwd):
    """ Environment is not recreated on any file change.

    As requirements file is parsed by pip library and tox-battery operates with
    parsed content and not text - reshuffling of the lines and adding comments
    doesn't cause of rebuilding the venvs.

    To ensure that venv is not recreated on second tox run we create a marker
    file before in the venv folder. If venv is not recreated, directory is not
    removed and maker file stays in it.
    """
    # given
    update_file(
        in_project('tox.ini'),
        textwrap.dedent('''
        [tox]
        skipsdist=True

        [testenv:python]
        deps = -rreq1/requirements.txt
        commands = {posargs}
    '''))
    update_file(
        in_project('req1/requirements.txt'),
        textwrap.dedent('''
        pytest-xdist==1.13.0
        pep8
    '''))
    run('tox -e python -- python -V', cwd)
    marker_fpath = in_project('.tox/python/marker.file')
    update_file(marker_fpath, '')

    # exercise
    # change order of dependencies
    update_file(
        in_project('req1/requirements.txt'),
        textwrap.dedent('''
        pep8
        pytest-xdist==1.13.0
        # ^ dependency for testing
    '''))
    run('tox -e python -- python -V', cwd)

    # verify
    previous_state_hash_file = in_project(
        '.tox/req1-requirements.txt.*.previous')
    matched = glob.glob(previous_state_hash_file)
    assert matched, "Previous version file is not found."
    # Ensure file with current requirements saved as a hash.
    expected_reqscontent_sum = 'eb30f761445bda7ca0fe06400a686a31ade734d1'
    assert expected_reqscontent_sum == read_text_file(matched[0])


def test_venv_recreated_on_requirements_file_update(in_project, cwd):
    """Ensure environment recreated on requirements file changed.
    """
    # given
    update_file(
        in_project('tox.ini'),
        textwrap.dedent('''
        [tox]
        skipsdist=True

        [testenv]
        deps = -rreq1/requirements.txt
        commands = {posargs}
    '''))
    update_file(in_project('req1/requirements.txt'), 'pytest-xdist==1.13.0\n')

    # exercise
    run('tox -- python -V', cwd)
    assert_package_intalled(cwd, package='pytest-xdist', version='1.13')
    update_file(in_project('req1/requirements.txt'), 'pytest-xdist==1.13.1\n')
    run('tox -- python -V', cwd)

    # verify
    assert_package_intalled(cwd, package='pytest-xdist', version='1.13.1')


def test_venv_recreated_on_nested_requirements_file_update(in_project, cwd):
    """Ensures a change in nested requirements recreates the venvs.
    """
    # given
    update_file(
        in_project('tox.ini'),
        textwrap.dedent('''
        [tox]
        skipsdist=True

        [testenv]
        deps = -rreq1/requirements.txt
        commands = {posargs}
    '''))
    update_file(in_project('req1/requirements.txt'), '-r requirements/base.txt\n')
    update_file(in_project('req1/requirements/base.txt'), 'pytest-xdist==1.13.0\n')

    # exercise
    run('tox -- python -V', cwd)
    assert_package_intalled(cwd, package='pytest-xdist', version='1.13')
    update_file(in_project('req1/requirements/base.txt'), 'pytest-xdist==1.13.1\n')
    run('tox -- python -V', cwd)

    # verify
    assert_package_intalled(cwd, package='pytest-xdist', version='1.13.1')


def test_venv_not_recreated_when_nested_requirements_file_do_not_change(in_project, cwd):
    """Ensures the venvs do not get recreated when nothing changes in the nested rquirements files.
    """
    # given
    update_file(
        in_project('tox.ini'),
        textwrap.dedent('''
        [tox]
        skipsdist=True

        [testenv]
        deps = -rreq1/requirements.txt
        commands = {posargs}
    '''))
    update_file(in_project('req1/requirements.txt'), '-r requirements/base.txt\n')
    update_file(in_project('req1/requirements/base.txt'), 'pytest-xdist==1.13.1\n')

    # exercise
    run('tox -- python -V', cwd)
    assert_package_intalled(cwd, package='pytest-xdist', version='1.13')
    update_file(in_project('req1/requirements/base.txt'), 'pytest-xdist==1.13.1\n')
    run('tox -- python -V', cwd)

    # verify
    assert_package_intalled(cwd, package='pytest-xdist', version='1.13.1')


def test_all_requirements_files_are_hashed(in_project, cwd):
    """ Ensure .previous files are created for all req-files in testenv.

    First run for the testenv should produce hash files for all the requirement
    files specified in the dependencies.
    """
    # given
    update_file(
        in_project('tox.ini'),
        textwrap.dedent('''
        [tox]
        skipsdist=True

        [testenv]
        deps =
            -rreq1/requirements.txt
            -rreq2/requirements.txt
        commands = {posargs}
    '''))
    update_file(in_project('req1/requirements.txt'), 'pep8\n')
    update_file(in_project('req2/requirements.txt'), 'click\n')

    # exercise
    run("tox -- python -V", cwd)

    # verify
    prev_files = glob.glob(in_project('.tox/req*-requirements.txt.*.previous'))
    assert 2 == len(prev_files), prev_files


def assert_package_intalled(toxini_dir, package, version):
    _, output, _ = run('tox -- pip freeze', toxini_dir, capture_output=True)
    expected_line = "{0}=={1}".format(package, version)
    assert expected_line in output


def run(cmd, working_dir, ok_return_codes=(0, ), capture_output=False):
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
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


def read_text_file(fpath):
    with open(fpath, 'r') as fd:
        return fd.read()
