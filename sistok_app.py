import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from datetime import datetime
import matplotlib.pyplot as plt
import os
import gdown
from openai import OpenAI




# Konfigurasi layout Streamlit
st.set_page_config(
    page_title="Sistok App",
    page_icon="🐟",
    layout="wide"
)
# Inisialisasi OpenAI Client
client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])


# ID file Googel Drive
file_id = '1eACQIHOn3oS96V8rHzN6VlMuKtNX5raz'

# URL Google drive untuk diunduh
drive_url = f'https://drive.google.com/uc?id={file_id}'

# Fungsi untuk memuat data dari database atau file CSV
@st.cache_data
def load_data():
    try:
        # Download file CSV
        file_path = 'data_bersih.csv'  
        gdown.download(drive_url, file_path, quiet=False)
        # Baca file CCSV
        df = pd.read_csv(file_path,  low_memory=False)
        # Konversi tanggal ke tipe datetime
        df['tanggal_berangkat'] = pd.to_datetime(df['tanggal_berangkat'], errors='coerce')
        df['tanggal_kedatangan'] = pd.to_datetime(df['tanggal_kedatangan'], errors='coerce')
        df['tahun'] = df['tanggal_kedatangan'].dt.year
        return df

    except FileNotFoundError:
        st.error("File tidak ditemukan. Pastikan file 'data_bersih.csv' ada di folder './data/'." )
        return pd.DataFrame()

# Fungsi filter data
def filter_data(df, pelabuhan_kedatangan_id, nama_ikan_id, start_year, end_year, time_frame):

    # Filter data berdasarkan pelabuhan kedatangan
    if pelabuhan_kedatangan_id:
        df = df[df['pelabuhan_kedatangan_id'] == pelabuhan_kedatangan_id]

    # Filter data berdasarkan nama ikan
    if nama_ikan_id:
        df = df[df['nama_ikan_id'].isin(nama_ikan_id)]

    # Filter berdasarkan tahun
    if start_year:
        df = df[df['tahun'] >= start_year]
    if end_year:
        df = df[df['tahun'] <= end_year]

    # Filter berdasarkan time frame
    if time_frame == 'Daily':
        df['time_period'] = df['tanggal_kedatangan'].dt.date
    elif time_frame == 'Weekly':
        df['time_period'] = df['tanggal_kedatangan'].dt.to_period('W').astype(str)
    elif time_frame == 'Monthly':
        df['time_period'] = df['tanggal_kedatangan'].dt.to_period('M').astype(str)
    elif time_frame == 'Yearly':
        df['time_period'] = df['tanggal_kedatangan'].dt.to_period('Y').astype(str)


    return df

# Function to get OpenAI chat response

