import discord
from discord.ui import View, Button
import os
import aiohttp
import json
import asyncio
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
import traceback
from pymongo import MongoClient

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
FLOWISE_API_URL = os.getenv('FLOWISE_API_URL')
FLOWISE_API_KEY = os.getenv('FLOWISE_API_KEY')
MAKE_WEBHOOK_URL = os.getenv('MAKE_WEBHOOK_URL')
TRADE_SUMMARY_WEBHOOK_URL = os.getenv('TRADE_SUMMARY_WEBHOOK_URL')
MONGO_URI = os.getenv('MONGO_URI')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client['flowisedb1']
collection = db['discordbot']

app = Flask('')


@app.route('/')
def home():
    return "I'm alive"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    server = Thread(target=run)
    server.start()


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

IDLE_TIMEOUT = timedelta(minutes=15)
SUBSCRIBER_CACHE_TIMEOUT = timedelta(hours=24)
user_last_interaction = {}
subscriber_cache = {}
chat_history_cache = {}
trade_summary_cache = {}
first_message_in_session = {}  # New dictionary to track first messages


class TradeSummaryButton(View):

    def __init__(self):
        super().__init__()
        self.add_item(
            Button(label="Get Trade Summary",
                   style=discord.ButtonStyle.primary,
                   custom_id="trade_summary_button"))
        # New button to show latest trades
       # self.add_item(
            #Button(label="Show My Latest Trades",
                  #style=discord.ButtonStyle.secondary,
                  # custom_id="show_latest_trades"))

# New function to fetch latest trades
async def fetch_latest_trades(user_id, user_name):
    payload = {"discord_id": user_id, "discord_name": user_name}
    result = await make_request(payload, 'get_latest_trades', TRADE_SUMMARY_WEBHOOK_URL)
    return result.get('trades', []) if result else []

async def make_request(payload, action, url=MAKE_WEBHOOK_URL):
    headers = {"Content-Type": "application/json"}
    payload['action'] = action
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload,
                                    headers=headers) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type',
                                                        '').lower()
                    if 'application/json' in content_type:
                        return await response.json()
                    else:
                        return await response.text()
                else:
                    logger.error(
                        f"Failed webhook request. URL: {url}, Action: {action}, Status: {response.status}, Response: {await response.text()}"
                    )
                    return None
    except Exception as e:
        logger.exception(
            f"Error in webhook request. URL: {url}, Action: {action}")
        return None


async def is_active_subscriber(user):
    user_id = str(user.id)
    current_time = datetime.utcnow()
    if user_id in subscriber_cache:
        cached_status, cache_time = subscriber_cache[user_id]
        if current_time - cache_time < SUBSCRIBER_CACHE_TIMEOUT:
            return cached_status
    payload = {
        "discord_id": user_id,
        "discord_name": user.name,
        "discord_discriminator": user.discriminator
    }
    result = await make_request(payload, 'check_subscriber')
    if result is None:
        logger.error("Failed to check subscriber status")
        return False
    is_subscriber = result.get('is_subscriber', False)
    subscriber_cache[user_id] = (is_subscriber, current_time)
    return is_subscriber


async def log_chat_history(user_id, user_name, message_content,
                           response_content):
    current_time = datetime.utcnow()
    if user_id not in chat_history_cache:
        chat_history_cache[user_id] = []

    chat_log_entry = {
        "message": message_content,
        "response": response_content,
        "timestamp": current_time.isoformat()
    }
    chat_history_cache[user_id].append(chat_log_entry)

    # Store chat history to MongoDB
    try:
        collection.update_one({"user_id": user_id},
                              {"$push": {
                                  "chat_logs": chat_log_entry
                              }},
                              upsert=True)
        logger.info(f"Chat history for {user_id} logged to MongoDB.")
    except Exception as e:
        logger.error(
            f"Failed to log chat history for {user_id} to MongoDB: {str(e)}")

    # Sending chat history to Make.com (as per existing logic)
    if len(chat_history_cache[user_id]) >= 5 or (
            not chat_history_cache[user_id] or current_time -
            datetime.fromisoformat(chat_history_cache[user_id][0]['timestamp'])
            > timedelta(minutes=5)):
        payload = {
            "discord_id": user_id,
            "discord_name": user_name,
            "chat_logs": chat_history_cache[user_id]
        }
        result = await make_request(payload, 'log_chat')
        if result is None:
            logger.error("Failed to log chat history to Make.com")
        else:
            chat_history_cache[user_id] = [
            ]  # Clear the local cache once it's logged


