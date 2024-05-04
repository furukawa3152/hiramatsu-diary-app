import os
import json
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]
# LINE Botの設定情報
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

def lambda_handler(event, context):
    # API Gatewayからのリクエストを処理
    signature = event['headers'].get('x-line-signature')
    body = event['body']

    # ハンドラーに処理を委譲
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid signature. Please check your channel access token/channel secret.')
        }
    except LineBotApiError as e:
        return {
            'statusCode': 500,
            'body': json.dumps('Internal server error')
        }

    return {
        'statusCode': 200,
        'body': json.dumps('OK')
    }

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # オウム返し
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text)
    )