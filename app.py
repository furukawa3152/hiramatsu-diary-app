import os
import json
import gspread
import pandas as pd
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
def auth(input_text,lineID):
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
        # authシートに登録がなければ、
        if len(input_text) < 4:
            return ("登録：平松太郎　のような形式で名前を入れてください。")
        else:
            username = input_text[3:]
            next_row = len(values_list) + 1
            sheet.update(f'A{next_row}', [[username]])
            sheet.update(f'B{next_row}', [[lineID]])
            return (f"{username}さんの登録が完了しました。\n日誌のユーザーIDは{lineID}です。")

    else:
        return(f"このIDは既に登録済みです。")

def write_diary(text,spread_sheet_key,user_id):
    scope = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
    #ダウンロードしたjsonファイル名をクレデンシャル変数に設定。
    credentials = Credentials.from_service_account_file("hiramatsudiaryproject-af40bbe80284.json", scopes=scope)

    gc = gspread.authorize(credentials)

    # スプレッドシート（ブック）を開く
    workbook = gc.open_by_key(SPREADSHEET_KEY)
    auth_sheet = workbook.worksheet('auth')
    # B列を検索して特定の文字列が存在するかチェック
    values_list = auth_sheet.col_values(2)  # B列のデータを取得
    target_string = user_id
    if target_string not in values_list:
        return "このIDは登録されていません。日記記入の前に、\n登録:平松太郎\nという形式で自分の名前を登録して下さい。"
    else:
        # シートを開く
        sheet = workbook.worksheet('シート1')
        # 7列目（userID）のデータを取得
        column_data = sheet.col_values(7)
        # userIDの文字列が列内に含まれている行があるかどうかを判定
        contains_id = any(user_id in cell for cell in column_data)
        #userIDが無い（初回入力）の場合の処理
        if not contains_id:
            counter = 1
        else:
            # スプレッドシートの全データを取得
            all_data = sheet.get_all_values()
            #現在のuserのデータのみに絞り込む
            filtered_data = [row for row in all_data if row[6] == user_id]
            # filtered_dataを1列目の値に基づいて昇順にソート
            sorted_filtered_data = sorted(filtered_data, key=lambda row: row[0])

            # 最終行の1列目の日付を取得
            last_date_str = sorted_filtered_data[-1][0]
            counter = int(sorted_filtered_data[-1][5])
            # 現在の日付と昨日の日付を取得
            two_hours_ago = datetime.now() - timedelta(hours=2)
            today = two_hours_ago.date()
            yesterday = today - timedelta(days=1)

            # 最終行の日付をdatetimeオブジェクトに変換
            last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()

            # 日付を比較して条件に応じた値を返す
            if last_date == today:
                counter = counter
            elif last_date == yesterday:
                counter += 1
            else:
                counter = 0+1

        #テキスト成形
        # newtext = text.replace(diary_keyword,"")
        entries = text.split('\n')
        result_dict = {}
        for entry in entries:
            # ':' でキーと値に分割
            key_value = entry.split(':')
            if len(key_value) == 2:
                key, value = key_value
                # 先頭と末尾の空白を削除
                result_dict[key.strip()] = value.strip()

        # 現在の日付を取得(2時までは前日として入力されるように２時間前で）
        two_hours_ago = datetime.now() - timedelta(hours=2)
        today_date = two_hours_ago.strftime('%Y-%m-%d')

        # 辞書から必要なデータを取得
        value_Efficacy = result_dict.get("本日のベスト", "")
        value_goal = result_dict.get("明日必ずやること", "")
        value_review = result_dict.get("今日をやり直せるなら", "")
        value_one_word = result_dict.get("今日の一言", "")
        #日誌記載の形式に則っていなければアラートを出す。
        if value_Efficacy == "" and value_goal == "" and value_review == "" and value_one_word =="":
            return "日記フォーマットを確認してね"
        else:
            # データをスプレッドシートに追加
            row_data = [today_date, value_Efficacy, value_goal, value_review, value_one_word,counter,user_id]
            sheet.append_row(row_data)
            ans = ""
            if value_Efficacy != "":
                ans += chatGPT_praise(value_Efficacy)
            if counter % 5 == 0:
                ans += f"\n{counter}日連続記録達成中です！！"
            if ans != "":
                return ans
            else:
                return "日誌への追記を完了しました。"
