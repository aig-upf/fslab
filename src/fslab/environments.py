
import os

from lab.environments import SlurmEnvironment


class UPFSlurmEnvironment(SlurmEnvironment):
    """ Environment for UPF HPC Cluster. """

    DEFAULT_SETUP = (
        '# The following directives will trigger the load of the appropriate GCC and Python versions\n'
        'module purge\n'
        'LMOD_DISABLE_SAME_NAME_AUTOSWAP=no module load Boost/1.65.1-foss-2017a-Python-3.6.4\n'
        'LMOD_DISABLE_SAME_NAME_AUTOSWAP=no module load SCons/3.0.1-foss-2017a-Python-3.6.4\n'
    )

    DEFAULT_PARTITION = 'short'
    DEFAULT_QOS = 'normal'
    # infai_1 nodes have 61964 MiB and 16 cores => 3872.75 MiB per core
    DEFAULT_MEMORY_PER_CPU = '7950M'  # see http://issues.fast-downward.org/issue733 for a discussion on this

    def __init__(self, time_limit=None, **kwargs):
        # Add some extra options that we want by default in the UPF cluster experiments
        default_extras = ['### Force the broadwell architecture\n#SBATCH --constraint="bdw"']
        if time_limit is not None:
            # From https://slurm.schedmd.com/sbatch.html:
            # A time limit of zero requests that no time limit be imposed. Acceptable time formats include "minutes",
            # "minutes:seconds", "hours:minutes:seconds", "days-hours", "days-hours:minutes" and
            # "days-hours:minutes:seconds".
            default_extras.append('### Max. CPU time\n#SBATCH --time={}'.format(time_limit))

        kwargs['extra_options'] = kwargs.get('extra_options', '\n'.join(default_extras))

        super().__init__(**kwargs)


# A hack to force the sourcing of the virtual environment the script has been invoked from
# upon execution of the SBATCH script
venv = os.getenv('VIRTUAL_ENV', None)
if venv is not None:
    UPFSlurmEnvironment.DEFAULT_SETUP += 'source {}/bin/activate\n'.format(venv)