async def fetch_chat_history(user_id):
    if user_id in chat_history_cache and chat_history_cache[user_id]:
        return chat_history_cache[user_id]
    payload = {"discord_id": user_id}
    result = await make_request(payload, 'fetch_chat_history')
    if result is None:
        logger.error("Failed to fetch chat history")
        return []
    chat_history = result.get('chat_history', [])
    for entry in chat_history:
        entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])
    chat_history_cache[user_id] = chat_history
    return chat_history


async def fetch_trade_summary(user_id, session_id):
    if session_id in trade_summary_cache:
        return trade_summary_cache[session_id]

    payload = {"discord_id": user_id}
    result = await make_request(payload, 'get_trade_summary',
                                TRADE_SUMMARY_WEBHOOK_URL)

    if result:
        trade_summary_cache[session_id] = result
        return result

    return None


async def append_trade_summary_to_mongodb(user_id, trade_summary):
    try:
        filter_query = {'sessionId': user_id}
        new_message = {
            "data": {
                "content": trade_summary,
                "additional_kwargs": {},
                "response_metadata": {}
            },
            "type": "ai"
        }
        update_query = {'$push': {'messages': new_message}}
        result = collection.update_one(filter_query, update_query, upsert=True)
        logger.info(
            f"Appended trade summary to MongoDB for user {user_id}. Matched: {result.matched_count}, Modified: {result.modified_count}, Upserted: {result.upserted_id is not None}"
        )
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        logger.error(
            f"Error appending trade summary to MongoDB for user {user_id}: {str(e)}"
        )
        return False


async def fetch_from_flowise(session, payload, headers):
    try:
        async with session.post(FLOWISE_API_URL, json=payload,
                                headers=headers) as response:
            logger.debug(f"Flowise response status: {response.status}")
            if response.status == 200:
                return await response.json()
            else:
                response_text = await response.text()
                logger.error(
                    f"Error: Received non-200 status code: {response.status}. Response: {response_text}"
                )
                return None
    except Exception as e:
        logger.exception("Exception occurred while fetching from Flowise")
        return None


def should_trigger_make_workflow(user_id):
    last_interaction = user_last_interaction.get(user_id)
    if last_interaction is None:
        return True
    return datetime.utcnow() - last_interaction > IDLE_TIMEOUT


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if client.user in message.mentions:
        # If the bot is mentioned in a server, send a DM to the user
        user = message.author
        dm_channel = await user.create_dm()
        await dm_channel.send(
            "You mentioned me! Let's continue this conversation here.")

        # You can add additional logic here if needed, such as logging the mention
        return

    if isinstance(message.channel, discord.DMChannel):
        user = message.author
        user_id = str(user.id)
        session_id = user_id  # Use user_id as the session ID

        try:
            if not await is_active_subscriber(user):
                await message.channel.send(
                    "I'm sorry but you don't have access to this chatbot. To subscribe, please contact our Admin."
                )
                return

            current_time = datetime.utcnow()
            is_new_session = should_trigger_make_workflow(user_id)
            user_last_interaction[user_id] = current_time

            if is_new_session:
                first_message_in_session[user_id] = True

            async with message.channel.typing():
                chat_history = await fetch_chat_history(user_id)

                payload = {
                    "question": message.content,
                    "overrideConfig": {
                        "sessionId": session_id
                    }
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {FLOWISE_API_KEY}"
                }

                async with aiohttp.ClientSession() as session:
                    flowise_response = await fetch_from_flowise(
                        session, payload, headers)
                    if flowise_response:
                        chatbot_reply = flowise_response.get(
                            "text") or flowise_response.get(
                                "answer") or "I couldn't generate a response."

                        if len(chatbot_reply) >= 2000:
                            chatbot_reply = chatbot_reply[:1997] + "..."

                        if first_message_in_session.get(user_id, False):
                            view = TradeSummaryButton()
                            await message.channel.send(chatbot_reply,
                                                       view=view)
                            first_message_in_session[user_id] = False
                        else:
                            await message.channel.send(chatbot_reply)

                        await log_chat_history(user_id, user.name,
                                               message.content, chatbot_reply)
                    else:
                        logger.error(
                            f"Flowise response was None. Payload: {payload}")
                        await message.channel.send(
                            "Sorry, there was an error processing your message. Please try again later."
                        )

        except Exception as e:
            logger.exception(f"Unexpected error in on_message: {str(e)}")
            await message.channel.send(
                "An unexpected error occurred. Please try again later.")


