######################################################################################################
                                           #Introduaao
######################################################################################################

# Aplicacao para inventário dos equipamentos da Ambev.

# Recebe base de dados em formato excel e os aadiciona a aplicacao os dividindo em dados validados e 
# nao validados.

# Apos receber a base, e possivel inventariar os equipamentos adicionados na base validada

# Tambem e possivel adicionar novos validar os itens da base nao validada e entao efetuar o inventario

# O inventario e exportado em CSV (implementado), Excel e PDF 

######################################################################################################
                                 # importar bibliotecas
######################################################################################################


import streamlit as st
from streamlit import caching
import plotly.graph_objects as go
import pandas as pd
from os.path import exists
from PIL import Image
import io
import base64
from streamlit_autorefresh import st_autorefresh
import time
from IPython.core.display import HTML
import os
from unicodedata import normalize

######################################################################################################
				#Configuraaaes da pagina
######################################################################################################


st.set_page_config(
     page_title="Inventário Ambev", 
)


######################################################################################################
                               #Funcoes
######################################################################################################


def main():
    ##### Sidebar #####
    c1,c2 = st.sidebar.columns([1,2])
    c1.image('logo2.png', width=150)
    telas = [
        'Inserir item no inventário',
        'Importar base de dados', 
        'Atualizar base de dados', 
        'Exportar inventário',
        'Suporte']

    colunas_saida = [
        'Empre',
        'Imob',
        'Sbn',
        'Classe',
        'Data',
        'Denominacao',
        'Div',
        'Centro_custo',
        'Justificativa',
        'Data do inventário',
        'Encontrado',
        'Ativo',
        'Marca',
        'Modelo',
    ]

    st.sidebar.subheader('Funcionalidades inventário')
    tela = st.sidebar.radio('', telas)

    # verifica se existe uma base de dados validada
    file_exists = exists('base_dados.parquet')
    if file_exists:
        df_base = pd.read_parquet('base_dados.parquet')

    # verifica se existe uma base de dados nao validada
    file_exists2 = exists('nao_validados.parquet')
    if file_exists2:
        df_not = pd.read_parquet('nao_validados.parquet')

    st.title('Inventário Ambev :memo:')

    if tela == 'Inserir item no inventário':
        inserir_item(file_exists, colunas_saida)

    if tela == 'Atualizar base de dados':
        if file_exists and file_exists2:
            atualizar_base(df_base, df_not)
        else: 
            st.error('Não existe base de dados')

    if tela == 'Importar base de dados':
        st.subheader('Importar base de dados')
        uploaded_file = st.file_uploader("Selecione o arquivo Excel para upload")
        if uploaded_file is not None:
            df_importar_base = pd.read_excel(uploaded_file, sheet_name=0)
            if df_importar_base.shape[1] == 11:
                importar_base(file_exists, file_exists2, df_importar_base)
            else:
                st.error('Base fora do padrão')

    if tela == 'Exportar inventário':
        if file_exists:
            exportar_base(df_base, colunas_saida)
        else: 
            st.error('Não existe base de dados')

    if tela == 'Suporte':
        suporte()

# Funções para gerar as imagens no HTML
def get_thumbnail(path):
    if exists(path):
        i = Image.open(path)
    else:
        # i = Image.open('fotos/empty.jpeg')
        i = Image.new('RGB', (1,1))
    i.thumbnail((700, 700), Image.LANCZOS)
    return i


def image_base64(im):
    if isinstance(im, str):
        im = get_thumbnail(im)
    with io.BytesIO() as buffer:
        im.save(buffer, 'jpeg')
        return base64.b64encode(buffer.getvalue()).decode()


def image_formatter(im):
    return f'<img src="data:image/jpeg;base64,{image_base64(im)}">'


def removedor_acentos(texto):
    return normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')


