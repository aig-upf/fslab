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

"""
A module for running FS experiments.
"""

import logging
import os.path

from downward.experiment import FastDownwardRun, FastDownwardExperiment, _DownwardAlgorithm
from lab.experiment import Run
from lab import tools

from .cached_revision import FSCachedRevision

DIR = os.path.dirname(os.path.abspath(__file__))
DOWNWARD_SCRIPTS_DIR = os.path.join(DIR, 'scripts')


class FSRun(FastDownwardRun):
    def __init__(self, exp, algo, task):
        # Note: We surpass the FastDownwardRun constructor to avoid adding the
        # Fast Downward planner command and adding ours instead
        Run.__init__(self, exp)
        self.algo = algo
        self.task = task

        self._set_properties()

        # Linking to instead of copying the PDDL files makes building
        # the experiment twice as fast.
        self.add_resource(
            'domain', self.task.domain_file, 'domain.pddl', symlink=True)
        self.add_resource(
            'problem', self.task.problem_file, 'problem.pddl', symlink=True)

        # TODO Note that we just pass '.' as the output directory, since the command
        # TODO will be executed from the run directory. Perhaps cleaner options are available
        # TODO that don't mix the workspace with other important LAB files?
        self.add_command(
            'fs',
            ['{' + algo.cached_revision.get_planner_resource_name() + '}'] +
            algo.driver_options + ['--domain', '{domain}', '--instance', '{problem}', '--output', '.']
            + algo.component_options,
            time_limit=exp.time_limit,
            memory_limit=exp.memory_limit,
        )


class FSExperiment(FastDownwardExperiment):
    """Conduct a FS experiment. See documentation
    FastDownwardExperiment class.
    """
    DEFAULT_SEARCH_TIME_LIMIT = 30*60  # in seconds
    DEFAULT_SEARCH_MEMORY_LIMIT = 8*1024  # in MB

    def __init__(self, path=None, environment=None, revision_cache=None, time_limit=None, memory_limit=None):
        """  """
        super().__init__(path, environment, revision_cache)
        self.time_limit = time_limit if time_limit is not None else self.DEFAULT_SEARCH_TIME_LIMIT
        self.memory_limit = memory_limit if memory_limit is not None else self.DEFAULT_SEARCH_MEMORY_LIMIT

    def add_algorithm(self, name, repo, rev, component_options,
                      build_options=None, driver_options=None):
        """ See documentation in FastDownwardExperiment.add_algorithm() """
        if not isinstance(name, tools.string_type):
            logging.critical('Algorithm name must be a string: {}'.format(name))
        if name in self._algorithms:
            logging.critical('Algorithm names must be unique: {}'.format(name))
        build_options = self._get_default_build_options() + (build_options or [])
        driver_options = ([] + (driver_options or []))  # No default options for the moment
        algorithm = _DownwardAlgorithm(
            name, FSCachedRevision(repo, rev, build_options),
            driver_options, component_options)
        for algo in self._algorithms.values():
            if algorithm == algo:
                logging.critical(
                    'Algorithms {algo.name} and {algorithm.name} are '
                    'identical.'.format(**locals()))
        self._algorithms[name] = algorithm

    def _add_code(self):
        """Add the compiled code to the experiment."""
        for cached_rev in self._get_unique_cached_revisions():
            self.add_resource(
                '',
                cached_rev.get_cached_path(),
                cached_rev.get_exp_path())
            # Overwrite the script to set an environment variable.
            self.add_resource(
                cached_rev.get_planner_resource_name(),
                cached_rev.get_cached_path('run.py'),
                cached_rev.get_exp_path('run.py'))

    def _add_runs(self):
        for algo in self._algorithms.values():
            for task in self._get_tasks():
                self.add_run(FSRun(self, algo, task))

    def _get_default_build_options(self):
        return ['-p']
