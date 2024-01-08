from weakref import finalize
from flask import Flask, render_template, request, redirect, abort, Response, send_from_directory, url_for, send_file, make_response, jsonify
from flask_cors import CORS
import textwrap
import re
import os
import urllib.parse
import urllib.request
import combineImg
from datetime import date,datetime, timedelta
from io import BytesIO, StringIO
import msgs
import twExtract as twExtract
from configHandler import config
from cache import addVnfToLinkCache,getVnfFromLinkCache
from yt_dlp.utils import ExtractorError
import radlogging as log
import zipfile
import html
app = Flask(__name__)
CORS(app)

pathregex = re.compile("\\w{1,15}\\/(status|statuses)\\/(\\d{2,20})")
generate_embed_user_agents = [
    "facebookexternalhit/1.1",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.57 Safari/537.36",
    "Mozilla/5.0 (Windows; U; Windows NT 10.0; en-US; Valve Steam Client/default/1596241936; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36",
    "Mozilla/5.0 (Windows; U; Windows NT 10.0; en-US; Valve Steam Client/default/0; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36", 
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.4 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.4 facebookexternalhit/1.1 Facebot Twitterbot/1.0", 
    "facebookexternalhit/1.1",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; Valve Steam FriendsUI Tenfoot/0; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36", 
    "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)", 
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:38.0) Gecko/20100101 Firefox/38.0", 
    "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)", 
    "TelegramBot (like TwitterBot)", 
    "Mozilla/5.0 (compatible; January/1.0; +https://gitlab.insrt.uk/revolt/january)", 
    "Synapse (bot; +https://github.com/matrix-org/synapse)",
    "test"]

def isValidUserAgent(user_agent):
    return True
    if user_agent in generate_embed_user_agents:
        return True
    elif "WhatsApp/" in user_agent:
        return True
    return False

def getTweetIdFromUrl(url):
    match = pathregex.search(url)
    if match is not None:
        return match.group(2)
    else:
        return None

@app.route('/robots.txt')
def robots():
    return "User-agent: *\nDisallow: /"

@app.route('/') # If the useragent is discord, return the embed, if not, redirect to configured repo directly
def default():
    user_agent = request.headers.get('user-agent')
    if isValidUserAgent(user_agent):
        return message("TwitFix is an attempt to fix twitter video embeds in discord! created by Robin Universe :)\n\n💖\n\nClick me to be redirected to the repo!")
    else:
        return redirect(config['config']['repo'], 301)

@app.route('/oembed.json') #oEmbed endpoint
def oembedend():
    desc  = request.args.get("desc", None)
    user  = request.args.get("user", None)
    link  = request.args.get("link", None)
    ttype = request.args.get("ttype", None)
    provName = request.args.get("provider",None)
    return  oEmbedGen(desc, user, link, ttype,providerName=provName)

