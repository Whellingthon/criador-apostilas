from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import google.genai as genai 
from pypdf import PdfReader
import io
import os
from dotenv import load_dotenv


from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

load_dotenv()

app = FastAPI(title="API Gerador de Apostilas Pro", version="2.0")

# 1. Busca a chave que está guardada estritamente dentro do seu arquivo .env
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")

# 2. Se o arquivo .env sumir ou a chave não estiver lá, o sistema trava por segurança
if not GENAI_API_KEY:
    raise ValueError("ERRO CRÍTICO: A variável de ambiente GEMINI_API_KEY não foi encontrada no arquivo .env!")

# 3. Inicializa o cliente do Google GenAI usando a variável segura
client = genai.Client(api_key=GENAI_API_KEY)

# Dicionário global temporário para guardar a última apostila gerada na memória
memoria_apostila = {}

@app.post("/gerar")
async def gerar_apostila(
    email: str = Form(...),
    tema: str = Form(...),
    publico_alvo: str = Form(...),
    metodologia: str = Form(...),
    bncc: str = Form(None), # Novo campo opcional
    arquivo_pdf: UploadFile = File(None)
):
    try:
        texto_contexto = ""
        if arquivo_pdf:
            conteudo_arquivo = await arquivo_pdf.read()
            leitor_pdf = PdfReader(io.BytesIO(conteudo_arquivo))
            # Habilitado para ler mais páginas se necessário (ex: até 30 páginas)
            paginas_para_ler = min(len(leitor_pdf.pages), 30)
            for i in range(paginas_para_ler):
                texto_contexto += leitor_pdf.pages[i].extract_text() or ""

        # Engenharia de Prompt Expandida com BNCC e Mais Conteúdo
        prompt = f"""
        Você é um mestre em pedagogia, designer educacional sênior e especialista na BNCC.
        O professor ({email}) solicitou uma apostila didática completa de alto padrão.
        
        Especificações:
        - Tema Central: {tema}
        - Público-Anvo/Ano: {publico_alvo}
        - Abordagem Metodológica: {metodologia}
        """
        
        if bncc:
            prompt += f"\n- Alinhamento Obrigatório com as competências da BNCC: {bncc}"
            
        if texto_contexto:
            prompt += f"\n\nUse o texto do livro fornecido pelo professor para extrair os conceitos principais:\n--- {texto_contexto[:12000]} ---"
        
        prompt += """
        \nEstruture a apostila EXATAMENTE com as seguintes seções expandidas:
        
        # {tema} - MATERIAL DIDÁTICO PRO
        
        ## 📋 DIRETRIZES PEDAGÓGICAS
        - **Público:** {publico_alvo}
        - **Abordagem:** {metodologia}
        - **Competências BNCC Relacionadas:** {bncc}
        
        ---
        
        ## 📅 PLANO E CRONOGRAMA DE AULA SUGERIDO
        (Proponha uma divisão detalhada de como o professor pode aplicar este conteúdo em 4 aulas de 50 minutos).
        
        ---
        
        ## 📖 1. CONTEÚDO TEÓRICO COMPLETO
        (Desenvolva o conceito de forma profunda, clara e atraente para o público-alvo, usando subtópicos, tabelas explicativas em texto ou analogias cotidianas).
        
        ---
        
        ## 🧠 2. GLOSSÁRIO DE TERMOS TÉCNICOS
        (Crie uma lista com os 5 termos mais importantes e suas respectivas definições simplificadas).
        
        ---
        
        ## ✍️ 3. EXERCÍCIOS DE FIXAÇÃO
        (Crie 5 questões autorais inéditas com níveis progressivos de dificuldade: 2 fáceis, 2 médias e 1 difícil, misturando múltipla escolha e dissertativas).
        
        ---
        
        ## 🔑 4. GABARITO COMENTADO (PARA O PROFESSOR)
        (Traga as respostas corretas com justificativas pedagógicas detalhadas indicando o erro das alternativas incorretas).
        
        Formate o texto elegantemente usando Markdown limpo.
        """
        
        resposta = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        conteudo_texto = resposta.text
        
        # Salva na memória interna para o botão de download conseguir buscar depois
        memoria_apostila[email] = {"tema": tema, "conteudo": conteudo_texto}
        
        return {"sucesso": True, "conteudo": conteudo_texto}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na geração da IA: {str(e)}")

# NOVA ROTA: Transforma o conteúdo gerado em um PDF estruturado
@app.get("/baixar-pdf/{email}")
def baixar_pdf(email: str):
    if email not in memoria_apostila:
        raise HTTPException(status_code=404, detail="Nenhuma apostila gerada para este e-mail.")
    
    dados = memoria_apostila[email]
    buffer = io.BytesIO()
    
    # Criação do documento PDF timbrado
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=50)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Criando estilos personalizados e "bonitinhos"
    estilo_titulo = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor("#1A365D"), spaceAfter=15)
    estilo_sub = ParagraphStyle('Subtitulo', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor("#2B6CB0"), spaceBefore=12, spaceAfter=8)
    estilo_texto = ParagraphStyle('Texto', parent=styles['Normal'], fontSize=11, leading=16, textColor=colors.HexColor("#2D3748"), spaceAfter=10)
    
    # Converte o texto da IA (linhas) para elementos do PDF
    story.append(Paragraph(f"<b>APOSTILA DIDÁTICA: {dados['tema'].upper()}</b>", estilo_titulo))
    story.append(Paragraph("Gerado por Inteligência Educacional Pro", estilo_texto))
    story.append(Spacer(1, 15))
    
    linhas = dados['conteudo'].split('\n')
    for linha in linhas:
        if not linha.strip():
            continue
        if linha.startswith('# '):
            story.append(Paragraph(linha.replace('# ', ''), estilo_titulo))
        elif linha.startswith('## ') or linha.startswith('### '):
            story.append(Paragraph(linha.replace('## ', '').replace('### ', ''), estilo_sub))
        else:
            # Remove marcações simples de markdown para não quebrar o PDF
            limpa = linha.replace('**', '').replace('*', '').replace('`', '')
            story.append(Paragraph(limpa, estilo_texto))
            
    doc.build(story)
    buffer.seek(0)
    
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Apostila_{dados['tema']}.pdf"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)