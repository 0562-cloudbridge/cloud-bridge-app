import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io
import requests
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
# 1. 系統初始化與字型設定 (核心關鍵)
# ==========================================
st.set_page_config(page_title="雲橋工程 - 水保查核系統", page_icon="🏗️")

# 設定中文字型檔案路徑
FONT_PATH = "NotoSansTC-Regular.ttf"
FONT_URL = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
# 備用字型連結 (若上方失敗)
FONT_URL_BACKUP = "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"

def download_font():
    """檢查並下載中文字型 (解決雲端亂碼問題)"""
    if not os.path.exists(FONT_PATH):
        with st.spinner("正在下載中文字型 (第一次啟動需時較久)..."):
            try:
                # 這裡為了展示，使用一個較小的相容字型或是直接從系統抓
                # 為了穩定性，我們下載 Google Noto Sans
                response = requests.get(FONT_URL_BACKUP) # 使用備用連結
                if response.status_code != 200:
                    response = requests.get(FONT_URL)
                
                with open(FONT_PATH, "wb") as f:
                    f.write(response.content)
                st.success("字型下載完成！")
            except:
                st.warning("⚠️ 字型下載失敗，PDF 可能會出現亂碼。")

# 註冊字型給 ReportLab 使用
download_font()
try:
    pdfmetrics.registerFont(TTFont('ChineseFont', FONT_PATH))
    HAS_FONT = True
except:
    HAS_FONT = False

# ==========================================
# 2. PDF 生成引擎 (專業 TAF 風格)
# ==========================================
def generate_pdf_report(base_info, sections_data, photos, captions):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    elements = []

    # --- 定義樣式 ---
    styles = getSampleStyleSheet()
    # 標題樣式
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontName='ChineseFont' if HAS_FONT else 'Helvetica', fontSize=18, leading=22, alignment=1, textColor=colors.HexColor("#0056b3"))
    # 子標題樣式
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName='ChineseFont' if HAS_FONT else 'Helvetica', fontSize=12, leading=16, alignment=1, textColor=colors.gray)
    # 表格內容樣式
    normal_style = ParagraphStyle('Normal_TC', parent=styles['Normal'], fontName='ChineseFont' if HAS_FONT else 'Helvetica', fontSize=10, leading=14)
    # 檢查結果(紅字)
    fail_style = ParagraphStyle('Fail_TC', parent=styles['Normal'], fontName='ChineseFont' if HAS_FONT else 'Helvetica', fontSize=10, leading=14, textColor=colors.red, fontName_bold='ChineseFont')

    # --- A. 標題區 ---
    elements.append(Paragraph("水土保持處理與維護現場查核表", title_style))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"專案名稱：{base_info['專案名稱']}", subtitle_style))
    elements.append(Spacer(1, 1*cm))

    # --- B. 基本資料表 ---
    data_info = [
        [f"檢查日期：{base_info['日期']}", f"檢查人員：{base_info['人員']}"],
        [f"天氣狀況：{base_info['天氣']}", f"施工狀態：{base_info['狀態']}"]
    ]
    t_info = Table(data_info, colWidths=[9*cm, 9*cm])
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'ChineseFont' if HAS_FONT else 'Helvetica'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 0.5*cm))

    # --- C. 檢查項目表 ---
    # 表頭
    table_data = [[Paragraph("檢查項目與標準", normal_style), "結果"]]
    
    section_titles = ["一、裸露區域防護", "二、臨時滯洪沉砂池", "三、排水系統", "四、已完成設施", "五、安全與防災"]
    
    for i, section in enumerate(sections_data):
        # 區塊標題列
        table_data.append([Paragraph(f"<b>{section_titles[i]}</b>", normal_style), ""])
        # 項目列
        for label, result_data in section.items():
            result = result_data['result']
            standard = result_data['standard']
            
            # 組合項目文字
            item_text = f"<b>{label}</b><br/><font color='grey' size='9'>{standard}</font>"
            
            # 結果欄位
            res_cell = result
            if result == "不符合":
                res_cell = Paragraph(f"<b>{result}</b>", fail_style)
            else:
                res_cell = Paragraph(result, normal_style)
                
            table_data.append([Paragraph(item_text, normal_style), res_cell])

    # 建立主表格
    t_main = Table(table_data, colWidths=[14*cm, 4*cm])
    # 設定表格樣式 (Tech Blue 風格)
    main_style = [
        ('FONTNAME', (0, 0), (-1, -1), 'ChineseFont' if HAS_FONT else 'Helvetica'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor("#0056b3")), # 表頭背景
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white), # 表頭文字
        ('ALIGN', (1, 0), (1, -1), 'CENTER'), # 結果欄置中
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]
    
    # 針對區塊標題列做特殊處理 (灰色背景, 合併欄位)
    current_row = 1
    for i in range(len(sections_data)):
        main_style.append(('BACKGROUND', (0, current_row), (1, current_row), colors.lightgrey))
        main_style.append(('SPAN', (0, current_row), (1, current_row)))
        current_row += len(sections_data[i]) + 1 # 跳過該區塊的項目數+標題本身

    t_main.setStyle(TableStyle(main_style))
    elements.append(t_main)

    # --- D. 照片區 ---
    if photos:
        elements.append(PageBreak()) # 強制換頁
        elements.append(Paragraph("現場照片紀錄", title_style))
        elements.append(Spacer(1, 0.5*cm))

        photo_rows = []
        temp_row = []
        
        for idx, photo in enumerate(photos):
            # 處理圖片
            img = PILImage.open(photo)
            # 保持比例縮放
            img_width, img_height = img.size
            aspect = img_height / float(img_width)
            desired_width = 8*cm
            desired_height = desired_width * aspect
            
            # 限制最大高度
            if desired_height > 10*cm:
                desired_height = 10*cm
                desired_width = desired_height / aspect

            # 轉換為 ReportLab Image
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='JPEG')
            img_buffer.seek(0)
            rl_img = Image(img_buffer, width=desired_width, height=desired_height)
            
            # 說明文字
            caption_text = captions[idx] if idx < len(captions) else ""
            caption_para = Paragraph(f"照片 {idx+1}: {caption_text}", normal_style)
            
            # 放入單元格
            cell_content = [rl_img, Spacer(1, 0.2*cm), caption_para]
            temp_row.append(cell_content)
            
            # 每兩張換一行
            if len(temp_row) == 2:
                photo_rows.append(temp_row)
                temp_row = []
        
        if temp_row: # 補齊最後一行
            temp_row.append("") # 補一個空位
            photo_rows.append(temp_row)

        # 建立照片表格 (隱形框線)
        t_photo = Table(photo_rows, colWidths=[9*cm, 9*cm])
        t_photo.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(t_photo)

    # 產生 PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==========================================
