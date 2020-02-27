
from setuptools import setup, find_packages
from codecs import open
from os import path
import importlib

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


# Load the version from ./src/tarski/version.py
spec = importlib.util.spec_from_file_location('tsk.version', path.join(here, 'src/fslab/version.py'))
version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version)


def main():

    setup(
        name='fslab',
        version=version.__version__,
        description='A plugin for Jendrik Seipp\'s Lab to run experiments for the FS planner',
        long_description=long_description,
        long_description_content_type='text/markdown',

        url='https://github.com/aig-upf/fslab',
        author='Guillem Francès',
        author_email='guillem.frances@upf.edu',

        keywords='planning experiments',
        classifiers=[
            'Development Status :: 3 - Alpha',

            'Intended Audience :: Science/Research',
            'Intended Audience :: Developers',

            'Topic :: Scientific/Engineering :: Artificial Intelligence',

            'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
        ],

        packages=find_packages('src'),  # include all packages under src
        package_dir={'': 'src'},  # tell distutils packages are under src


        install_requires=[
            'lab>=5.3',
        ],

        extras_require={
            'dev': ['pytest', 'tox', 'pytest-cov', 'mypy'],
            'test': ['pytest', 'tox', 'pytest-cov', 'mypy'],
        },

        # This will include non-code files specified in the manifest, see e.g.
        # http://python-packaging.readthedocs.io/en/latest/non-code-files.html
        include_package_data=True,
    )


if __name__ == '__main__':
    main()
