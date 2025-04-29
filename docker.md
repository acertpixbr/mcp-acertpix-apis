# Using the Dockerfile

This document explains how to use the Dockerfile provided in the `acertpix-api-score` project.

## Prerequisites

- Docker installed on your system. You can download it from [https://www.docker.com/](https://www.docker.com/).

## Building the Image

To build the Docker image, navigate to the root directory of the `acertpix-api-score` project (where the Dockerfile is located) and run the following command:

```bash
docker build -t acertpix-api-score .
```

This command will:

- `docker build`:  The Docker command to build an image from a Dockerfile.
- `-t acertpix-api-score`:  Tags the image with the name `acertpix-api-score`. You can choose any name you like.
- `.`: Specifies the build context as the current directory. Docker will look for the Dockerfile in this directory.

## Running the Container

Once the image is built, you can run a container from it using the following command:

```bash
docker run -i --rm -p 8001:8000 acertpix-api-score
```

This command will:

- `docker run`: The Docker command to run a container from an image.
- `-p 8000:8000`: Maps port 8000 on the host to port 8000 in the container. This allows you to access the application running inside the container from your host machine.  If your application uses a different port, adjust accordingly.
- `acertpix-api-score`: Specifies the image to use for creating the container.

## Running as an MCP Server

To use the `acertpix-api-score` image as an MCP server, you need to add it to your MCP configuration file (e.g., `mcp-config.json` or similar).  The exact location of this file depends on your MCP setup.

Add the following entry to the `mcpServers` section of your configuration file:

```json
"acertpix-api-score": {
  "command": "docker",
  "args": ["run", "-i", "--rm", "-p", "8000:8000", "acertpix-api-score"]
}
```

**Important:** The Dockerfile has been updated to set the `PYTHONPATH` environment variable and include the `requests` dependency. If you encounter issues, ensure you are using the latest version of the Docker image.

This configuration tells MCP to run the `acertpix-api-score` Docker image as an MCP server.

## Accessing the Application (if applicable)

If the `acertpix-api-score` image also provides a web application interface, you might be able to access it in your web browser at `http://localhost:8000`.  However, as an MCP server, its primary function is to provide tools and resources to MCP, not necessarily a web UI.

## Additional Notes

- Make sure the Docker daemon is running before building the image or running the container.
- You can stop the container by pressing `Ctrl+C` in the terminal where you ran the `docker run` command.
- To remove the container, use the command `docker stop <container_id>` followed by `docker rm <container_id>`. You can find the container ID using `docker ps -a`.
- To remove the image, use the command `docker rmi acertpix-api-score`.
