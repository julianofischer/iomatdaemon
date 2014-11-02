#!/usr/bin/python
# encoding: utf-8
# Juliano Fischer Naves

"""
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
"""

import sqlite3,getpass,os

CONF_ID = 1
DB_FILENAME = 'iomatdaemon.db'

def create_db():
    db_filename = 'iomatdaemon.db'

    db_table_documento = """create table if not exists documento (
               id     integer    primary key,
               date   text,
               number integer);
               """
    db_table_conf = """ create table if not exists conf(
               id integer primary key,
               username varchar(50) not null,
               password varchar(100) not null);"""

               
    db_insert_conf = "insert into conf (id,username,password) values (%d,'%s','%s');"
    user = raw_input("Entre com seu usuário do gmail:");
    passwd = getpass.getpass("Entre com sua senha:")
    
    with sqlite3.connect(db_filename) as conn:
       print "Creating database..."
       cur = conn.cursor()
       cur.execute(db_table_documento)
       cur.execute(db_table_conf)
       cur.execute(db_insert_conf % (CONF_ID,user,passwd))
   
def install_cron():
   print "Installing crontab entry..."
   os.system("crontab -l > crontemp")
   cwd = os.getcwd()
   my_script = cwd+"/iomatdaemon.py"
   os.system('echo "0 * * * * python2.7 %s" >> crontemp' % my_script) 
   os.system('crontab crontemp')
   os.system('rm crontemp')
                                                               
if __name__ == "__main__":
   create_db()
   install_cron()
