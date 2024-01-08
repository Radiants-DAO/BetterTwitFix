## Hosting

### Ubuntu Linux Server
The following instructions were tested with Ubuntu 22.10, and assumes a stock OS

Edit config.json to fit your setup

First, get everything updated by running `sudo apt-get update`

Verify Python is installed by running `python3 --version` or `python --version`. Versions 3.8, 3.9, and 3.10 are supported (This includes versions like 3.10.7)

Run the following command: `git clone https://github.com/Radiants-DAO/BetterTwitFix`
This will download all the code for radTwitter. Once that is done, you can run `cd BetterTwitFix` to enter the newly downloaded folder. 

Install pip and venv by running the following command: `apt install python3-pip python3-venv`

Create a virtual enviornment for all of BetterTwitFix's dependencies to live in by running `python3 -m venv venv` and then `source venv/bin/activate`

After that completes, install all the requirements for BetterTwitFix by running `pip3 install -r requirements.txt` and then `pip3 install uwsgi`

Test that everything is correct by running `python3 twitfix.py`. If all worked out well you should see a message that says it's running! You're not done yet though! Press CTRL+C to exit out of that for now.

Edit the twitfix.service file. You can use nano for this by running `nano twitfix.service`

Edit the variables under the [Service] secton. User and Group will need to be changed to the user you want to run this under, and WorkingDirectory, Environment, and ExecStart will all need to have `/home/dylan/BetterTwitFix` replaced with the directory you downloaded the code to. After that, you can save & exit the file (`CTRL+X then Y` on nano) and copy it to your system services by running `sudo cp twitfix.service /etc/systemd/system/`

Finally, get everything going by running `systemctl start twitfix` and `systemctl enable twitfix`

this script uses the youtube-dl python module, along with flask, twitter and pymongo, so install those with pip (you can use `pip install -r requirements.txt`) and start the server with `python twitfix.py`

After that, you need to set up an nginx proxy to point towards `/tmp/twitfix.sock`, which isn't covered here.

### Docker Setup
The following instructions were tested with Ubuntu 22.10, and assumes a stock OS

Edit config.json to fit your setup

First, install docker by following these instructions: [Install using the apt repository](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository) 

Run the following command: `git clone https://github.com/Radiants-DAO/BetterTwitFix`
This will download all the code for radTwitter. Once that is done, you can run `cd BetterTwitFix` to enter the newly downloaded folder. 

Remove the following lines in twitfix.ini:
```ini
socket = /var/run/twitfix.sock
chmod-socket = 660
```
and replace with
```ini
socket = 0.0.0.0:9000
buffer-size = 8192
```

Finally, run this command to set up everything through Docker: `docker-compose up -d --build`

### Serverless Setup
This assumes your AWS credentials are set up

Run the following command: `git clone https://github.com/Radiants-DAO/BetterTwitFix`

Enter into that directory and install serverless framework into it by running `npm install -g serverless`

Then run `serverless deploy`

Finally, set up a new API gateway resource to point towards the main Lambda function (should start with radTwitter) 