@client.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        user_id = str(interaction.user.id)
        user_name = interaction.user.name

        if interaction.data['custom_id'] == "trade_summary_button":
            await interaction.response.defer(thinking=True)

            payload = {"discord_id": user_id, "discord_name": user_name}
            result = await make_request(payload, 'get_trade_summary',
                                        TRADE_SUMMARY_WEBHOOK_URL)

            if result:
                session_id = user_id
                trade_summary_cache[session_id] = result
                await append_trade_summary_to_mongodb(user_id, result)

                messages = []
                current_message = "Here's your latest trade journal summary:\n\n"
                for line in result.split('\n'):
                    if len(current_message) + len(line) + 1 > 2000:
                        messages.append(current_message)
                        current_message = line + '\n'
                    else:
                        current_message += line + '\n'
                if current_message:
                    messages.append(current_message)

                for i, message in enumerate(messages):
                    if i == 0:
                        await interaction.followup.send(message)
                    else:
                        await interaction.followup.send(message)
            else:
                await interaction.followup.send(
                    "Sorry, I couldn't retrieve your trade summary at this time. Please try again later."
                )

        # Handle the "Show My Latest Trades" button
        #elif interaction.data['custom_id'] == "show_latest_trades":
            #await interaction.response.defer(thinking=True)

            #trades = await fetch_latest_trades(user_id, user_name)

            #if trades:
               # view = View()
               # for trade in trades:
                   # view.add_item(
                        #Button(label=f"Trade: {trade['id']}",
                         #      style=discord.ButtonStyle.secondary,
                           #    custom_id=f"view_trade_{trade['id']}"))
#
               # await interaction.followup.send(
                    #"Here are your latest trades:", view=view)
          #  else:
             #   await interaction.followup.send(
             #       "Sorry, I couldn't retrieve your latest trades at this time."
          #      )

        # Handle dynamic trade buttons
      #  elif interaction.data['custom_id'].startswith("view_trade_"):
           # trade_id = interaction.data['custom_id'].replace("view_trade_", "")
         #   await interaction.response.defer(thinking=True)

           # payload = {"discord_id": user_id, "trade_id": trade_id}
           # result = await make_request(payload, 'get_trade_details',
          #                             TRADE_SUMMARY_WEBHOOK_URL)
#
           # if result:
           #     trade_details = f"Details for Trade {trade_id}:\n{result}"
           #     await interaction.followup.send(trade_details)
          #  else:
          #      await interaction.followup.send(
          #          "Sorry, I couldn't retrieve the details for this trade."
           #     )


@client.event
async def on_ready():
    logger.info(f'We have logged in as {client.user}')
    client.loop.create_task(clear_subscriber_cache_periodically())


async def clear_subscriber_cache_periodically():
    while True:
        await asyncio.sleep(86400)  # 24 hours
        subscriber_cache.clear()
        first_message_in_session.clear()  # Clear first message flags
        logger.info("Cleared subscriber cache and first message flags")


if __name__ == "__main__":
    keep_alive()  # This starts the Flask app in a separate thread
    client.run(TOKEN)  