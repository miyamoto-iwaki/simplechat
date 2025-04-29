# lambda/index.py
import json
import os
import urllib.request
import urllib.error
import urllib.parse
import ssl
import time

# Google Colab API URLを環境変数から取得
COLAB_API_URL = os.environ.get("COLAB_API_URL", "https://603d-34-125-30-45.ngrok-free.app")

def lambda_handler(event, context):
    try:
        # APIのURLが設定されていることを確認
        if not COLAB_API_URL:
            raise Exception("COLAB_API_URL環境変数が設定されていません")
        
        print("受信イベント:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得（既存コードを維持）
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"認証済みユーザー: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("メッセージ処理:", message)
        
        # 会話履歴からプロンプトを構築
        prompt = ""
        for msg in conversation_history:
            if msg["role"] == "user":
                prompt += f"ユーザー: {msg['content']}\n"
            elif msg["role"] == "assistant":
                prompt += f"アシスタント: {msg['content']}\n"
        
        # 現在のメッセージを追加
        prompt += f"ユーザー: {message}\nアシスタント: "
        
        # Colab API用のリクエストペイロードを構築
        request_payload = {
            "prompt": prompt,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        print(f"Colab API呼び出し: {COLAB_API_URL}/generate")
        
        # APIを呼び出し
        data = json.dumps(request_payload).encode('utf-8')
        req = urllib.request.Request(
            f"{COLAB_API_URL}/generate",
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Content-Length': str(len(data))
            },
            method='POST'
        )
        
        # SSL設定とリクエスト送信
        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=30, context=context) as response:
            response_data = response.read().decode('utf-8')
            api_response = json.loads(response_data)
        
        # アシスタントの応答を取得
        assistant_response = api_response.get("generated_text")
        if not assistant_response:
            raise Exception("モデルからの応答内容がありません")
        
        # レスポンスタイムを記録
        response_time = api_response.get("response_time", 0)
        print(f"モデルレスポンス生成時間: {response_time:.2f}秒")
        
        # アシスタントの応答を会話履歴に追加
        updated_history = conversation_history.copy()
        updated_history.append({
            "role": "user",
            "content": message
        })
        updated_history.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却（既存コードを維持）
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": updated_history
            })
        }
        
    except urllib.error.URLError as e:
        print(f"API接続エラー: {str(e)}")
        return {
            "statusCode": 502,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "success": False,
                "error": f"ColaのAPIに接続できません。URLを確認してください: {str(e)}"
            })
        }
    except Exception as error:
        print("エラー:", str(error))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
