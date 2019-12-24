# -*- coding: utf-8 -*-
#
# Downward Lab uses the Lab package to conduct experiments with the
# Fast Downward planning system.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path

from downward.cached_revision import *
from lab import tools


def _get_options_relevant_for_cache_name(options):
    """
    Remove "-j", "-j4" and "-j 4" options.

    These options do not influence the result of the build and a build
    shouldn't be done again just because we build with a different
    number of jobs.

    This behaviour is important on the grid, where the compute and the
    job submission nodes have different numbers of cores. If we made
    these options part of the directory name, lab would try to
    recompile the planner on a compute node, which is undesirable.
    """
    relevant_options = options[:]
    for index, option in enumerate(relevant_options):
        if option and option.startswith('-j'):
            jobs = option[2:]
            if not jobs or jobs.isdigit():
                relevant_options[index] = None
            if not jobs and len(relevant_options) > index + 1:
                next_option = relevant_options[index + 1]
                if next_option.isdigit():
                    relevant_options[index + 1] = None
    return [x for x in relevant_options if x is not None]


def _compute_md5_hash(mylist):
    m = hashlib.md5()
    for s in mylist:
        m.update(tools.get_bytes(s))
    return m.hexdigest()[:8]


class FSCachedRevision(CachedRevision):
    """This class represents checkouts for the FS planner.

    It provides methods for caching and compiling given revisions.
    """
    def __init__(self, repo, local_rev, build_options):
        """
        * *repo*: Path to the FS planner repository.
        * *local_rev*: The desired (Git) revision.
        * *build_options*: List of build.py options.
        """
        if not os.path.isdir(repo):
            logging.critical('{} is not a Git repository.'.format(repo))
        super().__init__(repo, local_rev, build_options)

    def _compute_hashed_name(self):
        relevant_options = _get_options_relevant_for_cache_name(self.build_options)
        if relevant_options:
            return '{}_{}'.format(self.global_rev, _compute_md5_hash(relevant_options))
        else:
            return self.global_rev

    def cache(self, revision_cache):
        self._path = os.path.join(revision_cache, self._hashed_name)
        if os.path.exists(self.path):
            logging.info('Revision is already cached: "%s"' % self.path)
            if not os.path.exists(self._get_sentinel_file()):
                logging.critical(
                    'The build for the cached revision at {} is corrupted '
                    'or was made with an older Lab version. Please delete '
                    'it and try again.'.format(self.path))
        else:
            tools.makedirs(self.path)

            if not os.path.exists(os.path.join(self.repo, 'export.sh')):
                logging.critical('export.sh script not found. Make sure you\'re using a recent version of the planner.')
            # First export the main repo
            script = os.path.join(self.repo, "export.sh")
            retcode = tools.run_command((script, self.global_rev, self.path),
                                        cwd=self.repo)

            if retcode != 0:
                shutil.rmtree(self.path)
                logging.critical('Failed to make checkout.')
            self._compile()
            self._cleanup()

    def get_planner_resource_name(self):
        return 'fs_' + self._hashed_name

    def _cleanup(self):
        # Remove unneeded files.
        tools.remove_path(self.get_cached_path('.build'))
        tools.remove_path(self.get_cached_path('build'))
        tools.remove_path(self.get_cached_path('vendor'))

        # Strip binaries.
        binaries = []
        for path in glob.glob(os.path.join(self.path, "*.bin")):
            binaries.append(path)
        subprocess.call(['strip'] + binaries)

        # Compress src directory.
        subprocess.call(
            ['tar', '-cf', 'src.tar', '--remove-files', 'src', 'submodules'],
            cwd=self.path)
        subprocess.call(['xz', 'src.tar'], cwd=self.path)