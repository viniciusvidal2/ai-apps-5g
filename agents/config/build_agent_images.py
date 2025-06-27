import yaml
import subprocess


def load_agents_config(path: str) -> dict:
    """Load the agents configuration from a YAML file.

    Args:
        path (str): The path to the YAML configuration file.

    Returns:
        dict: The loaded configuration as a dictionary.
    """
    with open(path, 'r') as file:
        return yaml.safe_load(file)


def build_agent_images(agents_config: dict) -> None:
    """Build Docker images for each agent defined in the configuration.

    Args:
        agents_config (dict): The configuration dictionary containing agent definitions.
    """
    agents = agents_config.get('agents', [])
    for agent in agents.values():
        name = agent['name']
        dockerfile_path = agent['dockerfile_path']
        # Determine the build context (directory of the Dockerfile)
        context_dir = '.'
        print(f"Building Docker image for {name}...")
        cmd = [
            'docker', 'build',
            '--file', dockerfile_path,
            '-t', name,
            context_dir
        ]
        try:
            subprocess.run(cmd, check=True)
            print(f"Successfully built image: {name}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to build image for {name}: {e}")


if __name__ == "__main__":
    print("Loading agents configuration...")
    config = load_agents_config(path='agents/config/agents_config.yaml')
    print("Building agent images...")
    build_agent_images(agents_config=config)
    print("All agent images built successfully.")
    print("You can now run the agents using their respective Docker images.")
