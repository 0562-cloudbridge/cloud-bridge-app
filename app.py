import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io
import requests
import base64
from PIL import Image as PILImage

# --- PDF 生成套件 ---
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm

# ==========================================
# 1. 系統初始化與字型設定 (使用 TTF 格式)
# ==========================================
st.set_page_config(page_title="雲橋工程 - 水保查核系統", page_icon="🏗️")

# 使用 JustFont 粉圓體 (TTF格式，ReportLab 支援度最好)
FONT_URL = "https://github.com/justfont/open-huninn-font/releases/download/v2.0/jf-openhuninn-2.0.ttf"
FONT_PATH = "jf-openhuninn-2.0.ttf"

@st.cache_resource
def load_font():
    """下載並註冊中文字型 (只執行一次)"""
    if not os.path.exists(FONT_PATH):
        try:
            # 顯示下載訊息
            print("正在下載中文字型 (TTF)...")
            response = requests.get(FONT_URL)
            with open(FONT_PATH, "wb") as f:
                f.write(response.content)
            print("字型下載成功！")
        except Exception as e:
            print(f"字型下載失敗: {e}")
            return False

    try:
        # 註冊字型 (ReportLab 核心步驟)
        pdfmetrics.registerFont(TTFont('ChineseFont', FONT_PATH))
        return True
    except Exception as e:
        print(f"字型註冊失敗: {e}")
        return False

# 啟動時執行
HAS_FONT = load_font()

# ==========================================
# 2. PDF 生成引擎
# ==========================================
def generate_pdf_report(base_info, sections_data, photos, captions):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    elements = []

    # 樣式設定
    # 如果字型下載失敗，退回 Helvetica (至少顯示英文)，成功則用 ChineseFont
    font_name = 'ChineseFont' if HAS_FONT else 'Helvetica'
    
    styles = getSampleStyleSheet()
    # 自定義樣式
    title_style = ParagraphStyle('Title_TC', parent=styles['Heading1'], fontName=font_name, fontSize=20, leading=24, alignment=1, textColor=colors.HexColor("#0056b3"))
    sub_style = ParagraphStyle('Sub_TC', parent=styles['Normal'], fontName=font_name, fontSize=12, leading=16, alignment=1, textColor=colors.gray)
    normal_style = ParagraphStyle('Normal_TC', parent=styles['Normal'], fontName=font_name, fontSize=10, leading=14)
    # 紅色不符合樣式
    fail_style = ParagraphStyle('Fail_TC', parent=styles['Normal'], fontName=font_name, fontSize=10, leading=14, textColor=colors.red)

    # --- A. 標題 ---
    elements.append(Paragraph("水土保持處理與維護現場查核表", title_style))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"專案名稱：{base_info['專案名稱']}", sub_style))
    elements.append(Spacer(1, 1*cm))

    # --- B. 基本資料表格 ---
    data_info = [
        [f"檢查日期：{base_info['日期']}", f"檢查人員：{base_info['人員']}"],
        [f"天氣狀況：{base_info['天氣']}", f"施工狀態：{base_info['狀態']}"]
    ]
    t_info = Table(data_info, colWidths=[9*cm, 9*cm])
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name), # 關鍵：設定字型
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 0.5*cm))

    # --- C. 檢查項目表格 ---
    # 表頭
    header = [Paragraph("檢查項目與標準", normal_style), Paragraph("結果", normal_style)]
    table_data = [header]
    
    section_titles = ["一、裸露區域防護", "二、臨時滯洪沉砂池", "三、排水系統", "四、已完成設施", "五、安全與防災"]
    
    for i, section in enumerate(sections_data):
        # 區塊標題
        # 使用 Paragraph 確保中文字型應用
        title_para = Paragraph(f"<b>{section_titles[i]}</b>", normal_style)
        table_data.append([title_para, ""])
        
        # 細項
        for label, result_data in section.items():
            result = result_data['result']
            standard = result_data['standard']
            
            # 內容格式 (項目 + 標準)
            item_content = Paragraph(f"<b>{label}</b><br/><font color='grey' size='9'>{standard}</font>", normal_style)
            
            # 結果格式 (紅色或黑色)
            if result == "不符合":
                res_content = Paragraph(f"<b>{result}</b>", fail_style)
            else:
                res_content = Paragraph(result, normal_style)
                
            table_data.append([item_content, res_content])

    # 建立主表格
    t_main = Table(table_data, colWidths=[14*cm, 4*cm])
    
    # 表格樣式
    main_style = [
        ('FONTNAME', (0, 0), (-1, -1), font_name), # 關鍵：設定全表字型
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor("#0056b3")), # 表頭背景
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white), # 表頭文字
        ('ALIGN', (1, 0), (1, -1), 'CENTER'), # 結果欄置中
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]
    
    # 合併區塊標題欄位 (讓它橫跨兩欄)
    current_row = 1
    for i in range(len(sections_data)):
        # 設定灰色背景
        main_style.append(('BACKGROUND', (0, current_row), (1, current_row), colors.lightgrey))
        # 合併欄位 (SPAN)
        main_style.append(('SPAN', (0, current_row), (1, current_row)))
        # 跳到下一個區塊的起始列
        current_row += len(sections_data[i]) + 1

    t_main.setStyle(TableStyle(main_style))
    elements.append(t_main)

    # --- D. 照片區 ---
    if photos:
        elements.append(PageBreak())
        elements.append(Paragraph("現場照片紀錄", title_style))
        elements.append(Spacer(1, 0.5*cm))

        photo_rows = []
        temp_row = []
        
        for idx, photo in enumerate(photos):
            try:
                img = PILImage.open(photo)
                # 轉 RGB 避免報錯
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                # 計算縮放
                img_width, img_height = img.size
                aspect = img_height / float(img_width)
                desired_width = 8*cm
                desired_height = desired_width * aspect
                
                # 限制高度
                if desired_height > 10*cm:
                    desired_height = 10*cm
                    desired_width = desired_height / aspect

                # 寫入 Buffer
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG')
                img_buffer.seek(0)
                rl_img = Image(img_buffer, width=desired_width, height=desired_height)
                
                # 說明文字
                caption_text = captions[idx] if idx < len(captions) else ""
                caption_para = Paragraph(f"照片 {idx+1}: {caption_text}", normal_style)
                
                # 組合單元格
                cell_content = [rl_img, Spacer(1, 0.2*cm), caption_para]
                temp_row.append(cell_content)
                
                # 兩張換行
                if len(temp_row) == 2:
                    photo_rows.append(temp_row)
                    temp_row = []
            except:
                pass # 忽略壞圖
        
        if temp_row:
            temp_row.append("") # 補空位
            photo_rows.append(temp_row)

        if photo_rows:
            t_photo = Table(photo_rows, colWidths=[9*cm, 9*cm])
            t_photo.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(t_photo)

    # 輸出 PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==========================================
