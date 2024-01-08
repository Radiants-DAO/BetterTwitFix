# radTwitter Docker

## Configuration

Setup mongodb in `config.json`:
```json
{
    "config":{
        "link_cache":"db",
        "database":"mongodb://twitfix_db:27017/",
        [...]
    },
    [...]
}
```

Use TCP socket for uwsgi `twitfix.ini`:
```ini
[uwsgi]
module = wsgi:app

master = true
processes = 5

socket = 0.0.0.0:9000
buffer-size = 8192
#socket = /var/run/twitfix.sock
#chmod-socket = 660
vacuum = true

die-on-term = true
```

## Run

To run and build, use this command:
```bash
docker-compose up -d --build
```