def get_openai_response(query, filtered_data):
    # create context about the current data

    data_context = {
        'total_tangkapan' : f"{float(filtered_data['berat'].sum()):,.2f} Kg",
        'nilai_produksi' : f"{filtered_data['nilai_produksi'].sum():,.2f} IDR",
        'periode': f'{filtered_data['tahun'].min()} to {filtered_data['tahun'].max()}',
        'jenis_ikan_dominan': filtered_data.groupby('nama_ikan_id')['berat'].sum().nlargest(3).index.tolist(),
        'alat_tangkap_dominan': filtered_data.groupby('jenis_api')['berat'].sum().nlargest(3).index.tolist(),
    }
    system_prompt = f"""You are an expert fishing data analyst assistant. Analyzie the fishing data dashboard and provide insights based on the following context:

Current Dashboard Data:
- Total Tangkapan: {data_context['total_tangkapan']}
- Nilai Produksi: {data_context['nilai_produksi']}
- Time Period: {data_context['periode']}
- Top 3 Jenis Ikan: {', '.join(data_context['jenis_ikan_dominan'])}
- Top 3 Alat Tangkap: {', '.join(data_context['alat_tangkap_dominan'])}

Provide concise, data-driven answers in Bahasa Indonesia. Focus on trends, patterns, and insights from the data"""
    try:
        response=client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[
                {'role': 'system', 'content': system_prompt},
                *[{'role': msg['role'], 'content': msg['content']} for msg in st.session_state.chat_history[-5::]],
                {'role': 'user', 'content': query}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# st.write('Kolom yang ada:', data.columns)


# CSS
st.markdown(
    """
    <style>
    .metric-box{
      border: 1px solid #ccc;
      padding: 10px;
      border-radius: 5px;
    
      margin: 5px;
      text-align: center;
    }
    </style>
""", unsafe_allow_html=True
)

# Initialize chat history in session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Header
st.markdown("<h1 style='text-align: center; '>SISTOK</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center; '>Fish Stock Analysis Tools</h2>", unsafe_allow_html=True)



# Menu
menu = option_menu(None, ['Dashboard', 'Analysis', 'About'],
    icons= ['house', 'graph-up', 'book'],
    menu_icon='cast', default_index=0, orientation='horizontal')

# # Sidebar untuk navigasi
# menu = st.sidebar.radio('Navigasi', ['Dashboard', 'Analysis', 'About'])

# Memuat data
data = load_data()

if menu == 'Dashboard':
    st.title('Dashboard')
     

    # Filter
    st.sidebar.subheader("Filter Data")
    pelabuhan = st.sidebar.selectbox("Pilih Pelabuhan", options=[None] + list(data['pelabuhan_kedatangan_id'].unique()))

    jenis_ikan = st.sidebar.multiselect("Pilih Jenis Ikan", options=list(data['nama_ikan_id'].unique()), default=[])

    start_year = st.sidebar.number_input('Start Year', min_value = int(data['tahun'].min()), max_value=int(data['tahun'].max()), value=int(data['tahun'].min()), step=1)
    
    end_year = st.sidebar.number_input('End Year', min_value=start_year, max_value=int(data['tahun'].max()), value=int(data['tahun'].max()), step=1)

    time_frame = st.sidebar.selectbox('Time Frame', ['Daily', 'Weekly', 'Monthly', 'Yearly'])

    
    # Filter data
    filtered_data = filter_data(data, pelabuhan, jenis_ikan, start_year, end_year, time_frame )

    # Chatbot
    st.sidebar.markdown('---')
    st.sidebar.subheader('Chat with Sistok Assistant')

    # Chat input
    user_input = st.sidebar.text_input('Ask about the Data:', key='chat_input')

    # Send Button
    if st.sidebar.button('Send', key='send_button'):
        if user_input:
            # Add user message to history
            st.session_state.chat_history.append({'role': 'user', 'content': user_input})

            # Get bot response
            with st.spinner('Thinking...'):
                bot_response = get_openai_response(user_input, filtered_data)
            # Add bot response to history
            st.session_state.chat_history.append({'role': 'assistant', 'content': bot_response})

    #  Display chat history
    st.sidebar.markdown("### Riwayat Chat")
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.sidebar.markdown(f"**Anda:** {message['content']}")
        else:
            st.sidebar.markdown(f"**Assistant:** {message['content']}")
        st.sidebar.markdown("---")

    # Clear chat history button
    if st.sidebar.button("Hapus Riwayat Chat"):
        st.session_state.chat_history = []
        st.experimental_rerun()

    

 # Cek kelengkapan data tahun 2024
    if 2024 in range(start_year, end_year+1):
        if not filtered_data.empty:
            data_tahun_2024 = filtered_data[filtered_data['tahun'] == 2024]
            if data_tahun_2024.empty or data_tahun_2024['berat'].sum() == 0:
                st.warning("⚠️ Data tahun 2024 belum lengkap. Mohon diperhatikan!")
            else:
                st.success("✅ Data tahun 2024 sudah lengkap.")
        else:
            st.warning("Data tidak tersedia. Silahkan periksa kembali filter Anda.")


    # Rename column
    columns_to_rename ={
        
        'nilai_produksi': 'Nilai Produksi',
        'jumlah_hari': 'Jumlah Hari',
        'pelabuhan_kedatangan_id': 'Pelabuhan Kedatangan',
        'pelabuhan_keberangkatan_id': 'Pelabuhan Keberangkatan',
        'kelas_pelabuhan': 'Port Class',
        'provinsi': 'Provinsi',
        'tanggal_berangkat': 'Tanggal Berangkat',
        'tanggal_kedatangan': 'Tanggal Kedatangan',
        
    }
    #  rename kolom yang ada di dataframe
    filtered_data = filtered_data.rename(columns={k: v for k, v in columns_to_rename.items() if k in filtered_data.columns})

    # Ringkasan data
    with st.expander('VIEW DATASET'):
        showData= st.multiselect('Filter: ', filtered_data.columns, default=filtered_data.columns)
        st.dataframe(filtered_data[showData], use_container_width=True)
     
    #  compute top analytics
    if not filtered_data.empty:
        total_tangkapan = float(pd.Series(filtered_data['berat']).sum())
        total_nilai_produksi = float(pd.Series(filtered_data['Nilai Produksi']).sum())
        total_hari = filtered_data['Jumlah Hari'].sum()
        total_ikan = filtered_data['nama_ikan_id'].nunique()
    else:
        total_tangkapan = total_nilai_produksi = total_hari = total_ikan = 0


    # Display top analytics
    total1, total2, total3, total4 = st.columns(4, gap='small')
    with total1:
        st.markdown(f'<div class="metric-box"> 🐟<br>Total Tangkapan<br><b>{total_tangkapan:,.0f} Kg </b></div>', unsafe_allow_html=True)
    with total2:
        st.markdown(f"<div class='metric-box'>💵<br>Nilai Produksi<br><b>{total_nilai_produksi:,.0f} IDR</b></div>", unsafe_allow_html=True)
    with total3:
        st.markdown(f"<div class='metric-box'>📆<br>Total Hari<br><b>{total_hari}</b></div>", unsafe_allow_html=True)
    with total4:
        st.markdown(f"<div class='metric-box'>🎣<br>Jenis Ikan<br><b>{total_ikan}</b></div>", unsafe_allow_html=True)

    # Graph
    
    
    # Grafik 1 : Data Tangkapan per Tahun
    # st.subheader('Tangkapan per Tahun')
    tangkapan_tahunan = filtered_data.groupby('tahun').agg({'berat':'sum'}).reset_index()
    fig_tangkapan = px.line(
        tangkapan_tahunan, 
        x='tahun', 
        y='berat', 
        orientation= 'v',
        title='TOTAL BERAT TANGKAPAN',
        color_discrete_sequence = ['#0083b8']*len(tangkapan_tahunan),
        template='plotly_dark',
    )
    fig_tangkapan.update_layout(
        xaxis=dict(tickmode='linear'),
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=(dict(showgrid=False))
    )
    

     # Grafik 2: 10 Jenis Tangkapan Terbanyak
    tangkapan_dominan = (
        filtered_data.groupby('nama_ikan_id').agg({'berat':'sum'}).reset_index().sort_values(by='berat', ascending=False).head(10))
    fig_tangkapan_dominan = px.bar(
        tangkapan_dominan,
        x='berat', 
        y= 'nama_ikan_id',
        orientation='h',
        title="<b> JENIS TANGKAPAN TERBANYAK </b>",
        color_discrete_sequence=['#0083b8']*len(tangkapan_dominan),
        template='plotly_dark'
        )
    fig_tangkapan_dominan.update_layout(
        plot_bgcolor = 'rgba(0,0,0,0)',
        font=dict(color='black'),
        yaxis=dict(
            showgrid=True, 
            gridcolor='#cecdcd',
            categoryorder= 'total ascending'),
        paper_bgcolor= 'rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#cecdcd'),
        )
    
    left,right,center=st.columns(3)
    left.plotly_chart(fig_tangkapan,use_container_width=True)
    right.plotly_chart(fig_tangkapan_dominan, use_container_width=True)
   
    with center:
    # Pie chart
        alat_tangkap_dominan = filtered_data.groupby('jenis_api').agg({'berat':'sum'}).reset_index().sort_values(by='berat', ascending=False).head(10)
        fig_alat_tangkap = px.pie(alat_tangkap_dominan, names='jenis_api', values='berat', title='ALAT TANGKAP DOMINAN')
        fig_alat_tangkap.update_layout(legend_title='Alat Tangkap', legend_y=0.9)
        fig_alat_tangkap.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_alat_tangkap, use_container_width=True)
          

