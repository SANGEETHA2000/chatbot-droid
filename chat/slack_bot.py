import uuid
from slack_bolt.async_app import AsyncApp
from .models import Conversation, Message, WorkspaceToken
from django.conf import settings
import openai
import logging
from django.db import transaction
from asgiref.sync import sync_to_async
from openai import OpenAI
from django.utils import timezone

logger = logging.getLogger(__name__)

slack_app = AsyncApp(token=settings.SLACK_BOT_TOKEN)
client = OpenAI(api_key=settings.OPENAI_API_KEY)

class SlackBot:
    @staticmethod
    async def handle_mention(event, client):
        """
        Main handler for Slack mentions. Processes messages, maintains conversation history,
        and generates responses using the OpenAI API.
        """
        try:
            team_id = event.get("team")
            print(f"Received event for team: {team_id}")
            
            if not team_id:
                logger.error("Team ID not found in event data. Full event:", event)
                return

            workspace_token = await SlackBot._get_workspace_token(team_id)
            if not workspace_token:
                logger.error(f"No token found for team {team_id}")
                return
            
            workspace_client = AsyncApp(token=workspace_token)

            channel_id = event["channel"]
            thread_ts = event.get("thread_ts", event["ts"])
            user_id = event["user"]
            message_text = event["text"]
            event_ts = event["event_ts"]          
            slack_message_id = f"slack_{event_ts}"

            conversation = await SlackBot._get_or_create_conversation(
                channel_id, thread_ts
            )

            if await SlackBot._message_exists(slack_message_id):
                logger.info(f"Message {slack_message_id} already exists, skipping")
                return

            await SlackBot._store_message(
                conversation=conversation,
                content=message_text,
                user_id=user_id,
                is_bot=False,
                message_id=slack_message_id,
                processed=False
            )

            history = await SlackBot._get_conversation_history(conversation)
            
            formatted_messages = [
                {"role": "system", "content": """You are a helpful assistant in a Slack channel.
                    Maintain context from the conversation history and be consistent with previous responses.
                    If you're referring to information from earlier in the conversation, mention that you're 
                    recalling it from our previous discussion."""}
            ]

            for msg in history:
                role = "assistant" if msg.is_bot else "user"
                formatted_messages.append({
                    "role": role,
                    "content": msg.content
                })

            formatted_messages.append({
                "role": "user",
                "content": message_text
            })

            response = await SlackBot._get_llm_response(formatted_messages)

            bot_message_id = f"bot_{event_ts}_{uuid.uuid4().hex[:8]}"

            await SlackBot._store_message(
                conversation=conversation,
                content=response,
                user_id="BOT",
                is_bot=True,
                message_id=bot_message_id,
                processed=True
            )

            await workspace_client.client.chat_postMessage(
                channel=channel_id,
                text=response,
                thread_ts=thread_ts
            )

            await SlackBot._mark_message_processed(conversation, slack_message_id)

        except Exception as e:
            logger.error(f"Error in handle_mention: {str(e)}")
            try:
                if workspace_client:
                    await workspace_client.client.chat_postMessage(
                        channel=channel_id,
                        text="I apologize, but I encountered an error processing your request.",
                        thread_ts=thread_ts
                    )
            except Exception as send_error:
                logger.error(f"Error sending error message: {str(send_error)}")

    @staticmethod
    @sync_to_async
    def _get_workspace_token(team_id):
        """
        Retrieves the bot token for a specific workspace.
        """
        try:
            workspace = WorkspaceToken.objects.get(team_id=team_id)
            return workspace.bot_token
        except WorkspaceToken.DoesNotExist:
            return None

    @staticmethod
    @sync_to_async
    def _message_exists(message_id):
        """
        Check if a message with this ID already exists in any conversation.
        This prevents duplicate processing across all conversations.
        """
        return Message.objects.filter(message_id=message_id).exists()

    @staticmethod
    @sync_to_async
    def _get_or_create_conversation(channel_id, thread_ts):
        """
        Retrieves existing conversation or creates a new one.
        """
        with transaction.atomic():
            conversation, created = Conversation.objects.get_or_create(
                channel_id=channel_id,
                thread_ts=thread_ts
            )
            return conversation

    @staticmethod
    @sync_to_async
    def _store_message(conversation, content, user_id, is_bot=False, message_id=None, processed=False):
        """
        Stores a message with transaction safety.
        """
        with transaction.atomic():
            Message.objects.create(
                conversation=conversation,
                content=content,
                user_id=user_id,
                is_bot=is_bot,
                message_id=message_id,
                processed=processed,
                timestamp=timezone.now()
            )

    @staticmethod
    @sync_to_async
    def _mark_message_processed(conversation, message_id):
        """
        Marks a message as processed using a safe update operation.
        """
        with transaction.atomic():
            Message.objects.filter(
                conversation=conversation,
                message_id=message_id
            ).update(processed=True)

    @staticmethod
    @sync_to_async
    def _get_conversation_history(conversation):
        """
        Retrieves the last 5 messages from the conversation in chronological order.
        """
        messages = Message.objects.filter(
            conversation=conversation
        ).order_by('-timestamp')[:5]
        
        return list(reversed(messages))

    @staticmethod
    async def _get_llm_response(messages):
        """
        Gets response from OpenAI's API.
        """
        try:
            response = await sync_to_async(client.chat.completions.create)(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content

        except Exception as e:
            error_message = str(e)
            logger.error(f"OpenAI API error: {error_message}")
            
            if "insufficient_quota" in error_message:
                return "I apologize, but I'm currently unable to process requests due to API limitations. Please contact the system administrator to resolve this issue."
            else:
                return "I apologize, but I'm having trouble generating a response right now. Please try again."

@slack_app.event("app_mention")
async def handle_mention(event, say):
    await SlackBot.handle_mention(event, say)