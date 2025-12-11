import io
import textwrap

import pandas as pd
import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import streamlit as st

# ---------------- CONFIGURAÇÃO DE PÁGINA ----------------
st.set_page_config(
    page_title="QR Codes - Estoque Restaurante",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 16px;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .section-title {
        font-size: 20px;
        font-weight: 600;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .stButton>button {
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">Gerador de QR Codes para Estoque</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Envie uma planilha com <b>código</b> e <b>produto</b>, gere os QR codes e baixe um PDF pronto para impressão.</div>',
    unsafe_allow_html=True,
)

# ---------------- ESTADO DA SESSÃO ----------------
if "df" not in st.session_state:
    st.session_state.df = None
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

# ---------------- FUNÇÕES AUXILIARES ----------------
def gerar_imagem_qr(codigo: str, produto: str, fonte_tamanho: int = 12) -> Image.Image:
    # Gera QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(str(codigo))
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Nome do produto
    texto_produto = produto.strip() or "(sem nome)"
    linhas = textwrap.wrap(texto_produto, width=25)

    # Fonte
    try:
        fonte = ImageFont.truetype("arial.ttf", fonte_tamanho)
    except Exception:
        fonte = ImageFont.load_default()

    draw_dummy = ImageDraw.Draw(qr_img)

    line_heights = []
    max_text_width = 0
    for linha in linhas:
        bbox = draw_dummy.textbbox((0, 0), linha, font=fonte)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        max_text_width = max(max_text_width, w)
        line_heights.append(h)

    bbox_codigo = draw_dummy.textbbox((0, 0), str(codigo), font=fonte)
    codigo_w = bbox_codigo[2] - bbox_codigo[0]
    codigo_h = bbox_codigo[3] - bbox_codigo[1]

    texto_altura_total = sum(line_heights) + codigo_h + 10

    largura_final = max(qr_img.width, max_text_width, codigo_w) + 20
    altura_final = qr_img.height + texto_altura_total + 20

    img_final = Image.new("RGB", (largura_final, altura_final), "white")
    draw = ImageDraw.Draw(img_final)

    # Texto do produto
    y = 5
    for i, linha in enumerate(linhas):
        bbox = draw.textbbox((0, 0), linha, font=fonte)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (largura_final - w) // 2
        draw.text((x, y), linha, font=fonte, fill="black")
        y += h

    # Código
    x_codigo = (largura_final - codigo_w) // 2
    draw.text((x_codigo, y + 2), str(codigo), font=fonte, fill="black")
    y_qr = y + codigo_h + 10

    # QR centralizado
    x_qr = (largura_final - qr_img.width) // 2
    img_final.paste(qr_img, (x_qr, y_qr))

    return img_final


def gerar_pdf(produtos_df: pd.DataFrame, itens_por_linha: int, fonte_tamanho: int) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4

    margem_x = 40
    margem_y = 40
    espacamento_x = 20
    espacamento_y = 20

    largura_disponivel = page_width - 2 * margem_x - (itens_por_linha - 1) * espacamento_x
    largura_item = largura_disponivel / itens_por_linha

    x_atual = margem_x
    y_atual = page_height - margem_y
    col_atual = 0

    for _, row in produtos_df.iterrows():
        codigo = str(row["codigo"])
        produto = str(row["produto"])

        img = gerar_imagem_qr(codigo, produto, fonte_tamanho=fonte_tamanho)

        fator = largura_item / img.width
        nova_largura = largura_item
        nova_altura = img.height * fator
        img_resized = img.resize((int(nova_largura), int(nova_altura)))

        img_buffer = io.BytesIO()
        img_resized.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        if col_atual >= itens_por_linha:
            col_atual = 0
            x_atual = margem_x
            y_atual -= nova_altura + espacamento_y

        if y_atual - nova_altura < margem_y:
            c.showPage()
            x_atual = margem_x
            y_atual = page_height - margem_y

        # reportlab precisa de um filename ou ImageReader; aqui convertemos o buffer
        from reportlab.lib.utils import ImageReader
        img_reader = ImageReader(img_buffer)

        c.drawImage(
            img_reader,
            x_atual,
            y_atual - nova_altura,
            width=nova_largura,
            height=nova_altura,
        )

        x_atual += nova_largura + espacamento_x
        col_atual += 1

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# ---------------- LAYOUT PRINCIPAL ----------------
col_esq, col_dir = st.columns([1.2, 1])

with col_esq:
    st.markdown('<div class="section-title">1. Planilha de produtos</div>', unsafe_allow_html=True)

    modelo_df = pd.DataFrame({"codigo": [], "produto": []})
    modelo_csv = modelo_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Baixar modelo (codigo,produto)",
        data=modelo_csv,
        file_name="modelo_produtos_qr.csv",
        mime="text/csv",
        use_container_width=True,
    )

    uploaded_file = st.file_uploader(
        "Envie um arquivo .csv com as colunas: codigo,produto",
        type=["csv"],
    )

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, dtype=str)
        except Exception:
            st.error("Erro ao ler o arquivo. Verifique se é um CSV válido em UTF-8.")
            st.stop()

        df.columns = [c.strip().lower() for c in df.columns]

        if not {"codigo", "produto"}.issubset(set(df.columns)):
            st.error("O arquivo precisa ter as colunas: codigo e produto.")
            st.stop()

        df = df[["codigo", "produto"]].fillna("")
        st.session_state.df = df

        st.write("Pré-visualização dos dados:")
        st.dataframe(df.head(15), use_container_width=True)

    st.markdown('<div class="section-title">2. Configurações de layout</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        itens_por_linha = st.selectbox(
            "Códigos por linha no PDF",
            options=[2, 3, 4],
            index=1,
        )
    with col_b:
        fonte_tamanho = st.slider("Tamanho da fonte (nome/código)", 10, 20, 12)

    st.markdown('<div class="section-title">3. Ações</div>', unsafe_allow_html=True)

    bt_col1, bt_col2, bt_col3 = st.columns(3)
    gerar_pdf_click = False
    limpar_click = False

    with bt_col1:
        gerar_click = st.button("⚙️ Gerar QR Codes", use_container_width=True)
    with bt_col2:
        gerar_pdf_click = st.button("📄 Baixar PDF", use_container_width=True)
    with bt_col3:
        limpar_click = st.button("🧹 Limpar", use_container_width=True)

    if limpar_click:
        st.session_state.df = None
        st.session_state.pdf_bytes = None
        st.experimental_rerun()

    if gerar_click and st.session_state.df is None:
        st.warning("Envie uma planilha antes de gerar os QR codes.")

    if gerar_click and st.session_state.df is not None:
        with st.spinner("Gerando QR codes em memória..."):
            # Apenas garante que os