def html_report(df):

    df['fotos1'] = 'none.jpeg'
    df.loc[(df['Sbn'] == 0),'fotos1'] = 'fotos/' + df['Denominacao'].str.replace('-', '_') + '_' + df['Imob'].astype(str) + '_1.jpeg'

    df['fotos2'] = 'none.jpeg'
    df.loc[(df['Sbn'] == 0),'fotos2'] = 'fotos/' + df['Denominacao'].str.replace('-', '_') + '_' + df['Imob'].astype(str) + '_2.jpeg'

    df['fotos3'] = 'none.jpeg'
    df.loc[(df['Sbn'] == 0),'fotos3'] = 'fotos/' + df['Denominacao'].str.replace('-', '_') + '_' + df['Imob'].astype(str) + '_3.jpeg'

    df['foto_equipamento'] = df.fotos1.map(lambda f: get_thumbnail(f))
    df['foto_tag'] = df.fotos2.map(lambda f: get_thumbnail(f))
    df['foto_tag_amarela'] = df.fotos3.map(lambda f: get_thumbnail(f))

    dicionario = {
        'foto_equipamento': image_formatter,
        'foto_tag': image_formatter,
        'foto_tag_amarela': image_formatter,
    }

    colunas = [
        'Empre',
        'Imob',
        'Sbn',
        'Classe',
        'Data',
        'Denominacao',
        'Div',
        'Centro_custo',
        'Justificativa',
        'Data do inventário',
        'Encontrado',
        'Ativo',
        'Marca',
        'Modelo',
        'foto_equipamento',
        'foto_tag',
        'foto_tag_amarela'
    ]

    HTML(df.to_html(escape=False, formatters=dicionario))
    df[colunas].to_html('inventario.html', escape=False, formatters=dicionario)