# 3. HTML 備用引擎 (預覽用)
# ==========================================
def generate_html_report(base_info, sections_data, photos, captions):
    # 簡單版 HTML 生成
    img_html = ""
    if photos:
        img_html = "<div style='display:grid; grid-template-columns: 1fr 1fr; gap:10px;'>"
        for idx, photo in enumerate(photos):
            photo.seek(0)
            b64 = base64.b64encode(photo.read()).decode()
            cap = captions[idx] if idx < len(captions) else ""
            img_html += f"<div style='border:1px solid #ccc; padding:5px;'><img src='data:image/jpeg;base64,{b64}' style='width:100%'><div>{cap}</div></div>"
        img_html += "</div>"
            
    rows_html = ""
    titles = ["一、裸露防護", "二、滯洪池", "三、排水", "四、已完成", "五、安全"]
    for i, section in enumerate(sections_data):
        rows_html += f"<tr style='background:#eee'><td colspan='2'><b>{titles[i]}</b></td></tr>"
        for k, v in section.items():
            color = "red" if v['result'] == "不符合" else "black"
            rows_html += f"<tr><td>{k}<br><small>{v['standard']}</small></td><td style='color:{color}'>{v['result']}</td></tr>"

    return f"""
    <html><body style='font-family:sans-serif;'>
    <h2 style='text-align:center; color:#0056b3'>{base_info['專案名稱']}</h2>
    <p>日期：{base_info['日期']} | 人員：{base_info['人員']}</p>
    <table border='1' cellspacing='0' cellpadding='5' width='100%'>{rows_html}</table>
    <h3>照片紀錄</h3>{img_html}
    </body></html>
    """

# ==========================================
# 4. 主介面邏輯
# ==========================================
st.markdown("""
    <style>
    h1, h2, h3, .stHeader { color: #0056b3 !important; font-family: "Microsoft JhengHei", sans-serif; }
    .stButton>button { border-radius: 5px; font-weight: bold; border: 1px solid #0056b3; width: 100%; }
    .warning-box { background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #ffeeba; }
    </style>
""", unsafe_allow_html=True)

st.title("🏗️ 現場重點查核自主檢查表")

# 字型狀態檢查
if not HAS_FONT:
    st.error("⚠️ 中文字型下載失敗，PDF 可能會出現亂碼。請檢查網路或稍後再試。")

st.markdown("""
    <div class="warning-box">
        <b>📱 手機下載必讀：</b><br>
        請務必點擊右下角/右上角的 <b>指南針/地球圖示</b> (跳轉至 Safari/Chrome)，<br>
        否則 PDF 無法下載或顯示亂碼！
    </div>
""", unsafe_allow_html=True)

