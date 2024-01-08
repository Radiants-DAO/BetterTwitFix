import uuid
import json
import requests
import re
import os
import random
import urllib.parse
import math
bearer="Bearer AAAAAAAAAAAAAAAAAAAAAPYXBAAAAAAACLXUNDekMxqa8h%2F40K4moUkGsoc%3DTYfbDKbT3jJPCEVnMYqilB28NHfOPqkca3qaAxGfsyKCs0wRbw"
v2Bearer="Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
guestToken=None
guestTokenUses=0
pathregex = r"\w{1,15}\/(status|statuses)\/(\d{2,20})"
userregex = r"^https?:\/\/(?:www\.)?twitter\.com\/(?:#!\/)?@?([^/?#]*)(?:[?#/].*)?$"
userIDregex = r"\/i\/user\/(\d+)"

v2Features='{"longform_notetweets_inline_media_enabled":true,"super_follow_badge_privacy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"super_follow_user_api_enabled":true,"super_follow_tweet_api_enabled":true,"android_graphql_skip_api_media_color_palette":true,"creator_subscriptions_tweet_preview_api_enabled":true,"freedom_of_speech_not_reach_fetch_enabled":true,"creator_subscriptions_subscription_count_enabled":true,"tweetypie_unmention_optimization_enabled":true,"longform_notetweets_consumption_enabled":true,"subscriptions_verification_info_enabled":true,"blue_business_profile_image_shape_enabled":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"super_follow_exclusive_tweet_notifications_enabled":true}'
v2graphql_api="2OOZWmw8nAtUHVnXXQhgaA"

v2AnonFeatures='{"creator_subscriptions_tweet_preview_api_enabled":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":false,"tweet_awards_web_tipping_enabled":false,"responsive_web_home_pinned_timelines_enabled":true,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"responsive_web_media_download_video_enabled":false,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_enhance_cards_enabled":false}'
v2AnonGraphql_api="5GOHgZe-8U2j5sVHQzEm9A"
gt_pattern = r'document\.cookie="gt=([^;]+);'
class TwExtractError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.msg = message

    def __str__(self):
        return self.msg

