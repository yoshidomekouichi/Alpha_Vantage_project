#!/usr/bin/env python3
import requests
import json
import sys

# APIキーとスペースID
api_key = "gb_api_aNOhttKfusboE3nGHXZe48Q11RkduMGL0KRhO9zD"
space_id = "2U9HnYdITqVucgTAeqO1"  # URLから取得したスペースID
organization_id = "ENlKRYh2HENXQxpiGeKs"  # URLから取得した組織ID

# ヘッダー設定
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

def get_space_info():
    """スペース情報を取得"""
    print("スペース情報を取得中...")
    try:
        response = requests.get(
            f"https://api.gitbook.com/v1/spaces/{space_id}",
            headers=headers
        )
        response.raise_for_status()
        print("スペース情報の取得に成功しました。")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"エラー: スペース情報の取得に失敗しました。 {e}")
        if hasattr(e, 'response') and e.response:
            print(f"レスポンス: {e.response.text}")
        sys.exit(1)

def setup_github_sync():
    """GitHubとの同期を設定"""
    print("GitHubとの同期を設定中...")
    sync_data = {
        "provider": "github",
        "repository": "yoshidomekouichi/data_engineering_tutorial",
        "branch": "main",
        "rootPath": "Training"
    }
    
    try:
        response = requests.post(
            f"https://api.gitbook.com/v1/spaces/{space_id}/integrations/git",
            headers=headers,
            json=sync_data
        )
        response.raise_for_status()
        print("GitHubとの同期設定に成功しました。")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"エラー: GitHubとの同期設定に失敗しました。 {e}")
        if hasattr(e, 'response') and e.response:
            print(f"レスポンス: {e.response.text}")
        sys.exit(1)

def list_integrations():
    """連携の一覧を取得"""
    print("連携の一覧を取得中...")
    try:
        response = requests.get(
            f"https://api.gitbook.com/v1/spaces/{space_id}/integrations",
            headers=headers
        )
        response.raise_for_status()
        print("連携の一覧取得に成功しました。")
        result = response.json()
        print(f"レスポンス形式: {type(result)}")
        print(f"レスポンス内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result
    except requests.exceptions.RequestException as e:
        print(f"エラー: 連携の一覧取得に失敗しました。 {e}")
        if hasattr(e, 'response') and e.response:
            print(f"レスポンス: {e.response.text}")
        sys.exit(1)

def get_content_structure():
    """コンテンツ構造を取得"""
    print("コンテンツ構造を取得中...")
    try:
        response = requests.get(
            f"https://api.gitbook.com/v1/spaces/{space_id}/content",
            headers=headers
        )
        response.raise_for_status()
        print("コンテンツ構造の取得に成功しました。")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"エラー: コンテンツ構造の取得に失敗しました。 {e}")
        if hasattr(e, 'response') and e.response:
            print(f"レスポンス: {e.response.text}")
        sys.exit(1)

def main():
    """メイン関数"""
    print("GitBook APIを使用して設定を行います...")
    
    # スペース情報を取得
    space_info = get_space_info()
    print(f"スペース名: {space_info.get('title', 'Unknown')}")
    
    # 既存の連携を確認
    integrations = list_integrations()
    print(f"既存の連携数: {len(integrations)}")
    
    # GitHubとの連携がまだない場合は設定
    # APIレスポンスの形式に応じて処理を変更
    git_integration_exists = False
    if isinstance(integrations, list):
        git_integration_exists = any(isinstance(i, dict) and i.get('type') == 'git' for i in integrations)
    elif isinstance(integrations, dict) and 'items' in integrations:
        git_integration_exists = any(isinstance(i, dict) and i.get('type') == 'git' for i in integrations.get('items', []))
    
    if not git_integration_exists:
        print("GitHubとの連携が見つかりません。新しく設定します。")
        sync_result = setup_github_sync()
        print(f"同期設定結果: {json.dumps(sync_result, indent=2, ensure_ascii=False)}")
    else:
        print("GitHubとの連携がすでに存在します。")
    
    # コンテンツ構造を取得
    content = get_content_structure()
    print(f"コンテンツ構造: {json.dumps(content, indent=2, ensure_ascii=False)}")
    
    print("設定が完了しました。GitBookでコンテンツを確認してください。")
    print(f"GitBook URL: https://app.gitbook.com/o/{organization_id}/s/{space_id}")

if __name__ == "__main__":
    main()