elif menu == 'Analysis':
    st.title('Analysis')
   
    # Display Upload Button
   
    df_sample = pd.read_csv('./data/data_kembung_karangantu.csv')

    

    
    try:
        with open('./data/data_kembung_karangantu.csv', 'r') as file:
            sample_csv_content = file.read()
        st.download_button(
            label='Download Sample CSV',
            data=sample_csv_content,
            file_name='sample_data.csv',
            mime='text/csv'
        )
    except FileNotFoundError:
        st.error('Sample data tidak ditemukan. Silahkan periksa kembali file Anda.')

    # Komponen upload file
    uploaded_file = st.file_uploader(
        'Choose a file',
        type=['csv'],
        help='Limit: 200MB per file'
    )  

    # Proses jika file diupload
    if uploaded_file is not None:
        # Membaca file yang diupload
        user_data = pd.read_csv(uploaded_file)
        st.success('File uploaded succesfully!')
        with st.expander('Your Dataset:'):
            st.dataframe(user_data)

        # Analisis: Data Tangkapan per Tahun
        if 'tahun' in user_data.columns:

            if 'Nilai Produksi' in user_data.columns:
            
            # Grafik 1: Data Tangkapan per Tahun
            # Mengelompokkan data berdasarkan tahun dan menjumlahkan berat
                data_per_year = user_data.groupby('tahun').agg({'berat': 'sum', 'Nilai Produksi': 'sum'}).reset_index()

            # Menghitung rata-rata nilai produksi dan nilai produksi
                data_per_year['Harga rata-rata nilai produksi'] = data_per_year['Nilai Produksi'] / data_per_year['berat']
                data_per_year['Produksi (Ton)'] = data_per_year['berat'] / 1000
                data_per_year['Nilai Produksi'] = data_per_year['Produksi (Ton)'] * data_per_year['Harga rata-rata nilai produksi'] 
            else:
                data_per_year = user_data.groupby('tahun').agg({'berat': 'sum'}).reset_index()
                data_per_year['Produksi (Ton)'] = data_per_year['berat'] / 1000
                data_per_year['Harga rata-rata nilai produksi'] = None
                data_per_year['Nilai Produksi'] = None
            
            
            # Membuat grafik garis menggunakan plotly
            fig_data_per_year = px.line(
                data_per_year, 
                x='tahun', 
                y='berat', 
                orientation='v',
                title='TOTAL BERAT TANGKAPAN PER TAHUN', 
                template='plotly_dark'
            )
            
            # Memperbarui layout grafik
            fig_data_per_year.update_layout(
                xaxis=dict(tickmode='linear'),
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis=dict(showgrid=False)
            )

            # Grafik 2: 
            api_dominan = user_data.groupby('jenis_api').agg({'berat':'sum'}).reset_index().sort_values(by='berat', ascending=False).head(10)
            fig_api_dominan = px.bar(
                api_dominan,
                x='berat', 
                y= 'jenis_api',
                orientation='h',
                title="<b> JENIS API DOMINAN </b>",
                color_discrete_sequence=['#0083b8']*len(api_dominan),
                template='plotly_dark'
                )
            fig_api_dominan.update_layout(
                plot_bgcolor = 'rgba(0,0,0,0)',
                font=dict(color='black'),
                yaxis=dict(
                    showgrid=True, 
                    gridcolor='#cecdcd',
                    categoryorder= 'total ascending'),
                paper_bgcolor= 'rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='#cecdcd'),
                )
            
            
           
            left, right = st.columns(2)
            left.plotly_chart(fig_data_per_year, user_container_width=True)
            right.plotly_chart(fig_api_dominan, user_container_width=True)

            with st.expander('DATA PRODUKSI DAN NILAI PRODUKSI PER TAHUN'):
                st.dataframe(data_per_year[['tahun', 'Produksi (Ton)', 'Harga rata-rata nilai produksi', 'Nilai Produksi']].reset_index(drop=True), use_container_width=True)
            

        
        
        st.markdown(
            """
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            <hr>

           <div class="card mb-3" style='background-color: black; color: white;'>
                <div class="card">
                <div class="card-body">
                    <h3 class="card-title"style="color:#007710;"><strong>📈 ANALISIS LANJUTAN: MODEL PRODUKSI SURPLUS</strong></h3>
                    <p class="card-text">Model Produksi Surplus adalah salah satu model yang digunakan dalam analisis stok ikan untuk mengukur kelimpahan stok ikan dan hubungannya dengan upaya penangkapan (effort). Model ini membantu memprediksi tingkat eksploitasi optimal untuk menjaga keberlanjutan sumber daya perikanan. </p>
                    <p class="card-text"><small class="text-body-secondary"> </small></p>
                </div>
                </div>
                </div>
                <style>
                    [data-testid=stSidebar] {
                        color: white;
                        background-color: black;
                        text-size:24px;
                    }
                    .card{
                        background-color: black;
                        border: 1px solid #444
                    }
                    .card-body{
                        color: white;
                    }
                </style>
                """,unsafe_allow_html=True
                )
        

        # Hasil Tangkapan per Alat Tangkap 
        with st.expander('⬇ Hasil Tangkapan per Alat Tangkap'):	
            if {'jenis_api', 'tahun', 'berat'}.issubset(user_data.columns):
                tangkapan_per_tahun = user_data.groupby(['jenis_api', 'tahun']).agg({'berat': 'sum'}).reset_index()
                
                tangkapan_pivot = tangkapan_per_tahun.pivot(index='jenis_api', columns='tahun', values='berat').fillna(0)

                # Tambahkan kolom total untuk tiap alat tangkap
                tangkapan_pivot['Total'] = tangkapan_pivot.sum(axis=1)

                # Tambahkan baris jumlah total untuk tiap alat tangkap
                tangkapan_pivot.loc['Jumlah'] = tangkapan_pivot.sum()

                # Reset index untuk tampilkan tabel
                tangkapan_pivot = tangkapan_pivot.reset_index()

                # Tampilkan tabel
                st.write('Hasil Tangkapan per Alat Tangkap')
                st.dataframe(tangkapan_pivot, use_container_width=True)

                # Membuat grafik batang hasil tangkapan
            fig_tangkapan_total = px.bar(
                tangkapan_pivot[tangkapan_pivot['jenis_api'] != 'Jumlah'],
                x='jenis_api',
                y='Total',
                # orientation='h',
                title="<b>Hasil Tangkapan per Alat Tangkap</b>",
                color='jenis_api',
                template='plotly_dark'
            )
            fig_tangkapan_total.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='#cecdcd'),
                yaxis=dict(categoryorder='total ascending')
            )
            st.plotly_chart(fig_tangkapan_total, use_container_width=True)

        # Jumlah Trip per Alat Tangkap
        with st.expander('⬇ Jumlah Trip per Alat Tangkap'):
            if {'jenis_api', 'tahun', 'Jumlah Hari'}.issubset(user_data.columns):

                effort_per_tahun = user_data.groupby(['jenis_api', 'tahun']).agg({'Jumlah Hari': 'sum'}).reset_index()
                effort_pivot = effort_per_tahun.pivot(index='jenis_api', columns='tahun', values='Jumlah Hari').fillna(0)

                # Tambahkan kolom total untuk tiap alat tangkap
                effort_pivot['Total'] = effort_pivot.sum(axis=1)
                # Tambahkan baris jumlah total untuk tiap alat tangkap
                effort_pivot.loc['Jumlah'] = effort_pivot.sum()

                # Reset index untuk tampilkan tabel
                effort_pivot = effort_pivot.reset_index()
                

                # Tampilkan tabel
                st.write('Jumlah Trip per Alat Tangkap')
                st.dataframe(effort_pivot, use_container_width=True)

                # Membuat grafik batang jumlah trip
                fig_trip_per_alat = px.bar(
                    effort_pivot[effort_pivot['jenis_api'] != 'Jumlah'],
                    x='jenis_api',
                    y='Total',
                    # orientation='h',
                    title="<b>Jumlah Trip per Alat Tangkap</b>",
                    color='jenis_api',
                    template='plotly_dark'
                )
                fig_trip_per_alat.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=True, gridcolor='#cecdcd'),
                    yaxis=dict(categoryorder='total ascending')
                )
                st.plotly_chart(fig_trip_per_alat, use_container_width=True)

            
        # # Analisis Lanjutan: Model Produksi Surplus
        with st.expander('⬇ CPUE'):
            # st.write('CPUE (Catch Per Unit Effort) adalah rasio antara jumlah tangkapan ikan dengan upaya penangkapan yang dilakukan.')

        
            if 'jenis_api' in user_data.columns and 'berat' in user_data.columns and 'Jumlah Hari' in user_data.columns:
                user_data.rename(columns={'jenis_api' : 'Alat Tangkap', 'berat': 'catch (ton)', 'Jumlah Hari': 'effort (hari)'}, inplace=True)

                # Konversi tangkapan ke ton
                user_data['catch (ton)'] = user_data['catch (ton)'] / 1000 
                # Kelompokkan data berdasarkan jenis alat tangkap
                alat_tangkap_group = user_data.groupby('Alat Tangkap').agg({'catch (ton)': 'sum', 'effort (hari)': 'sum'}).reset_index()

                # Menambah kolom CPUE
                alat_tangkap_group['CPUE'] = alat_tangkap_group['catch (ton)'] / alat_tangkap_group['effort (hari)']


                # Urutkan data berdasarkan berat
                alat_tangkap_group = alat_tangkap_group.sort_values(by='catch (ton)', ascending=False)

                # Pilih 2 alat tangkap dominan
                alat_tangkap_dominan = alat_tangkap_group.head(2)

                # Cari CPUE tertinggi
                cpue_max = alat_tangkap_dominan['CPUE'].max()

                # Kolom FPI
                alat_tangkap_dominan['FPI'] = alat_tangkap_dominan['CPUE'] / cpue_max

                alat_tangkap_dominan.loc[alat_tangkap_dominan['CPUE'] == cpue_max, 'FPI'] = 1

                # Tampilkan data dalam tabel
                st.write('Data CPUE per Alat Tangkap:')
                st.table(alat_tangkap_dominan)

                # Buat grafik batang
                fig_cpue = px.bar(
                    alat_tangkap_dominan,
                    x='Alat Tangkap',
                    y='CPUE',
                    text='CPUE',	
                    title='CPUE per Alat Tangkap',
                    labels={'Alat Tangkap': 'Jenis Alat Tangkap', 'CPUE': 'CPUE'},
                    template='plotly_dark',
                    color= 'Alat Tangkap'
                )
                fig_cpue.update_traces(texttemplate='%{text:.4f}', textposition='outside')
                fig_cpue.update_layout(showlegend=False)

                st.plotly_chart(fig_cpue, use_container_width=True)
           	
        
            
        # # Analisis Lanjutan: Penghitungan CPUE
        # if 'Jumlah Hari' in user_data.columns and 'berat' in user_data.columns:
        #     st.subheader('Analisis Lanjutan: CPUE (Catch Per Unit Effort)')

        #     # Menghitung CPUE
        #     user_data['CPUE'] = user_data['berat'] / user_data['Jumlah Hari']
        #     cpue_per_year = user_data.groupby('tahun').agg({'CPUE': 'mean'}).reset_index()

        #     # Menampilkan Data CPUE dalam bentuk Tabel
        #     st.write('Data CPUE per Tahun:')
        #     st.dataframe(cpue_per_year)

        #     # Membuat Grafik CPUE per Tahun
        #     fig_cpue = px.line(
        #         cpue_per_year,
        #         x='tahun',
        #         y='CPUE',
        #         title='CPUE per Tahun',
        #         template='plotly_dark'
        #     )
        #     fig_cpue.update_layout(
        #         plot_bgcolor='rgba(0,0,0,0)',
        #         xaxis=dict(tickmode='linear'),
        #         yaxis=dict(showgrid=True, gridcolor='#cecdcd'),
        #         paper_bgcolor='rgba(0,0,0,0)'
        #     )

        #     # Menampilkan Grafik CPUE
        #     st.plotly_chart(fig_cpue, use_container_width=True)

           
        # else:
        #     st.warning('Kolom "tahun" atau "berat" tidak ditemukan. Pastikan file Anda memiliki kolom tersebut.')
    else:
        st.info('Please upload a CSV file to proceed.')
        



elif menu == 'About':
    st.title('About this App')
    st.write('Sistok adalah Aplikasi berbasis web untuk analisis data stok ikan')

else:
    st.error('Data tidak tersedia. Silahkan periksa kembali file Anda.')