def inserir_item(file_exists, colunas_saida):
    """
    Filtra os itens da base de dados pela planta, linha/area e equipamento. Entao permite o preenchimento
    dos dados do inventario. Caso o inventario ja tenha sido realizado, permite tambem a visualizacao do 
    mesmo.

    Os equipamentos podem ser classificados como em aberto, sim (encontrados em campo) e nao (nao encontrados)

    Args:
        file_exists ([bool]): [booleano que informa se o arquivo da base de dados existe ou nao]
    """    
    
    if file_exists:  
        st.subheader('Seleção do equipamento')
        base_dados = pd.read_parquet('base_dados.parquet')

        plantas_base = list(base_dados.Planta.unique())
        planta = st.selectbox('Selecione a planta', plantas_base)

        linhas_base = list(base_dados.loc[base_dados['Planta'] == planta, 'Linha'].unique())
        linha = st.selectbox('Selecione a área', linhas_base)

        equip_base = list(base_dados.loc[(base_dados['Linha'] == linha) & (base_dados['Planta'] == planta), 'Equipamento'].unique())
        equipamento = st.selectbox('Selecione o equipamento', equip_base)

        imob_base = list(base_dados.loc[(base_dados['Linha'] == linha) & (base_dados['Equipamento'] == equipamento) & (base_dados['Planta'] == planta), 'Imob'].unique())

        imobilizado = ''
        if len(imob_base) > 1:
            imobilizado = st.selectbox('Selecione o imobilizado', imob_base)
        else:
            imobilizado = imob_base[0]

        item_index = list(base_dados.loc[(base_dados['Imob'].astype(int) == imobilizado) & (base_dados['Linha'] == linha) & (base_dados['Equipamento'] == equipamento) & (base_dados['Planta'] == planta)].index)
        equipamento_sap = '_'.join((planta, linha, equipamento,str(imobilizado)))
        if base_dados.loc[item_index[0], 'Encontrado'] == 'Sim':
            st.success('** Imobilizado ' + str(imobilizado) + ' encontrado**')
        elif base_dados.loc[item_index[0], 'Encontrado'] == 'Nao':
            st.error('** Imobilizado ' + str(imobilizado) + ' não encontrado**')
        else:
            st.warning('** Imobilizado ' + str(imobilizado) + ' em aberto**')
        
        if base_dados.loc[item_index[0], 'Encontrado'] != 'Em aberto':
            visualizar = st.checkbox('Visualizar inventário')
            if visualizar:
                inventário(base_dados, item_index, False, None, None, None, equipamento_sap)
        
        st.subheader('Preenchimento do inventário')
        st.write(equipamento_sap)
        equip_encontrado = st.selectbox('Equipamento encontrado?', ['Sim', 'Não'])
        dicionario = {}

        with st.form(key='myform'):

            if equip_encontrado == 'Sim':
                data_inventario  = str(st.date_input('Data do inventário'))
                dicionario['Data do inventário']  = data_inventario.split('-')[2] + '/' + data_inventario.split('-')[1] + '/' + data_inventario.split('-')[0]
                dicionario['Marca'] = st.text_input('Marca do equipamento', base_dados.loc[item_index[0],'Marca'])
                dicionario['Modelo'] = st.text_input('Modelo do equipamento', base_dados.loc[item_index[0],'Modelo'])
                dicionario['Ativo'] = st.selectbox('Equipamento Ativo?', ['Sim', 'Não']) #base_dados.loc[item_index[0].index,'Local da instalacao'])
                dicionario['Encontrado']  = 'Sim'

                st.subheader('Foto do equipamento')
                im1 = st.file_uploader('Selecione a foto do equipamento')

                st.subheader('Foto da plaqueta do equipamento')
                im2 = st.file_uploader('Selecione a foto da plaqueta')

                st.subheader('Foto da TAG (Amarela)') 
                im3 = st.file_uploader('Selecione a foto da TAG (Amarela)')

                if im1 != None:
                    dicionario['Foto equipamento'] = im1.getvalue()

                if im2 != None:
                    dicionario['Foto da TAG'] = im2.getvalue()

                if im3 != None:
                    dicionario['Foto da TAG (Amarela)'] = im3.getvalue()
            else:
                data_inventario  = str(st.date_input('Data do inventário'))
                dicionario['Data do inventário']  = data_inventario.split('-')[2] + '/' + data_inventario.split('-')[1] + '/' + data_inventario.split('-')[0]
                dicionario['Marca'] = ''
                dicionario['Modelo'] = ''
                dicionario['Ativo'] = 'Não'  
                dicionario['Encontrado']  = 'Não'   
        
            submit_button = st.form_submit_button(label='Enviar formulário')

            if submit_button:
                base_dados.loc[item_index, 'Data do inventário'] = dicionario['Data do inventário']
                base_dados.loc[item_index, 'Encontrado'] = dicionario['Encontrado']
                base_dados.loc[item_index, 'Ativo'] = dicionario['Ativo']
                base_dados.loc[item_index, 'Marca'] = dicionario['Marca']
                base_dados.loc[item_index, 'Modelo'] = dicionario['Modelo']
                base_dados.to_parquet('base_dados.parquet')

                st.success('Item inserido com sucesso!')
                if equip_encontrado == 'Sim':
                    inventário(base_dados, item_index, True, im1, im2, im3, equipamento_sap)
                else:
                    inventário(base_dados, item_index, True, None, None, None, equipamento_sap)
                time.sleep(3)
                st.experimental_rerun()

    else:
        st.error('Não há equipamentos na base de dados. É necessário importar a base de dados!')

