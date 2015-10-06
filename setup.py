import os
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()


def default_config(cmd_sub):
    """
    Install command decorator for setting up required default configuration.
    It modifies the run() method so that it persists an updated configuration.
    """
    orig_run = cmd_sub.run

    def mod_run(self):
        try:
            from score.cli import config
        except ImportError:
            pass
        else:
            print('setting up default configuration')
            from score.varnish import defaults
            conf = config()
            for k, v in defaults.items():
                if k not in conf['score.varnish']:
                    if isinstance(v, str):
                        conf['score.varnish'][k] = v
            conf.persist()
        orig_run(self)

    cmd_sub.run = mod_run
    return cmd_sub


@default_config
class DefaultConfigInstall(install):
    pass


@default_config
class DefaultConfigDevelop(develop):
    pass

setup(
    name='score.varnish',
    version='0.1.4',
    description='Varnish management for The SCORE Framework',
    long_description=README,
    author='strg.at',
    author_email='score@strg.at',
    url='http://score-framework.org',
    keywords='score framework web svg icons',
    packages=['score.varnish'],
    namespace_packages=['score'],
    zip_safe=False,
    license='LGPL',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Framework :: Pyramid',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General '
            'Public License v3 or later (LGPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
    include_package_data=True,
    entry_points={
        'score.cli': [
            'varnish = score.varnish.cli:main',
        ]
    },
    install_requires=[
        'score.init',
    ],
    cmdclass={
        'install': DefaultConfigInstall,
        'develop': DefaultConfigDevelop
    }
)
