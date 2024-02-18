import os
import win32com.client
import xml.etree.ElementTree as ET
from xml.dom import minidom
import shutil
import time
from collections import deque

# Classes:

def concatenar_lista(lista, sep="\n", ignorar_vazio=True):
    """Concatena as strings dentro de uma lista e retorna uma string"""
    frase = ""
    for palavra in lista:
        if not ignorar_vazio or palavra != "":
            frase += palavra + sep
    
    return frase[:-len(sep)]


def concatenar_listas(lista1, lista2):
    """Concatena as duas listas, retornando uma lista"""
    lista_temp = []
    for lista in (lista1, lista2):
        for item in lista:
            lista_temp.append(item)

    return lista_temp


def add_fotos_xml(lista_fotos):
    global fotos_xml
    global root
    for foto in lista_fotos:
        fotos_xml.append(foto)
        new_elem = ET.Element("Foto")
        root.append(new_elem)
        new_elem.set("Nome", foto)


class Foto:
    def __init__(self, path):
        self.nome_completo = path
        self.nome_base = self.nome_completo.split("\\")[-1]
        self.nome_atalho = self.nome_base + ".lnk"
        self.nome_apresentavel = "; " + self.nome_atalho
        self.tags = []
        elems = [elemento for elemento in root.findall('.//Foto') if elemento.get('Nome') == self.nome_base]
        if elems == []:
            add_fotos_xml([self.nome_base])

        self.elem = [elemento for elemento in root.findall('.//Foto') if elemento.get('Nome') == self.nome_base][0]
        self.popular_tags()
        self.set_nome_apresentavel()
    
    def popular_tags(self):
        elems_tags_foto = self.elem.findall('Tag')
        for elem in elems_tags_foto:
            self.tags.append(elem.text)

    def set_nome_apresentavel(self):
        self.nome_apresentavel = concatenar_lista(self.tags, ", ") + "; " + self.nome_atalho
    
    def add_tag(self, tag):
        if tag not in self.tags:
            new_tag = ET.Element("Tag")
            self.elem.append(new_tag)
            new_tag.text = tag
            self.tags.append(tag)
            self.set_nome_apresentavel()
    
    def delete_tag(self, tag):
        lista_elem_tag_foto = [elem_tag for elem_tag in self.elem.findall("Tag") if elem_tag.text == tag]
        if len(lista_elem_tag_foto) > 0:
            self.elem.remove(lista_elem_tag_foto[0])
            self.tags.remove(tag)
            self.set_nome_apresentavel()


class Fotos:
    def __init__(self, path_dir_base):
        self.paths_fotos = [os.path.join(path_base, nome) for nome in os.listdir(path_dir_base)]
        self.fotos = []
        self.popular_fotos()
    
    def popular_fotos(self):
        for path in self.paths_fotos:
            self.fotos.append(Foto(path))
    
    def select_foto(self, nome):
        for foto in self.fotos:
            if nome == foto.nome_atalho:
                return foto
        

#===================================================================================================================================

# Parte OS 1:

path_atual = os.path.abspath(__file__)
path_root = os.path.dirname(path_atual)
path_xml = os.path.join(path_root, "base.xml")
if os.path.isfile(path_xml):
    pass

else:
    arq = open(path_xml, "w")
    arq.write("<Root></Root>")
    arq.close()
    

tree = ET.parse(path_xml)
root = tree.getroot()
path_base = os.path.join(path_root, "Base")
path_classi = os.path.join(path_root, "Classificador")
path_res = os.path.join(path_root, "Resultado")
path_tags = os.path.join(path_root, "Tags")
path_retirar = os.path.join(path_root, "Retirar Tag")
if os.path.isdir(path_tags):
    pass
  
else:
    os.mkdir(path_tags)

tags = os.listdir(path_tags)
paths_tags_list = [os.path.join(path_tags, pt) for pt in os.listdir(path_tags)]
if os.path.isdir(path_retirar):
    pass
    
else:
    os.mkdir(path_retirar)

paths_retirar_tags_list = [os.path.join(path_retirar, pt) for pt in os.listdir(path_retirar)]
candidatos = {}
if os.path.isdir(path_base):
    pass
    
else:
    os.mkdir(path_base)


fotos_xml = [elemento for elemento in root]
obj_fotos = Fotos(path_base)
shell = win32com.client.Dispatch("WScript.Shell")
Log = type("Log", (), {"__init__": (lambda self: exec("self.log = deque(maxlen=5)"))})
log = Log()
Ultima = type("Ultima", (), {"__init__": (lambda self: exec("self.ult = ''"))})  # Registra a ultima query
ultima = Ultima()
Equivalente = type("Equivalente", (), {"__init__": (lambda self: exec("self.equi = ''"))})  # Registra a query equivalente à seleção de tags
equivalente = Equivalente()
count = 0
count_equi = 0


def checar_estrutura():
    if os.path.isdir(path_classi):
        pass
    
    else:
        os.mkdir(path_classi)

    
    if os.path.isdir(path_res):
        pass
    
    else:
        os.mkdir(path_res)


