# Deadline Web App Backend

This is the Python WebSocket backend for my [Deadline Web App frontend](https://github.com/BreakTools/deadline-web-app-frontend)! You can witness this in action by visiting [my school's monitor](https://monitor.vfxim.nl/).

## Features

This WebSocket backend...

- ...retrieves job information from the Deadline Web Service, stores it in memory and sends the data to clients that request it.
- ...keeps connected clients in the loop by sending them updates whenever job information on the render farm changes.
- ...uses ChatGPT to parse error logs and provides an easy to read summary for artists.
- ...retrieves EXRs from disk and converts them to JPEGs so artists can preview their renders.

**Warning: This backend does not have authentication, so please don't open it to the public if you are dealing with NDAs.**

## Installation instructions (Docker)

1. Make sure you have the Deadline Web Service running on your internal network. You can find the instructions for that [here](https://docs.thinkboxsoftware.com/products/deadline/10.1/1_User%20Manual/manual/web-service.html). Make sure you do NOT open the Deadline Web Service up to the public internet, as that's a big security risk.
2. Pull the image from the GitHub Package registry with:

```
docker pull ghcr.io/breaktools/deadline-web-app-backend
```

3. Run the backend with the following command, replacing the text in {curly brackets} with your own info.

```
docker run -p {port}:80 -e OPENAI_API_KEY="{yourkey}" -e WEB_SERVICE_IP="{webserviceip}" -e WEB_SERVICE_PORT="{webserviceport}" -t ghcr.io/breaktools/deadline-web-app-backend
```

That's it! The backend is now running. You will probably have to do some additional configuration to get the image previews to work properly, such as mounting the folders your farm renders to. I recommend putting this behind something like an NGINX reverse proxy with SSL so you can securely connect to it from your web browser.

## Installation instructions (Standalone)

1. Make sure you have the Deadline Web Service running on your internal network. You can find the instructions for that [here](https://docs.thinkboxsoftware.com/products/deadline/10.1/1_User%20Manual/manual/web-service.html). Make sure you do NOT open the Deadline Web Service up to the public internet, as that's a big security risk.
2. Make sure you have Python 3.10 or higher installed on your computer.
3. Install OpenEXR on your computer. If you're on Linux, run `sudo apt-get install libopenexr-dev` and `sudo apt-get install openexr`. If you're on Mac, use Homebrew: `brew install openexr`. To avoid compiling OpenEXR yourself on Windows, try these commands: `pip install pipwin`, `pipwin install openexr`.
4. Clone this repository and put it in a good spot. CD into the folder and run `pip install -r requirements.txt` to install all required Python packages.
5. Create a .env file in /src and add the following variables: OPENAI_API_KEY, WEB_SERVICE_IP, WEB_SERVICE_PORT.
6. Make sure your computer has access to the files that are rendering on the farm, otherwise the image previews will not work. You're probably good if you're running this on a computer that also renders on the farm.

You might not be able to open a port to this backend if you're running your Deadline Web Service in a tightly controlled network. If that's the case but you do have access to a VPS that you can open ports to, have a look at my [WebSocket proxy scripts](https://github.com/BreakTools/websocket-proxy) to still make this backend work.

That's it! I recommend putting this behind something like an NGINX reverse proxy with SSL so you can securely connect to it from your web browser.