st.markdown("---")

with st.sidebar:
    st.header("📋 專案資訊")
    project_name = st.text_input("工程名稱", value="金崙地熱電廠新建工程 (多良段449地號)")
    check_date = st.date_input("檢查日期", datetime.now())
    inspector = st.text_input("檢查人員", placeholder="請輸入姓名")
    weather = st.selectbox("天氣狀況", ["請選擇", "晴", "陰", "雨"])
    status = st.selectbox("施工狀態", ["請選擇", "施工中", "停工中"])

def check_section(title, items_dict):
    st.markdown(f"### {title}")
    res = {}
    for label, standard in items_dict.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{label}**")
            st.caption(standard)
        with col2:
            val = st.radio("結果", ["符合", "不符合", "無此項"], key=label, label_visibility="collapsed", horizontal=True)
        st.divider()
        res[label] = {'result': val, 'standard': standard}
    return res

with st.form("inspection_form"):
    s1 = check_section("一、裸露區域防護檢查", {"1. 裸露區域是否全面覆蓋防沖蝕網": "設計面積900m²，無大面積裸露", "2. 防沖蝕網是否牢固無破損": "無掀開、破損，固定良好", "3. 未施工區域是否有臨時防護": "表3-1未施工項目有適當防護"})
    s2 = check_section("二、臨時滯洪沉砂池檢查", {"1. #A臨時池容量是否足夠(340m³)": "尺寸：40m×5m×1.7m，無嚴重淤積", "2. #B臨時池容量是否足夠(172.4m³)": "尺寸：30.8m×7m×0.8m，無嚴重淤積", "3. 總容量是否大於257.25m³": "總容量512.4m³ > 257.25m³", "4. 池體結構是否穩固": "土堤無崩塌、滲漏現象"})
    s3 = check_section("三、排水系統檢查", {"1. U1、U2臨時土溝是否暢通": "無堵塞，能有效導排水", "2. 已完成排水設施是否功能正常": "集水井、排水管無堵塞", "3. L1防災土堤是否完好": "長20m×高0.8m，能有效截導"})
    s4 = check_section("四、已完成設施檢查", {"1. W1擋土牆狀況是否良好": "無龜裂、變形、滑動", "2. #1永久滯洪沉砂池功能正常": "池體完整，無嚴重淤積", "3. 集水井是否暢通": "T2、T3、T10等井無堵塞"})
    s5 = check_section("五、安全與防災措施", {"1. 是否有土砂外流至下游": "無土砂外流造成環境污染", "2. 是否備有防災土砂包": "適當地點儲放緊急材料", "3. 是否有安全警示設施": "施工區設有適當警示"})

    st.markdown("### 📷 現場照片")
    uploaded_files = st.file_uploader("上傳照片", accept_multiple_files=True, type=['jpg', 'png', 'jpeg'])
    captions = []
    if uploaded_files:
        st.info("請輸入照片說明：")
        cols = st.columns(2)
        for i, file in enumerate(uploaded_files):
            with cols[i % 2]:
                st.image(file, use_container_width=True)
                captions.append(st.text_input(f"說明 {i+1}", key=f"cap_{i}"))

    submitted = st.form_submit_button("💾 提交查核", type="primary")

if submitted:
    if not inspector:
        st.error("❌ 請輸入檢查人員姓名")
    else:
        info = {"專案名稱": project_name, "日期": check_date.strftime("%Y-%m-%d"), "人員": inspector, "天氣": weather, "狀態": status}
        sects = [s1, s2, s3, s4, s5]
        
        st.success("✅ 資料已處理！")
        
        col1, col2 = st.columns(2)
        
        # 1. 優先下載 PDF
        with col1:
            try:
                # 再次確認字型
                if not HAS_FONT:
                    st.warning("⚠️ 系統無中文字型，PDF 將顯示亂碼。請使用右側網頁版備份。")
                
                pdf_data = generate_pdf_report(info, sects, uploaded_files, captions)
                st.download_button(
                    label="📥 下載 PDF (優先使用)",
                    data=pdf_data,
                    file_name=f"查核報告_{check_date}_{inspector}.pdf",
                    mime="application/pdf",
                    help="請務必使用 Safari/Chrome 開啟下載"
                )
            except Exception as e:
                st.error(f"PDF 錯誤: {e}")

        # 2. 備用網頁版
        with col2:
            html_data = generate_html_report(info, sects, uploaded_files, captions)
            st.download_button(
                label="📄 網頁版預覽 (備用)",
                data=html_data.encode('utf-8'),
                file_name=f"查核備份_{check_date}_{inspector}.html",
                mime="text/html",
                help="如果 PDF 下載失敗，請點此按鈕，並使用分享->列印功能"
            )