def criar_atalho(path_original, path_novo):
    atalho = shell.CreateShortcut(path_novo)
    atalho.TargetPath = path_original
    atalho.Save()


class Predicado:
    def __init__(self, pred):
        self.pred = pred
    
    def __call__(self, x):
        return self.pred(x)
    
    def __add__(self, alvo):
        return lambda x: self.pred(x) or alvo(x)
    
    def __mul__(self, alvo):
        return lambda x: self.pred(x) and alvo(x)
    

def traduzir(query:str):
    sep = " "
    query = query.replace("(", " ( ").replace(")", " ) ")
    lista_query = query.split(sep)
    nova_query = ""
    for palavra in lista_query:
        palavra = str.lower(palavra)
        if palavra == "e":
            nova_query += "and"
        
        elif palavra == "nao":
            nova_query += "not"
        
        elif palavra == "ou":
            nova_query += "or"
        
        elif palavra == "(" or palavra == ")":
            nova_query += palavra
        
        elif palavra in [str.lower(tag) for tag in tags]:
            nova_query += "'" + palavra + "' in x"
        
        nova_query += sep

    return nova_query


def checar_divergs(lista1, lista2):
    """checa as divergencias entre duas listas. Retorna (divs1, divs2)"""
    divs1 = [item for item in lista1 if item not in lista2]
    divs2 = [item for item in lista2 if item not in lista1]
    return divs1, divs2


def checar_fotos_base():
    """retorna (fotos_novas, fotos_deletadas).
    fotos_novas estão na variavel obj_fotos.fotos mas não estão na variavel fotos_xml.
    obj_fotos.fotos deletadas não estão na variavel obj_fotos.fotos mas estão na variavel fotos_xml."""
    # fotos_novas = [item for item in obj_fotos.fotos if item not in fotos_xml]
    # fotos_deletadas = [item for item in fotos_xml if item not in obj_fotos.fotos]
    fotos_novas, fotos_deletadas = checar_divergs(obj_fotos.fotos, fotos_xml)
    return fotos_novas, fotos_deletadas


def ler_format_dir(path):
    """le e formata o conteudo de um diretório de atalhos"""
    arqs = os.listdir(path)
    arqs_formatados = [arq.split("; ")[1] for arq in arqs]
    return arqs_formatados

#===================================================================================================================================

# Parte XML 1:

def salvar_xml(nome):
    xml_list = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ").split("\n")[1:]
    xml_string = ""
    for linha in xml_list:
        if linha != "" and linha != "  " and linha != "    ":
            xml_string += linha + "\n"

    with open(nome, "w", encoding="utf-8") as file:
        file.write(xml_string)


salvar_xml(path_xml)


def select_foto(nome):
    elems = [elemento for elemento in root.findall('.//Foto') if elemento.get('Nome') == nome]
    return elems[0]


def select_tags(elem_foto):
    elems_tags_foto = elem_foto.findall('Tag')
    tags_foto = []
    for elem in elems_tags_foto:
        tags_foto.append(elem.text)

    return tags_foto


def delete_fotos_xml(lista_fotos):
    global fotos_xml
    for foto in lista_fotos:
        fotos_xml.remove(foto.nome_base)
        elem_alvo = root.find(".//Foto[@Nome='{}']".format(foto.elem.get("Nome")))
        root.remove(elem_alvo)


def checar_altera_base():
    """Busca o que mudou no dir Base em relação ao que está salvo na variável obj_fotos.fotos.
    obj_fotos.fotos divergentes serão acrescentadas ou retiradas da variavel obj_fotos.fotos, da variavel fotos_xml e do xml.
    Util apenas quando uma foto é alterada inicialmente no dir Base."""
    global obj_fotos
    global log
    novo_fotos = os.listdir(path_base)
    divs_add, divs_del = checar_divergs(novo_fotos, [foto.nome_base for foto in obj_fotos.fotos])
    add_fotos_xml(divs_add)
    delete_fotos_xml(divs_del)
    obj_fotos.fotos = concatenar_listas(obj_fotos.fotos, divs_add)
    for foto in obj_fotos.fotos:
        if foto in divs_del:
            obj_fotos.fotos.remove(foto)
    
    tamanho_add = len(divs_add)
    tamanho_del = len(divs_del)
    texto_log_add = ""
    texto_log_del = ""
    if tamanho_add > 0:
        texto_log_add = "{0} fotos foram adicionadas.".format(tamanho_add)
    
    if tamanho_del > 0:
        texto_log_del = "{0} fotos foram deletadas.".format(tamanho_del)
    
    if tamanho_add + tamanho_del == 0:
        pass

    elif tamanho_add == 0 or tamanho_del == 0:
        log.log.append(texto_log_add + texto_log_del)
    
    else:
        log.log.append(texto_log_add + ". " + texto_log_del)


checar_altera_base()

