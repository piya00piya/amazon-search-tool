import streamlit as st
from amazon_paapi import AmazonApi

# --- 画面のデザイン ---
st.title("🍔 Amazon オフ率＆ポイント検索ツール")

# ==========================================
# ▼ 鍵の取り出し（金庫から読み込む） ▼
# ==========================================
# GitHubに公開しても安全なように、st.secrets という機能を使います
try:
    KEY = st.secrets["KEY"]
    SECRET = st.secrets["SECRET"]
    TAG = st.secrets["TAG"]
    COUNTRY = 'JP'
except Exception:
    st.error("⚠️ まだStreamlit Cloudで「Secrets（秘密の鍵）」が設定されていません！")
    st.stop()

# 1. 検索ワード入力欄
keyword = st.text_input("探したいキーワード（例: セール, 在庫処分, 水, 家電）", "セール")

# カテゴリー選択
category = st.selectbox(
    "カテゴリーで絞り込む",
    (
        "All", "Electronics", "Computers", "Kitchen", "GroceryAndGourmetFood",
        "HealthPersonalCare", "Beauty", "Apparel", "Shoes",
        "Toys", "Hobbies", "VideoGames", "Books", "KindleStore"
    ),
    format_func=lambda x: {
        "All": "すべてのカテゴリー",
        "Electronics": "家電・カメラ",
        "Computers": "パソコン・周辺機器",
        "Kitchen": "ホーム＆キッチン",
        "GroceryAndGourmetFood": "食品・飲料",
        "HealthPersonalCare": "ドラッグストア",
        "Beauty": "ビューティー",
        "Apparel": "服・ファッション",
        "Shoes": "シューズ・バッグ",
        "Toys": "おもちゃ",
        "Hobbies": "ホビー",
        "VideoGames": "ゲーム",
        "Books": "本",
        "KindleStore": "Kindleストア"
    }.get(x, x)
)

# 2. 割引率スライダー
discount = st.slider("最低割引率（OFF率）", 0, 90, 0, 10)

# 3. 並び替えオプション
sort_option = st.radio(
    "並び替え",
    ("ポイント還元率順", "割引率順", "価格が安い順")
)

# --- 検索処理 ---
if st.button("検索開始"):
    try:
        amazon = AmazonApi(KEY, SECRET, TAG, COUNTRY)
        
        with st.spinner('Amazonからデータを取得中...'):
            # カテゴリー(search_index)を指定して検索！
            result = amazon.search_items(
                keywords=keyword,
                search_index=category,
                item_count=10
            )
            items = result.items
            
            product_list = []

            for item in items:
                try:
                    if item.offers and item.offers.listings:
                        price = item.offers.listings[0].price.amount
                        if item.offers.listings[0].price.savings:
                            list_price = price + item.offers.listings[0].price.savings.amount
                        else:
                            list_price = price
                        
                        points = 0
                        if item.offers and item.offers.listings[0].loyalty_points:
                            points = item.offers.listings[0].loyalty_points.points
                        
                        off_rate = 0
                        if list_price > price:
                            off_rate = int(((list_price - price) / list_price) * 100)
                        
                        point_rate = int((points / price) * 100)
                        
                        img_url = item.images.primary.medium.url if item.images and item.images.primary else ""

                        product_list.append({
                            "name": item.item_info.title.display_value,
                            "price": price,
                            "off_rate": off_rate,
                            "point_rate": point_rate,
                            "points": points,
                            "url": item.detail_page_url,
                            "image": img_url
                        })
                except:
                    continue

            # --- フィルタリング ---
            filtered_list = [p for p in product_list if p['off_rate'] >= discount]

            # --- 並び替え ---
            if sort_option == "ポイント還元率順":
                final_list = sorted(filtered_list, key=lambda x: x['point_rate'], reverse=True)
            elif sort_option == "割引率順":
                final_list = sorted(filtered_list, key=lambda x: x['off_rate'], reverse=True)
            else:
                final_list = sorted(filtered_list, key=lambda x: x['price']) # 安い順

            # --- 結果の表示 ---
            if len(final_list) == 0:
                st.warning("条件に合う商品が見つかりませんでした。割引率を下げたり、キーワードを変えてみてください。")
            else:
                st.success(f"{len(final_list)}件見つかりました！")
                
                for p in final_list:
                    with st.container():
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            if p['image']:
                                st.image(p['image'], width=100)
                        with col2:
                            st.markdown(f"### [{p['name']}]({p['url']})")
                            st.write(f"💰 価格: **¥{p['price']:,}**")
                            st.write(f"🔴 割引: **{p['off_rate']}% OFF**")
                            st.write(f"🟡 ポイント: **{p['points']}pt ({p['point_rate']}%)**")
                        
                        st.markdown("---")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
