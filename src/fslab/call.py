# -*- coding: utf-8 -*-
#
# Lab is a Python package for evaluating algorithms.
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

import errno
import logging
import resource
import subprocess
import sys

from lab import tools
from lab.calls.call import Call as Labcall


def set_limit(kind, soft_limit, hard_limit):
    try:
        resource.setrlimit(kind, (soft_limit, hard_limit))
    except (OSError, ValueError) as err:
        logging.error(
            "Resource limit for %s could not be set to %s (%s)"
            % (kind, (soft_limit, hard_limit), err)
        )


class Call(Labcall):
    def __init__(
        self,
        args,
        name,
        time_limit=None,
        memory_limit=None,
        soft_stdout_limit=None,
        hard_stdout_limit=None,
        soft_stderr_limit=None,
        hard_stderr_limit=None,
        **kwargs
    ):
        """Make system calls with time and memory constraints.

        *args* and *kwargs* are passed to `subprocess.Popen
        <http://docs.python.org/library/subprocess.html>`_.

        See also the documentation for
        ``lab.experiment._Buildable.add_command()``.

        """
        assert "stdin" not in kwargs, "redirecting stdin is not supported"
        self.name = name

        if time_limit is None:
            self.wall_clock_time_limit = None
        else:
            # Enforce miminum on wall-clock limit to account for disk latencies.
            self.wall_clock_time_limit = max(30, time_limit * 1.5)

        def get_bytes(limit):
            return None if limit is None else int(limit * 1024)

        # Allow passing filenames instead of file handles.
        self.opened_files = []
        for stream_name in ["stdout", "stderr"]:
            stream = kwargs.get(stream_name)
            if isinstance(stream, tools.string_type):
                file = open(stream, mode="w")
                kwargs[stream_name] = file
                self.opened_files.append(file)

        # Allow redirecting and limiting the output to streams.
        self.redirected_streams_and_limits = {}

        # for stream_name, soft_limit, hard_limit in [
        #     ("stdout", get_bytes(soft_stdout_limit), get_bytes(hard_stdout_limit)),
        #     ("stderr", get_bytes(soft_stderr_limit), get_bytes(hard_stderr_limit)),
        # ]:
        #     stream = kwargs.pop(stream_name, None)
        #     if stream:
        #         self.redirected_streams_and_limits[stream_name] = (
        #             stream,
        #             (soft_limit, hard_limit),
        #         )
        #         kwargs[stream_name] = subprocess.PIPE

        def prepare_call():
            # When the soft time limit is reached, SIGXCPU is emitted. Once we
            # reach the higher hard time limit, SIGKILL is sent. Having some
            # padding between the two limits allows programs to handle SIGXCPU.
            if time_limit is not None:
                set_limit(resource.RLIMIT_CPU, time_limit, time_limit + 5)
            if memory_limit is not None:
                _, hard_mem_limit = resource.getrlimit(resource.RLIMIT_AS)
                # Convert memory from MiB to Bytes.
                set_limit(
                    resource.RLIMIT_AS, memory_limit * 1024 * 1024, hard_mem_limit
                )
            set_limit(resource.RLIMIT_CORE, 0, 0)

        try:
            self.process = subprocess.Popen(args, preexec_fn=prepare_call, **kwargs)
        except OSError as err:
            if err.errno == errno.ENOENT:
                sys.exit(
                    'Error: Call {name} failed. "{path}" not found'.format(
                        path=args[0], **locals()
                    )
                )
            else:
                raise

    def _redirect_streams(self):
        return