def checar_altera_fotos():
    """Busca o que mudou na variavel obj_fotos.fotos em relação a variavel fotos_xml.
    obj_fotos.fotos divergentes serão acrescentadas ou retiradas da variavel fotos_xml, do dir Base e do XML.
    Util apenas quando uma foto é alterada inicialmente na variavel obj_fotos.fotos."""
    global log
    fotos_novas, fotos_deletadas = checar_fotos_base()
    tamanho_add = len(fotos_novas)
    tamanho_del = len(fotos_deletadas)
    add_fotos_xml(fotos_novas)
    delete_fotos_xml(fotos_deletadas)
    texto_log_add = ""
    texto_log_del = ""
    if tamanho_add > 0:
        texto_log_add = "{0} fotos foram adicionadas.".format(tamanho_add)
    
    if tamanho_del > 0:
        texto_log_del = "{0} fotos foram deletadas.".format(tamanho_del)
    
    if tamanho_add + tamanho_del == 0:
        pass

    elif tamanho_add == 0 or tamanho_del == 0:
        log.log.append(texto_log_add + texto_log_del)
    
    else:
        log.log.append(texto_log_add + ". " + texto_log_del)


def retornar_deslocados(deslocados):
    """Pega uma lista de obj_fotos.fotos deslocadas do seu dir de origem, infere qual dir era esse e devonve tais obj_fotos.fotos"""
    # Se o primeiro deslocado (exemplo) da lista veio de um dir, todo os outros vieram do mesmo dir
    if len(deslocados) > 0:
        exemplo = deslocados[0][0]
        caminho_retorno = ""
        if exemplo.split("; ")[1] not in ler_format_dir(path_classi):
            caminho_retorno = path_classi
        
        else:
            caminho_retorno = path_res

        for deslocado_cru, path_tag in deslocados:
            tag = path_tag.split("\\")[-1]

            #nome = ""
            #tags_foto_atual = deslocado.split("; ")[0].split(", ")
            #if tag not in tags_foto_atual:
                #tags_foto_atual.append(tag)
                #nome = concatenar_lista(tags_foto_atual, ", ") + "; " + deslocado.split("; ")[1]
            
            #else:
                #nome = deslocado
            
            deslocado_nome = deslocado_cru.split("; ")[1]
            foto_atual = obj_fotos.select_foto(deslocado_nome)
            os.rename(os.path.join(path_tag, deslocado_cru), os.path.join(caminho_retorno, foto_atual.nome_apresentavel))


def classificar_candidatos():
    """Encontra, classifica e retorna os candidatos para seus diretorios de origem"""
    global log
    global count
    time.sleep(0.005)
    if count >= 100:
        tamanho = 0
        fotos_deslocadas = []

        for pt in paths_tags_list:
            arquivos_crus = os.listdir(pt)
            nomes_fotos = [arq.split("; ")[1] for arq in arquivos_crus]
            tamanho += len(nomes_fotos)
            candidatos[os.path.basename(pt)] = nomes_fotos
            for arq in arquivos_crus:
                fotos_deslocadas.append((arq, pt))
        
        for pt in paths_retirar_tags_list:
            arquivos_crus = os.listdir(pt)
            nomes_fotos = [arq.split("; ")[1] for arq in arquivos_crus]
            tamanho += len(nomes_fotos)
            candidatos[os.path.basename(pt)] = nomes_fotos
            for arq in arquivos_crus:
                fotos_deslocadas.append((arq, pt))

        for tag, classi_lista in candidatos.items():
            if "Retirar_" not in tag:
                for nome_foto in classi_lista:
                    obj_foto = obj_fotos.select_foto(nome_foto)
                    obj_foto.add_tag(tag)
            
            else:
                for nome_foto in classi_lista:
                    obj_foto = obj_fotos.select_foto(nome_foto)
                    obj_foto.delete_tag(tag[8:])
        
        retornar_deslocados(fotos_deslocadas)

        if len(fotos_deslocadas) > 0:    
            log.log.append("Tags modificadas em {} fotos".format(tamanho))
            salvar_xml(path_xml)
        
        count = 0
    
    else:
        count += 1
    

def tem_tags(elem, pred):
    return pred(select_tags(elem))



#===================================================================================================================================

# Parte Rotina Inicial:

def redefinir_classi():
    shutil.rmtree(path_classi) # deleta o diretorio Classificador
    os.mkdir(path_classi) # refaz o diretorio Classificador

    # atalhos de diretorios Tags
    """
    for tag in tags:
        candidatos[tag] = []
        paths_tags_list.append(os.path.join(path_tags, tag))
        criar_atalho(os.path.join(path_tags, tag), os.path.join(path_classi, tag + ".lnk"))
        """

    # atalhos de obj_fotos.fotos
    for foto in obj_fotos.fotos:
        criar_atalho(os.path.join(path_base, foto.nome_base), os.path.join(path_classi, foto.nome_apresentavel))


checar_estrutura()
redefinir_classi()

#===================================================================================================================================

# Parte Front 1:

