import setuptools


def content_of(fpath):
    with open(fpath, 'r') as fd:
        return fd.read()


setuptools.setup(
    name='tox-battery',
    description='Additional functionality for tox',
    long_description=content_of("README.rst"),
    license='http://opensource.org/licenses/MIT',
    version='0.3',
    author='Volodymyr Vitvitskyi',
    author_email='contact.volodymyr@gmail.com',
    url='https://github.com/signalpillar/tox-battery',
    packages=setuptools.find_packages(),
    entry_points={'tox': [
        'toxbat-requirements = toxbat.requirements',
    ]},
    install_requires=['tox'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3'],
)
