import os
import json
import gspread
from datetime import datetime , timedelta
from google.oauth2.service_account import Credentials
import requests
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]
# LINE Botの設定情報
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
SPREADSHEET_KEY = os.environ["SPREADSHEET_KEY"]
def auth(username,lineID):
    scope = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
    #ダウンロードしたjsonファイル名をクレデンシャル変数に設定。
    credentials = Credentials.from_service_account_file("hiramatsudiaryproject-af40bbe80284.json", scopes=scope)

    gc = gspread.authorize(credentials)

    # スプレッドシート（ブック）を開く
    workbook = gc.open_by_key(SPREADSHEET_KEY)

    # シートを開く
    sheet = workbook.worksheet('auth')
    # B列を検索して特定の文字列が存在するかチェック
    values_list = sheet.col_values(2)  # B列のデータを取得
    target_string = lineID
    if target_string not in values_list:
        # 特定の文字列が存在しない場合、A列に "AAA"、B列に "BBB" を書き込む
        next_row = len(values_list) + 1
        sheet.update(f'A{next_row}', [[username]])
        sheet.update(f'B{next_row}', [[lineID]])
        return (f"{username}さんの登録が完了しました。")
    else:
        return(f"{username}さんは既に登録済みです。")

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
    input_text = event.message.text
    user_id = event.source.user_id

    #入力に応じて返す処理を分岐
    if input_text == "ユーザーID確認" or input_text == "ユーザーid確認" or input_text == "ユーザーid" or input_text == "ユーザーID":
        return_words = f"あなたのuserIDは\n{user_id}\nです。他の人に教えることが無いように保管してください。"

    elif input_text[:2] == "登録" or input_text[:2] == "登録":
        user_name = input_text[3:]
        return_words = auth(user_name, user_id)
    elif input_text == "説明":
        return_words = """以下のフォーマットで入力して下さい。一部項目のみの入力も可能ですが、必ず改行はして下さい。日に何度でも入力可能です。\n\n本日のベスト:\n明日必ずやること:\n今日をやり直せるなら:\n今日の一言:\n\n日誌は\nhttps://diaryviewer-hiramatst2023.streamlit.app\nで閲覧できます。\n「ユーザーID確認」と入力すると自分のIDが確認できます。
        """
    else:
        return_words = write_diary(input_text,SPREADSHEET_KEY,user_id)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=return_words)
    )