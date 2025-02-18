from slack_bolt.async_app import AsyncApp
from .models import Conversation, Message
from django.conf import settings
import openai
import logging
from django.db import transaction
from asgiref.sync import sync_to_async
from openai import OpenAI

logger = logging.getLogger(__name__)

slack_app = AsyncApp(token=settings.SLACK_BOT_TOKEN)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

class SlackBot:
    @staticmethod
    async def handle_mention(event, client):
        """
        Handles when the bot is mentioned in Slack.
        """
        try:
            channel_id = event["channel"]
            thread_ts = event.get("thread_ts", event["ts"])
            user_id = event["user"]
            message_text = event["text"]

            conversation = await SlackBot._get_or_create_conversation(
                channel_id, thread_ts
            )

            await SlackBot._store_message(
                conversation, message_text, user_id, is_bot=False
            )

            history = await SlackBot._get_conversation_history(conversation)
            
            response = await SlackBot._get_llm_response(message_text, history)

            await SlackBot._store_message(
                conversation, response, "BOT", is_bot=True
            )

            await client.chat_postMessage(
                channel=channel_id,
                text=response,
                thread_ts=thread_ts
            )

        except Exception as e:
            logger.error(f"Error handling mention: {str(e)}")
            try:
                await client.chat_postMessage(
                    channel=channel_id,
                    text="I apologize, but I encountered an error processing your request.",
                    thread_ts=thread_ts
                )
            except Exception as send_error:
                logger.error(f"Error sending error message: {str(send_error)}")

    @staticmethod
    @sync_to_async
    def _get_or_create_conversation(channel_id, thread_ts):
        """
        Retrieves existing conversation or creates a new one.
        Now properly handles async operations.
        """
        conversation, created = Conversation.objects.get_or_create(
            channel_id=channel_id,
            thread_ts=thread_ts
        )
        return conversation

    @staticmethod
    @sync_to_async
    def _store_message(conversation, content, user_id, is_bot=False):
        """
        Stores a new message in the database.
        Now properly handles async operations.
        """
        Message.objects.create(
            conversation=conversation,
            content=content,
            user_id=user_id,
            is_bot=is_bot
        )

    @staticmethod
    @sync_to_async
    def _get_conversation_history(conversation):
        """
        Retrieves the last 5 messages from the conversation.
        Now properly handles async operations.
        """
        messages = Message.objects.filter(
            conversation=conversation
        ).order_by('-timestamp')[:5]
        
        formatted_history = []
        for msg in reversed(list(messages)):
            role = "Assistant" if msg.is_bot else "User"
            formatted_history.append(f"{role}: {msg.content}")
            
        return "\n".join(formatted_history)

    @staticmethod
    async def _get_llm_response(current_message, history):
        """
        Gets response from OpenAI's API with conversation context.
        """
        try:
            system_prompt = """You are a helpful assistant in a Slack channel. 
            Respond concisely and professionally while maintaining context 
            from the conversation history."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Conversation history:\n{history}\n\nCurrent message: {current_message}"}
            ]

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