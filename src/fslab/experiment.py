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


RUN_TPL = """#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import platform

from fslab.call import Call
from lab import tools

tools.configure_logging()

logging.info('node: {}'.format(platform.node()))

run_log = open('run.log', 'w')
run_err = open('run.err', 'w', buffering=1)  # line buffering
redirects = {'stdout': run_log, 'stderr': run_err}

# Make sure we're in the run directory.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

%(calls)s

for f in [run_log, run_err]:
    f.close()
    if os.path.getsize(f.name) == 0:
        os.remove(f.name)
"""


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
            'planner',
            ['{' + algo.cached_revision.get_planner_resource_name() + '}'] +
            algo.driver_options + ['--domain', '{domain}', '--instance', '{problem}', '--output', '.']
            + algo.component_options,
            time_limit=exp.time_limit,
            memory_limit=exp.memory_limit,
        )

    def _build_run_script(self):
        if not self.commands:
            logging.critical("Please add at least one command")

        exp_vars = self.experiment._env_vars
        run_vars = self._env_vars
        doubly_used_vars = set(exp_vars) & set(run_vars)
        if doubly_used_vars:
            logging.critical(
                "Resource names cannot be shared between experiments "
                "and runs, they must be unique: {}".format(doubly_used_vars)
            )
        env_vars = exp_vars
        env_vars.update(run_vars)
        env_vars = self._prepare_env_vars(env_vars)

        def make_call(name, cmd, kwargs):
            kwargs["name"] = name

            # Support running globally installed binaries.
            def format_arg(arg):
                if isinstance(arg, tools.string_type):
                    try:
                        return repr(arg.format(**env_vars))
                    except KeyError as err:
                        logging.critical("Resource {} is undefined.".format(err))
                else:
                    return repr(str(arg))

            def format_key_value_pair(key, val):
                if isinstance(val, tools.string_type):
                    formatted_value = format_arg(val)
                else:
                    formatted_value = repr(val)
                return "{}={}".format(key, formatted_value)

            cmd_string = "[{}]".format(", ".join([format_arg(arg) for arg in cmd]))
            kwargs_string = ", ".join(
                format_key_value_pair(key, value)
                for key, value in sorted(kwargs.items())
            )
            parts = [cmd_string]
            if kwargs_string:
                parts.append(kwargs_string)
            return "Call({}, **redirects).wait()\n".format(", ".join(parts))

        calls_text = "\n".join(
            make_call(name, cmd, kwargs)
            for name, (cmd, kwargs) in self.commands.items()
        )
        # run_script = tools.fill_template("run.py", calls=calls_text)
        run_script = RUN_TPL % dict(calls=calls_text)

        self.add_new_file("", "run", run_script, permissions=0o755)


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
