""" Contains the submitter function, which is used by JobManager to run new containers """

import json
import os.path

import docker


def submitter(jobid, inputdata, task_directory, limits, environment, docker_config, output_queue):
    """
        Runs a new job.

        Arguments:

        *jobid*
            the jobid.
        *inputdata*
            the input data, as a dictionnary of problemid:problem_answer pairs.
        *task_directory*
            the directory containing the data of the task to run
        *limits*
            the dictionary containing the task's limit
        *environment*
            the image to run the task in
        *docker_config*
            docker configuration, as a dict. See the JobManager class.
        *output_queue*
            queue of a Waiter. Will send a tuple (jobid, containerid).
            If an error happens, containerid will be None.

    """
    try:
        print "Start creating container for jobid {}".format(jobid)
        docker_connection = docker.Client(base_url=docker_config.get('server_url'))
        mem_limit = limits.get("memory", 100)
        if mem_limit < 20:
            mem_limit = 20
        elif mem_limit > 500:
            mem_limit = 500

        response = docker_connection.create_container(
            docker_config.get("container_prefix", "inginious/") + environment,
            stdin_open=True,
            network_disabled=True,
            volumes={'/ro/task': {}},
            mem_limit=mem_limit * 1024 * 1024
        )
        container_id = response["Id"]

        # Start the container
        docker_connection.start(container_id, binds={os.path.abspath(task_directory): {'ro': True, 'bind': '/ro/task'}})

        # Send the input data
        container_input = {"input": inputdata, "limits": limits}
        docker_connection.attach_socket(container_id, {'stdin': 1, 'stream': 1}).send(json.dumps(container_input) + "\n")

        output_queue.put((jobid, container_id))
        print "Container for jobid {} started: {}".format(jobid, container_id)
    except:
        print "Container for jobid {} failed to start".format(jobid)
        output_queue.put((jobid, None))