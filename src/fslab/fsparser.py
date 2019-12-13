#! /usr/bin/env python
"""
Regular expressions and methods for parsing the output of FS experiments.
"""

from __future__ import division

import re


from lab.parser import Parser


def solved(run):
    return run['coverage'] or run['unsolvable']


# This would be ideal, but ATM the planner is very unreliable with exit codes
# def coverage(content, props):
#     props['coverage'] = int(props['planner_exit_code'] == 0)


def parse_node_generation_rate(content, props):
    # We do a first parse of the online-printed generation rate, in case it exists,
    # but will overwrite this later if we found the final value in the JSON output.
    # [INFO][454.35526] Node generation rate after 5950K generations (nodes/sec.): 13281.5. Memory consumption: 7730092kB. / 7806784 kB.
    allrates = re.findall(r'Node generation rate after (\d+)K generations \(nodes/sec\.\): (.+). Memory consumption: (\d+)kB\.', content)
    props['node_generation_rate'] = float(allrates[-1][0]) if allrates else 0
    props['memory'] = float(allrates[-1][2]) if allrates else 0
    props['last_recorded_generations'] = int(allrates[-1][1]) if allrates else 0


def parse_memory_time_watchpoints(content, props):
    res = re.findall(r'Mem\. usage before match-tree construction: (\d+)kB\. /', content)
    props['mem_before_mt'] = int(res[-1]) if res else 0

    res = re.findall(r'Mem\. usage on start of SBFWS search: (\d+)kB\. /', content)
    props['mem_before_search'] = int(res[-1]) if res else 0

    allrates = re.findall(r'\[INFO\]\[(\d+\.\d+)\]', content)
    props['last_recorded_time'] = float(allrates[-1]) if allrates else 0


def parse_grounding_info(content, props):
    res = re.findall(r'Parsing and simplifying the problem with the ASP-based parser: \[(\d+\.\d+)s CPU, .+ wall-clock, diff: (\d+\.\d+)MB, .+\]', content)
    props['asp_prep_time'] = float(res[-1][0]) if res else 0
    props['asp_prep_mem'] = float(res[-1][1]) if res else 0

    res = re.findall(r'Successor Generator: (.+)\n', content)
    props['successor_generator'] = res[-1] if res else 'unknown'

    res = re.findall(r'Loaded a total of (\d+) reachable ground actions', content)
    props['num_reach_actions'] = int(res[-1]) if res else 0


def parse_sdd_minimization(content, props):
    # SDD minimization: 132 -> 101 nodes (30% reduction)
    allsizes = re.findall(r'SDD minimization: .+ -> ([0-9]+) nodes', content)
    props['sdd_sizes'] = sum(int(x) for x in allsizes) if allsizes else -1

    # Building SDD for 8 variables and 11 constraints
    thsizes = re.findall(r'Building SDD for ([0-9]+) variables and ([0-9]+) constraints', content)
    props['sdd_theory_vars'] = sum(int(x[0]) for x in thsizes) if allsizes else -1
    props['sdd_theory_constraints'] = sum(int(x[1]) for x in thsizes) if allsizes else -1


def parse_results(content, props):
    # TODO planner_exit_code is still not too reliable
    props['error'] = 'all-good' if 'planner_exit_code' not in props or props['planner_exit_code'] == 0\
        else 'unsolvable-or-error'

    props['coverage'] = 0  # Unless proven otherwise, the instance is assumed not solved

    if props['error'] != 'all-good':
        return

    if not content:
        props['error'] = 'json-output-is-empty'
        return

    try:
        import json
        out = json.loads(content)
    except Exception as e:
        props['error'] = 'json-output-parse-error'
        props['json-output-parse-error'] = str(e)
        return

    # If we reach this point, we can assume the json results file contains all attributes

    # Check if there was an OOM error
    props['out_of_memory'] = bool(out['out_of_memory'])
    if props['out_of_memory']:
        props['error'] = 'out-of-memory'
        return

    # Check if the plan was flagged as invalid
    props['invalid-plan'] = not bool(out['valid'])
    if props['invalid-plan']:
        props['error'] = 'invalid-plan'
        return

    props['coverage'] = int(out['solved'])  # i.e. either 1 or 0
    props['unsolvable'] = props['coverage'] == 0 and not props['out_of_memory']

    if solved(props):
        if 'memory' in out:
            props['memory'] = out['memory']  # Override previous temporary measurements
        props['search_time'] = out['search_time']
        props['total_time'] = out['total_time']
        props['plan_length'] = int(out['plan_length'])
        props['expansions'] = out['expanded']
        props['generations'] = out['generated']
        props['evaluations'] = out['evaluated']
        props['plan'] = ', '.join(out['plan'])
        props['node_generation_rate'] = out['gen_per_second']


def check_min_values(content, props):
    """
    Ensure that times are not 0 if they are present in log.
    """
    for attr in ['search_time', 'total_time']:
        time = props.get(attr, None)
        if time is not None:
            props[attr] = max(time, 0.01)


class FSOutputParser(Parser):
    def __init__(self):
        Parser.__init__(self)

        self.add_pattern('node', r'node: (.+)\n', type=str, file='driver.log', required=True)
        self.add_pattern('planner_exit_code', r'run-planner exit code: (.+)\n', type=int, file='driver.log')

        self.add_function(parse_memory_time_watchpoints, file="run.log")
        self.add_function(parse_grounding_info, file="run.log")
        self.add_function(parse_node_generation_rate, file="run.log")
        self.add_function(parse_sdd_minimization, file="run.log")

        self.add_function(parse_results, file="results.json")
        self.add_function(check_min_values, file="results.json")

        # Note We might want to parse problem stats as well
        # self.add_function(parse_problem_stats, file="problem_stats.json")


FSOutputParser().parse()