import pygame

pygame.init()
pygame.font.init()

class Grupo:
    # agrupa objetos Janela a serem usados pelo programa. contem metodos para
    # adicionar mais janelas e alterar a janela sendo visualizada
    def __init__(self):
        self.janelas = []
        self.main_janela = None
    
    def adicionar_janelas(self, janelas:list):
        """recebe uma lista de objetos Janela e adiciona-os no grupo"""
        for janela in janelas:
            self.janelas.append(janela)
    
    def trocar_janela(self, alvo:str):
        """recebe o nome de uma janela e torna essa janela como principal se
        for encontrada"""
        for janela in self.janelas:
            if janela.nome == alvo:
                if self.main_janela is not None:
                    self.main_janela.run = False

                self.main_janela = janela
                self.main_janela.iniciar()
                break
    
    def main_loop(self):
        """o loop principal o qual permite que o loop de uma janela seja
        terminado pela função trocar_janela e outro seja iniciado. se o
        loop da interface for terminado pois a janela foi fechada, o loop
        do grupo é terminado tbm"""
        run = True
        while run:
             novo_run = self.main_janela.main_loop()
             if novo_run == False:
                 run = False


class Janela:
    """padroniza o comportamento de uma janela, a interface"""
    def __init__(self, w: int, h: int, nome: str, steps:list=None):
        """recebe a largura, altura, o nome da janela e uma lista de
        funções para serem rodadas dentro do main loop"""
        self.w = w
        self.h = h
        self.nome = nome
        self.botoes = [] # lista de botões da janela
        self.textos = [] # lista de textos da janela
        self.inputs = [] # lista de inputs de texto da janela
        self.quads = []
        self.inpu = None
        self.run = False
        self.steps = steps

    def iniciar(self):
        """inicia a janela, atribui o titulo, dimensoes e fonte"""
        self.disp = pygame.display
        self.disp.set_caption(self.nome)
        self.screen = self.disp.set_mode((self.w, self.h))
        self.fonte = pygame.font.SysFont('arial', 25)

    def addBotões(self, bots: list):
        """adiciona os botões de uma lista a janela"""
        for bot in bots:
            self.botoes.append(bot)
    
    def substBotão(self, bot):
        """substitui um botão se possivel, se não existir previamente adiciona um novo"""
        for i, b in enumerate(self.botoes):
            if b.nome == bot.nome:
                self.botoes[i] = bot
            
            else:
                self.addBotões([bot])

    def addTextos(self, textos: list):
        """adiciona os textos de uma lista a janela"""
        for texto in textos:
            self.textos.append(texto)

    def substTexto(self, texto):
        """substitui ou adiciona um texto a janela"""
        for i, t in enumerate(self.textos):
            if t.nome == texto.nome:
                self.textos[i] = texto
            
            else:
                self.addTextos([texto])

    def addInputs(self, inputs: list):
        """adiciona os inputs de texto de uma lista a janela"""
        for inpu in inputs:
            self.inputs.append(inpu)
    
    def addQuads(self, quads: list):
        """adiciona os botões de uma lista a janela"""
        for quad in quads:
            self.quads.append(quad)

    def click(self, pos):
        """recebe uma posição do mouse (onde houve um click) e procura o primeiro
        botão e input que compreendem essa posição em sua area para ativar um evento"""
        for bot in self.botoes: # checa os botões
            limite_x = (pos[0] >= bot.campo_min[0]
                        and pos[0] <= bot.campo_max[0])
            limite_y = (pos[1] >= bot.campo_min[1]
                        and pos[1] <= bot.campo_max[1])
            if limite_x and limite_y: # se o botão for localizado seu evento é ativado e o loop é quebrado
                bot.click()
                break

        for inpu in self.inputs:
            limite_x = (pos[0] >= inpu.campo_min[0]
                        and pos[0] <= inpu.campo_max[0])
            limite_y = (pos[1] >= inpu.campo_min[1]
                        and pos[1] <= inpu.campo_max[1])
            if limite_x and limite_y: # se o input for localizado ele é escolhido como input ativo da janela
                self.inpu = inpu
                break

        else: # se um input não for escolhido o input ativo é desselecionado
            self.inpu = None

    def atualizar_janela(self):
        """gera um novo frame para a janela e a atualiza"""
        self.screen.fill((200, 200, 200)) # cor de fundo
        for quad in self.quads: # printa na interface botao por botao
            pygame.draw.rect(self.screen, quad.cor, [
                             quad.x, quad.y, quad.w, quad.h])

        for texto in self.textos: # printa na interface texto por texto
            conteudo = texto.printar()
            for frase, posx, posy in conteudo:
                self.screen.blit(frase, (posx, posy))

        for bot in self.botoes: # printa na interface botao por botao
            pygame.draw.rect(self.screen, bot.cor, [
                             bot.x, bot.y, bot.w, bot.h])
            texto = bot.fonte.render(bot.conteudo, False, (10, 10, 10))
            self.screen.blit(texto, (bot.x + 5, bot.y))

        for inpu in self.inputs: # printa na interface input por input
            for i in range(inpu.maximo):
                letra = ""
                if i < len(inpu.amostra):
                    letra = inpu.amostra[i]

                inpu.gerar_amostra()
                pygame.draw.rect(self.screen, inpu.cor, [
                                 inpu.x + inpu.w * i, inpu.y, inpu.w, inpu.h])
                texto = inpu.fonte.render(letra, False, (10, 10, 10))
                self.screen.blit(texto, (inpu.x + inpu.w * i, inpu.y))

        if self.inpu is not None: # desenha o cursor do input selecionado se houver algum
            for i, letra in enumerate(self.inpu.input):
                local_escolhido = self.inpu.x + 5 + \
                    self.inpu.fonte.size(
                        self.inpu.amostra[:self.inpu.cursor])[0]
                local_escolhido = self.inpu.x + self.inpu.w * self.inpu.cursor - 1
                pygame.draw.rect(self.screen, [10, 10, 10], [
                                 local_escolhido, self.inpu.y, 1, self.inpu.h - 5])

        pygame.display.flip()

    def main_loop(self):
        """o loop principal da janela, onde a atualização da tela é chamada e
        eventos são lidos. Se a janela for fechada, o bool False é retornado"""
        self.run = True
        while self.run:
            self.atualizar_janela()
            if self.steps != None:
                for step in self.steps:
                    step()

            for event in pygame.event.get(): # filtragem de eventos
                if event.type == pygame.QUIT: # fechar a janela
                    self.run = False
                    return False

                elif event.type == pygame.MOUSEBUTTONUP: # click
                    pos = pygame.mouse.get_pos()
                    self.click(pos)

                elif event.type == pygame.KEYDOWN: # envio de caracteres ao input selecionado
                    numeros = "0123456789"
                    letras_min = "abcdefghijklmnopqrstuvwxyz"
                    letras_mai = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    especiais = "+-=*/,.()"
                    opções = numeros + letras_min + letras_mai + especiais # caracteres possiveis
                    if self.inpu is not None:
                        indice = self.inpu.cursor + self.inpu.indice_am # posição do cursor relativa a todo o seu conteudo

                    else:
                        indice = 0

                    if event.unicode in opções and event.unicode != "": # adicionando uma letra ao input
                        if self.inpu is not None:
                            self.inpu.input = self.inpu.input[:indice] + \
                                event.unicode + self.inpu.input[indice:]
                            self.inpu.cursor += 1

                    elif str(event.key) == "32": # adicionando 'espaço' ao input
                        if self.inpu is not None:
                            self.inpu.input = self.inpu.input[:indice] + \
                                " " + self.inpu.input[indice:]
                            self.inpu.cursor = min(
                                self.inpu.cursor + 1, len(self.inpu.amostra))

                    elif str(event.key) == "8": # usando 'backspace'
                        if self.inpu is not None:
                            fatia_ante = self.inpu.input[:indice - 1]
                            fatia_pos = self.inpu.input[indice:]
                            self.inpu.input = fatia_ante + fatia_pos
                            self.inpu.cursor = max(0, self.inpu.cursor - 1)

                    elif str(event.key) == "1073741904": # seta para esquerda
                        if self.inpu is not None:
                            self.inpu.cursor = self.inpu.cursor - 1
                            self.inpu.gerar_amostra()

                    elif str(event.key) == "1073741903": # seta para direita
                        if self.inpu is not None:
                            self.inpu.cursor = self.inpu.cursor + 1
                            self.inpu.gerar_amostra()

                    elif str(event.key) == "13":
                        pass


