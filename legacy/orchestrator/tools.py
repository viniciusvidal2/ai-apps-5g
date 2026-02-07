import subprocess


def kill_all_processes(agents: dict) -> None:
    """Kills all the agents that can be running from old processes.

    Args:
        agents (dict): Dictionary containing agent configurations with their docker commands.
    """
    for agent in agents.values():
        subprocess.run(agent["docker_stop_command"],
                       shell=True, check=False)


def launch_agents_from_workflow(workflow: dict, agents: dict) -> None:
    """Launch the necessary agents based on the input workflow for the assistant

    Args:
        workflow (dict): The workflow configuration containing agent and topic information.
        agents (dict): The available agents with their Docker run commands.
    """
    necessary_agents = workflow["agents"]
    input_topics = workflow["input_topics"]
    output_topics = workflow["output_topics"]
    # Call each agent docker to start
    for agent_name, input_topic, output_topic in zip(necessary_agents, input_topics, output_topics):
        docker_run_command = agents[agent_name]["docker_run_command"]
        docker_run_command += f" --input_topic {input_topic} --output_topic {output_topic}"
        subprocess.Popen(docker_run_command, shell=True)
