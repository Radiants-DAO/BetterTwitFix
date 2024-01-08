from configHandler import config
import pymongo
from datetime import date,datetime
import json
import os
import boto3
import radlogging as log

link_cache_system = config['config']['link_cache']
link_cache = {}
DYNAMO_CACHE_TBL=None
if link_cache_system=="dynamodb": # pragma: no cover
    DYNAMO_CACHE_TBL=config['config']['table']

if link_cache_system == "json":
    link_cache = {}
    if not os.path.exists("links.json"):
        with open("links.json", "w") as outfile:
            default_link_cache = {}
            json.dump(default_link_cache, outfile)
    try:
        f = open('links.json',)
        link_cache = json.load(f)
    except json.decoder.JSONDecodeError:
        log.warn("Failed to load cache JSON file. Creating new file.")
        link_cache = {}
    except FileNotFoundError:
        log.warn("Failed to load cache JSON file. Creating new file.")
        link_cache = {}
    finally:
        f.close()
elif link_cache_system == "ram":
    link_cache = {}
    log.warn("Your link_cache_system is set to 'ram' which is not recommended; this is only intended to be used for tests")
elif link_cache_system == "db":
    client = pymongo.MongoClient(config['config']['database'], connect=False)
    table = config['config']['table']
    db = client[table]
elif link_cache_system == "dynamodb": # pragma: no cover
    client = boto3.resource('dynamodb')

def serializeUnknown(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def addVnfToLinkCache(video_link, vnf):
    video_link = video_link.lower()
    global link_cache
    try:
        if link_cache_system == "db":
                out = db.linkCache.update_one(vnf)
                log.debug("Link added to DB cache ")
                return True
        elif link_cache_system == "json":
            link_cache[video_link] = vnf
            with open("links.json", "w") as outfile: 
                json.dump(link_cache, outfile, indent=4, sort_keys=True, default=serializeUnknown)
            log.debug("Link added to JSON cache ")
            return True
        elif link_cache_system == "ram": # FOR TESTS ONLY
            link_cache[video_link] = vnf
            log.debug("Link added to RAM cache ")
        elif link_cache_system == "dynamodb": # pragma: no cover
            vnf["ttl"] = int(vnf["ttl"].strftime('%s'))
            table = client.Table(DYNAMO_CACHE_TBL)
            table.put_item(
                Item={
                    'tweet': video_link,
                    'vnf': vnf,
                    'ttl':vnf["ttl"]
                }
            )
            log.debug("Link added to dynamodb cache ")
            return True
    except Exception as e:
        log.error("Failed to add link to DB cache: "+str(e)+" "+video_link)
        return False

def getVnfFromLinkCache(video_link):
    video_link = video_link.lower()
    global link_cache
    if link_cache_system == "db":
        collection = db.linkCache
        vnf        = collection.find_one({'tweet': video_link})
        if vnf != None: 
            hits   = ( vnf['hits'] + 1 ) 
            log.debug("Link located in DB cache.")
            query  = { 'tweet': video_link }
            change = { "$set" : { "hits" : hits } }
            out    = db.linkCache.update_one(query, change)
            return vnf
        else:
            log.debug("Link not in DB cache")
            return None
    elif link_cache_system == "json":
        if video_link in link_cache:
            log.debug("Link located in json cache")
            vnf = link_cache[video_link]
            return vnf
        else:
            log.debug("Link not in json cache")
            return None
    elif link_cache_system == "dynamodb": # pragma: no cover
        table = client.Table(DYNAMO_CACHE_TBL)
        response = table.get_item(
            Key={
                'tweet': video_link
            }
        )
        if 'Item' in response:
            log.debug("Link located in dynamodb cache")
            vnf = response['Item']['vnf']
            return vnf
        else:
            log.debug("Link not in dynamodb cache")
            return None
    elif link_cache_system == "ram": # FOR TESTS ONLY
        if video_link in link_cache:
            log.debug("Link located in json cache")
            vnf = link_cache[video_link]
            return vnf
        else:
            log.debug("Link not in cache")
            return None
    elif link_cache_system == "none":
        return None

def clearCache():
    global link_cache
    # only intended for use in tests
    if link_cache_system == "ram":
        link_cache={}

def setCache(value):
    newCache = {}
    for key in value:
        newCache[key.lower()] = value[key]
    global link_cache
    # only intended for use in tests
    if link_cache_system == "ram":
        link_cache=newCache