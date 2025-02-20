# Slack Droid - AI-Powered Slack Assistant

A Slack chatbot that leverages OpenAI's API to provide intelligent responses while maintaining conversation context. The bot remembers the last 5 messages of any conversation, allowing it to provide contextually relevant responses.

## Features

- Responds to mentions in Slack channels to which it is added
- Maintains conversation history (last 5 messages)
- Handles multiple workspace installations

## Technical Overview

The application is built using:
- Django 4.2+ for the backend framework
- Slack Bolt for Python for Slack integration
- OpenAI API for generating intelligent responses
- SQLite for development (can be configured for PostgreSQL later if needed)
- Async handling for improved performance
- Have deployed the Django app in render

## How to use

 - To install the app to your workspace, navigate to this link - https://slack.com/oauth/v2/authorize?client_id=6641507106064.8465228072197&scope=app_mentions:read,calls:write,channels:history,chat:write&user_scope=
 - Click on 'Allow' to provide necessary permissions to the app
 - Invite to the slack channel, you would like to use
    /invite @Sangeetha's Droid
 - Interact with the bot (PS: The bot will respond while maintaining context of the last 5 messages in the conversation only)
    @Sangeetha's Droid Hello, how are you?
