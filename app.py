import io
import textwrap

import pandas as pd
import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import streamlit as st

# ---------- CONFIGURAÇÃO BÁSICA ----------
st.set_page_config(page_title="QR Codes Estoque Restaurante", layout="wide")
st.title("Gerador de QR Codes para Estoque")

st.markdown(
    "Use uma planilha com as colunas **codigo** e **produto** para gerar os QR Codes."
)

# ---------- MODELO DE PLANILHA ----------
st.subheader("1. Baixar modelo de planilha (.csv)")
modelo_df = pd.DataFrame({"codigo": [], "produto": []})
modelo_csv = modelo_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Baixar modelo (codigo,produto)",
    data=modelo_csv,
    file_name="modelo_produtos_qr.csv",
    mime="text/csv",
)

# ---------- UPLOAD DA PLANILHA ----------
st.subheader("2. Enviar planilha com produtos")
uploaded_file = st.file_uploader(
    "Envie um arquivo .csv com colunas: codigo,produto",
    type=["csv"],
)

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, dtype=str)
    except Exception:
        st.error("Erro ao ler o arquivo. Verifique se é um CSV válido em UTF-8.")
        st.stop()

    # Normaliza nomes de colunas
    df.columns = [c.strip().lower() for c in df.columns]

    # Validação de colunas
    if not {"codigo", "produto"}.issubset(set(df.columns)):
        st.error("O arquivo precisa ter as colunas: codigo e produto.")
        st.stop()

    df = df[["codigo", "produto"]].fillna("")

    st.write("Pré-visualização dos dados:")
    st.dataframe(df.head(20))

    # ---------- PARÂMETROS DE LAYOUT ----------
    st.subheader("3. Configurações de layout do PDF")
    col1, col2 = st.columns(2)
    with col1:
        itens_por_linha = st.selectbox(
            "Códigos por linha no PDF",
            options=[2, 3, 4],
            index=1,
        )
    with col2:
        fonte_tamanho = st.slider("Tamanho da fonte (nome/código)", 10, 20, 12)

    # ---------- FUNÇÕES AUXILIARES ----------

    def gerar_imagem_qr(codigo: str, produto: str, fonte_tamanho: int = 12) -> Image.Image:
        """
        Gera uma imagem com:
        - Nome do produto
        - Código
        - QR code com o código
        Tudo empilhado verticalmente.
        """
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

        # Quebra o nome do produto em linhas menores
        texto_produto = produto.strip()
        if not texto_produto:
            texto_produto = "(sem nome)"
        linhas = textwrap.wrap(texto_produto, width=25)

        # Tenta carregar uma fonte TrueType padrão
        try:
            fonte = ImageFont.truetype("arial.ttf", fonte_tamanho)
        except Exception:
            fonte = ImageFont.load_default()

        # Calcula área de texto
        draw_dummy = ImageDraw.Draw(qr_img)
        line_heights = []
        max_text_width = 0
        for linha in linhas:
            bbox = draw_dummy.textbbox((0, 0), linha, font=fonte)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            max_text_width = max(max_text_width, w)
            line_heights.append(h)

        # Código na linha de baixo
        bbox_codigo = draw_dummy.textbbox((0, 0), str(codigo), font=fonte)
        codigo_w = bbox_codigo[2] - bbox_codigo[0]
        codigo_h = bbox_codigo[3] - bbox_codigo[1]

        texto_altura_total = sum(line_heights) + codigo_h + 10  # margem

        # Largura final: maior entre QR e texto
        largura_final = max(qr_img.width, max_text_width, codigo_w) + 20
