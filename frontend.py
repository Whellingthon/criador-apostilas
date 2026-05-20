import streamlit as st
import requests

st.set_page_config(page_title="Gerador de Apostilas", page_icon="📚", layout="wide")

st.title("📚 Gerador Inteligente de Apostilas Pro")
st.caption("Gere planos de aula, conteúdos profundos e exercícios alinhados à BNCC.")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("Configurações")
    
    email = st.text_input("E-mail do Professor / Instituição", placeholder="seu-email@escola.com")
    tema = st.text_input("Tema da Apostila", placeholder="Ex: Introdução às Frações, História da Internet...")
    publico = st.text_input("Público-Alvo / Ano", placeholder="Ex: 5º ano do Ensino Fundamental, Técnico em TI...")
    
    # NOVO CAMPO: Alinhamento BNCC
    bncc = st.text_input("Códigos da BNCC (Opcional)", placeholder="Ex: EF05MA03, EM13LGG101...")
    
    metodologia = st.selectbox(
        "Abordagem Pedagógica",
        [
            "Tradicional (Direta e Conceitual)", 
            "Ludopedagogia (Foco em jogos e ludicidade)", 
            "Metodologias Ativas (Foco na resolução de problemas)",
            "Abordagem Sociointeracionista (Vygotsky)"
        ]
    )
    
    arquivo_pdf = st.file_uploader("📖 Upload de Livro/Texto Norteador (Lê até 30 págs)", type=["pdf"])
    botao_gerar = st.button("✨ Gerar Material Completo", use_container_width=True)

with col2:
    st.header("Conteúdo Gerado")
    
    # Cria um espaço persistente na tela para o botão de download aparecer
    container_download = st.empty()
    container_texto = st.empty()
    
    if botao_gerar:
        if not email or not tema or not publico:
            st.error("Por favor, preencha todos os campos obrigatórios!")
        else:
            with st.spinner("O Back-end está compilando os livros, regras da BNCC e redigindo as seções..."):
                url_api = "http://127.0.0.1:8001/gerar"
                
                payload = {
                    "email": email,
                    "tema": tema,
                    "publico_alvo": publico,
                    "metodologia": metodologia,
                    "bncc": bncc
                }
                
                arquivos = None
                if arquivo_pdf is not None:
                    arquivos = {"arquivo_pdf": (arquivo_pdf.name, arquivo_pdf.getvalue(), "application/pdf")}
                
                try:
                    response = requests.post(url_api, data=payload, files=arquivos)
                    
                    if response.status_code == 200:
                        resultado = response.json()
                        conteudo_final = resultado["conteudo"]
                        
                        st.success(f"Apostila estruturada com sucesso!")
                        
                        # Ativa o botão de download puxando o arquivo PDF do back-end
                        url_download = f"http://127.0.0.1:8001/baixar-pdf/{email}"
                        pdf_response = requests.get(url_download)
                        
                        if pdf_response.status_code == 200:
                            container_download.download_button(
                                label="📥 BAIXAR APOSTILA FORMATADA EM PDF",
                                data=pdf_response.content,
                                file_name=f"Apostila_{tema}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        
                        # Exibe na tela o preview em Markdown
                        container_texto.markdown(conteudo_final)
                    else:
                        st.error(f"Erro na API: {response.text}")
                        
                except requests.exceptions.ConnectionError:
                    st.error("Não foi possível conectar ao Back-end. O arquivo backend.py está rodando?")