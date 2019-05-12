# XKCD Emailer

Expects a configuration file called `config.json` that looks like this:

```json
{
    "email_config": {
        "email": "email.name@gmail.com",
        "password": "super-secret-password",
        "name": "a nice name for this email"
    },
    "mailing_list": {
        "name": "blah-blah-mailing-list",
        "emails": [
            "timcook@gmail.com",
            "robert.jones@gmail.com"
        ]
    },
    "image_folder_path": "/tmp/xkcd-pics/",
    "max_pics": 10,
    "poll_interval_sec": 900
}
```

all of the shown fields are required. This program will also create a file
in it's working directory to keep track of it's current state (most recent comic sent
out) called `state.json`. Do not modify this file
