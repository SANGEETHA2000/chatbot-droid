from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
from .slack_bot import slack_app

@csrf_exempt
async def slack_events(request):
    """
    Handles incoming Slack events and verifications.
    """
    if request.method == "POST":
        body = json.loads(request.body)
        
        if body.get("type") == "url_verification":
            return JsonResponse({"challenge": body["challenge"]})
            
        if body.get("type") == "event_callback":
            await slack_app.process(body)
            return HttpResponse(status=200)
            
    return HttpResponse(status=400)