def atualizar_base(df_base, df_not):
    """ 
    Inclui na base validada itens da nao validada. Pode-se alterar a linha/area e o nome do equipamento

    Args:
        df_base ([dataframe]): [base validada]
        df_not ([dataframe]): [base nao validada]
    """    
    st.subheader('Inserir itens na base de dados')
    
    plantas_base = list(df_not.Planta.unique())
    planta = st.selectbox('Selecione a planta', plantas_base)

    linhas_base = list(df_not.loc[df_not['Planta'] == planta, 'Linha'].unique())
    linha = st.selectbox('Selecione a área', linhas_base)

    equip_base = list(df_not.loc[(df_not['Linha'] == linha) & (df_not['Planta'] == planta), 'Equipamento'].unique())
    equipamento = st.selectbox('Selecione o equipamento', equip_base)

    imob_base = list(df_not.loc[(df_not['Linha'] == linha) & (df_not['Equipamento'] == equipamento) & (df_not['Planta'] == planta), 'Imob'].unique())

    imobilizado = ''
    if len(imob_base) > 1:
        imobilizado = st.selectbox('Selecione o imobilizado', imob_base)
    else:
        imobilizado = imob_base[0]
        st.info('**Imobilizado:** ' + str(imobilizado))

    item_index = list(df_not.loc[(df_not['Imob'] == imobilizado) & (df_not['Linha'] == linha) & (df_not['Equipamento'] == equipamento) & (df_not['Planta'] == planta)].index)

    alterar_campos = st.checkbox('Corrigir área/equipamento?')
    campos_alterados = df_not.loc[item_index, :]

    if alterar_campos:
        linha = st.text_input('Área', linha)
        campos_alterados.loc[item_index, 'Linha'] = removedor_acentos(linha)
        equipamento = st.text_input('Equipamento', equipamento)
        campos_alterados.loc[item_index, 'Equipamento'] = removedor_acentos(equipamento)
        campos_alterados.loc[item_index, 'Denominacao'] = removedor_acentos(planta) + '-' + linha + '-' + removedor_acentos(equipamento)
        campos_alterados.loc[item_index, 'ID'] = campos_alterados.loc[item_index, 'Denominacao'] + '-' + campos_alterados.loc[item_index, 'Imob'].astype('str') + '-' + campos_alterados.loc[item_index, 'Sbn'].astype('str')

    incluir = st.button("Confirmar inclusão")
    if incluir:

        if campos_alterados[campos_alterados['Imob'].isin(df_base['Imob'])].shape[0] == 0:
            df_base = df_base.append(campos_alterados)
            df_base.to_parquet('base_dados.parquet')
            df_not = df_not.drop(item_index)
            df_not.to_parquet('nao_validados.parquet')
            st.success('Equipamento movido para a base de dados')
            time.sleep(2)
            st.experimental_rerun()
        else:
            st.error('Imobilizado já está presente na base de dados')

        