# 3. 介面邏輯 (Streamlit)
# ==========================================
# 注入 CSS 樣式
st.markdown("""
    <style>
    h1, h2, h3, .stHeader { color: #0056b3 !important; font-family: "Microsoft JhengHei", sans-serif; }
    .critical-tag { color: #dc3545; font-weight: bold; font-size: 0.8em; border: 1px solid #dc3545; padding: 2px 5px; border-radius: 4px; }
    .stButton>button { border-radius: 5px; font-weight: bold; border: 1px solid #0056b3; width: 100%; }
    .block-container { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

st.title("🏗️ 現場重點查核自主檢查表")
st.markdown("---")

# 側邊欄
with st.sidebar:
    st.header("📋 專案資訊")
    project_name = st.text_input("工程名稱", value="金崙地熱電廠新建工程 (多良段449地號)")
    check_date = st.date_input("檢查日期", datetime.now())
    inspector = st.text_input("檢查人員", placeholder="請輸入姓名")
    weather = st.selectbox("天氣狀況", ["請選擇", "晴", "陰", "雨"])
    status = st.selectbox("施工狀態", ["請選擇", "施工中", "停工中"])

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
            if is_critical: st.markdown('<span class="critical-tag">⚠ 關鍵項目</span>', unsafe_allow_html=True)
        with col2:
            val = st.radio("結果", ["符合", "不符合", "無此項"], key=label, label_visibility="collapsed", horizontal=True)
        st.divider()
        section_results[label] = {'result': val, 'standard': standard}
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
    uploaded_files = st.file_uploader("上傳照片", accept_multiple_files=True, type=['jpg', 'png', 'jpeg'])
    
    captions = []
    if uploaded_files:
        st.info("請輸入照片說明：")
        cols = st.columns(2)
        for i, file in enumerate(uploaded_files):
            with cols[i % 2]:
                st.image(file, use_container_width=True)
                captions.append(st.text_input(f"說明 {i+1}", key=f"cap_{i}"))

    submitted = st.form_submit_button("💾 提交並生成 PDF", type="primary")

# 提交處理
if submitted:
    if not inspector:
        st.error("❌ 錯誤：請輸入檢查人員姓名")
    else:
        # 準備資料
        base_info = {"專案名稱": project_name, "日期": check_date.strftime("%Y-%m-%d"), "人員": inspector, "天氣": weather, "狀態": status}
        sections_data = [s1, s2, s3, s4, s5]
        
        # 1. 產生 PDF (直接生成檔案流)
        with st.spinner("📄 正在生成 PDF 報告..."):
            pdf_file = generate_pdf_report(base_info, sections_data, uploaded_files, captions)
        
        st.success("✅ 報告生成成功！請點擊下方按鈕直接下載 PDF。")
        
        # 2. 下載按鈕 (直接是 .pdf 檔)
        st.download_button(
            label="📥 下載 PDF 報告 (可直接傳 LINE)",
            data=pdf_file,
            file_name=f"查核報告_{check_date}_{inspector}.pdf",
            mime="application/pdf"
        )