class Botao:
    """padroniza o comportamento de cada botão"""
    def __init__(self, x: int, y: int, w: int, h: int, conteudo: str,
                 nome: str, tamanho: int, cor: list, func, inputs: dict = {}):
        """recebe a posição do botão, suas dimensoes, seu conteudo a ser mostrado,
        seu nome a ser usado no programa, o tamanho da sua fonte, sua cor, um objeto
        'function' e os inputs (kwargs) de sua função"""
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.conteudo = conteudo
        self.nome = nome
        self.tamanho = tamanho
        self.cor = cor
        self.func = func
        self.inputs = inputs
        self.fonte = pygame.font.Font(None, tamanho)
        self.formatar()
        self.campo_min = [self.x, self.y] # area a ser considerada pelo click
        self.campo_max = [self.x + self.w, self.y + self.h]

    def formatar(self):
        """formata o botão para caber o texto, se as dimensoes foram zero"""
        if self.h == 0:
            self.h = self.fonte.size(self.conteudo)[1]

        if self.w == 0:
            self.w = self.fonte.size(self.conteudo)[0] + 10

    def click(self):
        """chama a função do botão com seus inputs"""
        self.func(**self.inputs)


class Texto:
    """padroniza o comportamento de cada texto"""
    def __init__(self, x: int, y: int, tamanho: int, conteudo: str, nome: str, maximo: int=None):
        """recebe a posição, tamanho da fonte, o conteudo do texto e o nome a ser
        usado internamente"""
        self.x = x
        self.y = y
        self.tamanho = tamanho
        self.conteudo = conteudo
        self.nome = nome
        self.fonte = pygame.font.Font(None, tamanho)
        self.maximo = maximo

    def printar(self):
        """formata o texto em uma lista de linhas e a retorna para ser printada na tela"""
        lista = []
        y = self.y
        if str(type(self.conteudo)) == "<class '__main__.Log'>":
            for _, linha in enumerate(self.conteudo.log):
                textsurface = self.fonte.render(linha, False, (10, 10, 10))
                lista.append([textsurface, self.x, y])
                y += self.tamanho

            return lista
        
        elif str(type(self.conteudo)) == "<class '__main__.Ultima'>":
            cont = self.conteudo.ult
        
        elif str(type(self.conteudo)) == "<class '__main__.Equivalente'>":
            cont = self.conteudo.equi
        
        else:
            cont = self.conteudo

        for texto in cont.split("\n"):
            textsurface = self.fonte.render(texto, False, (10, 10, 10))
            width = textsurface.get_rect().width
            if self.maximo is not None:
                while width > self.maximo:
                    texto = texto[:-1]
                    textsurface = self.fonte.render(texto, False, (10, 10, 10))
                    width = textsurface.get_rect().width

            lista.append([textsurface, self.x, y])
            y += self.tamanho

        return lista


