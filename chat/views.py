from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import requests
from .slack_bot import slack_app, SlackBot
import logging
from .models import WorkspaceToken
from asgiref.sync import sync_to_async
import aiohttp

logger = logging.getLogger(__name__)

@csrf_exempt
async def slack_events(request):
    """
    Handles incoming Slack events and verifications.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
        
        if body.get("type") == "url_verification":
            return JsonResponse({"challenge": body["challenge"]})
            
        if body.get("type") == "event_callback":
            event = body.get("event", {})
            
            if event.get("type") == "app_mention":
                await SlackBot.handle_mention(event, slack_app.client)
                return HttpResponse(status=200)
                
        logger.warning(f"Received unknown event type: {body.get('type')}")
        return HttpResponse(status=200)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse request body: {str(e)}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Error processing slack event: {str(e)}")
        return HttpResponse(status=500)

async def slack_oauth_redirect(request):
    """Handle the OAuth redirect from Slack"""
    code = request.GET.get('code')
    
    if not code:
        return HttpResponse("Error: No code provided", status=400)
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://slack.com/api/oauth.v2.access',
                data={
                    'client_id': settings.SLACK_CLIENT_ID,
                    'client_secret': settings.SLACK_CLIENT_SECRET,
                    'code': code
                }
            ) as response:
                data = await response.json()
                
                if not data.get('ok'):
                    return HttpResponse(f"Error during OAuth: {data.get('error')}", status=400)
                
                await sync_to_async(WorkspaceToken.objects.update_or_create)(
                    team_id=data['team']['id'],
                    defaults={'bot_token': data['access_token']}
                )
                
                return HttpResponse("Successfully installed the app! You can close this window and start using the bot in your Slack workspace.")
        
    except Exception as e:
        return HttpResponse(f"Error during OAuth: {str(e)}", status=500)