# Dungeon AI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) 
[TODO:] link API/usage documentation once it exists

Dungeon AI is a discord bot in progress for [Dungeon Crawler World](https://docs.google.com/document/d/14qkOLhg9iDBqj0Go3g6nb2oTCQBHuCwg3gOzaIzFHFE/edit?usp=drive_link). 
When it is completed, this file will contain information such as [TODO:]  an invite link for the bot.

The bot *requires* you to use a COPY of [this google sheet](https://docs.google.com/spreadsheets/d/13yPf5jfGhHrjWoUe-_2rG-L97UMAkk6MB7n-kecQvig/edit?usp=drivesdk) as your character sheet. Changes to the sheet's format *will* break the bot.

*(Dungeon AI does not make use of artificial intelligence/machine learning/etc.)*

# Data Collection and Handling
Dungeon AI stores the following information in order to function:
- Links to character sheets
- User IDs of those who have used the bot
- Guild IDs of guilds/servers where the bot has been invited and used by at least one user.
Users may delete their data at any time using the `/unlink` command.

Do not pass sensitive information to the bot or give it access to sensitive information through linked sheets, 
as it does not use anything more than the basic encryption used for handling Discord messages. 

If you have concerns about your data being stored on our server(s), please either submit an [issue](issues) telling us
how we can fix this or create your own instance by cloning this repository.

# Self-hosting
This bot has two components requires two authorizations: one for Discord and one for the Google API.
Google API key setup is optional, but skipping it will result in only being able to access public sheets and having no write priveleges.
This guide is not comprehensive, but provides enough information that those who are familiar with running servers should
be able to manage.

The bot looks for the following environment variables, which can be stored in a `.env` file:
- `DISCORD_TOKEN`: The token that Discord associates with the bot instance.
- `TEST_SERVER_ID`: The guild ID of a guild hosting the bot. This is, naturally, intended for command testing.

[TODO:] this section. can be basic. just need to tell people where to put auth keys & such.

# Bug Reports & Other Requests

There is no support server for this bot at present; GitHub [issues](issues) are the prefered method for external feature suggestions and 
bug reports.

# Contributing
Anyone can contribute to this project. When submitting pull requests, please provide relevant information, such as what the PR implements
and linking any related issues.