def getGuestToken():
    global guestToken
    global guestTokenUses
    if guestToken is None:
        r = requests.get("https://twitter.com",headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0"})
        m = re.search(gt_pattern, r.text)
        if m is None:
            r = requests.post("https://api.twitter.com/1.1/guest/activate.json", headers={"Authorization":v2Bearer})
            guestToken = json.loads(r.text)["guest_token"]
        else:
            guestToken = m.group(1)
        guestTokenUses = 0
    else:
        guestTokenUses+=1
        if guestTokenUses > 40:
            gtTemp = guestToken
            guestToken = None
            guestTokenUses = 0
            return gtTemp
    return guestToken

def extractStatus_token(url,workaroundTokens):
    # get tweet ID
    m = re.search(pathregex, url)
    if m is None:
        raise TwExtractError(400, "Extract error")
    twid = m.group(2)
    if workaroundTokens == None:
        raise TwExtractError(400, "Extract error (no tokens defined)")
    # get tweet
    tokens = workaroundTokens
    random.shuffle(tokens)
    for authToken in tokens:
        try:
            csrfToken=str(uuid.uuid4()).replace('-', '')
            tweet = requests.get("https://api.twitter.com/1.1/statuses/show/" + twid + ".json?tweet_mode=extended&cards_platform=Web-12&include_cards=1&include_reply_count=1&include_user_entities=0", headers={"Authorization":bearer,"Cookie":f"auth_token={authToken}; ct0={csrfToken}; ","x-twitter-active-user":"yes","x-twitter-auth-type":"OAuth2Session","x-twitter-client-language":"en","x-csrf-token":csrfToken,"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0"})
            output = tweet.json()
            if "errors" in output:
                # try another token
                continue
        except Exception as e:
            continue
        return output
    raise TwExtractError(400, "Extract error")

def extractStatus_guestToken(url):
    # get tweet ID
    m = re.search(pathregex, url)
    if m is None:
        return extractStatus_token(url)
    twid = m.group(2)
    # get guest token
    guestToken = getGuestToken()
    # get tweet
    tweet = requests.get("https://api.twitter.com/1.1/statuses/show/" + twid + ".json?tweet_mode=extended&cards_platform=Web-12&include_cards=1&include_reply_count=1&include_user_entities=0", headers={"Authorization":bearer, "x-guest-token":guestToken})
    output = tweet.json()
    if "errors" in output:
        # pick the first error and create a twExtractError
        error = output["errors"][0]
        raise TwExtractError(error["code"], error["message"])
    return output

digits = "0123456789abcdefghijklmnopqrstuvwxyz"

def baseConversion(x, base):
    result = ''
    i = int(x)
    while i > 0:
        result = digits[i % base] + result
        i = i // base
    if int(x) != x:
        result += '.'
        i = x - int(x)
        d = 0
        while i != int(i):
            result += digits[int(i * base % base)]
            i = i * base
            d += 1
            if d >= 8:
                break
    return result

def calcSyndicationToken(idStr):
    id = int(idStr) / 1000000000000000 * math.pi
    o = baseConversion(x=id, base=int(math.pow(6, 2)))
    c = o.replace('0', '').replace('.', '')
    if c == '':
        c = '0'
    return c

def extractStatus_syndication(url,workaroundTokens=None):
    # https://github.com/mikf/gallery-dl/blob/46cae04aa3a113c7b6bbee1bb468669564b14ae8/gallery_dl/extractor/twitter.py#L1784
    m = re.search(pathregex, url)
    if m is None:
        raise TwExtractError(400, "Extract error")
    twid = m.group(2)
    tweet = requests.get("https://cdn.syndication.twimg.com/tweet-result?id=" + twid+"&token="+calcSyndicationToken(twid))
    
    
    if tweet.status_code == 404:
        raise TwExtractError(404, "Tweet not found")
    output = tweet.json()
    if "errors" in output:
        # pick the first error and create a twExtractError
        error = output["errors"][0]
        raise TwExtractError(error["code"], error["message"])
    
    # change returned data to match the one from the other methods
    output['full_text'] = output['text']
    output['user']['profile_image_url'] = output['user']['profile_image_url_https']
    output['retweet_count']=0
    if 'mediaDetails' in output:
        output['extended_entities'] = {'media':output['mediaDetails']}
        for media in output['extended_entities']['media']:
            media['media_url'] = media['media_url_https']
    if 'quoted_tweet' in output:
        output['quoted_status'] = output['quoted_tweet']
        quotedID=output['quoted_tweet']['id_str']
        quotedScreenName=output['quoted_tweet']['user']['screen_name']
        output['quoted_status_permalink'] = {'expanded':f"https://twitter.com/{quotedScreenName}/status/{quotedID}"}

    #output['user']['']

    return output

def extractStatus_twExtractProxy(url,workaroundTokens=None):
    proxies = os.getenv("RADTWITTER_PROXIES",None)
    if proxies is None:
        raise TwExtractError(400, "Extract error")
    proxies = proxies.split(',')
    random.shuffle(proxies)
    for proxy in proxies:
        try:
            tweet = requests.get(f"{proxy}?url={urllib.parse.quote(url)}")
            output = tweet.json()
            if "errors" in output:
                # try another token
                continue
        except Exception as e:
            continue
        return output

def extractStatusV2(url,workaroundTokens):
    # get tweet ID
    m = re.search(pathregex, url)
    if m is None:
        raise TwExtractError(400, "Extract error")
    twid = m.group(2)
    if workaroundTokens == None:
        raise TwExtractError(400, "Extract error (no tokens defined)")
    # get tweet
    tokens = workaroundTokens
    random.shuffle(tokens)
    for authToken in tokens:
        try:
            csrfToken=str(uuid.uuid4()).replace('-', '')
            vars = json.loads('{"includeTweetImpression":true,"includeHasBirdwatchNotes":false,"includeEditPerspective":false,"rest_ids":["x"],"includeEditControl":true,"includeCommunityTweetRelationship":true,"includeTweetVisibilityNudge":true}')
            vars['rest_ids'][0] = str(twid)
            tweet = requests.get(f"https://twitter.com/i/api/graphql/{v2graphql_api}/TweetResultsByIdsQuery?variables={urllib.parse.quote(json.dumps(vars))}&features={urllib.parse.quote(v2Features)}", headers={"Authorization":v2Bearer,"Cookie":f"auth_token={authToken}; ct0={csrfToken}; ","x-twitter-active-user":"yes","x-twitter-auth-type":"OAuth2Session","x-twitter-client-language":"en","x-csrf-token":csrfToken,"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0"})
            try:
                rateLimitRemaining = tweet.headers.get("x-rate-limit-remaining")
                print(f"Twitter Token Rate limit remaining: {rateLimitRemaining}")
            except: # for some reason the header is not always present
                pass
            if tweet.status_code == 429:
                # try another token
                continue
            output = tweet.json()
            
            if "errors" in output:
                # try another token
                continue
            entries=output['data']['tweet_results']
            tweetEntry=None
            for entry in entries:
                result = entry['result']
                if '__typename' in result and result['__typename'] == 'TweetWithVisibilityResults':
                    result=result['tweet']
                if 'rest_id' in result and result['rest_id'] == twid:
                    tweetEntry=result
                    break
            tweet=tweetEntry
        except Exception as e:
            continue
        return tweet
    raise TwExtractError(400, "Extract error")

def extractStatusV2Anon(url):
    # get tweet ID
    m = re.search(pathregex, url)
    if m is None:
        raise TwExtractError(400, "Extract error")
    twid = m.group(2)

    guestToken = getGuestToken()

    # get tweet
    try:
        vars = json.loads('{"tweetId":"0","withCommunity":false,"includePromotedContent":false,"withVoice":false}')
        vars['tweetId'] = str(twid)
        tweet = requests.get(f"https://api.twitter.com/graphql/{v2AnonGraphql_api}/TweetResultByRestId?variables={urllib.parse.quote(json.dumps(vars))}&features={urllib.parse.quote(v2AnonFeatures)}", headers={"Authorization":v2Bearer,"x-twitter-active-user":"yes","x-guest-token":guestToken,"x-twitter-client-language":"en","User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0"})
        try:
            rateLimitRemaining = tweet.headers.get("x-rate-limit-remaining")
            print(f"Twitter Anon Token Rate limit remaining: {rateLimitRemaining}")
        except: # for some reason the header is not always present
            pass
        if tweet.status_code == 429:
            raise TwExtractError(400, "Extract error")
        output = tweet.json()
        
        if "errors" in output:
            raise TwExtractError(400, "Extract error")
        entry=output['data']['tweetResult']
        tweetEntry=None
        result = entry['result']
        if '__typename' in result and result['__typename'] == 'TweetWithVisibilityResults':
            result=result['tweet']
        if 'rest_id' in result and result['rest_id'] == twid:
            tweetEntry=result
        tweet=tweetEntry
    except Exception as e:
        raise TwExtractError(400, "Extract error")
    return tweet

def extractStatusV2Legacy(url,workaroundTokens):
    tweet = extractStatusV2(url,workaroundTokens)
    if 'errors' in tweet or 'legacy' not in tweet:
        if 'errors' in tweet:
            raise TwExtractError(400, "Extract error: "+json.dumps(tweet['errors']))
        else:
            raise TwExtractError(400, "Extract error (no legacy data)")
    tweet['legacy']['user'] = tweet["core"]["user_result"]["result"]["legacy"]
    tweet['legacy']['user']['profile_image_url'] = tweet['legacy']['user']['profile_image_url_https']
    if 'card' in tweet:
        tweet['legacy']['card'] = tweet['card']['legacy']
    if 'extended_entities' in tweet['legacy']:
        tweet['legacy']['extended_entities'] = {'media':tweet['legacy']['extended_entities']['media']}
        for media in tweet['legacy']['extended_entities']['media']:
            media['media_url'] = media['media_url_https']
    if 'tweet_card' in tweet:
        tweet['legacy']['card'] = tweet['tweet_card']['legacy']
    return tweet['legacy']

def extractStatusV2AnonLegacy(url,workaroundTokens):
    tweet = extractStatusV2Anon(url)
    if 'errors' in tweet or 'legacy' not in tweet:
        if 'errors' in tweet:
            raise TwExtractError(400, "Extract error: "+json.dumps(tweet['errors']))
        else:
            raise TwExtractError(400, "Extract error (no legacy data)")
    tweet['legacy']['user'] = tweet["core"]["user_results"]["result"]["legacy"]
    tweet['legacy']['user']['profile_image_url'] = tweet['legacy']['user']['profile_image_url_https']
    if 'card' in tweet:
        tweet['legacy']['card'] = tweet['card']['legacy']
    if 'extended_entities' in tweet['legacy']:
        tweet['legacy']['extended_entities'] = {'media':tweet['legacy']['extended_entities']['media']}
        for media in tweet['legacy']['extended_entities']['media']:
            media['media_url'] = media['media_url_https']
    if 'tweet_card' in tweet:
        tweet['legacy']['card'] = tweet['tweet_card']['legacy']
    return tweet['legacy']

def extractStatus(url,workaroundTokens=None):
    methods=[extractStatusV2AnonLegacy,extractStatus_syndication,extractStatusV2Legacy,extractStatus_twExtractProxy]
    for method in methods:
        try:
            return method(url,workaroundTokens)
        except Exception as e:
            print(f"{method.__name__} method failed: {str(e)} for {url}")
            continue
    raise TwExtractError(400, "Extract error")

def extractUser(url,workaroundTokens):
    useId=True
    m = re.search(userIDregex, url)
    if m is None:
        m = re.search(userregex, url)
        if m is None:
            raise TwExtractError(400, "Invalid URL")
        else:
            useId=False
    screen_name = m.group(1)
    # get user
    tokens = workaroundTokens
    random.shuffle(tokens)
    for authToken in tokens:
        try:
            csrfToken=str(uuid.uuid4()).replace('-', '')
            reqHeaders = {"Authorization":bearer,"Cookie":f"auth_token={authToken}; ct0={csrfToken}; ","x-twitter-active-user":"yes","x-twitter-auth-type":"OAuth2Session","x-twitter-client-language":"en","x-csrf-token":csrfToken,"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0"}
            if not useId:
                user = requests.get(f"https://api.twitter.com/1.1/users/show.json?screen_name={screen_name}",headers=reqHeaders)
            else:
                user = requests.get(f"https://api.twitter.com/1.1/users/show.json?user_id={screen_name}",headers=reqHeaders)
            output = user.json()
            if "errors" in output:
                # pick the first error and create a twExtractError
                error = output["errors"][0]
                raise TwExtractError(error["code"], error["message"])
            return output
        except Exception as e:
            continue
    raise TwExtractError(400, "Extract error")

#def extractUserByID(id):
    

def lambda_handler(event, context):
    if ("queryStringParameters" not in event):
        return {
            "statusCode": 400,
            "body": "Invalid request."
        }
    url = event["queryStringParameters"].get("url","")
    return {
        'statusCode': 200,
        'body': extractStatus(url,workaroundTokens=os.getenv("RADTWITTER_WORKAROUND_TOKENS",None).split(','))
    }