def importar_base(file_exists, file_exists2, df_importar_base):
    """
    Importa a base de dados a partir de uma arquivo excel. A base pode ser incluida integralmente,
    caso nao haja dados no sistema, ou filtrada e concatenada a base atual.
    Adiciona novas colunas para o preenchimento do inventario e algumas outras para o controle interno.

    Args:
        file_exists ([bool]): [booleano que informa se o arquivo da base de dados existe ou nao]
        file_exists2 ([bool]): [booleano que informa se o arquivo da base nao validada existe ou nao]
        df_importar_base ([bool]): [dataframe gerado a partir do arquivo excel]
    """    
    colunas_novas = ['Empre', 'Imob', 'Sbn', 'Classe', 'Data', 'Denominacao', 'Div', 'Centro_custo', 'Justificativa']
    df_importar_base = df_importar_base.iloc[:,[0,1,2,3,4,5,8,9,10]]

    colunas_excel = df_importar_base.columns
    dicionario = {}

    for coluna_excel, coluna_nova in zip(colunas_excel, colunas_novas):
        dicionario[coluna_excel] = coluna_nova

    df_importar_base.rename(columns=dicionario, inplace=True)
    df_importar_base['Data do inventário'] = ''
    df_importar_base['Marca'] = ''
    df_importar_base['Modelo'] = ''
    df_importar_base['Ativo'] = 'Em aberto'
    df_importar_base['Encontrado']  = 'Em aberto'
    
    # converte campo da data para string
    df_importar_base.iloc[:,4] = df_importar_base.iloc[:,4].astype(str)
    
    # confere o tamanho da string
    if len(df_importar_base.iloc[0,4]) == 8:
        df_importar_base.iloc[:,4] =  df_importar_base.iloc[:,4].str[6:8] + '/' + df_importar_base.iloc[:,4].str[4:6] + '/' + df_importar_base.iloc[:,4].str[:4]

    no_padrao = df_importar_base[df_importar_base['Denominacao'].str.match(r'^\w\w-\d\d\d\d\d-')]
    linha = no_padrao.iloc[0,5]
    linha = linha[:3]

    df_importar_base.loc[~df_importar_base['Denominacao'].str.match(r'^\w\w-\d\d\d\d\d-'), 'Denominacao'] = df_importar_base.loc[~df_importar_base['Denominacao'].str.match(r'^\w\w-\d\d\d\d\d-'), 'Denominacao'].str.replace('-', '_')
    fora_padrao = list(df_importar_base[~df_importar_base['Denominacao'].str.match(r'^\w\w-\d\d\d\d\d-')].index)
    df_importar_base.iloc[fora_padrao, 5] = linha + '00000-' + df_importar_base.iloc[fora_padrao, 5]
    df_importar_base['Denominacao'] = df_importar_base['Denominacao'].map(lambda x: removedor_acentos(x))
    df_importar_base['ID'] = df_importar_base.iloc[:, 5].astype(str) + '_' + df_importar_base.iloc[:, 1].astype(str) + '_' + df_importar_base.iloc[:, 2].astype(str)

    st.subheader('Dados encontrados na planilha')
    st.write(df_importar_base)

    # gravar base de dados
    if 'gravar_base' not in st.session_state:
        st.session_state['gravar_base'] = False	

    # confirmar 
    if 'confirmar_gravar_base' not in st.session_state:
        st.session_state['confirmar_gravar_base'] = False

    if not st.session_state.gravar_base:
        gravar = st.button('Gravar base de dados')
        if gravar:
            st.session_state['gravar_base'] = True
            st.experimental_rerun()

    if st.session_state.gravar_base:
        confirmar = st.button('Confirmar base de dados')
        if confirmar:
            st.session_state['confirmar_gravar_base'] = True
            st.session_state['gravar_base'] = False

        cancelar = st.button('Cancelar gravacao')
        if cancelar:
            st.session_state['gravar_base'] = False
            st.experimental_rerun()

    if st.session_state.confirmar_gravar_base:
        st.session_state['gravar_base'] = False	
        st.session_state['confirmar_gravar_base'] = False

        caminho_sap = df_importar_base['Denominacao'].str.split('-', n=3, expand=True)
        df_importar_base['Planta'] = caminho_sap[0]
        df_importar_base['Linha'] = caminho_sap[1]
        df_importar_base['Equipamento'] = caminho_sap[2]

        df_importar_base.loc[:,'Justificativa'] = df_importar_base.loc[:,'Justificativa'].str.upper()
        df_base_dados_val = df_importar_base.loc[df_importar_base['Justificativa'] == 'SIM'] 
        df_base_dados_not = df_importar_base.loc[df_importar_base['Justificativa'] != 'SIM']

        if file_exists:
            df_base_atual = pd.read_parquet('base_dados.parquet')
            to_include = df_base_dados_val[~df_base_dados_val['ID'].isin(df_base_atual['ID'])]
            df_base_dados_val = df_base_atual.append(to_include,ignore_index=True)

        if file_exists2:
            df_nao_validados = pd.read_parquet('nao_validados.parquet')
            to_include = df_base_dados_not[~df_base_dados_not['ID'].isin(df_nao_validados['ID'])]
            df_base_dados_not = df_nao_validados.append(to_include,ignore_index=True)

        df_base_dados_val.to_parquet('base_dados.parquet')
        df_base_dados_not.to_parquet('nao_validados.parquet')
        time.sleep(1)
        st.experimental_rerun()     


def ler_base():
    pass


