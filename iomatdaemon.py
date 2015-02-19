#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
            
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
                           
You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''                                    

import requests, sqlite3, os, commands, pyPdf, smtplib, sys,  traceback, ConfigParser, json, logging
from BeautifulSoup import BeautifulSoup
from datetime import datetime
from email.mime.text import MIMEText



DB_FILENAME = "iomatdaemon.db"
dict_conf = {}


#carrega as configurações
def loadConf():
    global dict_conf
    config = ConfigParser.ConfigParser()
    config.read('defaults.cfg')
    dict_conf = json.loads (config.get("search","emails"))
    #print dict_conf
    #for key in dict_conf.keys():
        #print "Key: %s" % key
    
    global email_subject
    global gmail_username
    global gmail_pw
    
    email_subject = config.get("conf","subject")
    
    #print "email_subject: %s" % email_subject
    
    with sqlite3.connect(DB_FILENAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM conf WHERE id = 1")
        rows = cur.fetchall()
        gmail_username = rows[0][1]
        gmail_pw = rows[0][2]
    #print "username: %s" % gmail_username
    #print "passwd: %s" % gmail_pw
    
    logging_file = datetime.now().strftime("%I:%M%p on %B %d %Y")
    logging.basicConfig(filename=logging_file,level=logging.DEBUG)
    
#classe para representar conexão com BD
#filename: o arquivo do sqlite3
class DBConnection(object):
    def __init__(self):
        self.filename = DB_FILENAME

    def get_connection(self):
         return sqlite3.connect(self.filename)
        
#representa um diário oficial do iomat
#value: value da tag html da página inicial
#date: data do diário (string)
#number: número do diário
class IomatDoc:
    def __init__(self,value,date,number):
        self.value = value
        self.date = date
        self.number = number
    
    def __repr__(self):
        return '[Doc number: %s - date: %s]' % (self.number,self.date)

#classe de acesso ao banco de dados
#iomat_doc: o objeto que será acessado
class IomatDocDAO(object):
    SQL_SELECT = "SELECT * FROM documento WHERE id = %d"
    SQL_INSERT = "INSERT INTO documento (id,date,number) VALUES (%d,%s,%d)"

    def __init__(self,iomat_doc):
        self.iomat_doc = iomat_doc
        self.db_connection = DBConnection()

    #verifica se um documento está no banco de dados
    #retorna True se o documento está presente no bd
    #e False caso contrário
    def is_in_db(self):
        with self.db_connection.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(IomatDocDAO.SQL_SELECT % self.iomat_doc.value)
            rows = cur.fetchall()
            return bool(rows)

    #insere documento no banco de dados
    def insert(self):
        with self.db_connection.get_connection() as conn:
            cur = conn.cursor()
            doc = self.iomat_doc
            cur.execute(IomatDocDAO.SQL_INSERT % (doc.value,doc.date,doc.number))
            conn.commit()

#envia informações extraídas para a lista de e-mails
def sendEmailInfo(info,receiver):
    #print type(info)
    msg = MIMEText(info,_charset="utf-8")
    msg['Subject'] = unicode(email_subject,"utf-8")
    msg['From']=gmail_username
    msg['To']=receiver
    session = smtplib.SMTP('smtp.gmail.com',587)
    session.ehlo()
    session.starttls()
    session.login(gmail_username,gmail_pw)
    session.sendmail(gmail_username,receivers,msg.as_string())
    session.quit()

#recebe um element e busca no arquivo o conteúdo
def getPDFContent(doc,search_terms):
    #print "getPDFContent"
    filename = "iomat_%s.pdf" % (doc.date.replace("/","-"))
    content = ""
    pdf = pyPdf.PdfFileReader(file(filename,'rb'))
    str = ""
    
    for i in range (0,pdf.getNumPages()):
        page_content = pdf.getPage(i).extractText().lower()
        #print type(page_content)
        
        for term in search_terms:
            #print u"Procurando o termo %s" % term
            if page_content.find(term) != -1:
                where = page_content.find(term)
                str = str + "O termo %s foi encontrado no diario %s na pagina %d \n" % (term,filename,i+1)
                other = ""
                if where>60 and (where + 60 < len(page_content)):
                    other = page_content[where-60:where+60]
                str = str + other + "\r\n\r\n"
            
    docLink = "http://www.iomat.mt.gov.br/ler_pdf.php?download=ok\&edi_id=%d\&page=0" % (doc.value)
    str = str + docLink + "\r\n\r\n\r\n"
        
    return str

#retorna os documentos presentes no diário
def retrieveDOIElements():
    r = requests.get ('https://www.iomat.mt.gov.br', verify=False)
    soup = BeautifulSoup(r.text)
    lista = soup.find("select",{"name":"edi_id"})

    elements = []

    for value in lista:
        if unicode(str(value),"utf-8") != unicode("\n","utf-8"):
            value = str(value).decode("utf-8")
            val = int(value.split('"')[1])
            date = (value.split('>')[1]).split('<')[0]
            number = int((value.split('N')[1]).split('--')[0][2:])
            document = IomatDoc(val,date,number)
            elements.append(document)
    
    return elements

#baixa documento
#recebe um element por parâmetro (uma lista)
def downloadDocument(doc):
    try:
        os.system("wget http://www.iomat.mt.gov.br/ler_pdf.php?download=ok\&edi_id=%d\&page=0 -q --output-document iomat_%s.pdf" % (doc.value,doc.date.replace("/","-")))    
    except Exception as exc:
        msg = "iomatdaemon: Exception occured: "+str(type(exc))+"  args:"+str(exc)
        logging.error(msg)
    
def main():
    loadConf()
   
    #busca elementos DOI na página inicial do IOMAT
    elements = retrieveDOIElements()

    for e in elements:
        dao = IomatDocDAO(e)
        if not dao.is_in_db():
            logging.info('Verificando documento: %s' % (str(e)))            
            downloadDocument(e)
            logging.info("Documento baixado")
            str_content = ''
            #print dict_conf
            #print dict_conf.keys()
            
            for key in dict_conf.keys():
                logging.info("Procurando a chave %s" % key)
                str_content = getPDFContent(e,dict_conf[key])
                sendEmailInfo(str_content,key)
                
            dao.insert()

if __name__ == "__main__":
    try:
        gmail_username = None
        gmail_pw = None
        email_subject = None
        main()
    except Exception as exc:
         exc_type, exc_obj, exc_tb = sys.exc_info()
         msg = "iomatdaemon: Exception occured in main: "+str(type(exc))+"  args:"+str(exc)+" line:"+str(exc_tb.tb_lineno)
         #traceback.print_exc()
         logging.error(msg)
