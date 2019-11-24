# Fish shop tgbot



This bot is up to sell you some fish, you can try to resist temptation at @smells_fish_bot in Telegram!



### How to install



Python3 should be already installed.



Then use `pip` (or `pip3`, if there is a conflict with Python2) to install dependencies:



```



pip install -r requirements.txt



```

You need to get yourself bot token here>[botFather](https://medium.com/shibinco/create-a-telegram-bot-using-botfather-and-get-the-api-token-900ba00e0f39). Also, you gonna need to make your own redis DB [Redis](https://redislabs.com/) and crate online shop with [Moltin](https://www.moltin.com/).


### Launch example



First, you need to set up enviroment variables as listed below, then launch app in command prompt.



```



python shop-bot.py



```

### Environment variables

```

REDIS_HOST

```

Host of your Redis DB.

```

REDIS_PORT

```

Port of your Redis DB.

```

REDIS_PASWORD

```

Redis DB password

```

TG_TOKEN

```

TG bot token

```

MOLTIN_CLIENT_ID

```

clien id from moltin




### Project Goals



The code is written for educational purposes on online-course for web-developers [dvmn.org](https://dvmn.org/).
