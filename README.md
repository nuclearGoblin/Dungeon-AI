# Dungeon AI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) 

Dungeon AI is a discord bot in progress for [Dungeon Crawler World](https://docs.google.com/document/d/14qkOLhg9iDBqj0Go3g6nb2oTCQBHuCwg3gOzaIzFHFE/edit?usp=drive_link). 

The bot *requires* you to use a COPY of [this google sheet](https://docs.google.com/spreadsheets/d/13yPf5jfGhHrjWoUe-_2rG-L97UMAkk6MB7n-kecQvig/edit?usp=drivesdk) as your character sheet. Changes to the sheet's format *will* break the bot.

See the [wiki](https://github.com/nuclearGoblin/Dungeon-AI/wiki) for information about commands.

*(Dungeon AI does not make use of artificial intelligence/machine learning/etc.)*

# Data Collection and Handling
Dungeon AI stores the following information in order to function:
- Links to character sheets
- User IDs of those who have used the bot
- Guild IDs of guilds/servers where the bot has been invited and used by at least one user.
Users may delete their data at any time using the `/unlink` command.

Do not use this bot for any sheet handling other than playing DCW, and especially do not pass sensitive information to the bot or give it access to sensitive information through linked sheets, 
as data is not encrypted.

If you have concerns about your data being stored on our server(s), please self-host instead (see instructions below).

# Self-hosting
Self-hosting is encouraged! Data is not shared across hosts, although there is nothing stopping you from
linking the same character sheet to multiple hosts. 
This guide is not comprehensive, but provides enough information that those who are familiar with running servers should
be able to manage.

We encourage you to clone this git repository (`git clone git@github.com:nuclearGoblin/Dungeon-AI`) instead of downloading the zip,
as it will allow you to receive updates via the `main` branch using `git pull`.

This bot has two API components and therefore requires two authorizations: one for Discord and one for Google.
Google API key setup is optional, but skipping it will result in only being able to access public sheets and having no write priveleges.
Creating a Discord application through Discord's developer portal is required for self-hosting.

The bot looks for several environment variables, which can be stored in a file named `.env`. 
An example file [`sample.env`](sample.env) is provided to explain all environment variables that the bot checks for.

You will need to install Python as well as the packages specified in [`requirements.txt`](requirements.txt): 
`pip install -r requirements.txt`.  
Once the environment has correctly been set up, the bot can be run using `python bot.py`.

# Bug Reports & Other Requests

There is no support server for this bot at present; GitHub [issues](issues) are the prefered method for external feature suggestions and 
bug reports.

# Contributing

Anyone can contribute to this project. When submitting pull requests, please provide relevant information, such as what the PR implements
and linking any related issues.
