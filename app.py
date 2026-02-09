import streamlit as st
import pandas as pd
from datetime import datetime
import os
import base64
from PIL import Image
import io

# ==========================================
# 1. 專案設定與樣式 (Cloud Bridge Style)
# ==========================================
st.set_page_config(
    page_title="雲橋工程 - 水保查核系統",
    page_icon="🏗️",
    layout="centered"
)

# 注入 CSS 樣式
st.markdown("""
    <style>
    /* 雲橋科技藍配色 #0056b3 */
    h1, h2, h3, .stHeader { color: #0056b3 !important; font-family: "Microsoft JhengHei", sans-serif; }
    
    /* 關鍵字強調 */
    .critical-tag { color: #dc3545; font-weight: bold; font-size: 0.8em; border: 1px solid #dc3545; padding: 2px 5px; border-radius: 4px; }
    
    /* 按鈕樣式 */
    .stButton>button {
        border-radius: 5px;
        font-weight: bold;
        border: 1px solid #0056b3;
        width: 100%;
    }
    
    /* 圖片說明輸入框優化 */
    .caption-input { margin-bottom: 20px; }
    
    /* 區塊優化 */
    .block-container { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. HTML 報告引擎 (轉 PDF 用)
# ==========================================
def generate_html_report(base_info, sections_data, photos, captions):
    # 照片轉 Base64 並結合說明
    img_html = ""
    if photos:
        img_html = "<div class='photo-grid'>"
        for idx, photo_file in enumerate(photos):
            photo_file.seek(0)
            img_bytes = photo_file.read()
            b64_str = base64.b64encode(img_bytes).decode()
            # 取得對應的說明文字
            caption_text = captions[idx] if idx < len(captions) else ""
            
            img_html += f"""
            <div class='photo-item'>
                <div class='photo-header'>照片 {idx+1}</div>
                <div class='photo-img-container'>
                    <img src="data:image/jpeg;base64,{b64_str}">
                </div>
                <div class='photo-caption'>{caption_text}</div>
            </div>
            """
        img_html += "</div>"
    else:
        img_html = "<p style='text-align:center; color:#999; padding:20px;'>本次無上傳照片</p>"

    # 產生表格內容
    rows_html = ""
    section_titles = [
        "一、裸露區域防護檢查", 
        "二、臨時滯洪沉砂池檢查", 
        "三、排水系統檢查", 
        "四、已完成設施檢查", 
        "五、安全與防災措施"
    ]
    
    for i, section in enumerate(sections_data):
        rows_html += f"""
        <tr class="section-header">
            <td colspan="2">{section_titles[i]}</td>
        </tr>
        """
        for label, result_data in section.items():
            result = result_data['result']
            standard = result_data['standard']
            status_cls = "fail" if result == "不符合" else "pass" if result == "符合" else "na"
            
            rows_html += f"""
            <tr>
                <td>
                    <div class='item-title'>{label}</div>
                    <div class='item-std'>{standard}</div>
                </td>
                <td class='{status_cls}'>{result}</td>
            </tr>
            """

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: "Microsoft JhengHei", "Heiti TC", sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; color: #333; }}
            .header {{ text-align: center; border-bottom: 3px solid #0056b3; padding-bottom: 15px; margin-bottom: 20px; }}
            h1 {{ color: #0056b3; margin: 0; font-size: 22px; }}
            h2 {{ color: #666; margin: 5px 0; font-size: 16px; font-weight: normal; }}
            
            .info-box {{ background: #f4f8fb; padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #dcebf7; }}
            .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
            
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 14px; }}
            th {{ background: #0056b3; color: white; padding: 8px; text-align: left; }}
            td {{ border-bottom: 1px solid #eee; padding: 10px 8px; vertical-align: top; }}
            
            .section-header td {{ background-color: #e9ecef; color: #0056b3; font-weight: bold; padding: 8px; border-top: 2px solid #ccc; }}
            .item-title {{ font-weight: bold; margin-bottom: 4px; }}
            .item-std {{ font-size: 12px; color: #666; }}
            
            .pass {{ color: #28a745; font-weight: bold; }}
            .fail {{ color: #dc3545; font-weight: bold; background: #fff5f5; }}
            .na {{ color: #999; }}
            
            /* 照片排版 */
            .photo-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; page-break-inside: avoid; }}
            .photo-item {{ border: 1px solid #ddd; background: white; break-inside: avoid; display: flex; flex-direction: column; }}
            .photo-header {{ background: #f0f0f0; padding: 5px; text-align: center; font-size: 12px; font-weight: bold; color: #555; border-bottom: 1px solid #ddd; }}
            .photo-img-container {{ padding: 5px; text-align: center; }}
            .photo-item img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; max-height: 250px; }}
            .photo-caption {{ padding: 8px; font-size: 13px; color: #333; background: #fff; border-top: 1px solid #eee; min-height: 40px; }}
            
            @media print {{
                body {{ padding: 0; }}
                .photo-grid {{ display: block; }}
                .photo-item {{ width: 48%; display: inline-block; vertical-align: top; margin-bottom: 15px; margin-right: 1%; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>水土保持處理與維護現場查核表</h1>
            <h2>{base_info['專案名稱']}</h2>
        </div>
        
        <div class="info-box">
            <div class="info-grid">
                <div><strong>檢查日期：</strong> {base_info['日期']}</div>
                <div><strong>檢查人員：</strong> {base_info['人員']}</div>
                <div><strong>天氣狀況：</strong> {base_info['天氣']}</div>
                <div><strong>施工狀態：</strong> {base_info['狀態']}</div>
            </div>
        </div>

        <table>
            <thead>
                <tr><th width="75%">檢查項目與標準</th><th width="25%">檢查結果</th></tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        
        <div style="page-break-before: always;"></div>
        <h3 style="color:#0056b3;">📷 現場照片紀錄</h3>
        {img_html}
    </body>
    </html>
    """
    return html

# ==========================================
# 3. 主介面邏輯
# ==========================================

st.title("🏗️ 現場重點查核自主檢查表")
st.markdown("---")

# 側邊欄
with st.sidebar:
    st.header("📋 專案資訊")
    
    # 新增：工程名稱輸入欄位 (放在日期上方)
    # 預設值保留方便使用，但使用者可修改
    project_name = st.text_input("工程名稱", value="金崙地熱電廠新建工程 (多良段449地號)")
    
    check_date = st.date_input("檢查日期", datetime.now())
    inspector = st.text_input("檢查人員", placeholder="請輸入姓名")
    weather = st.selectbox("天氣狀況", ["請選擇", "晴", "陰", "雨"])
    status = st.selectbox("施工狀態", ["請選擇", "施工中", "停工中"])
    
    st.markdown("---")
    # CSV 下載 (備份用)
    if os.path.exists("inspection_log.csv"):
        try:
            df_log = pd.read_csv("inspection_log.csv")
            csv = df_log.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 下載系統備份 (.csv)",
                csv,
                f"系統紀錄_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
        except:
            pass

# 檢查邏輯函數
def check_section(title, items_dict):
    st.markdown(f"### {title}")
    section_results = {}
    
    for label, standard in items_dict.items():
        is_critical = any(k in label for k in ["容量", "裸露", "土砂", "暢通"])
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{label}**")
            st.caption(f"標準：{standard}")
            if is_critical:
                st.markdown('<span class="critical-tag">⚠ 關鍵項目</span>', unsafe_allow_html=True)
        with col2:
            val = st.radio("結果", ["符合", "不符合", "無此項"], key=label, label_visibility="collapsed", horizontal=True)
            
        st.divider()
        section_results[label] = {
            'result': val,
            'standard': standard
        }
    return section_results

# 表單本體
with st.form("inspection_form"):
    
    s1 = check_section("一、裸露區域防護檢查", {
        "1. 裸露區域是否全面覆蓋防沖蝕網": "設計面積900m²，無大面積裸露",
        "2. 防沖蝕網是否牢固無破損": "無掀開、破損，固定良好",
        "3. 未施工區域是否有臨時防護": "表3-1未施工項目有適當防護"
    })
    
    s2 = check_section("二、臨時滯洪沉砂池檢查", {
        "1. #A臨時池容量是否足夠(340m³)": "尺寸：40m×5m×1.7m，無嚴重淤積",
        "2. #B臨時池容量是否足夠(172.4m³)": "尺寸：30.8m×7m×0.8m，無嚴重淤積",
        "3. 總容量是否大於257.25m³": "總容量512.4m³ > 257.25m³",
        "4. 池體結構是否穩固": "土堤無崩塌、滲漏現象"
    })
    
    s3 = check_section("三、排水系統檢查", {
        "1. U1、U2臨時土溝是否暢通": "無堵塞，能有效導排水",
        "2. 已完成排水設施是否功能正常": "集水井、排水管無堵塞",
        "3. L1防災土堤是否完好": "長20m×高0.8m，能有效截導"
    })

    s4 = check_section("四、已完成設施檢查", {
        "1. W1擋土牆狀況是否良好": "無龜裂、變形、滑動",
        "2. #1永久滯洪沉砂池功能正常": "池體完整，無嚴重淤積",
        "3. 集水井是否暢通": "T2、T3、T10等井無堵塞"
    })
    
    s5 = check_section("五、安全與防災措施", {
        "1. 是否有土砂外流至下游": "無土砂外流造成環境污染",
        "2. 是否備有防災土砂包": "適當地點儲放緊急材料",
        "3. 是否有安全警示設施": "施工區設有適當警示"
    })

    st.markdown("### 📷 現場照片紀錄")
    uploaded_files = st.file_uploader("上傳照片 (可多選)", accept_multiple_files=True, type=['jpg', 'png', 'jpeg'])
    
    captions = []
    if uploaded_files:
        st.info("請在下方輸入每張照片的說明：")
        cols = st.columns(2)
        for i, file in enumerate(uploaded_files):
            col = cols[i % 2]
            with col:
                st.image(file, use_container_width=True)
                cap = st.text_input(f"照片 {i+1} 說明", placeholder="例如：A池角落淤積...", key=f"caption_{file.name}_{i}")
                captions.append(cap)
                st.markdown("---")

    submitted = st.form_submit_button("💾 提交並生成報告", type="primary")

# 提交處理
if submitted:
    if not inspector:
        st.error("❌ 錯誤：請輸入檢查人員姓名")
    else:
        # 整理基本資料 (含工程名稱)
        base_info = {
            "專案名稱": project_name, # 使用使用者輸入的名稱
            "日期": check_date.strftime("%Y-%m-%d"),
            "人員": inspector,
            "天氣": weather,
            "狀態": status
        }
        
        sections_data = [s1, s2, s3, s4, s5]
        
        # 儲存 CSV
        flat_data = base_info.copy()
        for section in sections_data:
            for k, v in section.items():
                flat_data[k] = v['result']
        
        df_log = pd.DataFrame([flat_data])
        file_path = "inspection_log.csv"
        if not os.path.exists(file_path):
            df_log.to_csv(file_path, index=False, encoding='utf-8-sig')
        else:
            df_log.to_csv(file_path, mode='a', header=False, index=False, encoding='utf-8-sig')
            
        st.success("✅ 提交成功！請下載下方正式報告")
        
        html_report = generate_html_report(base_info, sections_data, uploaded_files, captions)
        
        st.download_button(
            label="📄 下載正式報告 (可轉 PDF)",
            data=html_report.encode('utf-8'),
            file_name=f"正式報告_{check_date}_{inspector}.html",
            mime="text/html",
            help="手機開啟後 -> 分享 -> 列印 -> 縮放即可存為 PDF。"
        )