@app.route('/<path:sub_path>') # Default endpoint used by everything
def twitfix(sub_path):

    user_agent = request.headers.get('user-agent')
    match = pathregex.search(sub_path)

    if request.url.endswith(".mp4") or request.url.endswith("%2Emp4"):
        twitter_url = "https://twitter.com/" + sub_path
        
        if "?" not in request.url:
            clean = twitter_url[:-4]
        else:
            clean = twitter_url
            
        vnf,e = vnfFromCacheOrDL(clean)
        if vnf is None:
            if e is not None:
                return message(msgs.failedToScan+msgs.failedToScanExtra+e)
            return message(msgs.failedToScan)
        return make_cached_vnf_response(vnf,getTemplate("rawvideo.html",vnf,"","",clean,"","","",""))
    elif request.url.endswith(".txt") or request.url.endswith("%2Etxt"):
        twitter_url = "https://twitter.com/" + sub_path
        
        if "?" not in request.url:
            clean = twitter_url[:-4]
        else:
            clean = twitter_url
            
        vnf,e = vnfFromCacheOrDL(clean)
        if vnf is None:
            if e is not None:
                return abort(500,"Failed to scan tweet: "+e)
            return abort(500,"Failed to scan tweet")
        return make_content_type_response(getTemplate("txt.html",vnf,vnf["description"],"",clean,"","","",""),"text/plain")
    elif request.url.endswith(".zip") or request.url.endswith("%2Ezip"): # for certain types of archival software (i.e Hydrus)
        twitter_url = "https://twitter.com/" + sub_path
        
        if "?" not in request.url:
            clean = twitter_url[:-4]
        else:
            clean = twitter_url
            
        vnf,e = vnfFromCacheOrDL(clean)
        if vnf is None:
            if e is not None:
                return abort(500,"Failed to scan tweet: "+e)
            return abort(500,"Failed to scan tweet")
        with app.app_context():
            txtData = getTemplate("txt.html",vnf,vnf["description"],"",clean,"","","","")
        txtIo = BytesIO()
        txtIo.write(txtData.encode("utf-8"))
        txtIo.seek(0)
        zipIo = BytesIO()
        with zipfile.ZipFile(zipIo, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("tweetInfo.txt", txtIo.read())
        # todo: add images to zip
        zipIo.seek(0)
        return make_content_type_response(zipIo,"application/zip")
    elif request.url.startswith("https://d.rad"): # Matches d.fx? Try to give the user a direct link
        if isValidUserAgent(user_agent):
            twitter_url = config['config']['url'] + "/"+sub_path
            log.debug( "d.rad link shown to discord user-agent!")
            if request.url.endswith(".mp4") and "?" not in request.url:
                if "?" not in request.url:
                    clean = twitter_url[:-4]
                else:
                    clean = twitter_url
            else:
                clean = twitter_url
            return redirect(clean+".mp4", 301)
        else:
            log.debug("Redirect to MP4 using d.fxtwitter.com")
            return dir(sub_path)
    elif request.url.endswith("/1") or request.url.endswith("/2") or request.url.endswith("/3") or request.url.endswith("/4") or request.url.endswith("%2F1") or request.url.endswith("%2F2") or request.url.endswith("%2F3") or request.url.endswith("%2F4"):
        twitter_url = "https://twitter.com/" + sub_path
        
        if "?" not in request.url:
            clean = twitter_url[:-2]
        else:
            clean = twitter_url

        image = ( int(request.url[-1]) - 1 )
        return embed_video(clean, image)
    elif request.url.startswith("https://api.rad"):
        twitter_url = "https://twitter.com/" + sub_path
        try:
            try:
                tweet = twExtract.extractStatusV2Anon(twitter_url)
            except:
                tweet = None
            if tweet is None:
                tweet = twExtract.extractStatusV2(twitter_url,workaroundTokens=config['config']['workaroundTokens'].split(','))
            tweetL = tweet["legacy"]
            if "user_result" in tweet["core"]:
                userL = tweet["core"]["user_result"]["result"]["legacy"]
            elif "user_results" in tweet["core"]:
                userL = tweet["core"]["user_results"]["result"]["legacy"]
            media=[]
            media_extended=[]
            hashtags=[]
            communityNote=None
            try:
                if "birdwatch_pivot" in tweet:
                    communityNote=tweet["birdwatch_pivot"]["note"]["summary"]["text"]
            except:
                pass
            if "extended_entities" in tweetL:
                if "media" in tweetL["extended_entities"]:
                    tmedia=tweetL["extended_entities"]["media"]
                    for i in tmedia:
                        extendedInfo={}
                        if "video_info" in i:
                            # find the highest bitrate
                            best_bitrate = -1
                            besturl=""
                            for j in i["video_info"]["variants"]:
                                if j['content_type'] == "video/mp4" and j['bitrate'] > best_bitrate:
                                    besturl = j['url']
                                    best_bitrate = j['bitrate']
                            media.append(besturl)
                            extendedInfo["url"] = besturl
                            extendedInfo["type"] = "video"
                            if (i["type"] == "animated_gif"):
                                extendedInfo["type"] = "gif"
                            altText = None
                            extendedInfo["size"] = {"width":i["original_info"]["width"],"height":i["original_info"]["height"]}
                            if "ext_alt_text" in i:
                                altText=i["ext_alt_text"]
                            if "duration_millis" in i["video_info"]:
                                extendedInfo["duration_millis"] = i["video_info"]["duration_millis"]
                            else:
                                extendedInfo["duration_millis"] = 0
                            extendedInfo["thumbnail_url"] = i["media_url_https"]
                            extendedInfo["altText"] = altText
                            media_extended.append(extendedInfo)
                        else:
                            media.append(i["media_url_https"])
                            extendedInfo["url"] = i["media_url_https"]
                            altText=None
                            if "ext_alt_text" in i:
                                altText=i["ext_alt_text"]
                            extendedInfo["altText"] = altText
                            extendedInfo["type"] = "image"
                            extendedInfo["size"] = {"width":i["original_info"]["width"],"height":i["original_info"]["height"]}
                            extendedInfo["thumbnail_url"] = i["media_url_https"]
                            media_extended.append(extendedInfo)

                if "hashtags" in tweetL["entities"]:
                    for i in tweetL["entities"]["hashtags"]:
                        hashtags.append(i["text"])

            include_txt = request.args.get("include_txt", "false")
            include_zip = request.args.get("include_zip", "false") # for certain types of archival software (i.e Hydrus)

            if include_txt == "true" or (include_txt == "ifnomedia" and len(media)==0):
                txturl = config['config']['url']+"/"+userL["screen_name"]+"/status/"+tweet["rest_id"]+".txt"
                media.append(txturl)
                media_extended.append({"url":txturl,"type":"txt"})
            if include_zip == "true" or (include_zip == "ifnomedia" and len(media)==0): 
                zipurl = config['config']['url']+"/"+userL["screen_name"]+"/status/"+tweet["rest_id"]+".zip"
                media.append(zipurl)
                media_extended.append({"url":zipurl,"type":"zip"})

            qrtURL = None
            if 'quoted_status_id_str' in tweetL:
                qrtURL = "https://twitter.com/i/status/" + tweetL['quoted_status_id_str']

            if 'possibly_sensitive' not in tweetL:
                tweetL['possibly_sensitive'] = False

            twText = html.unescape(tweetL["full_text"])

            if 'entities' in tweetL and 'urls' in tweetL['entities']:
                for eurl in tweetL['entities']['urls']:
                    if "/status/" in eurl["expanded_url"] and eurl["expanded_url"].startswith("https://twitter.com/"):
                        twText = twText.replace(eurl["url"], "")
                    else:
                        twText = twText.replace(eurl["url"],eurl["expanded_url"])

            apiObject = {
                "text": twText,
                "likes": tweetL["favorite_count"],
                "retweets": tweetL["retweet_count"],
                "replies": tweetL["reply_count"],
                "date": tweetL["created_at"],
                "user_screen_name": html.unescape(userL["screen_name"]),
                "user_name": userL["name"],
                "user_profile_image_url": userL["profile_image_url_https"],
                "tweetURL": "https://twitter.com/"+userL["screen_name"]+"/status/"+tweet["rest_id"],
                "tweetID": tweet["rest_id"],
                "conversationID": tweetL["conversation_id_str"],
                "mediaURLs": media,
                "media_extended": media_extended,
                "possibly_sensitive": tweetL["possibly_sensitive"],
                "hashtags": hashtags,
                "qrtURL": qrtURL,
                "communityNote": communityNote
            }
            try:
                apiObject["date_epoch"] = int(datetime.strptime(tweetL["created_at"], "%a %b %d %H:%M:%S %z %Y").timestamp())
            except:
                pass

            if tweet is None:
                log.error("API Get failed: " + twitter_url + " (Tweet null)")
                abort(500, '{"message": "Failed to extract tweet (Twitter API error)"}')
            log.success("API Get success")
            return apiObject
        except Exception as e:
            log.error("API Get failed: " + twitter_url + " " + log.get_exception_traceback_str(e))
            abort(500, '{"message": "Failed to extract tweet (Processing error)"}')

    if match is not None:
        twitter_url = sub_path

        if match.start() == 0:
            twitter_url = "https://twitter.com/" + sub_path
        else:
            # URL normalization messes up the URL, so we have to fix it
            if sub_path.startswith("https:/") and not sub_path.startswith("https://"):
                twitter_url = sub_path.replace("https:/", "https://", 1)
            elif sub_path.startswith("http:/") and not sub_path.startswith("http://"):
                twitter_url = sub_path.replace("http:/", "http://", 1)

        if isValidUserAgent(user_agent):
            res = embedCombined(twitter_url)
            return res

        else:
            log.debug("Redirect to " + twitter_url)
            return redirect(twitter_url, 301)
    else:
        return message("This doesn't appear to be a twitter URL")

        
@app.route('/dir/<path:sub_path>') # Try to return a direct link to the MP4 on twitters servers
def dir(sub_path):
    user_agent = request.headers.get('user-agent')
    url   = sub_path
    match = pathregex.search(url)
    if match is not None:
        twitter_url = url

        if match.start() == 0:
            twitter_url = "https://twitter.com/" + url

        if isValidUserAgent(user_agent):
            res = embed_video(twitter_url)
            return res

        else:
            log.debug("Redirect to direct MP4 URL")
            return direct_video(twitter_url)
    else:
        return redirect(url, 301)

@app.route('/favicon.ico')
def favicon(): # pragma: no cover
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico',mimetype='image/vnd.microsoft.icon')

@app.route('/apple-touch-icon.png')
def apple_touch_icon(): # pragma: no cover
    return send_from_directory(os.path.join(app.root_path, 'static'), 'apple-touch-icon.png',mimetype='image/png')

@app.route("/rendercombined.jpg")
def rendercombined():
    # get "imgs" from request arguments
    imgs = request.args.get("imgs", "")

    if 'combination_method' in config['config'] and config['config']['combination_method'] != "local":
        url = config['config']['combination_method'] + "/rendercombined.jpg?imgs=" + imgs
        return redirect(url, 302)
    # Redirecting here instead of setting the embed URL directly to this because if the config combination_method changes in the future, old URLs will still work

    imgs = imgs.split(",")
    if (len(imgs) == 0 or len(imgs)>4):
        abort(400)
    #check that each image starts with "https://pbs.twimg.com"
    for img in imgs:
        if not img.startswith("https://pbs.twimg.com"):
            abort(400)
    finalImg= combineImg.genImageFromURL(imgs)
    imgIo = BytesIO()
    finalImg = finalImg.convert("RGB")
    finalImg.save(imgIo, 'JPEG',quality=70)
    imgIo.seek(0)
    return send_file(imgIo, mimetype='image/jpeg',max_age=86400)

def upgradeVNF(vnf):
    # Makes sure any VNF object passed through this has proper fields if they're added in later versions
    if 'verified' not in vnf:
        vnf['verified']=False
    if 'size' not in vnf:
        if vnf['type'] == 'Video':
            vnf['size']={'width':720,'height':480}
        else:
            vnf['size']={}
    if 'qrtURL' not in vnf:
        if vnf['qrt'] == {}:
            vnf['qrtURL'] = None
        else: # 
            vnf['qrtURL'] = f"https://twitter.com/{vnf['qrt']['screen_name']}/status/{vnf['qrt']['id']}"
    if 'isGif' not in vnf:
        vnf['isGif'] = False
    return vnf

def getDefaultTTL(): # TTL for deleting items from the database
    return datetime.today().replace(microsecond=0) + timedelta(days=1)

def secondsUntilTTL(ttl):
    untilTTL = ttl - datetime.today().replace(microsecond=0)
    return untilTTL.total_seconds()

def make_content_type_response(response, content_type):
    resp = make_response(response)
    resp.headers['Content-Type'] = content_type
    return resp

def make_cached_vnf_response(vnf,response):
    return response
    try:
        if 'ttl' not in vnf or vnf['ttl'] == None or secondsUntilTTL(vnf['ttl']) <= 0:
            return response
        resp = make_response(response)
        resp.cache_control.max_age = secondsUntilTTL(vnf['ttl'])
        resp.cache_control.public = True
        return resp
    except Exception as e:
        log.error("Error making cached response: " + str(e))
        return response

def vnfFromCacheOrDL(video_link):
    cached_vnf = getVnfFromLinkCache(video_link)
    if cached_vnf == None:
        try:
            vnf = link_to_vnf(video_link)
            addVnfToLinkCache(video_link, vnf)
            log.success("VNF Get success")
            return vnf,None
        except (ExtractorError, twExtract.TwExtractError) as exErr:
            if 'HTTP Error 404' in exErr.msg or 'No status found with that ID' in exErr.msg:
                exErr.msg=msgs.tweetNotFound
            elif 'suspended' in exErr.msg:
                exErr.msg=msgs.tweetSuspended
            else:
                exErr.msg=msgs.unknownError
                
            log.error("VNF Get failed: " + video_link + " " + log.get_exception_traceback_str(exErr))
            return None,exErr.msg
        except Exception as e:
            log.error("VNF Get failed: " + video_link + " " + log.get_exception_traceback_str(e))
            return None,None
    else:
        return upgradeVNF(cached_vnf),None

def direct_video(video_link): # Just get a redirect to a MP4 link from any tweet link
    vnf,e = vnfFromCacheOrDL(video_link)
    if vnf != None:
        return redirect(vnf['url'], 301)
    else:
        if e is not None:
            return message(msgs.failedToScan+msgs.failedToScanExtra+e)
        return message(msgs.failedToScan)

def direct_video_link(video_link): # Just get a redirect to a MP4 link from any tweet link
    vnf,e = vnfFromCacheOrDL(video_link)
    if vnf != None:
        return vnf['url']
    else:
        if e is not None:
            return message(msgs.failedToScan+msgs.failedToScanExtra+e)
        return message(msgs.failedToScan)

def embed_video(video_link, image=0): # Return Embed from any tweet link
    vnf,e = vnfFromCacheOrDL(video_link)

    if vnf != None:
        return embed(video_link, vnf, image)
    else:
        if e is not None:
            return message(msgs.failedToScan+msgs.failedToScanExtra+e)
        return message(msgs.failedToScan)

def tweetInfo(url, tweet="", desc="", thumb="", uploader="", screen_name="", pfp="", tweetType="", images="", hits=0, likes=0, rts=0, time="", qrtURL="", nsfw=False,ttl=None,verified=False,size={},poll=None,isGif=False): # Return a dict of video info with default values
    if (ttl==None):
        ttl = getDefaultTTL()
    vnf = {
        "tweet"         : tweet,
        "url"           : url,
        "description"   : desc,
        "thumbnail"     : thumb,
        "uploader"      : uploader,
        "screen_name"   : screen_name,
        "pfp"           : pfp,
        "type"          : tweetType,
        "images"        : images,
        "hits"          : hits,
        "likes"         : likes,
        "rts"           : rts,
        "time"          : time,
        "qrtURL"        : qrtURL,
        "nsfw"          : nsfw,
        "ttl"           : ttl,
        "verified"      : verified,
        "size"          : size,
        "poll"          : poll,
        "isGif"         : isGif,
        "tweetId"       : int(getTweetIdFromUrl(tweet))
    }
    if (poll is None):
        del vnf['poll']
    return vnf

def link_to_vnf_from_tweet_data(tweet,video_link):
    imgs = ["","","","", ""]
    log.debug("Tweet Type: " + tweetType(tweet))
    isGif=False
    # Check to see if tweet has a video, if not, make the url passed to the VNF the first t.co link in the tweet
    if tweetType(tweet) == "Video":
        media=tweet['extended_entities']['media'][0]
        if media['video_info']['variants']:
            best_bitrate = -1
            thumb = media['media_url']
            if 'original_info' in media:
                size=media["original_info"]
            elif 'sizes' in media and ('large' in media["sizes"] or 'medium' in media["sizes"] or 'small' in media["sizes"] or 'thumb' in media["sizes"]):
                possibleSizes=['large','medium','small','thumb']
                for p in possibleSizes:
                    if p in media["sizes"]:
                        size={'width':media["sizes"][p]['w'],'height':media["sizes"][p]['h']}
                        break
            else:
                size={'width':720,'height':480}
            for video in media['video_info']['variants']:
                if video['content_type'] == "video/mp4" and video['bitrate'] > best_bitrate:
                    url = video['url']
                    best_bitrate = video['bitrate']
    elif tweetType(tweet) == "Text":
        url   = ""
        thumb = ""
        size  = {}
    else:
        imgs = ["","","","", ""]
        i = 0
        for media in tweet['extended_entities']['media']:
            imgs[i] = media['media_url_https']
            i = i + 1

        imgs[4] = str(i)
        url   = ""
        images= imgs
        thumb = tweet['extended_entities']['media'][0]['media_url_https']
        size  = {}

    if 'extended_entities' in tweet and 'media' in tweet['extended_entities'] and tweet['extended_entities']['media'][0]['type'] == 'animated_gif':
        isGif=True

    qrtURL = None
    if 'quoted_status_permalink' in tweet:
        qrtURL = tweet['quoted_status_permalink']['expanded']
    elif 'quoted_status_id_str' in tweet:
        qrtURL = "https://twitter.com/i/status/" + tweet['quoted_status_id_str']

    text = tweet['full_text']

    if 'possibly_sensitive' in tweet:
        nsfw = tweet['possibly_sensitive']
    else:
        nsfw = False

    if 'entities' in tweet and 'urls' in tweet['entities']:
        for eurl in tweet['entities']['urls']:
            if "/status/" in eurl["expanded_url"] and eurl["expanded_url"].startswith("https://twitter.com/"):
                text = text.replace(eurl["url"], "")
            else:
                text = text.replace(eurl["url"],eurl["expanded_url"])
    ttl = None #default

    try:
        if 'card' in tweet and tweet['card']['name'].startswith('poll'):
            poll=getPollObject(tweet['card'])
            if tweet['card']['binding_values']['counts_are_final']['boolean_value'] == False:
                ttl = datetime.today().replace(microsecond=0) + timedelta(minutes=1)
        else:
            poll=None
    except:
        poll=None

    vnf = tweetInfo(
        url, 
        video_link, 
        text, thumb, 
        tweet['user']['name'], 
        tweet['user']['screen_name'], 
        tweet['user']['profile_image_url'], 
        tweetType(tweet), 
        likes=tweet['favorite_count'], 
        rts=tweet['retweet_count'], 
        time=tweet['created_at'], 
        qrtURL=qrtURL, 
        images=imgs,
        nsfw=nsfw,
        verified=tweet['user']['verified'],
        size=size,
        poll=poll,
        ttl=ttl,
        isGif=isGif
        )
        
    return vnf


def link_to_vnf_from_unofficial_api(video_link):
    tweet=None
    log.info("Attempting to download tweet info: "+video_link)
    tweet = twExtract.extractStatus(video_link,workaroundTokens=config['config']['workaroundTokens'].split(','))
    log.success("Unofficial API Success")

    if "extended_entities" not in tweet:
        # check if any entities with urls ending in /video/XXX or /photo/XXX exist
        if "entities" in tweet and "urls" in tweet["entities"]:
            for url in tweet["entities"]["urls"]:
                if "/video/" in url["expanded_url"] or "/photo/" in url["expanded_url"]:
                    log.info("Extra tweet info found in entities: "+video_link+" -> "+url["expanded_url"])
                    subTweet = twExtract.extractStatus(url["expanded_url"],workaroundTokens=config['config']['workaroundTokens'].split(','))
                    if "extended_entities" in subTweet:
                        tweet["extended_entities"] = subTweet["extended_entities"]
                    break

    return link_to_vnf_from_tweet_data(tweet,video_link)

def link_to_vnf(video_link): # Return a VideoInfo object or die trying
    return link_to_vnf_from_unofficial_api(video_link)

def message(text):
    return render_template(
        'default.html', 
        message = text, 
        color   = config['config']['color'], 
        appname = config['config']['appname'], 
        repo    = config['config']['repo'], 
        url     = config['config']['url'] )

def getTemplate(template,vnf,desc,image,video_link,color,urlDesc,urlUser,urlLink,appNameSuffix="",embedVNF=None):
    if (embedVNF is None):
        embedVNF = vnf
    if ('width' in embedVNF['size'] and 'height' in embedVNF['size']):
        embedVNF['size']['width'] = min(embedVNF['size']['width'],2000)
        embedVNF['size']['height'] = min(embedVNF['size']['height'],2000)
    return render_template(
        template, 
        likes      = vnf['likes'], 
        rts        = vnf['rts'], 
        time       = vnf['time'], 
        screenName = vnf['screen_name'], 
        vidlink    = embedVNF['url'], 
        userLink   = f"https://twitter.com/{vnf['screen_name']}",
        pfp        = vnf['pfp'],  
        vidurl     = embedVNF['url'], 
        desc       = desc,
        pic        = image,
        user       = vnf['uploader'], 
        video_link = vnf, 
        color      = color, 
        appname    = config['config']['appname'] + appNameSuffix, 
        repo       = config['config']['repo'], 
        url        = config['config']['url'], 
        urlDesc    = urlDesc, 
        urlUser    = urlUser, 
        urlLink    = urlLink,
        urlUserLink= urllib.parse.quote(f"https://twitter.com/{vnf['screen_name']}"),
        tweetLink  = vnf['tweet'],
        videoSize  = embedVNF['size'] )

def embed(video_link, vnf, image):
    log.info("Embedding " + vnf['type'] + ": " + video_link)
    
    desc    = re.sub(r' https:\/\/t\.co\/\S+(?=\s|$)', '', vnf['description'])
    urlUser = urllib.parse.quote(vnf['uploader'])
    urlDesc = urllib.parse.quote(desc)
    urlLink = urllib.parse.quote(video_link)
    likeDisplay = msgs.genLikesDisplay(vnf)
    
    if 'poll' in vnf:
        pollDisplay= msgs.genPollDisplay(vnf['poll'])
    else:
        pollDisplay=""

    qrt=None
    if vnf['qrtURL'] is not None:
        qrt,e=vnfFromCacheOrDL(vnf['qrtURL'])
        if qrt is not None:
            desc=msgs.formatEmbedDesc(vnf['type'],desc,qrt,pollDisplay,likeDisplay)
    else:
        desc=msgs.formatEmbedDesc(vnf['type'],desc,None,pollDisplay,likeDisplay)
    embedVNF=None
    appNamePost = ""
    if vnf['type'] == "Text": # Change the template based on tweet type
        template = 'text.html'
        if qrt is not None and qrt['type'] != "Text":
            embedVNF=qrt
            if qrt['type'] == "Image":
                if embedVNF['images'][4]!="1":
                    appNamePost = " - Image " + str(image+1) + " of " + str(vnf['images'][4])
                image = embedVNF['images'][image]
                template = 'image.html'
            elif qrt['type'] == "Video" or qrt['type'] == "":
                urlDesc = urllib.parse.quote(desc)
                template = 'video.html'
            
    if vnf['type'] == "Image":
        if vnf['images'][4]!="1":
            appNamePost = " - Image " + str(image+1) + "/" + str(vnf['images'][4])
        image = vnf['images'][image]
        template = 'image.html'

    if vnf['type'] == "Video":
        if vnf['isGif'] == True and config['config']['gifConvertAPI'] != "" and config['config']['gifConvertAPI'] != "none":
            vnf['url'] = f"{config['config']['gifConvertAPI']}/convert.mp4?url={vnf['url']}"
            appNamePost = " - GIF"
        urlDesc = urllib.parse.quote(desc)
        template = 'video.html'

    if vnf['type'] == "":
        urlDesc  = urllib.parse.quote(desc)
        template = 'video.html'
        
    color = "#7FFFD4" # Green

    if vnf['nsfw'] == True:
        color = "#800020" # Red
    
    return make_cached_vnf_response(vnf,getTemplate(template,vnf,desc,image,video_link,color,urlDesc,urlUser,urlLink,appNamePost,embedVNF))


def embedCombined(video_link):
    vnf,e = vnfFromCacheOrDL(video_link)

    if vnf != None:
        return make_cached_vnf_response(vnf,embedCombinedVnf(video_link, vnf))
    else:
        if e is not None:
            return message(msgs.failedToScan+msgs.failedToScanExtra+e)
        return message(msgs.failedToScan)

def embedCombinedVnf(video_link,vnf):
    qrt=None
    if vnf['qrtURL'] is not None:
        qrt,e=vnfFromCacheOrDL(vnf['qrtURL'])

    if vnf['type'] != "Image" and vnf['type'] != "Video" and qrt is not None and qrt['type'] == "Image":
        if qrt['images'][4]!="1":
            vnf['images'] = qrt['images']
            vnf['type'] = "Image"

    if vnf['type'] != "Image" or vnf['images'][4] == "1":
        return embed(video_link, vnf, 0)
    desc    = re.sub(r' http.*t\.co\S+', '', vnf['description'])
    urlUser = urllib.parse.quote(vnf['uploader'])
    urlDesc = urllib.parse.quote(desc)
    urlLink = urllib.parse.quote(video_link)
    likeDisplay = msgs.genLikesDisplay(vnf)

    if 'poll' in vnf:
        pollDisplay= msgs.genPollDisplay(vnf['poll'])
    else:
        pollDisplay=""


    if qrt is not None:
        desc=msgs.formatEmbedDesc(vnf['type'],desc,qrt,pollDisplay,likeDisplay)

    host = config['config']['url']
    image = f"{host}/rendercombined.jpg?imgs="
    for i in range(0,int(vnf['images'][4])):
        image = image + vnf['images'][i] + ","
    image = image[:-1] # Remove last comma

    color = "#7FFFD4" # Green

    if vnf['nsfw'] == True:
        color = "#800020" # Red
    return make_cached_vnf_response(vnf,getTemplate('image.html',vnf,desc,image,video_link,color,urlDesc,urlUser,urlLink,appNameSuffix=" - View original tweet for full quality"))


def getPollObject(card):
    poll={"total_votes":0,"choices":[]}
    choiceCount=0
    if (card["name"]=="poll2choice_text_only"):
        choiceCount=2
    elif (card["name"]=="poll3choice_text_only"):
        choiceCount=3
    elif (card["name"]=="poll4choice_text_only"):
        choiceCount=4
    
    for i in range(0,choiceCount):
        choice = {"text":card["binding_values"][f"choice{i+1}_label"]["string_value"],"votes":int(card["binding_values"][f"choice{i+1}_count"]["string_value"])}
        poll["total_votes"]+=choice["votes"]
        poll["choices"].append(choice)
    # update each choice with a percentage
    for choice in poll["choices"]:
        choice["percent"] = round((choice["votes"]/poll["total_votes"])*100,1)

    return poll


def tweetType(tweet): # Are we dealing with a Video, Image, or Text tweet?
    if 'extended_entities' in tweet:
        if 'video_info' in tweet['extended_entities']['media'][0]:
            out = "Video"
        else:
            out = "Image"
    else:
        out = "Text"

    return out


def oEmbedGen(description, user, video_link, ttype,providerName=None):
    if providerName == None:
        providerName = config['config']['appname']
    out = {
            "type"          : ttype,
            "version"       : "1.0",
            "provider_name" : providerName,
            "provider_url"  : config['config']['repo'],
            "title"         : description,
            "author_name"   : user,
            "author_url"    : video_link
            }

    return out

if __name__ == "__main__":
    app.config['SERVER_NAME']='localhost:80'
    app.run(host='0.0.0.0')
