## API

The RADTwitter API currently returns information about tweets. If you want more functionality added, please [Open an issue!](https://github.com/Radiants-DAO/BetterTwitFix/issues)

The following fields are returned:
```js
{
    "date": "Wed Oct 05 18:40:30 +0000 2022", // Date the tweet was posted
    "date_epoch": 1664995230, // Epoch date the tweet was posted
    "hashtags": ["so","cool"], // Array of hashtags in the tweet (without the actual hashtag)
    "likes": 21664, // the amount of likes the tweet has
    "mediaURLs": [ // A url for any media in the tweet (videos, gifs, images)
        "https://video.twimg.com/tweet_video/FeU5fh1XkA0vDAE.mp4",
        "https://pbs.twimg.com/media/FeU5fhPXkCoZXZB.jpg"
    ],
    "media_extended": [ // More detailed information about media
        { // image:
            "altText": "picture of Kermit doing a one legged stand on a bicycle seat riding through the park", // Alt text for the image or video, usually typed in by the poster of the tweet
            "size": { // Width and Height of the original image
                "height": 1007,
                "width": 1179
            },
            "thumbnail_url": "https://pbs.twimg.com/media/FeU5fhPXkCoZXZB.jpg", // For images, this is the same as 'url'
            "type": "image", // type of the media, can be 'image' or 'video'
            "url": "https://pbs.twimg.com/media/FeU5fhPXkCoZXZB.jpg" // direct URL to the media
        },
        {
            "altText": "GIF of Laura Dern in Jurassic Park as Dr. Ellie Sattler taking off her sunglasses in shock", 
            "duration_millis": 0, // duration of the video in milliseconds. This can be 0 if Twitter doesn't provide it (i.e gifs)
            "size": { // Width and Height of the original video
                "height": 206,
                "width": 194
            },
            "thumbnail_url": "https://pbs.twimg.com/tweet_video_thumb/FeU5fh1XkA0vDAE.jpg", // Direct link to the video thumbnail
            "type": "video",
            "url": "https://video.twimg.com/tweet_video/FeU5fh1XkA0vDAE.mp4" // Direct MP4 link
        },
    ],
    "replies": 2911, // the amount of replies the tweet has
    "retweets": 3229, // the amount of retweets the tweet has
    "text": "whoa, it works\n\nnow everyone can mix GIFs, videos, and images in one Tweet, available on iOS and Android https://t.co/LVVolAQPZi", // the tweet's text
    "tweetID": "1577730467436138524", // ID of the tweet as a string
    "tweetURL": "https://twitter.com/Twitter/status/1577730467436138524", // a link to the tweet, without tracking parameters
    "user_name": "Twitter", // Name of the user who posted the tweet. This CAN have spaces, emojis, etc. as it's not the 'handle' of the user. A good example is "Nintendo of America"
    "user_screen_name": "Twitter" // The actual handle of the user, i.e "NintendoAmerica"
}
```

Additionally, you can add the `include_txt` parameter. Setting it to 'true' will include an additional media URL, a link to a .txt containing basic tweet information.
`include_txt` can also be set to `ifnomedia`, which will only add a link to the .txt if there is no media URLs in the tweet.