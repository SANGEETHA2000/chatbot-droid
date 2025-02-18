from slack_bolt.async_app import AsyncApp
from .models import Conversation, Message
from django.conf import settings
import openai
import logging

logger = logging.getLogger(__name__)

slack_app = AsyncApp(token=settings.SLACK_BOT_TOKEN)

class SlackBot:
    @staticmethod
    async def handle_mention(event, say):
        """
        Handles when the bot is mentioned in Slack.
        Retrieves context, gets LLM response, and replies in the thread.
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

            await say(text=response, thread_ts=thread_ts)

        except Exception as e:
            logger.error(f"Error handling mention: {str(e)}")
            await say(
                text="I apologize, but I encountered an error processing your request.",
                thread_ts=thread_ts
            )

    @staticmethod
    async def _get_or_create_conversation(channel_id, thread_ts):
        """
        Retrieves existing conversation or creates a new one.
        """
        conversation, created = await Conversation.objects.aget_or_create(
            channel_id=channel_id,
            thread_ts=thread_ts
        )
        return conversation

    @staticmethod
    async def _store_message(conversation, content, user_id, is_bot=False):
        """
        Stores a new message in the database.
        """
        await Message.objects.acreate(
            conversation=conversation,
            content=content,
            user_id=user_id,
            is_bot=is_bot
        )

    @staticmethod
    async def _get_conversation_history(conversation):
        """
        Retrieves the last 5 messages from the conversation.
        Returns them formatted for the LLM.
        """
        messages = await Message.objects.filter(
            conversation=conversation
        ).order_by('-timestamp')[:5]
        
        formatted_history = []
        for msg in reversed(messages):
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

            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )

            return response.choices[0].message.content

        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return "I apologize, but I'm having trouble generating a response right now."
        except Exception as e:
            logger.error(f"Error getting LLM response: {str(e)}")
            return "I apologize, but I'm having trouble processing your request."

@slack_app.event("app_mention")
async def handle_mention(event, say):
    await SlackBot.handle_mention(event, say)