class Inp:
    """padroniza o comportamento de cada input de texto"""
    def __init__(self, x: int, y: int, maximo: int, tamanho: int,
                 input: str = "", nome: str = ""):
        """recebe a posição, o maximo de caracteres viziveis, o tamanho da fonte,
        o conteudo default e o nome a ser usado internamente"""
        self.tamanho = tamanho
        self.fonte = pygame.font.Font(
            None, self.tamanho)
        self.x = x
        self.y = y
        self.maximo = maximo
        self.w = self.fonte.size("w")[0] + 1
        self.h = self.fonte.size("w")[1]
        self.cor = [245, 245, 245]
        self.input = input
        self.nome = nome
        self.cursor = 0 # posição do cursor
        self.indice_am = 0 # indice referente a primeira letra a mostra em relação ao conteudo inteiro
        self.amostra = self.input # a pequena amostra a qual ficara a mostra
        self.campo_min = [self.x, self.y] # area a ser considerada pelo click
        self.campo_max = [self.x + self.w * self.maximo, self.y + self.h]
    
    def clear(self):
        self.input = ""
        self.cursor = 0
        self.amostra = ""
        self.indice_am = 0

    def gerar_amostra(self):
        """gerar nova amostra de texto para acomodar uma mudança nos caracteres ou
        na posição do cursor"""
        self.amostra = self.input[self.indice_am:]
        if self.cursor < 0 and self.indice_am > 0: # se o cursor estiver fora da amostra para a esquerda
            self.indice_am += -1
            maximo = min(self.indice_am + self.maximo,
                         len(self.input) - self.indice_am)
            self.amostra = self.input[self.indice_am:maximo]
            self.cursor += 1

        elif self.cursor > self.maximo: # se o cursor estiver fora da amostra para a direita
            self.cursor += -1
            final = self.indice_am + self.maximo
            if final <= len(self.input):
                self.indice_am += 1
                self.amostra = self.input[self.indice_am:final]

        if len(self.amostra) > self.maximo: # se a amostra for maior do que a parmitida
            if self.cursor < self.maximo:
                self.amostra = self.amostra[:-1]

            elif self.cursor == self.maximo:
                self.amostra = self.amostra[1:]


class Quadrado:
    """padroniza o comportamento de quadrados"""
    def __init__(self, x: int, y: int, cor, cons:int=None, nome=None, w=None, h=None):
        """recebe a posição do quadrado, uma constante para suas dimensoes, 
        sua cor e seu nome"""
        self.x = x
        self.y = y
        if w is None:
            self.w = cons
        
        else:
            self.w = w

        if h is None:
            self.h = cons
        
        else:
            self.h = h

        self.cor = cor
        self.nome = nome


def filtrar_por_predicado(inp):
    ps = []
    exec("ps.append(Predicado(lambda x: {}))".format(traduzir(inp)))
    pred = ps[0]
    fotos_com_tags = [foto for foto in obj_fotos.fotos if pred([str.lower(tag) for tag in foto.tags])]
    return fotos_com_tags


def rodar_ger_equi(janela):
    global count_equi
    time.sleep(0.005)
    if count_equi >= 100:
        count_equi = 0
        gerar_equivalente(janela)

    else:
        count_equi += 1