def exportar_base(base_dados, colunas_saida):
    """
    Gera graficos para acompanhamento do processo do inventario
    Exporta inventario em CSV, Excel e html

    Args:
        base_dados ([dataframe]): [base de dados atual]
    """    
    st.subheader('Acompanhamento do inventário')
    st.write(
    """
    Gráfico para acompanhamento do inventário

    * Em aberto: Ainda não inventariado
    * Sim: Inventariado e encontrado
    * Não:  Inventariado e não encontrado
    """)

    colors = ['rgb(243,235,189)', '#ffc1cc', 'rgb(163,224,163)', 'lightblue']
    x_ = ['Em aberto', 'Não', 'Sim', 'Total']
    y_ = []
    y_.append(base_dados.loc[base_dados['Encontrado'] == 'Em aberto', 'Imob'].nunique())
    y_.append(base_dados.loc[base_dados['Encontrado'] == 'Nao', 'Imob'].nunique())
    y_.append(base_dados.loc[base_dados['Encontrado'] == 'Sim', 'Imob'].nunique())
    y_.append(base_dados['Imob'].nunique())
    maximo = y_[3] * 1.2

    fig = go.Figure(data=[go.Bar(y=y_, x=x_, name='Produção (x100k)', text=y_, marker_color=colors)])

    fig.update_layout(
        yaxis_range=[0,maximo],
		bargap=0.1,
		width=400, 
		height=300,
		margin=dict(b=5,	t=5,	l=0,	r=0))

    fig.update_traces(textposition='outside', textfont_color='rgb(0,0,0)', textfont_size=16)
    st.write(fig)

    st.subheader('Exportar inventário')

    st.write(
    """
    Exporta o banco de dados do inventário nos formatos:
    * CSV
    * Excel
    * Report em html
    """)

    st.subheader('Inventário em csv')
    base_dados[colunas_saida].to_csv('inventario.csv')
    with open("inventario.csv", "rb") as file:
        st.download_button('Download csv', file, file_name='inventario.csv', mime='text/csv')

    st.subheader('Inventário em Excel')
    base_dados[colunas_saida].to_excel('inventario.xlsx')
    with open("inventario.xlsx", "rb") as file:
        st.download_button('Download Excel', file, file_name='inventario.xlsx', mime='text/xlsx')

    st.subheader('Inventário em html')
    html_report(base_dados)
    with open("inventario.html", "rb") as file:
        st.download_button('Download HTML', file, file_name='inventario.html', mime='text/html')


def suporte():
    pass


def inventário(base_dados, item_index, escrita, im1, im2, im3, equipamento_sap):
 
    for coluna in base_dados.columns:
        campo, valor = st.columns(2)
        campo.write(''.join(('**', coluna, ':** ')))
        valor.write(str(base_dados.loc[item_index[0], coluna]))

    if base_dados.loc[item_index[0], 'Encontrado'] == 'Sim':
        arquivo1 = ''.join(('fotos/', equipamento_sap, '_1.jpeg'))
        if (im1 is not None) and escrita:
            file_bytes1 = Image.open(io.BytesIO(im1.getvalue()))
            file_bytes1.save(arquivo1)

        st.write('**Foto Equipamento armazenada:**')
        if exists(arquivo1):
            st.image(arquivo1)
        else:
            st.warning('Imagem nao inserida')

        arquivo2 = ''.join(('fotos/', equipamento_sap, '_2.jpeg'))

        if (im2 is not None) and escrita:
            file_bytes2 = Image.open(io.BytesIO(im2.getvalue()))
            file_bytes2.save(arquivo2)

        st.write('**Foto TAG armazenada:**')
        if exists(arquivo2):
            st.image(arquivo2)
        else:
            st.warning('Imagem nao inserida')

        arquivo3 = ''.join(('fotos/', equipamento_sap, '_3.jpeg'))
        if (im3 is not None) and escrita:
            file_bytes3 = Image.open(io.BytesIO(im3.getvalue()))
            file_bytes3.save(arquivo3)

        st.write('**Foto TAG (amarela) armazenada:**')
        if exists(arquivo3):
            st.image(arquivo3)
        else:
            st.warning('Imagem nao inserida')


######################################################################################################
                               #main
######################################################################################################


if __name__ == '__main__':

    main()

