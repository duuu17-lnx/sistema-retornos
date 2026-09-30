import streamlit as st
import pandas as pd
import re
import requests
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Retorno de Clientes", layout="wide")
st.title("Sistema de Retorno de Clientes - Elyara Vieira")

# --- BARRA LATERAL PARA O TELEGRAM ---
st.sidebar.header("Notificações Telegram")
st.sidebar.write("Configure seu bot para receber avisos de clientes inativos há mais de 30 dias.")
telegram_token = st.sidebar.text_input("Bot Token", type="password")
telegram_chat_id = st.sidebar.text_input("Seu Chat ID")

# Upload da planilha
uploaded_file = st.file_uploader("Faça upload da sua planilha (Excel ou CSV)", type=['xlsx', 'csv', 'xltx'])

if uploaded_file is not None:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    colunas_esperadas = ['NOME', 'TEL', 'ULT ATEND', 'DATA ULT ATEND']
    if not all(coluna in df.columns for coluna in colunas_esperadas):
        st.error(f"A planilha deve conter exatamente estas colunas: {', '.join(colunas_esperadas)}")
    else:
        df['TEL'] = df['TEL'].astype(str)

        def padronizar_data_pt(data_str):
            if pd.isna(data_str): return data_str
            data_str = str(data_str).lower().strip()
            meses = {
                'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
                'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
                'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
            }
            data_str = data_str.replace(' de ', '/')
            for mes_nome, mes_num in meses.items():
                if mes_nome in data_str:
                    data_str = data_str.replace(mes_nome, mes_num)
            return data_str

        df['DATA ULT ATEND'] = df['DATA ULT ATEND'].apply(padronizar_data_pt)
        df['DATA ULT ATEND'] = pd.to_datetime(df['DATA ULT ATEND'], dayfirst=True, errors='coerce')

        def criar_link_whatsapp(telefone):
            if str(telefone).strip().lower() in ['nan', 'none', '']: return None
            num = re.sub(r'\D', '', str(telefone))
            if not num: return None
            if not num.startswith('55'): num = '55' + num
            return f"https://wa.me/{num}"

        df['LINK WHATSAPP'] = df['TEL'].apply(criar_link_whatsapp)
        
        df['TEL'] = df['TEL'].apply(lambda x: "" if str(x).lower() == 'nan' else str(x))
        df['TEL'] = df['TEL'].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)

        # --- LÓGICA DOS 30 DIAS E BOTÃO DO TELEGRAM ---
        hoje = pd.Timestamp.today()
        limite_30_dias = hoje - pd.Timedelta(days=30)
        
        # Filtra quem tem data de atendimento menor (mais antiga) que 30 dias atrás
        df_atrasados = df[df['DATA ULT ATEND'] < limite_30_dias]

        if st.sidebar.button("Enviar Relatório por Telegram"):
            if not telegram_token or not telegram_chat_id:
                st.sidebar.error("Preencha o Token e o Chat ID acima!")
            elif df_atrasados.empty:
                st.sidebar.success("Nenhum cliente com mais de 30 dias de ausência!")
            else:
                # Monta a mensagem que será enviada
                mensagem = f"🚨🚨🚨 *Atenção! Você tem {len(df_atrasados)} clientes ausentes há mais de 30 dias:*\n\n"
                
                for index, row in df_atrasados.iterrows():
                    nome = row['NOME']
                    data_formatada = row['DATA ULT ATEND'].strftime('%d/%m/%Y')
                    mensagem += f"👤 {nome} (Última vez: {data_formatada})\n"
                
                # Dispara para o servidor do Telegram
                url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                payload = {
                    "chat_id": telegram_chat_id,
                    "text": mensagem,
                    "parse_mode": "Markdown"
                }
                
                try:
                    resposta = requests.post(url, json=payload)
                    if resposta.status_code == 200:
                        st.sidebar.success("Relatório enviado com sucesso pro seu celular!")
                    else:
                        st.sidebar.error("Erro ao enviar. Verifique o Token e o Chat ID.")
                except Exception as e:
                    st.sidebar.error(f"Erro de conexão com a internet: {e}")

        # -----------------------------------------------

        st.divider() 
        st.subheader("Clientes para entrar em contato:")
        
        ordem = st.radio(
            "Escolha a ordem de exibição da data:",
            ["Mais antigos primeiro (Maior tempo sem agendar)", "Mais recentes primeiro (Atendidos recentemente)"],
            horizontal=True
        )

        if "antigos" in ordem:
            df_ordenado = df.sort_values(by='DATA ULT ATEND', ascending=True)
        else:
            df_ordenado = df.sort_values(by='DATA ULT ATEND', ascending=False)
        
        st.dataframe(
            df_ordenado,
            column_config={
                "DATA ULT ATEND": st.column_config.DatetimeColumn(
                    "Data do Último Atendimento",
                    format="DD/MM/YYYY"
                ),
                "LINK WHATSAPP": st.column_config.LinkColumn(
                    "Ação",
                    display_text="Chamar no WhatsApp 💬"
                )
            },
            hide_index=True,
            use_container_width=True
        )