def gerar_equivalente(janela):
    global equivalente
    for input in janela.inputs:
        if input.nome == "tags_obrig":
            alvo1 = input
        
        if input.nome == "tags_opcio":
            alvo2 = input

    obrig = alvo1.input
    opcio = alvo2.input
    obrig = obrig.replace(" ", "")
    opcio = opcio.replace(" ", "")
    obrig = obrig.replace(",", " e ")
    opcio = opcio.replace(",", " ou ")
    str_equivalente = ""
    if obrig != "":
        str_equivalente = obrig
        if opcio != "":
            str_equivalente += " e "
        
    
    if opcio != "":
        str_equivalente += "(" + opcio + ")"
    
    equivalente.equi = str_equivalente.lower()
    
    return str_equivalente, alvo1, alvo2


def nova_tag(**kwargs):
    """exemplo de função para ser usada em um botão"""
    global log
    janela = kwargs["janela"]
    alvo = None
    for input in janela.inputs:
        if input.nome == "add_tag":
            alvo = input

    tag = alvo.input
    alvo.clear()
    os.mkdir(os.path.join(path_tags, tag))
    os.mkdir(os.path.join(path_retirar, "Retirar_" + tag))
    tags.append(tag)
    tags.append("Retirar_" + tag)
    paths_tags_list.append(os.path.join(path_tags, tag))
    paths_retirar_tags_list.append(os.path.join(path_retirar, "Retirar_" + tag))
    log.log.append("Tag {} criada com sucesso.".format(tag))
          

def rodar_query(**kwargs):
    """exemplo de função para ser usada em um botão"""
    global log
    global ultima
    log.log.append("Executando Query...")
    import time
    time.sleep(1)
    janela = kwargs["janela"]
    alvo = None
    for input in janela.inputs:
        if input.nome == "inpu_query":
            alvo = input

    query = alvo.input
    alvo.clear()
    ultima.ult = query.lower()

    fotos_com_tags = filtrar_por_predicado(query)
    shutil.rmtree(path_res)
    os.mkdir(path_res)

    for foto in fotos_com_tags:
        criar_atalho(os.path.join(path_base, foto.nome_base), os.path.join(path_res, foto.nome_apresentavel))

    log.log.append("Query executada com sucesso.")


def rodar_query_novamente(**kwargs):
    """exemplo de função para ser usada em um botão"""
    global log
    log.log.append("Executando Query...")
    query = ultima.ult
    fotos_com_tags = filtrar_por_predicado(query)
    shutil.rmtree(path_res)
    os.mkdir(path_res)

    for foto in fotos_com_tags:
        criar_atalho(os.path.join(path_base, foto.nome_base), os.path.join(path_res, foto.nome_apresentavel))

    log.log.append("Query executada com sucesso.")


def rodar_equivalente(**kwargs):
    global log
    global ultima
    global equivalente
    log.log.append("Executando Query...")
    import time
    time.sleep(1)
    janela = kwargs["janela"]

    str_equivalente, alvo1, alvo2 = gerar_equivalente(janela)
    alvo1.clear()
    alvo2.clear()
    
    ultima.ult = str_equivalente.lower()

    fotos_com_tags = filtrar_por_predicado(str_equivalente)
    shutil.rmtree(path_res)
    os.mkdir(path_res)

    for foto in fotos_com_tags:
        criar_atalho(os.path.join(path_base, foto.nome_base), os.path.join(path_res, foto.nome_apresentavel))

    log.log.append("Query executada com sucesso.")



def refresh_classi(**kwargs):
    """exemplo de função para ser usada em um botão"""
    global log
    redefinir_classi()
    log.log.append("Classificador Recarregado")


def teste2(**kwargs):
    """exemplo de função para ser usada em um botão"""
    global log
    import random
    opts = ["a", "b", "c", "d", "e"]
    log.log.append("Escolhi: " + random.choice(opts) + random.choice(opts) + random.choice(opts))
    print(path_tags)


