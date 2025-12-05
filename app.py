import streamlit as st
from amazon_paapi import AmazonApi
import time

# --- 画面のデザイン ---
st.title("🍔 Amazon オフ率＆ポイント検索ツール")

# ==========================================
# ▼ 鍵の取り出し（金庫から読み込む） ▼
# ==========================================
try:
    KEY = st.secrets["KEY"]
    SECRET = st.secrets["SECRET"]
    TAG = st.secrets["TAG"]
    COUNTRY = 'JP'
except Exception:
    st.error("⚠️ まだStreamlit Cloudで「Secrets（秘密の鍵）」が設定されていません！")
    st.stop()

# 1. 検索ワード入力欄
keyword = st.text_input("探したいキーワード（空欄のままなら、全商品から探します）", "")

# ▼▼▼ 裏技スイッチ ▼▼▼
prioritize_points = st.checkbox("🔥 ポイント還元が高い商品を優先的に探す（裏技）")

# 2. カテゴリー選択
# ▼▼▼ 修正：カテゴリーを増やし、HomeとKitchenを分けました ▼▼▼
category = st.selectbox(
    "カテゴリーで絞り込む（※「すべて」だと割引指定が効きません！）",
    (
        "All",
        "Electronics", "Computers", "Appliances", # 家電系
        "Home", "Kitchen", "DIY", "PetSupplies", # 生活系
        "GroceryAndGourmetFood", "HealthPersonalCare", "Beauty", # 日用品
        "Apparel", "Shoes", "Jewelry", "Watches", # ファッション
        "Toys", "Hobbies", "VideoGames", "Books", "KindleStore" # 趣味
    ),
    format_func=lambda x: {
        "All": "すべてのカテゴリー",
        "Electronics": "家電・カメラ",
        "Computers": "パソコン・周辺機器",
        "Appliances": "大型家電",
        "Home": "ホーム＆キッチン（家具・インテリア）", # ← これを追加！
        "Kitchen": "キッチン用品・食器",
        "DIY": "DIY・工具・ガーデン",
        "PetSupplies": "ペット用品",
        "GroceryAndGourmetFood": "食品・飲料",
        "HealthPersonalCare": "ドラッグストア",
        "Beauty": "ビューティー",
        "Apparel": "服・ファッション",
        "Shoes": "シューズ・バッグ",
        "Jewelry": "ジュエリー",
        "Watches": "腕時計",
        "Toys": "おもちゃ",
        "Hobbies": "ホビー",
        "VideoGames": "ゲーム",
        "Books": "本",
        "KindleStore": "Kindleストア"
    }.get(x, x)
)

# 3. Amazonからの取得順序
sort_by = st.selectbox(
    "Amazonからの取得順序（仕入れ）",
    ("Featured", "Price:LowToHigh", "Price:HighToLow", "NewestArrivals", "AvgCustomerReviews"),
    format_func=lambda x: {
        "Featured": "おすすめ順（通常はコレ）",
        "Price:LowToHigh": "価格が安い順",
        "Price:HighToLow": "価格が高い順",
        "NewestArrivals": "最新商品順",
        "AvgCustomerReviews": "レビュー評価順"
    }.get(x, x)
)

# 4. 割引率スライダー
discount = st.slider("最低割引率（OFF率）", 0, 90, 0, 10)

# 5. 表示の並び替え
st.markdown("---")
st.subheader("👀 結果の並び替え")
sort_option = st.radio(
    "どの順番で表示しますか？",
    ("ポイント還元率が高い順", "割引率が高い順", "価格が安い順"),
    horizontal=True
)

# --- 検索処理 ---
if st.button("検索開始"):
    try:
        amazon = AmazonApi(KEY, SECRET, TAG, COUNTRY)
        
        # キーワード設定
        if not keyword:
            if prioritize_points:
                final_keyword = "Amazonポイント"
                st.info("💡 ポイント重視モード：キーワード「Amazonポイント」で検索します")
            else:
                final_keyword = "-"
                st.info("💡 キーワード指定なし：全商品から探します")
        else:
            if prioritize_points:
                final_keyword = f"{keyword} Amazonポイント"
                st.info(f"💡 ポイント重視モード：「{final_keyword}」で検索します")
            else:
                final_keyword = keyword
        
        product_list = []
        
        with st.spinner('Amazonからデータを収集中... (最大50件)'):
            
            search_params = {
                "keywords": final_keyword,
                "search_index": category,
                "item_count": 10,
                "sort_by": sort_by
            }

            # 割引率指定のルール（All以外かつ1%以上なら指定）
            if discount > 0:
                if category == "All":
                    st.warning("⚠️ 注意：「すべてのカテゴリー」では割引率での絞り込みができません。")
                else:
                    search_params["min_saving_percent"] = discount

            for page in range(1, 6):
                try:
                    search_params["item_page"] = page
                    result = amazon.search_items(**search_params)
                    items = result.items
                    
                    if not items:
                        break

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
                                asin = item.asin

                                product_list.append({
                                    "name": item.item_info.title.display_value,
                                    "price": price,
                                    "off_rate": off_rate,
                                    "point_rate": point_rate,
                                    "points": points,
                                    "url": item.detail_page_url,
                                    "image": img_url,
                                    "asin": asin
                                })
                        except:
                            continue
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    break

            # --- フィルタリング ---
            filtered_list = [p for p in product_list if p['off_rate'] >= discount]

            # --- 並び替え ---
            if sort_option == "ポイント還元率が高い順":
                final_list = sorted(filtered_list, key=lambda x: x['point_rate'], reverse=True)
            elif sort_option == "割引率が高い順":
                final_list = sorted(filtered_list, key=lambda x: x['off_rate'], reverse=True)
            else:
                final_list = sorted(filtered_list, key=lambda x: x['price']) # 安い順

            # --- 結果の表示 ---
            if len(final_list) == 0:
                st.warning("条件に合う商品が見つかりませんでした。")
            else:
                st.success(f"{len(final_list)}件見つかりました！")
                
                for i, p in enumerate(final_list):
                    
                    if i == 0: rank_icon = "🥇 1位"
                    elif i == 1: rank_icon = "🥈 2位"
                    elif i == 2: rank_icon = "🥉 3位"
                    else: rank_icon = f"{i+1}位"

                    with st.container():
                        st.markdown(f"### {rank_icon} : {p['name']}")
                        
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            if p['image']:
                                st.image(p['image'], width=100)
                        with col2:
                            st.write(f"💰 価格: **¥{p['price']:,}**")
                            
                            if sort_option == "ポイント還元率が高い順":
                                st.write(f"🟡 ポイント: **{p['points']}pt ({p['point_rate']}%)**")
                                st.write(f"🔴 割引: {p['off_rate']}% OFF")
                            else:
                                st.write(f"🔴 割引: **{p['off_rate']}% OFF**")
                                st.write(f"🟡 ポイント: {p['points']}pt ({p['point_rate']}%)")
                            
                            st.markdown(f"[🔗 Amazonで見る]({p['url']})")
                            
                            keepa_graph = f"https://graph.keepa.com/pricehistory.png?asin={p['asin']}&domain=co.jp"
                            with st.expander("📊 価格推移グラフを見る"):
                                st.image(keepa_graph, use_column_width=True)
                        
                        st.markdown("---")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