def chatGPT_praise(text):

    # ChatGPT_APIのエンドポイントURL
    url = "https://api.openai.com/v1/chat/completions"

    # APIキー
    api_key = os.environ["ChatGPT_API_KEY"]

    # リクエストヘッダー
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "gpt-4-turbo-preview",
        "messages": [{"role": "system", "content": "以下に与えられる発言を、「○○したのですね」という形式から始めて、発言者の自己肯定感が上がるように200文字以内で褒めて下さい。但し、世の中の倫理に反するような行いに対しては「そのようなことを褒めるわけにはいかないです」というようにいさめること"},
        {"role": "user", "content": text}]
        }
    # APIリクエストを送信
    response = requests.post(url, headers=headers, json=data)
    response_json = response.json()
    message_content = response_json["choices"][0]["message"]["content"]

    return message_content

def lambda_handler(event, context):
    try:
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
    #APIGatewayからのリクエストでないただの実行はこちらに流す。
    except KeyError:
        # 現在時刻の取得
        now = datetime.now()
        # 時間部分を2桁の文字列として取得（例: '08', '17'）
        hour_str = now.strftime('%H')
        #時間に応じた実行
        #8時台は昨日宣言した「明日やること」の一覧を投げる

        if hour_str == "08":
            scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            # ダウンロードしたjsonファイル名をクレデンシャル変数に設定。
            credentials = Credentials.from_service_account_file("hiramatsudiaryproject-af40bbe80284.json", scopes=scope)

            gc = gspread.authorize(credentials)

            # スプレッドシート（ブック）を開く
            workbook = gc.open_by_key(SPREADSHEET_KEY)

            # シートを開く
            sheet = workbook.worksheet('シート1')
            # 今日の日付を取得
            today = datetime.today() - timedelta(days=1)
            today = today.strftime('%Y-%m-%d')
            # データをDataFrameに読み込む
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            filtered_df = df[df['ymd'] == today]
            # 7列目'User_ID'の重複を排除 (ここでは列 'G' を参照)
            unique_col_seven = filtered_df['User_ID'].drop_duplicates().tolist()

            # 'User_ID'の各ユニークな値に対して、'明日必ずやる'の値を改行区切りで結合
            concatenated_values = []
            for value in unique_col_seven:
                concatenated = filtered_df[filtered_df['User_ID'] == value]['明日必ずやる'].str.cat(sep='\n')
                concatenated_values.append(concatenated)
            result_list = []
            for i in range(len(unique_col_seven)):
                result_list.append([unique_col_seven[i], concatenated_values[i]])
            for result in result_list:
                user_id = result[0]
                to_do = result[1]
                #送信出来ない場合はパス
                try:
                    if to_do != "":
                        tasks = "今日必ずやること！" + "\n" + to_do
                        messages = TextSendMessage(text=tasks)
                        line_bot_api.push_message(user_id, messages=messages)
                except Exception as e:
                    print(f"Error sending message: {e}")
                    pass

        if hour_str == "17":
            scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            # ダウンロードしたjsonファイル名をクレデンシャル変数に設定。
            credentials = Credentials.from_service_account_file("hiramatsudiaryproject-af40bbe80284.json", scopes=scope)

            gc = gspread.authorize(credentials)

            # スプレッドシート（ブック）を開く
            workbook = gc.open_by_key(SPREADSHEET_KEY)

            # シートを開く
            sheet = workbook.worksheet('transmission')
            transmission = sheet.acell('A1').value

            #user一覧を取得
            user_sheet = workbook.worksheet('シート1')
            values = user_sheet.col_values(7)[1:]  # col_values(4)はD列を意味し、[1:]は2行目以降を取得します
            # 重複を除いたリストを作成
            user_id_list = list(set(values))
            if transmission != "":
                for id in user_id_list:
                    messages = TextSendMessage(text=transmission)
                    line_bot_api.push_message(id, messages=messages)
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    input_text = event.message.text
    user_id = event.source.user_id

    #入力に応じて返す処理を分岐
    if input_text[:2] == "登録":
        return_words = auth(input_text, user_id)
    elif input_text == "ユーザーID確認" or input_text == "ユーザーid確認" or input_text == "ユーザーid" or input_text == "ユーザーID":
        return_words = f"あなたのuserIDは\n{user_id}\nです。他の人に教えることが無いように保管してください。"
    elif input_text == "説明":
        return_words = """日誌を、以下の４行構成で入力して下さい。一部項目のみの入力も可能です。日に何度でも入力できます。\n\n本日のベスト:\n明日必ずやること:\n今日をやり直せるなら:\n今日の一言:\n\n日誌は\nhttps://diaryviewer-hiramatst2023.streamlit.app\nで閲覧できます。\n「ユーザーID確認」と入力すると自分のIDが確認できます。
        """
    else:
        return_words = write_diary(input_text,SPREADSHEET_KEY,user_id)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=return_words)
    )