x_base = 25
y_base = 30
def setar(janela: Janela):
    x = x_base
    y = y_base
    text_titulo_add_tag = Texto(x, y, 30, "Nova Tag:", "titulo_add_tag")
    y += 30
    inpu_add_tag = Inp(x, y, 21, 30, "", "add_tag")
    y += 30
    bot_add_tag = Botao(x, y, 0, 0, "Adicionar Tag", "add_tag", 30,
                           [120, 120, 120], nova_tag, {"janela": janela})
    y += 100
    altura = 1
    quad_sep_tags = Quadrado(x, y, [10, 10, 10], w=350, h=altura)

    y += 10
    text_query = Texto(x, y, 30, "Query:", "query")
    y += 30
    inpu_query = Inp(x, y, 21, 30, "", "inpu_query")
    y += 30
    bot_rodar_query = Botao(x, y, 0, 0, "Rodar Query", "rodar_query", 30,
                           [120, 120, 120], rodar_query, {"janela": janela})

    y += 50
    dist1 = 120
    dist_ou = dist1 + 50
    text_ou = Texto(x + dist_ou, y, 25, "ou", "")
    altura = 1
    quad1 = Quadrado(x + dist1, y + 10 - altura, [10, 10, 10], w=40, h=altura)
    quad2 = Quadrado(x + dist_ou + 30, y + 10 - altura, [10, 10, 10], w=40, h=altura)

    y += 50
    text_obrig = Texto(x, y, 30, "Tags Obrigatorias:", "obrig")
    y += 30
    inpu_obrig = Inp(x, y, 21, 30, "", "tags_obrig")

    y += 50
    text_opcio = Texto(x, y, 30, "Tags Opcionais:", "opcio")
    y += 30
    inpu_opcio = Inp(x, y, 21, 30, "", "tags_opcio")

    y += 50
    text_equival = Texto(x, y, 30, "Equivalencia:", "equival")
    y += 30
    text_equival_conteudo = Texto(x + 5, y, 30, equivalente, "equival_conteudo", 350)
    espes = 2
    y += -espes*2
    w_base = 360
    h_base = 20 + espes*2
    quad_mold_fora = Quadrado(x, y, [30]*3, w=w_base, h=h_base)
    quad_mold_dentro = Quadrado(x + espes, y + espes, [180]*3, w=w_base - espes*2, h=h_base - espes*2)
    y += 40
    bot_rodar_equival = Botao(x, y, 0, 0, "Rodar Equivalente", "rodar_equival", 30,
                           [120, 120, 120], rodar_equivalente, {"janela": janela})

    # Segunda metade
    espes = 2
    x = 400 + y_base - 15
    y = y_base - espes
    w_base = 400 - 10 - 25
    h_base = 800 + espes*2
    quad_mold_fora2 = Quadrado(x, y, [30]*3, w=w_base, h=h_base)
    quad_mold_dentro2 = Quadrado(x + espes, y + espes, [180]*3, w=w_base - espes*2, h=h_base - espes*2)

    x += 5
    y += 5
    text_titulo_log = Texto(x, y, 30, "Log:", "titulo_log")
    y += 30
    text_log = Texto(x, y, 30, log, "log")
    y += 150
    quad3 = Quadrado(x - 5, y, [10, 10, 10], w=w_base, h=altura)

    y += 10
    text_titulo_views = Texto(x, y, 30, "Queries Salvas:", "titulo_views")
    y += 30
    text_views = Texto(x + 10, y, 30, "Nada Ainda", "log")

    y += 330 - 5
    altura = 1
    quad4 = Quadrado(x - 5, y, [10, 10, 10], w=w_base, h=altura)

    y += 10
    text_ult_query = Texto(x, y, 30, "Última Query Executada:", "ult_query")
    y += 40
    text_ult_query_conteudo = Texto(x + 5, y, 30, ultima, "ult_query_conteudo", 350)
    espes = 2
    y += -espes*2
    w_base = 359
    h_base = 20 + espes*2
    quad_mold_fora3 = Quadrado(x, y, [30]*3, w=w_base, h=h_base)
    quad_mold_dentro3 = Quadrado(x + espes, y + espes, [180]*3, w=w_base - espes*2, h=h_base - espes*2)
    y += 40
    bot_rodar_ult_query = Botao(x, y, 0, 0, "Rodar Novamente", "rodar_ult_query", 30,
                           [120, 120, 120], rodar_query_novamente, {"janela": janela})
    
    y += 70
    text_nome_vista = Texto(x, y, 30, "Salvar Query como:", "nome_vista")
    y += 30
    inpu_nome_vista = Inp(x, y, 21, 30, "", "nome_vista ")
    y += 30
    bot_salvar_vista = Botao(x, y, 0, 0, "Salvar", "salvar_vista", 30,
                           [120, 120, 120], teste2, {"janela": janela})



    janela.addBotões([bot_add_tag, bot_rodar_query, bot_rodar_equival, bot_rodar_ult_query, bot_salvar_vista])
    janela.addQuads([quad_sep_tags, quad1, quad2, quad_mold_fora, quad_mold_dentro, quad_mold_fora2, quad_mold_dentro2, quad3, quad4, quad_mold_fora3, quad_mold_dentro3])
    janela.addInputs([inpu_add_tag, inpu_query, inpu_obrig, inpu_opcio, inpu_nome_vista])
    janela.addTextos([text_titulo_add_tag, text_query, text_ou, text_obrig, text_opcio, text_equival, text_equival_conteudo, text_titulo_log, text_log, text_titulo_views, text_views, text_ult_query, text_ult_query_conteudo, text_nome_vista])


def iniciar_front():
    """inicia objetos Janela e um objeto Grupo, seta suas caracteristicas iniciais, 
    assim como seu botões, textos inputs e imagens. retorna o objeto Grupo com
    as janelas armazenadas"""
    global grupo
    grupo = Grupo()
    janela = Janela(800, 900, "menu", [classificar_candidatos])
    janela.steps.append(lambda: rodar_ger_equi(janela))
    janela.count = 0
    grupo.adicionar_janelas([janela])
    grupo.trocar_janela("menu")
    setar(janela)
    grupo.main_loop()


iniciar_front()

#===================================================================================================================================





        









