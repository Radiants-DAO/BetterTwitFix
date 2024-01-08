import json
import os

if ('RUNNING_SERVERLESS' in os.environ and os.environ['RUNNING_SERVERLESS'] == '1'): # pragma: no cover
    config = {
            "config":{
                "link_cache":os.getenv("RADTWITTER_LINK_CACHE","none"),
                "database":os.getenv("RADTWITTER_DATABASE",""),
                "table":os.getenv("RADTWITTER_CACHE_TABLE",""),
                "color":os.getenv("RADTWITTER_COLOR",""), 
                "appname": os.getenv("RADTWITTER_APP_NAME","radTwitter"), 
                "repo": os.getenv("RADTWITTER_REPO","https://github.com/Radiants-DAO/BetterTwitFix"), 
                "url": os.getenv("RADTWITTER_URL","https://radtwitter.com"),
                "combination_method": os.getenv("RADTWITTER_COMBINATION_METHOD","local"), # can either be 'local' or a URL to a server handling requests in the same format
                "gifConvertAPI":os.getenv("RADTWITTER_GIF_CONVERT_API",""),
                "workaroundTokens":os.getenv("RADTWITTER_WORKAROUND_TOKENS",None)
            }
        }
else:
    # Read config from config.json. If it does not exist, create new.
    if not os.path.exists("config.json"):
        with open("config.json", "w") as outfile:
            default_config = {
                "config":{
                    "link_cache":"json",
                    "database":"[url to mongo database goes here]",
                    "table":"TwiFix",
                    "color":"#43B581", 
                    "appname": "radTwitter", 
                    "repo": "https://github.com/Radiants-DAO/BetterTwitFix", 
                    "url": "https://radtwitter.com",
                    "combination_method": "local", # can either be 'local' or a URL to a server handling requests in the same format
                    "gifConvertAPI":"",
                    "workaroundTokens":None
                }
            }

            json.dump(default_config, outfile, indent=4, sort_keys=True)

        config = default_config
    else:
        f = open("config.json")
        config = json.load(f)
        f.close()
